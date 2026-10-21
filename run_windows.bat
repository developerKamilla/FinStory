@echo off
cd /d "%~dp0"
set "PY=python"
if exist "%USERPROFILE%\anaconda\envs\alisa-course\python.exe" set "PY=%USERPROFILE%\anaconda\envs\alisa-course\python.exe"
if exist ".venv\Scripts\python.exe" set "PY=%CD%\.venv\Scripts\python.exe"
echo Python: %PY%
echo Open http://127.0.0.1:8000
"%PY%" -u app.py --open
pause
