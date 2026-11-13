@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if %ERRORLEVEL% EQU 0 (
  py -3 desktop_client.py %*
) else (
  python desktop_client.py %*
)
exit /b %ERRORLEVEL%
