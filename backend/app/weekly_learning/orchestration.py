"""
WeekOrchestrator — runs the full swarm pipeline for a single week.

Pipeline:
  1. ResearchAgent for pedagogical retrieval
  2. Pedagogical structuring (stages, misconceptions, examples)
  3. Content generation (introduction, explanation, practice)
  4. Multimodal prompt engineering
  5. Consistency validation
  6. Shared memory persistence
  7. Week content creation in DB
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.agents.research_agent import ResearchAgent
from app.memory.narrative_continuity import (
    NARRATIVE_MEMORY_TYPE,
    publish_narrative_persona,
    query_narrative_persona,
)
from app.memory.shared_memory import SharedMemoryStore
from app.models.course import Course
from app.weekly_learning.models import CourseWeek, WeekContent
from app.weekly_learning.progression import BloomProgression

logger = logging.getLogger(__name__)


class WeekOrchestrator:
    """
    Orchestrates a single week's pedagogical content generation.

    Uses the ResearchAgent for retrieval, then enriches with structured
    pedagogical content tailored to the week's Bloom level and theme.
    """

    def __init__(self):
        self.research_agent = ResearchAgent()

    async def orchestrate_week(
        self,
        db: Session,
        course: Course,
        week: CourseWeek,
        memory_store: SharedMemoryStore | None = None,
        student_id: str | None = None,
    ) -> WeekContent:
        logger.info("Orchestrating week %d: %s (Bloom %d)", week.week_number, week.theme, week.bloom_target)

        if memory_store is not None:
            self.research_agent.shared_memory_store = memory_store

            narrative = query_narrative_persona(
                memory_store,
                student_id=student_id,
                module_id=f"{course.id}:week{week.week_number - 1}" if week.week_number > 1 else None,
            )
        else:
            narrative = {}

        research_state = await self.research_agent.run({
            "topic": week.theme,
            "objectives": week.objectives or [f"Comprender {week.theme}"],
            "bloom_target": week.bloom_target,
            "language": "es",
            "module_id": week.id,
            "student_id": student_id or course.teacher_id,
            "narrative_continuity": narrative,
        })

        research = research_state.get("research", {})
        research_metrics = research_state.get("research_metrics", {})
        consistency_validation = research_state.get("consistency_validation", {})

        concepts = research.get("concepts", [])
        misconceptions_raw = research.get("misconceptions", [])
        examples_raw = research.get("examples", [])
        multimodal_prompts_raw = research.get("multimodal_prompts", [])

        week.multimodal_prompts = multimodal_prompts_raw[:4]

        pedagogical_stages = self._build_pedagogical_stages(week)
        introduction = self._generate_introduction(week)
        explanation = self._generate_explanation(week, concepts)
        examples = self._build_examples(examples_raw, week)
        guided_practice = self._generate_guided_practice(week)
        storyboard = self._generate_storyboard(week, pedagogical_stages)
        continuity = self._generate_continuity(week, course)
        retrieval_evidence = self._build_retrieval_evidence(research)
        swarm_trace = {
            "research_metrics": research_metrics,
            "consistency_validation": consistency_validation,
            "memory_ids": research_state.get("memory_ids", []),
            "confidence": research_metrics.get("pedagogical_confidence", 0.0),
        }

        content = WeekContent(
            week_id=week.id,
            introduction=introduction,
            pedagogical_explanation=explanation,
            examples=examples,
            guided_practice=guided_practice,
            storyboard=storyboard,
            continuity_notes=continuity,
            pedagogical_stages=pedagogical_stages,
            retrieval_evidence=retrieval_evidence,
            swarm_trace=swarm_trace,
            memory_ids=research_state.get("memory_ids", []),
        )
        db.add(content)

        confidence = float(research_metrics.get("pedagogical_confidence", 0.0) or 0.0)
        week.orchestration_status = "completed" if confidence >= 0.4 else "completed_with_warnings"
        week.confidence = round(confidence, 4)
        week.generated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(content)

        if memory_store is not None:
            bloom_label = BloomProgression.get_label(week.bloom_target)
            publish_narrative_persona(
                memory_store,
                persona=f"Semana {week.week_number}: {week.theme} (Bloom {week.bloom_target} - {bloom_label})",
                tone="educativo",
                character=None,
                bloom_progress=f"Nivel Bloom {week.bloom_target} alcanzado en semana {week.week_number}",
                student_id=student_id,
                module_id=str(week.id),
                confidence=min(confidence + 0.1, 1.0),
            )

        logger.info("Week %d orchestrated (confidence=%.2f)", week.week_number, confidence)
        return content

    def _build_pedagogical_stages(self, week: CourseWeek) -> list[dict[str, Any]]:
        bloom = week.bloom_target
        return [
            {
                "phase": "activacion",
                "focus": f"Activar conocimientos previos sobre {week.theme}",
                "bloom_level": max(1, bloom - 1),
                "content": f"Reflexiona sobre lo que ya sabes de {week.theme}. ¿Qué conexiones puedes establecer?",
                "examples": [f"Pregunta guía: ¿Qué sabes sobre {week.theme}?"],
            },
            {
                "phase": "exploracion",
                "focus": f"Explorar {week.theme} en profundidad",
                "bloom_level": bloom,
                "content": f"Explora los conceptos clave de {week.theme}. Analiza sus propiedades y aplicaciones.",
                "examples": [f"Ejemplo: Análisis de {week.theme} en diferentes contextos"],
            },
            {
                "phase": "construccion",
                "focus": f"Construir conocimiento aplicado de {week.theme}",
                "bloom_level": min(bloom + 1, 6),
                "content": f"Construye soluciones usando los conceptos de {week.theme}. Practica con ejercicios.",
                "examples": [f"Ejercicio guiado: Aplica {week.theme} en un problema práctico"],
            },
            {
                "phase": "transferencia",
                "focus": f"Transferir {week.theme} a contextos reales",
                "bloom_level": min(bloom + 2, 6),
                "content": f"Aplica {week.theme} para resolver problemas auténticos del mundo real.",
                "examples": [f"Proyecto: Integra {week.theme} en una solución completa"],
            },
        ]

    def _generate_introduction(self, week: CourseWeek) -> str:
        bloom_label = BloomProgression.get_label(week.bloom_target)
        return (
            f"Bienvenido a la Semana {week.week_number}. "
            f"Esta semana exploraremos **{week.theme}**, "
            f"con un enfoque en **{bloom_label}** (Nivel Bloom {week.bloom_target}). "
            f"Los objetivos incluyen: {'; '.join(week.objectives[:3])}. "
            f"Prepárate para construir conocimiento sólido y aplicable."
        )

    def _generate_explanation(self, week: CourseWeek, concepts: list[str]) -> str:
        concept_detail = ". ".join(concepts[:4]) if concepts else week.theme
        bloom_label = BloomProgression.get_label(week.bloom_target)
        verbs = BloomProgression.get_verbs(week.bloom_target)
        verb_list = ", ".join(verbs[:3])
        return (
            f"**{week.theme}** — Semana centrada en **{bloom_label}**. "
            f"{concept_detail}. "
            f"Utilizarás verbos como: {verb_list} para alcanzar los objetivos propuestos. "
            f"Este nivel te permite {' y '.join(verbs[:2])} los conceptos fundamentales."
        )

    def _build_examples(self, raw: list[str], week: CourseWeek) -> list[str]:
        if raw and len(raw) >= 2:
            return raw[:5]
        bloom = week.bloom_target
        verbs = BloomProgression.get_verbs(bloom)
        return [
            f"Ejemplo {i + 1}: {verb.capitalize()} los conceptos de {week.theme} en un contexto guiado."
            for i, verb in enumerate(verbs[:4])
        ]

    def _generate_guided_practice(self, week: CourseWeek) -> str:
        bloom_label = BloomProgression.get_label(week.bloom_target)
        return (
            f"**Práctica guiada — Semana {week.week_number}: {bloom_label}**\n\n"
            f"**Tema:** {week.theme}\n"
            f"**Nivel Bloom:** {week.bloom_target} ({bloom_label})\n\n"
            f"**Instrucciones:**\n"
            f"1. Revisa los conceptos clave presentados en esta semana.\n"
            f"2. Completa los ejercicios propuestos siguiendo la progresión.\n"
            f"3. Reflexiona sobre tus respuestas y verifica tu comprensión.\n"
            f"4. Aplica lo aprendido en el ejercicio de transferencia.\n\n"
            f"**Criterios de evaluación:**\n" +
            "\n".join(f"- {criterio}" for criterio in week.evaluation_criteria[:3]) +
            "\n\n**Recuerda:** El aprendizaje es progresivo. Avanza a tu propio ritmo."
        )

    def _generate_storyboard(self, week: CourseWeek, stages: list[dict[str, Any]]) -> str:
        return (
            f"**Storyboard — Semana {week.week_number}**\n\n"
            + "\n".join(
                f"**Escena {i + 1}: {s['phase'].capitalize()}**\n"
                f"- Enfoque: {s['focus']}\n"
                f"- Bloom: {s['bloom_level']}\n"
                for i, s in enumerate(stages)
            )
            + f"\n**Transiciones:** Cada etapa prepara para la siguiente, construyendo complejidad gradual.\n"
            f"**Duración estimada:** 2-3 sesiones de 45 min."
        )

    def _generate_continuity(self, week: CourseWeek, course: Course) -> str:
        prev_text = f"Se conecta con la semana anterior al profundizar en los conceptos." if week.week_number > 1 else "Sienta las bases para las semanas siguientes."
        next_text = f"Prepara el terreno para la Semana {week.week_number + 1}." if week.week_number < 5 else "Concluye esta etapa del curso."
        return (
            f"**Continuidad pedagógica — Semana {week.week_number}**\n\n"
            f"Curso: {course.name}\n"
            f"Tema: {week.theme}\n\n"
            f"{prev_text}\n"
            f"{next_text}\n\n"
            f"Nivel Bloom: {week.bloom_target} ({BloomProgression.get_label(week.bloom_target)})."
        )

    def _build_retrieval_evidence(self, research: dict[str, Any]) -> dict[str, Any]:
        return {
            "sources_count": len(research.get("sources", [])),
            "confidence": research.get("confidence_score", 0.0),
            "degraded": research.get("degraded", False),
            "sources": [
                {"title": s.get("title", ""), "domain": s.get("domain", ""), "relevance": s.get("relevance", 0.0)}
                for s in research.get("sources", [])[:5]
            ],
        }


week_orchestrator = WeekOrchestrator()
