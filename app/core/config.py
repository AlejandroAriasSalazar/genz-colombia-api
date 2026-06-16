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

    app_name: str = "GenZ Colombia API V3"
    app_version: str = "3.0.0"
    environment: Literal["development", "test", "production"] = "development"
    log_level: str = "INFO"
    database_url: str = "sqlite:///./genz_v3.db"
    # Pool de SQLAlchemy (solo aplica a Postgres). Pequeño a propósito: el Postgres
    # es compartido con Supabase/n8n, y con 2 workers de API + el worker no conviene
    # abrir muchas conexiones. Override por env: DB_POOL_SIZE / DB_MAX_OVERFLOW.
    db_pool_size: int = 5
    db_max_overflow: int = 5
    redis_url: str | None = None
    api_key_pepper: str = "development-only-change-me"
    synthetic_id_secret: str = "development-only-change-me"
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])
    raw_storage_path: Path = Path("storage/raw")
    request_timeout_seconds: float = 60.0
    source_max_bytes: int = 200 * 1024 * 1024
    small_cell_threshold: int = 5
    default_reference_year: int = 2026
    # Highest single-year age in the DANE pyramid (top bucket = "max_age y más").
    # Must stay <= the population_cells CheckConstraint (age <= 100); raising it
    # requires an Alembic migration that widens that constraint.
    max_age: int = 100
    # Worker cadence for unattended re-ingestion (default weekly).
    ingestion_interval_seconds: int = 7 * 24 * 60 * 60
    # A deploy/restart must NOT trigger the heavy national parse. The worker only
    # re-ingests on boot when this is explicitly enabled; by default it sleeps the
    # full interval first. Production normally loads a prebuilt artifact instead
    # (see scripts/build_dataset.py + `manage load-release`).
    worker_ingest_on_start: bool = False
    # Heavy path switch. When False (default, the safe setting for the shared CCX13),
    # the worker NEVER re-parses the 131 MB national XLSX; each cycle it just streams in
    # the newest prebuilt artifact via COPY (a few MB of RAM, idempotent). Set
    # WORKER_AUTO_INGEST=true only on a box with memory headroom to re-download and
    # stream-parse the source on a schedule.
    worker_auto_ingest: bool = False
    # Rows inserted per batch during ingestion. Keeps peak memory flat on small boxes;
    # the whole national file is streamed, never materialized at once. Override by env.
    ingest_batch_size: int = 5000
    # Where prebuilt, compact dataset releases live (cells.csv.gz + controls.csv.gz +
    # release.json). Loaded in seconds via COPY; production never parses the 131 MB
    # source XLSX. Built offline with scripts/build_dataset.py.
    data_releases_path: Path = Path("data/releases")
    # Empty list = ingest every municipality in the DANE file (all of Colombia).
    # Provide explicit DIVIPOLA codes to restrict ingestion to a subset.
    target_municipalities: list[str] = Field(default_factory=list)
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
