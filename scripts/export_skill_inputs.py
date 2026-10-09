import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.engine import FinStoryEngine
from src.characters import choose_character

PROFILES = [('sport', 'music'), ('music', 'sport'), ('gaming', 'science'),
            ('science', 'books'), ('art', 'business'), ('travel', 'tech')]


def main():
    engine = FinStoryEngine(ROOT)
    output = ROOT / 'evaluation' / 'chatgpt_skill_tasks.jsonl'
    with output.open('w', encoding='utf-8') as stream:
        for number, (interest, second) in enumerate(PROFILES, 1):
            character = choose_character(engine.characters, interest, 1)
            plans = [engine.generator.planner.choose(lesson, character, interest) for lesson in engine.lessons]
            for mode in ('skill_only', 'hybrid'):
                task = {
                    'case_id': number, 'mode': mode,
                    'character': character, 'interests': [interest, second],
                    'financial_products': [lesson['title'] for lesson in engine.lessons],
                    'chapter_count': 12,
                }
                if mode == 'hybrid':
                    task['chapter_plans'] = [{key: value for key, value in plan.items() if key != 'character'} for plan in plans]
                stream.write(json.dumps(task, ensure_ascii=False) + '\n')
    print(output)


if __name__ == '__main__':
    main()
