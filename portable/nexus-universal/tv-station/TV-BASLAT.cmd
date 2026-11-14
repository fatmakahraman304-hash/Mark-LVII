@echo off
setlocal EnableExtensions
cd /d "%~dp0"
where py >nul 2>nul
if not errorlevel 1 (
  py -3 -c "import sys;sys.exit(0 if sys.version_info >= (3,10) else 1)" >nul 2>nul
  if not errorlevel 1 goto run_py
)
where python >nul 2>nul
if not errorlevel 1 (
  python -c "import sys;sys.exit(0 if sys.version_info >= (3,10) else 1)" >nul 2>nul
  if not errorlevel 1 goto run_python
)
echo [NEXUS TV] Python 3.10+ bulunamadi. Bu surum bagimsiz EXE degildir.
echo [NEXUS TV] Mini bilgisayarda Python, Ollama ve qwen3:8b kurulu olmali.
pause
exit /b 2
:run_py
py -3 "%~dp0tv_station.py"
exit /b %errorlevel%
:run_python
python "%~dp0tv_station.py"
exit /b %errorlevel%
