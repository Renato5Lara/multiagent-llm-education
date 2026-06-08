"""
Tests for the experimental baseline: conditions, metrics, analysis, pipelines.

Test modules:
    TestConditions        — condition definitions, configure_engine(), hypotheses
    TestMetrics           — PerRunMetrics extraction, aggregation, entropy
    TestAnalysis          — ANOVA, pairwise tests, Cohen's d, power analysis
    TestPipeline          — BatchPipeline and SingleAgentPipeline
    TestReproducibility   — same seed → same results
"""

from __future__ import annotations

import math
import random

import pytest

from app.core.consensus import (
    ConsensusEngine,
    ConsensusResult,
    ConsensusVote,
    VoteContext,
    VoteDecision,
)
from app.core.trust import TrustSystem
from app.core.specialization import SpecializationTracker
from app.experiment.conditions import (
    FULL_SWARM,
    UNIFORM_WEIGHTS,
    SINGLE_AGENT,
    NO_TRUST,
    NO_SPECIALIZATION,
    ExperimentCondition,
    get_all_conditions,
    get_condition,
    get_controls,
    get_treatments,
    get_ablations,
    get_hypotheses,
)
from app.experiment.metrics import (
    PerRunMetrics,
    AggregatedMetrics,
    aggregate_metrics,
    compute_entropy,
    compute_variance,
    extract_metrics,
)
from app.experiment.analysis import (
    ANOVA,
    PairwiseTest,
    cohens_d,
    compute_anova,
    generate_statistical_report,
    pairwise_bonferroni,
    pairwise_holm,
    power_analysis,
    significance_matrix,
)


# ═══════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════

def _make_dummy_result(
    decision: VoteDecision = VoteDecision.APPROVE,
    confidence: float = 0.85,
    num_voters: int = 4,
    weights: dict[str, float] | None = None,
) -> ConsensusResult:
    """Build a minimal ConsensusResult for testing.

    Note: unanimous is a @property computed from votes, not stored.
    """
    votes = [
        ConsensusVote(
            voter_name=f"voter_{i}",
            decision=decision,
            confidence=confidence,
            reason="test",
            evidence={},
        )
        for i in range(num_voters)
    ]
    voter_timings = [
        {"voter_name": f"voter_{i}", "decision": decision.value,
         "confidence": confidence, "duration_ms": 10.0 + i, "status": "ok"}
        for i in range(num_voters)
    ]

    if weights is None:
        weights = {f"voter_{i}": 1.0 for i in range(num_voters)}

    return ConsensusResult(
        module_id="test-mod",
        student_id="test-stu",
        decision=decision,
        confidence=confidence,
        votes=votes,
        trace_id=None,
        voter_timings=voter_timings,
        weights_used=weights,
        trust_scores={f"voter_{i}": 0.9 for i in range(num_voters)},
        specialization_affinities={f"voter_{i}": 0.8 for i in range(num_voters)},
        memory_ids=[],
        inference_ids=[],
        timeout_info=None,
    )


# ═══════════════════════════════════════════════════════════════════
# Condition tests
# ═══════════════════════════════════════════════════════════════════

class TestConditions:
    """Verify condition definitions and configuration."""

    def test_all_conditions_present(self):
        all_c = get_all_conditions()
        names = [c.name for c in all_c]
        assert "full_swarm" in names
        assert "uniform_weights" in names
        assert "single_agent" in names
        assert "no_trust" in names
        assert "no_specialization" in names
        assert len(all_c) == 5

    def test_get_condition_by_name(self):
        c = get_condition("full_swarm")
        assert c is FULL_SWARM
        assert c.name == "full_swarm"

    def test_get_condition_invalid(self):
        with pytest.raises(KeyError):
            get_condition("nonexistent")

    def test_control_conditions(self):
        controls = get_controls()
        names = [c.name for c in controls]
        assert "uniform_weights" in names
        assert "single_agent" in names

    def test_treatment_conditions(self):
        treatments = get_treatments()
        names = [c.name for c in treatments]
        assert "full_swarm" in names

    def test_ablation_conditions(self):
        ablations = get_ablations()
        names = [c.name for c in ablations]
        assert "no_trust" in names
        assert "no_specialization" in names

    def test_configure_full_swarm(self):
        ts = TrustSystem()
        spec = SpecializationTracker()
        kwargs = FULL_SWARM.configure_engine(
            ConsensusEngine(), trust_system=ts, specialization_tracker=spec,
        )
        assert kwargs["trust_system"] is ts
        assert kwargs["specialization_tracker"] is spec

    def test_configure_uniform_weights(self):
        ts = TrustSystem()
        spec = SpecializationTracker()
        kwargs = UNIFORM_WEIGHTS.configure_engine(
            ConsensusEngine(), trust_system=ts, specialization_tracker=spec,
        )
        assert kwargs["trust_system"] is None
        assert kwargs["specialization_tracker"] is None

    def test_configure_no_trust(self):
        ts = TrustSystem()
        spec = SpecializationTracker()
        kwargs = NO_TRUST.configure_engine(
            ConsensusEngine(), trust_system=ts, specialization_tracker=spec,
        )
        assert kwargs["trust_system"] is None
        assert kwargs["specialization_tracker"] is spec

    def test_configure_no_specialization(self):
        ts = TrustSystem()
        spec = SpecializationTracker()
        kwargs = NO_SPECIALIZATION.configure_engine(
            ConsensusEngine(), trust_system=ts, specialization_tracker=spec,
        )
        assert kwargs["trust_system"] is ts
        assert kwargs["specialization_tracker"] is None

    def test_hypotheses_are_formulated(self):
        hypotheses = get_hypotheses()
        assert len(hypotheses) == 8
        for h in hypotheses:
            assert h.startswith("H")

    def test_all_have_short_labels(self):
        for c in get_all_conditions():
            assert c.short_label

    def test_single_agent_configure_empty(self):
        kwargs = SINGLE_AGENT.configure_engine(ConsensusEngine())
        assert kwargs == {}


# ═══════════════════════════════════════════════════════════════════
# Metrics tests
# ═══════════════════════════════════════════════════════════════════

class TestMetrics:
    """Verify PerRunMetrics extraction and aggregation."""

    def test_extract_metrics_basic(self):
        result = _make_dummy_result()
        m = extract_metrics(result, "full_swarm", 0)
        assert m.condition_name == "full_swarm"
        assert m.decision == "approve"
        assert m.confidence == 0.85
        assert m.num_voters == 4
        assert m.total_latency_ms == pytest.approx(46.0, rel=0.1)  # 10+11+12+13

    def test_extract_metrics_with_ground_truth(self):
        result = _make_dummy_result(decision=VoteDecision.APPROVE)
        m = extract_metrics(result, "test", 0, ground_truth=VoteDecision.APPROVE)
        assert m.correct is True

        m2 = extract_metrics(result, "test", 0, ground_truth=VoteDecision.REJECT)
        assert m2.correct is False

    def test_extract_metrics_no_ground_truth(self):
        result = _make_dummy_result()
        m = extract_metrics(result, "test", 0)
        assert m.correct is None

    def test_extract_metrics_weight_entropy(self):
        weights = {"a": 0.5, "b": 0.5}
        result = _make_dummy_result(weights=weights)
        m = extract_metrics(result, "test", 0)
        expected = -(0.5 * math.log(0.5) + 0.5 * math.log(0.5))
        assert m.weight_entropy == pytest.approx(expected, rel=0.01)

    def test_extract_metrics_no_weights(self):
        result = _make_dummy_result(weights={})
        m = extract_metrics(result, "test", 0)
        assert m.weight_entropy is None

    def test_entropy_uniform(self):
        e = compute_entropy({"a": 1.0, "b": 1.0})
        expected = -(0.5 * math.log(0.5) + 0.5 * math.log(0.5))
        assert e == pytest.approx(expected, rel=0.01)

    def test_entropy_single_voter(self):
        e = compute_entropy({"a": 1.0})
        assert e == pytest.approx(0.0)

    def test_entropy_empty(self):
        e = compute_entropy({})
        assert e == 0.0

    def test_variance_single(self):
        assert compute_variance([1.0]) == 0.0

    def test_variance_multiple(self):
        v = compute_variance([1.0, 3.0])
        assert v == pytest.approx(2.0)

    def test_aggregate_metrics_empty(self):
        agg = aggregate_metrics([])
        assert agg.n_runs == 0

    def test_aggregate_metrics_single_run(self):
        result = _make_dummy_result(decision=VoteDecision.APPROVE)
        m = extract_metrics(result, "test", 0, ground_truth=VoteDecision.APPROVE)
        agg = aggregate_metrics([m])
        assert agg.condition_name == "test"
        assert agg.n_runs == 1
        assert agg.accuracy == 1.0

    def test_aggregate_metrics_multiple(self):
        ms = []
        for i in range(10):
            dec = VoteDecision.APPROVE if i < 7 else VoteDecision.REJECT
            result = _make_dummy_result(decision=dec)
            m = extract_metrics(result, "test", i, ground_truth=VoteDecision.APPROVE)
            ms.append(m)
        agg = aggregate_metrics(ms)
        assert agg.n_runs == 10
        assert agg.accuracy == pytest.approx(0.7, rel=0.01)

    def test_aggregate_entropy(self):
        weights = {"a": 0.8, "b": 0.2}
        ms = []
        for i in range(5):
            result = _make_dummy_result(weights=weights)
            m = extract_metrics(result, "test", i)
            ms.append(m)
        agg = aggregate_metrics(ms)
        assert agg.avg_weight_entropy is not None
        assert agg.avg_weight_entropy > 0

    def test_aggregate_no_weight_entropy(self):
        ms = []
        for i in range(5):
            result = _make_dummy_result(weights={})
            m = extract_metrics(result, "test", i)
            ms.append(m)
        agg = aggregate_metrics(ms)
        assert agg.avg_weight_entropy is None

    def test_metric_to_dict(self):
        result = _make_dummy_result()
        m = extract_metrics(result, "test", 0)
        d = m.to_dict()
        assert d["condition"] == "test"
        assert d["decision"] == "approve"

    def test_aggregated_summary_string(self):
        result = _make_dummy_result(decision=VoteDecision.APPROVE)
        m = extract_metrics(result, "test", 0, ground_truth=VoteDecision.APPROVE)
        agg = aggregate_metrics([m])
        assert "test" in agg.summary
        assert "Accuracy" in agg.summary


# ═══════════════════════════════════════════════════════════════════
# Analysis tests
# ═══════════════════════════════════════════════════════════════════

class TestAnalysis:
    """Verify statistical analysis functions."""

    def test_cohens_d_identical(self):
        d = cohens_d([1.0, 1.0, 1.0], [1.0, 1.0, 1.0])
        assert d == 0.0

    def test_cohens_d_different(self):
        # Data with non-zero variance
        d = cohens_d([0.1, 0.2, 0.3], [0.8, 0.9, 1.0])
        assert abs(d) > 1.0  # large effect

    def test_cohens_d_small_sample(self):
        d = cohens_d([1.0], [2.0])
        assert d == 0.0

    def test_cohens_d_zero_variance(self):
        d = cohens_d([1.0, 1.0], [1.0, 1.0])
        assert d == 0.0

    def test_anova_two_groups(self):
        groups = {"A": [0.5, 0.6, 0.7], "B": [0.8, 0.9, 1.0]}
        result = compute_anova(groups)
        assert result.n_groups == 2
        assert result.f_statistic > 0

    def test_anova_identical_groups(self):
        groups = {"A": [0.5, 0.5, 0.5], "B": [0.5, 0.5, 0.5]}
        result = compute_anova(groups)
        assert result.f_statistic == pytest.approx(0.0, abs=0.01)

    def test_anova_fewer_than_two(self):
        with pytest.raises(ValueError):
            compute_anova({"A": [1.0, 2.0]})

    def test_pairwise_bonferroni(self):
        groups = {
            "A": [0.5, 0.6, 0.7],
            "B": [0.8, 0.9, 1.0],
            "C": [0.4, 0.5, 0.6],
        }
        results = pairwise_bonferroni(groups, alpha=0.10)
        assert len(results) == 3  # 3 choose 2
        for r in results:
            assert r.method == "bonferroni"
            assert r.n_a == 3
            assert r.n_b == 3

    def test_pairwise_holm(self):
        groups = {"A": [0.5, 0.6], "B": [0.8, 0.9], "C": [0.4, 0.5]}
        results = pairwise_holm(groups)
        assert len(results) == 3
        # Holm sorts by p-value; first should have lowest p
        assert results[0].p_value <= results[1].p_value

    def test_pairwise_holm_vs_bonferroni(self):
        groups = {"A": [0.5, 0.6], "B": [0.8, 0.9], "C": [0.4, 0.5]}
        bonf = pairwise_bonferroni(groups)
        holm = pairwise_holm(groups)
        # Holm corrected p-values should be ≤ Bonferroni corrected p-values
        for br, hr in zip(bonf, holm):
            if hr.group_a == br.group_a and hr.group_b == br.group_b:
                assert hr.corrected_p <= br.corrected_p or abs(hr.corrected_p - br.corrected_p) < 0.001

    def test_power_analysis(self):
        n = power_analysis(effect_size=0.5, alpha=0.05, power=0.80)
        assert n >= 3

    def test_power_analysis_large_effect(self):
        n = power_analysis(effect_size=1.0, alpha=0.05, power=0.80)
        small = power_analysis(effect_size=0.2, alpha=0.05, power=0.80)
        assert n < small  # larger effect → smaller sample needed

    def test_power_analysis_zero_effect(self):
        n = power_analysis(effect_size=0.0)
        assert n == 0

    def test_power_analysis_with_correction(self):
        # Use a smaller effect size so the correction has visible impact
        n_one = power_analysis(0.2, n_groups=1)
        n_five = power_analysis(0.2, n_groups=5)
        # More groups → stricter correction → larger sample
        assert n_five >= n_one

    def test_regression_analysis_deterministic(self):
        groups = {"A": [0.6, 0.7], "B": [0.8, 0.9]}
        r1 = pairwise_bonferroni(groups)
        r2 = pairwise_bonferroni(groups)
        assert r1[0].p_value == r2[0].p_value
        assert r1[0].cohens_d == r2[0].cohens_d

    def test_significance_matrix(self):
        groups = {"A": [0.5, 0.6], "B": [0.8, 0.9], "C": [0.4, 0.5]}
        results = pairwise_bonferroni(groups)
        matrix = significance_matrix(results)
        assert "A" in matrix
        assert "B" in matrix
        assert "C" in matrix
        assert "ns" in matrix or "*" in matrix

    def test_statistical_report(self):
        groups = {"A": [0.5, 0.6], "B": [0.8, 0.9]}
        report = generate_statistical_report(groups, metric_name="accuracy")
        assert "ANOVA" in report
        assert "Bonferroni" in report
        assert "Holm" in report
        assert "Power" in report
        assert "matrix" in report

    def test_statistical_report_single_group(self):
        # Single group: ANOVA raises, report handles gracefully
        report = generate_statistical_report({"A": [0.5, 0.6]})
        assert "ANOVA skipped" in report or "ANOVA" in report


# ═══════════════════════════════════════════════════════════════════
# Pipeline tests
# ═══════════════════════════════════════════════════════════════════

class TestPipeline:
    """Verify BatchPipeline and SingleAgentPipeline."""

    @pytest.mark.asyncio
    async def test_batch_pipeline_runs(self):
        engine = ConsensusEngine()
        from app.experiment.pipelines import BatchPipeline

        pipeline = BatchPipeline(engine, seed=42)
        contexts = [
            _make_minimal_ctx("mod-1", "stu-1", score=0.8),
            _make_minimal_ctx("mod-2", "stu-2", score=0.3),
        ]
        result = await pipeline.run(contexts, n_runs=2, label="test")
        assert len(result.runs) > 0
        assert "full_swarm" in result.aggregated
        assert result.seed == 42

    @pytest.mark.asyncio
    async def test_single_agent_pipeline(self):
        engine = ConsensusEngine()
        from app.experiment.pipelines import SingleAgentPipeline

        pipeline = SingleAgentPipeline(voter_name="MasteryVoter")
        ctx = _make_minimal_ctx("mod-1", "stu-1")
        pr = await pipeline.run(engine, ctx, run_index=0)
        assert pr.condition == "single_agent"
        assert pr.decision in ("approve", "reject", "abstain")
        assert pr.metrics.num_voters == 1

    @pytest.mark.asyncio
    async def test_full_baseline(self):
        from app.experiment.pipelines import run_full_baseline

        engine = ConsensusEngine()
        contexts = [
            _make_minimal_ctx("mod-1", "stu-1", score=0.9),
            _make_minimal_ctx("mod-2", "stu-2", score=0.2),
        ]
        result = await run_full_baseline(
            engine, contexts,
            seed=42, n_runs=2, label="test-full",
        )
        assert len(result.runs) >= 5 * 2 * 2  # 5 conditions * 2 contexts * 2 runs
        assert "single_agent" in result.aggregated
        assert "full_swarm" in result.aggregated


def _make_minimal_ctx(
    module_id: str,
    student_id: str,
    score: float = 0.7,
) -> VoteContext:
    """Minimal VoteContext for pipeline testing."""
    from datetime import datetime, timezone

    class FakeUOW:
        db = None

    class FakeModule:
        def __init__(self):
            self.id = module_id
            self.title = "Test Module"
            self.module_type = "exercise"
            self.bloom_level = "3"
            self.difficulty = 0.5

    class FakePath:
        def __init__(self):
            self.id = f"path-{module_id}"

    return VoteContext(
        uow=FakeUOW(),
        module_id=module_id,
        student_id=student_id,
        course_id=f"course-{module_id[:4]}",
        path_id=f"path-{module_id}",
        score=score,
        module=FakeModule(),
        path=FakePath(),
        timestamp=datetime.now(timezone.utc),
    )


# ═══════════════════════════════════════════════════════════════════
# Reproducibility tests
# ═══════════════════════════════════════════════════════════════════

class TestReproducibility:
    """Verify same seed → same experimental results."""

    @pytest.mark.asyncio
    async def test_same_seed_same_results(self):
        from app.experiment.pipelines import BatchPipeline

        engine = ConsensusEngine()
        contexts = [
            _make_minimal_ctx("mod-1", "stu-1", score=0.7),
        ]

        p1 = BatchPipeline(engine, seed=42)
        r1 = await p1.run(contexts, n_runs=1, label="test")

        # Fresh engine, same seed
        engine2 = ConsensusEngine()
        p2 = BatchPipeline(engine2, seed=42)
        r2 = await p2.run(contexts, n_runs=1, label="test")

        for cname in ["full_swarm", "uniform_weights", "no_trust", "no_specialization"]:
            a1 = r1.aggregated.get(cname)
            a2 = r2.aggregated.get(cname)
            if a1 and a2:
                assert a1.accuracy == a2.accuracy, f"Accuracy mismatch for {cname}: {a1.accuracy} vs {a2.accuracy}"
                assert a1.avg_confidence == a2.avg_confidence, f"Confidence mismatch for {cname}"
