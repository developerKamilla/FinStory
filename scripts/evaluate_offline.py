import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.engine import FinStoryEngine
from src.scenes import SCENES


def main():
    engine = FinStoryEngine(ROOT)
    lessons = {}
    for chapter in range(1, 13):
        results = [engine.lesson({'interests': [{'name': interest}]}, chapter) for interest in SCENES]
        lessons[chapter] = {
            'max_characters': max(len(result['story']) for result in results),
            'different_stories': len({result['story'] for result in results}),
            'all_terms_differ_by_interest': all(
                len({result['terms'][index]['personalized'] for result in results}) == len(SCENES)
                for index in range(3)
            ),
        }
    report = {'note': 'Offline structure and diversity checks only; no reader ratings or live language-model calls.',
              'lessons': lessons}
    (ROOT / 'evaluation' / 'offline_report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print('12 lessons, 11 interests:', all(item['max_characters'] <= 500 and
                                       item['different_stories'] == 11 and
                                       item['all_terms_differ_by_interest']
                                       for item in lessons.values()))


if __name__ == '__main__':
    main()
