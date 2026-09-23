@echo off
setlocal
set "REPO=%~dp0"
set "VENV_PY=%REPO%.venv\Scripts\python.exe"
if not exist "%VENV_PY%" (
  echo [!!] .venv not found. Run install.bat first.
  exit /b 1
)
"%VENV_PY%" "%REPO%scripts\start_windows.py"
exit /b %errorlevel%
