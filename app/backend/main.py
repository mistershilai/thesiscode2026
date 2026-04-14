"""
FastAPI application for Botswana Antimicrobial Supply Chain Optimization.
"""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from fastapi import Request
from fastapi.responses import JSONResponse

from .core.data_loader import app_data
from .core.auth import init_db, verify_token
from .api.routes import router
from .api.auth_routes import auth_router

# Paths that don't require authentication
PUBLIC_PATHS = {"/api/auth/login", "/api/health", "/docs", "/redoc", "/openapi.json"}


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: init auth DB + load data
    init_db()
    print("Loading data...")
    app_data.load()
    print(f"Data loaded: {app_data.get_facility_summary()['total_facilities']} facilities")
    yield
    # Shutdown: nothing to clean up


app = FastAPI(
    title="Kaelo",
    description="Antimicrobial supply chain optimization for Botswana health facilities",
    version="1.0.0",
    lifespan=lifespan,
)

_cors_origins = os.environ.get(
    "CORS_ORIGINS", "http://localhost:5173,http://localhost:3000"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(router)


@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    path = request.url.path

    # Allow public paths, static assets, and CORS preflight
    if (
        path in PUBLIC_PATHS
        or path.startswith("/assets")
        or path.startswith("/logos")
        or not path.startswith("/api/")
        or request.method == "OPTIONS"
    ):
        return await call_next(request)

    # Check JWT
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return JSONResponse(status_code=401, content={"detail": "Not authenticated"})

    token = auth_header[7:]
    if not verify_token(token):
        return JSONResponse(status_code=401, content={"detail": "Invalid or expired token"})

    return await call_next(request)

# In production, serve the built frontend from the backend
_static_dir = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")
if os.path.isdir(_static_dir):
    from fastapi.staticfiles import StaticFiles
    from fastapi.responses import FileResponse

    # Serve static assets first (JS, CSS, images)
    _assets_dir = os.path.join(_static_dir, "assets")
    if os.path.isdir(_assets_dir):
        app.mount("/assets", StaticFiles(directory=_assets_dir), name="assets")

    # SPA fallback — any non-API route serves index.html
    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        file_path = os.path.join(_static_dir, full_path)
        if os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(_static_dir, "index.html"))
