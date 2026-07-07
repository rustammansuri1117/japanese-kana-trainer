"""
Mistakes routes — lets a student see (and clear) the characters they've
previously gotten wrong, split by script.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas, auth
from app.utils.data_loader import get_character_by_id

router = APIRouter(prefix="/mistakes", tags=["Mistakes"])


@router.get("", response_model=List[schemas.MistakeOut])
def list_mistakes(
    script: Optional[schemas.ScriptType] = Query(None),
    include_resolved: bool = Query(False),
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(models.Mistake).filter_by(user_id=current_user.id)
    if not include_resolved:
        query = query.filter_by(resolved=False)
    if script and script != "mixed":
        query = query.filter_by(script=script)

    mistakes = query.order_by(models.Mistake.last_missed_at.desc()).all()
    out = []
    for m in mistakes:
        char = get_character_by_id(m.character_id)
        if not char:
            continue
        out.append(schemas.MistakeOut(
            character_id=m.character_id,
            script=m.script,
            character=char["character"],
            romaji=char["romaji"],
            mistake_count=m.mistake_count,
            last_missed_at=m.last_missed_at,
        ))
    return out


@router.delete("/{character_id}")
def clear_mistake(
    character_id: str,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    mistake = db.query(models.Mistake).filter_by(
        user_id=current_user.id, character_id=character_id
    ).first()
    if mistake:
        mistake.resolved = True
        db.commit()
    return {"message": "Mistake cleared"}
