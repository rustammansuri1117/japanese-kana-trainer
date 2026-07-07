"""
Gamification Service — XP, levels, daily streaks, and achievement unlocking.
"""
from datetime import datetime, timedelta, date
from typing import List

from sqlalchemy.orm import Session

from app import models

XP_PER_CORRECT = 10
XP_PER_WRONG = 2  # small consolation XP so users still feel progress
XP_PER_LEVEL = 200  # flat XP curve for simplicity: level = xp // 200 + 1

ACHIEVEMENTS = [
    {"code": "first_quiz", "title": "First Steps", "description": "Answer your first quiz question.", "icon": "🎯"},
    {"code": "streak_3", "title": "Getting Warmed Up", "description": "Practice 3 days in a row.", "icon": "🔥"},
    {"code": "streak_7", "title": "Week Warrior", "description": "Practice 7 days in a row.", "icon": "🏆"},
    {"code": "streak_30", "title": "Dedicated Student", "description": "Practice 30 days in a row.", "icon": "💎"},
    {"code": "correct_50", "title": "Half Century", "description": "Answer 50 questions correctly.", "icon": "⭐"},
    {"code": "correct_200", "title": "Kana Machine", "description": "Answer 200 questions correctly.", "icon": "🚀"},
    {"code": "hiragana_mastered", "title": "Hiragana Hero", "description": "Master all 46 Hiragana characters.", "icon": "🀄"},
    {"code": "katakana_mastered", "title": "Katakana King", "description": "Master all 46 Katakana characters.", "icon": "👑"},
    {"code": "level_5", "title": "Rising Star", "description": "Reach level 5.", "icon": "🌟"},
    {"code": "level_10", "title": "Kana Sensei", "description": "Reach level 10.", "icon": "🎓"},
]


def award_xp(user: models.User, correct: bool) -> int:
    amount = XP_PER_CORRECT if correct else XP_PER_WRONG
    user.xp += amount
    return amount


def check_level_up(user: models.User) -> bool:
    new_level = (user.xp // XP_PER_LEVEL) + 1
    leveled_up = new_level > user.level
    user.level = new_level
    return leveled_up


def update_daily_streak(user: models.User) -> None:
    today = date.today().isoformat()
    if user.last_practice_date == today:
        return  # already counted today
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    if user.last_practice_date == yesterday:
        user.current_streak += 1
    else:
        user.current_streak = 1
    user.longest_streak = max(user.longest_streak, user.current_streak)
    user.last_practice_date = today


def _grant(db: Session, user: models.User, code: str) -> str | None:
    existing = db.query(models.Achievement).filter_by(user_id=user.id, code=code).first()
    if existing:
        return None
    meta = next((a for a in ACHIEVEMENTS if a["code"] == code), None)
    if not meta:
        return None
    ach = models.Achievement(
        user_id=user.id, code=code, title=meta["title"],
        description=meta["description"], icon=meta["icon"],
    )
    db.add(ach)
    return meta["title"]


def check_and_unlock_achievements(
    db: Session, user: models.User, stats: models.UserStats,
    hiragana_mastered_count: int, katakana_mastered_count: int,
) -> List[str]:
    unlocked = []

    if stats.total_answered == 1:
        r = _grant(db, user, "first_quiz")
        if r:
            unlocked.append(r)
    if user.current_streak >= 3:
        r = _grant(db, user, "streak_3")
        if r:
            unlocked.append(r)
    if user.current_streak >= 7:
        r = _grant(db, user, "streak_7")
        if r:
            unlocked.append(r)
    if user.current_streak >= 30:
        r = _grant(db, user, "streak_30")
        if r:
            unlocked.append(r)
    if stats.total_correct >= 50:
        r = _grant(db, user, "correct_50")
        if r:
            unlocked.append(r)
    if stats.total_correct >= 200:
        r = _grant(db, user, "correct_200")
        if r:
            unlocked.append(r)
    if hiragana_mastered_count >= 46:
        r = _grant(db, user, "hiragana_mastered")
        if r:
            unlocked.append(r)
    if katakana_mastered_count >= 46:
        r = _grant(db, user, "katakana_mastered")
        if r:
            unlocked.append(r)
    if user.level >= 5:
        r = _grant(db, user, "level_5")
        if r:
            unlocked.append(r)
    if user.level >= 10:
        r = _grant(db, user, "level_10")
        if r:
            unlocked.append(r)

    return unlocked
