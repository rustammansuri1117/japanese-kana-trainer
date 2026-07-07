"""
Progress routes: view aggregate progress stats, and explicitly log a
completed study session (used by the Flashcards page, which doesn't go
through /quiz/check for every card flip).
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import datetime

from app.database import get_db
from app import models, schemas, auth
from app.services import stats_service, gamification_service

router = APIRouter(prefix="/progress", tags=["Progress"])


@router.get("", response_model=schemas.ProgressOut)
def get_progress(
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    return stats_service.compute_progress(db, current_user)


@router.post("", response_model=schemas.ProgressOut)
def log_study_session(
    payload: schemas.ProgressUpdateIn,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    session = models.StudySession(
        user_id=current_user.id,
        session_type=payload.session_type,
        script=payload.script,
        ended_at=datetime.utcnow(),
        questions_answered=payload.questions_answered,
        correct_answers=payload.correct_answers,
    )
    db.add(session)

    # Flashcard sessions still count toward the daily streak and give a small XP bonus.
    if payload.questions_answered > 0:
        gamification_service.update_daily_streak(current_user)
        current_user.xp += min(payload.questions_answered, 20)  # capped small bonus
        gamification_service.check_level_up(current_user)

    db.commit()
    return stats_service.compute_progress(db, current_user)
