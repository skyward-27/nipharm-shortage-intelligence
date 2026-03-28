@echo off
REM Nipharma Intelligence - Development Server Startup Script (Windows)
REM Starts both FastAPI backend and React frontend in parallel

cls
echo ==================================================
echo.
echo   Nipharma Intelligence - Development Server
echo.
echo ==================================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python 3 is not installed
    exit /b 1
)

REM Check if Node.js is installed
node --version >nul 2>&1
if errorlevel 1 (
    echo Error: Node.js is not installed
    exit /b 1
)

echo Python and Node.js found!
echo.

REM Start Backend
echo Starting FastAPI Backend...
cd nipharma-backend

if not exist venv (
    echo Creating virtual environment...
    python -m venv venv
)

call venv\Scripts\activate.bat
pip install -q -r requirements.txt 2>nul || exit /b 1

echo   Backend starting at http://localhost:8000
echo   Swagger UI: http://localhost:8000/docs
start "Nipharma Backend" cmd /k "python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000"

timeout /t 2 /nobreak

REM Start Frontend
echo.
echo Starting React Frontend...
cd ..\nipharma-frontend

if not exist node_modules (
    echo Installing dependencies...
    npm install -q 2>nul || yarn install -q 2>nul
)

echo   Frontend starting at http://localhost:3000
start "Nipharma Frontend" cmd /k "npm start"

timeout /t 3 /nobreak

echo.
echo ==================================================
echo Both servers are running!
echo ==================================================
echo.
echo Dashboard:     http://localhost:3000
echo API Docs:      http://localhost:8000/docs
echo Backend:       http://localhost:8000
echo.
echo Close windows to stop servers
echo.
pause
