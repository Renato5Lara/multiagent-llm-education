"""Configuración del subsistema (variables de entorno con valores por defecto
reproducibles). Redis es OBLIGATORIO (DEC-05): no hay ningún sustituto."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class SwarmSettings:
    redis_url: str = os.getenv("SWARM_REDIS_URL", "redis://localhost:6379/0")
    key_prefix: str = os.getenv("SWARM_REDIS_PREFIX", "swarm:")
    log_ttl_seconds: int = int(os.getenv("SWARM_LOG_TTL_SECONDS", "86400"))
    seen_ttl_seconds: int = int(os.getenv("SWARM_SEEN_TTL_SECONDS", "3600"))
    redis_max_connections: int = int(os.getenv("SWARM_REDIS_MAX_CONNECTIONS", "1024"))
    stream_maxlen: int = int(os.getenv("SWARM_STREAM_MAXLEN", "5000"))
    library_root: Path = Path(
        os.getenv("SWARM_LIBRARY_ROOT", str(_REPO_ROOT / "datasets" / "adaptation_library"))
    )
    request_timeout_seconds: float = float(os.getenv("SWARM_REQUEST_TIMEOUT", "30"))
    sandbox_bin: str = os.getenv("SWARM_SANDBOX_BIN", "podman")  # DEC-15: podman en este entorno


SETTINGS = SwarmSettings()
