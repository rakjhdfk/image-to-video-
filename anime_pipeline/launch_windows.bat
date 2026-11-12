@echo off
setlocal
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" app.py
  if errorlevel 1 pause
  exit /b
)
where py >nul 2>nul
if errorlevel 1 (
  python app.py
) else (
  py -3 app.py
)
if errorlevel 1 pause
