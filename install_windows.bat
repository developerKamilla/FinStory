@echo off
cd /d "%~dp0"
set "PY=python"
if exist "%USERPROFILE%\anaconda\envs\alisa-course\python.exe" set "PY=%USERPROFILE%\anaconda\envs\alisa-course\python.exe"
if exist ".venv\Scripts\python.exe" set "PY=%CD%\.venv\Scripts\python.exe"
echo Python: %PY%
"%PY%" -m pip install -r requirements.txt
if errorlevel 1 goto end
"%PY%" setup_model.py
:end
pause
