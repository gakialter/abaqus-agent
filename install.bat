@echo off
REM ============================================================
REM  abaqus-agent - one-click install (double-click this file)
REM  English-only console output on purpose (codepage-safe).
REM ============================================================
setlocal DisableDelayedExpansion
set "REPO=%~dp0"

REM --- find a system Python to run the bootstrap ---
set "PY="
where py >nul 2>&1 && set "PY=py"
if not defined PY (
  where python >nul 2>&1 && set "PY=python"
)
if not defined PY (
  echo [!!] No Python found.
  echo     Install external Python 3.11 first, then run install.bat again.
  echo.
  pause
  exit /b 1
)

echo Using Python launcher: %PY%
echo Repo: "%REPO%"
echo.

"%PY%" "%REPO%scripts\bootstrap_windows.py"
set "RC=%ERRORLEVEL%"

echo.
if "%RC%"=="0" (
  echo [OK] install finished. Next: double-click doctor.bat, then start_abaqus_agent.bat
) else (
  echo [!!] install did not complete. Read the messages above, fix, and re-run.
  echo     If unsure, double-click doctor.bat
)
echo.
pause
exit /b %RC%
