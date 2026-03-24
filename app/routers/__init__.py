# File: app/routers/__init__.py
"""API route handlers."""
from app.routers.health import router as health_router

__all__ = ["health_router"]
