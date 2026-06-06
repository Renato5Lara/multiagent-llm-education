"""RiskAgent — detects risk factors, generates early warnings, prerequisite recommendations."""

from __future__ import annotations

import logging
from typing import Any

from app.agents.base import BaseAgent
from app.models.student_memory import WeaknessRecord
from app.models.enrollment import Enrollment, EnrollmentStatus
from app.models.course_prerequisite import CoursePrerequisite
from app.models.student_progress import StudentProgress

logger = logging.getLogger(__name__)


class RiskAgent(BaseAgent):
    """Detects academic risk: weak concepts, missing prerequisites, low progress.

    Reads from shared memory:
    - pedagogical:stage
    - adaptive:pathway

    Writes to shared memory:
    - risk:assessment
    - risk:early_warnings
    """

    @property
    def agent_type(self) -> str:
        return "risk"

    async def analyze(self, state: dict[str, Any]) -> dict[str, Any]:
        weak_concepts = self._get_weak_concepts()
        prerequisite_gaps = self._get_prerequisite_gaps()
        progress_data = self._get_progress_data()

        risk_score = self._compute_risk_score(
            len(weak_concepts),
            len(prerequisite_gaps),
            progress_data,
        )
        risk_level = self._risk_level(risk_score)

        early_warnings = self._build_early_warnings(
            risk_level, weak_concepts, prerequisite_gaps, progress_data,
        )
        recommendations = self._build_recommendations(
            risk_level, weak_concepts, prerequisite_gaps,
        )

        result = {
            "risk_score": risk_score,
            "risk_level": risk_level,
            "weak_concepts": weak_concepts,
            "prerequisite_gaps": prerequisite_gaps,
            "progress_percentage": progress_data.get("progress_percentage", 0),
            "early_warnings": early_warnings,
            "recommendations": recommendations,
        }

        await self.publish_observation(
            f"{self.context_key}:risk:assessment",
            result,
            memory_type="inference",
            confidence=0.85,
        )

        for warning in early_warnings:
            await self.publish_observation(
                f"{self.context_key}:risk:warning:{warning.get('id', 'unknown')}",
                warning,
                memory_type="signal",
                confidence=warning.get("confidence", 0.5),
            )

        return result

    def _get_weak_concepts(self) -> list[str]:
        try:
            records = (
                self.uow.db.query(WeaknessRecord)
                .filter(
                    WeaknessRecord.student_id == self.student_id,
                    WeaknessRecord.resolved == False,
                )
                .order_by(WeaknessRecord.detection_count.desc())
                .limit(10)
                .all()
            )
            return [
                {
                    "topic": r.topic,
                    "bloom_level": r.bloom_level,
                    "detection_count": r.detection_count,
                    "last_detected": r.last_detected_at.isoformat() if r.last_detected_at else None,
                }
                for r in records
            ]
        except Exception as e:
            logger.debug("Weak concepts load failed: %s", e)
            return []

    def _get_prerequisite_gaps(self) -> list[dict]:
        try:
            prereqs = (
                self.uow.db.query(CoursePrerequisite)
                .filter(CoursePrerequisite.course_id == self.course_id)
                .all()
            )
            gaps = []
            for p in prereqs:
                completed = (
                    self.uow.db.query(Enrollment)
                    .filter(
                        Enrollment.student_id == self.student_id,
                        Enrollment.course_id == p.prerequisite_course_id,
                        Enrollment.status == EnrollmentStatus.COMPLETED,
                    )
                    .first()
                )
                if not completed:
                    gaps.append({
                        "prerequisite_course_id": p.prerequisite_course_id,
                        "prerequisite_course_name": p.prerequisite_course_id,
                    })
            return gaps
        except Exception as e:
            logger.debug("Prerequisite gaps load failed: %s", e)
            return []

    def _get_progress_data(self) -> dict[str, Any]:
        try:
            progress = (
                self.uow.db.query(StudentProgress)
                .filter(
                    StudentProgress.student_id == self.student_id,
                    StudentProgress.course_id == self.course_id,
                )
                .all()
            )
            total = len(progress)
            completed = sum(1 for p in progress if p.completed)
            return {
                "total_modules": total,
                "completed_modules": completed,
                "progress_percentage": (completed / total * 100) if total > 0 else 0,
            }
        except Exception as e:
            logger.debug("Progress data load failed: %s", e)
            return {"total_modules": 0, "completed_modules": 0, "progress_percentage": 0}

    def _compute_risk_score(self, weak_count: int, prereq_gaps: int, progress: dict) -> float:
        score = 0.0
        score += weak_count * 0.1
        score += prereq_gaps * 0.2
        progress_pct = progress.get("progress_percentage", 50)
        if progress_pct < 20:
            score += 0.3
        elif progress_pct < 50:
            score += 0.15
        return min(score, 1.0)

    def _risk_level(self, score: float) -> str:
        if score >= 0.6:
            return "alto"
        if score >= 0.3:
            return "medio"
        return "bajo"

    def _build_early_warnings(
        self, level: str, weak: list, prereq_gaps: list, progress: dict,
    ) -> list[dict]:
        warnings = []
        if level == "alto":
            warnings.append({
                "id": "risk_high",
                "severity": "critical",
                "message": "Riesgo académico alto detectado",
                "confidence": 0.9,
            })
        if prereq_gaps:
            warnings.append({
                "id": "prereq_gaps",
                "severity": "warning",
                "message": f"{len(prereq_gaps)} prerequisitos sin completar",
                "confidence": 0.85,
            })
        if weak:
            weak_topics = [w["topic"] for w in weak[:3]]
            warnings.append({
                "id": "weak_concepts",
                "severity": "warning",
                "message": f"Conceptos débiles: {', '.join(weak_topics)}",
                "confidence": 0.8,
            })
        if progress.get("progress_percentage", 100) < 20:
            warnings.append({
                "id": "low_progress",
                "severity": "warning",
                "message": "Progreso menor al 20%",
                "confidence": 0.7,
            })
        return warnings

    def _build_recommendations(self, level: str, weak: list, prereq_gaps: list) -> list[str]:
        recs = []
        if prereq_gaps:
            recs.append("Completar cursos prerrequisito antes de avanzar")
        if weak:
            topics = [w["topic"] for w in weak[:3]]
            recs.append(f"Reforzar: {', '.join(topics)}")
        if level == "alto":
            recs.append("Solicitar tutoría académica personalizada")
            recs.append("Establecer plan de recuperación con el docente")
        elif level == "medio":
            recs.append("Mantener ritmo y priorizar conceptos débiles")
        else:
            recs.append("Continuar con el plan actual. Buen progreso.")
        return recs
