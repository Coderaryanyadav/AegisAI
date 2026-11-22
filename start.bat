@echo off
title Aegis Legal AI Assistant - Launcher
echo ==========================================================
echo ⚖️ Starting Local Legal AI Assistant Suite (Windows)
echo ==========================================================

:: Check if Python is installed
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] Python is not installed or not in PATH.
    echo     Please download and install Python 3.11+ from https://www.python.org/
    echo     Make sure to check "Add Python to PATH" during installation.
    pause
    exit /b 1
)

:: Check for Port Collisions (Port 8000 for FastAPI, Port 3000 for Next.js)
python -c "import socket; s = socket.socket(); s.bind(('127.0.0.1', 8000))" >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] Error: Port 8000 (FastAPI Backend) is already in use.
    echo     Please stop any process running on port 8000.
    pause
    exit /b 1
)

python -c "import socket; s = socket.socket(); s.bind(('127.0.0.1', 3000))" >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] Error: Port 3000 (Next.js React Frontend) is already in use.
    echo     Please stop any process running on port 3000.
    pause
    exit /b 1
)

:: Setup Virtual Environment if not present
if not exist "venv" (
    echo [*] Creating Python virtual environment ('venv')...
    python -m venv venv
    if %errorlevel% neq 0 (
        echo [!] Failed to create virtual environment.
        pause
        exit /b 1
    )
    call venv\Scripts\activate
    echo [*] Installing dependencies from requirements.txt (this may take a minute)...
    python -m pip install --upgrade pip
    pip install -r requirements.txt
    if %errorlevel% neq 0 (
        echo [!] Failed to install dependencies. Please check requirements.txt.
        pause
        exit /b 1
    )
) else (
    call venv\Scripts\activate
    echo [*] Verifying/updating dependencies...
    pip install -r requirements.txt
)

:: Check for Node.js (required for Next.js frontend dev server)
where npm >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] Error: Node.js/NPM is not installed. Please install Node.js to run the Next.js frontend.
    pause
    exit /b 1
)

:: Verify frontend node_modules
if not exist "aegis_frontend\node_modules" (
    echo [*] Installing frontend dependencies in aegis_frontend...
    cd aegis_frontend
    call npm install
    cd ..
)

:: Ensure data directories exist
if not exist "data" mkdir "data"

:: Check for Local AI (LM Studio on port 1234 primary, Ollama fallback)
powershell -Command "try { $r = Invoke-WebRequest -Uri http://127.0.0.1:1234/v1/models -UseBasicParsing -TimeoutSec 2; exit 0 } catch { exit 1 }" >nul 2>&1
if %errorlevel% eq 0 (
    echo [*] LM Studio Local AI service is active and running on port 1234.
) else (
    where lms >nul 2>&1
    if %errorlevel% eq 0 (
        echo [*] LM Studio CLI detected. Starting server...
        lms server start --cors >nul 2>&1
    ) else (
        where ollama >nul 2>&1
        if %errorlevel% eq 0 (
            echo [*] Ollama CLI detected.
        ) else (
            echo ----------------------------------------------------------
            echo [INFO] LM Studio is recommended for local legal reasoning.
            echo Please ensure LM Studio Local Server is running on port 1234.
            echo ----------------------------------------------------------
        )
    )
)

echo ==========================================================
echo [*] Starting AegisAI FastAPI Backend & Next.js Frontend...
echo ==========================================================

:: Launch backend in background
start /b cmd /c "set PYTHONPATH=.&& python aegis_backend\main.py"

:: Launch Next.js frontend in the foreground
cd aegis_frontend
call npm run dev

