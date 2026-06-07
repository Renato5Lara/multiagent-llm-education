"""
Configuración central de la aplicación.
Lee variables de entorno desde .env usando pydantic-settings.
Soporta entornos development, production y testing.
"""

from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Configuración de la aplicación UPAO-MAS-EDU."""

    # Entorno
    ENV: str = "development"
    DEBUG: bool = True

    @property
    def is_production(self) -> bool:
        return self.ENV == "production"

    # Base de datos
    DATABASE_URL: str = "postgresql+psycopg://upao_user:upao_pass@localhost:5432/upao_mas_edu"

    @field_validator("DATABASE_URL")
    @classmethod
    def fix_postgres_scheme(cls, v: str) -> str:
        # Render and Heroku provide `postgres://` — SQLAlchemy requires `postgresql://`.
        if v.startswith("postgres://"):
            v = v.replace("postgres://", "postgresql://", 1)
        # Ensure psycopg3 is used explicitly; avoids psycopg2 fallback on plain
        # `postgresql://` URLs that arrive from cloud providers without a driver hint.
        if v.startswith("postgresql://") and "+psycopg" not in v:
            v = v.replace("postgresql://", "postgresql+psycopg://", 1)
        return v

    # URLs
    FRONTEND_URL: str = "http://localhost:5173"
    BACKEND_URL: str = "http://localhost:8000"

    # JWT
    SECRET_KEY: str = "cambia-esto-en-produccion-genera-uno-aleatorio-de-32-bytes"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Uploads
    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_SIZE_MB: int = 50

    # Tavily Search API
    TAVILY_API_KEY: str = ""

    # Logging
    LOG_LEVEL: str = "INFO"

    # Nombre de la app
    APP_NAME: str = "UPAO-MAS-EDU"
    APP_VERSION: str = "1.0.0"

    @property
    def max_upload_size_bytes(self) -> int:
        return self.MAX_UPLOAD_SIZE_MB * 1024 * 1024

    @property
    def cors_origins(self) -> list[str]:
        origins = [self.FRONTEND_URL]
        if not self.is_production:
            origins.extend(["http://localhost:5173", "http://localhost:3000"])
        return list(set(origins))

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
    }


settings = Settings()
