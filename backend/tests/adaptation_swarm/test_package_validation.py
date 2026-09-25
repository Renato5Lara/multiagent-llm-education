"""Validación común de paquetes: un paquete NO es válido si falta o falla una modalidad requerida."""

import copy

import pytest

from adaptation_swarm.multimodal.validation import validate_package
from adaptation_swarm.stack import SwarmStack
from tests.adaptation_swarm.conftest import WHILE_ID

pytestmark = [pytest.mark.integration, pytest.mark.requires_library_audio]


@pytest.fixture(scope="module")
async def pkg(store, profiles):
    import uuid
    async with SwarmStack(library_version=store.version, prefix=f"swarm-test-{uuid.uuid4().hex[:8]}:") as st:
        r = await st.orchestrator.run_cycle(profiles["syn-visual_dominant-repetitive-r0"], batch_seed=20260923)
        await st.bus.purge_prefix()
    assert r.status == "completed", r.error
    return r.package


def test_delivered_package_passes_every_modality_check(store, pkg):
    assert pkg["validation"]["valid"] is True
    v = validate_package({k: pkg[k] for k in ("package_id", "cycle_id", "concept_id", "library_version", "S", "code", "diagram", "text", "audio", "chain_valid")}, store)
    assert v.valid and v.errors == []
    for m in ("code", "diagram", "text", "audio"):
        assert v.modalities[m].ok and v.modalities[m].checks


def test_code_diagram_text_audio_checks_are_the_ones_the_spec_requires(store, pkg):
    v = pkg["validation"]["modalities"]
    assert {"present", "extension_py", "sha256", "sandbox_passed", "hygiene", "covers_concept"} <= set(v["code"]["checks"])
    assert {"structure", "derived_from_code", "matches_ast"} <= set(v["diagram"]["checks"])
    assert {"concept", "level_and_vocabulary", "consistent_with_code", "sha256"} <= set(v["text"]["checks"])
    assert {"file_exists", "sha256", "size", "mp3_format", "duration", "provider_metadata", "narrates_package_text"} <= set(v["audio"]["checks"])
    if store.svg(WHILE_ID, pkg["code"]["variant"], pkg["diagram"]["variant"]) is not None:
        assert {"svg_sha256", "svg_min_size", "svg_valid_xml_and_nodes", "svg_derived_from_mermaid"} <= set(v["diagram"]["checks"])
    if store.cpp(WHILE_ID, pkg["code"]["variant"]) is not None:
        assert {"cpp_extension", "cpp_sha256", "cpp_compiles_and_runs", "cpp_not_python"} <= set(v["code"]["checks"])


@pytest.mark.parametrize("modality,mutate,failing", [
    ("code", lambda p: p["code"].update(source=""), "code.present"),
    ("code", lambda p: p["code"].update(source=p["code"]["source"] + "\nassert 1 == 1\n"), "code.sha256"),
    ("diagram", lambda p: p["diagram"].update(mermaid=""), "diagram.present"),
    ("diagram", lambda p: p["diagram"].update(derived_from="0" * 64), "diagram.derived_from_code"),
    ("text", lambda p: p["text"].update(text=""), "text.present"),
    ("text", lambda p: p["text"].update(concept_id="otro"), "text.concept"),
    ("text", lambda p: p["text"].update(text="Hola. " * 3), "text.sha256"),
    ("audio", lambda p: p["audio"].update(path=""), "audio.present"),
    ("audio", lambda p: p["audio"].update(sha256="f" * 64), "audio.sha256"),
    ("audio", lambda p: p["audio"].update(derived_from="0" * 64), "audio.narrates_package_text"),
])
def test_package_is_invalid_when_a_required_modality_is_missing_or_tampered(store, pkg, modality, mutate, failing):
    bad = copy.deepcopy({k: pkg[k] for k in ("package_id", "cycle_id", "concept_id", "library_version", "S", "code", "diagram", "text", "audio", "chain_valid")})
    mutate(bad)
    v = validate_package(bad, store)
    assert not v.valid and any(e.startswith(failing) for e in v.errors), v.errors


def test_missing_whole_modality_makes_the_package_invalid(store, pkg):
    bad = {k: pkg[k] for k in ("package_id", "cycle_id", "concept_id", "library_version", "S", "code", "diagram", "text", "audio", "chain_valid")}
    bad = copy.deepcopy(bad)
    bad["audio"] = {}
    assert not validate_package(bad, store).valid


async def test_orchestrator_refuses_to_deliver_an_invalid_package(store, profiles, monkeypatch):
    import uuid
    from adaptation_swarm.multimodal import validation as V
    real = V.validate_package

    def broken(pkg, store):
        pkg = copy.deepcopy(pkg)
        pkg["audio"] = {}
        return real(pkg, store)

    monkeypatch.setattr("adaptation_swarm.agents.ag0_swarm_orchestrator.validate_package", broken)
    async with SwarmStack(library_version=store.version, prefix=f"swarm-test-{uuid.uuid4().hex[:8]}:") as st:
        r = await st.orchestrator.run_cycle(profiles["syn-visual_dominant-repetitive-r0"], batch_seed=1)
        await st.bus.purge_prefix()
    assert r.status == "failed" and r.stop_reason == "error" and r.package is None and "paquete inválido" in r.error["message"]
