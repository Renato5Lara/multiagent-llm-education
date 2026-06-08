"""
Calculadora de métricas especializadas de programación.

Mide y actualiza 12 dimensiones:
- Pseudocode quality (0-1): basado en estructura, legibilidad, variables
- Debugging efficiency (0-1): tiempo en resolver errores, intentos
- Code reading speed (0-1): velocidad de comprensión de código
- 4 CT dimensions (0-1): descomposición, patrones, abstracción, algoritmos
- 3 Error rates (0-1): sintaxis, lógica, semántica (ponderados)
- Stage progression (0-1): avance entre etapas cognitivas
- Concept mastery rate (0-1): % de conceptos dominados
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.models.programming_domain import ProgrammingConcept, ProgrammingStage
from app.models.programming_metrics import ProgrammingMetrics
from app.models.student_memory import WeaknessRecord, StrengthRecord

logger = logging.getLogger(__name__)

ERROR_WEIGHTS = {
    "syntax": 0.3,
    "logic": 0.65,
    "semantic": 0.5,
}


class ProgrammingMetricsCalculator:
    """Calcula y persiste métricas de programación para un estudiante."""

    def __init__(self, db: Session, student_id: str, course_id: str):
        self.db = db
        self.student_id = student_id
        self.course_id = course_id

    def calculate(
        self,
        pseudocode_quality: float | None = None,
        debugging_efficiency: float | None = None,
        code_reading_speed: float | None = None,
        ct_scores: dict[str, float] | None = None,
        error_counts: dict[str, int] | None = None,
        current_stage: str | None = None,
        total_concepts: int = 26,
    ) -> ProgrammingMetrics:
        existing = self._get_or_create_metrics()

        # Update only provided fields
        if pseudocode_quality is not None:
            existing.pseudocode_quality = self._ema(existing.pseudocode_quality, pseudocode_quality, 0.3)

        if debugging_efficiency is not None:
            existing.debugging_efficiency = self._ema(existing.debugging_efficiency, debugging_efficiency, 0.3)

        if code_reading_speed is not None:
            existing.code_reading_speed = self._ema(existing.code_reading_speed, code_reading_speed, 0.3)

        if ct_scores:
            existing.ct_decomposition = self._ema(existing.ct_decomposition, ct_scores.get("decomposition", existing.ct_decomposition), 0.3)
            existing.ct_pattern_recognition = self._ema(existing.ct_pattern_recognition, ct_scores.get("pattern_recognition", existing.ct_pattern_recognition), 0.3)
            existing.ct_abstraction = self._ema(existing.ct_abstraction, ct_scores.get("abstraction", existing.ct_abstraction), 0.3)
            existing.ct_algorithm_design = self._ema(existing.ct_algorithm_design, ct_scores.get("algorithm_design", existing.ct_algorithm_design), 0.3)

        if error_counts:
            total_errors = sum(error_counts.values()) or 1
            weighted_sum = sum(
                count * ERROR_WEIGHTS.get(err_type, 0.5)
                for err_type, count in error_counts.items()
            )
            existing.syntax_error_rate = self._ema(existing.syntax_error_rate, error_counts.get("syntax", 0) / total_errors, 0.2)
            existing.logic_error_rate = self._ema(existing.logic_error_rate, error_counts.get("logic", 0) / total_errors, 0.2)
            existing.semantic_error_rate = self._ema(existing.semantic_error_rate, error_counts.get("semantic", 0) / total_errors, 0.2)

        # Stage progression
        if current_stage:
            stage_order = list(ProgrammingStage)
            try:
                stage_idx = stage_order.index(ProgrammingStage(current_stage))
                existing.stage_progression = self._ema(existing.stage_progression, stage_idx / (len(stage_order) - 1), 0.2)
            except ValueError:
                pass

        # Concept mastery rate from DB
        mastered = self._count_mastered_concepts()
        existing.concept_mastery_rate = self._ema(existing.concept_mastery_rate, mastered / max(total_concepts, 1), 0.2)

        # Concept scores
        concept_scores = self._build_concept_scores()
        if concept_scores:
            existing.concept_scores = concept_scores

        # Error history
        errors = self._build_error_history()
        if errors:
            existing.error_history = errors

        existing.calculated_at = datetime.now(timezone.utc)
        self.db.add(existing)
        self.db.flush()

        return existing

    def _get_or_create_metrics(self) -> ProgrammingMetrics:
        existing = (
            self.db.query(ProgrammingMetrics)
            .filter(
                ProgrammingMetrics.student_id == self.student_id,
                ProgrammingMetrics.course_id == self.course_id,
            )
            .first()
        )
        if existing:
            return existing
        m = ProgrammingMetrics(
            student_id=self.student_id,
            course_id=self.course_id,
        )
        self.db.add(m)
        self.db.flush()
        return m

    def _count_mastered_concepts(self) -> int:
        strengths = (
            self.db.query(StrengthRecord)
            .filter(
                StrengthRecord.student_id == self.student_id,
            )
            .all()
        )
        mastered = 0
        for s in strengths:
            try:
                ProgrammingConcept(s.topic.lower())
                mastered += 1
            except ValueError:
                pass
        return mastered

    def _build_concept_scores(self) -> dict[str, float]:
        strengths = (
            self.db.query(StrengthRecord)
            .filter(StrengthRecord.student_id == self.student_id)
            .all()
        )
        weaknesses = (
            self.db.query(WeaknessRecord)
            .filter(
                WeaknessRecord.student_id == self.student_id,
                WeaknessRecord.resolved == False,
            )
            .all()
        )

        scores: dict[str, float] = {}
        concept_names = {c.value for c in ProgrammingConcept}
        for s in strengths:
            topic = s.topic.lower()
            if topic in concept_names:
                scores[topic] = max(scores.get(topic, 0), 0.7)
        for w in weaknesses:
            topic = w.topic.lower()
            if topic in concept_names:
                scores[topic] = min(scores.get(topic, 1.0), 0.3)

        for c in ProgrammingConcept:
            if c.value not in scores:
                scores[c.value] = 0.5

        return scores

    def _build_error_history(self) -> list[dict[str, Any]]:
        weaknesses = (
            self.db.query(WeaknessRecord)
            .filter(
                WeaknessRecord.student_id == self.student_id,
            )
            .order_by(WeaknessRecord.last_detected_at.desc())
            .limit(20)
            .all()
        )
        return [
            {
                "topic": w.topic,
                "bloom_level": w.bloom_level,
                "detection_count": w.detection_count,
                "resolved": w.resolved,
            }
            for w in weaknesses
        ]

    @staticmethod
    def _ema(prev: float, current: float, alpha: float = 0.3) -> float:
        """Exponential Moving Average."""
        return round(alpha * current + (1 - alpha) * prev, 4)
