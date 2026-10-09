from __future__ import annotations

from .classifier import InterestClassifier
from .quiz import score_knowledge


def build_user_profile(
    classifier: InterestClassifier,
    selected_interests: list[str],
    free_text_answers: list[str],
    knowledge_answers: list[int | None],
) -> dict:
    text = " ".join(x.strip() for x in free_text_answers if x and x.strip())
    interests = classifier.predict(text, selected_interests)
    score, level = score_knowledge(knowledge_answers)
    return {
        "interests": interests,
        "knowledge_score": score,
        "knowledge_level": level,
        "completed_lessons": [],
    }
