"""
Configuración central de la aplicación.
Lee variables de entorno desde .env usando pydantic-settings.
Soporta entornos development, production y testing.
"""

from pydantic import field_validator
from pydantic_settings import BaseSettings


_API_KEY_MASK_LEN = 8


def _mask_key(key: str) -> str:
    """Return a safe-for-logs representation of an API key."""
    if not key:
        return "<empty>"
    clean = key.strip()
    if len(clean) <= _API_KEY_MASK_LEN:
        return "<too-short>"
    return f"{clean[:_API_KEY_MASK_LEN]}...{clean[-4:]}"


class Settings(BaseSettings):
    """Configuración de la aplicación UPAO-MAS-EDU."""

    # Entorno
    ENV: str = "development"
    DEBUG: bool = True

    @property
    def is_production(self) -> bool:
        return self.ENV == "production"

    @property
    def is_testing(self) -> bool:
        return self.ENV == "testing"

    # Base de datos
    DATABASE_URL: str = "postgresql+psycopg://upao_user:upao_pass@localhost:5432/upao_mas_edu"

    @field_validator("DATABASE_URL")
    @classmethod
    def fix_postgres_scheme(cls, v: str) -> str:
        if v.startswith("postgres://"):
            return v.replace("postgres://", "postgresql://", 1)
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

    # API Keys
    TAVILY_API_KEY: str = ""
    OPENAI_API_KEY: str = ""

    # Logging
    LOG_LEVEL: str = "INFO"

    # Nombre de la app
    APP_NAME: str = "UPAO-MAS-EDU"
    APP_VERSION: str = "1.0.0"

    # ── Derived properties ──────────────────────────────────────────

    @property
    def has_tavily(self) -> bool:
        """True if TAVILY_API_KEY is set and non-empty."""
        return bool(self.TAVILY_API_KEY and self.TAVILY_API_KEY.strip())

    @property
    def has_openai(self) -> bool:
        """True if OPENAI_API_KEY is set and non-empty."""
        return bool(self.OPENAI_API_KEY and self.OPENAI_API_KEY.strip())

    @property
    def has_llm(self) -> bool:
        """True if any LLM provider is configured."""
        return self.has_openai

    @property
    def max_upload_size_bytes(self) -> int:
        return self.MAX_UPLOAD_SIZE_MB * 1024 * 1024

    @property
    def cors_origins(self) -> list[str]:
        origins = [self.FRONTEND_URL]
        if not self.is_production:
            origins.extend([
                "http://localhost:5173",
                "http://127.0.0.1:5173",
                "http://localhost:3000",
                "http://127.0.0.1:3000",
            ])
        return list(set(origins))

    @property
    def available_modalities(self) -> list[str]:
        """Return which AI modalities are available (safe for /health)."""
        out = []
        if self.has_tavily:
            out.append("web_search")
        if self.has_openai:
            out.append("llm_generation")
        out.append("deterministic_fallback")
        return out

    # ── Secrets-safe logging ────────────────────────────────────────

    def secrets_summary(self) -> dict[str, str]:
        """Return a dict of API key statuses safe for logging."""
        return {
            "tavily": "configured" if self.has_tavily else "missing",
            "openai": "configured" if self.has_openai else "missing",
            "tavily_key_preview": _mask_key(self.TAVILY_API_KEY),
            "openai_key_preview": _mask_key(self.OPENAI_API_KEY),
        }

    def validate_api_keys(self) -> list[str]:
        """Return a list of warning messages for missing API keys."""
        warnings: list[str] = []
        if not self.has_tavily:
            warnings.append(
                "TAVILY_API_KEY not set — web search retrieval will be degraded"
            )
        if not self.has_openai:
            warnings.append(
                "OPENAI_API_KEY not set — AI generation will fall back to deterministic templates"
            )
        return warnings

    # ── Pydantic config ─────────────────────────────────────────────

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
    }

    def __repr__(self) -> str:
        return (
            f"Settings(env={self.ENV}, debug={self.DEBUG}, "
            f"tavily={'✓' if self.has_tavily else '✗'}, "
            f"openai={'✓' if self.has_openai else '✗'})"
        )


settings = Settings()
