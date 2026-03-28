# File: app/main.py
"""FastAPI application factory.

Creates and configures the ASGI application with all routers
and manages database engine lifecycle.
"""
from contextlib import asynccontextmanager
import logging
from time import perf_counter
from typing import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.database import get_engine
from app.core.logging import configure_logging
from app.routers import health_router, diagnosis_router, knowledge_router, tasks_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan manager.

    Handles startup and shutdown events:
    - Startup: Validate runtime dependencies are ready
    - Shutdown: Dispose engine connections
    """
    engine = get_engine()
    logger = logging.getLogger("app.lifecycle")
    logger.info("application_started")

    yield

    # Shutdown: Close all connections
    await engine.dispose()
    logger.info("application_stopped")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()
    configure_logging(settings.debug)

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        debug=settings.debug,
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register routers
    app.include_router(health_router)
    app.include_router(diagnosis_router)
    app.include_router(knowledge_router)
    app.include_router(tasks_router)

    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        """Log each request with status code and elapsed time."""
        logger = logging.getLogger("app.http")
        started_at = perf_counter()

        try:
            response = await call_next(request)
        except Exception:
            duration_ms = int((perf_counter() - started_at) * 1000)
            logger.exception(
                "request_failed method=%s path=%s duration_ms=%s",
                request.method,
                request.url.path,
                duration_ms,
            )
            raise

        duration_ms = int((perf_counter() - started_at) * 1000)
        logger.info(
            "request_completed method=%s path=%s status=%s duration_ms=%s",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
        )
        return response

    return app


# Application instance (used by uvicorn)
app = create_app()
