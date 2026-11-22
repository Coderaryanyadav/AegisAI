#!/bin/bash
# Local Legal AI Assistant Startup Script

# Determine project root
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

echo "=========================================================="
echo "⚖️ Starting Local Legal AI Assistant Suite"
echo "=========================================================="

# Find suitable Python 3 (prefer 3.12 or 3.11, fallback to python3)
PYTHON_BIN=""
for py in python3.12 python3.11 python3; do
    if command -v "$py" &>/dev/null; then
        if "$py" -c "import sys; exit(0 if sys.version_info >= (3, 11) and sys.version_info < (3, 15) else 1)" 2>/dev/null; then
            PYTHON_BIN="$py"
            break
        elif [ -z "$PYTHON_BIN" ] && "$py" -c "import sys; exit(0 if sys.version_info >= (3, 11) else 1)" 2>/dev/null; then
            PYTHON_BIN="$py"
        fi
    fi
done

if [ -z "$PYTHON_BIN" ]; then
    echo "[!] Python 3 (3.11+) is not installed or not in PATH."
    exit 1
fi

# Check for Port Collisions (Port 8000 for FastAPI, Port 3000 for Next.js)
$PYTHON_BIN -c "import socket; s = socket.socket(); s.bind(('127.0.0.1', 8000))" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "[!] Error: Port 8000 (FastAPI Backend) is already in use."
    echo "    Please stop any process running on port 8000."
    exit 1
fi

$PYTHON_BIN -c "import socket; s = socket.socket(); s.bind(('127.0.0.1', 3000))" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "[!] Error: Port 3000 (Next.js React Frontend) is already in use."
    echo "    Please stop any process running on port 3000."
    exit 1
fi

# Setup Virtual Environment if not present
if [ ! -d "venv" ]; then
    echo "[*] Creating Python virtual environment ('venv') using $PYTHON_BIN..."
    $PYTHON_BIN -m venv venv
    if [ $? -ne 0 ]; then
        echo "[!] Failed to create virtual environment. Please install python3-venv or verify Python setup."
        exit 1
    fi
    ./venv/bin/pip install --upgrade pip
    echo "[*] Installing dependencies from requirements.txt (this may take a minute)..."
    ./venv/bin/pip install -r requirements.txt -r requirements-dev.txt
    if [ $? -ne 0 ]; then
        echo "[!] Failed to install dependencies. Please check requirements.txt."
        exit 1
    fi
else
    ./venv/bin/pip install -q -r requirements.txt
fi

VENV_PY="$PROJECT_DIR/venv/bin/python"

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

# Check for Local AI Inference Runtime (LM Studio primary, Ollama fallback)
LMSTUDIO_ACTIVE=false
$PYTHON_BIN -c "import socket; s = socket.socket(); s.connect(('127.0.0.1', 1234))" 2>/dev/null
if [ $? -eq 0 ]; then
    LMSTUDIO_ACTIVE=true
    echo "[*] LM Studio Local AI service is active on port 1234."
else
    # Try finding lms CLI
    LMS_BIN=""
    if command -v lms &>/dev/null; then
        LMS_BIN="lms"
    elif [ -f "$HOME/.lmstudio/bin/lms" ]; then
        LMS_BIN="$HOME/.lmstudio/bin/lms"
    fi
    
    if [ -n "$LMS_BIN" ]; then
        echo "[*] LM Studio CLI detected. Starting local server..."
        env -u ELECTRON_RUN_AS_NODE "$LMS_BIN" server start --cors >/dev/null 2>&1
        sleep 2
        $PYTHON_BIN -c "import socket; s = socket.socket(); s.connect(('127.0.0.1', 1234))" 2>/dev/null
        if [ $? -eq 0 ]; then
            LMSTUDIO_ACTIVE=true
            echo "[*] LM Studio local server started successfully on port 1234."
        fi
    fi
fi

if [ "$LMSTUDIO_ACTIVE" = false ]; then
    # Fallback check for Ollama
    $PYTHON_BIN -c "import socket; s = socket.socket(); s.connect(('127.0.0.1', 11434))" 2>/dev/null
    if [ $? -eq 0 ]; then
        echo "[*] Ollama service detected on port 11434."
    else
        echo "----------------------------------------------------------"
        echo "[💡 INFO] LM Studio is recommended for fastest GPU acceleration."
        echo "Ensure LM Studio Local Server is running on port 1234."
        echo "Or run: lms server start --cors"
        echo "----------------------------------------------------------"
    fi
fi

# Ensure data directories exist
mkdir -p data

echo "=========================================================="
echo "[*] Starting AegisAI FastAPI Backend & Next.js Frontend..."
echo "=========================================================="

# Trap to kill background tasks on exit
trap 'kill $(jobs -p)' EXIT

# Launch backend in background
PYTHONPATH=. "$VENV_PY" aegis_backend/main.py &

# Launch Next.js frontend
cd aegis_frontend && npm run dev

