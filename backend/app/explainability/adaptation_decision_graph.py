"""Build a directed decision graph from explanations."""

from __future__ import annotations

from typing import Any

from app.explainability.models import Explanation


class AdaptationDecisionGraph:
    """Builds a ``{nodes, edges}`` graph showing which factors led to which decisions.

    Each factor in an explanation's reasons becomes a node of type ``signal``.
    The explanation itself becomes a node of type ``decision``.
    Edges run from signal → decision with causal labels.
    """

    def build(self, explanations: list[Explanation]) -> dict[str, list[dict]]:
        nodes: list[dict] = []
        edges: list[dict] = []
        seen_signals: set[str] = set()
        seen_decisions: set[str] = set()

        for exp in explanations:
            decision_id = f"decision:{exp.dimension}"
            if decision_id not in seen_decisions:
                nodes.append({
                    "id": decision_id,
                    "label": _decision_label(exp),
                    "type": "decision",
                    "dimension": exp.dimension,
                })
                seen_decisions.add(decision_id)

            for reason in exp.reasons:
                signal_id = f"signal:{reason.factor}"
                if signal_id not in seen_signals:
                    nodes.append({
                        "id": signal_id,
                        "label": _signal_label(reason),
                        "type": "signal",
                        "factor": reason.factor,
                    })
                    seen_signals.add(signal_id)

                edges.append({
                    "from": signal_id,
                    "to": decision_id,
                    "label": f"contribución: {reason.contribution:.0%}",
                    "contribution": reason.contribution,
                })

        return {"nodes": nodes, "edges": edges}


def _decision_label(exp: Explanation) -> str:
    prev = exp.previous_value
    new = exp.new_value
    if prev is not None and new is not None and prev != new:
        return f"{exp.dimension}: {prev} → {new}"
    if new is not None:
        return f"{exp.dimension}: {new}"
    return f"{exp.dimension}: adjusted"


def _signal_label(reason: Any) -> str:
    label = reason.factor.replace("_", " ").title()
    val = reason.value
    if isinstance(val, (int, float)):
        return f"{label}: {val}"
    if isinstance(val, str):
        return f"{label}: {val[:40]}"
    if isinstance(val, list):
        return f"{label}: {', '.join(str(v)[:20] for v in val[:2])}"
    return label
