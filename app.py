import argparse
import csv
import hashlib
import json
import logging
import os
import threading
import time
from collections import deque
from contextlib import contextmanager, nullcontext
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from agent import DemoAgent, StoryAgent
from interests import InterestModel
from terms import TERMS_MODEL, DICTIONARY

ROOT = Path(__file__).resolve().parent
LESSONS = json.loads((ROOT / 'data' / 'lessons.json').read_text(encoding='utf-8'))
ENTRY = json.loads((ROOT / 'data' / 'entry_quiz.json').read_text(encoding='utf-8'))
with (ROOT / 'data' / 'finance_terms.csv').open(encoding='utf-8-sig', newline='') as source:
    TERMS = {row['term'].lower(): row['definition'] for row in csv.DictReader(source)}
TERMS.update(DICTIONARY)
LOG_LOCK = threading.Lock()
CACHE_LOCK = threading.Lock()
CACHE = {}
MAX_BODY_BYTES = 10_000
LOGGER = logging.getLogger(__name__)


class GenerationLimit(Exception):
    def __init__(self, retry_after):
        self.retry_after = retry_after


class GenerationGate:
    def __init__(self, daily_limit):
        if daily_limit < 1:
            raise ValueError('FINSTORY_DAILY_GENERATIONS должен быть больше нуля')
        self.daily_limit = daily_limit
        self.slots = threading.BoundedSemaphore(3)
        self.lock = threading.Lock()
        self.requests = deque()

    @contextmanager
    def admit(self, client):
        if not self.slots.acquire(blocking=False):
            raise GenerationLimit(10)
        try:
            with self.lock:
                now = time.monotonic()
                while self.requests and self.requests[0][0] <= now - 86_400:
                    self.requests.popleft()
                if len(self.requests) >= self.daily_limit:
                    raise GenerationLimit(int(self.requests[0][0] + 86_400 - now) + 1)
                recent = 0
                for timestamp, address in reversed(self.requests):
                    if timestamp <= now - 60:
                        break
                    if address == client:
                        recent += 1
                        if recent >= 12:
                            raise GenerationLimit(int(timestamp + 60 - now) + 1)
                self.requests.append((now, client))
            yield
        finally:
            self.slots.release()


def record_lesson(number, result, weights, definitions):
    path = ROOT / 'data' / 'generated.jsonl'
    event = {'time': time.time(), 'lesson': number, 'source': result['source'],
             'story': result['story'], 'hints': result['hints'], 'weights': weights,
             'terms': definitions}
    with LOG_LOCK, path.open('a', encoding='utf-8') as stream:
        stream.write(json.dumps(event, ensure_ascii=False) + '\n')


def create_lesson(data, admission=nullcontext):
    lesson = get_lesson(data.get('number'))
    answer = interest_answer(data)
    previous_story = data.get('previous_story', '')
    if not isinstance(previous_story, str):
        raise ValueError('Некорректная предыдущая история')
    previous_story = previous_story[:650]
    character = data.get('character')
    if character is not None:
        if not isinstance(character, dict) or set(character) != {'name', 'age', 'personality'}:
            raise ValueError('Некорректные данные персонажа')
        if (type(character['age']) is not int or not isinstance(character['name'], str)
                or not isinstance(character['personality'], str)):
            raise ValueError('Некорректные данные персонажа')
    demo = os.getenv('FINSTORY_DEMO') == '1'
    identity = (lesson['lesson_id'], answer, previous_story, character, demo)
    key = hashlib.sha256(json.dumps(identity, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
    with CACHE_LOCK:
        if key in CACHE:
            return CACHE[key]
    with admission():
        response = generate_lesson(lesson, answer, previous_story, character, demo)
        with CACHE_LOCK:
            if key not in CACHE and len(CACHE) >= 64:
                CACHE.pop(next(iter(CACHE)))
            CACHE[key] = response
    return response


def interest_answer(data):
    value = data.get('answer', '')
    if not isinstance(value, str):
        raise ValueError('Некорректный ответ об интересах')
    answer = value.strip()[:800]
    if not answer:
        raise ValueError('Напиши о своих интересах')
    return answer


def generate_lesson(lesson, answer, previous_story, character, demo):
    definitions = [{'term':name, 'definition':TERMS[name]} for name in lesson['terms']]
    weights = InterestModel().weights(answer)
    agent = DemoAgent() if demo else StoryAgent()
    if not demo and not agent.configured:
        raise RuntimeError('Нужны YANDEX_API_KEY и YANDEX_FOLDER_ID')
    try:
        result = agent.write(lesson, answer, weights, definitions, previous_story, character)
    except (ValueError, KeyError, TypeError, AttributeError, OSError) as exc:
        raise StoryProviderError from exc
    explanations = [TERMS_MODEL.explain(item['term'],item['definition'],result['story'],
                      result['hints'][item['term']],weights,demo=demo) for item in definitions]
    if os.getenv('FINSTORY_RECORD_LESSONS', '1') == '1':
        record_lesson(lesson['lesson_id'], result, weights, explanations)
    return {'story':result['story'],'takeaway':result['takeaway'],
            'character':result['character'], 'terms':[
                {k:v for k,v in item.items() if k not in ('source','raw')}
                for item in explanations]}


class StoryProviderError(Exception):
    pass


CHECK_TASKS = {
    6: ('Покупка стоила 1000 ₽, затем цена выросла на 10%. Какова новая цена?', ['1010 ₽', '1100 ₽', '900 ₽'], 1),
    9: ('Цена акции снизилась с 1000 ₽ до 800 ₽. Как изменится сумма от продажи одной акции без учёта комиссий?', ['Уменьшится на 200 ₽', 'Увеличится на 200 ₽', 'Не изменится'], 0),
    3: ('На счёте 1000 ₽. Оплатили покупку на 350 ₽. Сколько осталось?', ['350 ₽', '650 ₽', '1350 ₽'], 1),
}


def get_lesson(number):
    if type(number) is not int or number < 1 or number > len(LESSONS):
        raise ValueError('Нет такого урока')
    return LESSONS[number - 1]


def questions(number, checkpoint=False):
    if checkpoint:
        if number not in CHECK_TASKS:
            raise ValueError('Для этого урока нет повторения')
        result = []
        for n in range(number - 2, number + 1):
            result.extend(get_lesson(n)['questions'][:2])
        title, answers, correct = CHECK_TASKS[number]
        return result + [{'question': title, 'answers': answers, 'correct': correct}]
    return get_lesson(number)['questions']


def grade(number, answers, checkpoint=False):
    items = questions(number, checkpoint)
    if not isinstance(answers, list) or len(answers) != len(items) or any(
        type(answer) is not int or answer < 0 or answer >= len(item['answers'])
        for answer, item in zip(answers, items)
    ):
        raise ValueError('Ответь на все вопросы')
    return {'correct': sum(answer == item['correct'] for answer, item in zip(answers, items)),
            'total': len(items),
            'right_answers': [item['answers'][item['correct']] for item in items]}


def response(payload, content_type, status=HTTPStatus.OK, headers=()):
    return status, [
        ('Content-Type', content_type),
        ('Content-Length', str(len(payload))),
        *headers,
    ], payload


def json_response(data, status=HTTPStatus.OK, headers=()):
    payload = json.dumps(data, ensure_ascii=False).encode('utf-8')
    return response(payload, 'application/json; charset=utf-8', status,
                    [('Cache-Control', 'no-store'), *headers])


def get_response(path):
    if path == '/':
        return response((ROOT / 'index.html').read_bytes(), 'text/html; charset=utf-8')
    if path in ('/assets/logo.png', '/assets/mascot.png'):
        return response((ROOT / path.lstrip('/')).read_bytes(), 'image/png')
    if path == '/healthz':
        return json_response({'status': 'ok'})
    if path == '/api/entry':
        return json_response(public_questions(ENTRY))
    if path == '/api/lessons':
        return json_response([{'id': lesson['lesson_id'], 'title': lesson['title']} for lesson in LESSONS])
    if path == '/api/status':
        mode = 'demo' if os.getenv('FINSTORY_DEMO') == '1' else 'needs_env'
        if mode != 'demo' and StoryAgent().configured:
            mode = 'yandex'
        return json_response({'mode': mode, 'lessons': len(LESSONS), 'term_backend': TERMS_MODEL.backend,
                              'trained_terms': list(DICTIONARY), 'cache_version': 'course-ten-single-v2'})
    return json_response({'error': 'Страница не найдена.'}, HTTPStatus.NOT_FOUND)


def public_questions(items):
    return [{'question': item['question'], 'answers': item['answers']} for item in items]


def entry_grade(answers):
    if not isinstance(answers, list) or len(answers) != len(ENTRY) or any(
        type(value) is not int or not 0 <= value < len(item['answers'])
        for value, item in zip(answers, ENTRY)
    ):
        raise ValueError('Ответь на все пять вопросов')
    score = sum(value == item['correct'] for value, item in zip(answers, ENTRY))
    return {'score': score, 'level': 'начальный' if score < 3 else 'базовый'}


def post_response(path, data, admission):
    if path == '/api/entry-grade':
        return json_response(entry_grade(data.get('answers')))
    if path == '/api/interest':
        weights = InterestModel().weights(interest_answer(data))
        return json_response({'interest': next(iter(weights), 'other'), 'weights': weights})
    if path == '/api/lesson':
        return json_response(create_lesson(data, admission))
    if path in ('/api/questions', '/api/grade'):
        number = data.get('number')
        checkpoint = data.get('checkpoint', False)
        if type(checkpoint) is not bool:
            raise ValueError('Некорректный тип проверки')
        if path == '/api/questions':
            return json_response(public_questions(questions(number, checkpoint)))
        return json_response(grade(number, data.get('answers'), checkpoint))
    return json_response({'error': 'Страница не найдена.'}, HTTPStatus.NOT_FOUND)


def handle_request(method, path, content_length, body, admission=nullcontext):
    try:
        if method in ('GET', 'HEAD'):
            return get_response(path)
        if method != 'POST':
            return json_response({'error': 'Метод не поддерживается.'}, HTTPStatus.METHOD_NOT_ALLOWED,
                                 [('Allow', 'GET, HEAD, POST')])
        length = int(content_length or 0)
        if length > MAX_BODY_BYTES:
            return json_response({'error': 'Запрос слишком большой.'}, HTTPStatus.REQUEST_ENTITY_TOO_LARGE)
        if length < 1:
            raise ValueError('Пустой запрос')
        data = json.loads(body.read(length).decode('utf-8'))
        if not isinstance(data, dict):
            raise ValueError('Ожидается объект JSON')
        return post_response(path, data, admission)
    except (ValueError, RecursionError):
        return json_response({'error': 'Не удалось подготовить материал. Проверь ответы и попробуй ещё раз.'},
                             HTTPStatus.BAD_REQUEST)
    except GenerationLimit as exc:
        return json_response({'error': 'Сейчас много запросов на уроки. Попробуй позже.'},
                             HTTPStatus.TOO_MANY_REQUESTS, [('Retry-After', str(exc.retry_after))])
    except StoryProviderError as exc:
        LOGGER.warning('Ошибка генерации истории (%s)', type(exc.__cause__).__name__)
        return json_response({'error': 'Не удалось создать историю. Попробуй позже.'}, HTTPStatus.BAD_GATEWAY)
    except (ImportError, RuntimeError) as exc:
        LOGGER.error('Приложение временно недоступно (%s)', type(exc).__name__)
        return json_response({'error': 'Генерация временно недоступна. Попробуй позже.'},
                             HTTPStatus.SERVICE_UNAVAILABLE)
    except Exception as exc:
        LOGGER.error('Необработанная ошибка (%s)', type(exc).__name__)
        return json_response({'error': 'Не удалось выполнить запрос. Попробуй позже.'},
                             HTTPStatus.INTERNAL_SERVER_ERROR)


class Handler(BaseHTTPRequestHandler):
    def serve_request(self):
        path = self.path.partition('?')[0]
        status, headers, payload = handle_request(self.command, path,
                                                  self.headers.get('Content-Length'), self.rfile)
        self.send_response(status)
        for name, value in headers:
            self.send_header(name, value)
        self.end_headers()
        if self.command != 'HEAD':
            self.wfile.write(payload)

    do_GET = do_HEAD = do_POST = serve_request


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--demo',action='store_true')
    parser.add_argument('--open',action='store_true')
    args = parser.parse_args()
    if args.demo:
        os.environ['FINSTORY_DEMO'] = '1'
    port = int(os.getenv('FINSTORY_PORT', '8000'))
    print(f'FinStory: http://127.0.0.1:{port}', flush=True)
    print('Режим:', 'демонстрация' if args.demo else 'Yandex + модель терминов', flush=True)
    if not args.demo and not StoryAgent().configured:
        print('Нужны YANDEX_API_KEY и YANDEX_FOLDER_ID в .env', flush=True)
    server = ThreadingHTTPServer(('127.0.0.1', port), Handler)
    if args.open:
        import webbrowser
        timer=threading.Timer(0.8,lambda:webbrowser.open(f'http://127.0.0.1:{port}'))
        timer.daemon=True
        timer.start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
