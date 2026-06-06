"""
Servicio de detección de etapa cognitiva en programación.
Determina la etapa actual del estudiante basado en fortalezas,
debilidades, conceptos completados y puntuaciones CT.
Se ejecuta después de cada módulo completado (no bloqueante).
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.orm import Session

from app.models.programming_domain import (
    ProgrammingConcept,
    ProgrammingStage,
    STAGE_CONFIG,
)
from app.models.programming_prerequisite import CONCEPT_DEPENDENCY_GRAPH
from app.models.student_memory import StrengthRecord, WeaknessRecord
from app.models.student_progress import StudentProgress
from app.models.programming_metrics import ProgrammingMetrics

logger = logging.getLogger(__name__)


class CognitiveStageDetector:
    """Detecta la etapa cognitiva actual del estudiante en programación.

    Usa 4 inputs:
    1. Fortalezas/Conceptos dominados (StrengthRecord)
    2. Debilidades detectadas (WeaknessRecord)
    3. Conceptos completados (StudentProgress + evidencia)
    4. Puntuaciones CT (ProgrammingMetrics)

    Reglas:
    - La etapa se determina por la etapa más alta donde el estudiante
      cumple con >= mastery_threshold de los conceptos de esa etapa.
    - No puede avanzar si >30% de conceptos críticos están ausentes.
    """

    def __init__(
        self,
        db: Session,
        student_id: str,
        course_id: str,
    ):
        self.db = db
        self.student_id = student_id
        self.course_id = course_id

    def detect(self) -> dict[str, Any]:
        strengths = self._get_strengths()
        weaknesses = self._get_weaknesses()
        mastered_concepts = self._get_mastered_concepts(strengths)
        ct_scores = self._get_ct_scores()

        current_stage, confidence, missing_critical = self._determine_stage(
            mastered_concepts, ct_scores,
        )

        next_stage = self._get_next_stage(current_stage)
        recommendations = self._build_recommendations(
            current_stage, missing_critical, weaknesses, ct_scores,
        )

        return {
            "current_stage": current_stage.value,
            "current_stage_config": {
                "bloom_range": STAGE_CONFIG[current_stage]["bloom_range"],
                "concepts": [c.value for c in STAGE_CONFIG[current_stage]["concepts"]],
                "mastery_threshold": STAGE_CONFIG[current_stage]["mastery_threshold"],
            },
            "confidence": round(confidence, 2),
            "mastered_concepts": [c.value for c in sorted(mastered_concepts, key=lambda x: x.value)],
            "missing_critical": [c.value for c in sorted(missing_critical, key=lambda x: x.value)],
            "ct_scores": ct_scores,
            "next_stage": next_stage.value if next_stage else None,
            "next_stage_requirements": self._get_stage_requirements(next_stage) if next_stage else None,
            "recommendations": recommendations,
        }

    def _get_strengths(self) -> list[StrengthRecord]:
        return (
            self.db.query(StrengthRecord)
            .filter(
                StrengthRecord.student_id == self.student_id,
            )
            .all()
        )

    def _get_weaknesses(self) -> list[WeaknessRecord]:
        return (
            self.db.query(WeaknessRecord)
            .filter(
                WeaknessRecord.student_id == self.student_id,
                WeaknessRecord.resolved == False,
            )
            .all()
        )

    def _get_mastered_concepts(
        self, strengths: list[StrengthRecord],
    ) -> set[ProgrammingConcept]:
        mastered: set[ProgrammingConcept] = set()
        for s in strengths:
            try:
                concept = ProgrammingConcept(s.topic.lower())
                mastered.add(concept)
            except ValueError:
                pass
        return mastered

    def _get_ct_scores(self) -> dict[str, float]:
        metrics = (
            self.db.query(ProgrammingMetrics)
            .filter(
                ProgrammingMetrics.student_id == self.student_id,
                ProgrammingMetrics.course_id == self.course_id,
            )
            .order_by(ProgrammingMetrics.calculated_at.desc())
            .first()
        )
        if metrics:
            return {
                "decomposition": metrics.ct_decomposition,
                "pattern_recognition": metrics.ct_pattern_recognition,
                "abstraction": metrics.ct_abstraction,
                "algorithm_design": metrics.ct_algorithm_design,
                "average": (
                    metrics.ct_decomposition
                    + metrics.ct_pattern_recognition
                    + metrics.ct_abstraction
                    + metrics.ct_algorithm_design
                ) / 4.0,
            }
        return {
            "decomposition": 0.0,
            "pattern_recognition": 0.0,
            "abstraction": 0.0,
            "algorithm_design": 0.0,
            "average": 0.0,
        }

    def _determine_stage(
        self,
        mastered_concepts: set[ProgrammingConcept],
        ct_scores: dict[str, float],
    ) -> tuple[ProgrammingStage, float, list[ProgrammingConcept]]:
        stages = list(ProgrammingStage)

        # Find highest stage where mastery threshold is met
        best_stage = stages[0]
        best_confidence = 0.0
        best_missing: list[ProgrammingConcept] = []

        for stage in reversed(stages):
            config = STAGE_CONFIG[stage]
            stage_concepts = config["concepts"]
            threshold = config["mastery_threshold"]
            bloom_min, bloom_max = config["bloom_range"]

            if not stage_concepts:
                best_stage = stage
                best_confidence = 1.0
                best_missing = []
                continue

            mastered_in_stage = mastered_concepts & stage_concepts
            ratio = len(mastered_in_stage) / len(stage_concepts)
            missing = sorted(stage_concepts - mastered_concepts, key=lambda c: c.value)

            # CT score bonus: average CT > 0.5 adds 0.1 to ratio
            ct_avg = ct_scores.get("average", 0.0)
            adjusted_ratio = min(ratio + (0.1 if ct_avg > 0.5 else 0.0), 1.0)

            if adjusted_ratio >= threshold:
                best_stage = stage
                best_confidence = adjusted_ratio
                best_missing = missing

        # Check critical concept gap (cannot have >30% missing of critical concepts)
        critical_missing = self._get_critical_missing(best_stage, mastered_concepts)
        if len(critical_missing) > 0:
            total_critical = len(STAGE_CONFIG[best_stage]["concepts"])
            if total_critical > 0 and len(critical_missing) / total_critical > 0.3:
                prev_index = stages.index(best_stage) - 1
                if prev_index >= 0:
                    best_stage = stages[prev_index]
                    best_confidence = 0.5

        return best_stage, best_confidence, best_missing

    def _get_critical_missing(
        self,
        stage: ProgrammingStage,
        mastered: set[ProgrammingConcept],
    ) -> list[ProgrammingConcept]:
        """Returns concepts missing that are prerequisites for the next stage."""
        config = STAGE_CONFIG[stage]
        stage_concepts = config["concepts"]
        missing = stage_concepts - mastered

        # A concept is "critical" if it is a prerequisite for any concept
        # in the same or next stage
        critical = set()
        for concept in missing:
            for prereq_of, prereqs in CONCEPT_DEPENDENCY_GRAPH.items():
                if concept in prereqs:
                    if prereq_of in stage_concepts:
                        critical.add(concept)
                    else:
                        # Check next stage
                        stages = list(ProgrammingStage)
                        idx = stages.index(stage)
                        if idx + 1 < len(stages):
                            next_concepts = STAGE_CONFIG[stages[idx + 1]]["concepts"]
                            if prereq_of in next_concepts:
                                critical.add(concept)
        return sorted(critical, key=lambda c: c.value)

    def _get_next_stage(self, current: ProgrammingStage) -> ProgrammingStage | None:
        stages = list(ProgrammingStage)
        idx = stages.index(current)
        if idx + 1 < len(stages):
            return stages[idx + 1]
        return None

    def _get_stage_requirements(self, stage: ProgrammingStage) -> dict:
        config = STAGE_CONFIG[stage]
        return {
            "bloom_range": config["bloom_range"],
            "concepts": [c.value for c in sorted(config["concepts"], key=lambda x: x.value)],
            "mastery_threshold": config["mastery_threshold"],
            "description": config["description"],
        }

    def _build_recommendations(
        self,
        stage: ProgrammingStage,
        missing: list[ProgrammingConcept],
        weaknesses: list[WeaknessRecord],
        ct_scores: dict[str, float],
    ) -> list[str]:
        recs = []
        if missing:
            names = ", ".join(c.value.replace("_", " ") for c in missing[:5])
            recs.append(f"Reforzar conceptos pendientes: {names}")
        if ct_scores.get("average", 0.0) < 0.5:
            dims = []
            if ct_scores.get("decomposition", 0.0) < 0.5:
                dims.append("descomposición")
            if ct_scores.get("pattern_recognition", 0.0) < 0.5:
                dims.append("patrones")
            if ct_scores.get("abstraction", 0.0) < 0.5:
                dims.append("abstracción")
            if ct_scores.get("algorithm_design", 0.0) < 0.5:
                dims.append("diseño de algoritmos")
            if dims:
                recs.append(f"Mejorar pensamiento computacional en: {', '.join(dims)}")
        if weaknesses:
            weak_topics = ", ".join(w.topic for w in weaknesses[:3])
            recs.append(f"Trabajar debilidades detectadas: {weak_topics}")
        if not recs:
            recs.append("Continúa con el siguiente nivel. Buen progreso.")
        return recs
