"""Ground truth dataset system for swarm education experiments.

Provides:
    - ExperimentScenario: a single student-module evaluation case
    - ScenarioLabel: expert-assigned label for a scenario
    - GroundTruthConfig: configuration for ground truth generation
    - ExperimentDataset: versioned collection of scenarios with load/save
    - Synthetic data generation with controlled difficulty distributions
    - Labeling batch export/import for expert review workflows
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import random
import statistics
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

from app.core.consensus import VoteDecision


@dataclass(frozen=True)
class ScenarioLabel:
    """A single expert- or algorithm-assigned ground-truth label."""

    labeler_id: str
    decision: VoteDecision
    confidence: float = 1.0
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "labeler_id": self.labeler_id,
            "decision": self.decision.value,
            "confidence": self.confidence,
            "timestamp": self.timestamp.isoformat(),
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> ScenarioLabel:
        return cls(
            labeler_id=d["labeler_id"],
            decision=VoteDecision(d["decision"]),
            confidence=d.get("confidence", 1.0),
            timestamp=datetime.fromisoformat(d["timestamp"]),
            notes=d.get("notes", ""),
        )


@dataclass
class ExperimentScenario:
    """A single evaluation case: student readiness for a given module.

    This is the atomic unit of the experiment dataset. Each scenario
    can have multiple expert labels for inter-rater reliability analysis.
    """

    scenario_id: str
    student_id: str
    module_id: str
    path_id: str
    course_id: str
    score: float

    # Module metadata
    module_bloom_level: int = 3
    module_type: str = "exercise"
    module_difficulty: float = 0.5

    # Student cognitive profile
    student_mastered_concepts: list[str] = field(default_factory=list)
    student_weak_concepts: list[str] = field(default_factory=list)
    student_learning_profile: str = "visual"
    student_cognitive_stage: str = "concrete_operational"

    # Pathway context
    completed_modules: list[str] = field(default_factory=list)
    next_modules: list[str] = field(default_factory=list)
    gaps: list[str] = field(default_factory=list)

    # Evaluation-specific
    mastery_scores: dict[str, float] = field(default_factory=dict)
    practice_timing: dict[str, int] = field(default_factory=dict)
    concept_coverage: float = 0.0

    # Ground truth + expert labels
    ground_truth: VoteDecision | None = None
    expert_labels: dict[str, ScenarioLabel] = field(default_factory=dict)

    # Metadata
    difficulty_category: str = "medium"
    tags: list[str] = field(default_factory=list)

    @property
    def n_expert_labels(self) -> int:
        return len(self.expert_labels)

    @property
    def expert_consensus(self) -> VoteDecision | None:
        """Majority vote among expert labels (ties → ABSTAIN)."""
        if not self.expert_labels:
            return self.ground_truth
        counts: dict[VoteDecision, int] = {}
        for lbl in self.expert_labels.values():
            counts[lbl.decision] = counts.get(lbl.decision, 0) + 1
        if not counts:
            return None
        max_count = max(counts.values())
        winners = [d for d, c in counts.items() if c == max_count]
        if len(winners) == 1:
            return winners[0]
        return VoteDecision.ABSTAIN

    def add_expert_label(self, label: ScenarioLabel) -> None:
        self.expert_labels[label.labeler_id] = label

    def to_dict(self) -> dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "student_id": self.student_id,
            "module_id": self.module_id,
            "path_id": self.path_id,
            "course_id": self.course_id,
            "score": self.score,
            "module_bloom_level": self.module_bloom_level,
            "module_type": self.module_type,
            "module_difficulty": self.module_difficulty,
            "student_mastered_concepts": self.student_mastered_concepts,
            "student_weak_concepts": self.student_weak_concepts,
            "student_learning_profile": self.student_learning_profile,
            "student_cognitive_stage": self.student_cognitive_stage,
            "completed_modules": self.completed_modules,
            "next_modules": self.next_modules,
            "gaps": self.gaps,
            "mastery_scores": self.mastery_scores,
            "practice_timing": self.practice_timing,
            "concept_coverage": self.concept_coverage,
            "ground_truth": self.ground_truth.value if self.ground_truth else None,
            "expert_labels": {
                k: v.to_dict() for k, v in self.expert_labels.items()
            },
            "difficulty_category": self.difficulty_category,
            "tags": self.tags,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> ExperimentScenario:
        gt = d.get("ground_truth")
        return cls(
            scenario_id=d["scenario_id"],
            student_id=d["student_id"],
            module_id=d["module_id"],
            path_id=d["path_id"],
            course_id=d["course_id"],
            score=d["score"],
            module_bloom_level=d.get("module_bloom_level", 3),
            module_type=d.get("module_type", "exercise"),
            module_difficulty=d.get("module_difficulty", 0.5),
            student_mastered_concepts=d.get("student_mastered_concepts", []),
            student_weak_concepts=d.get("student_weak_concepts", []),
            student_learning_profile=d.get("student_learning_profile", "visual"),
            student_cognitive_stage=d.get("student_cognitive_stage", "concrete_operational"),
            completed_modules=d.get("completed_modules", []),
            next_modules=d.get("next_modules", []),
            gaps=d.get("gaps", []),
            mastery_scores=d.get("mastery_scores", {}),
            practice_timing=d.get("practice_timing", {}),
            concept_coverage=d.get("concept_coverage", 0.0),
            ground_truth=VoteDecision(gt) if gt else None,
            expert_labels={
                k: ScenarioLabel.from_dict(v)
                for k, v in d.get("expert_labels", {}).items()
            },
            difficulty_category=d.get("difficulty_category", "medium"),
            tags=d.get("tags", []),
        )


@dataclass
class GroundTruthConfig:
    """Configuration for ground truth generation."""
    approve_threshold: float = 0.7
    reject_threshold: float = 0.4
    n_scenarios: int = 100
    seed: int = 42
    difficulty_distribution: dict[str, float] = field(default_factory=lambda: {
        "easy": 0.3, "medium": 0.4, "hard": 0.3,
    })
    bloom_range: tuple[int, int] = (1, 6)
    n_experts: int = 3

    def hash(self) -> str:
        raw = json.dumps(asdict(self), sort_keys=True)
        return hashlib.sha256(raw.encode()).hexdigest()[:12]


class ExperimentDataset:
    """A versioned, serializable collection of scenarios.

    Supports:
        - JSON load/save with schema versioning
        - CSV export for expert labeling
        - Synthetic data generation with controlled distributions
        - Train/test splitting
        - Ground truth consistency checks
    """

    SCHEMA_VERSION = "1.0"

    def __init__(
        self,
        scenarios: list[ExperimentScenario] | None = None,
        *,
        name: str = "",
        description: str = "",
        config: GroundTruthConfig | None = None,
    ):
        self.scenarios = list(scenarios) if scenarios else []
        self.name = name
        self.description = description
        self.config = config or GroundTruthConfig()
        self.created_at = datetime.now(timezone.utc)
        self._version = self.SCHEMA_VERSION

    @property
    def n_scenarios(self) -> int:
        return len(self.scenarios)

    @property
    def labeled_scenarios(self) -> list[ExperimentScenario]:
        return [s for s in self.scenarios if s.ground_truth is not None]

    @property
    def with_expert_labels(self) -> list[ExperimentScenario]:
        return [s for s in self.scenarios if s.n_expert_labels > 0]

    @property
    def difficulty_distribution(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for s in self.scenarios:
            counts[s.difficulty_category] = counts.get(s.difficulty_category, 0) + 1
        return counts

    # ── Serialization ─────────────────────────────────────

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self._version,
            "name": self.name,
            "description": self.description,
            "created_at": self.created_at.isoformat(),
            "config": asdict(self.config),
            "scenarios": [s.to_dict() for s in self.scenarios],
            "statistics": {
                "n_scenarios": self.n_scenarios,
                "n_labeled": len(self.labeled_scenarios),
                "n_with_expert_labels": len(self.with_expert_labels),
                "difficulty_distribution": self.difficulty_distribution,
            },
        }

    def save_json(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)

    @classmethod
    def load_json(cls, path: str) -> ExperimentDataset:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        config_dict = data.get("config", {})
        config = GroundTruthConfig(**config_dict) if config_dict else None
        ds = cls(
            scenarios=[ExperimentScenario.from_dict(s) for s in data["scenarios"]],
            name=data.get("name", ""),
            description=data.get("description", ""),
            config=config,
        )
        ds.created_at = datetime.fromisoformat(data["created_at"])
        return ds

    # ── CSV export for expert labeling ────────────────────

    def export_labeling_csv(self, path: str, *, expert_id: str = "expert") -> None:
        """Export a CSV for human expert labeling.

        Each row contains scenario metadata + empty decision column.
        """
        rows = []
        for s in self.scenarios:
            if s.ground_truth is not None:
                continue  # Only export unlabeled scenarios
            rows.append({
                "scenario_id": s.scenario_id,
                "student_id": s.student_id,
                "score": s.score,
                "bloom_level": s.module_bloom_level,
                "module_type": s.module_type,
                "difficulty": s.module_difficulty,
                "learning_profile": s.student_learning_profile,
                "cognitive_stage": s.student_cognitive_stage,
                "mastered_concepts": ";".join(s.student_mastered_concepts),
                "weak_concepts": ";".join(s.student_weak_concepts),
                "decision": "",  # Expert fills this
                "confidence": "",  # Expert fills this
                "notes": "",  # Expert fills this
            })

        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else [])
            writer.writeheader()
            writer.writerows(rows)

    def import_labeling_csv(self, path: str, *, labeler_id: str = "expert") -> int:
        """Import expert labels from a completed CSV. Returns count of labels imported."""
        imported = 0
        with open(path, "r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                scenario_id = row.get("scenario_id", "").strip()
                if not scenario_id:
                    continue
                decision_str = row.get("decision", "").strip().upper()
                if decision_str not in ("APPROVE", "REJECT", "ABSTAIN"):
                    continue

                scenario = self.get(scenario_id)
                if scenario is None:
                    continue

                label = ScenarioLabel(
                    labeler_id=labeler_id,
                    decision=VoteDecision(decision_str.lower()),
                    confidence=float(row.get("confidence", 1.0) or 1.0),
                    notes=row.get("notes", ""),
                )
                scenario.add_expert_label(label)
                imported += 1

        return imported

    # ── Query ─────────────────────────────────────────────

    def get(self, scenario_id: str) -> ExperimentScenario | None:
        for s in self.scenarios:
            if s.scenario_id == scenario_id:
                return s
        return None

    def filter(
        self,
        *,
        difficulty: str | None = None,
        labeled: bool | None = None,
        has_expert_labels: bool | None = None,
    ) -> list[ExperimentScenario]:
        results = list(self.scenarios)
        if difficulty:
            results = [s for s in results if s.difficulty_category == difficulty]
        if labeled is True:
            results = [s for s in results if s.ground_truth is not None]
        elif labeled is False:
            results = [s for s in results if s.ground_truth is None]
        if has_expert_labels is True:
            results = [s for s in results if s.n_expert_labels > 0]
        elif has_expert_labels is False:
            results = [s for s in results if s.n_expert_labels == 0]
        return results

    def train_test_split(
        self, train_ratio: float = 0.8, seed: int = 42,
    ) -> tuple[ExperimentDataset, ExperimentDataset]:
        rng = random.Random(seed)
        indices = list(range(len(self.scenarios)))
        rng.shuffle(indices)
        split = int(len(indices) * train_ratio)
        train_idx = indices[:split]
        test_idx = indices[split:]
        train = ExperimentDataset(
            [self.scenarios[i] for i in train_idx],
            name=f"{self.name}_train",
            config=self.config,
        )
        test = ExperimentDataset(
            [self.scenarios[i] for i in test_idx],
            name=f"{self.name}_test",
            config=self.config,
        )
        return train, test


# ── Synthetic dataset generation ─────────────────────────

def generate_synthetic_dataset(
    config: GroundTruthConfig | None = None,
) -> ExperimentDataset:
    """Generate a synthetic dataset of student-module scenarios.

    Uses a controlled random process with configurable difficulty distribution,
    bloom level distribution, and ground truth assignment.

    Ground truth rule (heuristic):
        - APPROVE if score >= approve_threshold
        - REJECT if score <= reject_threshold
        - ABSTAIN otherwise (borderline cases)
    """
    cfg = config or GroundTruthConfig()
    rng = random.Random(cfg.seed)

    scenarios: list[ExperimentScenario] = []
    difficulty_categories = list(cfg.difficulty_distribution.keys())
    difficulty_weights = list(cfg.difficulty_distribution.values())

    for i in range(cfg.n_scenarios):
        diff_cat = rng.choices(difficulty_categories, weights=difficulty_weights, k=1)[0]
        bloom = rng.randint(cfg.bloom_range[0], cfg.bloom_range[1])
        score_mean = {"easy": 0.75, "medium": 0.55, "hard": 0.35}[diff_cat]
        score_std = {"easy": 0.15, "medium": 0.20, "hard": 0.20}[diff_cat]
        score = max(0.0, min(1.0, rng.gauss(score_mean, score_std)))

        n_mastered = rng.randint(2, 8)
        n_weak = rng.randint(1, 5)
        mastered = [f"concept_{rng.randint(1, 100)}" for _ in range(n_mastered)]
        weak = [f"concept_{rng.randint(1, 100)}" for _ in range(n_weak)]

        gt: VoteDecision | None = None
        if score >= cfg.approve_threshold:
            gt = VoteDecision.APPROVE
        elif score <= cfg.reject_threshold:
            gt = VoteDecision.REJECT
        else:
            gt = VoteDecision.ABSTAIN

        scenario = ExperimentScenario(
            scenario_id=f"SCENARIO_{i+1:04d}",
            student_id=f"STU_{rng.randint(1000, 9999)}",
            module_id=f"MOD_{rng.randint(1, 50):03d}",
            path_id=f"PATH_{rng.randint(1, 5):03d}",
            course_id="COURSE_001",
            score=round(score, 4),
            module_bloom_level=bloom,
            module_type=rng.choice(["exercise", "quiz", "project", "reading"]),
            module_difficulty=round(rng.uniform(0.2, 0.9), 2),
            student_mastered_concepts=mastered,
            student_weak_concepts=weak,
            student_learning_profile=rng.choice(["visual", "auditory", "reading", "kinesthetic"]),
            student_cognitive_stage=rng.choice([
                "preoperational", "concrete_operational", "formal_operational",
            ]),
            completed_modules=[f"MOD_{rng.randint(1, 20):03d}" for _ in range(rng.randint(2, 8))],
            next_modules=[f"MOD_{rng.randint(21, 50):03d}" for _ in range(rng.randint(1, 4))],
            gaps=rng.sample(weak, min(2, len(weak))),
            mastery_scores={c: round(rng.uniform(0.3, 1.0), 2) for c in mastered},
            practice_timing={c: rng.randint(1, 30) for c in mastered},
            concept_coverage=round(rng.uniform(0.3, 1.0), 2),
            ground_truth=gt,
            difficulty_category=diff_cat,
            tags=[diff_cat, f"bloom_{bloom}"],
        )
        scenarios.append(scenario)

    return ExperimentDataset(
        scenarios=scenarios,
        name=f"synthetic_n{cfg.n_scenarios}_seed{cfg.seed}",
        description=f"Synthetic dataset: {cfg.n_scenarios} scenarios, seed={cfg.seed}",
        config=cfg,
    )


# ── Ground truth consistency ─────────────────────────

def check_ground_truth_consistency(
    dataset: ExperimentDataset,
) -> list[dict[str, Any]]:
    """Check where heuristic ground truth disagrees with expert labels.

    Returns a list of inconsistency reports.
    """
    inconsistencies: list[dict[str, Any]] = []
    for s in dataset.scenarios:
        if s.ground_truth is None or not s.expert_labels:
            continue
        expert_consensus = s.expert_consensus
        if expert_consensus is None:
            continue
        if expert_consensus != s.ground_truth:
            inconsistencies.append({
                "scenario_id": s.scenario_id,
                "ground_truth": s.ground_truth.value,
                "expert_consensus": expert_consensus.value,
                "n_experts": s.n_expert_labels,
                "score": s.score,
                "difficulty": s.difficulty_category,
            })
    return inconsistencies
