"""AdaptiveAgent — selects pathway, adjusts difficulty, calibrates Bloom range and pace."""

from __future__ import annotations

import logging
from typing import Any

from app.agents.base import BaseAgent
from app.models.programming_domain import ProgrammingConcept, ProgrammingStage
from app.services.programming_pathway_service import (
    ProgrammingPathwayEngine,
    ProgrammingPathGenerator,
)
from app.memory.patterns import PatternDetector

logger = logging.getLogger(__name__)


class AdaptiveAgent(BaseAgent):
    """Adjusts learning parameters based on pedagogical analysis and historical patterns.

    Responsibilities:
    - Select pathway (standard/accelerated/reinforced/visual_first)
    - Calibrate Bloom range
    - Adjust pace
    - Generate concept sequence

    Reads from shared memory:
    - pedagogical:stage (from PedagogicalAgent)
    - student:baseline

    Writes to shared memory:
    - adaptive:pathway
    - adaptive:concept_sequence
    """

    @property
    def agent_type(self) -> str:
        return "adaptive"

    async def analyze(self, state: dict[str, Any]) -> dict[str, Any]:
        is_programming = state.get("is_programming_course", False)

        if not is_programming:
            return {
                "pathway": "standard",
                "bloom_range": [1, 6],
                "pace": "moderate",
                "concept_sequence": [],
            }

        # Read pedagogical analysis from shared memory
        pedagogical = await self._read_pedagogical()
        stage_str = pedagogical.get("cognitive_stage", "pre_algorithmic")
        mastered = pedagogical.get("mastered_concepts", [])
        weak = pedagogical.get("weak_concepts", [])

        try:
            cognitive_stage = ProgrammingStage(stage_str)
        except ValueError:
            cognitive_stage = ProgrammingStage.PRE_ALGORITHMIC

        mastered_set = set()
        for c in mastered:
            try:
                mastered_set.add(ProgrammingConcept(c))
            except ValueError:
                pass

        weak_set = set()
        for c in weak:
            try:
                weak_set.add(ProgrammingConcept(c))
            except ValueError:
                pass

        # Detect patterns from recent memory
        patterns = await self._detect_patterns()

        # Build pathway engine
        engine = ProgrammingPathwayEngine(
            cognitive_stage=cognitive_stage,
            mastered_concepts=mastered_set,
            weak_concepts=weak_set,
            ct_scores=patterns,
        )
        pathway_plan = engine.build_pathway_plan()

        # Generate topological concept sequence
        topo_order = ProgrammingPathGenerator.generate_topological_order()
        bloom_min, bloom_max = pathway_plan.get("bloom_range", [1, 4])
        bloom_filtered = ProgrammingPathGenerator.filter_by_bloom_range(
            topo_order, bloom_min, bloom_max,
        )

        concept_sequence = [c.value for c in bloom_filtered]

        result = {
            "pathway": pathway_plan.get("pathway", "standard"),
            "bloom_range": [bloom_min, bloom_max],
            "pace": self._determine_pace(pathway_plan, patterns),
            "concept_sequence": concept_sequence,
            "exercises_per_concept": pathway_plan.get("exercises_per_concept", 3),
            "visual_emphasis": pathway_plan.get("visual_emphasis", False),
            "challenge_frequency": pathway_plan.get("challenge_frequency", 0.2),
        }

        await self.publish_observation(
            f"{self.context_key}:adaptive:pathway",
            result,
            memory_type="inference",
            confidence=0.8,
        )

        return result

    async def _read_pedagogical(self) -> dict[str, Any]:
        records = await self.query_memory(memory_type="inference", limit=10)
        for r in reversed(records):
            try:
                val = r.value if hasattr(r, "value") else {}
                if isinstance(val, dict) and val.get("cognitive_stage"):
                    return val
            except Exception:
                continue
        return {}

    async def _detect_patterns(self) -> dict[str, float]:
        records = await self.query_memory(limit=20)
        if not records:
            return {}
        try:
            detector = PatternDetector()
            patterns = detector.detect_all(records)
            ct_scores = {}
            for p in patterns:
                if hasattr(p, "pattern_type") and p.pattern_type == "improvement":
                    ct_scores["average"] = min(p.strength, 1.0)
            return ct_scores
        except Exception:
            return {}

    def _determine_pace(self, plan: dict, patterns: dict) -> str:
        pathway = plan.get("pathway", "standard")
        if pathway == "accelerated":
            return "fast"
        if pathway == "reinforced":
            return "slow"
        if patterns.get("average", 0.5) > 0.7:
            return "fast"
        return "moderate"
