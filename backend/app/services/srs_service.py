"""
Spaced Repetition Service.

Implements a simplified SM-2-inspired algorithm:
  - Every character a user has seen has a mastery_score (0-100).
  - Correct answers increase mastery and push the next_review_at date further out
    (the interval grows by the ease_factor).
  - Incorrect answers drop mastery sharply, reset the interval to be short, and
    slightly reduce the ease_factor so the character comes back around sooner
    and more often until the student gets it right consistently.
  - Question selection is weighted: characters that are "due" for review
    (next_review_at <= now), characters with low mastery, and characters in
    the user's mistake list are all more likely to be picked than a character
    the student has already mastered.
"""
import random
from datetime import datetime, timedelta
from typing import List, Optional

from sqlalchemy.orm import Session

from app import models
from app.utils.data_loader import get_characters

MASTERY_THRESHOLD = 90.0  # mastery_score at/above this counts as "mastered"


def get_or_create_progress(db: Session, user_id: int, character_id: str, script: str) -> models.CharacterProgress:
    progress = (
        db.query(models.CharacterProgress)
        .filter_by(user_id=user_id, character_id=character_id)
        .first()
    )
    if not progress:
        progress = models.CharacterProgress(
            user_id=user_id,
            character_id=character_id,
            script=script,
            mastery_score=0.0,
            interval_days=0.0,
            ease_factor=2.5,
            next_review_at=datetime.utcnow(),
        )
        db.add(progress)
        db.flush()
    return progress


def update_progress_after_answer(progress: models.CharacterProgress, correct: bool) -> models.CharacterProgress:
    progress.times_seen += 1
    progress.last_seen_at = datetime.utcnow()

    if correct:
        progress.times_correct += 1
        # Increase mastery, diminishing returns as it approaches 100
        gain = max(2.0, (100 - progress.mastery_score) * 0.25)
        progress.mastery_score = min(100.0, progress.mastery_score + gain)

        # Grow the review interval (spaced repetition)
        progress.ease_factor = min(3.0, progress.ease_factor + 0.05)
        progress.interval_days = max(1.0, progress.interval_days * progress.ease_factor) if progress.interval_days else 1.0
        progress.next_review_at = datetime.utcnow() + timedelta(days=progress.interval_days)
    else:
        progress.times_wrong += 1
        # Sharp mastery drop on a miss
        progress.mastery_score = max(0.0, progress.mastery_score - 20.0)
        progress.ease_factor = max(1.3, progress.ease_factor - 0.2)
        progress.interval_days = 0.25  # ~6 hours, i.e. "come back soon"
        progress.next_review_at = datetime.utcnow() + timedelta(hours=6)

    return progress


def select_quiz_characters(db: Session, user_id: int, script: str, count: int = 10) -> List[dict]:
    """
    Selects `count` characters for a quiz session, weighted toward:
      - characters due for review (or never seen)
      - characters with low mastery
      - characters currently in the user's active mistake list
    Falls back to random selection from the full pool if there aren't enough
    weighted candidates (e.g. a brand new user).
    """
    pool = get_characters(script)
    if not pool:
        return []

    char_ids = [c["id"] for c in pool]
    progress_rows = (
        db.query(models.CharacterProgress)
        .filter(models.CharacterProgress.user_id == user_id, models.CharacterProgress.character_id.in_(char_ids))
        .all()
    )
    progress_by_id = {p.character_id: p for p in progress_rows}

    now = datetime.utcnow()
    weighted: List[tuple] = []  # (weight, character_dict)

    for char in pool:
        progress = progress_by_id.get(char["id"])
        if progress is None:
            weight = 10.0  # never seen -> high priority
        else:
            due_bonus = 5.0 if progress.next_review_at <= now else 0.5
            mastery_gap = (100.0 - progress.mastery_score) / 100.0  # 0 (mastered) .. 1 (unseen/weak)
            weight = 1.0 + due_bonus + (mastery_gap * 8.0)
        weighted.append((weight, char))

    # Weighted random sample without replacement
    selected = []
    candidates = weighted[:]
    k = min(count, len(candidates))
    for _ in range(k):
        total = sum(w for w, _ in candidates)
        r = random.uniform(0, total)
        upto = 0.0
        for i, (w, char) in enumerate(candidates):
            upto += w
            if upto >= r:
                selected.append(char)
                candidates.pop(i)
                break
    return selected


def get_mastery_map(db: Session, user_id: int, script: str) -> dict:
    """Returns {character_id: mastery_score} for enriching character listings."""
    pool = get_characters(script)
    char_ids = [c["id"] for c in pool]
    rows = (
        db.query(models.CharacterProgress)
        .filter(models.CharacterProgress.user_id == user_id, models.CharacterProgress.character_id.in_(char_ids))
        .all()
    )
    return {r.character_id: r for r in rows}
