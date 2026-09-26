"""
SnapAI Edge - Backend Entry Point
FastAPI application with unified multi-model AI routing, providers, and startup validation.
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import os
import time
from contextlib import asynccontextmanager
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from database.db import init_db
from api import ai as ai_api
from api import vision, documents, rag, hardware, models, benchmark, privacy, voice
from ai.manager import ai_manager
from ai.router import router as ai_router
from ai.types import ProviderType
from ai.providers.local_provider import LocalProvider


async def print_environment_validation():
    """Print the startup environment validation banner specified in Section 29."""
    openai_key = os.getenv("OPENAI_API_KEY", "").strip()
    gemini_key = (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or "").strip()

    openai_str = "✓ Configured" if openai_key else "✗ Not configured"
    gemini_str = "✓ Configured" if gemini_key else "✗ Not configured"

    ollama_ok = await ai_router.is_ollama_available()
    ollama_str = "✓ Running" if ollama_ok else "✗ Not running"

    installed_models = await ai_router.get_installed_ollama_models() if ollama_ok else []
    models_count = len(installed_models)

    local_p = ai_manager.get_provider(ProviderType.LOCAL.value)
    hw = local_p.detect_hardware() if local_p else {}
    if hw.get("is_snapdragon"):
        snapdragon_str = "Detected"
    elif hw.get("snapdragon_status") == "UNAVAILABLE":
        snapdragon_str = "Not detected"
    else:
        snapdragon_str = "Unknown"

    online = await ai_router.is_online()
    network_str = "Online" if online else "Offline"

    banner = f"""
============================================================
                  SnapAI Edge AI System
============================================================
OpenAI:       {openai_str}
Gemini:       {gemini_str}
Ollama:       {ollama_str}
Local Models: {models_count} available ({', '.join(installed_models) if installed_models else 'none'})
Snapdragon:   {snapdragon_str} ({hw.get('verified_device', 'CPU')})
Network:      {network_str}
============================================================
"""
    print(banner)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup + shutdown."""
    print("[START] SnapAI Edge backend starting...")
    init_db()
    os.makedirs(os.getenv("UPLOAD_DIR", "./uploads"), exist_ok=True)
    print("[OK] Database initialized")
    print("[OK] Upload directory ready")

    # Run non-blocking startup validation banner
    try:
        await print_environment_validation()
    except Exception as e:
        print(f"[WARN] Startup validation notice: {e}")

    yield
    print("[STOP] SnapAI Edge backend shutting down...")


app = FastAPI(
    title="SnapAI Edge API",
    description="Multi-Model AI Integration - Snapdragon AI Lab Challenge",
    version="2.0.0",
    lifespan=lifespan,
)

# ─── CORS ─────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Request timing middleware ─────────────────────────────
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    process_ms = round((time.time() - start) * 1000, 2)
    response.headers["X-Process-Time-Ms"] = str(process_ms)
    return response


# ─── Global error handler ─────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc),
            "path": str(request.url),
        },
    )


# ─── Routers ──────────────────────────────────────────────
app.include_router(ai_api.router,     prefix="/api/ai",        tags=["Unified AI"])
app.include_router(vision.router,     prefix="/api/ai",        tags=["Vision"])
app.include_router(voice.router,      prefix="/api/ai",        tags=["Voice"])
app.include_router(documents.router,  prefix="/api/documents", tags=["Documents"])
app.include_router(rag.router,        prefix="/api/rag",       tags=["RAG"])
app.include_router(hardware.router,   prefix="/api/device",    tags=["Hardware"])
app.include_router(models.router,     prefix="/api/models",    tags=["Models"])
app.include_router(benchmark.router,  prefix="/api/benchmark", tags=["Benchmark"])
app.include_router(privacy.router,    prefix="/api/privacy",   tags=["Privacy"])


# ─── Health check ─────────────────────────────────────────
@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "app": "SnapAI Edge",
        "version": "2.0.0",
        "interface": "unified_multi_model",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=os.getenv("BACKEND_HOST", "127.0.0.1"),
        port=int(os.getenv("BACKEND_PORT", 8000)),
        reload=True,
        log_level="info",
    )
