import json
import os
import re
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent


def load_env():
    path = ROOT / '.env'
    if not path.is_file():
        return
    for line in path.read_text(encoding='utf-8-sig').splitlines():
        if '=' not in line or line.lstrip().startswith('#'):
            continue
        name, value = line.split('=', 1)
        if name.strip() in ('YANDEX_API_KEY', 'YANDEX_FOLDER_ID', 'FINSTORY_YANDEX_MODEL'):
            os.environ[name.strip()] = value.strip().strip('"\'')


def safe_hints(story, terms, raw):
    found = {item.get('term'): item.get('keywords', []) for item in raw
             if isinstance(item, dict)} if isinstance(raw, list) else {}
    tokens = set(re.findall(r'[а-яёa-z0-9]+', story.casefold()))
    hints = {}
    for term in terms:
        result = []
        phrases = found.get(term, [])
        for phrase in phrases if isinstance(phrases, list) else []:
            if not isinstance(phrase, str) or len(phrase) > 100:
                continue
            words = re.findall(r'[а-яёa-z0-9]+', phrase.casefold())
            need = [word for word in words if len(word) > 2 or word.isdigit()]
            if need and all(word in tokens for word in need):
                result.append(phrase.strip())
        if not result:
            parts = [x.strip() for x in re.split(r'(?<=[.!?])\s+', story) if x.strip()]
            match = [s for s in parts if term.casefold() in s.casefold()]
            result = (match or parts)[:1]
        hints[term] = result[:6]
    return hints


class StoryAgent:
    def __init__(self, opener=urlopen):
        load_env()
        self.key = os.getenv('YANDEX_API_KEY', '')
        self.folder = os.getenv('YANDEX_FOLDER_ID', '')
        self.model = os.getenv('FINSTORY_YANDEX_MODEL', 'aliceai-llm')
        self.opener = opener

    @property
    def configured(self):
        return bool(self.key and self.folder)

    def ask(self, task, schema):
        payload = {
            'model': self.model if self.model.startswith('gpt://') else f'gpt://{self.folder}/{self.model}',
            'instructions': (
                'Пиши связную реалистичную историю финансового выбора для 14–22 лет. '
                'Интересы пользователя влияют на детали истории. Сохраняй героя и прошлые события, '
                'если они даны. Глава 350–500 знаков, с целью, ограничением, выбором и последствием. '
                'Финансовые понятия вплетай в сюжет естественно. Не выдумывай проверяемые сведения '
                'о реальных людях. Для каждого термина верни несколько ключевых фактов, которые '
                'ПРЯМО написаны в созданной главе. Не объясняй термины: их объяснит отдельная модель. '
                'Сначала проверь последовательность событий, предметы покупок, имена, род и финансовый смысл. '
                'Не выводи свои рассуждения. Возвращай только JSON.'),
            'input': json.dumps(task, ensure_ascii=False),
            'temperature': 0.5,
            'max_output_tokens': 1100,
            'text': {'format': {'type': 'json_schema', 'name': 'finstory_chapter',
                                'strict': True, 'schema': schema}},
        }
        request = Request('https://ai.api.cloud.yandex.net/v1/responses',
                          data=json.dumps(payload, ensure_ascii=False).encode('utf-8'),
                          headers={'Authorization': 'Api-Key ' + self.key,
                                   'x-folder-id': self.folder,
                                   'Content-Type': 'application/json'})
        with self.opener(request, timeout=60) as response:
            data = json.load(response)
        output = ''.join(part.get('text', '') for item in data.get('output', [])
                         for part in item.get('content', [])
                         if part.get('type') == 'output_text')
        if not output:
            raise ValueError('Пустой ответ генерации')
        return json.loads(output)

    def write(self, lesson, answer, weights, definitions, previous_story='', character=None):
        if not self.configured:
            raise ValueError('Не заполнены YANDEX_API_KEY и YANDEX_FOLDER_ID в .env')
        term_names = [item['term'] for item in definitions]
        schema = {'type': 'object', 'properties': {
            'story': {'type': 'string'}, 'takeaway': {'type': 'string'},
            'character': {'type': 'object', 'properties': {
                'name': {'type': 'string'}, 'age': {'type': 'integer'},
                'personality': {'type': 'string'}},
                'required': ['name', 'age', 'personality'], 'additionalProperties': False},
            'hints': {'type': 'array', 'items': {'type': 'object', 'properties': {
                'term': {'type': 'string', 'enum': term_names},
                'keywords': {'type': 'array', 'items': {'type': 'string'}}},
                'required': ['term', 'keywords'], 'additionalProperties': False}}},
            'required': ['story', 'takeaway', 'character', 'hints'],
            'additionalProperties': False}
        task = {'lesson': lesson['title'], 'learning_goal': lesson['learning_goal'],
                'terms': definitions, 'fixed_facts':lesson.get('fixed_facts',[]),
                'scenario':lesson.get('scenario',{}), 'user_answer': answer[:800],
                'interest_weights': weights, 'previous_story': previous_story[:650],
                'character': character}
        for attempt in range(3):
            result = self.ask(task, schema)
            story = result['story'].strip()
            takeaway = result['takeaway'].strip()
            hero = result['character']
            issues = []
            if not 120 <= len(story) <= 650:
                issues.append(f"Длина главы {len(story)} знаков. Перепиши её в пределах 350–500 знаков.")
            if len(takeaway) > 350:
                issues.append(f"Длина микровывода {len(takeaway)} знаков. Сократи его до 80–180 знаков.")
            if not issues:
                break
            print(f'Chapter length correction {attempt + 1}/3: story={len(story)}, takeaway={len(takeaway)}', flush=True)
            if attempt == 2:
                raise RuntimeError('Агент не смог выдержать длину главы после трёх попыток. Попробуй открыть урок позже.')
            task['revision'] = {
                'issues': issues,
                'previous_result': result,
                'instruction': 'Исправь длину без обрыва предложений. Сохрани финансовый смысл, интересы пользователя и героя. Верни полный JSON с актуальными фактами из исправленной главы.'}
        if character and hero != character:
            raise ValueError('Герой изменился между уроками')
        if type(hero['age']) is not int or not hero['name'].strip():
            raise ValueError('Некорректный герой')
        return {'story': story, 'takeaway': takeaway,
                'character': hero, 'hints': safe_hints(story, term_names, result['hints']),
                'source': 'yandex'}


class DemoAgent:
    def write(self, lesson, answer, weights, definitions, previous_story='', character=None):
        stories = json.loads((ROOT / 'data' / 'demo_stories.json').read_text(encoding='utf-8'))
        story = stories[lesson['lesson_id'] - 1]
        hero = character or {'name': 'Мира', 'age': 17, 'personality': 'внимательная'}
        hints = safe_hints(story, [d['term'] for d in definitions], [])
        return {'story': story, 'takeaway': lesson['learning_goal'] + '.',
                'character': hero, 'hints': hints, 'source': 'demo'}
