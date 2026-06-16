"""
Carbon Footprint Tracker — FastAPI Application Entry Point.

Features:
- CORS with configurable origins
- Security headers middleware
- Rate limiting (slowapi)
- Auto OpenAPI documentation
- Health check endpoint
"""
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from app.database.session import create_tables
from app.routers.auth import router as auth_router
from app.routers.activities import router as activities_router
from app.routers.dashboard import dashboard_router, insights_router


# ─── Rate Limiter ─────────────────────────────────────────────────────────────
limiter = Limiter(key_func=get_remote_address)


# ─── Lifespan ─────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """Initialize database on startup."""
    create_tables()
    yield


# ─── App Factory ──────────────────────────────────────────────────────────────
app = FastAPI(
    title="🌿 Carbon Footprint Tracker API",
    description=(
        "Track, understand, and reduce your personal carbon footprint. "
        "Powered by IPCC AR6 / EPA 2023 emission factors."
    ),
    version="1.0.0",
    contact={"name": "Carbon Tracker", "email": "support@carbontracker.io"},
    license_info={"name": "MIT"},
    lifespan=lifespan,
)

# ─── State ────────────────────────────────────────────────────────────────────
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ─── CORS ─────────────────────────────────────────────────────────────────────
ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:5500",
    "http://127.0.0.1:5500",
    "http://localhost:8080",
    "null",  # file:// for local dev
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


# ─── Security Headers Middleware ──────────────────────────────────────────────
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), camera=()"
    return response


# ─── Routers ──────────────────────────────────────────────────────────────────
API_PREFIX = "/api/v1"
app.include_router(auth_router, prefix=API_PREFIX)
app.include_router(activities_router, prefix=API_PREFIX)
app.include_router(dashboard_router, prefix=API_PREFIX)
app.include_router(insights_router, prefix=API_PREFIX)


# ─── Health Check ─────────────────────────────────────────────────────────────
@app.get("/health", tags=["System"], summary="Health check endpoint")
@limiter.limit("30/minute")
async def health_check(request: Request) -> JSONResponse:
    """Returns service health status."""
    return JSONResponse({"status": "healthy", "version": "1.0.0"})


@app.get("/", tags=["System"], summary="API root")
async def root() -> dict:
    return {
        "message": "🌿 Carbon Footprint Tracker API",
        "docs": "/docs",
        "health": "/health",
    }
