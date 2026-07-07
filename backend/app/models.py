"""
SQLAlchemy ORM models for the Japanese Kana Trainer.

Tables:
    User            - registered students
    CharacterProgress - per-user, per-character mastery / spaced-repetition state
    QuizHistory     - a log of every question answered
    Mistake         - characters a user has gotten wrong, for the mistake-review feature
    StudySession    - a single practice session (quiz or flashcard run)
    Achievement     - unlocked badges / achievements
    UserStats       - aggregate, frequently-read statistics for a user (denormalized for speed)
"""
from datetime import datetime

from sqlalchemy import (
    Column, Integer, String, Boolean, Float, DateTime, ForeignKey, Text
)
from sqlalchemy.orm import relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    display_name = Column(String(100), nullable=True)
    theme_preference = Column(String(10), default="light")  # "light" or "dark"

    xp = Column(Integer, default=0)
    level = Column(Integer, default=1)
    current_streak = Column(Integer, default=0)
    longest_streak = Column(Integer, default=0)
    last_practice_date = Column(String(10), nullable=True)  # ISO date "YYYY-MM-DD"

    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)

    progress_entries = relationship("CharacterProgress", back_populates="user", cascade="all, delete-orphan")
    quiz_history = relationship("QuizHistory", back_populates="user", cascade="all, delete-orphan")
    mistakes = relationship("Mistake", back_populates="user", cascade="all, delete-orphan")
    sessions = relationship("StudySession", back_populates="user", cascade="all, delete-orphan")
    achievements = relationship("Achievement", back_populates="user", cascade="all, delete-orphan")
    stats = relationship("UserStats", back_populates="user", uselist=False, cascade="all, delete-orphan")


class CharacterProgress(Base):
    """Per-user mastery state for a single kana character (drives spaced repetition)."""
    __tablename__ = "character_progress"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    character_id = Column(String(20), nullable=False, index=True)  # e.g. "hiragana_001"
    script = Column(String(10), nullable=False)  # "hiragana" | "katakana"

    times_seen = Column(Integer, default=0)
    times_correct = Column(Integer, default=0)
    times_wrong = Column(Integer, default=0)
    mastery_score = Column(Float, default=0.0)  # 0.0 (unseen) - 100.0 (mastered)

    # Simple spaced-repetition bookkeeping (SM-2-inspired but simplified)
    interval_days = Column(Float, default=0.0)
    ease_factor = Column(Float, default=2.5)
    next_review_at = Column(DateTime, default=datetime.utcnow)
    last_seen_at = Column(DateTime, nullable=True)
    is_favorite = Column(Boolean, default=False)
    is_bookmarked = Column(Boolean, default=False)

    user = relationship("User", back_populates="progress_entries")


class QuizHistory(Base):
    """A log entry for every single question answered, across all quiz types."""
    __tablename__ = "quiz_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    character_id = Column(String(20), nullable=False, index=True)
    script = Column(String(10), nullable=False)
    quiz_type = Column(String(30), nullable=False)  # char_to_romaji, romaji_to_char, multiple_choice, timed, mixed
    question_prompt = Column(String(50), nullable=False)
    correct_answer = Column(String(50), nullable=False)
    submitted_answer = Column(String(50), nullable=True)
    was_correct = Column(Boolean, nullable=False)
    response_time_ms = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="quiz_history")


class Mistake(Base):
    """Tracks characters a user has answered incorrectly, for the mistake-review feature."""
    __tablename__ = "mistakes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    character_id = Column(String(20), nullable=False, index=True)
    script = Column(String(10), nullable=False)
    mistake_count = Column(Integer, default=1)
    last_missed_at = Column(DateTime, default=datetime.utcnow)
    resolved = Column(Boolean, default=False)  # marked resolved once mastered again

    user = relationship("User", back_populates="mistakes")


class StudySession(Base):
    """A single practice session — a quiz run or flashcard run."""
    __tablename__ = "study_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    session_type = Column(String(20), nullable=False)  # "quiz" | "flashcards"
    script = Column(String(10), nullable=False)  # hiragana | katakana | mixed
    started_at = Column(DateTime, default=datetime.utcnow)
    ended_at = Column(DateTime, nullable=True)
    questions_answered = Column(Integer, default=0)
    correct_answers = Column(Integer, default=0)

    user = relationship("User", back_populates="sessions")


class Achievement(Base):
    """Unlocked achievements / badges."""
    __tablename__ = "achievements"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    code = Column(String(50), nullable=False)  # unique key, e.g. "first_quiz"
    title = Column(String(100), nullable=False)
    description = Column(String(255), nullable=False)
    icon = Column(String(10), default="🏅")
    earned_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="achievements")


class UserStats(Base):
    """Denormalized aggregate stats for fast dashboard/progress reads."""
    __tablename__ = "user_stats"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False, index=True)

    total_correct = Column(Integer, default=0)
    total_wrong = Column(Integer, default=0)
    total_response_time_ms = Column(Integer, default=0)
    total_answered = Column(Integer, default=0)

    characters_learned = Column(Integer, default=0)   # seen at least once
    characters_mastered = Column(Integer, default=0)  # mastery_score >= 90

    daily_log = Column(Text, default="{}")   # JSON string: {"2026-07-06": {"answered": 10, "correct": 8}}

    user = relationship("User", back_populates="stats")
