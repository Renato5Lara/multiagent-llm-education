"""AG1–AG4 y biblioteca M1: mensajes por Redis real, integridad por hash, artefactos REALMENTE generados
(código validado en sandbox, diagrama derivado del AST, texto con vocabulario del ancla, audio MP3 real)."""

import asyncio
import copy
import io
import json
import shutil

import pytest
from mutagen.mp3 import MP3

from adaptation_swarm.agents.ag1_profil_agent import ProfilAgent
from adaptation_swarm.agents.ag2_code_agent import CodeAgent, _structure, extract_code
from adaptation_swarm.agents.ag3_diagram_agent import DiagramAgent
from adaptation_swarm.agents.ag4_text_agent import AUDIO_PROFILES, TextAgent
from adaptation_swarm.multimodal.flowchart import build_flowchart, validate_flowchart
from adaptation_swarm.multimodal.library import LibraryStore, LibraryWriter, variant_key
from adaptation_swarm.multimodal.versioning import format_version, manifest_hash
from adaptation_swarm.schemas.errors import LibraryIntegrityError, LibraryMissError, ProfileError
from adaptation_swarm.schemas.ids import sha256_bytes, sha256_text
from adaptation_swarm.schemas.messages import AgentId, BusMessage, MessageType
from tests.adaptation_swarm.conftest import WHILE_ID


async def _ask(bus, agent, receiver, mtype, payload, *, n_replies=1, timeout=5.0):
    """Publica una petición AG0→agente por Redis y recoge las respuestas que llegan a AG0."""
    await bus.ensure_group(AgentId.AG0)
    req = BusMessage(correlation_id="t-corr", cycle_id="t-cyc", sender=AgentId.AG0, receiver=receiver,
                     message_type=mtype, request_key="k", payload=payload)
    stop = asyncio.Event()
    task = asyncio.create_task(agent.run(stop))
    await asyncio.sleep(0.2)
    await bus.publish(req)
    out = []
    deadline = asyncio.get_event_loop().time() + timeout
    while len(out) < n_replies and asyncio.get_event_loop().time() < deadline:
        for eid, m in await bus.read(AgentId.AG0, "t", block_ms=200):
            out.append(m)
            await bus.ack(AgentId.AG0, eid)
    stop.set()
    await task
    return req, out


# ── AG1 ────────────────────────────────────────────────────────────────────
async def test_ag1_replies_w_over_redis_and_is_deterministic(bus, slice_profile):
    payload = {"profile": slice_profile.model_dump(mode="json")}
    _, r1 = await _ask(bus, ProfilAgent(bus), AgentId.AG1, MessageType.PROFILE_REQUEST, payload)
    assert len(r1) == 1 and r1[0].message_type is MessageType.W_READY and r1[0].sender is AgentId.AG1
    p = r1[0].payload
    assert abs(sum(p["W_list"]) - 1) < 1e-9 and p["profile_id"] == slice_profile.profile_id
    assert p["archetype"] == "visual_dominant" and p["difficulty"] == "repetitive" and p["concept_id"] == WHILE_ID
    assert p["generation"]["agent"] == "AG1" and "rule_version" in p["generation"] and len(p["heuristic_start"]) == 8
    assert ProfilAgent(None).build_weights(payload["profile"]) == p         # determinista


async def test_ag1_invalid_profile_returns_explicit_error_and_no_silence(bus):
    _, r = await _ask(bus, ProfilAgent(bus), AgentId.AG1, MessageType.PROFILE_REQUEST, {"profile": {"profile_id": "x"}})
    assert len(r) == 1 and r[0].message_type is MessageType.ERROR and r[0].status == "error"
    assert r[0].error["code"] == "ProfileError"
    with pytest.raises(ProfileError):
        ProfilAgent(None).build_weights({"nivel": 3})


async def test_agent_is_idempotent_on_duplicate_message(bus, slice_profile):
    await bus.ensure_group(AgentId.AG0)
    agent = ProfilAgent(bus)
    stop = asyncio.Event()
    task = asyncio.create_task(agent.run(stop))
    await asyncio.sleep(0.2)
    req = BusMessage(correlation_id="c", cycle_id="dup", sender=AgentId.AG0, receiver=AgentId.AG1,
                     message_type=MessageType.PROFILE_REQUEST, request_key="profile",
                     payload={"profile": slice_profile.model_dump(mode="json")})
    await bus.publish(req)
    await bus.publish(req)                    # el mismo message_id llega dos veces
    await asyncio.sleep(0.6)
    stop.set()
    await task
    replies = [m for m in await bus.read_log("dup") if m.message_type is MessageType.W_READY]
    assert agent.handled == 1 and len(replies) == 1


# ── AG2/AG3/AG4 sobre la biblioteca real (por el bus) ─────────────────────────
async def test_ag2_ag3_ag4_realize_candidates_via_redis_with_hash_chain(bus, store):
    _, code = await _ask(bus, CodeAgent(bus, store), AgentId.AG2, MessageType.CODE_REQUEST, {"concept_id": WHILE_ID, "variant": 1})
    _, diag = await _ask(bus, DiagramAgent(bus, store), AgentId.AG3, MessageType.DIAGRAM_REQUEST,
                         {"concept_id": WHILE_ID, "code_variant": 1, "diagram_variant": 2})
    _, txt = await _ask(bus, TextAgent(bus, store), AgentId.AG4, MessageType.TEXT_REQUEST,
                        {"concept_id": WHILE_ID, "text_variant": 2, "audio_variant": 0}, n_replies=2)
    c, d = code[0].payload, diag[0].payload
    assert code[0].message_type is MessageType.CODE_READY and c["sha256"] == sha256_text(c["code"])
    assert d["derived_from"] == c["sha256"]                       # el diagrama sale del código pedido
    types = {m.message_type for m in txt}
    assert types == {MessageType.TEXT_READY, MessageType.AUDIO_READY}
    t = next(m.payload for m in txt if m.message_type is MessageType.TEXT_READY)
    a = next(m.payload for m in txt if m.message_type is MessageType.AUDIO_READY)
    assert a["derived_from"] == t["sha256"] == sha256_text(t["text"])   # el audio narra ESE texto
    assert a["provider"]["name"] == "openai" and a["provider"]["input_sha256"] == t["sha256"]


async def test_missing_candidate_is_an_explicit_error_never_invented(bus, store):
    _, r = await _ask(bus, CodeAgent(bus, store), AgentId.AG2, MessageType.CODE_REQUEST, {"concept_id": "no-existe", "variant": 0})
    assert r[0].message_type is MessageType.ERROR and r[0].error["code"] == "LibraryMissError"


# ── biblioteca: completitud, trazabilidad e integridad ────────────────────────
def test_library_covers_81_combinations_with_full_traceability(store):
    assert store.is_complete(WHILE_ID)
    entries = [e for e in store.manifest["entries"] if e["concept_id"] == WHILE_ID]
    assert {m: sum(1 for e in entries if e["modality"] == m) for m in ("code", "diagram", "text", "audio")} == \
        {"code": 3, "diagram": 9, "text": 3, "audio": 9}
    for e in entries:
        for f in ("content_id", "anchor_version", "sha256", "generated_at", "generator", "prompt_template_version",
                  "provider", "validation", "generation_ms", "path"):
            assert e[f] not in (None, ""), (e["modality"], e["key"], f)
        assert e["generator"]["agent"] in {"AG2", "AG3", "AG4"} and e["validation"]["status"] == "passed"
    assert len({e["content_id"] for e in entries}) == len(entries)         # content_id único
    assert store.version.startswith("lib-v") and manifest_hash(store.manifest) == store.version.rsplit("-", 1)[1]


@pytest.mark.requires_library_audio
def test_library_artifacts_are_real_and_valid(store):
    anchor = store.anchor(WHILE_ID)
    from app.services.cmg_concept_catalog import obtener_plantilla
    ref = obtener_plantilla("Bucle while")
    for v in range(3):
        code = store.code(WHILE_ID, v)
        assert code.sha256 == sha256_bytes(code.content)
        assert all(f in code.text for f in anchor.function_names)
        assert _structure(code.text) != _structure(ref.code)                # no es copia del código de referencia
        assert code.entry["validation"]["sandbox_status"] == "success" and code.entry["generator"]["agent"] == "AG2"
        for d in range(3):
            dia = store.diagram(WHILE_ID, v, d)
            assert dia.text == build_flowchart(code.text, d) + "\n"        # derivado del AST real, reproducible
            assert validate_flowchart(dia.text) == [] and dia.entry["derived_from"] == code.sha256
    for t in range(3):
        text = store.text(WHILE_ID, t)
        assert TextAgent.check_text(anchor, text.text.strip(), t) is None
        for a in range(3):
            au = store.audio(WHILE_ID, t, a, load=True)
            info = MP3(io.BytesIO(au.content)).info
            assert info.length > 3.0 and au.entry["size_bytes"] == len(au.content) > 10_000
            assert au.entry["provider"]["input_sha256"] == text.sha256 == au.entry["derived_from"]
            assert au.entry["provider"]["speed"] == AUDIO_PROFILES[a]["speed"]
    assert store.audio(WHILE_ID, 1, 0, load=True).content != store.audio(WHILE_ID, 1, 2, load=True).content


@pytest.mark.integration
async def test_library_code_passes_reference_tests_in_real_sandbox(store):
    from app.services.cmg_concept_catalog import obtener_plantilla
    ag2 = CodeAgent(None, store)
    tests = obtener_plantilla("Bucle while").tests
    for v in range(3):
        status, ms, detail = await ag2.validate_in_sandbox(store.code(WHILE_ID, v).text, tests)
        assert status == "success", detail


@pytest.mark.integration
async def test_sandbox_validation_rejects_wrong_and_unsafe_code(store):
    ag2 = CodeAgent(None, store)
    tests = "assert contar_hasta(3) == [1, 2, 3]\n"
    bad, _, _ = await ag2.validate_in_sandbox("def contar_hasta(n):\n    return []\n", tests)
    unsafe, _, detail = await ag2.validate_in_sandbox("import os\ndef contar_hasta(n):\n    return list(range(1, n + 1))\n", tests)
    assert bad != "success" and unsafe == "security_violation" and "os" in detail


def test_library_integrity_detects_tampering(store, tmp_path):
    root = tmp_path / "lib"
    shutil.copytree(store.dir, root / store.version)
    ok = LibraryStore(root, store.version)
    rel = ok.entry(WHILE_ID, "code", "c0")["path"]
    (root / store.version / rel).write_text("def contar_hasta(n):\n    return []\n")   # artefacto adulterado
    with pytest.raises(LibraryIntegrityError):
        LibraryStore(root, store.version).code(WHILE_ID, 0)
    mpath = root / store.version / "manifest.json"
    m = json.loads(mpath.read_text())
    m["entries"][0]["sha256"] = "0" * 64
    mpath.write_text(json.dumps(m))
    with pytest.raises(LibraryIntegrityError):                                          # manifiesto adulterado
        LibraryStore(root, store.version)


def test_library_detects_broken_derivation_chain(store, tmp_path):
    root = tmp_path / "lib"
    m = copy.deepcopy(store.manifest)
    for e in m["entries"]:
        if e["modality"] == "diagram" and e["concept_id"] == WHILE_ID and e["key"] == "c0d0":
            e["derived_from"] = "f" * 64
    m.pop("library_version")
    version = format_version(99, m)
    m["library_version"] = version
    shutil.copytree(store.dir, root / version)
    (root / version / "manifest.json").write_text(json.dumps(m, sort_keys=True))
    broken = LibraryStore(root, version)
    with pytest.raises(LibraryIntegrityError):
        broken.diagram(WHILE_ID, 0, 0)
    assert broken.diagram(WHILE_ID, 0, 1).text                                          # el resto sigue íntegro


def test_library_miss_is_explicit(store):
    with pytest.raises(LibraryMissError):
        store.code("otro-concepto", 0)
    with pytest.raises(LibraryMissError):
        store.anchor("otro-concepto")
    with pytest.raises(LibraryMissError):
        LibraryStore.open(store.root, "lib-v999-deadbeef")


def test_sealed_versions_are_never_overwritten(store, tmp_path):
    root = tmp_path / "lib"
    w = LibraryWriter(root=root).begin()
    w.add_anchor(store.anchor(WHILE_ID))
    v1 = w.seal()
    w2 = LibraryWriter(root=root, base_version=v1).begin()
    v2 = w2.seal()
    assert v1 != v2 and v1.startswith("lib-v1-") and v2.startswith("lib-v2-")
    assert (root / v1 / "manifest.json").exists() and (root / v2 / "manifest.json").exists()


# ── AG2/AG4 unitarios ─────────────────────────────────────────────────────────
def test_ag2_variant_shape_and_code_extraction():
    ag2 = CodeAgent(None)
    plain = "def f(n):\n    return n\n"
    doc = 'def f(n):\n    """Doc."""\n    # paso\n    return n\n\ndef ejemplo_uso():\n    print(f(1))\n'
    assert ag2.check_variant_shape(plain, 0) is None and ag2.check_variant_shape(doc, 0) is not None
    assert ag2.check_variant_shape(plain, 1) is not None and ag2.check_variant_shape(doc, 1) is None
    assert ag2.check_variant_shape(doc.replace("ejemplo_uso", "otra"), 2) is not None and ag2.check_variant_shape(doc, 2) is None
    assert extract_code("```python\nx = 1\n```") == "x = 1\n" and extract_code("x = 1") == "x = 1\n"
    assert _structure('def f():\n    """d"""\n    return 1\n') == _structure("def f():\n    return 1\n")


def test_ag4_text_validation_rules(store):
    anchor = store.anchor(WHILE_ID)
    good = "Un bucle while repite instrucciones mientras se cumpla una condición. La función contar_hasta recibe n y guarda los valores en una lista hasta llegar a n."
    assert TextAgent.check_text(anchor, good, 0) is None
    assert "palabras" in TextAgent.check_text(anchor, "Un bucle while.", 0)
    assert "funciones" in TextAgent.check_text(anchor, good.replace("contar_hasta", "la función"), 0)
    assert "markdown" in TextAgent.check_text(anchor, good + " `while`", 0)


@pytest.mark.integration
async def test_tts_real_call_and_content_cache(tmp_path):
    from adaptation_swarm.tts.openai_tts import OpenAITTSProvider
    ag4 = TextAgent(None, tts=OpenAITTSProvider(), tts_cache_dir=tmp_path)
    text = "Un bucle repite instrucciones."
    a = await ag4.generate_audio(text, 0, 1)
    b = await ag4.generate_audio(text, 0, 1)
    r = a.result
    assert not a.cache_hit and b.cache_hit and a.result.output_sha256 == b.result.output_sha256
    assert r.provider == "openai" and r.model == "tts-1" and r.voice == "alloy" and r.format == "mp3"
    assert r.input_sha256 == sha256_text(text) and r.output_sha256 == sha256_bytes(r.audio) and len(r.audio) > 5_000
    assert r.duration_s and r.duration_s > 0.5


@pytest.mark.integration
async def test_ag2_generates_real_code_with_llm_and_sandbox(store):
    from app.services.cmg_concept_catalog import obtener_plantilla
    ref = obtener_plantilla("Bucle while")
    g = await CodeAgent(None, store).generate_variant(store.anchor(WHILE_ID), ref.code, ref.tests, 0)
    assert g.sandbox_status == "success" and g.model and g.tokens_total > 0 and g.attempts >= 1
    assert _structure(g.code) != _structure(ref.code) and "contar_hasta" in g.code


def test_ag2_rejects_module_level_calls():
    ag2 = CodeAgent(None)
    assert "nivel de módulo" in ag2.check_variant_shape("def f():\n    return 1\nf()\n", 0)
    assert ag2.check_variant_shape("total = 0\ndef f():\n    return 1\n", 0) is None


def test_extending_a_library_never_modifies_the_sealed_base(store, tmp_path):
    """Los artefactos se enlazan (hardlink) desde la versión base; reescribir uno en la versión nueva NO debe alterar la base."""
    anchor = store.anchor(WHILE_ID)
    kw = dict(anchor=anchor, modality="code", key="c0", variant={"code": 0}, agent="AG2", agent_version="t", generation_ms=1.0,
              derived_from=None, provider={"name": "t"}, prompt_template_version="t", validation={"status": "passed"})
    root = tmp_path / "lib"
    w1 = LibraryWriter(root=root).begin()
    w1.add_anchor(anchor)
    w1.add_artifact(data=b"version-1", **kw)
    v1 = w1.seal()
    w2 = LibraryWriter(root=root, base_version=v1).begin()
    w2.add_artifact(data=b"version-2", **kw)
    v2 = w2.seal()
    rel = f"artifacts/{WHILE_ID}/code_c0.py"
    assert (root / v1 / rel).read_bytes() == b"version-1" and (root / v2 / rel).read_bytes() == b"version-2"
    assert LibraryStore(root, v1).code(WHILE_ID, 0).content == b"version-1"          # v1 sigue íntegra (hash verificado)


def test_restore_concept_undoes_a_failed_regeneration(store, tmp_path):
    anchor = store.anchor(WHILE_ID)
    kw = dict(anchor=anchor, modality="code", key="c0", variant={"code": 0}, agent="AG2", agent_version="t", generation_ms=1.0,
              derived_from=None, provider={"name": "t"}, prompt_template_version="t", validation={"status": "passed"})
    root = tmp_path / "lib"
    w1 = LibraryWriter(root=root).begin()
    w1.add_anchor(anchor)
    w1.add_artifact(data=b"orig", **kw)
    base = LibraryStore(root, w1.seal())
    w2 = LibraryWriter(root=root, base_version=base.version).begin()
    mark = len(w2.changes)
    w2.add_artifact(data=b"nuevo", **kw)
    w2.changes.append({"x": 1})
    w2.restore_concept(base, WHILE_ID, mark)
    v2 = w2.seal()
    assert LibraryStore(root, v2).code(WHILE_ID, 0).content == b"orig" and LibraryStore(root, v2).manifest["changes"] == []
