# File: app/routers/__init__.py
"""API 路由处理器"""
from app.routers.health import router as health_router
from app.routers.diagnosis import router as diagnosis_router
from app.routers.knowledge import router as knowledge_router
from app.routers.tasks import router as tasks_router

__all__ = ["health_router", "diagnosis_router", "knowledge_router", "tasks_router"]
