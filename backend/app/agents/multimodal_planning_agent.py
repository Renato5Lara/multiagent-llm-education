"""MultimodalPlanningAgent — decide qué modalidad usar, qué generar directamente y qué convertir en prompt."""

from __future__ import annotations

import logging
from typing import Any

from app.agents.base import BaseAgent
from app.schemas.pedagogical_orchestration import ModalityDecision, MultimodalPlan
from app.services.multimodal_generation_config import (
    MultimodalGenerationConfig,
    DEFAULT_MULTIMODAL_CONFIG,
)

logger = logging.getLogger(__name__)

MODALITY_PRIORITIES: dict[str, list[str]] = {
    "introduction": ["text", "video", "image", "audio"],
    "conceptual_explanation": ["text", "image", "video", "audio"],
    "example": ["text", "image", "video", "interactive"],
    "practical_application": ["interactive", "text", "video"],
    "real_case": ["video", "text", "image", "audio"],
    "evaluation": ["text", "interactive"],
}


class MultimodalPlanningAgent(BaseAgent):
    """Planifica la estrategia multimodal: decide qué y cómo generar contenido.

    Responsabilidades:
    - Decidir qué modalidad usar para cada sección pedagógica
    - Decidir qué generar directamente (texto)
    - Decidir qué convertir en prompt (imagen, audio, video)
    - Optimizar eficiencia de recursos

    Lee de shared memory:
    - pedagogical:structure
    - adaptive:plan

    Escribe en shared memory:
    - multimodal:plan
    """

    @property
    def agent_type(self) -> str:
        return "multimodal_planning"

    async def analyze(self, state: dict[str, Any]) -> dict[str, Any]:
        pedagogical = state.get("pedagogical_structure", {})
        sections = pedagogical.get("sections", []) if isinstance(pedagogical, dict) else []
        adaptation = state.get("adaptation_plan", {})

        config_dict = state.get("multimodal_config", {})
        config = MultimodalGenerationConfig(
            **{k: v for k, v in config_dict.items() if hasattr(DEFAULT_MULTIMODAL_CONFIG, k)}
        ) if config_dict else DEFAULT_MULTIMODAL_CONFIG

        modality_prefs = adaptation.get("modality_preferences", []) if isinstance(adaptation, dict) else []

        decisions = []
        text_sections = []
        prompt_sections = {}

        for section in sections:
            section_type = section.get("section_type", "general")
            decision = self._plan_section_modality(
                section_type=section_type,
                section_title=section.get("title", ""),
                config=config,
                modality_prefs=modality_prefs,
            )
            decisions.append(decision)

            if decision.generate_directly:
                text_sections.append(section.get("section_type", "unknown"))
            if decision.generate_prompt and decision.prompt_type:
                prompt_sections[section.get("section_type", "unknown")] = decision.prompt_type

        total_decisions = len(decisions)
        prompt_count = sum(1 for d in decisions if d.generate_prompt)
        efficiency_ratio = prompt_count / max(total_decisions, 1)

        plan = MultimodalPlan(
            decisions=decisions,
            text_sections=text_sections,
            prompt_sections=prompt_sections,
            efficiency_ratio=round(efficiency_ratio, 2),
        )

        result = plan.model_dump()

        await self.publish_observation(
            f"{self.context_key}:multimodal:plan",
            result,
            memory_type="inference",
            confidence=0.9,
        )

        return result

    def _plan_section_modality(
        self,
        section_type: str,
        section_title: str,
        config: MultimodalGenerationConfig,
        modality_prefs: list[str],
    ) -> ModalityDecision:
        priorities = MODALITY_PRIORITIES.get(section_type, ["text"])

        chosen_modality = "text"
        for modality in priorities:
            if not modality_prefs or modality in modality_prefs:
                chosen_modality = modality
                break

        generate_directly = False
        generate_prompt = True
        prompt_type = None

        if chosen_modality == "text" and config.generate_text_directly:
            generate_directly = True
            generate_prompt = False
        elif chosen_modality == "image":
            if config.generate_image_directly:
                generate_directly = True
            if config.generate_image_prompt:
                generate_prompt = True
                prompt_type = "visual"
        elif chosen_modality == "video":
            if config.generate_video_directly:
                generate_directly = True
            if config.generate_video_prompt:
                generate_prompt = True
                prompt_type = "cinematic"
        elif chosen_modality == "audio":
            if config.generate_audio_directly:
                generate_directly = True
            if config.generate_audio_prompt:
                generate_prompt = True
                prompt_type = "audio"
        elif chosen_modality == "interactive":
            generate_prompt = True
            prompt_type = "interactive"

        reason = self._build_modality_reason(section_type, chosen_modality, config)

        return ModalityDecision(
            section=section_type,
            modality=chosen_modality,
            generate_directly=generate_directly,
            generate_prompt=generate_prompt,
            reason=reason,
            prompt_type=prompt_type,
        )

    def _build_modality_reason(self, section_type: str, modality: str, config: MultimodalGenerationConfig) -> str:
        reason_map = {
            "introduction": "La introducción se beneficia de contenido textual directo y apoyo visual.",
            "conceptual_explanation": "La explicación conceptual requiere texto estructurado con apoyos visuales.",
            "example": "Los ejemplos se ilustran mejor con imágenes o diagramas.",
            "practical_application": "La aplicación práctica funciona bien en formato interactivo o textual.",
            "real_case": "Los casos reales tienen mayor impacto con narrativa visual o video.",
            "evaluation": "La evaluación se entrega eficientemente en formato textual interactivo.",
        }
        base = reason_map.get(section_type, f"Modalidad {modality} para sección {section_type}.")

        if not config.generate_video_directly and modality == "video":
            base += " En lugar de video, se genera prompt cinematográfico + storyboard + narrativa."

        return base
