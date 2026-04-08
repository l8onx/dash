import logging
import os

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .config import settings
from .database import Base, engine
from .middleware.auth import PSKMiddleware
from .routers import auth, health, reports, schema_route

logging.basicConfig(
    level=logging.INFO,
    format="[dash] %(levelname)s %(message)s",
)
logger = logging.getLogger("dash")

# ── Create tables ─────────────────────────────────────────────────────────────
Base.metadata.create_all(bind=engine)

# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Dash",
    version="2.0.0",
    description="OpenClaw Agent Report Portal",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# ── PSK middleware (runs before routing) ──────────────────────────────────────
app.add_middleware(PSKMiddleware)

# ── API routers ───────────────────────────────────────────────────────────────
app.include_router(health.router)
app.include_router(schema_route.router)
app.include_router(auth.router)
app.include_router(reports.router)

# ── SPA / legacy HTML routes ──────────────────────────────────────────────────
# The public/ directory contains the legacy HTML until the React/Vite frontend
# replaces it in the next session.
# Resolve public/ relative to the package dir — one level up from app/ to reach /app/public/
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_PUBLIC_DIR = os.path.join(_REPO_ROOT, "public")


def _html(filename: str) -> FileResponse:
    return FileResponse(os.path.join(_PUBLIC_DIR, filename))


@app.get("/login")
def serve_login():
    return _html("login.html")


@app.get("/reports/{report_id}")
def serve_report(report_id: str):
    return _html("report.html")


@app.get("/")
def serve_index():
    return _html("index.html")


# Mount remaining static assets (JS, CSS, etc.)
if os.path.isdir(_PUBLIC_DIR):
    app.mount("/", StaticFiles(directory=_PUBLIC_DIR, html=True), name="static")

# ── Startup log ───────────────────────────────────────────────────────────────
@app.on_event("startup")
def _startup():
    if not settings.DASH_PSK:
        logger.warning("⚠️  DASH_PSK not set — authentication disabled.")
    else:
        logger.info("🔒 PSK authentication enabled (365-day cookie)")
    logger.info("🚀 Dash Portal v2.0.0 starting on port %s", settings.PORT)
    logger.info("🌐 DASH_URL: %s", settings.DASH_URL)
    logger.info("📁 DATA_DIR: %s", settings.DATA_DIR)
