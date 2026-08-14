"""OncoVision AI Backend — application entry point.

Phase 1: Backend foundation only. No database, authentication, prediction,
or TensorFlow integration is implemented in this phase.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.constants.app import API_V1_PREFIX
from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.lifecycle.shutdown import run_shutdown
from app.lifecycle.startup import run_startup
from app.middleware.logging import LoggingMiddleware
from app.middleware.metrics import RequestMetricsMiddleware
from app.middleware.process_time import ProcessTimeMiddleware
from app.middleware.request_id import RequestIDMiddleware
from app.middleware.security_headers import SecurityHeadersMiddleware
from app.utils.response import success_response

DESCRIPTION = "Enterprise AI Medical Platform Backend"

TAGS_METADATA = [
    {"name": "System", "description": "Application and runtime system information."},
    {"name": "Health", "description": "Service health check endpoints."},
    {"name": "Authentication", "description": "Registration, login, and token management."},
    {"name": "Predictions", "description": "Histopathology image prediction requests."},
    {
        "name": "Prediction History",
        "description": "Retrieval of the authenticated user's stored prediction history.",
    },
    {"name": "Reports", "description": "Prediction analytics, CSV export, and PDF export."},
    {
        "name": "Administration",
        "description": (
            "Administrative user management, prediction/history oversight, and "
            "system status. Every endpoint requires administrator authorization."
        ),
    },
    {
        "name": "Monitoring",
        "description": (
            "Aggregated operational monitoring: application health, database "
            "connectivity, AI Runtime Manager health, and per-model availability. "
            "Requires administrator authorization."
        ),
    },
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application startup and shutdown using FastAPI's lifespan API."""
    await run_startup()
    yield
    await run_shutdown()


def create_application() -> FastAPI:
    """Construct and configure the FastAPI application instance."""
    app = FastAPI(
        title="OncoVision AI Backend API",
        description=DESCRIPTION,
        version=settings.APP_VERSION,
        openapi_tags=TAGS_METADATA,
        lifespan=lifespan,
    )

    # Middleware order matters: the last added middleware runs first on the
    # request path and last on the response path.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(LoggingMiddleware)
    app.add_middleware(RequestMetricsMiddleware)
    app.add_middleware(ProcessTimeMiddleware)
    app.add_middleware(RequestIDMiddleware)

    register_exception_handlers(app)

    app.include_router(api_router, prefix=API_V1_PREFIX)

    return app


app = create_application()


@app.get("/", tags=["System"], summary="Root")
async def root():
    """Return basic application metadata and the health endpoint URL."""
    return success_response(
        data={
            "name": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "environment": settings.APP_ENV,
            "health_endpoint": f"{API_V1_PREFIX}/health",
        },
        message="Welcome to OncoVision AI Backend API.",
    )
