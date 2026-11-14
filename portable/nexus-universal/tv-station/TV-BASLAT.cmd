@echo off
setlocal EnableExtensions
cd /d "%~dp0"
where py >nul 2>nul
if not errorlevel 1 (
  py -3 -c "import sys;sys.exit(0 if sys.version_info >= (3,10) else 1)" >nul 2>nul
  if not errorlevel 1 (
    py -3 "%~dp0tv_station.py"
    exit /b %errorlevel%
  )
)
where python >nul 2>nul
if not errorlevel 1 (
  python -c "import sys;sys.exit(0 if sys.version_info >= (3,10) else 1)" >nul 2>nul
  if not errorlevel 1 (
    python "%~dp0tv_station.py"
    exit /b %errorlevel%
  )
)
echo [NEXUS TV] Python 3.10+ bulunamadi. Bu surum tek basina calisan EXE degildir.
echo [NEXUS TV] Mini bilgisayarda Python, Ollama ve qwen3:8b kurulu olmali.
pause
exit /b 2
