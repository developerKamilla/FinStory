import argparse
import csv
import hashlib
import time
import json
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError, URLError

from agent import DemoAgent, StoryAgent
from interests import InterestModel
from terms import TERMS_MODEL, DICTIONARY

ROOT = Path(__file__).parent
LESSONS = json.loads((ROOT / 'data' / 'lessons.json').read_text(encoding='utf-8'))
ENTRY = json.loads((ROOT / 'data' / 'entry_quiz.json').read_text(encoding='utf-8'))
with (ROOT / 'data' / 'finance_terms.csv').open(encoding='utf-8-sig', newline='') as source:
    TERMS = {row['term'].lower(): row['definition'] for row in csv.DictReader(source)}
TERMS.update(DICTIONARY)
LOG_LOCK = threading.Lock()
CACHE_LOCK = threading.Lock()
CACHE = {}


def record_lesson(number, result, weights, definitions):
    path = ROOT / 'data' / 'generated.jsonl'
    event = {'time': time.time(), 'lesson': number, 'source': result['source'],
             'story': result['story'], 'hints': result['hints'], 'weights': weights,
             'terms': definitions}
    with LOG_LOCK, path.open('a', encoding='utf-8') as stream:
        stream.write(json.dumps(event, ensure_ascii=False) + '\n')


def create_lesson(data):
    lesson = get_lesson(data.get('number'))
    answer = str(data.get('answer', '')).strip()[:800]
    if not answer:
        raise ValueError('Напиши о своих интересах')
    demo = os.getenv('FINSTORY_DEMO') == '1'
    identity = dict(data, demo=demo)
    key = hashlib.sha256(json.dumps(identity,ensure_ascii=False,sort_keys=True).encode()).hexdigest()
    with CACHE_LOCK:
        if key in CACHE:
            return CACHE[key]
    definitions = [{'term':name, 'definition':TERMS[name]} for name in lesson['terms']]
    weights = InterestModel().weights(answer)
    agent = DemoAgent() if demo else StoryAgent()
    if not demo and not agent.configured:
        raise RuntimeError('Заполни YANDEX_API_KEY и YANDEX_FOLDER_ID в .env или запусти python app.py --demo')
    character = data.get('character')
    if character is not None:
        if not isinstance(character,dict) or set(character) != {'name','age','personality'}:
            raise ValueError('Некорректные данные персонажа')
        if type(character['age']) is not int or not isinstance(character['name'],str) or not isinstance(character['personality'],str):
            raise ValueError('Некорректные данные персонажа')
    result = agent.write(lesson,answer,weights,definitions,
                         str(data.get('previous_story',''))[:650],character)
    explanations = [TERMS_MODEL.explain(item['term'],item['definition'],result['story'],
                      result['hints'][item['term']],weights,demo=demo) for item in definitions]
    record_lesson(lesson['lesson_id'],result,weights,explanations)
    response = {'story':result['story'],'takeaway':result['takeaway'],
                'character':result['character'], 'terms':[
                    {k:v for k,v in item.items() if k not in ('source','raw')}
                    for item in explanations]}
    with CACHE_LOCK:
        if len(CACHE) >= 64:
            CACHE.pop(next(iter(CACHE)))
        CACHE[key] = response
    return response


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


class Handler(BaseHTTPRequestHandler):
    def json_response(self, data, status=200):
        payload = json.dumps(data, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self):
        if self.path == '/':
            payload = (ROOT / 'index.html').read_bytes()
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
        elif self.path in ('/assets/logo.png', '/assets/mascot.png'):
            name = self.path.rsplit('/', 1)[-1]
            payload = (ROOT / 'assets' / name).read_bytes()
            self.send_response(200)
            self.send_header('Content-Type', 'image/png')
            self.send_header('Content-Length', str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
        elif self.path == '/api/entry':
            self.json_response([{'question': q['question'], 'answers': q['answers']} for q in ENTRY])
        elif self.path == '/api/lessons':
            self.json_response([{'id': x['lesson_id'], 'title': x['title']} for x in LESSONS])
        elif self.path == '/api/status':
            self.json_response({'mode': 'demo' if os.getenv('FINSTORY_DEMO') == '1' else ('yandex' if StoryAgent().configured else 'needs_env'),
                                'lessons': len(LESSONS), 'term_backend': TERMS_MODEL.backend,
                                'trained_terms':list(DICTIONARY), 'cache_version':'course-ten-single-v2'})
        else:
            self.send_error(404)

    def do_POST(self):
        try:
            length = int(self.headers.get('Content-Length', 0))
            if length < 1 or length > 10000:
                raise ValueError('Некорректный запрос')
            data = json.loads(self.rfile.read(length))
            if self.path == '/api/entry-grade':
                answers = data.get('answers')
                if (not isinstance(answers, list) or len(answers) != 5 or any(
                    type(value) is not int or not 0 <= value < 3 for value in answers)):
                    raise ValueError('Ответь на все пять вопросов')
                score = sum(value == q['correct'] for value, q in zip(answers, ENTRY))
                self.json_response({'score': score, 'level': 'начальный' if score < 3 else 'базовый'})
            elif self.path == '/api/interest':
                answer = str(data.get('answer', '')).strip()
                if not answer:
                    raise ValueError('Напиши о своих интересах')
                weights = InterestModel().weights(answer[:800])
                self.json_response({'interest': next(iter(weights), 'other'),
                                    'weights': weights})
            elif self.path == '/api/lesson':
                self.json_response(create_lesson(data))
            elif self.path == '/api/questions':
                self.json_response([{'question': q['question'], 'answers': q['answers']}
                                    for q in questions(data.get('number'), data.get('checkpoint', False))])
            elif self.path == '/api/grade':
                self.json_response(grade(data.get('number'), data.get('answers'),
                                         data.get('checkpoint', False)))
            else:
                self.send_error(404)
        except (ValueError, KeyError, TypeError, FileNotFoundError) as exc:
            print('Request error:', type(exc).__name__, str(exc), flush=True)
            self.json_response({'error': 'Не удалось подготовить материал. Попробуй ещё раз.'}, 400)
        except ImportError as exc:
            print('Dependencies missing:',str(exc),flush=True)
            self.json_response({'error':'Приложение ещё не настроено. Проверь установку зависимостей в терминале.'},503)
        except RuntimeError as exc:
            print('Configuration error:', str(exc), flush=True)
            self.json_response({'error': 'Не удалось подготовить объяснение. Проверь настройку приложения в терминале.'}, 503)
        except (HTTPError, URLError, OSError) as exc:
            print('Generation error:', type(exc).__name__, str(exc), flush=True)
            self.json_response({'error': 'Не удалось создать урок. Попробуй позже.'}, 502)


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
