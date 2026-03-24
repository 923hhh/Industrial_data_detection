# File: app/routers/health.py
"""Health check endpoint for service monitoring.

Executes a lightweight database query to verify connectivity.
"""
from fastapi import APIRouter, status
from pydantic import BaseModel

from app.core.database import check_database_connection

router = APIRouter(tags=["Health"])


class HealthResponse(BaseModel):
    """Response schema for health check endpoint."""

    status: str
    database: str


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Health Check",
    description="Verify application and database connectivity."
)
async def health_check() -> HealthResponse:
    """Check application and database health.

    Returns:
        HealthResponse with status and database connection state.
    """
    db_connected = await check_database_connection()

    return HealthResponse(
        status="healthy" if db_connected else "degraded",
        database="connected" if db_connected else "disconnected"
    )
