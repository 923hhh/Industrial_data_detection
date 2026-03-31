"""Application lifespan handlers."""
from contextlib import asynccontextmanager
import logging
from typing import AsyncIterator

from fastapi import FastAPI

from app.shared.database import get_engine
from app.services.knowledge_import_worker import KnowledgeImportWorker


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Manage startup and shutdown resources."""
    engine = get_engine()
    logger = logging.getLogger("app.lifecycle")
    logger.info("application_started")
    try:
        resumed_job_ids = await KnowledgeImportWorker.resume_pending_jobs()
    except Exception:
        logger.exception("knowledge_import_jobs_resume_failed")
        resumed_job_ids = []
    if resumed_job_ids:
        logger.info("knowledge_import_jobs_resumed count=%s", len(resumed_job_ids))

    yield

    await engine.dispose()
    logger.info("application_stopped")
