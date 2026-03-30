"""Application middleware registration."""
import logging
from time import perf_counter

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware


def register_middlewares(app: FastAPI, cors_origins: list[str]) -> None:
    """Register CORS and request logging middleware."""
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

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
