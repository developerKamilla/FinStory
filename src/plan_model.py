from pathlib import Path

import joblib

from .plan_catalog import CHAPTERS, STYLES, character_style
from .scenes import SCENES


def features(lesson_id, interest, style, candidate_interest, candidate_style):
    return {
        'lesson': str(lesson_id), 'interest': interest, 'style': style,
        'candidate_interest': candidate_interest, 'candidate_style': candidate_style,
        'interest_agrees': int(interest == candidate_interest),
        'style_agrees': int(style == candidate_style),
    }


class PlotPlanner:
    def __init__(self, model_path):
        path = Path(model_path)
        self.model = joblib.load(path) if path.exists() else None

    def choose(self, lesson, character, interest):
        chapter = int(lesson['lesson_id'])
        style = character_style(character)
        candidates = [(i, s) for i in SCENES for s in STYLES]
        if self.model:
            probabilities = self.model.predict_proba(
                [features(chapter, interest, style, i, s) for i, s in candidates]
            )[:, 1]
            selected = candidates[int(probabilities.argmax())]
            if selected != (interest, style):
                selected = (interest, style)
        else:
            selected = (interest, style)
        setting = SCENES[selected[0]]
        problem, decision, hook, facts = CHAPTERS[chapter]
        return {
            'lesson_id': chapter, 'character': character, 'interest': interest,
            'interest_keywords': [setting[2], setting[3]],
            'setting': setting[0], 'goal': setting[3],
            'problem': problem, 'character_action': STYLES[selected[1]],
            'financial_decision': decision, 'next_hook': hook,
            'verified_facts': facts, 'product': lesson['title'],
        }
