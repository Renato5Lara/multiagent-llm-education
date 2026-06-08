"""Experiment configuration hashing, versioning, and serialization.

Provides:
    - ExperimentConfig: comprehensive configuration dataclass
    - config_hash(): deterministic SHA-256 hash of any config
    - ConfigVersion: version tracking for reproducibility
    - save_config() / load_config(): JSON serialization
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

from app.experiment.dataset import GroundTruthConfig


@dataclass
class ExperimentConfig:
    """Complete, versioned configuration for a swarm experiment run.

    Serializes to JSON deterministically (sorted keys, no surprises).
    Hash is stable across Python versions and platforms.
    """

    # Experiment identity
    label: str = ""
    description: str = ""
    experimenter: str = ""

    # Dataset
    dataset_path: str = ""
    n_scenarios: int = 100
    ground_truth: GroundTruthConfig = field(default_factory=GroundTruthConfig)

    # Conditions to compare
    conditions: list[str] = field(default_factory=lambda: [
        "full_swarm", "uniform_weights", "single_agent",
        "no_trust", "no_specialization",
    ])
    n_runs_per_condition: int = 10

    # Randomization
    seed: int = 42
    seeds: list[int] | None = None  # If set, overrides single seed + n_runs

    # Deliberation
    use_deliberation: bool = False
    deliberation_max_rounds: int = 3
    deliberation_threshold: float = 0.85
    deliberation_min_confidence: float = 0.6

    # LLM (voter configuration)
    llm_provider: str = ""
    llm_model: str = ""
    llm_budget_per_voter: int = 100000

    # Cross-validation
    cv_folds: int = 1  # 1 = no CV
    cv_seed: int = 42

    # Resource limits
    timeout_ms: int = 30000
    max_concurrent: int = 4

    # Metadata
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    version: str = "1.0"

    def __post_init__(self):
        if self.seeds is None:
            self.seeds = [self.seed + i for i in range(self.n_runs_per_condition)]

    @property
    def hash(self) -> str:
        """Deterministic SHA-256 fingerprint of this config."""
        return config_hash(self)

    @property
    def n_runs_total(self) -> int:
        return len(self.conditions) * len(self.seeds) * self.cv_folds

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d.pop("created_at", None)
        d.pop("version", None)
        return d

    def save(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False, default=str)

    @classmethod
    def load(cls, path: str) -> ExperimentConfig:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        data.pop("hash", None)
        gt_data = data.pop("ground_truth", {})
        gt = GroundTruthConfig(**gt_data) if gt_data else GroundTruthConfig()
        seeds = data.pop("seeds", None)
        cfg = cls(ground_truth=gt, seeds=seeds, **data)
        return cfg


def config_hash(obj: Any) -> str:
    """Compute a deterministic SHA-256 hash of any config object.

    Handles dataclasses, dicts, lists, and primitive types.
    """
    if hasattr(obj, "to_dict"):
        raw = json.dumps(obj.to_dict(), sort_keys=True, default=str)
    elif hasattr(obj, "__dict__"):
        raw = json.dumps(asdict(obj), sort_keys=True, default=str)
    elif isinstance(obj, dict):
        raw = json.dumps(obj, sort_keys=True, default=str)
    else:
        raw = json.dumps(obj, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode()).hexdigest()


# ── Config version tracking ──────────────────────────────

@dataclass
class ConfigVersion:
    """Tracks config versions for reproducibility."""

    versions: dict[str, str] = field(default_factory=dict)  # hash -> path

    def register(self, config: ExperimentConfig, path: str | None = None) -> str:
        h = config.hash
        self.versions[h] = path or ""
        return h

    def lookup(self, config_hash: str) -> str | None:
        return self.versions.get(config_hash)

    def has(self, config_hash: str) -> bool:
        return config_hash in self.versions

    def save(self, path: str) -> None:
        data = {
            "versions": self.versions,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    @classmethod
    def load(cls, path: str) -> ConfigVersion:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        cv = cls()
        cv.versions = data.get("versions", {})
        return cv


# ── Config parameter sweep ──────────────────────────────

@dataclass
class ConfigSweep:
    """Generate multiple configs by sweeping over parameter ranges."""

    base: ExperimentConfig = field(default_factory=ExperimentConfig)
    seeds: list[int] | None = None
    conditions: list[list[str]] | None = None
    deliberation_settings: list[bool] | None = None
    n_scenarios_list: list[int] | None = None

    def generate(self) -> list[ExperimentConfig]:
        configs: list[ExperimentConfig] = []
        seeds = self.seeds or [self.base.seed]
        conditions_list = self.conditions or [self.base.conditions]
        delib_list = self.deliberation_settings or [self.base.use_deliberation]
        n_scenarios_list = self.n_scenarios_list or [self.base.n_scenarios]

        for seed in seeds:
            for conds in conditions_list:
                for use_delib in delib_list:
                    for n_scen in n_scenarios_list:
                        cfg = ExperimentConfig(
                            label=f"seed{seed}_cond{len(conds)}_delib{use_delib}_n{n_scen}",
                            seed=seed,
                            conditions=conds,
                            use_deliberation=use_delib,
                            n_scenarios=n_scen,
                            n_runs_per_condition=1,
                            seeds=[seed],
                            ground_truth=GroundTruthConfig(seed=seed, n_scenarios=n_scen),
                        )
                        configs.append(cfg)
        return configs


# ── Config persistence helpers ───────────────────────────

def save_config_snapshot(config: ExperimentConfig, output_dir: str) -> str:
    """Save config to a versioned JSON file in output_dir. Returns file path."""
    os.makedirs(output_dir, exist_ok=True)
    path = os.path.join(output_dir, f"config_{config.hash}.json")
    config.save(path)
    return path


def load_config_snapshot(config_hash: str, output_dir: str) -> ExperimentConfig | None:
    """Load a config by its hash from output_dir."""
    path = os.path.join(output_dir, f"config_{config_hash}.json")
    if not os.path.exists(path):
        return None
    return ExperimentConfig.load(path)
