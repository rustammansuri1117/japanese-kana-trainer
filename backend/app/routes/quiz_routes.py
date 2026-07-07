"""
Quiz routes — the core learning-loop feature of the app.

GET  /quiz/random   generates the next question (character->romaji,
                     romaji->character, multiple choice, timed, or a random
                     mix of the above), optionally restricted to the user's
                     mistake list for "Review Mistakes" mode.
POST /quiz/check    validates a submitted answer, updates mastery / XP /
                     streaks / achievements, and returns the correct answer
                     immediately so the frontend can show a checkmark/X and
                     auto-advance to the next question.
"""
import random
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas, auth
from app.utils.data_loader import get_characters, get_character_by_id
from app.services import srs_service, stats_service

router = APIRouter(prefix="/quiz", tags=["Quiz"])

DIRECTIONAL_TYPES = ("char_to_romaji", "romaji_to_char")


def _build_multiple_choice_options(correct_char: dict, script: str, direction: str) -> list:
    pool = [c for c in get_characters(script if script != "mixed" else correct_char["script"]) if c["id"] != correct_char["id"]]
    distractors = random.sample(pool, k=min(3, len(pool)))
    if direction == "char_to_romaji":
        options = [d["romaji"] for d in distractors] + [correct_char["romaji"]]
    else:
        options = [d["character"] for d in distractors] + [correct_char["character"]]
    random.shuffle(options)
    return options


@router.get("/random", response_model=schemas.QuizQuestion)
def get_random_question(
    script: schemas.ScriptType = Query("hiragana"),
    quiz_type: schemas.QuizType = Query("char_to_romaji"),
    review_mistakes: bool = Query(False),
    timer_seconds: Optional[int] = Query(None, description="5, 10, 15, or omit for unlimited"),
    db: Session = Depends(get_db),
    user: models.User = Depends(auth.get_current_user),
):
    if review_mistakes:
        query = db.query(models.Mistake).filter_by(user_id=user.id, resolved=False)
        if script != "mixed":
            query = query.filter_by(script=script)
        mistakes = query.all()
        if not mistakes:
            raise HTTPException(status_code=404, detail="No mistakes to review — great job!")
        mistake = random.choice(mistakes)
        char = get_character_by_id(mistake.character_id)
    else:
        candidates = srs_service.select_quiz_characters(db, user.id, script, count=1)
        if not candidates:
            raise HTTPException(status_code=404, detail="No characters available for this script")
        char = candidates[0]

    # Resolve actual quiz_type when "mixed" direction requested
    effective_type = quiz_type
    if quiz_type == "mixed":
        effective_type = random.choice(["char_to_romaji", "romaji_to_char", "multiple_choice"])
    elif quiz_type == "timed" and timer_seconds is None:
        timer_seconds = 10

    direction = "char_to_romaji" if effective_type in ("char_to_romaji", "timed", "multiple_choice") else "romaji_to_char"
    prompt = char["character"] if direction == "char_to_romaji" else char["romaji"]

    options = None
    if effective_type == "multiple_choice" or direction == "romaji_to_char":
        options = _build_multiple_choice_options(char, script, direction)

    return schemas.QuizQuestion(
        question_id=char["id"],
        script=char["script"],
        quiz_type=quiz_type,
        prompt=prompt,
        options=options,
        timer_seconds=timer_seconds,
    )


@router.post("/check", response_model=schemas.QuizAnswerOut)
def check_answer(
    payload: schemas.QuizAnswerIn,
    db: Session = Depends(get_db),
    user: models.User = Depends(auth.get_current_user),
):
    char = get_character_by_id(payload.question_id)
    if not char:
        raise HTTPException(status_code=404, detail="Unknown character")

    direction = "char_to_romaji"
    if payload.quiz_type == "romaji_to_char":
        direction = "romaji_to_char"

    correct_answer = char["romaji"] if direction == "char_to_romaji" else char["character"]
    submitted_norm = payload.submitted_answer.strip().lower()
    correct_norm = correct_answer.strip().lower()
    is_correct = submitted_norm == correct_norm

    prompt = char["character"] if direction == "char_to_romaji" else char["romaji"]

    result = stats_service.record_answer(
        db=db,
        user=user,
        character_id=char["id"],
        script=char["script"],
        quiz_type=payload.quiz_type,
        prompt=prompt,
        correct_answer=correct_answer,
        submitted_answer=payload.submitted_answer,
        correct=is_correct,
        response_time_ms=payload.response_time_ms,
    )

    return schemas.QuizAnswerOut(
        correct=is_correct,
        correct_answer=correct_answer,
        character=char["character"],
        example_word=char["example_word"],
        meaning=char["meaning"],
        **result,
    )
