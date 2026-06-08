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

# Default modality priority per pedagogical section type.
# Higher-order Bloom sections (real_case, practical_application) prefer richer modalities.
MODALITY_PRIORITIES: dict[str, list[str]] = {
    "introduction": ["text", "video", "image", "audio"],
    "conceptual_explanation": ["text", "image", "video", "audio"],
    "example": ["text", "image", "video", "interactive"],
    "practical_application": ["interactive", "text", "video"],
    "real_case": ["video", "text", "image", "audio"],
    "evaluation": ["text", "interactive"],
}

# When a section's Bloom level is high (≥ 4), prefer more active/generative modalities.
BLOOM_HIGH_MODALITY_BOOST: dict[str, list[str]] = {
    "conceptual_explanation": ["image", "video", "text", "audio"],
    "example": ["interactive", "image", "video", "text"],
    "practical_application": ["interactive", "video", "text"],
    "real_case": ["video", "image", "text", "audio"],
}


class MultimodalPlanningAgent(BaseAgent):
    """Planifica la estrategia multimodal adaptada al perfil del aprendiz y al nivel Bloom de cada sección.

    Responsabilidades:
    - Decidir qué modalidad usar para cada sección pedagógica
    - Considerar el nivel Bloom de la sección para calibrar la riqueza de la modalidad
    - Incorporar las preferencias del perfil del aprendiz en la selección
    - Construir trazas explicativas de por qué cada modalidad fue elegida
    - Optimizar eficiencia de recursos

    Lee de shared memory:
    - pedagogical:structure (incluye bloom_level por sección)
    - adaptive:plan (incluye modality_preferences, difficulty_level, explanation_depth)

    Escribe en shared memory:
    - multimodal:plan (incluye learner_signals y adaptation_trace por sección)
    """

    @property
    def agent_type(self) -> str:
        return "multimodal_planning"

    async def analyze(self, state: dict[str, Any]) -> dict[str, Any]:
        pedagogical = state.get("pedagogical_structure", {})
        sections = pedagogical.get("sections", []) if isinstance(pedagogical, dict) else []
        adaptation = state.get("adaptation_plan", {}) if isinstance(state.get("adaptation_plan"), dict) else {}

        config_dict = state.get("multimodal_config", {})
        config = MultimodalGenerationConfig(
            **{k: v for k, v in config_dict.items() if hasattr(DEFAULT_MULTIMODAL_CONFIG, k)}
        ) if config_dict else DEFAULT_MULTIMODAL_CONFIG

        modality_prefs = adaptation.get("modality_preferences", [])
        difficulty_level = adaptation.get("difficulty_level", "intermediate")
        explanation_depth = adaptation.get("explanation_depth", "standard")

        decisions = []
        text_sections = []
        prompt_sections = {}

        for section in sections:
            section_type = section.get("section_type", "general")
            bloom_level = int(section.get("bloom_level", 2))
            decision = self._plan_section_modality(
                section_type=section_type,
                section_title=section.get("title", ""),
                bloom_level=bloom_level,
                config=config,
                modality_prefs=modality_prefs,
                difficulty_level=difficulty_level,
                explanation_depth=explanation_depth,
            )
            decisions.append(decision)

            if decision.generate_directly:
                text_sections.append(section_type)
            if decision.generate_prompt and decision.prompt_type:
                prompt_sections[section_type] = decision.prompt_type

        total_decisions = len(decisions)
        prompt_count = sum(1 for d in decisions if d.generate_prompt)
        efficiency_ratio = prompt_count / max(total_decisions, 1)

        adaptation_summary = self._build_adaptation_summary(
            modality_prefs=modality_prefs,
            difficulty_level=difficulty_level,
            explanation_depth=explanation_depth,
            decisions=decisions,
        )

        plan = MultimodalPlan(
            decisions=decisions,
            text_sections=text_sections,
            prompt_sections=prompt_sections,
            efficiency_ratio=round(efficiency_ratio, 2),
            adaptation_summary=adaptation_summary,
            orchestration_metadata={
                "agent": "multimodal_planning",
                "n_sections": total_decisions,
                "n_prompt_sections": prompt_count,
                "learner_prefs_applied": bool(modality_prefs),
                "bloom_aware": True,
            },
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
        bloom_level: int,
        config: MultimodalGenerationConfig,
        modality_prefs: list[str],
        difficulty_level: str,
        explanation_depth: str,
    ) -> ModalityDecision:
        # Higher Bloom levels (≥4: analyze/evaluate/create) benefit from richer modalities.
        if bloom_level >= 4 and section_type in BLOOM_HIGH_MODALITY_BOOST:
            base_priorities = BLOOM_HIGH_MODALITY_BOOST[section_type]
        else:
            base_priorities = MODALITY_PRIORITIES.get(section_type, ["text"])

        learner_signals: list[str] = []

        # Select modality respecting learner preferences
        chosen_modality = "text"
        if modality_prefs:
            for modality in base_priorities:
                if modality in modality_prefs:
                    chosen_modality = modality
                    learner_signals.append(
                        f"learner_prefers_{modality}→selected_over_default"
                    )
                    break
            else:
                # No preference matched — fall to first in priority list
                chosen_modality = base_priorities[0]
                learner_signals.append(
                    f"no_learner_pref_matched_priorities→default_{chosen_modality}"
                )
        else:
            chosen_modality = base_priorities[0]
            learner_signals.append("no_profile_preferences→default_priority_order")

        if bloom_level >= 4:
            learner_signals.append(
                f"bloom_{bloom_level}≥4→richer_modality_priorities_applied"
            )

        if difficulty_level == "beginner" and chosen_modality in ("interactive",):
            learner_signals.append(
                "beginner_difficulty→interactive_modality_still_valid_for_scaffolded_practice"
            )
        elif difficulty_level == "advanced" and chosen_modality == "text":
            learner_signals.append(
                "advanced_difficulty→text_supplemented_with_analytical_prompts"
            )

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

        reason = self._build_modality_reason(
            section_type=section_type,
            modality=chosen_modality,
            bloom_level=bloom_level,
            config=config,
        )
        adaptation_trace = self._build_adaptation_trace(
            section_type=section_type,
            chosen_modality=chosen_modality,
            bloom_level=bloom_level,
            difficulty_level=difficulty_level,
            explanation_depth=explanation_depth,
            modality_prefs=modality_prefs,
            learner_signals=learner_signals,
        )

        return ModalityDecision(
            section=section_type,
            modality=chosen_modality,
            generate_directly=generate_directly,
            generate_prompt=generate_prompt,
            reason=reason,
            prompt_type=prompt_type,
            bloom_level=bloom_level,
            learner_signals=learner_signals,
            adaptation_trace=adaptation_trace,
        )

    def _build_modality_reason(
        self,
        section_type: str,
        modality: str,
        bloom_level: int,
        config: MultimodalGenerationConfig,
    ) -> str:
        bloom_context = {
            1: "nivel recordar (Bloom 1) — refuerzo mnémico",
            2: "nivel comprender (Bloom 2) — construcción de significado",
            3: "nivel aplicar (Bloom 3) — transferencia a contextos",
            4: "nivel analizar (Bloom 4) — descomposición estructural",
            5: "nivel evaluar (Bloom 5) — juicio crítico",
            6: "nivel crear (Bloom 6) — síntesis y producción",
        }.get(bloom_level, f"Bloom {bloom_level}")

        reason_map = {
            "introduction": (
                f"La introducción activa conocimientos previos ({bloom_context}). "
                f"Modalidad '{modality}' orienta al aprendiz hacia el tema con mínima carga cognitiva."
            ),
            "conceptual_explanation": (
                f"La explicación conceptual ({bloom_context}) requiere representación precisa. "
                f"Modalidad '{modality}' soporta la construcción del esquema mental del concepto."
            ),
            "example": (
                f"Los ejemplos ({bloom_context}) anclan el concepto en instancias concretas. "
                f"Modalidad '{modality}' maximiza la transferencia analógica."
            ),
            "practical_application": (
                f"La práctica ({bloom_context}) requiere acción activa del aprendiz. "
                f"Modalidad '{modality}' habilita la aplicación deliberada con retroalimentación."
            ),
            "real_case": (
                f"El caso real ({bloom_context}) conecta teoría con contexto profesional. "
                f"Modalidad '{modality}' maximiza el impacto narrativo y la relevancia percibida."
            ),
            "evaluation": (
                f"La evaluación ({bloom_context}) mide la comprensión alcanzada. "
                f"Modalidad '{modality}' permite verificar desempeño con estructura clara."
            ),
        }
        base = reason_map.get(
            section_type,
            f"Modalidad '{modality}' seleccionada para '{section_type}' ({bloom_context}).",
        )

        if not config.generate_video_directly and modality == "video":
            base += (
                " Video no se genera directamente — se produce prompt cinematográfico "
                "con storyboard pedagógico para sistema generativo especializado."
            )

        return base

    def _build_adaptation_trace(
        self,
        section_type: str,
        chosen_modality: str,
        bloom_level: int,
        difficulty_level: str,
        explanation_depth: str,
        modality_prefs: list[str],
        learner_signals: list[str],
    ) -> str:
        prefs_str = ", ".join(modality_prefs) if modality_prefs else "ninguna (perfil no disponible)"
        signals_str = " | ".join(learner_signals) if learner_signals else "sin señales"
        return (
            f"Sección '{section_type}' → modalidad '{chosen_modality}' | "
            f"Bloom {bloom_level} | dificultad={difficulty_level} | profundidad={explanation_depth} | "
            f"preferencias_aprendiz=[{prefs_str}] | señales=[{signals_str}]"
        )

    def _build_adaptation_summary(
        self,
        modality_prefs: list[str],
        difficulty_level: str,
        explanation_depth: str,
        decisions: list[ModalityDecision],
    ) -> dict[str, Any]:
        modality_counts: dict[str, int] = {}
        bloom_distribution: dict[int, str] = {}
        for d in decisions:
            modality_counts[d.modality] = modality_counts.get(d.modality, 0) + 1
            bloom_distribution[d.bloom_level] = d.section

        return {
            "learner_modality_preferences": modality_prefs or ["visual", "reading"],
            "difficulty_level": difficulty_level,
            "explanation_depth": explanation_depth,
            "modality_distribution": modality_counts,
            "bloom_section_map": bloom_distribution,
            "profile_influenced_decisions": sum(
                1 for d in decisions if any("learner_prefers" in s for s in d.learner_signals)
            ),
            "bloom_aware_decisions": sum(
                1 for d in decisions if any("bloom_" in s for s in d.learner_signals)
            ),
        }
