"""
Configuración de la aplicación GenZ Colombia API.
Carga variables de entorno y define settings globales.
"""
from pydantic_settings import BaseSettings
from typing import List
import json


class Settings(BaseSettings):
    """Configuración global de la aplicación."""

    # Application
    APP_NAME: str = "GenZ Colombia API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/genz_api"
    DATABASE_URL_SYNC: str = "postgresql://postgres:postgres@localhost:5432/genz_api"

    # Supabase
    SUPABASE_URL: str = ""
    SUPABASE_KEY: str = ""

    # Rate Limiting (por tier)
    RATE_LIMIT_FREE: str = "100/minute"
    RATE_LIMIT_PRO: str = "1000/minute"
    RATE_LIMIT_ENTERPRISE: str = "10000/minute"

    # CORS
    CORS_ORIGINS: str = '["http://localhost:3000", "http://localhost:8000"]'

    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS origins from JSON string."""
        try:
            return json.loads(self.CORS_ORIGINS)
        except (json.JSONDecodeError, TypeError):
            return ["http://localhost:3000", "http://localhost:8000"]

    @property
    def rate_limits(self) -> dict:
        """Retorna límites de rate por tier."""
        return {
            "free": self.RATE_LIMIT_FREE,
            "pro": self.RATE_LIMIT_PRO,
            "enterprise": self.RATE_LIMIT_ENTERPRISE,
        }

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


settings = Settings()
