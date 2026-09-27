"""Salvaguardas de aislamiento de los ejecutores y auditores de `adaptation_swarm`.

Los ejecutores (`run_experiment`, `run_slice`), los auditores (`analysis/f1_audit`, `analysis/pso_audit`) y `scripts/repro_db_bootstrap.sh` solo pueden operar sobre el
ENTORNO AISLADO de pruebas (`tests/adaptation_swarm/integration_env/`): PostgreSQL en 127.0.0.1:55432 (base y usuario `swarm_test`) y Redis en 127.0.0.1:56379.
Nunca sobre el entorno de desarrollo (`upao_postgres`/`upao_redis`, puertos 5432/6379, base `upao_mas_edu`) ni sobre uno remoto.

- Los destinos deben venir EXPLÍCITOS del entorno del proceso (`DATABASE_URL`, `SWARM_REDIS_URL`): sin ellos se rechaza, en vez de caer en los valores por defecto ni en
  `backend/.env`. Como `app.core.config` y `adaptation_swarm.config` fijan su valor al importarse, se comprueba además que el destino EFECTIVO coincide con el explícito.
- Los resultados solo se escriben en un directorio indicado explícitamente, nunca dentro de `experiments/results/` (resultados congelados), de un paquete de evidencia ni de la
  biblioteca, y nunca sobre un archivo existente.

Este módulo solo usa la biblioteca estándar al importarse; no abre conexiones ni escribe nada.

    python -m adaptation_swarm.tools.isolated_env check-database URL     # exit 0 si URL es la base aislada; imprime el destino sin contraseña
    python -m adaptation_swarm.tools.isolated_env check-redis URL
    python -m adaptation_swarm.tools.isolated_env verify-effective       # el destino EFECTIVO de DATABASE_URL (settings) es el explícito
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit

DB_HOST_PORT = 55432
DB_NAME = "swarm_test"
DB_USER = "swarm_test"
REDIS_PORT = 56379
LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}
LABEL_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
FROZEN_LABELS = ("corrida-poc-1", "corrida-poc-2")                # corridas congeladas: nunca se reutilizan como etiqueta de una corrida nueva

BACK = Path(__file__).resolve().parents[2]
REPO = BACK.parent
PROTECTED_DIRS = (BACK / "experiments" / "results", REPO / "datasets")           # resultados congelados, dataset y biblioteca
# Además, los analizadores NUEVOS (réplicas, línea base, alternativas de Balanced) no escriben en los resultados de carga ni dentro del propio paquete `adaptation_swarm`
# (fuentes, pruebas de contrato, documentos). No se aplica a `check_output_targets`: los ejecutores existentes y los nuevos experimentos (p. ej. `loadtest/results/<fecha>_<hw>/`
# escrito por Locust) siguen pudiendo escribir donde les corresponde.
NEW_ANALYZER_FORBIDDEN_DIRS = (BACK / "loadtest" / "results", BACK / "adaptation_swarm")


def mask(url: str) -> str:
    """La URL sin la contraseña."""
    return re.sub(r"(://[^:/@]*):[^@]*@", r"\1:***@", url)


def _reject(what: str, url: str, why: str, allowed: str) -> None:
    raise SystemExit(f"{what} RECHAZADA ({why}): {mask(url)}\n"
                     f"solo se opera sobre el entorno aislado {allowed} (tests/adaptation_swarm/integration_env/); nunca sobre desarrollo, producción ni un host remoto")


def check_database_url(url: str) -> str:
    """Devuelve la descripción del destino (sin contraseña) o aborta si `url` no es la base aislada de pruebas."""
    allowed = f"127.0.0.1:{DB_HOST_PORT}/{DB_NAME}"
    parts = urlsplit(url)
    if not parts.scheme.startswith("postgresql"):
        _reject("URL de base de datos", url, "no es PostgreSQL", allowed)
    if (parts.hostname or "") not in LOCAL_HOSTS:
        _reject("URL de base de datos", url, "host no local", allowed)
    if parts.port != DB_HOST_PORT:
        _reject("URL de base de datos", url, f"puerto {parts.port}, no {DB_HOST_PORT} (5432 es el de desarrollo)", allowed)
    if parts.path.lstrip("/") != DB_NAME:
        _reject("URL de base de datos", url, f"base '{parts.path.lstrip('/')}', no '{DB_NAME}'", allowed)
    if unquote(parts.username or "") != DB_USER:
        _reject("URL de base de datos", url, f"usuario '{parts.username}', no '{DB_USER}'", allowed)
    return f"PostgreSQL {parts.hostname}:{parts.port}/{DB_NAME} (usuario {DB_USER})"


def check_redis_url(url: str) -> str:
    allowed = f"127.0.0.1:{REDIS_PORT}"
    parts = urlsplit(url)
    if parts.scheme not in {"redis", "rediss"}:
        _reject("URL de Redis", url, "no es redis://", allowed)
    if (parts.hostname or "") not in LOCAL_HOSTS:
        _reject("URL de Redis", url, "host no local", allowed)
    if parts.port != REDIS_PORT:
        _reject("URL de Redis", url, f"puerto {parts.port}, no {REDIS_PORT} (6379 es el de desarrollo)", allowed)
    return f"Redis {parts.hostname}:{parts.port}"


def _explicit(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise SystemExit(f"{name} explícita requerida: exportarla en el entorno ANTES de ejecutar (no se usan valores por defecto ni backend/.env)")
    return value


def verify_effective_database() -> str:
    """El destino que `app.core.config.settings` realmente usará es el explícito (que `backend/.env` no lo sobrescribió). Importar settings no abre conexiones."""
    url = check_database_url(_explicit("DATABASE_URL"))
    from app.core.config import settings
    if settings.DATABASE_URL != os.environ["DATABASE_URL"]:
        raise SystemExit(f"el destino efectivo de la aplicación ({mask(settings.DATABASE_URL)}) difiere del DATABASE_URL explícito: "
                         "exportar DATABASE_URL antes de arrancar el proceso")
    return url


def require_isolated_database() -> str:
    target = verify_effective_database()
    print(f"destino de base de datos: {target}", file=sys.stderr)
    return target


def require_isolated_redis() -> str:
    url = _explicit("SWARM_REDIS_URL")
    target = check_redis_url(url)
    from adaptation_swarm.config import SETTINGS
    if SETTINGS.redis_url != url:
        raise SystemExit(f"el destino efectivo de Redis ({mask(SETTINGS.redis_url)}) difiere del SWARM_REDIS_URL explícito: exportarlo antes de arrancar el proceso")
    print(f"destino de Redis: {target}", file=sys.stderr)
    return target


def check_label(label: str | None) -> str:
    if not label or not LABEL_RE.match(label):
        raise SystemExit("--run-label es obligatorio y debe ser [A-Za-z0-9._-] (máx. 64), p. ej. 'repro-2026-09-25'")
    if label in FROZEN_LABELS:
        raise SystemExit(f"'{label}' es una corrida congelada: elige otra etiqueta para una corrida nueva")
    return label


def check_output_targets(targets: list[Path]) -> None:
    """Los archivos a generar: no existen, y no están dentro de resultados congelados, de un paquete de evidencia ni de la biblioteca."""
    for t in targets:
        resolved = t.resolve()
        for protected in PROTECTED_DIRS:
            if resolved == protected.resolve() or protected.resolve() in resolved.parents:
                raise SystemExit(f"{t}: dentro de {protected.relative_to(REPO)}, que contiene resultados/datos congelados; usa otro --out-dir")
        if any(p.name.startswith("evidence_package_") for p in resolved.parents):
            raise SystemExit(f"{t}: dentro de un paquete de evidencia congelado; usa otro --out-dir")
        if resolved.exists():
            raise SystemExit(f"{t} ya existe: los resultados no se sobrescriben")


def check_new_output_targets(targets: list[Path]) -> None:
    """`check_output_targets` + los analizadores nuevos tampoco escriben en `loadtest/results/` ni dentro de `adaptation_swarm/`. Resuelve rutas (`..`, enlaces simbólicos)."""
    check_output_targets(targets)
    for t in targets:
        resolved = t.resolve()
        for forbidden in NEW_ANALYZER_FORBIDDEN_DIRS:
            if resolved == forbidden.resolve() or forbidden.resolve() in resolved.parents:
                raise SystemExit(f"{t}: dentro de {forbidden.relative_to(REPO)}, que no admite salidas de los analizadores; usa otro --out-dir")


def require_out_dir(value: str | None) -> Path:
    if not value:
        raise SystemExit("--out-dir es obligatorio (no hay destino por defecto: los resultados congelados no se mezclan con los nuevos)")
    return Path(value)


def main(argv: list[str] | None = None) -> None:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) == 2 and argv[0] == "check-database":
        print(f"destino: {check_database_url(argv[1])}")
    elif len(argv) == 2 and argv[0] == "check-redis":
        print(f"destino: {check_redis_url(argv[1])}")
    elif argv == ["verify-effective"]:
        print(f"destino efectivo verificado: {verify_effective_database()}")
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main()
