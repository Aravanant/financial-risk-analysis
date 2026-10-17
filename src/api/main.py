"""RiskLens AI - Production FastAPI Backend Application.

Configures:
1. Lifespan event for startup database verification.
2. CORS middleware using whitelisted origins from configuration.
3. Structured JSON logging and sanitized exception handlers (no trace leaks).
4. Analytical REST routers for portfolio KPIs, dimensions, haircuts, and applications.
5. Interactive OpenAPI/Swagger documentation at /docs and ReDoc at /redoc.
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import settings
from .database import check_db_health
from .routers import (
    health,
    overview,
    channels,
    loan_purposes,
    haircut,
    risk_tiers,
    data_quality,
    applications,
    servicing_demo
)

logger = logging.getLogger("risklens.api")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event handler verifying database readiness on startup."""
    logger.info("Initializing RiskLens AI Analytics API...")
    health_status = check_db_health()
    if health_status.get("status") == "healthy":
        logger.info(
            f"Database connected and verified: {settings.DB_PATH} "
            f"({health_status.get('database_size_bytes', 0):,} bytes)"
        )
    else:
        logger.warning(f"Database health check returned non-healthy state: {health_status}")
    yield
    logger.info("RiskLens AI Analytics API shut down cleanly.")


app = FastAPI(
    title=settings.APP_TITLE,
    version=settings.APP_VERSION,
    description=settings.APP_DESCRIPTION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Configure CORS middleware with whitelisted origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "OPTIONS"],
    allow_headers=["*"],
)


# Global exception handler preventing internal filesystem and stack trace leakage
@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception on {request.method} {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "An internal server error occurred while processing the request.",
            "error_code": "INTERNAL_ERROR"
        }
    )


# 1. Root and Health Endpoints
app.include_router(health.router)
app.include_router(health.router, prefix=settings.API_V1_PREFIX)

# 2. Analytical API v1 Routers
app.include_router(overview.router, prefix=settings.API_V1_PREFIX)
app.include_router(channels.router, prefix=settings.API_V1_PREFIX)
app.include_router(loan_purposes.router, prefix=settings.API_V1_PREFIX)
app.include_router(haircut.router, prefix=settings.API_V1_PREFIX)
app.include_router(risk_tiers.router, prefix=settings.API_V1_PREFIX)
app.include_router(data_quality.router, prefix=settings.API_V1_PREFIX)
app.include_router(applications.router, prefix=settings.API_V1_PREFIX)
app.include_router(servicing_demo.router, prefix=settings.API_V1_PREFIX)


@app.get("/", include_in_schema=False)
def root():
    """Root redirect / information endpoint."""
    return {
        "name": settings.APP_TITLE,
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "health": "/health",
        "api_v1": settings.API_V1_PREFIX
    }
