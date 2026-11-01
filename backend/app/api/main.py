"""
main.py - Main FastAPI Application for Tulya Bilingual Statutory Auditor.
"""

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from backend.app.api.routes import router as api_router

app = FastAPI(
    title="Tulya API (तुल्य)",
    description="Evidence-backed bilingual law consistency auditor for Indian legal texts (English & Hindi)",
    version="1.0.0"
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes under both /api and root prefixes for maximum compatibility
app.include_router(api_router, prefix="/api")
app.include_router(api_router)


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "tulya-api",
        "version": "1.0.0"
    }


# Static and SPA mounting if frontend directory exists
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "frontend")
if os.path.exists(FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=os.path.join(FRONTEND_DIR, "static")), name="static")
    public_dir = os.path.join(FRONTEND_DIR, "public")
    if os.path.exists(public_dir):
        app.mount("/public", StaticFiles(directory=public_dir), name="public")

    @app.get("/")
    def serve_index():
        index_path = os.path.join(FRONTEND_DIR, "index.html")
        if os.path.exists(index_path):
            return FileResponse(index_path)
        return {"message": "Tulya API online. Frontend index not found."}

    @app.get("/app")
    def serve_app():
        app_path = os.path.join(FRONTEND_DIR, "app.html")
        if os.path.exists(app_path):
            return FileResponse(app_path)
        return {"message": "Tulya Workspace UI online."}

