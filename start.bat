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

:: Check for Port Collisions (Port 8000 for FastAPI, Port 8501 for Streamlit)
python -c "import socket; s = socket.socket(); s.bind(('127.0.0.1', 8000))" >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] Error: Port 8000 (FastAPI Backend) is already in use.
    echo     Please stop any process running on port 8000.
    pause
    exit /b 1
)

python -c "import socket; s = socket.socket(); s.bind(('127.0.0.1', 8501))" >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] Error: Port 8501 (Streamlit Frontend) is already in use.
    echo     Please stop any process running on port 8501.
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

:: Ensure data directories exist
if not exist "data\encrypted_files" mkdir "data\encrypted_files"
if not exist "data\chromadb" mkdir "data\chromadb"

:: Check for Ollama Setup
where ollama >nul 2>&1
if %errorlevel% eq 0 (
    echo [*] Ollama CLI detected.
    :: Check if Ollama is running on port 11434 (using PowerShell curl/web request)
    powershell -Command "try { $r = Invoke-WebRequest -Uri http://127.0.0.1:11434/api/tags -UseBasicParsing -TimeoutSec 2; exit 0 } catch { exit 1 }" >nul 2>&1
    if %errorlevel% eq 0 (
        echo [*] Ollama service is active and running.
        :: Check if qwen3:8b is pulled
        ollama list | findstr "qwen3:8b" >nul 2>&1
        if %errorlevel% eq 0 (
            echo [*] Found qwen3:8b local model.
        ) else (
            echo ----------------------------------------------------------
            echo [WARNING] Local model 'qwen3:8b' not found in Ollama.
            echo We recommend running this command in another terminal:
            echo     ollama pull qwen3:8b
            echo ----------------------------------------------------------
        )
    ) else (
        echo ----------------------------------------------------------
        echo [WARNING] Ollama service is not running on port 11434.
        echo Please start the Ollama desktop app or service.
        echo ----------------------------------------------------------
    )
) else (
    echo ----------------------------------------------------------
    echo [WARNING] Ollama CLI was not found in your PATH.
    echo Aegis AI runs 100% locally and requires Ollama.
    echo Please download and install it from: https://ollama.com/
    echo Once installed, pull the model by running:
    echo     ollama pull qwen3:8b
    echo ----------------------------------------------------------
)

:: Start FastAPI Backend in a minimized command window to isolate PID
echo [*] Starting FastAPI Backend on http://127.0.0.1:8000...
start "Aegis_Backend_Server" /Min python -m uvicorn legal_ai.main:app --host 127.0.0.1 --port 8000

:: Sleep for 3 seconds to let backend initialize
timeout /t 3 /nobreak >nul

:: Launch Streamlit Frontend in foreground
echo [*] Launching Streamlit Desktop UI on http://127.0.0.1:8501...
echo ----------------------------------------------------------
python -m streamlit run legal_ai\app\frontend.py --server.port 8501 --server.address 127.0.0.1

:: Clean up uvicorn backend on exit (identifies process by window title)
echo.
echo [*] Stopping uvicorn backend server...
taskkill /FI "WINDOWTITLE eq Aegis_Backend_Server" /T /F >nul 2>&1
echo [*] Done.
