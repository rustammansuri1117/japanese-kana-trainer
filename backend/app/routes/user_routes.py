"""
User profile routes: view/edit profile, change password, export/import progress.
"""
import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas, auth
from app.services import stats_service

router = APIRouter(prefix="/user", tags=["User Profile"])


@router.get("/profile", response_model=schemas.UserOut)
def get_profile(current_user: models.User = Depends(auth.get_current_user)):
    return current_user


@router.put("/profile", response_model=schemas.UserOut)
def update_profile(
    payload: schemas.UserUpdate,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    if payload.display_name is not None:
        current_user.display_name = payload.display_name
    if payload.email is not None:
        existing = db.query(models.User).filter(
            models.User.email == payload.email, models.User.id != current_user.id
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="Email already in use")
        current_user.email = payload.email
    if payload.theme_preference is not None:
        current_user.theme_preference = payload.theme_preference

    db.commit()
    db.refresh(current_user)
    return current_user


@router.post("/change-password")
def change_password(
    payload: schemas.PasswordChange,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    if not auth.verify_password(payload.current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    current_user.hashed_password = auth.hash_password(payload.new_password)
    db.commit()
    return {"message": "Password updated successfully"}


@router.get("/export", response_model=schemas.ExportData)
def export_progress(
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    progress = stats_service.compute_progress(db, current_user)
    char_progress = db.query(models.CharacterProgress).filter_by(user_id=current_user.id).all()
    achievements = db.query(models.Achievement).filter_by(user_id=current_user.id).all()

    return {
        "user": current_user,
        "progress": progress,
        "character_progress": [
            {
                "character_id": c.character_id,
                "script": c.script,
                "mastery_score": c.mastery_score,
                "times_seen": c.times_seen,
                "times_correct": c.times_correct,
                "times_wrong": c.times_wrong,
            }
            for c in char_progress
        ],
        "achievements": [
            {"code": a.code, "title": a.title, "description": a.description, "icon": a.icon}
            for a in achievements
        ],
    }


@router.post("/import")
def import_progress(
    data: dict,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    """Restores character_progress mastery scores from a previously exported file.
    This intentionally only restores per-character mastery (non-destructive to
    quiz history / achievements) to avoid conflicting duplicate log entries.
    """
    char_progress = data.get("character_progress", [])
    restored = 0
    for entry in char_progress:
        cid = entry.get("character_id")
        if not cid:
            continue
        progress = db.query(models.CharacterProgress).filter_by(
            user_id=current_user.id, character_id=cid
        ).first()
        if not progress:
            progress = models.CharacterProgress(
                user_id=current_user.id, character_id=cid, script=entry.get("script", "hiragana")
            )
            db.add(progress)
        progress.mastery_score = entry.get("mastery_score", progress.mastery_score)
        progress.times_seen = entry.get("times_seen", progress.times_seen)
        progress.times_correct = entry.get("times_correct", progress.times_correct)
        progress.times_wrong = entry.get("times_wrong", progress.times_wrong)
        restored += 1
    db.commit()
    return {"message": f"Restored progress for {restored} characters"}
