# File: app/core/config.py
"""Application configuration management.

Supports seamless migration from SQLite (dev) to PostgreSQL (prod)
by simply changing the DATABASE_URL environment variable.
"""
import os
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Database connection string
    # SQLite (dev): sqlite+aiosqlite:///./sensor_data.db
    # PostgreSQL (prod): postgresql+asyncpg://user:pass@localhost/sensor_db
    database_url: str = os.getenv(
        "DATABASE_URL",
        "sqlite+aiosqlite:///./sensor_data.db"
    )

    # Application metadata
    app_name: str = "Industrial Fault Detection API"
    app_version: str = "0.1.0"
    debug: bool = os.getenv("DEBUG", "false").lower() == "true"

    # LLM API credentials
    deepseek_api_key: str | None = None
    openai_api_key: str | None = None
    openai_api_base: str | None = None
    anthropic_api_key: str | None = None

    # CORS settings
    cors_origins: list[str] = ["*"]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",  # 允许 .env 中存在未声明的字段（如 DEEPSEEK_API_KEY 等）
    )


@lru_cache()
def get_settings() -> Settings:
    """Return cached settings instance (singleton pattern)."""
    return Settings()
