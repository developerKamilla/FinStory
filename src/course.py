from __future__ import annotations

import csv
import json
from pathlib import Path


def load_lessons(path: str | Path) -> list[dict]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_terms(path: str | Path) -> dict[str, dict]:
    out = {}
    with Path(path).open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            out[row["term"].strip().lower()] = row
    return out


def get_lesson(lessons: list[dict], lesson_id: int) -> dict:
    for lesson in lessons:
        if int(lesson["lesson_id"]) == int(lesson_id):
            return lesson
    raise KeyError(f"Урок {lesson_id} не найден")
