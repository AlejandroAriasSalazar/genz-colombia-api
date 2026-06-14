from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "GenZ Colombia API V2"
    app_version: str = "2.0.0"
    environment: Literal["development", "test", "production"] = "development"
    log_level: str = "INFO"
    database_url: str = "sqlite:///./genz_v2.db"
    redis_url: str | None = None
    api_key_pepper: str = "development-only-change-me"
    synthetic_id_secret: str = "development-only-change-me"
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])
    raw_storage_path: Path = Path("storage/raw")
    request_timeout_seconds: float = 60.0
    source_max_bytes: int = 200 * 1024 * 1024
    small_cell_threshold: int = 5
    default_reference_year: int = 2026
    target_municipalities: list[str] = Field(default_factory=lambda: ["05001", "11001"])
    trust_proxy_headers: bool = False

    @model_validator(mode="after")
    def validate_production(self) -> "Settings":
        if self.environment == "production":
            if not self.database_url.startswith(("postgresql://", "postgresql+psycopg://")):
                raise ValueError("Production requires PostgreSQL")
            if not self.redis_url:
                raise ValueError("Production requires Redis")
            insecure = {"development-only-change-me", "", "changeme"}
            if self.api_key_pepper in insecure or self.synthetic_id_secret in insecure:
                raise ValueError("Production secrets must be configured")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
