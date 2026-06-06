"""PedagogicalAgent — analyzes student level, cognitive stage, concept mastery, and learning profile.
Legacy version used by the programming course swarm pathway."""

from __future__ import annotations

import logging
from typing import Any

from app.agents.base import BaseAgent
from app.db.uow import UnitOfWork
from app.memory.shared_memory import SharedMemoryStore
from app.models.programming_domain import ProgrammingConcept, ProgrammingStage
from app.models.student_memory import StrengthRecord, WeaknessRecord
from app.models.programming_metrics import ProgrammingMetrics
from app.models.diagnostic_result import DiagnosticResult
from app.services.cognitive_stage_service import CognitiveStageDetector

logger = logging.getLogger(__name__)


class PedagogicalAgent(BaseAgent):
    """Analyzes the student's current cognitive stage, concept mastery, and learning profile.

    Publishes to shared memory:
    - cognitive_stage: detected stage + confidence
    - concept_mastery: per-concept scores
    - learning_profile: modality, pace, bloom preferences
    """

    @property
    def agent_type(self) -> str:
        return "pedagogical"

    async def analyze(self, state: dict[str, Any]) -> dict[str, Any]:
        is_programming = state.get("is_programming_course", False)

        diagnostic = self._load_diagnostic()

        stage_result = self._detect_cognitive_stage(state) if is_programming else None

        mastered, weak = self._load_concept_mastery()

        profile = self._extract_profile(diagnostic)

        result = {
            "cognitive_stage": stage_result.get("current_stage", "general") if stage_result else "general",
            "stage_confidence": stage_result.get("confidence", 0.0) if stage_result else 0.0,
            "mastered_concepts": mastered,
            "weak_concepts": weak,
            "learning_profile": profile,
            "is_programming": is_programming,
            "concept_count": len(mastered) + len(weak),
        }

        await self.publish_observation(
            f"{self.context_key}:pedagogical:stage",
            result,
            memory_type="inference",
            confidence=stage_result.get("confidence", 0.5) if stage_result else 0.5,
        )

        return result

    def _detect_cognitive_stage(self, state: dict) -> dict:
        try:
            detector = CognitiveStageDetector(
                self.uow.db,
                self.student_id,
                self.course_id,
            )
            return detector.detect()
        except Exception as e:
            logger.warning("Cognitive stage detection failed: %s", e)
            return {
                "current_stage": "pre_algorithmic",
                "confidence": 0.3,
                "mastered_concepts": [],
                "missing_critical": [],
            }

    def _load_diagnostic(self) -> dict | None:
        try:
            diag = (
                self.uow.db.query(DiagnosticResult)
                .filter(
                    DiagnosticResult.student_id == self.student_id,
                    DiagnosticResult.course_id == self.course_id,
                )
                .order_by(DiagnosticResult.completed_at.desc())
                .first()
            )
            if diag:
                return {
                    "answers": diag.answers,
                    "modality": diag.dominant_modality,
                    "profile": diag.profile,
                }
        except Exception as e:
            logger.debug("Diagnostic load failed: %s", e)
        return None

    def _load_concept_mastery(self) -> tuple[list[str], list[str]]:
        mastered = []
        weak = []
        try:
            strengths = (
                self.uow.db.query(StrengthRecord)
                .filter(StrengthRecord.student_id == self.student_id)
                .all()
            )
            weaknesses = (
                self.uow.db.query(WeaknessRecord)
                .filter(
                    WeaknessRecord.student_id == self.student_id,
                    WeaknessRecord.resolved == False,
                )
                .all()
            )
            concept_values = {c.value for c in ProgrammingConcept}
            for s in strengths:
                if s.topic.lower() in concept_values:
                    mastered.append(s.topic.lower())
            for w in weaknesses:
                if w.topic.lower() in concept_values:
                    weak.append(w.topic.lower())
        except Exception as e:
            logger.debug("Concept mastery load failed: %s", e)
        return mastered, weak

    def _extract_profile(self, diagnostic: dict | None) -> dict:
        if diagnostic and diagnostic.get("profile"):
            return diagnostic["profile"]
        if diagnostic and diagnostic.get("modality"):
            return {"dominant_modality": diagnostic["modality"]}
        return {}
