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

python3 -c "import socket; s = socket.socket(); s.bind(('127.0.0.1', 8501))" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "[!] Error: Port 8501 (Streamlit Frontend) is already in use."
    echo "    Please stop any process running on port 8501."
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

# Check for Ollama Setup
if command -v ollama &>/dev/null; then
    echo "[*] Ollama CLI detected."
    # Check if service is active
    python3 -c "import socket; s = socket.socket(); s.connect(('127.0.0.1', 11434))" 2>/dev/null
    if [ $? -eq 0 ]; then
        echo "[*] Ollama service is active."
        # Check if model is pulled
        if ollama list | grep -q "qwen3:8b"; then
            echo "[*] Found qwen3:8b local model."
        else
            echo "----------------------------------------------------------"
            echo "[⚠️ WARNING] Local model 'qwen3:8b' not found in Ollama."
            echo "We recommend running this command in another terminal:"
            echo "    ollama pull qwen3:8b"
            echo "----------------------------------------------------------"
        fi
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
    echo "Once installed, pull the model by running:"
    echo "    ollama pull qwen3:8b"
    echo "----------------------------------------------------------"
fi

# Ensure data directories exist
mkdir -p data/encrypted_files data/chromadb

# Launch Standalone Desktop Application
echo "[*] Launching Aegis Legal AI Standalone Desktop Application..."
echo "----------------------------------------------------------"
python3 desktop_app.py

# The cleanup trap will run when Streamlit exits
