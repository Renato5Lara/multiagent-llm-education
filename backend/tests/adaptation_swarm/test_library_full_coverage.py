"""La biblioteca M1 cubre los 30 conceptos del dataset con artefactos REALES y válidos, y los 2151 MP3 de sus 10 versiones coinciden con los
manifiestos. SOLO LECTURA sobre `datasets/adaptation_library/` (o `SWARM_LIBRARY_ROOT`): sin PostgreSQL, Redis, red, sandbox ni escritura
(los casos negativos usan copias con enlaces simbólicos en `tmp_path`).

Audio ausente ≠ audio corrupto: un MP3 corrupto (hash incorrecto) SIEMPRE hace fallar; un MP3 ausente omite la prueba, salvo con
`SWARM_REQUIRE_LIBRARY=1`, que la hace fallar (ver `LIBRARY_TESTS.md`). La validación de cada variante de código en el sandbox real
vive aparte y diferida: `test_library_sandbox_integration.py`."""

import io
import json
import os
from pathlib import Path

import pytest
from mutagen.mp3 import MP3

from adaptation_swarm.config import SETTINGS
from adaptation_swarm.multimodal.flowchart import build_flowchart, validate_flowchart
from adaptation_swarm.profiles.generator import read_dataset
from adaptation_swarm.tools import library_inventory as inv_mod
from tests.adaptation_swarm.conftest import DATASET

TOTAL_MP3 = 2151                # 10 versiones: 9 + 126 + 144 + 252 + 270 × 6 (manifiestos de `lib-v1` … `lib-v10`)


def _concepts():
    return {p.concept_id: p.metadata["concept_title"] for p in read_dataset(DATASET)}


def _audio_absent_or_fail(absent: int) -> None:
    """Audio ausente: se omite (clon sin los mp3, que están fuera de Git) o falla si se exige la biblioteca completa."""
    if not absent:
        return
    msg = f"faltan {absent} mp3 de la biblioteca (están fuera de Git; ver REPRODUCIBILITY.md §9)"
    if os.getenv("SWARM_REQUIRE_LIBRARY") == "1":
        pytest.fail(msg)
    pytest.skip(msg)


def test_every_dataset_concept_is_complete_in_the_library(store):
    concepts = _concepts()
    assert len(concepts) == 30
    incomplete = [t for c, t in concepts.items() if not store.is_complete(c)]
    assert incomplete == []
    assert len(store.manifest["entries"]) >= 30 * 24


def test_every_entry_records_agent_provider_prompt_version_and_hashes(store):
    for e in store.manifest["entries"]:
        assert e["generator"]["agent"] in {"AG2", "AG3", "AG4"} and e["prompt_template_version"] and e["provider"]
        assert len(e["sha256"]) == 64 and e["validation"]["status"] == "passed" and e["generated_at"]


@pytest.mark.requires_library_audio
def test_all_diagrams_texts_and_audios_are_valid_and_chained(store):
    for cid, title in _concepts().items():
        anchor = store.anchor(cid)
        for c in range(3):
            code = store.code(cid, c)
            for d in range(3):
                dia = store.diagram(cid, c, d)
                assert validate_flowchart(dia.text) == [] and dia.text == build_flowchart(code.text, d) + "\n", (title, c, d)
        for t in range(3):
            txt = store.text(cid, t)
            assert len(txt.text.split()) >= 15 and all(f in txt.text.lower() for f in anchor.function_names), (title, t)
            for a in range(3):
                au = store.audio(cid, t, a, load=True)
                assert MP3(io.BytesIO(au.content)).info.length > 2.0, (title, t, a)
                assert au.entry["derived_from"] == txt.sha256 and au.entry["provider"]["input_sha256"] == txt.sha256


def test_the_2151_mp3_of_all_ten_versions_match_their_manifest_hashes():
    inv = inv_mod.inventory(SETTINGS.library_root, results_dir=None)
    audio = [v["by_modality"]["audio"] for v in inv["versions"]]
    assert [v["number"] for v in inv["versions"]] == list(range(1, 11)) and sum(a["entries"] for a in audio) == TOTAL_MP3
    assert sum(a["hash_mismatch"] for a in audio) == 0, "hay mp3 CORRUPTOS (hash incorrecto): no es lo mismo que ausentes"
    _audio_absent_or_fail(sum(a["absent"] for a in audio))
    assert sum(a["ok"] for a in audio) == TOTAL_MP3 and inv["summary"]["any_hash_mismatch"] is False


def test_absent_and_corrupt_mp3_are_told_apart_on_the_real_v10_manifest(tmp_path):
    """Copia (enlaces simbólicos) de la última versión con UN mp3 ausente y OTRO corrupto: la copia es lo único que se escribe."""
    src = max(SETTINGS.library_root.glob("lib-v*"), key=lambda p: int(p.name.split("-")[1][1:]))
    manifest = json.loads((src / "manifest.json").read_text(encoding="utf-8"))
    audio = [e for e in manifest["entries"] if e["modality"] == "audio"]
    _audio_absent_or_fail(sum(not (src / e["path"]).is_file() for e in audio))
    root = tmp_path / "adaptation_library"
    dst = root / src.name
    dst.mkdir(parents=True)
    (dst / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    absent_entry, corrupt_entry = audio[0], audio[1]
    for e in manifest["entries"]:
        if e is absent_entry:
            continue                                                                   # ausente: no se crea
        target = dst / e["path"]
        target.parent.mkdir(parents=True, exist_ok=True)
        if e is corrupt_entry:
            target.write_bytes((src / e["path"]).read_bytes() + b"x")                  # corrupto: copia alterada; el original no se toca
        else:
            target.symlink_to((src / e["path"]).resolve())
    v = inv_mod.inventory(root, results_dir=None)["versions"][0]
    c = v["by_modality"]["audio"]
    assert (c["ok"], c["absent"], c["hash_mismatch"]) == (len(audio) - 2, 1, 1)
    assert v["audio"]["presence"] == "parcial" and v["audio"]["integrity"] == "hash_incorrecto"
    assert not (dst / absent_entry["path"]).exists()                                   # el ausente sigue ausente
