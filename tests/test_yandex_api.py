import io
import json
import unittest
from pathlib import Path
from unittest.mock import patch

from src.language_model import LanguageModel


class YandexApiTests(unittest.TestCase):
    def test_request_contains_plan_and_uses_yandex_endpoint(self):
        class Reply(io.BytesIO):
            def __enter__(self):
                return self

            def __exit__(self, *args):
                self.close()

        captured = {}

        def fake_urlopen(request, timeout):
            captured['request'] = request
            captured['timeout'] = timeout
            response = {'output': [{'content': [{'type': 'output_text', 'text':
                json.dumps({'story': 'История', 'takeaway': 'Вывод'})}]}]}
            return Reply(json.dumps(response).encode('utf-8'))

        root = Path(__file__).resolve().parents[1]
        with patch.dict('os.environ', {'YANDEX_API_KEY': 'test-secret',
                                      'YANDEX_FOLDER_ID': 'test-folder'}):
            model = LanguageModel(root)
        with patch('src.language_model.urlopen', side_effect=fake_urlopen):
            result = model.write({'lesson_id': 3, 'title': 'Счёт', 'learning_goal': 'Срок'},
                                 {'name': 'Маша'}, ['sport'],
                                 {'interest_keywords': ['мяч'],
                                  'verified_facts': '12% годовых'}, 'Предыдущая глава',
                                 [{'term': 'процент', 'personalized': 'Пример'}])
        request = captured['request']
        body = json.loads(request.data)
        task = json.loads(body['input'])
        self.assertEqual(request.full_url, 'https://ai.api.cloud.yandex.net/v1/responses')
        self.assertEqual(request.get_header('Authorization'), 'Api-Key test-secret')
        self.assertEqual(body['model'], 'gpt://test-folder/aliceai-llm')
        self.assertEqual(task['story_plan']['verified_facts'], '12% годовых')
        self.assertEqual(task['previous_chapter'], 'Предыдущая глава')
        self.assertEqual(task['terms'][0]['personalized'], 'Пример')
        self.assertEqual(result['story'], 'История')


if __name__ == '__main__':
    unittest.main()
