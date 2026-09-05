@echo off
setlocal enabledelayedexpansion
title GridForecast AI - Setup

echo.
echo ================================================
echo        GridForecast AI  --  Setup
echo    Delhi Electricity Demand Forecasting
echo ================================================
echo.

set "PROJECT_DIR=%~dp0.."
cd /d "%PROJECT_DIR%"

:: ── Step 1: Python check ─────────────────────────────────────
echo [1/8] Checking Python...
set "PYTHON="
for %%P in (python3.12 python3.11 python3.10 python python3) do (
    where %%P >nul 2>&1
    if !errorlevel! == 0 (
        for /f "tokens=*" %%V in ('%%P --version 2^>^&1') do set PY_VER=%%V
        set PYTHON=%%P
        echo       OK: Found !PY_VER! ^(!PYTHON!^)
        goto :python_found
    )
)
echo       ERROR: Python 3.10+ not found.
echo       Download from: https://www.python.org/downloads/
echo       Make sure to check "Add Python to PATH" during install.
pause
exit /b 1
:python_found

:: ── Step 2: Node.js check ────────────────────────────────────
echo [2/8] Checking Node.js...
where node >nul 2>&1
if %errorlevel% neq 0 (
    echo       ERROR: Node.js not found.
    echo       Download from: https://nodejs.org ^(choose LTS^)
    pause
    exit /b 1
)
for /f "tokens=*" %%V in ('node --version') do echo       OK: Node.js %%V

:: ── Step 3: Virtual environment ──────────────────────────────
echo [3/8] Setting up Python virtual environment...
if not exist "venv" (
    echo       Creating venv...
    %PYTHON% -m venv venv
    if %errorlevel% neq 0 (
        echo       ERROR: Could not create venv.
        pause
        exit /b 1
    )
)
echo       OK: venv ready

:: ── Step 4: Install Python packages ──────────────────────────
echo [4/8] Installing Python dependencies...
echo       This may take 2-3 minutes on first run...

call venv\Scripts\python.exe -m pip install --upgrade pip -q

call venv\Scripts\python.exe -m pip install ^
    fastapi "uvicorn[standard]" python-multipart starlette ^
    pandas numpy pyarrow openpyxl ^
    scikit-learn xgboost scipy joblib ^
    prophet statsmodels holidays ^
    httpx requests beautifulsoup4 lxml playwright ^
    sqlalchemy aiosqlite aiofiles ^
    pydantic pydantic-settings python-dotenv ^
    apscheduler ruff ^
    --no-user -q

if %errorlevel% neq 0 (
    echo       ERROR: Package installation failed.
    pause
    exit /b 1
)
echo       OK: Python packages installed

:: Playwright browser
echo       Installing Playwright browser...
call venv\Scripts\python.exe -m playwright install chromium --with-deps
echo       OK: Playwright ready

:: Try TensorFlow (only works on Python 3.10-3.12)
call venv\Scripts\python.exe -m pip install tensorflow --no-user -q 2>nul
if %errorlevel% == 0 (
    echo       OK: TensorFlow installed ^(CNN/LSTM models available^)
) else (
    echo       NOTE: TensorFlow not available for this Python version.
    echo             CNN/LSTM will be skipped. All other models work fine.
)

:: ── Step 5: Create directories ───────────────────────────────
echo [5/8] Creating data directories...
if not exist "data\raw"       mkdir "data\raw"
if not exist "data\processed" mkdir "data\processed"
if not exist "data\models"    mkdir "data\models"
if not exist "logs"           mkdir "logs"
echo       OK: Directories created

:: ── Step 6: .env file ────────────────────────────────────────
echo [6/8] Setting up configuration...
if not exist ".env" (
    copy ".env.example" ".env" >nul
    echo       OK: .env created
) else (
    echo       OK: .env already exists
)

:: ── Step 7: Download real data ───────────────────────────────
echo [7/8] Downloading real Delhi demand + weather data...
echo       Fetching from delhisldc.org and open-meteo.com...
call venv\Scripts\python.exe scripts\download_real_data.py
if %errorlevel% neq 0 (
    echo       WARNING: Data download had issues. Check internet connection.
)

:: ── Step 8: Frontend ─────────────────────────────────────────
echo [8/8] Installing frontend dependencies...
cd frontend
call npm install --legacy-peer-deps --silent
cd ..
echo       OK: Frontend ready

:: ── Done ─────────────────────────────────────────────────────
echo.
echo ================================================
echo             Setup Complete!
echo ================================================
echo.
echo  To start the system:
echo.
echo    Double-click:  scripts\start.bat
echo    Or run:        scripts\start.bat
echo.
echo  Then open:  http://localhost:3000
echo.
pause
