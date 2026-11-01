"""
main.py - Main FastAPI Application for Tulya Bilingual Statutory Auditor.

Reads TULYA_DEPLOY_MODE environment variable:
  - "precomputed" (default on Render free tier): serves pre-built reports only;
    does not import torch, sentence-transformers, or any ML library at startup.
    Upload and live-audit endpoints return HTTP 503 with a clear message.
  - "live" (default locally): full pipeline including PDF ingestion, embedding
    alignment with LaBSE, and optional LLM semantic verification.

Reads CORS_ORIGINS environment variable (comma-separated list of allowed origins).
Falls back to "*" only in live/local mode.
"""

import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

# --- Deploy Mode ---
DEPLOY_MODE = os.environ.get("TULYA_DEPLOY_MODE", "live").strip().lower()
IS_PRECOMPUTED = DEPLOY_MODE == "precomputed"

# --- CORS ---
_raw_origins = os.environ.get("CORS_ORIGINS", "")
if _raw_origins:
    CORS_ORIGINS = [o.strip() for o in _raw_origins.split(",") if o.strip()]
elif IS_PRECOMPUTED:
    # In hosted mode, only allow from Vercel domain set via env; default deny-all
    CORS_ORIGINS = ["*"]  # operator should set CORS_ORIGINS in Render dashboard
else:
    CORS_ORIGINS = ["*"]

# --- Conditional heavy imports ---
if not IS_PRECOMPUTED:
    # Full pipeline routes are included only in live mode
    from backend.app.api.routes import router as api_router
else:
    from backend.app.api.routes_precomputed import router as api_router

app = FastAPI(
    title="Tulya API (तुल्य)",
    description="Evidence-backed bilingual law consistency auditor for Indian legal texts (English & Hindi)",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes are always mounted (precomputed router is lighter)
app.include_router(api_router, prefix="/api")
app.include_router(api_router)  # also at root for backwards compat


@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "tulya-api", "version": "1.0.0"}


@app.get("/healthz")
def healthz():
    """Render health-check endpoint."""
    return {"status": "ok", "mode": DEPLOY_MODE}


# --- Static / SPA serving ---
FRONTEND_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
    "frontend"
)

if os.path.exists(FRONTEND_DIR):
    static_dir = os.path.join(FRONTEND_DIR, "static")
    if os.path.exists(static_dir):
        app.mount("/static", StaticFiles(directory=static_dir), name="static")

    public_dir = os.path.join(FRONTEND_DIR, "public")
    if os.path.exists(public_dir):
        app.mount("/public", StaticFiles(directory=public_dir), name="public")

    @app.get("/")
    def serve_index():
        index_path = os.path.join(FRONTEND_DIR, "index.html")
        if os.path.exists(index_path):
            return FileResponse(index_path)
        return JSONResponse({"message": "Tulya API online. Frontend index not found."})

    @app.get("/app")
    def serve_app():
        app_path = os.path.join(FRONTEND_DIR, "app.html")
        if os.path.exists(app_path):
            return FileResponse(app_path)
        return JSONResponse({"message": "Tulya Workspace UI online."})
