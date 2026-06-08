"""Expert evaluation protocol and inter-rater reliability analysis.

Provides:
    - Fleiss' Kappa computation (multi-rater agreement)
    - Agreement matrix construction
    - Per-category agreement analysis
    - Expert evaluation round management
    - Label consistency validation
"""

from __future__ import annotations

import json
import math
import statistics
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from app.core.consensus import VoteDecision


# ── Fleiss' Kappa ────────────────────────────────────────

def fleiss_kappa(
    ratings: list[list[int]],
    n_categories: int | None = None,
) -> float:
    """Compute Fleiss' Kappa for inter-rater agreement.

    Args:
        ratings: Matrix of shape (n_subjects, n_raters) where each entry
                 is an integer category label (0..n_categories-1).
                 Missing ratings should use -1 or None (will be excluded
                 per-subject).
        n_categories: Number of rating categories. Auto-detected if None.

    Returns:
        Kappa value in [-1, 1]. 1 = perfect agreement,
        0 = chance agreement, < 0 = less than chance.

    Raises:
        ValueError: If data is insufficient for computation.

    Reference:
        Fleiss, J. L. (1971). Measuring nominal scale agreement
        among many raters. Psychological Bulletin, 76(5), 378-382.
    """
    if not ratings or not ratings[0]:
        raise ValueError("Empty ratings matrix")

    # Filter invalid entries per subject
    cleaned: list[list[int]] = []
    for row in ratings:
        valid = [r for r in row if r is not None and r >= 0]
        if len(valid) >= 2:  # Need at least 2 raters per subject
            cleaned.append(valid)

    if len(cleaned) < 2:
        raise ValueError("Need at least 2 subjects with >= 2 raters each")

    if n_categories is None:
        all_vals = [r for row in cleaned for r in row]
        n_categories = max(all_vals) + 1 if all_vals else 1

    N = len(cleaned)  # Number of subjects
    n = len(cleaned[0])  # Number of raters (assume constant after cleaning)

    # Build agreement matrix: subjects x categories
    # Each cell = number of raters who assigned subject i to category j
    agreement = [[0] * n_categories for _ in range(N)]
    for i, row in enumerate(cleaned):
        for r in row:
            agreement[i][r] += 1

    # Pi_i: proportion of agreement for subject i
    pi_i: list[float] = []
    for i in range(N):
        total_ratings = sum(agreement[i])
        if total_ratings < 2:
            continue
        n_pairs = total_ratings * (total_ratings - 1)
        if n_pairs == 0:
            continue
        sum_sq = sum(n * (n - 1) for n in agreement[i])
        pi_i.append(sum_sq / n_pairs)

    if not pi_i:
        raise ValueError("No subjects with sufficient ratings")

    P_bar = statistics.mean(pi_i)  # Mean agreement proportion

    # P_j: proportion of all assignments to category j
    n_total = sum(sum(row) for row in agreement)
    P_j = [sum(agreement[i][j] for i in range(N)) / n_total for j in range(n_categories)]
    P_bar_e = sum(p ** 2 for p in P_j)  # Expected agreement by chance

    # Avoid division by zero
    denominator = 1.0 - P_bar_e
    if abs(denominator) < 1e-10:
        return 0.0

    kappa = (P_bar - P_bar_e) / denominator
    return max(-1.0, min(1.0, kappa))


def agreement_matrix(
    ratings: list[list[int]],
    n_categories: int | None = None,
) -> list[list[int]]:
    """Build a square agreement matrix: how many rater pairs agreed per category pair.

    Returns a n_categories x n_categories matrix where cell (i, j)
    counts the number of rater-pair assignments where one rater chose
    category i and another chose category j.

    Diagonal = agreement counts.
    """
    if not ratings:
        return []

    cleaned: list[list[int]] = []
    for row in ratings:
        valid = [r for r in row if r is not None and r >= 0]
        if len(valid) >= 2:
            cleaned.append(valid)

    if n_categories is None:
        all_vals = [r for row in cleaned for r in row]
        n_categories = max(all_vals) + 1 if all_vals else 1

    matrix = [[0] * n_categories for _ in range(n_categories)]
    for row in cleaned:
        for i in range(len(row)):
            for j in range(i + 1, len(row)):
                a, b = row[i], row[j]
                matrix[a][b] += 1
                if a != b:
                    matrix[b][a] += 1
    return matrix


def per_category_agreement(
    ratings: list[list[int]],
    n_categories: int | None = None,
) -> list[dict[str, float]]:
    """Compute per-category agreement statistics.

    Returns a list of dicts with keys:
        category, n_assigned, proportion, conditional_kappa
    """
    if not ratings:
        return []

    cleaned: list[list[int]] = []
    for row in ratings:
        valid = [r for r in row if r is not None and r >= 0]
        if len(valid) >= 2:
            cleaned.append(valid)

    if n_categories is None:
        all_vals = [r for row in cleaned for r in row]
        n_categories = max(all_vals) + 1 if all_vals else 1

    N = len(cleaned)
    n = len(cleaned[0])

    agreement_mat = [[0] * n_categories for _ in range(N)]
    for i, row in enumerate(cleaned):
        for r in row:
            agreement_mat[i][r] += 1

    # Per-category stats
    results = []
    for cat in range(n_categories):
        total_assigned = sum(agreement_mat[i][cat] for i in range(N))
        proportion = total_assigned / (N * n) if N * n > 0 else 0.0

        # Conditional kappa for this category
        # (treat as binary: category cat vs not-cat)
        binary_ratings = []
        for row in cleaned:
            binary_ratings.append([1 if r == cat else 0 for r in row])

        try:
            cat_kappa = fleiss_kappa(binary_ratings, n_categories=2)
        except (ValueError, ZeroDivisionError):
            cat_kappa = 0.0

        results.append({
            "category": cat,
            "n_assigned": total_assigned,
            "proportion": round(proportion, 4),
            "conditional_kappa": round(cat_kappa, 4),
        })

    return results


def kappa_interpretation(kappa: float) -> str:
    """Interpret Fleiss' Kappa value according to Landis & Koch (1977)."""
    if kappa < 0.0:
        return "poor (less than chance)"
    elif kappa <= 0.20:
        return "slight agreement"
    elif kappa <= 0.40:
        return "fair agreement"
    elif kappa <= 0.60:
        return "moderate agreement"
    elif kappa <= 0.80:
        return "substantial agreement"
    else:
        return "almost perfect agreement"


# ── Expert evaluation round ──────────────────────────────

@dataclass
class ExpertEvaluationRound:
    """A round of expert evaluation for a set of scenarios."""

    round_id: str
    expert_ids: list[str] = field(default_factory=list)
    scenario_ids: list[str] = field(default_factory=list)
    status: str = "pending"  # pending | in_progress | completed
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "round_id": self.round_id,
            "expert_ids": self.expert_ids,
            "scenario_ids": self.scenario_ids,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> ExpertEvaluationRound:
        ca = d.get("completed_at")
        return cls(
            round_id=d["round_id"],
            expert_ids=d.get("expert_ids", []),
            scenario_ids=d.get("scenario_ids", []),
            status=d.get("status", "pending"),
            created_at=datetime.fromisoformat(d["created_at"]),
            completed_at=datetime.fromisoformat(ca) if ca else None,
        )


# ── Evaluate expert agreement ────────────────────────────

@dataclass
class AgreementReport:
    """Full inter-rater reliability report."""

    n_subjects: int
    n_raters: int
    n_categories: int
    kappa: float
    interpretation: str
    per_category: list[dict[str, float]]
    matrix: list[list[int]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "n_subjects": self.n_subjects,
            "n_raters": self.n_raters,
            "n_categories": self.n_categories,
            "kappa": round(self.kappa, 4),
            "interpretation": self.interpretation,
            "per_category": self.per_category,
            "matrix": self.matrix,
        }


def evaluate_expert_agreement(
    scenarios: list,
    *,
    label_attr: str = "expert_labels",
    decision_attr: str = "decision",
) -> AgreementReport:
    """Evaluate inter-rater agreement among experts for a list of scenarios.

    Args:
        scenarios: List of objects with expert_labels dict
                   (e.g., ExperimentScenario instances).
        label_attr: Attribute name for the expert_labels dict.
        decision_attr: Attribute name for VoteDecision on each label.

    Returns:
        AgreementReport with kappa, interpretation, per-category stats.
    """
    # Build ratings matrix: subjects x experts
    # Collect all expert IDs
    all_expert_ids: set[str] = set()
    for s in scenarios:
        labels = getattr(s, label_attr, {})
        all_expert_ids.update(labels.keys())

    expert_ids = sorted(all_expert_ids)
    if len(expert_ids) < 2:
        return AgreementReport(
            n_subjects=0, n_raters=0, n_categories=0,
            kappa=0.0, interpretation="insufficient raters",
            per_category=[], matrix=[],
        )

    decision_map = {
        VoteDecision.APPROVE: 0,
        VoteDecision.REJECT: 1,
        VoteDecision.ABSTAIN: 2,
    }
    n_categories = len(decision_map)

    ratings: list[list[int]] = []
    for s in scenarios:
        labels = getattr(s, label_attr, {})
        row = []
        for eid in expert_ids:
            if eid in labels:
                label = labels[eid]
                decision = getattr(label, decision_attr)
                row.append(decision_map.get(decision, -1))
            else:
                row.append(-1)
        ratings.append(row)

    kappa = fleiss_kappa(ratings, n_categories)
    interpretation = kappa_interpretation(kappa)
    matrix = agreement_matrix(ratings, n_categories)
    per_cat = per_category_agreement(ratings, n_categories)

    return AgreementReport(
        n_subjects=len(ratings),
        n_raters=len(expert_ids),
        n_categories=n_categories,
        kappa=kappa,
        interpretation=interpretation,
        per_category=per_cat,
        matrix=matrix,
    )
