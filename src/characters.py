from __future__ import annotations

import json
from pathlib import Path


def load_characters(path: str | Path) -> list[dict]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def choose_character(characters: list[dict], main_interest: str, lesson_id: int) -> dict:
    candidates = [c for c in characters if main_interest in c.get("natural_interests", [])]
    pool = candidates or characters
    return pool[(lesson_id - 1) % len(pool)]
