"""Estado REAL del código y del entorno que producen una campaña: árbol de Git (`git status --porcelain`), sha256 de los fuentes que la determinan, versiones de software, biblioteca y dataset.
Nada se supone ni se inventa: lo que no puede obtenerse se registra como `unavailable` (y `git_state.dirty` es `None`, nunca «limpio»). `provenance_gaps` dice qué falta para que un resultado sea reproducible."""

from __future__ import annotations

import hashlib
import platform
import subprocess
from importlib import metadata
from pathlib import Path
from typing import Mapping, Sequence

from adaptation_swarm.tools import isolated_env as iso

UNAVAILABLE = "unavailable"
BACKEND = Path(__file__).resolve().parents[2]
PACKAGE = BACKEND / "adaptation_swarm"
# Fuentes que determinan una campaña HTTP de OE2/OE4 (rutas relativas a backend/).
CAMPAIGN_SOURCES = (
    "adaptation_swarm/oe/http_campaign.py", "adaptation_swarm/oe/http_window.py", "adaptation_swarm/oe/locust_raw_log.py", "adaptation_swarm/oe/profile_sequence.py",
    "adaptation_swarm/oe/time_contract.py", "adaptation_swarm/oe/campaign_spec.py", "adaptation_swarm/oe/campaign_guards.py", "adaptation_swarm/oe/oe2_confirmatory.py",
    "adaptation_swarm/oe/factorial.py", "adaptation_swarm/oe/code_state.py", "adaptation_swarm/metrics/performance.py", "adaptation_swarm/baselines/conventional.py", "adaptation_swarm/baselines/decision_table.py", "adaptation_swarm/api/router.py", "loadtest/locustfile.py",
)
# Campos SIN los cuales una campaña no es reproducible (ruta con puntos dentro de la provenance). Redis/PostgreSQL son opcionales: solo se registran si pueden obtenerse.
PROVENANCE_REQUIRED = (
    "code.commit", "code_state.dirty", "hardware.vcpu", "hardware.ram_gib", "hardware.cpu_model", "software.redis_client", "software.fastapi", "cold_warm.planned_server_starts", "software.python", "software.os", "software.uvicorn", "software.locust", "software.app_version",
    "library.version", "dataset.sha256", "dataset.n_profiles", "server.uvicorn_workers", "client_timeout_s", "generator_policy.id", "persist_policy", "persistence_status.status",
    "systems", "time_contract.version", "profile_sequence.algorithm", "campaign_spec.sha256", "official", "oe2_official",
    "persistence_conditions.comparison", "persistence_conditions.roles", "run_roles", "redis_isolation.prefix", "redis_isolation.mechanism",
)
# Requeridos para EJECUTAR una campaña real (no un dry-run, que puede correr sin servicios): el swarm usa Redis, así que su versión debe poder registrarse.
PROVENANCE_REQUIRED_FOR_EXECUTION = ("software.redis_server",)
# Requeridos solo AL TERMINAR una campaña ejecutada (no existen en un dry-run): verificación final del estado de Git y de los fuentes.
PROVENANCE_REQUIRED_AT_END = ("code_state_final.dirty", "code_state_final.unchanged_since_start", "campaign_source_fingerprints_final")


def git_state(repo: Path | None = None) -> dict:
    try:
        res = subprocess.run(["git", "status", "--porcelain"], cwd=str(repo or iso.REPO), capture_output=True, text=True, timeout=30, check=True)
    except (OSError, subprocess.SubprocessError):
        return {"dirty": None, "method": "git status --porcelain", "modified_paths": None, "note": "git no disponible: estado desconocido"}
    paths = [l[3:] for l in res.stdout.splitlines() if l.strip()]
    return {"dirty": bool(paths), "method": "git status --porcelain", "n_modified_or_untracked": len(paths), "modified_paths": paths[:50]}


def source_fingerprints(sources: Sequence[str] = CAMPAIGN_SOURCES) -> dict[str, str]:
    return {rel: hashlib.sha256((BACKEND / rel).read_bytes()).hexdigest() for rel in sources}


def _version(dist: str) -> str:
    try:
        return metadata.version(dist)
    except metadata.PackageNotFoundError:
        return UNAVAILABLE


def _redis_server_version() -> str:
    """Versión del servidor Redis si responde; `unavailable` si no (p. ej. en un dry-run sin servicios). Solo lee: no escribe nada."""
    try:
        import redis
        from adaptation_swarm.config import SETTINGS
        return str(redis.Redis.from_url(SETTINGS.redis_url, socket_connect_timeout=2, socket_timeout=2).info()["redis_version"])
    except Exception:
        return UNAVAILABLE


def _postgres_version() -> str:
    """Versión del servidor PostgreSQL si responde; `unavailable` si no. Solo lee (`select version()`)."""
    try:
        from sqlalchemy import text
        from app.db.session import SessionLocal
        with SessionLocal() as s:
            return str(s.execute(text("select version()")).scalar())
    except Exception:
        return UNAVAILABLE


def software_report(persist_policy="off") -> dict:
    """Versiones reales. `persist_policy`: una política o un conjunto de las que intervienen en la campaña. PostgreSQL no participa con persistencia `off`; si alguna condición es `on` SE REGISTRA su versión (o `unavailable`:
    nunca se declara «no usado» cuando sí interviene)."""
    policies = {persist_policy} if isinstance(persist_policy, str) else set(persist_policy)
    postgres = {"off": "not_used_persistence_off", "on": _postgres_version()} if "on" in policies else "not_used_persistence_off"
    version_file = iso.REPO / "VERSION"
    return {"python": platform.python_version(), "implementation": platform.python_implementation(), "os": platform.platform(), "app_version": version_file.read_text(encoding="utf-8").strip() if version_file.exists() else UNAVAILABLE,
            "uvicorn": _version("uvicorn"), "locust": _version("locust"), "fastapi": _version("fastapi"), "redis_client": _version("redis"), "redis_server": _redis_server_version(),
            "postgresql": postgres}


def library_report() -> dict:
    try:
        from adaptation_swarm.config import SETTINGS
        from adaptation_swarm.multimodal.library import LibraryStore
        return {"version": LibraryStore.open(SETTINGS.library_root).version, "root": str(SETTINGS.library_root)}
    except Exception as exc:                                                   # no se inventa: se declara
        return {"version": UNAVAILABLE, "reason": f"{type(exc).__name__}"}


def dataset_report(path: Path) -> dict:
    from adaptation_swarm.analysis import replicas as _infra
    p = Path(path)
    n = sum(1 for l in p.read_text(encoding="utf-8").splitlines() if l.strip())
    return {**_infra.dataset_identity(p), "file": p.name, "sha256": hashlib.sha256(p.read_bytes()).hexdigest(), "n_profiles": n}


def _get(prov: Mapping, path: str):
    cur = prov
    for part in path.split("."):
        if not isinstance(cur, Mapping) or part not in cur:
            return None
        cur = cur[part]
    return cur


def provenance_gaps(prov: Mapping, required: Sequence[str] = PROVENANCE_REQUIRED) -> list[str]:
    """Campos requeridos ausentes, `None` o `unavailable`/`unknown`. `code_state.dirty = None` (git no respondió) también cuenta como hueco. Lista vacía = provenance completa."""
    gaps = [p for p in required if _get(prov, p) in (None, "", UNAVAILABLE, "unknown")]
    if (prov.get("persistence_conditions") or {}).get("proposal_cost") == "on" and _get(prov, "software.postgresql.on") in (None, "", UNAVAILABLE, "unknown"):
        gaps.append("software.postgresql.on")                                  # hay condición ON: PostgreSQL interviene y su versión debe constar
    return gaps


def completion_gaps(prov: Mapping) -> list[str]:
    """Huecos de una campaña YA ejecutada: falta la verificación final del estado de Git/fuentes o ésta detectó cambios durante la campaña."""
    gaps = [p for p in PROVENANCE_REQUIRED_AT_END if _get(prov, p) in (None, "", UNAVAILABLE, "unknown")]
    if _get(prov, "code_state_final.unchanged_since_start") is False:
        gaps.append("code_state_final.unchanged_since_start=False: el código cambió durante la campaña")
    return gaps


def final_code_state(prov: dict, repo: Path | None = None) -> None:
    """Verificación FINAL de una campaña ejecutada: vuelve a leer el árbol de Git y los hashes de los fuentes y compara con los del inicio. No decide nada: registra `unchanged_since_start`."""
    start = prov.get("code_state", {})
    final = git_state(repo)
    fp_final = source_fingerprints()
    final["unchanged_since_start"] = bool(final.get("dirty") == start.get("dirty") and final.get("modified_paths") == start.get("modified_paths") and fp_final == prov.get("campaign_source_fingerprints") and final.get("dirty") is not None)
    prov["code_state_final"], prov["campaign_source_fingerprints_final"] = final, fp_final
