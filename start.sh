#!/bin/bash
# Local Legal AI Assistant Startup Script

# Determine project root
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

echo "=========================================================="
echo "⚖️ Starting Local Legal AI Assistant Suite"
echo "=========================================================="

# Verify Python 3 is installed
if ! command -v python3 &>/dev/null; then
    echo "[!] Python 3 is not installed or not in PATH. Please install Python 3.11+."
    exit 1
fi

# Check for Port Collisions (Port 8000 for FastAPI, Port 8501 for Streamlit)
python3 -c "import socket; s = socket.socket(); s.bind(('127.0.0.1', 8000))" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "[!] Error: Port 8000 (FastAPI Backend) is already in use."
    echo "    Please stop any process running on port 8000."
    exit 1
fi

python3 -c "import socket; s = socket.socket(); s.bind(('127.0.0.1', 3000))" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "[!] Error: Port 3000 (Next.js React Frontend) is already in use."
    echo "    Please stop any process running on port 3000."
    exit 1
fi

# Setup Virtual Environment if not present
if [ ! -d "venv" ]; then
    echo "[*] Creating Python virtual environment ('venv')..."
    python3 -m venv venv
    if [ $? -ne 0 ]; then
        echo "[!] Failed to create virtual environment. Please install python3-venv or verify Python setup."
        exit 1
    fi
    source venv/bin/activate
    echo "[*] Installing dependencies from requirements.txt (this may take a minute)..."
    pip install --upgrade pip
    pip install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo "[!] Failed to install dependencies. Please check requirements.txt."
        exit 1
    fi
else
    source venv/bin/activate
    echo "[*] Verifying/updating dependencies..."
    pip install -r requirements.txt
fi

# Check for Node.js (required for Next.js frontend dev server)
if ! command -v npm &>/dev/null; then
    echo "[!] Error: Node.js/NPM is not installed. Please install Node.js to run the Next.js frontend."
    exit 1
fi

# Verify frontend node_modules
if [ ! -d "aegis_frontend/node_modules" ]; then
    echo "[*] Installing frontend dependencies in aegis_frontend..."
    cd aegis_frontend && npm install && cd ..
fi

# Check for Ollama Setup
if command -v ollama &>/dev/null; then
    echo "[*] Ollama CLI detected."
    # Check if service is active
    python3 -c "import socket; s = socket.socket(); s.connect(('127.0.0.1', 11434))" 2>/dev/null
    if [ $? -eq 0 ]; then
        echo "[*] Ollama service is active."
    else
        echo "----------------------------------------------------------"
        echo "[⚠️ WARNING] Ollama service is not running on port 11434."
        echo "Please start the Ollama desktop app or service."
        echo "----------------------------------------------------------"
    fi
else
    echo "----------------------------------------------------------"
    echo "[⚠️ WARNING] Ollama CLI was not found in your PATH."
    echo "Aegis AI runs 100% locally and requires Ollama."
    echo "Please download and install it from: https://ollama.com/"
    echo "----------------------------------------------------------"
fi

# Ensure data directories exist
mkdir -p data

echo "=========================================================="
echo "[*] Starting AegisAI FastAPI Backend & Next.js Frontend..."
echo "=========================================================="

# Trap to kill background tasks on exit
trap 'kill $(jobs -p)' EXIT

# Launch backend in background
PYTHONPATH=. python3 aegis_backend/main.py &

# Launch Next.js frontend
cd aegis_frontend && npm run dev

