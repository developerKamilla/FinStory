# FinStory

## Первая установка
```powershell
conda create -n alisa-course python=3.11
conda activate alisa-course
python -m pip install -r requirements.txt
Copy-Item .env.example .env
notepad .env
python setup_model.py .\FinStory_trained_model.zip
python -u .\app.py --open
```
В .env заполните YANDEX_API_KEY и YANDEX_FOLDER_ID.

## Развёртывание на VPS

Для запуска нужен Linux VPS с Docker Compose и публичным IP. Начальная конфигурация для модели на CPU — 2 vCPU, 4 ГБ RAM и 15 ГБ диска.

1. Направьте запись `A` домена `kami-finstory.online` на публичный IPv4 VPS и откройте входящие TCP-порты 80 и 443. Caddy получит и будет обновлять HTTPS-сертификат.
2. Перенесите на сервер файлы из списка ниже, включая `.dockerignore`. Папка `models/terms` должна содержать распакованные веса и токенизатор. Контейнеру нужен доступ к этим файлам на чтение.
3. Создайте на сервере `.env` по шаблону `.env.example`, заполните `YANDEX_API_KEY` и `YANDEX_FOLDER_ID`. Установите для файла права `600`.
4. Запустите и проверьте приложение:

   ```sh
   docker compose up -d --build
   docker compose ps
   curl -fsS https://kami-finstory.online/healthz
   curl -fsS https://kami-finstory.online/api/status
   ```

   Первый запрос возвращает `{"status":"ok"}`. Второй показывает режим `yandex` и модель терминов `local_merged`. Журнал запуска доступен по команде `docker compose logs --tail=100 app proxy`.

Файлы для переноса:

```text
.dockerignore  .env.example  Dockerfile  compose.yaml  Caddyfile
app.py  agent.py  baseline_terms.py  interests.py  serve.py  terms.py
requirements.txt  dictionary.json  index.html
assets/logo.png  assets/mascot.png
data/demo_stories.json  data/entry_quiz.json  data/finance_terms.csv  data/lessons.json
models/terms/
```

Сервер допускает три одновременные генерации, до 12 новых генераций в минуту с одного IP и до `FINSTORY_DAILY_GENERATIONS` за 24 часа. Счётчики сбрасываются при перезапуске. Прогресс хранится в браузере на адресе сайта. Серверная конфигурация отключает запись текстов историй в файл.

## Курс
Один ответ об увлечениях, пять вводных вопросов, десять уроков с одним основным понятием в каждом. Первые три темы: дебетовая карта, накопительный счёт, вклад. Далее: кредит, инфляция, сложный процент, инвестиции, акции, облигации, диверсификация.

После урока есть три вопроса, после уроков 3, 6 и 9 повторение из семи вопросов. Повторное открытие показывает сохранённый материал. Повторный опрос в профиле сбрасывает прежние главы и прогресс.

## Проверки
```powershell
python -m unittest discover -s tests -q
```
Тесты проверяют код и взаимодействие компонентов с подменой внешних ответов. Качество живой генерации оценивается отдельно по финансовому смыслу, русскому языку и связи с историей. Модель обучена на пяти понятиях.

## Файлы
app.py связывает компоненты; agent.py обращается к Yandex; terms.py загружает модель; interests.py вычисляет веса по словам; index.html содержит интерфейс. data хранит учебный материал, docs — отчёт, инструкции, протокол и сценарий демонстрации.

Репозиторий: https://sourcecraft.dev/organization-kamilla-farr/finalfa
