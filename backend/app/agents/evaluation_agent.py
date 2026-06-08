"""EvaluationAgent — generates evaluations, tracks progress, integrates with ConsensusEngine and CollectiveInference."""

from __future__ import annotations

import logging
from typing import Any

from app.agents.base import BaseAgent
from app.models.programming_domain import ProgrammingConcept, ProgrammingStage
from app.services.exercise_generator_service import ProgrammingExerciseGenerator
from app.models.evaluation_attempt import EvaluationAttempt
from app.models.student_progress import StudentProgress
from app.models.learning_objective import LearningObjective

logger = logging.getLogger(__name__)


class EvaluationAgent(BaseAgent):
    """Generates evaluations and tracks student progress.

    Responsibilities:
    - Generate exercises per concept at calibrated Bloom level
    - Track evaluation attempts and scores
    - Compute concept-level mastery from evaluations
    - Integrate with ConsensusEngine for progression decisions
    - Feed data to CollectiveInference

    Reads from shared memory:
    - adaptive:pathway (concept sequence)
    - pedagogical:stage

    Writes to shared memory:
    - evaluation:plan
    - evaluation:mastery_scores
    """

    @property
    def agent_type(self) -> str:
        return "evaluation"

    async def analyze(self, state: dict[str, Any]) -> dict[str, Any]:
        is_programming = state.get("is_programming_course", False)

        if not is_programming:
            return self._general_evaluation(state)

        pathway = await self._read_pathway()
        concept_sequence = pathway.get("concept_sequence", [])
        bloom_range = pathway.get("bloom_range", [1, 3])
        exercises_per = pathway.get("exercises_per_concept", 3)

        # Generate exercises for first concepts
        generator = ProgrammingExerciseGenerator()
        exercises = []

        for concept_str in concept_sequence[:5]:
            try:
                concept = ProgrammingConcept(concept_str)
                bloom = min(bloom_range[0] + 1, bloom_range[1])
                generated = generator.generate(concept, bloom_level=bloom, count=exercises_per)
                for ex in generated:
                    exercises.append({
                        "concept": ex.concept,
                        "bloom_level": ex.bloom_level,
                        "title": ex.title,
                        "problem": ex.problem_statement,
                        "difficulty": ex.difficulty,
                        "hints": ex.hints,
                    })
            except (ValueError, Exception):
                continue

        # Load historical mastery from past evaluations
        mastery = self._compute_mastery_scores(concept_sequence)

        result = {
            "exercises": exercises,
            "mastery_scores": mastery,
            "total_exercises": len(exercises),
            "concepts_covered": len(set(e["concept"] for e in exercises)),
            "evaluation_ready": True,
        }

        await self.publish_observation(
            f"{self.context_key}:evaluation:plan",
            result,
            memory_type="inference",
            confidence=0.85,
        )

        return result

    def _general_evaluation(self, state: dict) -> dict:
        return {
            "exercises": [],
            "mastery_scores": {},
            "evaluation_ready": False,
            "evaluation_type": "general",
        }

    async def _read_pathway(self) -> dict:
        records = await self.query_memory(memory_type="inference", limit=10)
        for r in reversed(records):
            try:
                val = r.value if hasattr(r, "value") else {}
                if isinstance(val, dict) and val.get("concept_sequence"):
                    return val
            except Exception:
                continue
        return {}

    def _compute_mastery_scores(self, concept_sequence: list[str]) -> dict[str, float]:
        mastery = {}
        try:
            for concept_str in concept_sequence:
                attempts = (
                    self.uow.db.query(EvaluationAttempt)
                    .filter(
                        EvaluationAttempt.student_id == self.student_id,
                    )
                    .all()
                )
                attempts = [a for a in attempts if (a.metadata_json or {}).get("concept") == concept_str]
                if attempts:
                    scores = [a.score for a in attempts if a.score is not None]
                    if scores:
                        # EWMA: recent attempts weighted more
                        weight = 1.0
                        weighted_sum = 0.0
                        total_weight = 0.0
                        for s in reversed(scores):
                            weighted_sum += s * weight
                            total_weight += weight
                            weight *= 0.7
                        mastery[concept_str] = round(weighted_sum / total_weight, 4) if total_weight > 0 else 0.5
                    else:
                        mastery[concept_str] = 0.0
                else:
                    mastery[concept_str] = 0.0
        except Exception as e:
            logger.debug("Mastery computation failed: %s", e)
            for c in concept_sequence:
                mastery[c] = 0.0
        return mastery
