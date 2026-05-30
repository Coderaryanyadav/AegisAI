#!/bin/bash
# Local Legal AI Assistant Startup Script

# Determine project root
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

echo "=========================================================="
echo "⚖️ Starting Local Legal AI Assistant Suite"
echo "=========================================================="

# Activate Virtual Environment
if [ -d "venv" ]; then
    source venv/bin/activate
else
    echo "[!] Virtual environment 'venv' not found. Please create it or verify workspace."
    exit 1
fi

# Ensure data directories exist
mkdir -p data/encrypted_files data/chromadb

# Start FastAPI Backend in the background
echo "[*] Starting FastAPI Backend on http://127.0.0.1:8000..."
python3 -m uvicorn legal_ai.main:app --host 127.0.0.1 --port 8000 > backend.log 2>&1 &
BACKEND_PID=$!

# Trap signals to clean up the backend server on exit
cleanup() {
    echo ""
    echo "[*] Stopping FastAPI Backend (PID: $BACKEND_PID)..."
    kill $BACKEND_PID 2>/dev/null
    exit 0
}
trap cleanup SIGINT SIGTERM EXIT

# Give backend a moment to spin up and seed database
sleep 2

# Check if backend successfully started
if ! kill -0 $BACKEND_PID 2>/dev/null; then
    echo "[!] FastAPI Backend failed to start. Check backend.log for details:"
    cat backend.log | tail -n 20
    exit 1
fi

echo "[*] Backend running successfully (PID: $BACKEND_PID)."
echo "[*] Launching Streamlit Desktop UI on http://127.0.0.1:8501..."
echo "----------------------------------------------------------"

# Launch Streamlit Frontend in the foreground (blocks here)
python3 -m streamlit run legal_ai/app/frontend.py --server.port 8501 --server.address 127.0.0.1

# The cleanup trap will run when Streamlit exits
