"""
Learning routes: browse Hiragana / Katakana character tables, view a single
character's full lesson, and search across all characters.

These endpoints work for anonymous visitors (so the home page / character
library is browsable without an account) but are enriched with mastery
scores, favorite, and bookmark flags whenever a valid token is supplied.
"""
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas, auth
from app.utils.data_loader import get_characters, get_character_by_id
from app.services import srs_service

router = APIRouter(tags=["Learning"])


def _enrich(char: dict, db: Session, user: Optional[models.User]) -> dict:
    out = dict(char)
    if user:
        progress = db.query(models.CharacterProgress).filter_by(
            user_id=user.id, character_id=char["id"]
        ).first()
        out["mastery_score"] = progress.mastery_score if progress else 0.0
        out["is_favorite"] = progress.is_favorite if progress else False
        out["is_bookmarked"] = progress.is_bookmarked if progress else False
    return out


@router.get("/hiragana", response_model=List[schemas.CharacterOut])
def list_hiragana(
    db: Session = Depends(get_db),
    user: Optional[models.User] = Depends(auth.get_current_user_optional),
):
    return [_enrich(c, db, user) for c in get_characters("hiragana")]


@router.get("/katakana", response_model=List[schemas.CharacterOut])
def list_katakana(
    db: Session = Depends(get_db),
    user: Optional[models.User] = Depends(auth.get_current_user_optional),
):
    return [_enrich(c, db, user) for c in get_characters("katakana")]


@router.get("/character/{character_id}", response_model=schemas.CharacterOut)
def get_character(
    character_id: str,
    db: Session = Depends(get_db),
    user: Optional[models.User] = Depends(auth.get_current_user_optional),
):
    char = get_character_by_id(character_id)
    if not char:
        raise HTTPException(status_code=404, detail="Character not found")
    return _enrich(char, db, user)


@router.get("/search", response_model=List[schemas.CharacterOut])
def search_characters(
    q: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
    user: Optional[models.User] = Depends(auth.get_current_user_optional),
):
    """Search by character, romaji, or example word (case-insensitive substring match)."""
    q_lower = q.lower()
    all_chars = get_characters("mixed")
    matches = [
        c for c in all_chars
        if q_lower in c["character"].lower()
        or q_lower in c["romaji"].lower()
        or q_lower in c["example_word"].lower()
        or q_lower in c["meaning"].lower()
    ]
    return [_enrich(c, db, user) for c in matches]


@router.post("/character/{character_id}/favorite")
def toggle_favorite(
    character_id: str,
    db: Session = Depends(get_db),
    user: models.User = Depends(auth.get_current_user),
):
    char = get_character_by_id(character_id)
    if not char:
        raise HTTPException(status_code=404, detail="Character not found")
    progress = srs_service.get_or_create_progress(db, user.id, character_id, char["script"])
    progress.is_favorite = not progress.is_favorite
    db.commit()
    return {"character_id": character_id, "is_favorite": progress.is_favorite}


@router.post("/character/{character_id}/bookmark")
def toggle_bookmark(
    character_id: str,
    db: Session = Depends(get_db),
    user: models.User = Depends(auth.get_current_user),
):
    char = get_character_by_id(character_id)
    if not char:
        raise HTTPException(status_code=404, detail="Character not found")
    progress = srs_service.get_or_create_progress(db, user.id, character_id, char["script"])
    progress.is_bookmarked = not progress.is_bookmarked
    db.commit()
    return {"character_id": character_id, "is_bookmarked": progress.is_bookmarked}
