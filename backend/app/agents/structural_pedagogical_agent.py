"""StructuralPedagogicalAgent — estructura el aprendizaje en secciones pedagógicas con progresión Bloom."""

from __future__ import annotations

import logging
from typing import Any

from app.agents.base import BaseAgent
from app.schemas.pedagogical_orchestration import (
    PedagogicalSection,
    SectionPlan,
    PedagogicalStructure,
)

logger = logging.getLogger(__name__)


class StructuralPedagogicalAgent(BaseAgent):
    """Estructura pedagógicamente el contenido en 6 secciones con progresión taxonómica.

    Responsabilidades:
    - Estructurar aprendizaje en introducción, explicación, ejemplo, práctica, caso real, evaluación
    - Definir progresión basada en Taxonomía de Bloom
    - Alinear objetivos con secciones
    - Calcular duración estimada por sección

    Lee de shared memory:
    - research:findings

    Escribe en shared memory:
    - pedagogical:structure
    - pedagogical:sections
    """

    @property
    def agent_type(self) -> str:
        return "structural_pedagogical"

    async def analyze(self, state: dict[str, Any]) -> dict[str, Any]:
        topic = state.get("topic", "")
        objectives = state.get("learning_objectives", [])
        research = state.get("research_result", {})
        findings = research.get("findings", []) if isinstance(research, dict) else []
        examples = research.get("examples", []) if isinstance(research, dict) else []

        sections = self._build_pedagogical_sections(topic, objectives, findings, examples)
        structure = PedagogicalStructure(
            topic=topic,
            sections=sections,
            progression_logic=self._build_progression_logic(objectives, sections),
            total_duration_minutes=sum(s.estimated_duration_minutes for s in sections),
            recommended_prerequisites=self._infer_prerequisites(topic, objectives),
        )

        result = structure.model_dump()

        await self.publish_observation(
            f"{self.context_key}:pedagogical:structure",
            result,
            memory_type="inference",
            confidence=0.9,
        )

        for section in sections:
            await self.publish_observation(
                f"{self.context_key}:pedagogical:section:{section.section_type.value}",
                section.model_dump(),
                memory_type="observation",
                confidence=0.85,
            )

        return result

    def _build_pedagogical_sections(
        self,
        topic: str,
        objectives: list[str],
        findings: list[dict],
        examples: list[str],
    ) -> list[SectionPlan]:
        sections = []

        sections.append(SectionPlan(
            section_type=PedagogicalSection.INTRODUCTION,
            title=f"Introducción a {topic}",
            description=(
                f"Presentación del tema '{topic}'. Contextualización, "
                f"activación de conocimientos previos y planteamiento de objetivos."
            ),
            estimated_duration_minutes=8,
            bloom_level=1,
            modality="text",
        ))

        sections.append(SectionPlan(
            section_type=PedagogicalSection.CONCEPTUAL_EXPLANATION,
            title=f"Fundamentos de {topic}",
            description=(
                f"Explicación detallada de los conceptos fundamentales de '{topic}'. "
                f"Definiciones, principios y marco teórico."
            ),
            estimated_duration_minutes=15,
            bloom_level=2,
            modality="text",
        ))

        sections.append(SectionPlan(
            section_type=PedagogicalSection.EXAMPLE,
            title=f"Ejemplos de {topic}",
            description=(
                f"Ejemplos prácticos y resueltos que ilustran la aplicación de '{topic}'."
            ),
            estimated_duration_minutes=12,
            bloom_level=3,
            modality="text",
        ))

        sections.append(SectionPlan(
            section_type=PedagogicalSection.PRACTICAL_APPLICATION,
            title=f"Aplicación práctica de {topic}",
            description=(
                f"Ejercicios y actividades para aplicar los conceptos de '{topic}' "
                f"en contextos controlados."
            ),
            estimated_duration_minutes=15,
            bloom_level=3,
            modality="text",
        ))

        sections.append(SectionPlan(
            section_type=PedagogicalSection.REAL_CASE,
            title=f"Caso real: {topic} en acción",
            description=(
                f"Análisis de un caso real donde se aplica '{topic}', "
                f"mostrando impacto y resultados concretos."
            ),
            estimated_duration_minutes=10,
            bloom_level=4,
            modality="text",
        ))

        sections.append(SectionPlan(
            section_type=PedagogicalSection.EVALUATION,
            title=f"Evaluación de {topic}",
            description=(
                f"Preguntas y actividades de evaluación para verificar "
                f"la comprensión de '{topic}'."
            ),
            estimated_duration_minutes=10,
            bloom_level=4,
            modality="text",
        ))

        return sections

    def _build_progression_logic(self, objectives: list[str], sections: list[SectionPlan]) -> str:
        bloom_levels = [s.bloom_level for s in sections]
        progression = " → ".join(
            f"{s.section_type.value}(Bloom {s.bloom_level})" for s in sections
        )
        return (
            f"Progresión pedagógica basada en Taxonomía de Bloom: {progression}. "
            f"Se avanza desde recordar/comprender hasta aplicar/analizar. "
            f"Alineado con {len(objectives)} objetivos de aprendizaje."
        )

    def _infer_prerequisites(self, topic: str, objectives: list[str]) -> list[str]:
        prereqs = []
        for obj in objectives:
            if any(word in obj.lower() for word in ["fundamentos", "básico", "introducción"]):
                continue
        prereqs.append(f"Conceptos básicos relacionados con {topic}")
        return prereqs
