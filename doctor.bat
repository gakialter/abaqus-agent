@echo off
REM ============================================================
REM  abaqus-agent - diagnostic (double-click this file)
REM ============================================================
setlocal
set "REPO=%~dp0"
set "VENV_PY=%REPO%.venv\Scripts\python.exe"

if exist "%VENV_PY%" (
  set "PY=%VENV_PY%"
) else (
  set "PY=py"
  where py >nul 2>&1 || set "PY=python"
)

"%PY%" "%REPO%scripts\doctor.py"
set "RC=%ERRORLEVEL%"

echo.
if "%RC%"=="0" (
  echo Overall: READY - you can use abaqus-agent in Doubao Work.
) else (
  echo Overall: NOT READY - follow the fix hints above, then re-run.
)
echo.
pause
exit /b %RC%
