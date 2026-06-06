"""ConsensusMediator — resuelve conflictos, coordina el swarm y mantiene consistencia global."""

from __future__ import annotations

import logging
from typing import Any

from app.agents.base import BaseAgent
from app.schemas.pedagogical_orchestration import (
    OrchestrationResult,
    ConsistencyReport,
    NarrativeMemory,
    GeneratedPrompt,
    PedagogicalStructure,
    MultimodalPlan,
    AdaptationPlan,
)

logger = logging.getLogger(__name__)


class ConsensusMediator(BaseAgent):
    """Mediador final que resuelve conflictos, coordina el swarm y produce el resultado consolidado.

    Responsabilidades:
    - Resolver conflictos entre agentes
    - Coordinar la salida del swarm
    - Consolidar resultado final
    - Validar consistencia global
    - Proveer explicabilidad del proceso

    Lee de shared memory:
    - research:findings
    - pedagogical:structure
    - adaptive:plan
    - multimodal:plan
    - prompts:generated
    - consistency:report
    - narrative:memory

    Escribe en shared memory:
    - orchestration:result
    """

    @property
    def agent_type(self) -> str:
        return "consensus_mediator"

    async def analyze(self, state: dict[str, Any]) -> dict[str, Any]:
        warnings = []
        execution_summary = {}

        research_result = state.get("research_result", {})
        pedagogical_structure = state.get("pedagogical_structure", {})
        adaptation_plan = state.get("adaptation_plan", {})
        multimodal_plan = state.get("multimodal_plan", {})
        prompts_data = state.get("prompts", [])
        consistency_data = state.get("consistency_result", {})
        narrative_memory = state.get("narrative_memory", {})

        pedagogical_obj = None
        if isinstance(pedagogical_structure, dict) and pedagogical_structure.get("sections"):
            try:
                pedagogical_obj = PedagogicalStructure(**pedagogical_structure)
            except Exception:
                warnings.append("Error al parsear estructura pedagógica")

        multimodal_obj = None
        if isinstance(multimodal_plan, dict) and multimodal_plan.get("decisions"):
            try:
                multimodal_obj = MultimodalPlan(**multimodal_plan)
            except Exception:
                warnings.append("Error al parsear plan multimodal")

        adaptation_obj = None
        if isinstance(adaptation_plan, dict) and adaptation_plan.get("difficulty_level"):
            try:
                adaptation_obj = AdaptationPlan(**adaptation_plan)
            except Exception:
                warnings.append("Error al parsear plan de adaptación")

        parsed_prompts = []
        if isinstance(prompts_data, list):
            for p in prompts_data:
                if isinstance(p, dict) and p.get("prompt_type"):
                    try:
                        parsed_prompts.append(GeneratedPrompt(**p))
                    except Exception:
                        warnings.append(f"Error al parsear prompt: {p.get('prompt_type', 'unknown')}")

        consistency_raw = {}
        if isinstance(consistency_data, dict):
            if "report" in consistency_data:
                consistency_raw = consistency_data["report"]
            else:
                consistency_raw = consistency_data

        consistency_obj = None
        if consistency_raw:
            try:
                consistency_obj = ConsistencyReport(**consistency_raw)
            except Exception:
                warnings.append("Error al parsear reporte de consistencia")

        narrative_memory_obj = None
        if isinstance(narrative_memory, dict) and narrative_memory.get("characters") is not None:
            try:
                narrative_memory_obj = NarrativeMemory(**narrative_memory)
            except Exception:
                pass

        if consistency_obj and not consistency_obj.passed:
            for issue in consistency_obj.issues:
                if issue.severity == "error":
                    warnings.append(
                        f"Error de consistencia ({issue.category}): {issue.description[:100]}"
                    )

        direct_text = {}
        if multimodal_obj:
            for section_type in multimodal_obj.text_sections:
                matching = [s for s in (pedagogical_obj.sections if pedagogical_obj else [])
                           if s.section_type.value == section_type or s.section_type == section_type]
                if matching:
                    direct_text[section_type] = (
                        f"Contenido generado para '{matching[0].title}': "
                        f"{matching[0].description}"
                    )

        result = OrchestrationResult(
            topic=state.get("topic", ""),
            pedagogical_structure=pedagogical_obj,
            multimodal_plan=multimodal_obj,
            prompts=parsed_prompts,
            direct_text=direct_text,
            consistency_report=consistency_obj,
            research_result=None,
            adaptation_plan=adaptation_obj,
            narrative_memory=narrative_memory_obj,
            warnings=warnings,
            execution_summary=self._build_execution_summary(state),
        )

        output = result.model_dump()

        await self.publish_observation(
            f"{self.context_key}:orchestration:result",
            output,
            memory_type="inference",
            confidence=0.95,
        )

        return output

    def _build_execution_summary(self, state: dict[str, Any]) -> dict[str, Any]:
        return {
            "topic": state.get("topic", ""),
            "has_research": bool(state.get("research_result")),
            "has_pedagogical_structure": bool(state.get("pedagogical_structure")),
            "has_adaptation": bool(state.get("adaptation_plan")),
            "has_multimodal_plan": bool(state.get("multimodal_plan")),
            "has_prompts": bool(state.get("prompts")),
            "has_consistency_check": bool(state.get("consistency_result")),
            "agent_steps_completed": sum(
                1 for key in [
                    "research_result", "pedagogical_structure", "adaptation_plan",
                    "multimodal_plan", "prompts", "consistency_result",
                ] if state.get(key)
            ),
            "total_agent_steps": 7,
        }
