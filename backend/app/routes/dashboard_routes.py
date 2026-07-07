"""
Dashboard route — a single combined payload for the dashboard.html page:
user info, progress summary, recent mistakes, achievements, and a
deterministic "daily challenge" (same challenge for everyone on a given
calendar day, changes automatically at midnight UTC).
"""
import hashlib
from datetime import date
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas, auth
from app.services import stats_service
from app.utils.data_loader import get_characters

router = APIRouter(tags=["Dashboard"])

DAILY_CHALLENGE_SIZE = 10


def _daily_challenge_for_today() -> dict:
    """Deterministically picks a script + a seeded set of characters for today,
    so every user gets the same daily challenge and it's stable across requests."""
    today = date.today().isoformat()
    seed = int(hashlib.sha256(today.encode()).hexdigest(), 16)
    script = "hiragana" if seed % 2 == 0 else "katakana"
    pool = get_characters(script)
    # Deterministic shuffle using the date-based seed
    indices = list(range(len(pool)))
    rnd_state = seed
    for i in range(len(indices) - 1, 0, -1):
        rnd_state = (rnd_state * 1103515245 + 12345) & 0x7FFFFFFF
        j = rnd_state % (i + 1)
        indices[i], indices[j] = indices[j], indices[i]
    chosen = [pool[i] for i in indices[:DAILY_CHALLENGE_SIZE]]
    return {
        "date": today,
        "script": script,
        "character_count": len(chosen),
        "character_ids": [c["id"] for c in chosen],
        "reward_xp": 50,
    }


@router.get("/dashboard", response_model=schemas.DashboardOut)
def get_dashboard(
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    progress = stats_service.compute_progress(db, current_user)

    mistakes = (
        db.query(models.Mistake)
        .filter_by(user_id=current_user.id, resolved=False)
        .order_by(models.Mistake.last_missed_at.desc())
        .limit(5)
        .all()
    )
    from app.utils.data_loader import get_character_by_id
    recent_mistakes = []
    for m in mistakes:
        char = get_character_by_id(m.character_id)
        if char:
            recent_mistakes.append(schemas.MistakeOut(
                character_id=m.character_id, script=m.script,
                character=char["character"], romaji=char["romaji"],
                mistake_count=m.mistake_count, last_missed_at=m.last_missed_at,
            ))

    achievements = (
        db.query(models.Achievement)
        .filter_by(user_id=current_user.id)
        .order_by(models.Achievement.earned_at.desc())
        .all()
    )
    achievements_out = [
        {"code": a.code, "title": a.title, "description": a.description,
         "icon": a.icon, "earned_at": a.earned_at.isoformat()}
        for a in achievements
    ]

    return schemas.DashboardOut(
        user=current_user,
        progress=progress,
        recent_mistakes=recent_mistakes,
        achievements=achievements_out,
        daily_challenge=_daily_challenge_for_today(),
    )
