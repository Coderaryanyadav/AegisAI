import os
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
import sys
import uvicorn
import logging
import asyncio
import argparse
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

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

# Setup structured JSON logging
from pythonjsonlogger import jsonlogger
log_handler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter('%(asctime)s %(levelname)s %(name)s %(message)s')
log_handler.setFormatter(formatter)
logging.basicConfig(level=logging.INFO, handlers=[log_handler], force=True)
logger = logging.getLogger("aegis_ai.backend")
# Initialize database schemas
init_db()

ollama_process = None

async def ensure_ollama_runtime():
    """Starts local Ollama daemon if offline and pre-pulls reasoning models."""
    import subprocess
    import shutil
    global ollama_process
    
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
                ollama_process = subprocess.Popen([ollama_path, "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:
                logger.info("Ollama binary not found in common locations. Attempting standard command execute...")
                ollama_process = subprocess.Popen(["ollama", "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
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

async def monitor_ollama_runtime():
    """Watchdog loop to ensure background Ollama remains running during execution."""
    global ollama_process
    while True:
        await asyncio.sleep(10.0)
        # Only supervise if we programmatically started it
        if ollama_process is not None:
            if ollama_process.poll() is not None:
                logger.warning("Programmatically spawned Ollama process terminated unexpectedly. Restarting...")
                ollama_process = None
                await ensure_ollama_runtime()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Schedule automated snapshot every hour
    backup_task = asyncio.create_task(run_backup_scheduler(interval_seconds=3600, retention_limit=5))
    # Spin up background Ollama checks and auto-launcher
    ollama_task = asyncio.create_task(ensure_ollama_runtime())
    # Spin up subprocess watchdog monitor
    watchdog_task = asyncio.create_task(monitor_ollama_runtime())
    yield
    # Clean up background tasks on shutdown
    logger.info("AegisAI backend shutting down. Cleaning up background tasks...")
    backup_task.cancel()
    ollama_task.cancel()
    watchdog_task.cancel()
    
    # Close HTTP connection pool
    try:
        from aegis_backend.core.http_client import close_http_client
        await close_http_client()
        logger.info("Shared HTTP client connection pool closed.")
    except Exception as e:
        logger.warning(f"Error closing HTTP client pool: {e}")

    try:
        await asyncio.gather(backup_task, ollama_task, watchdog_task, return_exceptions=True)
    except Exception as e:
        logger.warning(f"Error during lifespan shutdown cleanup: {e}")

    # Clean up programmatically started Ollama process
    global ollama_process
    if ollama_process:
        logger.info("Terminating programmatically spawned Ollama subprocess...")
        try:
            ollama_process.terminate()
            for _ in range(5):
                if ollama_process.poll() is not None:
                    break
                await asyncio.sleep(1.0)
            if ollama_process.poll() is None:
                logger.warning("Ollama process did not terminate. Killing process...")
                ollama_process.kill()
                ollama_process.wait()
            logger.info("Ollama subprocess cleaned up successfully.")
        except Exception as e:
            logger.error(f"Failed to clean up Ollama subprocess: {e}")

test_mode = os.environ.get("AEGIS_TEST_MODE") == "true"
app = FastAPI(
    title="AegisAI Offline Legal Suite",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if test_mode else None,
    redoc_url="/redoc" if test_mode else None,
    openapi_url="/openapi.json" if test_mode else None
)

# OpenTelemetry Instrumentation setup
if os.environ.get("AEGIS_OTEL_ENABLED") == "true":
    logger.info("Initializing OpenTelemetry Tracing...")
    
    # OpenTelemetry Imports
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
    from opentelemetry.sdk.resources import Resource
    
    resource = Resource(attributes={"service.name": "aegis_backend"})
    provider = TracerProvider(resource=resource)
    processor = BatchSpanProcessor(OTLPSpanExporter())
    provider.add_span_processor(processor)
    trace.set_tracer_provider(provider)
    FastAPIInstrumentor.instrument_app(app)
    
    from aegis_backend.database import engine
    SQLAlchemyInstrumentor().instrument(
        engine=engine,
        enable_commenter=True,
        commenter_options={}
    )

# Allow CORS dynamically from environment, defaulting to local Electron/Next.js frontend
cors_origins_env = os.environ.get("AEGIS_CORS_ORIGINS")
if cors_origins_env:
    origins = [o.strip() for o in cors_origins_env.split(",") if o.strip()]
else:
    origins = ["http://localhost:3000", "http://127.0.0.1:3000"]

app.add_middleware(GZipMiddleware, minimum_size=1000)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
)

@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "connect-src 'self' http://localhost:* http://127.0.0.1:* ws://localhost:* ws://127.0.0.1:*; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
        "style-src 'self' 'unsafe-inline'; "
        "font-src 'self' data:; "
        "img-src 'self' data: blob:;"
    )
    return response


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

for r in [
    auth_router, clients_router, matters_router, schedules_router,
    documents_router, research_router, billing_router, backup_router,
    system_router, analytics_router, annotations_router
]:
    app.include_router(r, prefix="/api/v1")

if __name__ == "__main__":
    import multiprocessing
    multiprocessing.freeze_support()
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", 8000)))
    args, unknown = parser.parse_known_args()
    uvicorn.run(app, host="0.0.0.0", port=args.port)
