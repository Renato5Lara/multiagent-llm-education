"""OE2 Fase I.1 — integridad de los guards oficiales. P6 es un bloqueo real (compatibilidad técnica ≠ aprobación metodológica), el runner in-process usa la MISMA fuente metodológica que la campaña HTTP y las
decisiones internas F.2.3 no pueden aparecer como aprobadas por el asesor. No se cierra ninguna decisión: aquí solo se prueba que el código las REPRESENTA como pendientes."""
from __future__ import annotations

import pytest

from adaptation_swarm.oe import campaign_guards as guards, campaign_spec, definitions as defs, http_campaign as hc, runner, time_contract
from adaptation_swarm.oe.conditions import oe2_systems

OK_HW = {"vcpu": 20, "ram_gib": 31.75}                                  # cumple el criterio operativo del código
METHODOLOGICAL = {"B1", "B5", "B13", "P6", "PEND"}
SPEC = campaign_spec.SPEC["oe2"]


def _runner_gate(hw=OK_HW):
    v = runner.validity("oe2", hw=hw, n_profiles=100, k=10, batches=5, warmup=10, conditions=oe2_systems(1))
    return runner.official_gate(v)


def _http_gate():
    return hc.official_refusals(OK_HW, 10, 10.0, 60.0, None)


def _ids(reasons):
    return {r.split("[", 1)[1].split("]", 1)[0] for r in reasons if "[" in r}


def _green_methodology(monkeypatch):
    monkeypatch.setitem(time_contract.TTFC_CONTRACT, "status", time_contract.APPROVED_STATUS)
    monkeypatch.setattr(time_contract, "VALIDATION_STATUS", "VALIDATED")
    monkeypatch.setitem(SPEC["comparator_scope_validation"], "status", "VALIDATED")
    monkeypatch.setitem(SPEC["hardware_target_validation"], "status", campaign_spec.APPROVED_STATUS)
    monkeypatch.setitem(SPEC["persist_policy"], "status", campaign_spec.APPROVED_STATUS)
    for k, d in SPEC["methodological_decisions"].items():
        monkeypatch.setitem(SPEC["methodological_decisions"], k, {**d, "status": "DECIDED", "chosen": d["options"][0]})


# ═════════════════════════════ P6 ═════════════════════════════
def test_p6_is_a_real_blocker_and_technical_compatibility_does_not_resolve_it():
    spec = SPEC["hardware_target_validation"]
    assert spec["status"] == "PENDING_EXTERNAL_ANSWER" and spec["advisor_approved"] is False
    hs = guards.hardware_state(OK_HW)                                                       # A: compatible con el criterio operativo ...
    assert hs["technically_compatible"] is True and hs["methodologically_approved"] is False and hs["environment_class"] == "TECHNICALLY_COMPATIBLE_P6_PENDING"
    p6 = [b for b in guards.evaluate(None) if b.id == "P6"]                                  # ... pero P6 bloquea (B)
    assert len(p6) == 1 and p6[0].critical and p6[0].frozen and p6[0].kind == "methodological"
    assert any("[P6]" in r for r in _http_gate()) and any("[P6]" in r for r in _runner_gate())
    assert guards.hardware_state({"vcpu": 4, "ram_gib": 8.0})["environment_class"] == "PILOT"        # el criterio técnico no se tocó


def test_p6_can_only_be_resolved_by_its_explicit_approval_state_not_by_the_measured_hardware(monkeypatch):
    for status in ("PENDING_EXTERNAL_ANSWER", "VALIDATED", "TECHNICALLY_COMPATIBLE", None):
        monkeypatch.setitem(SPEC["hardware_target_validation"], "status", status)
        assert any(b.id == "P6" for b in guards.evaluate(None)), status
    monkeypatch.setitem(SPEC["hardware_target_validation"], "status", campaign_spec.APPROVED_STATUS)       # C: aprobado explícitamente en el futuro
    assert not any(b.id == "P6" for b in guards.evaluate(None)) and guards.hardware_state(OK_HW)["environment_class"] == "OFFICIAL_TARGET"
    assert guards.hardware_state({"vcpu": 4, "ram_gib": 8.0})["environment_class"] == "PILOT"                                    # aprobar P6 no relaja el hardware medido
    assert not any("[P6]" in r for r in _http_gate())


# ═════════════════════════════ runner in-process ═════════════════════════════
def _breaker(monkeypatch, blocker):
    {"B1": lambda: monkeypatch.setattr(time_contract, "VALIDATION_STATUS", "PENDING_METHODOLOGICAL_VALIDATION"),
     "B5": lambda: monkeypatch.setitem(SPEC["persist_policy"], "status", "FROZEN_PROVISIONAL_NOT_ADVISOR_APPROVED"),
     "B13": lambda: monkeypatch.setitem(SPEC["comparator_scope_validation"], "status", "PENDING_METHODOLOGICAL_VALIDATION"),
     "PEND": lambda: monkeypatch.setitem(SPEC["methodological_decisions"], "latency_statistic", {**SPEC["methodological_decisions"]["latency_statistic"], "status": "PENDING"}),
     "P6": lambda: monkeypatch.setitem(SPEC["hardware_target_validation"], "status", "PENDING_EXTERNAL_ANSWER")}[blocker]()


@pytest.mark.parametrize("blocker", ["B1", "B5", "B13", "PEND", "P6"])
def test_the_runner_gate_blocks_whenever_campaign_guards_block_that_methodological_decision(monkeypatch, blocker):
    _green_methodology(monkeypatch)
    assert not (_ids(_runner_gate()) & METHODOLOGICAL)                                       # todo resuelto ⇒ el runner no bloquea por metodología (el gate no es un candado fijo)
    _breaker(monkeypatch, blocker)
    assert _ids(_runner_gate()) & METHODOLOGICAL == {blocker}


@pytest.mark.parametrize("definition", ["common_time_indicator_oe2", "statistical_unit_performance"])
def test_the_runner_gate_blocks_while_these_definitions_are_pending(monkeypatch, definition):
    for k, v in list(defs.DEFINITIONS.items()):
        if v["status"] == defs.PENDING:
            monkeypatch.setitem(defs.DEFINITIONS, k, {**v, "status": defs.APPROVED})
    assert not any(r.startswith("definición bloqueada") for r in _runner_gate())
    monkeypatch.setitem(defs.DEFINITIONS, definition, {**defs.DEFINITIONS[definition], "status": defs.PENDING})
    assert f"definición bloqueada: {definition}" in _runner_gate()


# ═════════════════════════════ HTTP vs runner ═════════════════════════════
def test_http_and_runner_gates_take_the_same_methodological_decision_for_the_same_state(monkeypatch):
    assert _ids(_http_gate()) & METHODOLOGICAL == _ids(_runner_gate()) & METHODOLOGICAL == METHODOLOGICAL       # estado actual: mismos cinco bloqueos
    assert {b.id for b in guards.methodological_blockers("oe2")} == METHODOLOGICAL
    for broken in ("B1", "B5", "B13", "PEND", "P6"):
        with monkeypatch.context() as m:
            _green_methodology(m)
            _breaker(m, broken)
            assert _ids(_http_gate()) & METHODOLOGICAL == _ids(_runner_gate()) & METHODOLOGICAL == {broken}


def test_the_runner_official_dry_run_is_rejected_and_writes_nothing(tmp_path):
    out = tmp_path / "never"
    with pytest.raises(SystemExit) as exc:
        runner.main(["oe2", "--label", "i1", "--out-dir", str(out), "--official", "--dry-run"])
    assert "OFICIAL RECHAZADA" in str(exc.value) and not out.exists()


# ═════════════════════════════ decisiones internas ≠ aprobación del asesor ═════════════════════════════
INTERNAL = ["common_indicator_asymmetry", "cold_warm_policy", "errors_timeouts_in_l_resp", "execution_order", "holm_family_size", "http_pairing"]


def test_internal_decisions_are_never_advisor_approved_and_nothing_flips_it_automatically():
    decisions = SPEC["methodological_decisions"]
    for k in INTERNAL:
        d = decisions[k]
        assert d["advisor_approved"] is False and d["decision_level"] == "INTERNAL_STUDY_DECISION" and d["source"] == "internal_decision_F2.3" and d["decided_in"] == "F.2.3"
        assert d["status"] != campaign_spec.APPROVED_STATUS and "ADVISOR_APPROVED" not in str(d["status"])
    for k in ("latency_statistic", "l_resp_literal_hypothesis_h1"):
        assert decisions[k]["status"] == "PENDING" and decisions[k]["chosen"] is None and decisions[k]["advisor_approved"] is False
    d = campaign_spec._decided("x", ["x"], "q", "x", "r")                                    # el constructor de decisiones internas fija advisor_approved=False siempre
    assert d["advisor_approved"] is False and d["decision_level"] == "INTERNAL_STUDY_DECISION" and d["source"] == campaign_spec.INTERNAL_SOURCE
    assert SPEC["holm_design"]["advisor_backing"] == "NONE"


def test_resolving_the_guard_for_a_decision_does_not_make_it_advisor_approved(monkeypatch):
    decisions = SPEC["methodological_decisions"]
    monkeypatch.setitem(decisions, "latency_statistic", {**decisions["latency_statistic"], "status": "DECIDED", "chosen": "p95"})        # resolver el guard no escribe advisor_approved
    assert "latency_statistic" not in guards.pending_methodological_decisions() and decisions["latency_statistic"]["advisor_approved"] is False
