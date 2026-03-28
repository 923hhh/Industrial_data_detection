# File: app/core/config.py
"""Application configuration management.

统一由 Pydantic Settings 管理环境变量，避免手动读取环境变量与
BaseSettings 混用造成的解析不一致。
"""
from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # 数据库连接
    database_url: str = Field(
        default="sqlite+aiosqlite:///./sensor_data.db",
        alias="DATABASE_URL",
    )

    # 应用元信息
    app_name: str = "Industrial Fault Detection API"
    app_version: str = "0.1.0"
    debug: bool = Field(default=False, alias="DEBUG")

    # LLM 配置
    deepseek_api_key: str | None = Field(default=None, alias="DEEPSEEK_API_KEY")
    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    openai_api_base: str | None = Field(default=None, alias="OPENAI_API_BASE")
    anthropic_api_key: str | None = Field(default=None, alias="ANTHROPIC_API_KEY")

    # CORS 配置
    cors_origins: list[str] = ["*"]

    @field_validator("debug", mode="before")
    @classmethod
    def _normalize_debug(cls, value: object) -> bool:
        """容错解析 DEBUG，避免异常字符串直接导致启动失败。"""
        if isinstance(value, bool):
            return value

        if value is None:
            return False

        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"1", "true", "yes", "on", "debug"}:
                return True
            if normalized in {"0", "false", "no", "off", "release", ""}:
                return False

        return False

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        populate_by_name=True,
        extra="ignore",  # 允许 .env 中存在未声明的字段（如 DEEPSEEK_API_KEY 等）
    )


@lru_cache()
def get_settings() -> Settings:
    """Return cached settings instance (singleton pattern)."""
    return Settings()
