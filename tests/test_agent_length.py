import unittest
from agent import StoryAgent


class LengthTests(unittest.TestCase):
    def run_case(self, results):
        agent = StoryAgent()
        agent.key, agent.folder = 'test', 'test'
        calls = []
        def ask(task, schema):
            calls.append(dict(task))
            return results[min(len(calls) - 1, len(results) - 1)]
        agent.ask = ask
        lesson = {'title': 'Карта', 'learning_goal': 'Оплата своими деньгами'}
        return agent, calls, lesson

    def result(self, n=400, takeaway='Проверь деньги на счёте.'):
        return {'story': 'Мира ' + 'а' * (n - 6) + '.', 'takeaway': takeaway,
                'character': {'name': 'Мира', 'age': 17, 'personality': 'внимательная'},
                'hints': []}

    def test_short_and_long_story_corrected_automatically(self):
        for n in (40, 900):
            with self.subTest(length=n):
                good = self.result()
                agent, calls, lesson = self.run_case([self.result(n), good])
                output = agent.write(lesson, 'Рисую', {'art': 1}, [])
                self.assertEqual(output['story'], good['story'])
                self.assertEqual(len(calls), 2)
                self.assertIn('revision', calls[1])
                self.assertNotIn('revision', calls[0])

    def test_long_takeaway_corrected(self):
        agent, calls, lesson = self.run_case([self.result(takeaway='а' * 400), self.result()])
        self.assertLess(len(agent.write(lesson, 'Рисую', {}, [])['takeaway']), 350)
        self.assertEqual(len(calls), 2)

    def test_retry_limit(self):
        agent, calls, lesson = self.run_case([self.result(900)])
        with self.assertRaisesRegex(RuntimeError, 'трёх попыток'):
            agent.write(lesson, 'Рисую', {}, [])
        self.assertEqual(len(calls), 3)

    def test_valid_result_has_no_extra_request(self):
        agent, calls, lesson = self.run_case([self.result()])
        agent.write(lesson, 'Рисую', {}, [])
        self.assertEqual(len(calls), 1)
