import json
import os
from unittest.mock import patch
import io
import threading
import unittest
from http.server import ThreadingHTTPServer
from urllib.request import Request, urlopen

from agent import DemoAgent, StoryAgent, safe_hints
from app import ENTRY, Handler, LESSONS, TERMS, grade, questions
from baseline_terms import TermModel
from interests import InterestModel


class CourseTests(unittest.TestCase):
    def test_course_and_entry(self):
        self.assertEqual(len(ENTRY), 5)
        self.assertEqual(len(LESSONS), 10)
        from terms import DICTIONARY
        self.assertTrue(all(t in DICTIONARY for lesson in LESSONS[:3] for t in lesson['terms']))
        self.assertTrue(set(DICTIONARY).issubset({t for lesson in LESSONS for t in lesson['terms']}))
        for number in range(1, 11):
            self.assertEqual(len(questions(number)), 3)
            self.assertEqual(len(LESSONS[number-1]['terms']), 1)
            self.assertTrue(all(term in TERMS for term in LESSONS[number-1]['terms']))
        for number in (3, 6, 9):
            self.assertEqual(len(questions(number, True)), 7)
        self.assertEqual(grade(1, [q['correct'] for q in questions(1)])['correct'], 3)

    def test_interests_and_grounded_baseline(self):
        scores = InterestModel().weights('Люблю гонки Formula1 Ferrari и музеи Пикассо')
        self.assertIn('cars', scores)
        self.assertIn('art', scores)
        story = 'Мира получила 2000 рублей за монтаж. Она составила бюджет на месяц.'
        text = TermModel().explain('бюджет', 'План доходов и расходов', story,
                                   ['Мира', 'бюджет', 'месяц'])
        self.assertIn('Мира получила 2000 рублей за монтаж. Она составила бюджет на месяц.', text)
        self.assertNotIn('футбол', text)
        self.assertEqual(safe_hints(story, ['бюджет'], [
            {'term': 'бюджет', 'keywords': ['Мира; футбол']}])['бюджет'],
            ['Она составила бюджет на месяц.'])

    def test_demo_story_through_course(self):
        hero = None
        for lesson in LESSONS:
            definitions = [{'term': t, 'definition': TERMS[t]} for t in lesson['terms']]
            result = DemoAgent().write(lesson, 'Люблю музыку', {'music': 1}, definitions,
                                       character=hero)
            hero = result['character']
            self.assertEqual(set(result['hints']), set(lesson['terms']))
            self.assertGreater(len(result['story']), 120)
            for term in lesson['terms']:
                self.assertTrue(TermModel().explain(term, TERMS[term],
                                                    result['story'], result['hints'][term]))

    def test_yandex_contract_without_network(self):
        agent = StoryAgent()
        agent.key, agent.folder = 'test-key', 'test-folder'
        calls = []
        story = 'Мира получила 2000 рублей за монтаж. Она записала их и расходы на студию в бюджет. На микрофон денег не хватило, и Мира отложила его покупку.'
        def fake_ask(task, schema):
            calls.append((task, schema))
            return {'story': story, 'takeaway': 'Сначала посчитай доходы и расходы.',
                    'character': {'name': 'Мира', 'age': 17, 'personality': 'творческая'},
                    'hints': [{'term': 'бюджет', 'keywords': ['Мира', 'студию', 'футбол']} ]}
        agent.ask = fake_ask
        lesson = LESSONS[0]
        result = agent.write(lesson, 'Люблю музыку', {'music': 1},
                             [{'term': 'бюджет', 'definition': TERMS['бюджет']}])
        self.assertEqual(calls[0][0]['interest_weights'], {'music': 1})
        self.assertNotIn('футбол', result['hints']['бюджет'])
        self.assertEqual(result['source'], 'yandex')

    def test_yandex_request_format(self):
        class Reply(io.BytesIO):
            def __enter__(self):
                return self
            def __exit__(self, *args):
                self.close()
        calls = []
        def opener(req, timeout):
            calls.append((req.full_url, dict(req.header_items()),
                          json.loads(req.data), timeout))
            text = json.dumps({'story': 'Мира записала расходы в бюджет.'})
            return Reply(json.dumps({'output': [{'content': [
                {'type': 'output_text', 'text': text}]}]}).encode())
        agent = StoryAgent(opener=opener)
        agent.key, agent.folder = 'fake', 'folder123'
        result = agent.ask({'lesson': 'Бюджет'}, {'type': 'object'})
        self.assertIn('/v1/responses', calls[0][0])
        self.assertEqual(calls[0][2]['model'], 'gpt://folder123/' + agent.model)
        self.assertEqual(result['story'], 'Мира записала расходы в бюджет.')


class HttpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mode = patch.dict(os.environ, {'FINSTORY_DEMO':'1'})
        cls.mode.start()
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = f'http://127.0.0.1:{cls.server.server_address[1]}'

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)
        cls.mode.stop()

    def post(self, route, body):
        req = Request(self.base+route, json.dumps(body).encode(),
                      {'Content-Type': 'application/json'})
        with urlopen(req, timeout=5) as response:
            return json.load(response)

    def test_browser_api_flow(self):
        with urlopen(self.base, timeout=5) as response:
            page = response.read().decode()
            self.assertIn('FinStory', page)
            self.assertIn('function welcome()', page)
            self.assertIn('entryResult(result.score)', page)
        for name in ('logo', 'mascot'):
            with urlopen(self.base+'/assets/'+name+'.png', timeout=5) as response:
                self.assertEqual(response.headers['Content-Type'], 'image/png')
                self.assertGreater(len(response.read()), 1000)
        with urlopen(self.base+'/api/entry', timeout=5) as response:
            self.assertEqual(len(json.load(response)), 5)
        self.assertEqual(self.post('/api/entry-grade', {'answers': [0, 0, 0, 0, 0]})['score'],
                         sum(q['correct'] == 0 for q in ENTRY))
        self.assertIn('cars', self.post('/api/interest', {'answer': 'Люблю Ferrari и гонки'})['weights'])
        story = self.post('/api/lesson', {'number': 1, 'answer': 'Люблю музыку'})
        self.assertEqual(len(story['terms']), 1)
        self.assertTrue(all(t['definition'] and t['example'] in story['story']
                            for t in story['terms']))
        self.assertTrue(story['character']['name'])
        self.assertEqual(len(self.post('/api/questions', {'number': 3, 'checkpoint': True})), 7)


if __name__ == '__main__':
    unittest.main()
