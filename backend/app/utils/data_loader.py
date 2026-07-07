"""
Loads the static kana character data (Hiragana / Katakana) from JSON files
into memory once at import time. This keeps character lookups fast (no DB
round-trip needed) while still allowing Kanji to be added later simply by
dropping in a new kanji.json file and a loader function.
"""
import json
import os
from functools import lru_cache
from typing import Dict, List, Optional

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")


def _load_json(filename: str) -> List[dict]:
    path = os.path.join(DATA_DIR, filename)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


@lru_cache(maxsize=1)
def _all_characters() -> Dict[str, dict]:
    """Returns a dict keyed by character_id, combining all supported scripts."""
    combined: Dict[str, dict] = {}
    for record in _load_json("hiragana.json"):
        combined[record["id"]] = record
    for record in _load_json("katakana.json"):
        combined[record["id"]] = record
    return combined


def get_characters(script: str) -> List[dict]:
    """script: 'hiragana', 'katakana', or 'mixed' (returns both)."""
    all_chars = _all_characters()
    if script == "mixed":
        return list(all_chars.values())
    return [c for c in all_chars.values() if c["script"] == script]


def get_character_by_id(character_id: str) -> Optional[dict]:
    return _all_characters().get(character_id)


def get_total_character_count(script: str = "mixed") -> int:
    return len(get_characters(script))
