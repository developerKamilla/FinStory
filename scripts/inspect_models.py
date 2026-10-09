import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.engine import FinStoryEngine
from src.plan_catalog import STYLES, character_style
from src.plan_model import features as plan_features
from src.scenes import SCENES
from src.term_model import features as term_features


def top_scores(model, candidates, make_features, count=3):
    probabilities = model.predict_proba([make_features(*item) for item in candidates])[:, 1]
    order = sorted(range(len(candidates)), key=lambda index: probabilities[index], reverse=True)
    return [(candidates[index], round(float(probabilities[index]), 3)) for index in order[:count]]


def main():
    parser = argparse.ArgumentParser(description='Показать решения моделей FinStory')
    parser.add_argument('--lesson', type=int, default=3, choices=range(1, 13))
    parser.add_argument('--interests', nargs='+', default=['sport', 'music'], choices=list(SCENES))
    parser.add_argument('--text', default='', help='Ответ пользователя о своих интересах')
    parser.add_argument('--with-llm', action='store_true', help='Запросить новую главу через API')
    args = parser.parse_args()

    engine = FinStoryEngine(ROOT)
    if not args.with_llm:
        engine.generator.language_model.key = ''
    predicted = engine.classifier.predict(args.text, args.interests)
    profile = {'interests': predicted, 'knowledge_level': 'beginner'}
    result = engine.lesson(profile, args.lesson)
    main_interest = result['main_interest']
    style = character_style(result['character'])
    print('Интересы по классификатору:', ', '.join(
        f"{entry['name']} ({entry['score']:.3f})" for entry in predicted
    ))
    print('Персонаж:', result['character']['name'], '| черта:', style)

    planner = engine.generator.planner.model
    candidates = [(interest, candidate_style) for interest in SCENES for candidate_style in STYLES]
    plan_ranking = top_scores(
        planner, candidates,
        lambda interest, candidate_style: plan_features(
            args.lesson, main_interest, style, interest, candidate_style
        ),
    )
    print('\nТри варианта плана с наибольшими оценками модели:')
    for candidate, score in plan_ranking:
        print(f'  {candidate[0]} / {candidate[1]}: {score:.3f}')
    print('Итоговый план:', result['plan']['setting'])
    print('Проблема:', result['plan']['problem'])
    print('Решение:', result['plan']['financial_decision'])

    selector = engine.generator.term_selector.model
    for card in result['terms']:
        candidates = [(interest, kind) for interest in SCENES for kind in ('contextual', 'generic')]
        ranking = top_scores(
            selector, candidates,
            lambda interest, kind: term_features(card['term'].lower(), card['interest'], interest, kind),
        )
        print(f"\nТермин: {card['term']} | интерес: {card['interest']}")
        print('Три оценки:', ', '.join(
            f'{candidate[0]}/{candidate[1]}={score:.3f}' for candidate, score in ranking
        ))
        print('Объяснение:', card['personalized'])

    print('\nИсточник истории:', result['generation']['mode'])
    if args.with_llm and engine.generator.language_model.last_error:
        print(engine.generator.language_model.last_error)
    print('Глава:', result['story'])
    print('Микровывод:', result['takeaway'])
    print('Знаков в главе:', len(result['story']))


if __name__ == '__main__':
    main()
