"""
Pydantic schemas — request bodies and response models for the API.
"""
from datetime import datetime
from typing import Optional, List, Literal

from pydantic import BaseModel, EmailStr, Field, ConfigDict


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

class UserRegister(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(min_length=6, max_length=100)
    display_name: Optional[str] = None


class UserLogin(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: EmailStr
    display_name: Optional[str] = None
    theme_preference: str
    xp: int
    level: int
    current_streak: int
    longest_streak: int
    created_at: datetime


class UserUpdate(BaseModel):
    display_name: Optional[str] = None
    email: Optional[EmailStr] = None
    theme_preference: Optional[Literal["light", "dark"]] = None


class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(min_length=6, max_length=100)


# ---------------------------------------------------------------------------
# Characters
# ---------------------------------------------------------------------------

class CharacterOut(BaseModel):
    id: str
    script: str
    character: str
    romaji: str
    row: str
    stroke_count: int
    example_word: str
    example_reading: str
    meaning: str
    memory_tip: str
    writing_tip: str
    # user-specific enrichment (optional, populated when authenticated)
    mastery_score: Optional[float] = None
    is_favorite: Optional[bool] = None
    is_bookmarked: Optional[bool] = None


# ---------------------------------------------------------------------------
# Quiz
# ---------------------------------------------------------------------------

QuizType = Literal[
    "char_to_romaji", "romaji_to_char", "multiple_choice", "timed", "mixed"
]
ScriptType = Literal["hiragana", "katakana", "mixed"]


class QuizQuestion(BaseModel):
    question_id: str          # character_id, reused as the question reference
    script: str
    quiz_type: QuizType
    prompt: str                # what is shown to the student (character or romaji)
    options: Optional[List[str]] = None  # populated for multiple_choice
    timer_seconds: Optional[int] = None


class QuizAnswerIn(BaseModel):
    question_id: str
    quiz_type: QuizType
    script: str
    submitted_answer: str
    response_time_ms: Optional[int] = None


class QuizAnswerOut(BaseModel):
    correct: bool
    correct_answer: str
    character: str
    example_word: str
    meaning: str
    xp_awarded: int
    new_mastery_score: float
    streak: int
    leveled_up: bool
    new_level: int
    unlocked_achievements: List[str] = []


# ---------------------------------------------------------------------------
# Progress
# ---------------------------------------------------------------------------

class ProgressOut(BaseModel):
    total_correct: int
    total_wrong: int
    accuracy: float
    current_streak: int
    longest_streak: int
    characters_learned: int
    characters_mastered: int
    average_response_time_ms: float
    daily_practice: dict
    weekly_practice: dict
    monthly_practice: dict
    xp: int
    level: int


class ProgressUpdateIn(BaseModel):
    """Allows the client to explicitly log a completed study session (e.g. flashcards)."""
    session_type: Literal["quiz", "flashcards"]
    script: ScriptType
    questions_answered: int = 0
    correct_answers: int = 0


# ---------------------------------------------------------------------------
# Mistakes
# ---------------------------------------------------------------------------

class MistakeOut(BaseModel):
    character_id: str
    script: str
    character: str
    romaji: str
    mistake_count: int
    last_missed_at: datetime


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

class DashboardOut(BaseModel):
    user: UserOut
    progress: ProgressOut
    recent_mistakes: List[MistakeOut]
    achievements: List[dict]
    daily_challenge: dict


# ---------------------------------------------------------------------------
# Export / Import
# ---------------------------------------------------------------------------

class ExportData(BaseModel):
    user: UserOut
    progress: ProgressOut
    character_progress: List[dict]
    achievements: List[dict]
