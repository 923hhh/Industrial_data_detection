# File: app/services/sensor_service.py
"""Business logic layer for sensor data operations.

Provides an abstraction layer between API routes and database access,
enabling future integration with LangChain agents without DB coupling.
"""
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.sensor_data import SensorData
from app.schemas.sensor_data import SensorDataCreate


class SensorService:
    """Service class for sensor data CRUD operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, data: SensorDataCreate) -> SensorData:
        """Create a new sensor data record."""
        record = SensorData(**data.model_dump())
        self.session.add(record)
        await self.session.commit()
        await self.session.refresh(record)
        return record

    async def get_by_id(self, record_id: int) -> SensorData | None:
        """Retrieve a sensor record by ID."""
        result = await self.session.execute(
            select(SensorData).where(SensorData.id == record_id)
        )
        return result.scalar_one_or_none()

    async def get_by_timestamp(
        self,
        start: datetime,
        end: datetime,
        limit: int = 1000
    ) -> list[SensorData]:
        """Query sensor records within a time range."""
        result = await self.session.execute(
            select(SensorData)
            .where(SensorData.timestamp >= start, SensorData.timestamp <= end)
            .order_by(SensorData.timestamp)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_latest(self, limit: int = 100) -> list[SensorData]:
        """Retrieve the most recent sensor records."""
        result = await self.session.execute(
            select(SensorData)
            .order_by(SensorData.timestamp.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def count(self) -> int:
        """Return total count of sensor records."""
        result = await self.session.execute(
            select(SensorData).with_only_columns(SensorData.id.count())
        )
        return result.scalar_one() or 0
