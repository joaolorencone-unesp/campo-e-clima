@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Instale o ambiente conforme docs\REPRODUCIBILITY.md
  pause
  exit /b 1
)
echo Painel local: http://127.0.0.1:8776
start "" "http://127.0.0.1:8776"
".venv\Scripts\python.exe" -m http.server 8776 --bind 127.0.0.1 --directory site
