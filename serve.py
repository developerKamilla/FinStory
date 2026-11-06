import logging
import os
from functools import partial

from agent import StoryAgent
from app import MAX_BODY_BYTES, GenerationGate, handle_request
from terms import ROOT, TERMS_MODEL


def create_application(gate):
    def application(environ, start_response):
        method = environ['REQUEST_METHOD']
        # Caddy sets this header, and Compose does not publish the application port.
        client = environ.get('HTTP_X_FINSTORY_CLIENT') or environ['REMOTE_ADDR']
        status, headers, payload = handle_request(
            method, environ['PATH_INFO'], environ.get('CONTENT_LENGTH'), environ['wsgi.input'],
            partial(gate.admit, client),
        )
        start_response(f'{status.value} {status.phrase}', headers)
        return [] if method == 'HEAD' else [payload]

    return application


def main():
    from waitress import serve

    logging.basicConfig(level=logging.INFO)
    gate = GenerationGate(int(os.getenv('FINSTORY_DAILY_GENERATIONS', '300')))
    if os.getenv('FINSTORY_DEMO') != '1':
        if not StoryAgent().configured:
            raise SystemExit('Нужны YANDEX_API_KEY и YANDEX_FOLDER_ID')
        if not (ROOT / 'models' / 'terms' / 'config.json').is_file():
            raise SystemExit('Нужны полные веса в models/terms')
        TERMS_MODEL.load()
    serve(create_application(gate), host='0.0.0.0', port=8000, threads=8,
          connection_limit=100, max_request_header_size=16_384,
          max_request_body_size=MAX_BODY_BYTES, expose_tracebacks=False, ident='FinStory')


if __name__ == '__main__':
    main()
