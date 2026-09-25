"""La corrida-poc-1 es evidencia experimental: NO se modifica. Parte PURA: no usa bases de datos, colas ni red.

JSON/CSV, hashes, dataset, gold, F1 y coherencia de los 100 casos ya los cubre `test_frozen_runs_preserved.py` (no se duplican aquí).
Lo que este archivo añade es la inmutabilidad de los archivos de la biblioteca lib-v5, que esa suite no abre."""

import hashlib

import pytest


@pytest.mark.requires_library_audio
def test_library_lib_v5_is_immutable_and_hash_addressed():
    from adaptation_swarm.config import SETTINGS
    from adaptation_swarm.multimodal.library import LibraryStore
    v5 = LibraryStore(SETTINGS.library_root, "lib-v5-9ae9ffdd")            # verifica hash del manifiesto
    assert len(v5.concepts()) == 30 and len(v5.manifest["entries"]) == 720
    for e in v5.manifest["entries"][::37]:
        assert hashlib.sha256((v5.dir / e["path"]).read_bytes()).hexdigest() == e["sha256"]
