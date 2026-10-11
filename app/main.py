"""
Stelloid Command Center Dashboard API — Main Application

FastAPI app entry point. Mounts all routers, serves the
frontend dashboard, and provides the health check endpoint.
"""

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.routers import (
    channels,
    overview,
    trends,
    channel_distribution,
    channel_performance,
)

app = FastAPI(
    title="Stelloid Command Center API",
    description=(
        "Backend service providing mock analytics data for the "
        "Stelloid Command Center dashboard. Supports brand overview, "
        "revenue trends, channel distribution, and channel performance APIs."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS — allow all origins for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_cache_headers(request: Request, call_next):
    """Add standard Cache-Control headers to API GET endpoints."""
    response = await call_next(request)
    if request.method == "GET" and request.url.path.startswith("/api/v1"):
        response.headers["Cache-Control"] = "public, max-age=60"
    return response


# ---------- Health Check ----------

@app.get(
    "/health",
    tags=["Health"],
    summary="Health check",
    description="Returns a simple health status.",
)
def health_check():
    return {"status": "healthy"}


# ---------- Mount Routers ----------

app.include_router(channels.router)
app.include_router(overview.router)
app.include_router(trends.router)
app.include_router(channel_distribution.router)
app.include_router(channel_performance.router)


# ---------- Frontend ----------

# Resolve absolute path to the frontend directory
_FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"


@app.get("/", include_in_schema=False)
def serve_index():
    """Serve the dashboard index.html at the root URL."""
    return FileResponse(_FRONTEND_DIR / "index.html")


# Mount static files (CSS, JS, SVG) under /frontend
app.mount(
    "/frontend",
    StaticFiles(directory=str(_FRONTEND_DIR)),
    name="frontend",
)
