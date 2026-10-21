@echo off
cd /d "%~dp0"
set "PY=python"
if exist "%USERPROFILE%\anaconda\envs\alisa-course\python.exe" set "PY=%USERPROFILE%\anaconda\envs\alisa-course\python.exe"
if exist ".venv\Scripts\python.exe" set "PY=%CD%\.venv\Scripts\python.exe"
"%PY%" -u app.py --demo --open
pause
