FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 HF_HUB_OFFLINE=1 HF_HOME=/tmp/huggingface
WORKDIR /app

COPY requirements.txt ./
RUN python -m pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu 'torch>=2.6,<3' \
    && python -m pip install --no-cache-dir -r requirements.txt waitress==3.0.2

COPY app.py agent.py baseline_terms.py interests.py serve.py terms.py dictionary.json index.html ./
COPY assets/logo.png assets/mascot.png ./assets/
COPY data/demo_stories.json data/entry_quiz.json data/finance_terms.csv data/lessons.json ./data/

USER 10001:10001
EXPOSE 8000
CMD ["python", "-m", "serve"]
