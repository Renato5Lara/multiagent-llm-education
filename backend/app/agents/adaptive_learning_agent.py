"""AdaptiveLearningAgent — adapta dificultad, modalidad, complejidad y profundidad explicativa."""

from __future__ import annotations

import logging
from typing import Any

from app.agents.base import BaseAgent
from app.schemas.pedagogical_orchestration import AdaptationPlan

logger = logging.getLogger(__name__)


class AdaptiveLearningAgent(BaseAgent):
    """Adapta los parámetros de aprendizaje según el perfil del estudiante y el contexto.

    Responsabilidades:
    - Adaptar dificultad (principiante/intermedio/avanzado)
    - Adaptar modalidad preferida
    - Adaptar complejidad (Bloom range)
    - Adaptar profundidad explicativa

    Lee de shared memory:
    - pedagogical:structure
    - student:profile (histórico)

    Escribe en shared memory:
    - adaptive:plan
    - adaptive:rationale (trazabilidad de decisiones de adaptación)
    """

    @property
    def agent_type(self) -> str:
        return "adaptive_learning"

    async def analyze(self, state: dict[str, Any]) -> dict[str, Any]:
        pedagogical = state.get("pedagogical_structure", {})
        sections = pedagogical.get("sections", []) if isinstance(pedagogical, dict) else []

        student_profile = await self._load_student_profile()
        profile_source = "historical_memory" if student_profile else "defaults"

        difficulty = self._determine_difficulty(student_profile)
        pace = self._determine_pace(student_profile)
        bloom_range = self._determine_bloom_range(difficulty, sections)
        modalities = self._determine_modalities(student_profile, sections)
        depth = self._determine_explanation_depth(difficulty, student_profile)
        reinforcement = self._determine_reinforcement(difficulty)

        adaptation_rationale = self._build_adaptation_rationale(
            student_profile=student_profile,
            profile_source=profile_source,
            difficulty=difficulty,
            pace=pace,
            bloom_range=bloom_range,
            modalities=modalities,
            depth=depth,
            reinforcement=reinforcement,
        )

        plan = AdaptationPlan(
            difficulty_level=difficulty,
            pace_adjustment=pace,
            bloom_range=bloom_range,
            modality_preferences=modalities,
            explanation_depth=depth,
            concept_sequence=[s.get("title", "") for s in sections],
            reinforcement_frequency=reinforcement,
            adaptation_rationale=adaptation_rationale,
        )

        result = plan.model_dump()

        await self.publish_observation(
            f"{self.context_key}:adaptive:plan",
            result,
            memory_type="inference",
            confidence=0.85,
        )

        return result

    async def _load_student_profile(self) -> dict[str, Any]:
        records = await self.query_memory(memory_type="inference", limit=10)
        for r in reversed(records):
            try:
                val = r.value if hasattr(r, "value") else {}
                if isinstance(val, dict):
                    profile = val.get("learning_profile") or val.get("profile") or {}
                    if profile:
                        return profile if isinstance(profile, dict) else {}
            except Exception:
                continue
        return {}

    def _determine_difficulty(self, profile: dict) -> str:
        bloom_levels = profile.get("preferred_bloom_levels", [2, 3])
        avg_bloom = sum(bloom_levels) / len(bloom_levels) if bloom_levels else 2.5
        if avg_bloom >= 4:
            return "advanced"
        elif avg_bloom >= 2.5:
            return "intermediate"
        return "beginner"

    def _determine_pace(self, profile: dict) -> str:
        return profile.get("pace", "moderate")

    def _determine_bloom_range(self, difficulty: str, sections: list[dict]) -> list[int]:
        if difficulty == "advanced":
            return [3, 6]
        elif difficulty == "beginner":
            return [1, 3]
        return [1, 4]

    def _determine_modalities(self, profile: dict, sections: list[dict]) -> list[str]:
        preferred = profile.get("preferred_modalities", ["visual", "reading"])
        return preferred[:3]

    def _determine_explanation_depth(self, difficulty: str, profile: dict) -> str:
        pace = profile.get("pace", "moderate")
        if difficulty == "beginner" or pace == "slow":
            return "detailed"
        elif difficulty == "advanced":
            return "basic"
        return "standard"

    def _determine_reinforcement(self, difficulty: str) -> str:
        if difficulty == "beginner":
            return "high"
        elif difficulty == "advanced":
            return "low"
        return "normal"

    def _build_adaptation_rationale(
        self,
        student_profile: dict,
        profile_source: str,
        difficulty: str,
        pace: str,
        bloom_range: list[int],
        modalities: list[str],
        depth: str,
        reinforcement: str,
    ) -> dict[str, Any]:
        bloom_levels = student_profile.get("preferred_bloom_levels", [2, 3])
        avg_bloom = sum(bloom_levels) / len(bloom_levels) if bloom_levels else 2.5
        preferred_modalities = student_profile.get("preferred_modalities", [])

        return {
            "profile_source": profile_source,
            "profile_signals_present": list(student_profile.keys()),
            "difficulty_decision": {
                "result": difficulty,
                "signal": f"avg_bloom_from_profile={avg_bloom:.1f}",
                "rule": "avg_bloom>=4→advanced, >=2.5→intermediate, else→beginner",
            },
            "pace_decision": {
                "result": pace,
                "signal": student_profile.get("pace", "not_in_profile_→_default_moderate"),
            },
            "bloom_range_decision": {
                "result": bloom_range,
                "derived_from": f"difficulty={difficulty}",
                "pedagogical_intent": (
                    "Bloom range caps the cognitive demand ceiling for this learner, "
                    "ensuring content is neither trivially simple nor excessively complex."
                ),
            },
            "modality_decision": {
                "result": modalities,
                "profile_preferred": preferred_modalities or "not_in_profile_→_default_visual+reading",
                "note": "Top 3 modalities from profile drive multimodal planning agent priorities.",
            },
            "depth_decision": {
                "result": depth,
                "signals": {
                    "difficulty": difficulty,
                    "pace": pace,
                },
                "rule": "beginner/slow→detailed, advanced→basic, otherwise→standard",
            },
            "reinforcement_decision": {
                "result": reinforcement,
                "rationale": (
                    "Beginners benefit from high reinforcement frequency; "
                    "advanced learners need less repetition."
                ),
            },
        }
