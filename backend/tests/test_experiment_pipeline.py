"""Tests for Phase 3 experiment pipeline: dataset, evaluation, config, anomaly, export, replay."""

from __future__ import annotations

import json
import os
import tempfile
from unittest.mock import MagicMock

import pytest

from app.core.consensus import VoteDecision
from app.experiment.dataset import (
    ExperimentDataset,
    ExperimentScenario,
    GroundTruthConfig,
    ScenarioLabel,
    check_ground_truth_consistency,
    generate_synthetic_dataset,
)
from app.experiment.evaluation import (
    AgreementReport,
    ExpertEvaluationRound,
    agreement_matrix,
    evaluate_expert_agreement,
    fleiss_kappa,
    kappa_interpretation,
    per_category_agreement,
)
from app.experiment.config import (
    ExperimentConfig,
    ConfigVersion,
    ConfigSweep,
    save_config_snapshot,
    load_config_snapshot,
)
from app.experiment.anomaly import (
    detect_anomalies,
    detect_latency_anomalies,
    detect_confidence_anomalies,
)
from app.experiment.export import (
    export_all,
    export_to_csv,
    export_to_json,
    export_latex_table,
    export_summary,
)
from app.experiment.replay import verify_reproducibility


# ═══════════════════════════════════════════════════════════
# DATASET TESTS
# ═══════════════════════════════════════════════════════════

class TestScenarioLabel:
    def test_to_dict_roundtrip(self):
        label = ScenarioLabel(
            labeler_id="expert_1",
            decision=VoteDecision.APPROVE,
            confidence=0.9,
            notes="Good student",
        )
        d = label.to_dict()
        restored = ScenarioLabel.from_dict(d)
        assert restored.labeler_id == "expert_1"
        assert restored.decision == VoteDecision.APPROVE
        assert restored.confidence == 0.9
        assert restored.notes == "Good student"


class TestExperimentScenario:
    def test_expert_consensus_majority(self):
        scenario = ExperimentScenario(scenario_id="S001", student_id="S", module_id="M",
                                       path_id="P", course_id="C", score=0.8)
        scenario.add_expert_label(ScenarioLabel("e1", VoteDecision.APPROVE, 0.9))
        scenario.add_expert_label(ScenarioLabel("e2", VoteDecision.APPROVE, 0.8))
        scenario.add_expert_label(ScenarioLabel("e3", VoteDecision.REJECT, 0.7))
        assert scenario.expert_consensus == VoteDecision.APPROVE

    def test_expert_consensus_tie(self):
        scenario = ExperimentScenario(scenario_id="S001", student_id="S", module_id="M",
                                       path_id="P", course_id="C", score=0.8)
        scenario.add_expert_label(ScenarioLabel("e1", VoteDecision.APPROVE, 0.9))
        scenario.add_expert_label(ScenarioLabel("e2", VoteDecision.REJECT, 0.8))
        assert scenario.expert_consensus == VoteDecision.ABSTAIN

    def test_to_dict_roundtrip(self):
        scenario = ExperimentScenario(
            scenario_id="S001", student_id="STU_001", module_id="MOD_001",
            path_id="PATH_001", course_id="C_001", score=0.75,
            module_bloom_level=4, module_type="quiz",
            student_learning_profile="visual",
            ground_truth=VoteDecision.APPROVE,
            difficulty_category="medium",
            tags=["test", "demo"],
        )
        d = scenario.to_dict()
        restored = ExperimentScenario.from_dict(d)
        assert restored.scenario_id == "S001"
        assert restored.ground_truth == VoteDecision.APPROVE
        assert restored.module_bloom_level == 4
        assert restored.tags == ["test", "demo"]

    def test_add_expert_label(self):
        s = ExperimentScenario(scenario_id="S1", student_id="S", module_id="M",
                                path_id="P", course_id="C", score=0.5)
        assert s.n_expert_labels == 0
        s.add_expert_label(ScenarioLabel("e1", VoteDecision.APPROVE))
        assert s.n_expert_labels == 1


class TestExperimentDataset:
    def test_empty_dataset(self):
        ds = ExperimentDataset()
        assert ds.n_scenarios == 0
        assert ds.labeled_scenarios == []

    def test_add_scenarios(self):
        s1 = ExperimentScenario(scenario_id="S1", student_id="S", module_id="M",
                                 path_id="P", course_id="C", score=0.8,
                                 ground_truth=VoteDecision.APPROVE)
        s2 = ExperimentScenario(scenario_id="S2", student_id="S", module_id="M",
                                 path_id="P", course_id="C", score=0.3,
                                 ground_truth=VoteDecision.REJECT)
        ds = ExperimentDataset([s1, s2])
        assert ds.n_scenarios == 2
        assert len(ds.labeled_scenarios) == 2

    def test_filter_by_difficulty(self):
        scenarios = [
            ExperimentScenario(scenario_id=f"S{i}", student_id="S", module_id="M",
                                path_id="P", course_id="C", score=0.5,
                                difficulty_category=cat)
            for i, cat in enumerate(["easy", "medium", "hard"])
        ]
        ds = ExperimentDataset(scenarios)
        assert len(ds.filter(difficulty="easy")) == 1
        assert len(ds.filter(difficulty="medium")) == 1
        assert len(ds.filter(difficulty="hard")) == 1

    def test_train_test_split(self):
        scenarios = [
            ExperimentScenario(scenario_id=f"S{i}", student_id="S", module_id="M",
                                path_id="P", course_id="C", score=0.5)
            for i in range(100)
        ]
        ds = ExperimentDataset(scenarios)
        train, test = ds.train_test_split(train_ratio=0.8, seed=42)
        assert train.n_scenarios == 80
        assert test.n_scenarios == 20

    def test_save_load_json(self):
        s1 = ExperimentScenario(scenario_id="S1", student_id="S", module_id="M",
                                 path_id="P", course_id="C", score=0.8,
                                 ground_truth=VoteDecision.APPROVE)
        ds = ExperimentDataset([s1], name="test_ds")
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            tmp = f.name
        try:
            ds.save_json(tmp)
            loaded = ExperimentDataset.load_json(tmp)
            assert loaded.n_scenarios == 1
            assert loaded.scenarios[0].scenario_id == "S1"
            assert loaded.scenarios[0].ground_truth == VoteDecision.APPROVE
        finally:
            os.unlink(tmp)

    def test_csv_labeling_roundtrip(self):
        s = ExperimentScenario(scenario_id="S1", student_id="STU", module_id="MOD",
                                path_id="PATH", course_id="C", score=0.6,
                                ground_truth=None)
        ds = ExperimentDataset([s])
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            csv_path = f.name
        try:
            ds.export_labeling_csv(csv_path)
            with open(csv_path) as f:
                content = f.read()
            assert "S1" in content
            assert "decision" in content

            # Import labels - but first write a proper CSV with the label
            import csv
            rows = []
            with open(csv_path, "r") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    row["decision"] = "APPROVE"
                    row["confidence"] = "0.9"
                    row["notes"] = "looks good"
                    rows.append(row)

            with open(csv_path, "w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=rows[0].keys())
                writer.writeheader()
                writer.writerows(rows)

            imported = ds.import_labeling_csv(csv_path, labeler_id="expert_1")
            assert imported == 1
            assert ds.scenarios[0].n_expert_labels == 1
        finally:
            os.unlink(csv_path)


class TestGroundTruthConfig:
    def test_config_hash(self):
        cfg1 = GroundTruthConfig(n_scenarios=100, seed=42)
        cfg2 = GroundTruthConfig(n_scenarios=100, seed=42)
        cfg3 = GroundTruthConfig(n_scenarios=200, seed=42)
        assert cfg1.hash() == cfg2.hash()
        assert cfg1.hash() != cfg3.hash()


class TestGenerateSyntheticDataset:
    def test_generates_correct_number(self):
        cfg = GroundTruthConfig(n_scenarios=50, seed=42)
        ds = generate_synthetic_dataset(cfg)
        assert len(ds.scenarios) == 50

    def test_all_have_ground_truth(self):
        cfg = GroundTruthConfig(n_scenarios=100, seed=42)
        ds = generate_synthetic_dataset(cfg)
        assert all(s.ground_truth is not None for s in ds.scenarios)

    def test_difficulty_distribution(self):
        cfg = GroundTruthConfig(n_scenarios=1000, seed=42)
        ds = generate_synthetic_dataset(cfg)
        dist = ds.difficulty_distribution
        assert "easy" in dist
        assert "medium" in dist
        assert "hard" in dist

    def test_reproducible(self):
        cfg = GroundTruthConfig(n_scenarios=50, seed=42)
        ds1 = generate_synthetic_dataset(cfg)
        ds2 = generate_synthetic_dataset(cfg)
        assert len(ds1.scenarios) == len(ds2.scenarios)
        for s1, s2 in zip(ds1.scenarios, ds2.scenarios):
            assert s1.scenario_id == s2.scenario_id
            assert s1.ground_truth == s2.ground_truth


class TestCheckGroundTruthConsistency:
    def test_no_inconsistencies_without_experts(self):
        s = ExperimentScenario(scenario_id="S1", student_id="S", module_id="M",
                                path_id="P", course_id="C", score=0.5,
                                ground_truth=VoteDecision.APPROVE)
        ds = ExperimentDataset([s])
        assert check_ground_truth_consistency(ds) == []

    def test_detects_inconsistencies(self):
        s = ExperimentScenario(scenario_id="S1", student_id="S", module_id="M",
                                path_id="P", course_id="C", score=0.5,
                                ground_truth=VoteDecision.APPROVE)
        s.add_expert_label(ScenarioLabel("e1", VoteDecision.REJECT))
        s.add_expert_label(ScenarioLabel("e2", VoteDecision.REJECT))
        ds = ExperimentDataset([s])
        inc = check_ground_truth_consistency(ds)
        assert len(inc) == 1
        assert inc[0]["ground_truth"] == "approve"
        assert inc[0]["expert_consensus"] == "reject"


# ═══════════════════════════════════════════════════════════
# FLEISS' KAPPA TESTS
# ═══════════════════════════════════════════════════════════

class TestFleissKappa:
    def test_perfect_agreement(self):
        """All raters agree on all subjects → kappa = 1."""
        ratings = [
            [0, 0, 0],
            [1, 1, 1],
            [0, 0, 0],
        ]
        k = fleiss_kappa(ratings, n_categories=2)
        assert k == 1.0

    def test_chance_agreement(self):
        """Random assignments → kappa ≈ 0."""
        ratings = [
            [0, 1, 1, 0],
            [1, 0, 1, 0],
            [0, 1, 0, 1],
            [1, 0, 0, 1],
        ]
        k = fleiss_kappa(ratings, n_categories=2)
        assert abs(k) < 0.4  # Close to chance with small N

    def test_empty_raises(self):
        with pytest.raises(ValueError):
            fleiss_kappa([])

    def test_insufficient_raters(self):
        with pytest.raises(ValueError):
            fleiss_kappa([[0]])

    def test_kappa_interpretation(self):
        assert "substantial" in kappa_interpretation(0.7)
        assert "perfect" in kappa_interpretation(0.9)
        assert "poor" in kappa_interpretation(-0.1)

    def test_agreement_matrix(self):
        ratings = [
            [0, 0, 1],
            [1, 1, 0],
        ]
        matrix = agreement_matrix(ratings, n_categories=2)
        assert len(matrix) == 2
        assert len(matrix[0]) == 2

    def test_per_category_agreement(self):
        ratings = [
            [0, 0, 0],
            [1, 1, 1],
            [0, 0, 0],
        ]
        cats = per_category_agreement(ratings, n_categories=2)
        assert len(cats) == 2


class TestEvaluateExpertAgreement:
    def test_insufficient_experts_returns_empty(self):
        report = evaluate_expert_agreement([])
        assert report.kappa == 0.0
        assert report.n_subjects == 0

    def test_two_experts_varied_agreement(self):
        """Two experts with varied labels → kappa > 0."""
        scenarios = []
        labels = [
            (VoteDecision.APPROVE, VoteDecision.APPROVE),
            (VoteDecision.APPROVE, VoteDecision.APPROVE),
            (VoteDecision.REJECT, VoteDecision.REJECT),
            (VoteDecision.REJECT, VoteDecision.REJECT),
            (VoteDecision.APPROVE, VoteDecision.REJECT),  # Disagreement
        ]
        for i, (d1, d2) in enumerate(labels):
            s = ExperimentScenario(
                scenario_id=f"S{i}", student_id="S", module_id="M",
                path_id="P", course_id="C", score=0.5,
            )
            s.add_expert_label(ScenarioLabel("e1", d1, 0.9))
            s.add_expert_label(ScenarioLabel("e2", d2, 0.8))
            scenarios.append(s)
        report = evaluate_expert_agreement(scenarios)
        assert report.n_subjects == 5
        assert report.n_raters == 2
        assert report.kappa > 0.0  # Should show some agreement

    def test_report_to_dict(self):
        report = AgreementReport(
            n_subjects=5, n_raters=3, n_categories=3,
            kappa=0.7, interpretation="substantial agreement",
            per_category=[], matrix=[],
        )
        d = report.to_dict()
        assert d["kappa"] == 0.7
        assert d["interpretation"] == "substantial agreement"


class TestExpertEvaluationRound:
    def test_to_dict_roundtrip(self):
        r = ExpertEvaluationRound(
            round_id="R001",
            expert_ids=["e1", "e2"],
            scenario_ids=["S1", "S2"],
            status="completed",
        )
        d = r.to_dict()
        restored = ExpertEvaluationRound.from_dict(d)
        assert restored.round_id == "R001"
        assert restored.status == "completed"


# ═══════════════════════════════════════════════════════════
# CONFIG TESTS
# ═══════════════════════════════════════════════════════════

class TestExperimentConfig:
    def test_default_config(self):
        cfg = ExperimentConfig()
        assert cfg.n_runs_per_condition == 10
        assert cfg.seed == 42
        assert cfg.hash

    def test_config_hash_stable(self):
        cfg1 = ExperimentConfig(label="test", seed=42)
        cfg2 = ExperimentConfig(label="test", seed=42)
        assert cfg1.hash == cfg2.hash

    def test_config_hash_changes_with_params(self):
        cfg1 = ExperimentConfig(label="test", seed=42)
        cfg2 = ExperimentConfig(label="test", seed=99)
        assert cfg1.hash != cfg2.hash

    def test_save_load_json(self):
        cfg = ExperimentConfig(label="test_save", seed=123, n_scenarios=50)
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            tmp = f.name
        try:
            cfg.save(tmp)
            loaded = ExperimentConfig.load(tmp)
            assert loaded.label == "test_save"
            assert loaded.seed == 123
            assert loaded.n_scenarios == 50
        finally:
            os.unlink(tmp)

    def test_n_runs_total(self):
        cfg = ExperimentConfig(
            conditions=["a", "b", "c"],
            seeds=[1, 2, 3],
            cv_folds=1,
        )
        assert cfg.n_runs_total == 9

    def test_seeds_auto_generated(self):
        cfg = ExperimentConfig(n_runs_per_condition=5, seed=42)
        assert cfg.seeds == [42, 43, 44, 45, 46]

    def test_save_load_snapshot(self):
        cfg = ExperimentConfig(label="snapshot_test")
        with tempfile.TemporaryDirectory() as tmp:
            path = save_config_snapshot(cfg, tmp)
            assert os.path.exists(path)
            loaded = load_config_snapshot(cfg.hash, tmp)
            assert loaded is not None
            assert loaded.label == "snapshot_test"


class TestConfigVersion:
    def test_register_and_lookup(self):
        cv = ConfigVersion()
        cfg = ExperimentConfig(label="v1", seed=42)
        h = cfg.hash
        cv.register(cfg)
        assert cv.has(h)
        assert cv.lookup(h) is not None

    def test_save_load(self):
        cv = ConfigVersion()
        cv.versions = {"abc": "/path/to/config.json"}
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            tmp = f.name
        try:
            cv.save(tmp)
            loaded = ConfigVersion.load(tmp)
            assert loaded.versions["abc"] == "/path/to/config.json"
        finally:
            os.unlink(tmp)


class TestConfigSweep:
    def test_generate_multiple_configs(self):
        sweep = ConfigSweep(
            seeds=[1, 2],
            deliberation_settings=[False, True],
            n_scenarios_list=[50],
        )
        configs = sweep.generate()
        assert len(configs) == 4  # 2 seeds × 2 delib settings × 1 n_scenario
        assert all(isinstance(c, ExperimentConfig) for c in configs)


# ═══════════════════════════════════════════════════════════
# ANOMALY TESTS
# ═══════════════════════════════════════════════════════════

class TestAnomalyDetection:
    def make_mock_result(self, latencies, confidences, conditions=None):
        from app.experiment.orchestrator import OrchestratorResult, RunResult
        from app.experiment.metrics import PerRunMetrics
        from app.core.consensus import VoteDecision

        if conditions is None:
            conditions = ["test_cond"] * len(latencies)

        result = OrchestratorResult(config=MagicMock())
        for i, (lat, conf, cond) in enumerate(zip(latencies, confidences, conditions)):
            run = RunResult(
                condition_name=cond,
                run_index=i,
                seed=42,
                decision=VoteDecision.APPROVE,
                confidence=conf,
                correct=True,
                elapsed_ms=lat,
                metrics=PerRunMetrics(
                    condition_name=cond, run_index=i,
                    decision="approve",
                    confidence=conf,
                    correct=True,
                    unanimous=True,
                    total_latency_ms=lat,
                    voter_latencies_ms=[lat],
                    latency_variance=0.0,
                    min_voter_latency_ms=lat,
                    max_voter_latency_ms=lat,
                    num_voters=1,
                    approvals=1, rejections=0, abstentions=0,
                    disagreement=False,
                    weight_entropy=None, trust_variance=None, affinity_variance=None,
                ),
            )
            result.runs.append(run)
        return result

    def test_no_anomalies_with_normal_data(self):
        result = self.make_mock_result(
            latencies=[100, 110, 105, 95, 102, 98],
            confidences=[0.8, 0.81, 0.79, 0.82, 0.8, 0.81],
        )
        anomalies = detect_anomalies(result)
        assert len(anomalies.anomalies) == 0

    def test_detects_latency_outlier(self):
        result = self.make_mock_result(
            latencies=[100, 110, 105, 95, 9999],
            confidences=[0.8, 0.81, 0.79, 0.82, 0.8],
        )
        latency_anomalies = detect_latency_anomalies(result)
        assert len(latency_anomalies) > 0

    def test_detects_confidence_outlier(self):
        result = self.make_mock_result(
            latencies=[100] * 6,
            confidences=[0.8, 0.8, 0.8, 0.8, 0.8, 0.01],
        )
        conf_anomalies = detect_confidence_anomalies(result)
        assert len(conf_anomalies) > 0

    def test_anomaly_collection_counts(self):
        from app.experiment.anomaly import AnomalyCollection, AnomalyReport
        col = AnomalyCollection(anomalies=[
            AnomalyReport(0, "a", "m", 1.0, 0.0, 2.0, "critical"),
            AnomalyReport(1, "a", "m", 1.0, 0.0, 2.0, "warning"),
        ])
        assert col.n_critical == 1
        assert col.n_warnings == 1
        assert len(col.to_dict()) == 2


# ═══════════════════════════════════════════════════════════
# EXPORT TESTS
# ═══════════════════════════════════════════════════════════

class TestExport:
    def make_result(self):
        from app.experiment.orchestrator import OrchestratorResult, RunResult
        from app.experiment.metrics import PerRunMetrics
        from app.core.consensus import VoteDecision
        from app.experiment.config import ExperimentConfig

        config = ExperimentConfig()
        result = OrchestratorResult(config=config)
        for i in range(5):
            run = RunResult(
                condition_name="test_cond",
                run_index=i,
                seed=42 + i,
                decision=VoteDecision.APPROVE,
                confidence=0.8 + i * 0.02,
                correct=True,
                elapsed_ms=100.0 + i * 10,
                metrics=PerRunMetrics(
                    condition_name="test_cond", run_index=i,
                    decision="approve", confidence=0.8,
                    correct=True, unanimous=True,
                    total_latency_ms=100.0,
                    voter_latencies_ms=[100.0],
                    latency_variance=0.0,
                    min_voter_latency_ms=100.0,
                    max_voter_latency_ms=100.0,
                    num_voters=1,
                    approvals=1, rejections=0, abstentions=0,
                    disagreement=False,
                    weight_entropy=None, trust_variance=None, affinity_variance=None,
                ),
            )
            result.runs.append(run)
        result.completed_at = result.started_at
        return result

    def test_export_csv(self):
        result = self.make_result()
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            path = f.name
        try:
            export_to_csv(result, path)
            with open(path) as f:
                content = f.read()
            assert "condition" in content
            assert "test_cond" in content
        finally:
            os.unlink(path)

    def test_export_json(self):
        result = self.make_result()
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            path = f.name
        try:
            export_to_json(result, path)
            with open(path) as f:
                data = json.load(f)
            assert "summary" in data
            assert "config" in data
        finally:
            os.unlink(path)

    def test_export_summary(self):
        result = self.make_result()
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            path = f.name
        try:
            export_summary(result, path)
            with open(path) as f:
                content = f.read()
            assert "EXPERIMENT SUMMARY" in content
        finally:
            os.unlink(path)

    def test_export_latex_table(self):
        result = self.make_result()
        with tempfile.NamedTemporaryFile(mode="w", suffix=".tex", delete=False) as f:
            path = f.name
        try:
            export_latex_table(result, path)
            with open(path) as f:
                content = f.read()
            assert "begin{table}" in content
            assert "Accuracy" in content
        finally:
            os.unlink(path)

    def test_export_all(self):
        result = self.make_result()
        with tempfile.TemporaryDirectory() as tmp:
            paths = export_all(result, tmp)
            assert "csv" in paths
            assert "json" in paths
            assert "summary" in paths
            assert "latex" in paths
            for p in paths.values():
                assert os.path.exists(p)


# ═══════════════════════════════════════════════════════════
# REPLAY TESTS
# ═══════════════════════════════════════════════════════════

class TestVerifyReproducibility:
    def make_result(self, n_runs=5, seed_offset=0):
        from app.experiment.orchestrator import OrchestratorResult, RunResult
        from app.experiment.metrics import PerRunMetrics
        from app.core.consensus import VoteDecision
        from app.experiment.config import ExperimentConfig

        config = ExperimentConfig()
        result = OrchestratorResult(config=config)
        for i in range(n_runs):
            run = RunResult(
                condition_name="test_cond",
                run_index=i,
                seed=42 + i + seed_offset,
                decision=VoteDecision.APPROVE,
                confidence=0.8,
                correct=True,
                elapsed_ms=100.0,
                metrics=PerRunMetrics(
                    condition_name="test_cond", run_index=i,
                    decision="approve",
                    confidence=0.8,
                    correct=True,
                    unanimous=True,
                    total_latency_ms=100.0,
                    voter_latencies_ms=[100.0],
                    latency_variance=0.0,
                    min_voter_latency_ms=100.0,
                    max_voter_latency_ms=100.0,
                    num_voters=1,
                    approvals=1, rejections=0, abstentions=0,
                    disagreement=False,
                    weight_entropy=None, trust_variance=None, affinity_variance=None,
                ),
            )
            result.runs.append(run)
        result.completed_at = result.started_at
        return result

    def test_identical_results_are_reproducible(self):
        orig = self.make_result(3)
        replay = self.make_result(3)
        report = verify_reproducibility(orig, replay)
        assert report["reproducible"] is True

    def test_different_run_counts_not_reproducible(self):
        orig = self.make_result(5)
        replay = self.make_result(3)
        report = verify_reproducibility(orig, replay)
        assert report["reproducible"] is False
        assert "Run count mismatch" in report["reason"]
