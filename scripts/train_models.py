import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

import joblib
from sklearn.feature_extraction import DictVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.plan_model import features as plan_features
from src.plan_catalog import STYLES
from src.scenes import SCENES
from src.term_model import features as term_features
from src.terms import APPLICATIONS


def split_group(index):
    return 'test' if (index * 17 + 11) % 5 == 0 else 'train'


def build_rows():
    plans, terms = [], []
    for lesson in range(1, 13):
        for interest_index, interest in enumerate(SCENES):
            group = (lesson - 1) * len(SCENES) + interest_index
            style = list(STYLES)[(lesson + interest_index) % len(STYLES)]
            for candidate_interest in SCENES:
                for candidate_style in STYLES:
                    label = int(interest == candidate_interest and style == candidate_style)
                    plans.append({'group': group, 'split': split_group(group), 'label': label,
                                  'query': {'lesson': lesson, 'interest': interest, 'style': style},
                                  'candidate': {'interest': candidate_interest, 'style': candidate_style},
                                  'features': plan_features(lesson, interest, style, candidate_interest, candidate_style)})
    for term_index, term in enumerate(APPLICATIONS):
        for interest_index, interest in enumerate(SCENES):
            group = term_index * len(SCENES) + interest_index
            for candidate_interest in SCENES:
                for kind in ('contextual', 'generic'):
                    label = int(interest == candidate_interest and kind == 'contextual')
                    terms.append({'group': group, 'split': split_group(group), 'label': label,
                                  'query': {'term': term, 'interest': interest},
                                  'candidate': {'interest': candidate_interest, 'kind': kind},
                                  'features': term_features(term, interest, candidate_interest, kind)})
    return plans, terms


def fit_and_report(name, rows):
    train = [r for r in rows if r['split'] == 'train']
    test = [r for r in rows if r['split'] == 'test']
    model = make_pipeline(DictVectorizer(), LogisticRegression(max_iter=500, class_weight='balanced'))
    model.fit([r['features'] for r in train], [r['label'] for r in train])
    groups = defaultdict(list)
    for row in test:
        groups[row['group']].append(row)
    correct = 0
    for group_rows in groups.values():
        probabilities = model.predict_proba([r['features'] for r in group_rows])[:, 1]
        chosen = group_rows[int(probabilities.argmax())]
        correct += chosen['label']
    joblib.dump(model, ROOT / 'models' / f'{name}.joblib')
    return {'train_rows': len(train), 'test_rows': len(test), 'test_queries': len(groups),
            'top1_rule_label_agreement': round(correct / len(groups), 3),
            'baseline_random_top1': round(1 / len(groups[next(iter(groups))]), 3),
            'label_source': 'author-defined compatibility rules; no human quality judgments'}


def main():
    plans, terms = build_rows()
    for name, rows in [('plot_ranker', plans), ('term_ranker', terms)]:
        path = ROOT / 'data' / f'{name}_labeled.jsonl'
        with path.open('w', encoding='utf-8') as stream:
            for row in rows:
                stream.write(json.dumps(row, ensure_ascii=False) + '\n')
    report = {'plot_ranker': fit_and_report('plot_ranker', plans),
              'term_ranker': fit_and_report('term_ranker', terms)}
    (ROOT / 'evaluation' / 'model_report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
