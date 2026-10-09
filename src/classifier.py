from __future__ import annotations

from pathlib import Path
from typing import Iterable

import joblib

from .constants import INTEREST_LABELS


KEYWORDS = {
    "gaming": ["игр", "minecraft", "майн", "dota", "дота", "cs", "кс", "roblox", "фортнайт", "valorant"],
    "sport": ["спорт", "футбол", "баскет", "волейбол", "хоккей", "бег", "теннис", "зал", "фитнес", "формул"],
    "music": ["музык", "пес", "рэп", "рок", "концерт", "гитар", "пианино", "исполнител"],
    "movies": ["кино", "фильм", "сериал", "аниме", "marvel", "марвел", "netflix"],
    "tech": ["программ", "код", "python", "java", "ai", "ии", "компьют", "робот", "технолог"],
    "science": ["физик", "хими", "биолог", "космос", "математ", "наук", "астроном"],
    "business": ["бизнес", "стартап", "эконом", "предприним", "маркет", "продаж"],
    "books": ["книг", "чита", "литератур", "роман", "комикс"],
    "travel": ["путеше", "поезд", "страны", "туризм", "летать", "город"],
    "art": ["рис", "дизайн", "фото", "творч", "иллюстр", "монтаж"],
    "cars": ["машин", "авто", "гонк", "формула-1", "f1", "мотор", "bmw", "mercedes"],
}


class InterestClassifier:
    def __init__(self, model_path: str | Path | None = None):
        self.model_path = Path(model_path) if model_path else None
        self.bundle = None
        if self.model_path and self.model_path.exists():
            self.bundle = joblib.load(self.model_path)

    def predict(self, text: str, selected: Iterable[str] | None = None, threshold: float = 0.34) -> list[dict]:
        text = (text or "").strip()
        selected = list(selected or [])
        scores = {label: 0.0 for label in INTEREST_LABELS}

        if self.bundle is not None and text:
            vectorizer = self.bundle["vectorizer"]
            classifier = self.bundle["classifier"]
            mlb = self.bundle["mlb"]
            X = vectorizer.transform([text])
            probs = classifier.predict_proba(X)[0]
            for label, prob in zip(mlb.classes_, probs):
                scores[label] = float(prob)
        elif text:
            lowered = text.lower()
            for label, words in KEYWORDS.items():
                hits = sum(1 for word in words if word in lowered)
                scores[label] = min(0.95, hits * 0.35)

        for label in selected:
            if label in scores:
                scores[label] = max(scores[label], 0.92)

        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        result = [{"name": label, "score": round(score, 3)} for label, score in ranked if score >= threshold]
        if not result and ranked:
            result = [{"name": ranked[0][0], "score": round(ranked[0][1], 3)}]
        return result[:5]
