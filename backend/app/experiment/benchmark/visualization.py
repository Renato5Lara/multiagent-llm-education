"""
Benchmark Visualization — Generación de gráficos académicos.

Produce:
  - comparison charts (barras comparativas por métrica)
  - confidence distributions (distribuciones de confianza)
  - adaptation comparisons (impacto de adaptación)
  - retrieval effectiveness (efectividad de recuperación)
  - hallucination reduction (reducción de alucinación)
  - replay evolution (evolución de reproducibilidad)
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any

from app.experiment.benchmark.metrics import (
    BenchmarkMetrics,
    BenchmarkResult,
    condition_summary,
)
from app.experiment.benchmark.conditions import BenchmarkConditions


@dataclass
class ChartConfig:
    """Configuración para generación de gráficos."""

    output_dir: str = "benchmark_charts"
    figsize: tuple[float, float] = (12, 6)
    dpi: int = 150
    style: str = "seaborn-v0_8-whitegrid"
    palette: list[str] = field(default_factory=lambda: [
        "#2E86AB", "#A23B72", "#F18F01", "#C73E1D", "#3B1F2B", "#4A7C59",
    ])
    format: str = "png"


class VisualizationEngine:
    """Motor de visualización académica para el benchmark.

    Genera gráficos comparativos entre condiciones usando matplotlib.
    """

    METRIC_LABELS = {
        "pass_at_1": "Pass@1",
        "correction_rate": "Correction Rate",
        "grounding_score": "Grounding Score",
        "misconception_coverage": "Misconception Coverage",
        "bloom_alignment": "Bloom Alignment",
        "adaptation_impact": "Adaptation Impact",
        "hallucination_reduction": "Hallucination Reduction",
        "sandbox_validation_success": "Sandbox Validation",
        "execution_success": "Execution Success",
        "consensus_confidence": "Consensus Confidence",
        "retrieval_confidence": "Retrieval Confidence",
        "prompt_grounding_score": "Prompt Grounding",
        "personalization_impact": "Personalization Impact",
    }

    CONDITION_LABELS = {
        "single-agent_static": "Single-Agent Static",
        "swarm_full": "Swarm Full",
        "swarm_no_retrieval": "Swarm No Retrieval",
        "swarm_no_memory": "Swarm No Memory",
        "swarm_no_reviewer": "Swarm No Reviewer",
        "swarm_static_pedagogy": "Swarm Static Pedagogy",
    }

    def __init__(self, results: list[BenchmarkResult], config: ChartConfig | None = None):
        self.results = results
        self.config = config or ChartConfig()
        self.summary = condition_summary(results)
        self.conditions_order = [
            "single-agent_static", "swarm_full",
            "swarm_no_retrieval", "swarm_no_memory",
            "swarm_no_reviewer", "swarm_static_pedagogy",
        ]
        self._has_matplotlib = self._check_matplotlib()

    def _check_matplotlib(self) -> bool:
        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
            return True
        except ImportError:
            return False

    def _get_condition_values(self, metric_key: str) -> tuple[list[str], list[float]]:
        labels: list[str] = []
        values: list[float] = []
        for cond in self.conditions_order:
            if cond in self.summary:
                labels.append(self.CONDITION_LABELS.get(cond, cond))
                values.append(self.summary[cond].get(metric_key, 0.0))
        return labels, values

    def _get_individual_values(
        self, metric_key: str,
    ) -> dict[str, list[float]]:
        by_cond: dict[str, list[float]] = {}
        for r in self.results:
            by_cond.setdefault(r.condition_name, []).append(
                getattr(r.metrics, metric_key, 0.0),
            )
        return by_cond

    def plot_comparison_chart(self, path: str | None = None) -> str | None:
        if not self._has_matplotlib:
            return None
        import matplotlib.pyplot as plt
        import numpy as np

        n_metrics = len(BenchmarkMetrics.__dataclass_fields__.keys())
        n_conds = len([c for c in self.conditions_order if c in self.summary])

        fig, axes = plt.subplots(
            nrows=4, ncols=4, figsize=(18, 14),
        )
        axes_flat = axes.flatten()

        colors = self.config.palette[:n_conds]
        cond_labels = [
            self.CONDITION_LABELS.get(c, c)
            for c in self.conditions_order if c in self.summary
        ]

        for idx, key in enumerate(BenchmarkMetrics.__dataclass_fields__.keys()):
            if idx >= len(axes_flat):
                break
            ax = axes_flat[idx]
            _, values = self._get_condition_values(key)
            x = np.arange(len(values))
            bars = ax.bar(x, values, color=colors[:len(values)], width=0.6)
            ax.set_title(self.METRIC_LABELS.get(key, key), fontsize=10, fontweight="bold")
            ax.set_ylim(0, 1.1)
            ax.set_xticks(x)
            ax.set_xticklabels(cond_labels, rotation=45, ha="right", fontsize=7)
            for bar, val in zip(bars, values):
                ax.text(
                    bar.get_x() + bar.get_width() / 2.0,
                    bar.get_height() + 0.02,
                    f"{val:.3f}",
                    ha="center", va="bottom", fontsize=7,
                )

        for idx in range(len(BenchmarkMetrics.__dataclass_fields__.keys()), len(axes_flat)):
            axes_flat[idx].set_visible(False)

        fig.suptitle(
            "Academic Benchmark — Metric Comparison Across Conditions",
            fontsize=14, fontweight="bold", y=1.01,
        )
        fig.tight_layout(pad=2.0)

        output_path = path or os.path.join(
            self.config.output_dir, f"comparison_chart.{self.config.format}",
        )
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        fig.savefig(output_path, dpi=self.config.dpi, bbox_inches="tight")
        plt.close(fig)
        return output_path

    def plot_confidence_distributions(self, path: str | None = None) -> str | None:
        if not self._has_matplotlib:
            return None
        import matplotlib.pyplot as plt

        by_cond = self._get_individual_values("consensus_confidence")
        fig, ax = plt.subplots(figsize=self.config.figsize)

        for idx, (cond, vals) in enumerate(by_cond.items()):
            if vals:
                color = self.config.palette[idx % len(self.config.palette)]
                label = self.CONDITION_LABELS.get(cond, cond)
                ax.hist(vals, bins=15, alpha=0.5, color=color, label=label)

        ax.set_xlabel("Consensus Confidence", fontsize=12)
        ax.set_ylabel("Frequency", fontsize=12)
        ax.set_title("Confidence Distributions by Condition", fontsize=13, fontweight="bold")
        ax.legend(fontsize=9)
        ax.grid(True, alpha=0.3)

        output_path = path or os.path.join(
            self.config.output_dir, f"confidence_distributions.{self.config.format}",
        )
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        fig.savefig(output_path, dpi=self.config.dpi, bbox_inches="tight")
        plt.close(fig)
        return output_path

    def plot_adaptation_comparison(self, path: str | None = None) -> str | None:
        if not self._has_matplotlib:
            return None
        import matplotlib.pyplot as plt
        import numpy as np

        conds = [
            c for c in self.conditions_order
            if c in self.summary and c != "single-agent_static"
        ]
        labels = [self.CONDITION_LABELS.get(c, c) for c in conds]
        values = [self.summary[c].get("adaptation_impact", 0) for c in conds]

        fig, ax = plt.subplots(figsize=(10, 6))
        x = np.arange(len(conds))
        colors = self.config.palette[1:1 + len(conds)]
        bars = ax.bar(x, values, color=colors, width=0.5)

        ax.set_xticks(x)
        ax.set_xticklabels(labels, rotation=30, ha="right", fontsize=10)
        ax.set_ylabel("Adaptation Impact", fontsize=12)
        ax.set_title("Adaptation Impact by Condition", fontsize=13, fontweight="bold")
        ax.axhline(y=0, color="gray", linestyle="--", alpha=0.5)
        ax.grid(True, axis="y", alpha=0.3)

        for bar, val in zip(bars, values):
            ax.text(
                bar.get_x() + bar.get_width() / 2.0,
                bar.get_height() + 0.01 if val >= 0 else bar.get_height() - 0.03,
                f"{val:.3f}",
                ha="center", va="bottom" if val >= 0 else "top",
                fontsize=9,
            )

        output_path = path or os.path.join(
            self.config.output_dir, f"adaptation_comparison.{self.config.format}",
        )
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        fig.savefig(output_path, dpi=self.config.dpi, bbox_inches="tight")
        plt.close(fig)
        return output_path

    def plot_retrieval_effectiveness(self, path: str | None = None) -> str | None:
        if not self._has_matplotlib:
            return None
        import matplotlib.pyplot as plt
        import numpy as np

        conds = [
            c for c in self.conditions_order if c in self.summary
        ]
        labels = [self.CONDITION_LABELS.get(c, c) for c in conds]

        retrieval_vals = [
            self.summary[c].get("retrieval_confidence", 0) for c in conds
        ]
        grounding_vals = [
            self.summary[c].get("grounding_score", 0) for c in conds
        ]

        fig, ax = plt.subplots(figsize=self.config.figsize)
        x = np.arange(len(conds))
        width = 0.35

        bars1 = ax.bar(x - width / 2, retrieval_vals, width,
                       label="Retrieval Confidence", color=self.config.palette[0])
        bars2 = ax.bar(x + width / 2, grounding_vals, width,
                       label="Grounding Score", color=self.config.palette[1])

        ax.set_xticks(x)
        ax.set_xticklabels(labels, rotation=30, ha="right", fontsize=10)
        ax.set_ylabel("Score", fontsize=12)
        ax.set_title("Retrieval Effectiveness & Grounding", fontsize=13, fontweight="bold")
        ax.legend(fontsize=10)
        ax.set_ylim(0, 1.1)
        ax.grid(True, axis="y", alpha=0.3)

        output_path = path or os.path.join(
            self.config.output_dir, f"retrieval_effectiveness.{self.config.format}",
        )
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        fig.savefig(output_path, dpi=self.config.dpi, bbox_inches="tight")
        plt.close(fig)
        return output_path

    def plot_hallucination_reduction(self, path: str | None = None) -> str | None:
        if not self._has_matplotlib:
            return None
        import matplotlib.pyplot as plt
        import numpy as np

        conds = [
            c for c in self.conditions_order if c in self.summary
        ]
        labels = [self.CONDITION_LABELS.get(c, c) for c in conds]
        values = [self.summary[c].get("hallucination_reduction", 0) for c in conds]

        fig, ax = plt.subplots(figsize=(10, 6))
        x = np.arange(len(conds))
        colors = self.config.palette[:len(conds)]
        bars = ax.bar(x, values, color=colors, width=0.5)

        ax.set_xticks(x)
        ax.set_xticklabels(labels, rotation=30, ha="right", fontsize=10)
        ax.set_ylabel("Hallucination Reduction", fontsize=12)
        ax.set_title("Hallucination Reduction by Condition", fontsize=13, fontweight="bold")
        ax.set_ylim(0, 1.1)
        ax.grid(True, axis="y", alpha=0.3)

        for bar, val in zip(bars, values):
            ax.text(
                bar.get_x() + bar.get_width() / 2.0,
                bar.get_height() + 0.02,
                f"{val:.3f}",
                ha="center", va="bottom", fontsize=9,
            )

        output_path = path or os.path.join(
            self.config.output_dir, f"hallucination_reduction.{self.config.format}",
        )
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        fig.savefig(output_path, dpi=self.config.dpi, bbox_inches="tight")
        plt.close(fig)
        return output_path

    def plot_replay_evolution(self, path: str | None = None) -> str | None:
        if not self._has_matplotlib:
            return None
        import matplotlib.pyplot as plt
        import numpy as np

        if not self.results:
            return None

        cond_order = []
        cond_values = []
        for cond in self.conditions_order:
            vals = [
                getattr(r.metrics, "execution_success", 0)
                for r in self.results
                if r.condition_name == cond
            ]
            if vals:
                cond_order.append(self.CONDITION_LABELS.get(cond, cond))
                cond_values.append(vals)

        fig, ax = plt.subplots(figsize=self.config.figsize)

        positions = []
        labels = []
        start = 0
        for i, vals in enumerate(cond_values):
            x = np.arange(start, start + len(vals))
            color = self.config.palette[i % len(self.config.palette)]
            ax.scatter(x, vals, color=color, alpha=0.5, s=20)
            if vals:
                ax.plot(
                    [start, start + len(vals) - 1],
                    [sum(vals) / len(vals)] * 2,
                    color=color, linestyle="--", linewidth=2,
                    label=cond_order[i],
                )
            positions.append(start + len(vals) / 2 - 0.5)
            labels.append(cond_order[i])
            start += len(vals) + 2

        ax.set_xticks(positions)
        ax.set_xticklabels(labels, rotation=30, ha="right", fontsize=9)
        ax.set_ylabel("Execution Success", fontsize=12)
        ax.set_title("Replay Evolution Across Conditions", fontsize=13, fontweight="bold")
        ax.legend(fontsize=8, loc="lower right")
        ax.grid(True, alpha=0.3)

        output_path = path or os.path.join(
            self.config.output_dir, f"replay_evolution.{self.config.format}",
        )
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        fig.savefig(output_path, dpi=self.config.dpi, bbox_inches="tight")
        plt.close(fig)
        return output_path

    def generate_all(self, output_dir: str | None = None) -> dict[str, str | None]:
        if output_dir:
            self.config.output_dir = output_dir
        os.makedirs(self.config.output_dir, exist_ok=True)

        return {
            "comparison_chart": self.plot_comparison_chart(),
            "confidence_distributions": self.plot_confidence_distributions(),
            "adaptation_comparison": self.plot_adaptation_comparison(),
            "retrieval_effectiveness": self.plot_retrieval_effectiveness(),
            "hallucination_reduction": self.plot_hallucination_reduction(),
            "replay_evolution": self.plot_replay_evolution(),
        }
