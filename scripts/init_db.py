# File: scripts/init_db.py
"""Database initialization script.

Run this script to create all tables and optionally seed sample data.
Usage: python scripts/init_db.py
"""
import asyncio
import sys
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import get_engine, get_session_context
from app.models import Base
from app.models.sensor_data import SensorData


async def init_database():
    """Create all tables in the database."""
    engine = get_engine()

    print("Creating database tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    print("Database tables created successfully.")

    # Verify table creation
    async with get_session_context() as session:
        from sqlalchemy import select
        result = await session.execute(select(SensorData).limit(1))
        print(f"SensorData table verified. Sample query: {result.first() is not None}")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(init_database())
