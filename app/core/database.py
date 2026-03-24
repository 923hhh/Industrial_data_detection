# File: app/core/database.py
"""Asynchronous SQLAlchemy 2.0 database engine and session factory.

Design decisions:
- AsyncEngine: Required for FastAPI's non-blocking request handling
- check_same_thread=False: Required for SQLite in async context
- JSON type: Auto-detected based on dialect (JSONB for PostgreSQL, Text for SQLite)
"""
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from app.core.config import get_settings


def _get_async_engine() -> AsyncEngine:
    """Create async engine with dialect-specific configuration.

    SQLite uses NullPool to avoid thread-checking issues in async context.
    PostgreSQL uses default connection pooling for production performance.
    """
    settings = get_settings()
    is_sqlite = settings.database_url.startswith("sqlite")

    if is_sqlite:
        # SQLite: disable thread check, use NullPool for async safety
        return create_async_engine(
            settings.database_url,
            echo=settings.debug,
            poolclass=NullPool,
            connect_args={"check_same_thread": False},
        )
    else:
        # PostgreSQL: use default pool for production workloads
        return create_async_engine(
            settings.database_url,
            echo=settings.debug,
            pool_pre_ping=True,  # Verify connections before use
        )


# Global async engine instance (initialized lazily)
_async_engine: AsyncEngine | None = None


def get_engine() -> AsyncEngine:
    """Get or create the global async engine instance."""
    global _async_engine
    if _async_engine is None:
        _async_engine = _get_async_engine()
    return _async_engine


# 全局会话工厂 (惰性初始化，避免 alembic 迁移时过早创建 engine)
_async_session_factory: async_sessionmaker[AsyncSession] | None = None


def _get_session_factory() -> async_sessionmaker[AsyncSession]:
    """惰性创建 session factory，在第一次访问时才初始化."""
    global _async_session_factory
    if _async_session_factory is None:
        _async_session_factory = async_sessionmaker(
            bind=get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )
    return _async_session_factory


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for FastAPI to inject async session per request."""
    async with _get_session_factory()() as session:
        try:
            yield session
        finally:
            await session.close()


@asynccontextmanager
async def get_session_context() -> AsyncGenerator[AsyncSession, None]:
    """Context manager for sessions outside request scope (e.g., scripts)."""
    async with _get_session_factory()() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def check_database_connection() -> bool:
    """Execute lightweight query to verify database connectivity."""
    try:
        async with get_session_context() as session:
            await session.execute(text("SELECT 1"))
            return True
    except Exception:
        return False
