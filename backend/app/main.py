"""
Support Intake AI — FastAPI Application Entry Point
====================================================
Receives uploaded files, validates them for security, and routes them
through the agentic workflow to produce structured support ticket analysis.
"""

import logging
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

import mimetypes

# Fix Windows registry MIME type bug for JavaScript module scripts
mimetypes.add_type('application/javascript', '.js')

from app.api.routes import tickets

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(name)s | %(message)s")
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
#  App and security config
# ─────────────────────────────────────────────────────────────────────────────
ALLOWED_ORIGINS = [
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "http://localhost:5500",
    "http://127.0.0.1:5500",
    "http://localhost:5501",
    "http://127.0.0.1:5501",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "null",
]

app = FastAPI(
    title="Support Intake AI",
    description="Agentic system for intelligent support ticket analysis",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "OPTIONS"],
    allow_headers=["Content-Type", "Accept"],
)

# ─────────────────────────────────────────────────────────────────────────────
#  API Routes Mounting
# ─────────────────────────────────────────────────────────────────────────────
app.include_router(tickets.router)

# ─────────────────────────────────────────────────────────────────────────────
#  Static frontend — served at /ui/  (root / redirects here)
# ─────────────────────────────────────────────────────────────────────────────
_FRONTEND_DIR = Path(__file__).parent.parent.parent / "frontend"

if _FRONTEND_DIR.exists():
    # html=True: serves index.html for directory requests and 404s
    app.mount("/ui", StaticFiles(directory=str(_FRONTEND_DIR), html=True), name="frontend")


@app.get("/", include_in_schema=False)
async def serve_frontend():
    """Redirect root to the frontend UI at /ui/."""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/ui/")


@app.get("/health", tags=["health"])
async def health():
    return {"status": "ok"}
