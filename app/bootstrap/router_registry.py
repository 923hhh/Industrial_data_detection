"""Router registration for the application factory."""
from fastapi import FastAPI

from app.modules.agents import router as agents_router
from app.modules.cases import router as cases_router
from app.modules.diagnosis import router as diagnosis_router
from app.modules.knowledge import router as knowledge_router
from app.modules.tasks import router as tasks_router
from app.modules.workbench import router as workbench_router
from app.routers.health import router as health_router
from app.routers.observability import router as observability_router


def register_routers(app: FastAPI) -> None:
    """Register all public API routers."""
    app.include_router(health_router)
    app.include_router(observability_router)
    app.include_router(workbench_router)
    app.include_router(agents_router)
    app.include_router(diagnosis_router)
    app.include_router(knowledge_router)
    app.include_router(tasks_router)
    app.include_router(cases_router)
