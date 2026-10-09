import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.characters import choose_character
from src.engine import FinStoryEngine
from src.plots import PLOTS
from src.scenes import scene_for

PROFILES = [('sport', 'music'), ('music', 'sport'), ('gaming', 'science'),
            ('science', 'books'), ('art', 'business'), ('travel', 'tech')]


def main():
    engine = FinStoryEngine(ROOT)
    rows = []
    for index, (interest, second) in enumerate(PROFILES, 1):
        chapter = (1, 3, 5, 7, 9, 11)[index - 1]
        character = choose_character(engine.characters, interest, 1)
        scene = scene_for(interest)
        template = '\n\n'.join(
            PLOTS[number].format(name=character['name'], income=scene[1], cost=scene[2], event=scene[3])
            for number in (chapter, chapter + 1)
        )
        for mode in ('template', 'skill_only', 'hybrid'):
            rows.append({'case_id': index, 'lesson_pair': f'{chapter}-{chapter+1}',
                         'interests': f'{interest}, {second}', 'mode': mode,
                         'story': template if mode == 'template' else '', 'takeaway': '',
                         'rater_id': '', 'interest_fit_1_5': '', 'financial_accuracy_1_5': '',
                         'continuity_1_5': '', 'want_to_continue_1_5': '', 'notes': ''})
    path = ROOT / 'evaluation' / 'manual_review_blank.csv'
    with path.open('w', encoding='utf-8-sig', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    print(path)


if __name__ == '__main__':
    main()
