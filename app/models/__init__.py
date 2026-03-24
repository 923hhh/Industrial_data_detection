# File: app/models/__init__.py
"""SQLAlchemy ORM models."""
from app.models.sensor_data import SensorData, Base

__all__ = ["SensorData", "Base"]
