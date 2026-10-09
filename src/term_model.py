from pathlib import Path

import joblib

from .scenes import SCENES, scene_for
from .terms import APPLICATIONS


def features(term, interest, candidate_interest, kind):
    return {
        'term': term, 'interest': interest, 'candidate_interest': candidate_interest,
        'kind': kind, 'interest_agrees': int(interest == candidate_interest),
        'concrete_example': int(kind == 'contextual'),
    }


def example(term, interest, kind):
    activity, income, cost, event = scene_for(interest)
    if kind == 'contextual':
        return APPLICATIONS[term].format(activity=activity, income=income, cost=cost, event=event)
    return f'Для события «{event}» стоит разобраться, как работает понятие «{term}».'


class TermSelector:
    def __init__(self, model_path):
        path = Path(model_path)
        self.model = joblib.load(path) if path.exists() else None

    def select(self, term, interest):
        choices = [(candidate, kind) for candidate in SCENES for kind in ('contextual', 'generic')]
        if self.model:
            scores = self.model.predict_proba(
                [features(term['term'].lower(), interest, candidate, kind) for candidate, kind in choices]
            )[:, 1]
            candidate, kind = choices[int(scores.argmax())]
            if candidate != interest or kind != 'contextual':
                candidate, kind = interest, 'contextual'
        else:
            candidate, kind = interest, 'contextual'
        return term['definition'].strip().rstrip('.') + '. ' + example(term['term'].lower(), candidate, kind)
