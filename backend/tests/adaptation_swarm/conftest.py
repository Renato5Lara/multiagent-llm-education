"""Fixtures del subsistema adaptation_swarm. Redis es OBLIGATORIO (DEC-05): si no está disponible,
las pruebas de integración FALLAN (no se saltan).

Marcador `requires_library_audio` (Decisión C, DECISION-CLOSURE §14): los mp3 de la biblioteca están FUERA de Git, y en el código actual un ciclo
completo entrega un paquete solo si su validación (que abre los bytes de audio y de SVG) lo aprueba. Las pruebas marcadas necesitan la
biblioteca restaurada (audio y SVG de lib-v5, lib-v9 y la última versión). Ver `LIBRARY_TESTS.md`.
- Biblioteca completa → se ejecutan (y fallan normalmente si algo está mal).
- Faltan archivos (ausentes, NO corruptos) y `SWARM_REQUIRE_LIBRARY` no es `1` → se omiten con una razón que cuenta cuántos archivos faltan.
- `SWARM_REQUIRE_LIBRARY=1` → NO se omiten nunca: la ausencia hace fallar las pruebas (modo de evidencia/CI).
Un archivo presente con hash incorrecto nunca se omite: la prueba corre y falla."""

from __future__ import annotations

import os
import uuid
from pathlib import Path

import pytest

from adaptation_swarm.bus.redis_bus import RedisBus
from adaptation_swarm.config import SETTINGS
from adaptation_swarm.multimodal.library import LibraryStore
from adaptation_swarm.profiles.generator import read_dataset

REPO = Path(__file__).resolve().parents[3]
DATASET = REPO / "datasets" / "synthetic_profiles" / "profiles-v1.jsonl"
WHILE_ID = "80655903-265e-42cc-a904-979c5915a762"     # concepto "Bucle while" (slice)
SLICE_PROFILE = "syn-visual_dominant-repetitive-r0"


REQUIRED_LIBRARY_VERSIONS = ("lib-v5-9ae9ffdd", "lib-v9-a0231e9b", None)      # None = la última versión (numérica)


def _library_presence() -> dict[str, dict[str, int]]:
    from adaptation_swarm.multimodal.versioning import latest_version
    from adaptation_swarm.tools.library_inventory import presence_summary
    latest = latest_version(SETTINGS.library_root)
    wanted = tuple(v or latest for v in REQUIRED_LIBRARY_VERSIONS if (v or latest))
    return presence_summary(SETTINGS.library_root, wanted)


def _missing_library_files(presence: dict[str, dict[str, int]]) -> dict[str, int]:
    return {v: r["audio_absent"] + r["svg_absent"] + r["manifest_absent"] for v, r in presence.items()
            if r["audio_absent"] + r["svg_absent"] + r["manifest_absent"]}


def pytest_configure(config):
    config.addinivalue_line("markers", "integration: usa servicios reales (Redis/OpenAI/sandbox)")
    config.addinivalue_line("markers", "requires_library_audio: necesita la biblioteca restaurada (audio y SVG de v5, v9 y la última; ver LIBRARY_TESTS.md)")


def pytest_report_header(config):
    missing = _missing_library_files(_library_presence())
    if not missing:
        return "biblioteca M1: audio y SVG de v5/v9/última PRESENTES (las pruebas requires_library_audio se ejecutan)"
    return f"biblioteca M1: FALTAN archivos de audio/SVG {missing} (requires_library_audio: {'FALLAN' if os.getenv('SWARM_REQUIRE_LIBRARY') == '1' else 'se omiten'})"


def pytest_collection_modifyitems(config, items):
    marked = [i for i in items if i.get_closest_marker("requires_library_audio")]
    missing = _missing_library_files(_library_presence()) if marked else {}
    if not missing or os.getenv("SWARM_REQUIRE_LIBRARY") == "1":
        return
    reason = (f"biblioteca sin restaurar: faltan archivos de audio/SVG {missing} (los mp3 están fuera de Git; ver REPRODUCIBILITY.md §9 y "
              f"tests/adaptation_swarm/LIBRARY_TESTS.md). Ejecutar con SWARM_REQUIRE_LIBRARY=1 para exigirla")
    for item in marked:
        item.add_marker(pytest.mark.skip(reason=reason))


@pytest.fixture
async def bus():
    b = RedisBus(prefix=f"swarm-test-{uuid.uuid4().hex[:8]}:")
    await b.connect()          # falla si Redis no está: es un requisito, no algo opcional
    yield b
    await b.purge_prefix()
    await b.close()


@pytest.fixture(scope="session")
def store() -> LibraryStore:
    return LibraryStore.open(SETTINGS.library_root)


@pytest.fixture(scope="session")
def profiles():
    return {p.profile_id: p for p in read_dataset(DATASET)}


@pytest.fixture
def slice_profile(profiles):
    return profiles[SLICE_PROFILE]
