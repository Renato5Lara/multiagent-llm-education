"""Convencional INDEPENDIENTE `decision_table` (OE2, Fase A): ejecutable, misma entrada/salida que la propuesta, sin PSO ni heurística del enjambre, reproducible, con tiempo de decisión medido; clasificación
explícita de `rules` / `bruteforce`; endpoint baseline que lo selecciona y lo distingue; y captura de `t_conv_ms` de AMBOS endpoints en el log HTTP. Sin mocks de métricas: los tiempos son medidos."""

import ast
import inspect
from pathlib import Path

import httpx
import pytest

import adaptation_swarm.api.router as router_mod
from adaptation_swarm.baselines import conventional as conv
from adaptation_swarm.baselines import decision_table as dt
from adaptation_swarm.oe import http_window as hw
from adaptation_swarm.profiles.models import ProfileRequest
from adaptation_swarm.pso import engine
from adaptation_swarm.pso.space import Configuration
from app.main import app

KEY = "test-key-dt"


def _profile(**kw) -> ProfileRequest:
    base = {"profile_id": "p", "nivel": 0.5, "tasa_error_previa": 0.2, "concept_id": "c", "estilo": {"w_v": 0.1, "w_a": 0.1, "w_t": 0.1, "w_c": 0.7}}
    return ProfileRequest.model_validate({**base, **kw})


# ── la tabla de decisión ────────────────────────────────────────────────────────────────────────────────────
def test_primary_modality_gets_emphasis_2_secondaries_by_threshold_and_depth_by_level():
    c = dt.decide(_profile(estilo={"w_v": 0.55, "w_a": 0.05, "w_t": 0.15, "w_c": 0.25}, nivel=0.9))
    assert c.emphasis == (1, 2, 0, 0)                      # (code, diagram, text, audio): código ≥ 0,25 → 1; diagrama primaria → 2; texto 0,15 y audio 0,05 → 0
    assert c.variants == (2, 2, 2, 2)                      # nivel ≥ 2/3 → profundidad 2
    assert dt.decide(_profile(nivel=0.1)).variants == (0, 0, 0, 0) and dt.decide(_profile(nivel=0.5)).variants == (1, 1, 1, 1)


def test_high_prior_error_lowers_depth_one_level_never_below_zero():
    assert dt.decide(_profile(nivel=0.9, tasa_error_previa=0.8)).variants == (1, 1, 1, 1)
    assert dt.decide(_profile(nivel=0.1, tasa_error_previa=0.8)).variants == (0, 0, 0, 0)
    assert dt.decide(_profile(nivel=0.9, tasa_error_previa=0.5)).variants == (2, 2, 2, 2)           # umbral estricto (> 0,5)


def test_tie_between_styles_follows_the_fixed_modality_priority_and_output_is_a_valid_configuration():
    c = dt.decide(_profile(estilo={"w_v": 0.25, "w_a": 0.25, "w_t": 0.25, "w_c": 0.25}))
    assert isinstance(c, Configuration) and len(c.vector) == 8 and all(v in (0, 1, 2) for v in c.vector)
    assert c.emphasis == (2, 1, 1, 1)                      # empate → código > diagrama > texto > audio
    assert dt.decide(_profile()) == dt.decide(_profile())                                          # determinista


# ── independencia del enjambre ──────────────────────────────────────────────────────────────────────────────
def test_decision_table_source_does_not_import_or_use_the_swarm_machinery():
    tree = ast.parse(Path(inspect.getsourcefile(dt)).read_text(encoding="utf-8"))
    imported = {n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)} | {a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
    assert imported <= {"__future__", "adaptation_swarm.profiles.models", "adaptation_swarm.pso.space"}          # solo el perfil y el espacio de configuración (la definición del problema)
    used = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)} | {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
    assert not used & {"heuristic_start", "compute_weights", "engine", "decode", "PSOParams", "evaluate", "FitnessWeights", "RedisBus", "SwarmOrchestrator", "SwarmStack", "replay_cycle"}


def test_decision_table_decides_without_calling_heuristic_start_or_pso(monkeypatch):
    def boom(*a, **k):
        raise AssertionError("el convencional independiente no debe llamar a la heurística ni al PSO")
    monkeypatch.setattr(conv, "heuristic_start", boom)
    monkeypatch.setattr(engine, "initialize", boom)
    monkeypatch.setattr(engine, "advance", boom)
    assert isinstance(dt.decide(_profile()), Configuration)


def test_rules_still_depends_on_the_swarm_heuristic_which_is_why_it_is_not_the_independent_convencional(monkeypatch):
    monkeypatch.setattr(conv, "heuristic_start", lambda W: (_ for _ in ()).throw(AssertionError("heuristic_start llamada")))
    adapter = conv.ConventionalAdapter.__new__(conv.ConventionalAdapter)
    adapter.system = "rules"
    with pytest.raises(AssertionError, match="heuristic_start"):
        adapter._decide(_profile(), object())
    adapter.system = "decision_table"
    S, F, evals = adapter._decide(_profile(), object())                      # W ni se mira: el convencional solo lee el perfil
    assert F is None and evals == 0 and S == dt.decide(_profile()).vector


def test_systems_are_classified_explicitly_without_mixing_semantics():
    assert conv.SYSTEM_ROLES == {"decision_table": "conventional_independent", "rules": "swarm_heuristic_ablation", "bruteforce": "reference_optimum"}
    assert set(conv.SYSTEM_ROLES) == set(conv.SYSTEMS) and len(set(conv.SYSTEM_ROLES.values())) == 3


# ── adaptador sobre la biblioteca real ──────────────────────────────────────────────────────────────────────
@pytest.mark.requires_library_audio
def test_adapter_is_executable_reproducible_and_times_its_decision(store, slice_profile):
    a = conv.ConventionalAdapter(store, "decision_table").adapt(slice_profile)
    b = conv.ConventionalAdapter(store, "decision_table").adapt(slice_profile)
    assert a.status == "completed" and a.error is None and a.n_evaluations == 0
    assert a.package["chain_valid"] and a.package["validation"]["valid"] and len(a.package["S"]) == 8 and a.package["code"]["source"] and a.package["audio"]["path"]
    assert a.S == list(dt.decide(slice_profile).vector) == b.S and a.F == b.F                    # misma entrada → misma salida; F evaluada con el mismo 𝓕 fuera del cronómetro
    assert a.t_conv_ms is None and a.decision_ms is not None and 0 < a.decision_ms <= a.total_ms        # sin convergencia iterativa: no se publica T_conv
    assert conv.ConventionalAdapter(store, "decision_table").adapt({"profile_id": "x"}).status == "failed"


# ── endpoint baseline ───────────────────────────────────────────────────────────────────────────────────────
@pytest.fixture
async def client(monkeypatch):
    monkeypatch.setenv("SWARM_API_KEY", KEY)
    monkeypatch.setenv("SWARM_API_PERSIST", "0")
    router_mod._stack = None
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        yield c


@pytest.mark.integration
@pytest.mark.requires_library_audio
@pytest.mark.parametrize("system, role", [("decision_table", "conventional_independent"), ("rules", "swarm_heuristic_ablation"), ("bruteforce", "reference_optimum")])
async def test_baseline_endpoint_selects_each_system_and_distinguishes_its_role(client, slice_profile, system, role):
    r = await client.post(f"/api/adaptation/baseline/{system}", json=slice_profile.model_dump(mode="json"), headers={"X-Swarm-Key": KEY})
    assert r.status_code == 200, r.text
    out = r.json()
    assert out["system"] == system and out["system_role"] == role
    m = out["metrics"]
    assert m["t_conv_ms"] is None and 0 < m["decision_ms"] <= m["total_ms"]
    assert hw.extract_cycle_metrics(out) == {"shape": "baseline", "t_conv_ms": None, "decision_ms": m["decision_ms"], "k_stop": None, "profile_id": out["profile_id"]}      # lo que el log HTTP captura del convencional


# ── captura de T_conv en el log HTTP ────────────────────────────────────────────────────────────────────────
def test_extract_cycle_metrics_reads_both_response_shapes_and_refuses_unknown_ones():
    assert hw.extract_cycle_metrics({"profile_id": "p", "t_conv_ms": 12.5, "decision_ms": 12.5, "k_stop": 3, "metrics": {"n_messages": 9}}) == {"shape": "swarm", "t_conv_ms": 12.5, "decision_ms": 12.5, "k_stop": 3, "profile_id": "p"}
    assert hw.extract_cycle_metrics({"profile_id": "q", "metrics": {"t_conv_ms": None, "decision_ms": 0.02, "total_ms": 5.0}}) == {"shape": "baseline", "t_conv_ms": None, "decision_ms": 0.02, "k_stop": None, "profile_id": "q"}
    with pytest.raises(ValueError, match="decision_ms"):                                          # la propuesta sin la métrica común no se acepta ni se rellena
        hw.extract_cycle_metrics({"t_conv_ms": 12.5, "k_stop": 3})
    for bad in ({}, {"metrics": None}, {"metrics": {"total_ms": 1.0}}, {"metrics": "x"}):
        with pytest.raises(ValueError, match="reconocibles"):
            hw.extract_cycle_metrics(bad)


def test_raw_log_marks_requests_without_metrics_and_the_summary_counts_them(tmp_path):
    csv_path = tmp_path / "raw.csv"
    rows = ["t_end_epoch_s,response_ms,ok,timeout,t_conv_ms,k_stop,metrics_ok,decision_ms,profile_id,user_index,seq_pos"]
    for i in range(900):
        rows.append(f"{1000 + i / 10:.3f},100.0,1,0,,,{0 if i % 100 == 0 else 1},{'' if i % 100 == 0 else 0.05},p{i % 3},0,{i}")      # convencional: sin T_conv, con decision_ms
    csv_path.write_text("\n".join(rows) + "\n", encoding="utf-8")
    raw = hw.read_raw(csv_path)
    assert sum(not r["metrics_ok"] for r in raw) == 9 and raw[1]["decision_ms"] == 0.05 and raw[0]["decision_ms"] is None and all(r["t_conv_ms"] is None for r in raw)
    s = hw.summarize_run(raw, [], users=1, system="decision_table", run_id="t")
    assert s["status"] == "ok" and s["requests_without_cycle_metrics"] >= 5 and s["decision_ms_mean"] == pytest.approx(0.05) and s["t_conv_ms_mean"] is None


def test_locust_plugin_uses_the_shared_extractor_and_does_not_swallow_failures():
    src = (Path(hw.__file__).with_name("locust_raw_log.py")).read_text(encoding="utf-8")
    assert "extract_cycle_metrics" in src and "metrics_ok" in src and "_log.warning" in src and "except Exception:\n                pass" not in src
