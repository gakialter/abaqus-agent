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
  echo Bridge ready. MCP host integration must be verified separately.
) else (
  echo Review INSTALLED and BRIDGE_READY above. Integration is external.
)
echo.
pause
exit /b %RC%
