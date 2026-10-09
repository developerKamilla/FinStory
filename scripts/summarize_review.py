import csv
import statistics
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KEYS = ('interest_fit_1_5', 'financial_accuracy_1_5', 'continuity_1_5', 'want_to_continue_1_5')


def main():
    with (ROOT / 'evaluation' / 'answer_key.csv').open(encoding='utf-8-sig', newline='') as stream:
        lookup = {(r['case_id'], r['variant']): r['mode'] for r in csv.DictReader(stream)}
    with (ROOT / 'evaluation' / 'blind_review.csv').open(encoding='utf-8-sig', newline='') as stream:
        reviews = list(csv.DictReader(stream))
    scores = defaultdict(lambda: defaultdict(list))
    raters = set()
    for row in reviews:
        if not row['rater_id']:
            continue
        raters.add(row['rater_id'])
        mode = lookup[row['case_id'], row['variant']]
        for metric in KEYS:
            score = int(row[metric])
            if score not in range(1, 6):
                raise ValueError(f'Оценка вне диапазона 1–5: {metric}')
            scores[mode][metric].append(score)
    if len(raters) < 2:
        raise SystemExit('Нужны оценки как минимум двух независимых участников; итогов пока нет.')
    for mode in ('template', 'skill_only', 'hybrid'):
        print(mode, ' '.join(f'{metric}={statistics.mean(scores[mode][metric]):.2f}' for metric in KEYS))


if __name__ == '__main__':
    main()
