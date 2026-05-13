"""
Configuración central de la aplicación.
Lee variables de entorno desde .env usando pydantic-settings.
"""

from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Configuración de la aplicación UPAO-MAS-EDU."""

    # Base de datos
    DATABASE_URL: str = "postgresql+psycopg://upao_user:upao_pass@localhost:5432/upao_mas_edu"

    # JWT
    SECRET_KEY: str = "cambia-esto-en-produccion-genera-uno-aleatorio-de-32-bytes"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # Uploads
    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_SIZE_MB: int = 50

    # Entorno
    ENV: str = "development"

    # Nombre de la app
    APP_NAME: str = "UPAO-MAS-EDU"
    APP_VERSION: str = "1.0.0"

    @property
    def max_upload_size_bytes(self) -> int:
        """Tamaño máximo de subida en bytes."""
        return self.MAX_UPLOAD_SIZE_MB * 1024 * 1024

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
    }


# Instancia global de configuración
settings = Settings()
