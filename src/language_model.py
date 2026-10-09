import json
import os
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen


class LanguageModel:
    def __init__(self, root):
        self.key = os.getenv('YANDEX_API_KEY', '').strip()
        self.folder_id = os.getenv('YANDEX_FOLDER_ID', '').strip()
        self.model = os.getenv('FINSTORY_YANDEX_MODEL', 'aliceai-llm').strip()
        self.last_error = ''
        self.rules = (Path(root) / 'data' / 'story_contract.txt').read_text(encoding='utf-8')

    @property
    def available(self):
        return bool(self.key and self.folder_id)

    def write(self, lesson, character, interests, plan=None, previous_story='', terms=None):
        self.last_error = ''
        if not self.available:
            self.last_error = 'Не заданы YANDEX_API_KEY и YANDEX_FOLDER_ID.'
            return None
        schema = {
            'type': 'object',
            'properties': {'story': {'type': 'string'}, 'takeaway': {'type': 'string'}},
            'required': ['story', 'takeaway'], 'additionalProperties': False,
        }
        task = {
            'character': character, 'financial_products': [lesson['title']],
            'interests': interests[:3], 'chapter_number': lesson['lesson_id'],
            'total_chapters': 12, 'learning_goal': lesson['learning_goal'],
            'previous_chapter': previous_story[:500], 'terms': terms or [],
        }
        if plan:
            task.update({
                'interest_keywords': plan['interest_keywords'], 'story_plan': {
                    key: value for key, value in plan.items()
                    if key not in ('character', 'interest_keywords')
                },
            })
        payload = {
            'model': f'gpt://{self.folder_id}/{self.model}',
            'instructions': self.rules, 'temperature': 0.7,
            'max_output_tokens': 700,
            'input': json.dumps(task, ensure_ascii=False),
            'text': {'format': {'type': 'json_schema', 'name': 'story_chapter',
                                'strict': True, 'schema': schema}},
        }
        request = Request(
            'https://ai.api.cloud.yandex.net/v1/responses',
            json.dumps(payload, ensure_ascii=False).encode('utf-8'),
            {'Authorization': 'Api-Key ' + self.key, 'x-folder-id': self.folder_id,
             'Content-Type': 'application/json'},
        )
        try:
            with urlopen(request, timeout=45) as response:
                data = json.load(response)
            chunks = [part.get('text', '') for item in data.get('output', [])
                      for part in item.get('content', []) if part.get('type') == 'output_text']
            result = json.loads(''.join(chunks))
            return result if isinstance(result, dict) else None
        except HTTPError as exc:
            self.last_error = f'Yandex AI Studio вернул HTTP {exc.code}.'
            return None
        except (OSError, ValueError, KeyError, TypeError) as exc:
            self.last_error = f'Ошибка ответа Yandex AI Studio: {type(exc).__name__}.'
            return None
