"""Data models for explainable adaptive pedagogy."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Reason:
    factor: str
    value: Any
    contribution: float
    evidence: str


@dataclass
class Explanation:
    dimension: str
    previous_value: Any = None
    new_value: Any = None
    reasons: list[Reason] = field(default_factory=list)
    confidence: float = 0.0
    trace_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "dimension": self.dimension,
            "previous_value": self.previous_value,
            "new_value": self.new_value,
            "reasons": [
                {
                    "factor": r.factor,
                    "value": r.value,
                    "contribution": r.contribution,
                    "evidence": r.evidence,
                }
                for r in self.reasons
            ],
            "confidence": self.confidence,
            "trace_id": self.trace_id,
        }


@dataclass
class AdaptationExplanation:
    student_id: str = ""
    week_number: int = 0
    explanations: list[Explanation] = field(default_factory=list)
    decision_graph: dict[str, Any] = field(default_factory=dict)
    metrics: dict[str, Any] = field(default_factory=dict)
    generated_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "student_id": self.student_id,
            "week_number": self.week_number,
            "explanations": [e.to_dict() for e in self.explanations],
            "decision_graph": self.decision_graph,
            "metrics": self.metrics,
            "generated_at": self.generated_at,
        }
