@echo off
setlocal EnableExtensions
cd /d "%~dp0"
set "PYTHON="
where py >nul 2>nul
if not errorlevel 1 (
  py -3 -c "import sys;sys.exit(0 if sys.version_info >= (3,10) else 1)" >nul 2>nul
  if not errorlevel 1 set "PYTHON=py -3"
)
if not defined PYTHON (
  where python >nul 2>nul
  if not errorlevel 1 (
    python -c "import sys;sys.exit(0 if sys.version_info >= (3,10) else 1)" >nul 2>nul
    if not errorlevel 1 set "PYTHON=python"
  )
)
if not defined PYTHON (
  echo [NEXUS] Python 3.10+ bulunamadi. Bu USB surumu henuz bagimsiz EXE degildir.
  echo [NEXUS] Guvenli kurulum tamamlanmadan cihaz kontrolu baslatilmayacak.
  exit /b 2
)
if "%~1"=="" (
  echo [NEXUS] Kullanim: desktop-launch-windows.cmd --server https://SUNUCU:8765
  echo [NEXUS] Sertifika gerekirse --ca-file guvenilir-sertifika.pem
  exit /b 2
)
%PYTHON% "%~dp0desktop_client.py" %*
exit /b %ERRORLEVEL%
