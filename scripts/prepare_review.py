import argparse
import csv
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.engine import FinStoryEngine
from src.plots import PLOTS
from src.characters import choose_character
from src.scenes import scene_for

PROFILES = [
    ('sport', 'music'), ('music', 'sport'), ('gaming', 'science'),
    ('science', 'books'), ('art', 'business'), ('travel', 'tech'),
]
LESSONS = (1, 3, 5, 7, 9, 11)


def build(engine, interest, secondary, first_chapter):
    profile = {'interests': [{'name': interest}, {'name': secondary}], 'knowledge_level': 'beginner'}
    character = choose_character(engine.characters, interest, 1)
    outputs = {name: [] for name in ('template', 'skill_only', 'hybrid')}
    previous_skill = previous_hybrid = ''
    for chapter in (first_chapter, first_chapter + 1):
        lesson = engine.lessons[chapter - 1]
        scene = scene_for(interest)
        old = PLOTS[chapter].format(name=character['name'], income=scene[1], cost=scene[2], event=scene[3])
        skill = engine.generator.language_model.write(lesson, character, [interest, secondary],
                                                     previous_story=previous_skill)
        hybrid = engine.lesson(profile, chapter, previous_story=previous_hybrid)
        if not skill or hybrid['generation']['mode'] != 'генерация по плану':
            return None
        previous_skill, previous_hybrid = skill['story'], hybrid['story']
        outputs['template'].append((old, ''))
        outputs['skill_only'].append((skill['story'], skill['takeaway']))
        outputs['hybrid'].append((hybrid['story'], hybrid['takeaway']))
    return {mode: {'story': '\n\n'.join(f'Глава {first_chapter + index}: {story}'
                                    for index, (story, _) in enumerate(chapters)),
                   'takeaway': ' / '.join(takeaway for _, takeaway in chapters if takeaway)}
            for mode, chapters in outputs.items()}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--cases', type=int, default=6)
    args = parser.parse_args()
    engine = FinStoryEngine(ROOT)
    if not engine.generator.language_model.available:
        raise SystemExit('Нужны YANDEX_API_KEY и YANDEX_FOLDER_ID для сравнения с агентом.')
    pairs = [(a, b, lesson) for a, b in PROFILES for lesson in LESSONS][:args.cases]
    random.Random(42).shuffle(pairs)
    reviews, answer_key = [], []
    for number, (interest, secondary, chapter) in enumerate(pairs, 1):
        variants = build(engine, interest, secondary, chapter)
        if variants is None:
            raise SystemExit(f'Глава {chapter}, случай {number}: генерация не удалась. Данные неполные; оценка не создана.')
        labels = list(variants)
        random.Random(number + 42).shuffle(labels)
        for letter, mode in zip('ABC', labels):
            item = variants[mode]
            reviews.append({
                'case_id': number, 'variant': letter, 'interest': interest,
                'lesson_id': f'{chapter}-{chapter+1}', 'story': item['story'], 'takeaway': item.get('takeaway', ''),
                'rater_id': '', 'interest_fit_1_5': '', 'financial_accuracy_1_5': '',
                'continuity_1_5': '', 'want_to_continue_1_5': '', 'notes': '',
            })
            answer_key.append({'case_id': number, 'variant': letter, 'mode': mode})
    for name, rows in [('blind_review.csv', reviews), ('answer_key.csv', answer_key)]:
        with (ROOT / 'evaluation' / name).open('w', encoding='utf-8-sig', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)
    print(f'{len(pairs)} случаев, {len(reviews)} текстов. Попросите минимум двух человек оценить все строки независимо.')


if __name__ == '__main__':
    main()
