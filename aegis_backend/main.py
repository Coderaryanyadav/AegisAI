import os
import sys
import uvicorn
import logging
import asyncio
import argparse
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Dynamic resolution of parent directories to support compiled packaging
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from aegis_backend.database import init_db, AEGIS_DIR
from aegis_backend.backup_manager import run_backup_scheduler
from aegis_backend.ollama_service import OllamaService

# Setup loggers
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("aegis_ai.backend")

# Initialize database schemas
init_db()

async def ensure_ollama_runtime():
    """Starts local Ollama daemon if offline and pre-pulls reasoning models."""
    import subprocess
    import shutil
    
    # 1. Check if Ollama is running
    is_running = await OllamaService.is_ollama_running()
    if not is_running:
        logger.info("Ollama is not running. Attempting to start local Ollama service...")
        try:
            ollama_path = shutil.which("ollama")
            if not ollama_path:
                if sys.platform == "darwin":
                    for path in ["/Applications/Ollama.app/Contents/Resources/ollama", "/usr/local/bin/ollama"]:
                        if os.path.exists(path):
                            ollama_path = path
                            break
                elif sys.platform == "win32":
                    local_app_data = os.environ.get("LOCALAPPDATA", "")
                    win_path = os.path.join(local_app_data, "Programs", "Ollama", "ollama.exe")
                    if os.path.exists(win_path):
                        ollama_path = win_path

            if ollama_path:
                logger.info(f"Spawning background Ollama daemon programmatically: {ollama_path} serve")
                subprocess.Popen([ollama_path, "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:
                logger.info("Ollama binary not found in common locations. Attempting standard command execute...")
                subprocess.Popen(["ollama", "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as e:
            logger.error(f"Failed to start Ollama daemon automatically: {e}")

        # 2. Wait up to 12 seconds for Ollama to start responding
        for _ in range(12):
            await asyncio.sleep(1.0)
            if await OllamaService.is_ollama_running():
                logger.info("Ollama service came online successfully.")
                break
    else:
        logger.info("Ollama service is already online.")

    # 3. Check and pull mistral:latest if missing, and auto-register offline model bundle if aegis-default is missing
    if await OllamaService.is_ollama_running():
        models = await OllamaService.get_available_models()
        
        # Auto-register local bundled model 'aegis-default'
        if not any("aegis-default" in m for m in models):
            logger.info("Aegis-default model is missing from Ollama. Auto-registering from offline bundle...")
            if hasattr(sys, '_MEIPASS'):
                bundle_dir = os.path.join(sys._MEIPASS, "aegis_backend", "model_bundle")
            else:
                bundle_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "model_bundle")
            modelfile_path = os.path.join(bundle_dir, "Modelfile")
            if os.path.exists(modelfile_path):
                try:
                    subprocess.Popen(["ollama", "create", "aegis-default", "-f", modelfile_path],
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    logger.info("Successfully initiated offline model creation for 'aegis-default'.")
                except Exception as e:
                    logger.error(f"Failed to auto-register bundled model: {e}")
            else:
                logger.warning(f"Offline model bundle Modelfile not found at: {modelfile_path}")

        target_model = "mistral:latest"
        has_model = any(target_model in m or "deepseek-r1" in m for m in models)
        if not has_model:
            logger.info(f"Target model '{target_model}' is not present in local list: {models}. Initiating background pull...")
            asyncio.create_task(OllamaService.pull_model(target_model))
        else:
            logger.info(f"Target model '{target_model}' is already present. Ready for local queries.")
    else:
        logger.warning("Could not establish connection to Ollama. Automatic model pre-pull skipped.")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Schedule automated snapshot every hour
    backup_task = asyncio.create_task(run_backup_scheduler(interval_seconds=3600, retention_limit=5))
    # Spin up background Ollama checks and auto-launcher
    ollama_task = asyncio.create_task(ensure_ollama_runtime())
    yield
    # Clean up background tasks on shutdown
    logger.info("AegisAI backend shutting down. Cleaning up background tasks...")
    backup_task.cancel()
    ollama_task.cancel()
    try:
        await asyncio.gather(backup_task, ollama_task, return_exceptions=True)
    except Exception as e:
        logger.warning(f"Error during lifespan shutdown cleanup: {e}")

app = FastAPI(
    title="AegisAI Offline Legal Suite",
    version="1.0.0",
    lifespan=lifespan,
    docs_url=None,
    redoc_url=None,
    openapi_url=None
)

# Allow CORS strictly for local Electron/Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import and register routers
from aegis_backend.routers.auth import router as auth_router
from aegis_backend.routers.clients import router as clients_router
from aegis_backend.routers.matters import router as matters_router
from aegis_backend.routers.schedules import router as schedules_router
from aegis_backend.routers.documents import router as documents_router
from aegis_backend.routers.research import router as research_router
from aegis_backend.routers.billing import router as billing_router
from aegis_backend.routers.backup import router as backup_router
from aegis_backend.routers.system import router as system_router
from aegis_backend.routers.analytics import router as analytics_router
from aegis_backend.routers.annotations import router as annotations_router

app.include_router(auth_router)
app.include_router(clients_router)
app.include_router(matters_router)
app.include_router(schedules_router)
app.include_router(documents_router)
app.include_router(research_router)
app.include_router(billing_router)
app.include_router(backup_router)
app.include_router(system_router)
app.include_router(analytics_router)
app.include_router(annotations_router)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", 8000)))
    args, unknown = parser.parse_known_args()
    uvicorn.run(app, host="0.0.0.0", port=args.port)
