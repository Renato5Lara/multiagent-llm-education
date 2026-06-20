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

    Lee de state (inter-agent):
    - debate_context (conflicto AdaptiveLearning vs EvaluationAgent)

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
        debate_context = state.get("debate_context")

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

        _steps_completed = sum(
            1 for key in [
                "research_result", "pedagogical_structure", "adaptation_plan",
                "evaluation_result", "multimodal_plan", "prompts", "consistency_result",
            ]
            if state.get(key)
        )
        _consistency_passed = consistency_obj.passed if consistency_obj else None
        _warning_count = len(warnings)

        # Inter-agent debate resolution
        has_conflict = bool(debate_context and debate_context.get("conflict"))
        resolved_difficulty = (
            adaptation_obj.difficulty_level
            if adaptation_obj is not None
            else state.get("adaptation_plan", {}).get("difficulty_level", "intermediate")
        )
        if debate_context:
            agent_debate = {
                "has_debate_context": True,
                "conflict": has_conflict,
                "adaptive_difficulty": debate_context.get("adaptive_difficulty", "unknown"),
                "evaluation_override": debate_context.get("evaluation_override", "none"),
                "resolved_difficulty": resolved_difficulty,
                "recommendation": debate_context.get("recommendation", ""),
                "resolution_reason": self._build_resolution_reason(debate_context),
            }
        else:
            agent_debate = {
                "has_debate_context": False,
                "conflict": False,
                "adaptive_difficulty": resolved_difficulty,
                "evaluation_override": "none",
                "resolved_difficulty": resolved_difficulty,
                "recommendation": None,
                "resolution_reason": (
                    "No inter-agent conflict: EvaluationAgent did not override "
                    "AdaptiveLearning proposal."
                ),
            }

        self._trace_evidence(
            source="state",
            key="pipeline_outputs",
            value={
                "has_research": bool(state.get("research_result")),
                "has_pedagogical": bool(state.get("pedagogical_structure")),
                "has_adaptation": bool(state.get("adaptation_plan")),
                "has_evaluation": bool(state.get("evaluation_result")),
                "has_multimodal": bool(state.get("multimodal_plan")),
                "has_prompts": bool(state.get("prompts")),
                "has_consistency": bool(state.get("consistency_result")),
            },
            confidence=0.9 if _steps_completed >= 5 else 0.6,
        )
        self._trace_evidence(
            source="state",
            key="debate_context",
            value={
                "has_debate_context": agent_debate["has_debate_context"],
                "conflict": has_conflict,
                "adaptive_difficulty": agent_debate["adaptive_difficulty"],
                "evaluation_override": agent_debate["evaluation_override"],
                "recommendation": agent_debate["recommendation"],
            },
            confidence=0.90 if debate_context else 0.50,
        )
        self._trace_dimension(
            dimension="pipeline_completeness",
            result=f"{_steps_completed}/7 pipeline steps completed",
            signal=f"research={bool(state.get('research_result'))}, pedagogical={bool(state.get('pedagogical_structure'))}, evaluation={bool(state.get('evaluation_result'))}, adaptation={bool(state.get('adaptation_plan'))}, multimodal={bool(state.get('multimodal_plan'))}, prompts={bool(state.get('prompts'))}, consistency={bool(state.get('consistency_result'))}",
            rule="consolidate all steps with non-empty state output; 7/7=fully grounded pipeline, <7=partial execution",
            confidence=0.9 if _steps_completed >= 5 else 0.6,
            evidence={"steps_completed": _steps_completed, "total_steps": 7},
        )
        self._trace_dimension(
            dimension="consistency_gate",
            result=f"consistency={'passed' if _consistency_passed else 'failed' if _consistency_passed is False else 'not_run'}",
            signal=f"consistency_obj.passed={_consistency_passed}, parse_failure_warnings={_warning_count}",
            rule="consistency_obj.passed=False → error-severity issues logged as warnings; does not block final consolidation",
            confidence=0.90,
            evidence={"consistency_passed": _consistency_passed, "parse_warnings": _warning_count},
        )
        self._trace_dimension(
            dimension="consolidation_quality",
            result=f"warnings={_warning_count}, steps_completed={_steps_completed}/7",
            signal=f"each failed schema parse (pedagogical, multimodal, adaptation, prompts, consistency) adds a warning",
            rule="warning_count=0 AND steps>=5 → high quality consolidation; each warning reduces confidence",
            confidence=0.90 if _warning_count == 0 else 0.70,
            evidence={"warning_count": _warning_count, "steps_completed": _steps_completed},
        )
        self._trace_dimension(
            dimension="debate_resolution",
            result=f"conflict={has_conflict}, resolved_difficulty='{resolved_difficulty}'",
            signal=(
                f"adaptive_difficulty='{agent_debate['adaptive_difficulty']}', "
                f"evaluation_override='{agent_debate['evaluation_override']}', "
                f"recommendation='{agent_debate['recommendation']}'"
            ),
            rule=(
                "if debate_context.conflict=True: EvaluationAgent override wins; "
                "resolved_difficulty = adaptation_plan.difficulty_level post-override; "
                "if no debate_context: no conflict, AdaptiveLearning proposal preserved"
            ),
            confidence=0.95 if debate_context else 0.80,
            evidence={
                "has_debate_context": agent_debate["has_debate_context"],
                "conflict": has_conflict,
                "resolved_difficulty": resolved_difficulty,
                "recommendation": agent_debate["recommendation"],
            },
        )

        output["agent_debate"] = agent_debate

        await self.publish_observation(
            f"{self.context_key}:orchestration:result",
            output,
            memory_type="inference",
            confidence=0.95,
        )

        _debate_suffix = ""
        if has_conflict:
            _debate_suffix = (
                f" | AdaptiveLearning proposed '{agent_debate['adaptive_difficulty']}' but "
                f"EvaluationAgent recommended '{agent_debate['evaluation_override']}' "
                f"({agent_debate['recommendation']}). Resolved: '{agent_debate['resolved_difficulty']}'."
            )
        output["_decision_summary"] = (
            f"Consolidated pipeline: {_steps_completed}/7 steps, "
            f"consistency={'passed' if _consistency_passed else 'failed' if _consistency_passed is False else 'not_run'}, "
            f"warnings={_warning_count}"
            + _debate_suffix
        )
        output["_confidence"] = 0.90 if (_steps_completed >= 5 and _warning_count == 0) else 0.70

        return output

    def _build_execution_summary(self, state: dict[str, Any]) -> dict[str, Any]:
        return {
            "topic": state.get("topic", ""),
            "has_research": bool(state.get("research_result")),
            "has_pedagogical_structure": bool(state.get("pedagogical_structure")),
            "has_adaptation": bool(state.get("adaptation_plan")),
            "has_evaluation": bool(state.get("evaluation_result")),
            "has_multimodal_plan": bool(state.get("multimodal_plan")),
            "has_prompts": bool(state.get("prompts")),
            "has_consistency_check": bool(state.get("consistency_result")),
            "agent_steps_completed": sum(
                1 for key in [
                    "research_result", "pedagogical_structure", "adaptation_plan",
                    "evaluation_result", "multimodal_plan", "prompts", "consistency_result",
                ] if state.get(key)
            ),
            "total_agent_steps": 8,
        }

    def _build_resolution_reason(self, debate_context: dict[str, Any]) -> str:
        """Human-readable explanation of how the inter-agent conflict was resolved."""
        recommendation = debate_context.get("recommendation", "")
        adaptive = debate_context.get("adaptive_difficulty", "unknown")
        override = debate_context.get("evaluation_override", "unknown")
        conflict = debate_context.get("conflict", False)

        if not conflict:
            return (
                f"Both agents agreed: AdaptiveLearning and EvaluationAgent "
                f"both proposed '{adaptive}'."
            )

        _reasons: dict[str, str] = {
            "retroceder": (
                f"EvaluationAgent detected insufficient mastery (learning_score < 0.40) "
                f"and overrode AdaptiveLearning proposal '{adaptive}' → '{override}' "
                f"to support remediation before advancing."
            ),
            "simplificar": (
                f"EvaluationAgent detected cognitive overload and overrode AdaptiveLearning "
                f"proposal '{adaptive}' → '{override}' to prevent ceiling effect."
            ),
            "cambiar_modalidad": (
                f"EvaluationAgent detected sustained low engagement and overrode "
                f"AdaptiveLearning proposal '{adaptive}' → '{override}' "
                f"to trigger modality change."
            ),
            "reforzar": (
                f"EvaluationAgent detected partial mastery (score in [0.40, 0.65)) "
                f"and overrode AdaptiveLearning proposal '{adaptive}' → '{override}' "
                f"for reinforcement phase."
            ),
            "continuar": (
                f"EvaluationAgent confirmed that the proposed difficulty '{override}' "
                f"is appropriate and recommended continuing without remediation."
            ),
        }
        return _reasons.get(
            recommendation,
            f"EvaluationAgent overrode AdaptiveLearning proposal '{adaptive}' → '{override}' "
            f"(recommendation='{recommendation}').",
        )
