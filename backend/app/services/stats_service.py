"""
Stats Service — ties together quiz history logging, mistake tracking,
per-character progress (SRS), user aggregate stats, and gamification
whenever a student answers a question. Also computes the data shown on
the Progress page (daily/weekly/monthly practice, accuracy, streak, etc).
"""
import json
from datetime import datetime, date, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from app import models
from app.services import srs_service, gamification_service
from app.utils.data_loader import get_characters


def get_or_create_stats(db: Session, user_id: int) -> models.UserStats:
    stats = db.query(models.UserStats).filter_by(user_id=user_id).first()
    if not stats:
        stats = models.UserStats(user_id=user_id, daily_log="{}")
        db.add(stats)
        db.flush()
    return stats


def _bump_daily_log(stats: models.UserStats, correct: bool) -> None:
    log = json.loads(stats.daily_log or "{}")
    today = date.today().isoformat()
    day = log.get(today, {"answered": 0, "correct": 0})
    day["answered"] += 1
    if correct:
        day["correct"] += 1
    log[today] = day
    stats.daily_log = json.dumps(log)


def _count_mastered(db: Session, user_id: int, script: str) -> int:
    char_ids = [c["id"] for c in get_characters(script)]
    if not char_ids:
        return 0
    return (
        db.query(models.CharacterProgress)
        .filter(
            models.CharacterProgress.user_id == user_id,
            models.CharacterProgress.character_id.in_(char_ids),
            models.CharacterProgress.mastery_score >= srs_service.MASTERY_THRESHOLD,
        )
        .count()
    )


def record_answer(
    db: Session,
    user: models.User,
    character_id: str,
    script: str,
    quiz_type: str,
    prompt: str,
    correct_answer: str,
    submitted_answer: str,
    correct: bool,
    response_time_ms: Optional[int] = None,
) -> dict:
    """
    Full pipeline executed whenever a student submits a quiz answer:
      1. Log the raw answer in quiz_history
      2. Update per-character SRS mastery
      3. Update / clear mistake tracking
      4. Update aggregate UserStats + daily log
      5. Award XP, update streak, check for level up
      6. Check for newly unlocked achievements
    Returns a dict summarizing everything the API response needs.
    """
    # 1. Quiz history log
    history = models.QuizHistory(
        user_id=user.id,
        character_id=character_id,
        script=script,
        quiz_type=quiz_type,
        question_prompt=prompt,
        correct_answer=correct_answer,
        submitted_answer=submitted_answer,
        was_correct=correct,
        response_time_ms=response_time_ms,
    )
    db.add(history)

    # 2. SRS mastery update
    progress = srs_service.get_or_create_progress(db, user.id, character_id, script)
    srs_service.update_progress_after_answer(progress, correct)

    # 3. Mistake tracking
    mistake = db.query(models.Mistake).filter_by(user_id=user.id, character_id=character_id).first()
    if correct:
        if mistake:
            mistake.resolved = True
    else:
        if mistake:
            mistake.mistake_count += 1
            mistake.last_missed_at = datetime.utcnow()
            mistake.resolved = False
        else:
            mistake = models.Mistake(
                user_id=user.id, character_id=character_id, script=script,
                mistake_count=1, last_missed_at=datetime.utcnow(), resolved=False,
            )
            db.add(mistake)

    # 4. Aggregate stats
    stats = get_or_create_stats(db, user.id)
    stats.total_answered += 1
    if correct:
        stats.total_correct += 1
    else:
        stats.total_wrong += 1
    if response_time_ms:
        stats.total_response_time_ms += response_time_ms
    _bump_daily_log(stats, correct)

    stats.characters_learned = (
        db.query(models.CharacterProgress).filter_by(user_id=user.id).count()
    )
    stats.characters_mastered = _count_mastered(db, user.id, "mixed")

    # 5. Gamification
    xp_awarded = gamification_service.award_xp(user, correct)
    gamification_service.update_daily_streak(user)
    leveled_up = gamification_service.check_level_up(user)

    # 6. Achievements
    hira_mastered = _count_mastered(db, user.id, "hiragana")
    kata_mastered = _count_mastered(db, user.id, "katakana")
    unlocked = gamification_service.check_and_unlock_achievements(
        db, user, stats, hira_mastered, kata_mastered
    )

    db.commit()
    db.refresh(user)
    db.refresh(progress)

    return {
        "xp_awarded": xp_awarded,
        "new_mastery_score": progress.mastery_score,
        "streak": user.current_streak,
        "leveled_up": leveled_up,
        "new_level": user.level,
        "unlocked_achievements": unlocked,
    }


def compute_progress(db: Session, user: models.User) -> dict:
    stats = get_or_create_stats(db, user.id)
    log = json.loads(stats.daily_log or "{}")

    total = stats.total_correct + stats.total_wrong
    accuracy = round((stats.total_correct / total) * 100, 1) if total else 0.0
    avg_response = (
        round(stats.total_response_time_ms / stats.total_answered, 0)
        if stats.total_answered else 0.0
    )

    today = date.today()
    daily_practice = {}
    for i in range(7):
        d = (today - timedelta(days=i)).isoformat()
        entry = log.get(d, {"answered": 0, "correct": 0})
        daily_practice[d] = entry

    # weekly: last 4 ISO weeks, summed
    weekly_practice = {}
    for w in range(4):
        week_start = today - timedelta(days=today.weekday() + 7 * w)
        week_key = f"week_of_{week_start.isoformat()}"
        answered = correct = 0
        for i in range(7):
            d = (week_start + timedelta(days=i)).isoformat()
            entry = log.get(d)
            if entry:
                answered += entry.get("answered", 0)
                correct += entry.get("correct", 0)
        weekly_practice[week_key] = {"answered": answered, "correct": correct}

    # monthly: last 6 calendar months, summed
    monthly_practice = {}
    for m in range(6):
        year = today.year
        month = today.month - m
        while month <= 0:
            month += 12
            year -= 1
        month_key = f"{year}-{month:02d}"
        answered = correct = 0
        for d_str, entry in log.items():
            if d_str.startswith(month_key):
                answered += entry.get("answered", 0)
                correct += entry.get("correct", 0)
        monthly_practice[month_key] = {"answered": answered, "correct": correct}

    return {
        "total_correct": stats.total_correct,
        "total_wrong": stats.total_wrong,
        "accuracy": accuracy,
        "current_streak": user.current_streak,
        "longest_streak": user.longest_streak,
        "characters_learned": stats.characters_learned,
        "characters_mastered": stats.characters_mastered,
        "average_response_time_ms": avg_response,
        "daily_practice": daily_practice,
        "weekly_practice": weekly_practice,
        "monthly_practice": monthly_practice,
        "xp": user.xp,
        "level": user.level,
    }
