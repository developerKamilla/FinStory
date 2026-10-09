from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class KnowledgeQuestion:
    id: int
    text: str
    options: list[str]
    correct_index: int


KNOWLEDGE_QUESTIONS = [
    KnowledgeQuestion(
        5,
        "На счёте лежит 10 000 ₽ под 10% годовых. Примерно сколько процентов начислится за год?",
        ["100 ₽", "1 000 ₽", "10 000 ₽", "11 000 ₽"],
        1,
    ),
    KnowledgeQuestion(
        6,
        "Что обычно происходит с покупательной способностью денег при инфляции?",
        ["Растёт", "Не меняется", "Снижается", "Всегда удваивается"],
        2,
    ),
    KnowledgeQuestion(
        7,
        "Что такое акция?",
        [
            "Доля в компании",
            "Банковский вклад",
            "Страховой полис",
            "Фиксированный налог",
        ],
        0,
    ),
    KnowledgeQuestion(
        8,
        "Что лучше всего описывает диверсификацию?",
        [
            "Хранить все деньги наличными",
            "Распределять деньги между разными активами",
            "Покупать только одну знакомую акцию",
            "Брать больше кредитов",
        ],
        1,
    ),
    KnowledgeQuestion(
        9,
        "Если ставка по кредиту выше, то при прочих равных переплата обычно…",
        ["Ниже", "Выше", "Всегда нулевая", "Не связана со ставкой"],
        1,
    ),
    KnowledgeQuestion(
        10,
        "Сложный процент означает, что проценты могут начисляться…",
        [
            "Только на первоначальную сумму",
            "На первоначальную сумму и ранее начисленные проценты",
            "Только один раз",
            "Только при снятии денег",
        ],
        1,
    ),
]


def score_knowledge(answer_indexes: Iterable[int | None]) -> tuple[int, str]:
    answers = list(answer_indexes)
    score = 0
    for question, answer in zip(KNOWLEDGE_QUESTIONS, answers):
        if answer is not None and int(answer) == question.correct_index:
            score += 1

    if score <= 2:
        level = "beginner"
    elif score <= 4:
        level = "basic"
    else:
        level = "intermediate"
    return score, level
