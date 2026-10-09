import unittest
from pathlib import Path

from src.engine import FinStoryEngine
from src.validation import valid_chapter


class ContentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = FinStoryEngine(Path(__file__).resolve().parents[1])

    def lesson(self, lesson_id, *interests):
        profile = {'interests': [{'name': name} for name in interests], 'knowledge_level': 'beginner'}
        return self.engine.lesson(profile, lesson_id)

    def test_fixed_curriculum_and_short_chapters(self):
        for lesson_id in range(1, 13):
            result = self.lesson(lesson_id, 'sport')
            self.assertEqual(result['lesson']['lesson_id'], lesson_id)
            self.assertLessEqual(len(result['story']), 500)
            self.assertTrue(result['takeaway'])

    def test_interest_changes_plot_and_all_terms(self):
        for lesson_id in range(1, 13):
            sport = self.lesson(lesson_id, 'sport')
            music = self.lesson(lesson_id, 'music')
            self.assertNotEqual(sport['story'], music['story'])
            self.assertNotEqual(sport['plan']['setting'], music['plan']['setting'])
            for left, right in zip(sport['terms'], music['terms']):
                self.assertNotEqual(left['personalized'], right['personalized'])
                definition = self.engine.terms[left['term'].lower()]['definition']
                self.assertIn(definition, left['personalized'])
                self.assertIn(definition, right['personalized'])

    def test_mixed_interest_and_stable_character(self):
        first = self.lesson(1, 'gaming', 'science')
        second = self.lesson(2, 'gaming', 'science')
        self.assertEqual(first['character']['id'], second['character']['id'])
        self.assertEqual([x['interest'] for x in first['terms']], ['gaming', 'science', 'gaming'])

    def test_rejects_invented_number_and_long_story(self):
        result = self.lesson(4, 'sport')
        generated = {'story': result['story'].replace('1 000 ₽', '1 500 ₽'), 'takeaway': result['takeaway']}
        self.assertFalse(valid_chapter(generated, result['lesson'], result['character'], result['story']))
        generated['story'] = result['story'] * 3
        self.assertFalse(valid_chapter(generated, result['lesson'], result['character'], result['story']))

    def test_models_loaded(self):
        self.assertIsNotNone(self.engine.generator.planner.model)
        self.assertIsNotNone(self.engine.generator.term_selector.model)

    def test_generated_chapter_is_accepted_when_valid(self):
        writer = self.engine.generator.language_model
        original = writer.write
        try:
            sample = self.lesson(1, 'sport')
            revised = sample['story'].replace('Вечером выяснилось', 'К вечеру выяснилось')
            writer.write = lambda *args, **kwargs: {'story': revised, 'takeaway': sample['takeaway']}
            result = self.lesson(1, 'sport')
            self.assertEqual(result['generation']['mode'], 'генерация по плану')
            self.assertEqual(result['story'], revised)
        finally:
            writer.write = original


if __name__ == '__main__':
    unittest.main()
