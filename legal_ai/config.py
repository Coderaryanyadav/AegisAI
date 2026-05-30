import os
import warnings

# Suppress all deprecation and runtime warnings globally at runtime
warnings.simplefilter("ignore")

from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

import sys

# Base directories
BASE_DIR = Path(__file__).resolve().parent.parent

if getattr(sys, 'frozen', False):
    # Packaged production mode: store data persistently in user's home directory
    USER_DIR = Path(os.path.expanduser("~")) / ".aegis_legal_ai"
else:
    # Development mode: store data in the project workspace
    USER_DIR = BASE_DIR

DATA_DIR = USER_DIR / "data"
ENCRYPTED_FILES_DIR = DATA_DIR / "encrypted_files"
CHROMA_DB_DIR = DATA_DIR / "chromadb"

# Create directories if they do not exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
ENCRYPTED_FILES_DIR.mkdir(parents=True, exist_ok=True)
CHROMA_DB_DIR.mkdir(parents=True, exist_ok=True)

# Configuration Variables
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DATA_DIR}/legal_assistant.db")
SECRET_KEY = os.getenv("SECRET_KEY", "SUPER_SECRET_LEGAL_AI_DEVELOPMENT_KEY_CHANGE_THIS_IN_PRODUCTION")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "120"))

# AES-256 Fernet Encryption Key for files (Must be 32 url-safe base64-encoded bytes)
# If not provided, we will dynamically generate one and warning the user (not ideal for persistence if regenerated)
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY", "")

# Ollama settings
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
DEFAULT_LLM_MODEL = os.getenv("OLLAMA_LLM_MODEL", "qwen3:8b")

# Dynamically resolve available model
OLLAMA_LLM_MODEL = DEFAULT_LLM_MODEL
try:
    import requests
    response = requests.get(f"{OLLAMA_BASE_URL.rstrip('/')}/api/tags", timeout=2)
    if response.status_code == 200:
        models = [m["name"] for m in response.json().get("models", [])]
        if DEFAULT_LLM_MODEL not in models and len(models) > 0:
            # Check if there is an exact match without tags (e.g. qwen2.5:7b-instruct vs qwen2.5:7b-instruct:latest)
            matched = False
            for m in models:
                if m.startswith(DEFAULT_LLM_MODEL):
                    OLLAMA_LLM_MODEL = m
                    matched = True
                    break
            if not matched:
                # Fall back to first available model
                OLLAMA_LLM_MODEL = models[0]
                print(f"[!] Target model '{DEFAULT_LLM_MODEL}' not found locally in Ollama.")
                print(f"[*] Falling back to available model: '{OLLAMA_LLM_MODEL}'")
except Exception:
    # If connection fails, keep default model config
    pass

# Embedded parameters
EMBEDDINGS_MODEL_NAME = os.getenv("EMBEDDINGS_MODEL_NAME", "all-MiniLM-L6-v2")
