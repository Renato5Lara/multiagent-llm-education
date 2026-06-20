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

        self._trace_evidence(
            source="shared_memory",
            key=f"{self.context_key}:adaptive:inference",
            value={"keys_found": list(student_profile.keys()), "profile_source": profile_source},
            confidence=0.90 if student_profile else 0.0,
            memory_type="inference",
        )

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

        self._trace_rationale(adaptation_rationale)

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

        _bloom_lvs = student_profile.get("preferred_bloom_levels", [2, 3])
        _avg_bloom = sum(_bloom_lvs) / len(_bloom_lvs) if _bloom_lvs else 2.5
        result["_decision_summary"] = (
            f"Adapted: difficulty={difficulty}, bloom={bloom_range}, pace={pace}, "
            f"depth={depth}, reinforcement={reinforcement} "
            f"[source={profile_source}, avg_bloom={_avg_bloom:.1f}]"
        )
        result["_confidence"] = 0.85 if profile_source == "historical_memory" else 0.55

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

        _near_threshold = abs(avg_bloom - 2.5) <= 0.3 or abs(avg_bloom - 4.0) <= 0.3
        _diff_confidence = (
            0.50 if profile_source == "defaults"
            else 0.70 if _near_threshold
            else 0.90
        )

        return {
            "profile_source": profile_source,
            "profile_signals_present": list(student_profile.keys()),
            "difficulty_decision": {
                "result": difficulty,
                "signal": f"avg_bloom={avg_bloom:.2f} (preferred_bloom_levels={bloom_levels})",
                "rule": "avg_bloom>=4→advanced, >=2.5→intermediate, else→beginner",
                "confidence": _diff_confidence,
                "evidence": {
                    "avg_bloom": round(avg_bloom, 2),
                    "bloom_levels": bloom_levels,
                    "profile_source": profile_source,
                },
            },
            "pace_decision": {
                "result": pace,
                "signal": (
                    f"pace='{pace}' present in student profile"
                    if "pace" in student_profile
                    else "pace absent from profile → default=moderate"
                ),
                "rule": "use profile.pace directly if present, else default=moderate",
                "confidence": 0.90 if "pace" in student_profile else 0.50,
                "evidence": {"pace_in_profile": "pace" in student_profile},
            },
            "bloom_range_decision": {
                "result": bloom_range,
                "signal": f"difficulty={difficulty} → deterministic bloom mapping",
                "rule": "advanced→[3,6]; intermediate→[1,4]; beginner→[1,3]",
                "confidence": _diff_confidence,
                "evidence": {"difficulty_level": difficulty, "avg_bloom": round(avg_bloom, 2)},
            },
            "modality_decision": {
                "result": modalities,
                "signal": (
                    f"preferred_modalities={preferred_modalities} from profile (top 3 selected)"
                    if preferred_modalities
                    else "no preferred_modalities in profile → default=[visual, reading]"
                ),
                "rule": "select top 3 from profile.preferred_modalities; default=[visual,reading] if absent",
                "confidence": (
                    0.90 if len(preferred_modalities) >= 2
                    else 0.75 if len(preferred_modalities) == 1
                    else 0.50
                ),
                "evidence": {
                    "profile_preferred": preferred_modalities,
                    "selected": modalities,
                },
            },
            "depth_decision": {
                "result": depth,
                "signal": f"difficulty={difficulty}, pace={pace}",
                "rule": "beginner OR pace=slow → detailed; advanced → basic; else → standard",
                "confidence": 0.85,
                "evidence": {"difficulty": difficulty, "pace": pace},
            },
            "reinforcement_decision": {
                "result": reinforcement,
                "signal": f"difficulty={difficulty} → reinforcement frequency derived",
                "rule": "beginner→high; advanced→low; intermediate→normal",
                "confidence": _diff_confidence,
                "evidence": {"difficulty_level": difficulty},
            },
        }
