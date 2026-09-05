@echo off
setlocal
title GridForecast AI

set "PROJECT_DIR=%~dp0.."
cd /d "%PROJECT_DIR%"

if not exist "venv\Scripts\python.exe" (
    echo ERROR: venv not found. Run setup.bat first.
    pause
    exit /b 1
)

echo.
echo ================================================
echo        GridForecast AI  --  Starting
echo ================================================
echo.

:: Start backend in a new window
echo Starting backend on http://localhost:8000 ...
start "GridForecast Backend" cmd /k "cd /d %PROJECT_DIR% && venv\Scripts\python.exe -m uvicorn backend.api.main:app --reload --port 8000 --host 0.0.0.0"

:: Wait for backend to come up
echo Waiting for backend...
:wait_loop
timeout /t 2 /nobreak >nul
curl -s http://localhost:8000/health >nul 2>&1
if %errorlevel% neq 0 goto wait_loop
echo Backend ready.

:: Start frontend in a new window
echo Starting frontend on http://localhost:3000 ...
start "GridForecast Frontend" cmd /k "cd /d %PROJECT_DIR%\frontend && npm start"

echo.
echo ================================================
echo  Both services are starting!
echo.
echo  Dashboard : http://localhost:3000
echo  API docs  : http://localhost:8000/docs
echo.
echo  Close the Backend and Frontend windows to stop.
echo ================================================
echo.
pause
