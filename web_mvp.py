from __future__ import annotations

import json
import mimetypes
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from src.constants import INTEREST_NAMES_RU
from src.engine import FinStoryEngine
from src.quiz import KNOWLEDGE_QUESTIONS

ROOT = Path(__file__).resolve().parent
WEB = ROOT / "web"
engine = FinStoryEngine(ROOT)


def json_bytes(obj) -> bytes:
    return json.dumps(obj, ensure_ascii=False).encode("utf-8")


def bootstrap_payload() -> dict:
    return {
        "interests": [
            {"id": key, "name": value}
            for key, value in INTEREST_NAMES_RU.items()
        ],
        "knowledge_questions": [
            {
                "id": q.id,
                "text": q.text,
                "options": q.options,
            }
            for q in KNOWLEDGE_QUESTIONS
        ],
        "lessons": [
            {
                "lesson_id": x["lesson_id"],
                "title": x["title"],
                "difficulty": x["difficulty"],
                "learning_goal": x["learning_goal"],
            }
            for x in engine.lessons
        ],
    }


class Handler(BaseHTTPRequestHandler):
    server_version = "FinStory/5.0"

    def _send_json(self, obj, status=200):
        payload = json_bytes(obj)
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(payload)

    def _read_json(self):
        length = int(self.headers.get("Content-Length", "0") or 0)
        if length <= 0:
            return {}
        raw = self.rfile.read(length)
        return json.loads(raw.decode("utf-8"))

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/api/health":
            self._send_json({
                "ok": True,
                "version": "5.0",
                "interest_model_loaded": engine.classifier.bundle is not None,
                "language_model_configured": engine.generator.language_model.available,
                "plot_ranker_loaded": engine.generator.planner.model is not None,
                "term_ranker_loaded": engine.generator.term_selector.model is not None,
            })
            return
        if path == "/api/bootstrap":
            self._send_json(bootstrap_payload())
            return

        if path == "/":
            file_path = WEB / "index.html"
        else:
            rel = path.lstrip("/")
            file_path = (WEB / rel).resolve()
            try:
                file_path.relative_to(WEB.resolve())
            except ValueError:
                self.send_error(403)
                return

        if not file_path.exists() or not file_path.is_file():
            self.send_error(404)
            return

        ctype, _ = mimetypes.guess_type(str(file_path))
        content = file_path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", (ctype or "application/octet-stream") + ("; charset=utf-8" if (ctype or "").startswith("text/") else ""))
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def do_POST(self):
        path = urlparse(self.path).path
        try:
            body = self._read_json()
            if path == "/api/profile":
                profile = engine.profile(
                    body.get("selected_interests", []),
                    body.get("free_text_answers", []),
                    body.get("knowledge_answers", []),
                )
                self._send_json({"ok": True, "profile": profile})
                return

            if path == "/api/lesson":
                profile = body.get("profile") or {}
                lesson_id = int(body.get("lesson_id", 1))
                result = engine.lesson(profile, lesson_id, body.get("previous_story", ""))
                self._send_json({"ok": True, "result": result})
                return

            self._send_json({"ok": False, "error": "unknown endpoint"}, status=404)
        except Exception as exc:
            self._send_json({"ok": False, "error": "Не удалось подготовить урок"}, status=500)

    def log_message(self, fmt, *args):
        print("[FinStory]", fmt % args)


def run(host="127.0.0.1", port=8000):
    print(f"FinStory MVP: http://{host}:{port}")
    print("Остановить: Ctrl+C")
    ThreadingHTTPServer((host, port), Handler).serve_forever()


if __name__ == "__main__":
    run()
