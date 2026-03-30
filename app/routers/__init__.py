# File: app/routers/__init__.py
"""API 路由处理器"""
from app.routers.agents import router as agents_router
from app.routers.workbench import router as workbench_router
from app.routers.health import router as health_router
from app.routers.diagnosis import router as diagnosis_router
from app.routers.knowledge import router as knowledge_router
from app.routers.tasks import router as tasks_router
from app.routers.cases import router as cases_router

__all__ = [
    "health_router",
    "workbench_router",
    "agents_router",
    "diagnosis_router",
    "knowledge_router",
    "tasks_router",
    "cases_router",
]
