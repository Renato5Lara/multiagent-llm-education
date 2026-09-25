"""Métricas puras de ciclo/convergencia/rendimiento/búsqueda (deterministas, sin infraestructura; no declaran cumplimiento de umbrales).
La prueba de recursos con Redis real vive en `test_resources_integration.py` (integración)."""

import numpy as np
import pytest

from adaptation_swarm.metrics.convergence import convergence_rate, convergence_summary
from adaptation_swarm.metrics.cycle import CycleMetrics, comm_overhead_ms, inflight_overlap, parallel_overlap
from adaptation_swarm.metrics.performance import latency_report, percentile, throughput_rps
from adaptation_swarm.schemas.messages import AgentId, BusMessage, MessageType


def cm(reason, k, status="completed", ms=10.0):
    return CycleMetrics("c", "corr", "p", status, reason, k, ms, 20.0, 0.5)


def test_convergence_rate_is_share_of_epsilon_stops():
    ms = [cm("epsilon", 2)] * 3 + [cm("k_max", 15)] + [cm("error", None, "failed", None)]
    assert convergence_rate(ms) == pytest.approx(3 / 5)
    s = convergence_summary(ms)
    assert s["stop_reasons"] == {"epsilon": 3, "k_max": 1, "error": 1} and s["completed"] == 4 and s["failed"] == 1
    assert s["k_stop"]["max"] == 15 and s["CR"] == pytest.approx(0.6)
    with pytest.raises(ValueError):
        convergence_rate([])


def test_t_conv_reported_in_iterations_and_ms():
    m = cm("epsilon", 4, ms=123.4)
    assert m.t_conv_iterations == 4 and m.to_dict()["t_conv_ms"] == 123.4 and m.to_dict()["t_conv_iterations"] == 4


def test_percentiles_and_throughput():
    xs = list(range(1, 101))
    assert percentile(xs, 50) == pytest.approx(50.5) and percentile(xs, 95) == pytest.approx(95.05)
    assert percentile([], 50) is None and percentile([7], 99) == 7
    r = latency_report(xs)
    assert r["p50_ms"] < r["p90_ms"] < r["p95_ms"] < r["p99_ms"] <= r["max_ms"] == 100
    assert throughput_rps(120, 6.0) == 20.0
    with pytest.raises(ValueError):
        throughput_rps(1, 0)


def _pair(agent, recv, req_type, rep_type, t_req, t_rep, handler_ms=1.0, span=(0, 0)):
    req = BusMessage(correlation_id="c", cycle_id="y", sender=AgentId.AG0, receiver=agent, message_type=req_type, t_wall_ns=t_req)
    rep = BusMessage(correlation_id="c", cycle_id="y", sender=agent, receiver=AgentId.AG0, message_type=rep_type,
                     in_reply_to=req.message_id, t_wall_ns=t_rep,
                     timing={"agent": agent.value, "handler_ms": handler_ms, "t_recv_wall_ns": span[0], "t_done_wall_ns": span[1]})
    return [req, rep]


def test_comm_overhead_is_rtt_minus_handler_time():
    log = _pair(AgentId.AG2, None, MessageType.CODE_REQUEST, MessageType.CODE_READY, 0, 10_000_000, handler_ms=4.0)
    log += _pair(AgentId.AG3, None, MessageType.DIAGRAM_REQUEST, MessageType.DIAGRAM_READY, 0, 3_000_000, handler_ms=5.0)
    assert comm_overhead_ms(log) == pytest.approx(6.0 + 0.0)          # 10−4, y max(0, 3−5)


def test_parallelism_evidence():
    par = _pair(AgentId.AG2, None, MessageType.CODE_REQUEST, MessageType.CODE_READY, 0, 10, span=(2, 8)) \
        + _pair(AgentId.AG3, None, MessageType.DIAGRAM_REQUEST, MessageType.DIAGRAM_READY, 1, 9, span=(3, 7))
    seq = _pair(AgentId.AG2, None, MessageType.CODE_REQUEST, MessageType.CODE_READY, 0, 4, span=(1, 3)) \
        + _pair(AgentId.AG3, None, MessageType.DIAGRAM_REQUEST, MessageType.DIAGRAM_READY, 5, 9, span=(6, 8))
    assert parallel_overlap(par) and inflight_overlap(par)
    assert not parallel_overlap(seq) and not inflight_overlap(seq)


# ── casos límite de convergencia (DEC-10: la regla de parada NO se modifica; solo se reporta) ──────────────────────
def test_immediate_convergence_is_cr_one_with_a_single_iteration():
    ms = [cm("epsilon", 1, ms=5.0) for _ in range(4)]
    s = convergence_summary(ms)
    assert convergence_rate(ms) == 1.0 and s["CR"] == 1.0
    assert s["k_stop"] == {"mean": 1, "median": 1, "max": 1} and s["t_conv_ms"]["max"] == 5.0
    assert s["stop_reasons"] == {"epsilon": 4, "k_max": 0, "error": 0}


def test_k_max_exhaustion_is_not_counted_as_convergence():
    ms = [cm("k_max", 15) for _ in range(3)]
    s = convergence_summary(ms)
    assert convergence_rate(ms) == 0.0 and s["completed"] == 3 and s["k_stop"]["max"] == 15
    assert s["stop_reasons"] == {"epsilon": 0, "k_max": 3, "error": 0}


def test_failed_cycles_lower_cr_and_leave_iteration_and_time_stats_undefined_when_none_completed():
    ms = [cm("error", None, "failed", None) for _ in range(2)]
    s = convergence_summary(ms)
    assert s["CR"] == 0.0 and s["failed"] == 2 and s["completed"] == 0
    assert s["k_stop"] == {"mean": None, "median": None, "max": None} and s["t_conv_ms"] == {"mean": None, "median": None, "max": None}
    with pytest.raises(ValueError):
        convergence_summary([])


def test_latency_report_and_throughput_edge_cases():
    assert latency_report([]) == {"n": 0, "p50_ms": None, "p90_ms": None, "p95_ms": None, "p99_ms": None, "max_ms": None, "mean_ms": None}
    one = latency_report([42.0])
    assert one["p50_ms"] == one["p99_ms"] == one["max_ms"] == one["mean_ms"] == 42.0
    assert throughput_rps(0, 3.0) == 0.0


# ── calidad de búsqueda: óptimo global por fuerza bruta (biblioteca versionada, solo lectura, sin audio) ─────────────
def _fitness_of(store, concept_id, W, cfg, fw):
    from adaptation_swarm.fitness.coher import coher
    from adaptation_swarm.fitness.costt import costt
    from adaptation_swarm.fitness.fitness import evaluate
    from adaptation_swarm.fitness.redund import redund
    vc, vd, vt, _ = cfg.variants
    anchor = store.anchor(concept_id)
    code, diagram, text = store.code(concept_id, vc).text, store.diagram(concept_id, vc, vd).text, store.text(concept_id, vt).text
    return evaluate(cfg, W.by_modality(), coher(anchor, code, diagram, text).value, redund(anchor, code, diagram, text),
                    costt(cfg.variants, store.calibration()), fw).F


def test_brute_force_optimum_dominates_a_seeded_sample_of_the_search_space_and_is_reproducible(store):
    from adaptation_swarm.fitness.fitness import FitnessWeights
    from adaptation_swarm.metrics.search_quality import brute_force_optimum
    from adaptation_swarm.profiles.models import ModalityWeights
    from adaptation_swarm.pso.space import SPACE_SIZE, Configuration, all_configurations

    cid, fw = store.concepts()[0], FitnessWeights()
    W = ModalityWeights(w_v=0.6, w_a=0.1, w_t=0.1, w_c=0.2)
    opt = brute_force_optimum(store, cid, W, fw)
    assert brute_force_optimum(store, cid, W, fw) == opt                                    # determinista
    assert opt.n_optimal >= 1 and Configuration(opt.S).vector == opt.S
    assert _fitness_of(store, cid, W, Configuration(opt.S), fw) == pytest.approx(opt.F)      # F del óptimo recomputada de forma independiente
    configs = list(all_configurations())
    assert len(configs) == SPACE_SIZE == 6561
    rng = np.random.default_rng(7)
    for i in rng.integers(0, len(configs), size=150):
        assert _fitness_of(store, cid, W, configs[i], fw) <= opt.F + 1e-9                    # ninguna configuración lo supera
