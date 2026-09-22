@echo off
setlocal enabledelayedexpansion
REM ============================================================
REM  abaqus-agent - daily start (double-click this file)
REM  Reads its own folder as the workspace. English output only.
REM ============================================================
set "REPO=%~dp0"
set "VENV_PY=%REPO%.venv\Scripts\python.exe"
set "MCP_HOME=%REPO%mcp_home"
set "STATUS=%MCP_HOME%\status.json"
set "LOCALENV=%REPO%.abaqus-agent.local"

if not exist "%VENV_PY%" (
  echo [!!] .venv not found. Run install.bat first.
  echo.
  pause
  exit /b 1
)

REM --- load detected abaqus command written by install.bat ---
if exist "%LOCALENV%" call "%LOCALENV%"
if not defined ABAQUS_CMD set "ABAQUS_CMD=abaqus"
if "%ABAQUS_CMD%"=="" set "ABAQUS_CMD=abaqus"

set "ABAQUS_MCP_HOME=%MCP_HOME%"

REM --- is the bridge already running? (avoid starting a 2nd Abaqus/license use) ---
REM --- RUNNING only when status==running AND a real ping succeeds (not just a stale status) ---
"%VENV_PY%" "%REPO%scripts\bridge_state.py" > "%TEMP%\abaqus_bridge_state.txt"
set "BSTATE="
for /f "usebackq delims=" %%A in ("%TEMP%\abaqus_bridge_state.txt") do set "BSTATE=%%A"

if "%BSTATE%"=="RUNNING" (
  echo ================================================
  echo Abaqus Agent is already running - not starting a second one.
  echo ================================================
  echo Open Doubao Work and upload your task.
  echo.
  pause
  exit /b 0
)

REM --- record old status mtime so we wait for a FRESH file, not a stale one ---
set "OLDMTIME="
if exist "%STATUS%" for %%F in ("%STATUS%") do set "OLDMTIME=%%~tF"

echo Starting Abaqus/CAE with the agent bridge...
echo (This opens the Abaqus window; keep it open while you work.)
echo.
start "" "%ABAQUS_CMD%" cae script="%REPO%abaqus_start_mcp.py"

echo Waiting for the bridge to come online (up to ~90s)...
set /a waited=0
:waitloop
set "CURMTIME="
if exist "%STATUS%" for %%F in ("%STATUS%") do set "CURMTIME=%%~tF"
if defined CURMTIME (
  if not "!CURMTIME!"=="!OLDMTIME!" (
    findstr /C:"\"status\": \"running\"" "%STATUS%" >nul 2>&1 && goto started
  )
)
if %waited% GEQ 90 goto timeout
timeout /t 3 /nobreak >nul
set /a waited+=3
goto waitloop

:started
echo ================================================
echo Abaqus Agent is started.
echo Now open Doubao Work and upload your task.
echo ================================================
echo.
pause
exit /b 0

:timeout
echo [!!] Bridge did not report a fresh 'running' within 90s.
echo     The Abaqus window may still be loading, or startup failed.
echo     Double-click doctor.bat to diagnose.
echo.
pause
exit /b 1
