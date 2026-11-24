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

ai_subprocess = None

async def ensure_local_ai_runtime():
    """Starts local LM Studio (primary) or Ollama (fallback) daemon if offline."""
    import subprocess
    import shutil
    global ai_subprocess
    
    # 1. Check if LM Studio is already running on port 1234
    if await OllamaService.is_lmstudio_running():
        models = await OllamaService.get_available_models()
        logger.info(f"LM Studio local AI service is online on port 1234. Active models: {models}")
        return

    # 2. Try starting LM Studio via lms CLI
    clean_env = dict(os.environ)
    clean_env.pop("ELECTRON_RUN_AS_NODE", None)
    lms_path = shutil.which("lms")
    if not lms_path:
        home_lms = os.path.expanduser("~/.lmstudio/bin/lms")
        if os.path.exists(home_lms):
            lms_path = home_lms

    if lms_path:
        logger.info(f"Attempting to launch LM Studio server via CLI: {lms_path} server start --cors")
        try:
            subprocess.run([lms_path, "server", "start", "--cors"], env=clean_env, capture_output=True, timeout=10)
        except Exception as e:
            logger.warning(f"Failed to start LM Studio server via lms: {e}")

        # Wait for LM Studio to respond
        for _ in range(6):
            await asyncio.sleep(1.0)
            if await OllamaService.is_lmstudio_running():
                models = await OllamaService.get_available_models()
                logger.info(f"LM Studio came online successfully! Available models: {models}")
                return

    # 3. Fallback: Check if Ollama is running or can be started
    is_ollama = await OllamaService.is_ollama_running()
    if not is_ollama:
        logger.info("LM Studio not found. Checking Ollama fallback...")
        try:
            ollama_path = shutil.which("ollama")
            if not ollama_path and sys.platform == "darwin":
                for path in ["/Applications/Ollama.app/Contents/Resources/ollama", "/usr/local/bin/ollama", "/opt/homebrew/bin/ollama"]:
                    if os.path.exists(path):
                        ollama_path = path
                        break
            if ollama_path:
                logger.info(f"Spawning background Ollama daemon: {ollama_path} serve")
                ai_subprocess = subprocess.Popen([ollama_path, "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                for _ in range(8):
                    await asyncio.sleep(1.0)
                    if await OllamaService.is_ollama_running():
                        logger.info("Ollama fallback service online.")
                        break
        except Exception as e:
            logger.debug(f"Ollama startup attempt: {e}")

    models = await OllamaService.get_available_models()
    if models:
        logger.info(f"Local AI inference runtime initialized with models: {models}")
    else:
        logger.warning("No local models detected. Please launch LM Studio and load a model.")

async def monitor_local_ai_runtime():
    """Watchdog loop to ensure programmatically spawned AI service remains running."""
    global ai_subprocess
    while True:
        await asyncio.sleep(15.0)
        if ai_subprocess is not None and ai_subprocess.poll() is not None:
            logger.warning("Programmatically spawned AI process terminated unexpectedly. Restarting...")
            ai_subprocess = None
            await ensure_local_ai_runtime()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Schedule automated snapshot every hour
    backup_task = asyncio.create_task(run_backup_scheduler(interval_seconds=3600, retention_limit=5))
    # Spin up background Local AI runtime checks (LM Studio / Ollama)
    ai_task = asyncio.create_task(ensure_local_ai_runtime())
    # Spin up subprocess watchdog monitor
    watchdog_task = asyncio.create_task(monitor_local_ai_runtime())
    yield
    # Clean up background tasks on shutdown
    logger.info("AegisAI backend shutting down. Cleaning up background tasks...")
    backup_task.cancel()
    ai_task.cancel()
    watchdog_task.cancel()
    
    # Close HTTP connection pool
    try:
        from aegis_backend.core.http_client import close_http_client
        await close_http_client()
        logger.info("Shared HTTP client connection pool closed.")
    except Exception as e:
        logger.warning(f"Error closing HTTP client pool: {e}")

    try:
        await asyncio.gather(backup_task, ai_task, watchdog_task, return_exceptions=True)
    except Exception as e:
        logger.warning(f"Error during lifespan shutdown cleanup: {e}")

    # Clean up programmatically started subprocess if any
    global ai_subprocess
    if ai_subprocess:
        logger.info("Terminating programmatically spawned AI subprocess...")
        try:
            ai_subprocess.terminate()
            ai_subprocess.wait(timeout=5)
            logger.info("AI subprocess cleaned up successfully.")
        except Exception as e:
            logger.error(f"Failed to clean up AI subprocess: {e}")

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

# Allow CORS dynamically from environment, defaulting to local Electron/Next.js frontend on any local port
cors_origins_env = os.environ.get("AEGIS_CORS_ORIGINS")
if cors_origins_env:
    origins = [o.strip() for o in cors_origins_env.split(",") if o.strip()]
else:
    origins = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
        "http://localhost:3002",
        "http://127.0.0.1:3002",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "app://.",
        "file://",
    ]

app.add_middleware(GZipMiddleware, minimum_size=1000)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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

@app.get("/health")
@app.get("/api/health")
async def root_health_check():
    return {"status": "healthy"}

for r in [
    auth_router, clients_router, matters_router, schedules_router,
    documents_router, research_router, billing_router, backup_router,
    system_router, analytics_router, annotations_router
]:
    app.include_router(r, prefix="/api/v1")
    app.include_router(r, prefix="/api")

if __name__ == "__main__":
    import multiprocessing
    multiprocessing.freeze_support()
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", 8000)))
    args, unknown = parser.parse_known_args()
    uvicorn.run(app, host="0.0.0.0", port=args.port)
