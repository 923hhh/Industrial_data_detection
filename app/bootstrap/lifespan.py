"""Application lifespan handlers."""
from contextlib import asynccontextmanager
import logging
from typing import AsyncIterator

from fastapi import FastAPI

from app.shared.database import get_engine


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Manage startup and shutdown resources."""
    engine = get_engine()
    logger = logging.getLogger("app.lifecycle")
    logger.info("application_started")

    yield

    await engine.dispose()
    logger.info("application_stopped")
