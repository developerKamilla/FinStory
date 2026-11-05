# FinStory. Запуск и использование

## Запуск уже настроенного проекта в VS Code
Открыть папку FinStory_SITE_FINAL и терминал PowerShell.

```powershell
cd "$HOME\Desktop\FinStory_SITE_FINAL"
conda activate alisa-course
Remove-Item Env:FINSTORY_DEMO -ErrorAction SilentlyContinue
python -u .\app.py --open
```

Если активация не сработала:

```powershell
conda run --no-capture-output -n alisa-course python -u .\app.py --open
```

Терминал оставить открытым. Адрес: http://127.0.0.1:8000. Остановка: Ctrl+C.

## Первая установка
Создать окружение, если его ещё нет, затем установить зависимости тем же интерпретатором:

```powershell
conda create -n alisa-course python=3.11
conda activate alisa-course
python -m pip install -r requirements.txt
Copy-Item .env.example .env
notepad .env
```


Положить архив FinStory_trained_model.zip рядом с app.py и установить готовые веса:

```powershell
python setup_model.py .\FinStory_trained_model.zip
python -u .\app.py --open
```

## Использование
Описать интересы, пройти пять вводных вопросов и посмотреть результат. Выбрать урок, прочитать историю и объяснение понятия, затем ответить на вопросы. В курсе доступны повторения после уроков 3, 6 и 9. В профиле можно начать опрос заново; это сбрасывает старые главы и прогресс в этом браузере.

## Диагностика
- Сообщение «Модель терминов готова» появляется в терминале при загрузке, не на странице.
- Источник local_merged в объяснении обозначает путь локальных объединённых весов.
- При ошибке сохранить строку терминала с типом и текстом ошибки, не отправляя API-ключ.

## Проверки
```powershell
python -m unittest discover -s tests -q
git status
git rev-parse HEAD
```

Первая команда проверяет программные тесты; две другие помогают зафиксировать состояние исходного кода. Оценка русского языка и финансового смысла проводится отдельно.
