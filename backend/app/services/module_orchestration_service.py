"""
Module Orchestration Service.

Runs the full pedagogical pipeline for a student module:
  narrative-query → research → content-generation → narrative-publish

Design constraints:
  - No shared mutable state across concurrent requests.  The service singleton
    holds no per-request state; every call creates its own ResearchAgent so
    concurrent requests cannot corrupt each other's memory-store reference.
  - All I/O phases are individually timed and guarded; any phase failure
    degrades gracefully (template fallback) rather than crashing the request.
  - An overall per-call timeout prevents runaway requests from holding DB
    connections indefinitely.
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.agents.research_agent import ResearchAgent
from app.memory.narrative_continuity import (
    publish_narrative_persona,
    query_narrative_persona,
)
from app.memory.shared_memory import SharedMemoryStore
from app.models.course import Course
from app.models.student_progress import PathModule
from app.models.user import User

logger = logging.getLogger(__name__)

BLOOM_LABELS = {
    1: "Recordar",
    2: "Comprender",
    3: "Aplicar",
    4: "Analizar",
    5: "Evaluar",
    6: "Crear",
}

# Maximum time (seconds) for the entire orchestration.  If exceeded the
# pipeline returns a gracefully-degraded result rather than a 500.
_ORCHESTRATE_TIMEOUT_S = 60.0
# Timeout for the research-agent phase alone (Tavily + async gather).
_RESEARCH_TIMEOUT_S = 28.0


class ModuleOrchestrationService:
    """Stateless coordinator — safe to use as a module-level singleton.

    No per-request state is stored on ``self``.  Each call to
    ``orchestrate_module`` creates its own ``ResearchAgent`` instance so that
    concurrent requests never share a memory-store reference.
    """

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def orchestrate_module(
        self,
        db: Session,
        student: User,
        course: Course,
        module: PathModule,
        memory_store: SharedMemoryStore | None = None,
        request_id: str | None = None,
    ) -> dict[str, Any]:
        """Run the full module orchestration pipeline.

        Returns a dict that validates against ``ModuleOrchestrationResponse``.
        Never raises — on unrecoverable failure it returns a deterministic
        degraded result so the frontend can render something useful.
        """
        orch_id = (request_id or str(uuid.uuid4()))[:16]

        try:
            return await asyncio.wait_for(
                self._orchestrate_impl(orch_id, db, student, course, module, memory_store),
                timeout=_ORCHESTRATE_TIMEOUT_S,
            )
        except asyncio.TimeoutError:
            logger.error(
                "orchestrate[%s]: overall timeout exceeded (%.0fs) — "
                "returning degraded result. module=%s student=%s",
                orch_id, _ORCHESTRATE_TIMEOUT_S, module.id[:8], student.id[:8],
            )
            return self._degraded_result(module, course, orch_id, reason="timeout")
        except Exception as exc:
            logger.error(
                "orchestrate[%s]: unhandled exception — returning degraded result. "
                "module=%s student=%s error=%r",
                orch_id, module.id[:8], student.id[:8], exc,
                exc_info=True,
            )
            return self._degraded_result(module, course, orch_id, reason=str(exc))

    # ------------------------------------------------------------------
    # Implementation
    # ------------------------------------------------------------------

    async def _orchestrate_impl(
        self,
        orch_id: str,
        db: Session,
        student: User,
        course: Course,
        module: PathModule,
        memory_store: SharedMemoryStore | None,
    ) -> dict[str, Any]:
        topic = module.title
        bloom_target = module.bloom_level or 3
        t0 = time.monotonic()

        logger.info(
            "orchestrate[%s]: start — module=%s topic=%r bloom=%d student=%s course=%s",
            orch_id, module.id[:8], topic[:40], bloom_target,
            student.id[:8], course.id[:8],
        )

        # ── Phase 1: Narrative query (reads prior session context) ───────
        narrative = self._phase_narrative_query(orch_id, memory_store, student, course)

        # ── Phase 2: Research (Tavily retrieval, degraded if no API key) ─
        research_state = await self._phase_research(
            orch_id, topic, bloom_target, student, module, narrative,
            memory_store=memory_store,
        )

        # ── Phase 3: Content generation (CPU-only, no I/O) ───────────────
        t_content = time.monotonic()
        result = self._build_orchestration_result(
            research_state, student, course, module, bloom_target, orch_id,
        )
        logger.debug(
            "orchestrate[%s]: content_build done (%.0fms)",
            orch_id, (time.monotonic() - t_content) * 1000,
        )

        # ── Phase 4: Narrative publish (writes session context for future) ─
        self._phase_narrative_publish(orch_id, memory_store, student, module, course, result)

        elapsed_ms = (time.monotonic() - t0) * 1000
        logger.info(
            "orchestrate[%s]: complete in %.0fms — "
            "status=%s confidence=%.3f module=%s",
            orch_id, elapsed_ms,
            result.get("orchestration_status", "?"),
            result.get("confidence", 0.0),
            module.id[:8],
        )
        return result

    # ------------------------------------------------------------------
    # Phases
    # ------------------------------------------------------------------

    def _phase_narrative_query(
        self,
        orch_id: str,
        memory_store: SharedMemoryStore | None,
        student: User,
        course: Course,
    ) -> dict[str, Any]:
        if memory_store is None:
            return {}
        t = time.monotonic()
        try:
            narrative = query_narrative_persona(
                memory_store,
                student_id=student.id,
                course_id=course.id,
            )
            logger.debug(
                "orchestrate[%s]: narrative_query done (%.0fms keys=%d)",
                orch_id, (time.monotonic() - t) * 1000, len(narrative),
            )
            return narrative
        except Exception as exc:
            logger.warning(
                "orchestrate[%s]: narrative_query failed (non-critical): %s",
                orch_id, exc, exc_info=True,
            )
            return {}

    async def _phase_research(
        self,
        orch_id: str,
        topic: str,
        bloom_target: int,
        student: User,
        module: PathModule,
        narrative: dict[str, Any],
        memory_store: SharedMemoryStore | None,
    ) -> dict[str, Any]:
        # Create a fresh ResearchAgent per call — never reuse the singleton's
        # agent so concurrent requests cannot overwrite each other's
        # shared_memory_store reference.
        research_agent = ResearchAgent(shared_memory_store=memory_store)

        t = time.monotonic()
        try:
            state = await asyncio.wait_for(
                research_agent.run({
                    "topic": topic,
                    "objectives": [f"Comprender y aplicar {topic.lower()}"],
                    "bloom_target": bloom_target,
                    "language": "es",
                    "student_id": student.id,
                    "module_id": module.id,
                    "narrative_continuity": narrative,
                }),
                timeout=_RESEARCH_TIMEOUT_S,
            )
            logger.info(
                "orchestrate[%s]: research done (%.0fms degraded=%s sources=%d)",
                orch_id, (time.monotonic() - t) * 1000,
                state.get("research", {}).get("degraded", True),
                state.get("research", {}).get("total_sources", 0),
            )
            return state
        except asyncio.TimeoutError:
            logger.warning(
                "orchestrate[%s]: research timed out after %.0fs — using empty state",
                orch_id, _RESEARCH_TIMEOUT_S,
            )
        except asyncio.CancelledError:
            logger.warning("orchestrate[%s]: research cancelled", orch_id)
            raise
        except Exception as exc:
            logger.warning(
                "orchestrate[%s]: research failed (%.0fms) — using empty state. error=%r",
                orch_id, (time.monotonic() - t) * 1000, exc, exc_info=True,
            )
        return {"research": {}, "research_metrics": {}, "consistency_validation": {}}

    def _phase_narrative_publish(
        self,
        orch_id: str,
        memory_store: SharedMemoryStore | None,
        student: User,
        module: PathModule,
        course: Course,
        result: dict[str, Any],
    ) -> None:
        if memory_store is None:
            return
        t = time.monotonic()
        try:
            bloom_target = int(result.get("bloom_progression", [{}])[0].get("level", 1)) if result.get("bloom_progression") else (module.bloom_level or 3)
            bloom_label = BLOOM_LABELS.get(module.bloom_level or 3, "Aplicar")
            confidence = float(result.get("confidence", 0.0))
            publish_narrative_persona(
                memory_store,
                persona=f"Módulo {module.title} — Bloom {module.bloom_level or 3} ({bloom_label}) — Curso {course.name}",
                tone="educativo",
                bloom_progress=f"Nivel Bloom {module.bloom_level or 3} trabajado en módulo {module.title}",
                student_id=student.id,
                module_id=module.id,
                confidence=min(confidence + 0.1, 1.0),
            )
            logger.debug(
                "orchestrate[%s]: narrative_publish done (%.0fms)",
                orch_id, (time.monotonic() - t) * 1000,
            )
        except Exception as exc:
            logger.warning(
                "orchestrate[%s]: narrative_publish failed (non-critical): %s",
                orch_id, exc, exc_info=True,
            )

    # ------------------------------------------------------------------
    # Content builders (pure functions — no I/O, no shared state)
    # ------------------------------------------------------------------

    def _build_orchestration_result(
        self,
        research_state: dict[str, Any],
        student: User,
        course: Course,
        module: PathModule,
        bloom_target: int,
        orch_id: str,
    ) -> dict[str, Any]:
        research = research_state.get("research", {})
        research_metrics = research_state.get("research_metrics", {})
        consistency = research_state.get("consistency_validation", {})

        concepts = [
            c.get("concept") or c.get("title") or ""
            for c in research.get("concepts", [])
            if isinstance(c, dict)
        ]
        concepts = [c for c in concepts if c]

        raw_sources = research.get("sources", [])
        misconceptions_raw = research.get("misconceptions", [])
        examples_raw = research.get("examples", [])
        multimodal_prompts_raw = research.get("multimodal_prompts", [])
        applications_raw = research.get("real_applications", [])

        pedagogical_stages = self._build_pedagogical_stages(module.title, bloom_target, concepts)
        introduction = self._generate_introduction(module.title, concepts)
        explanation = self._generate_explanation(module.title, concepts, bloom_target)
        misconceptions = self._build_misconceptions(misconceptions_raw, module.title)
        examples = self._build_examples(examples_raw, module.title, bloom_target)
        applications = self._build_real_applications(applications_raw, module.title)
        guided_practice = self._generate_guided_practice(module.title, bloom_target)
        multimodal_prompts = self._build_multimodal_prompts(multimodal_prompts_raw, module.title)
        storyboard = self._generate_storyboard(module.title, pedagogical_stages)
        continuity = self._generate_continuity_notes(module.title, module, course)
        bloom_progression = self._build_bloom_progression(module.title)
        retrieval_evidence = self._build_retrieval_evidence(research)

        confidence = float(research_metrics.get("pedagogical_confidence", 0.0) or 0.0)
        valid = consistency.get("valid", False)
        orchestration_status = "approved" if valid and confidence >= 0.5 else "generated_with_warnings"

        return {
            "module_id": str(module.id),
            "module_title": module.title,
            "course_id": str(course.id),
            "course_name": course.name,
            "orchestration_status": orchestration_status,
            "introduction": introduction,
            "pedagogical_explanation": explanation,
            "misconceptions": misconceptions,
            "examples": examples,
            "real_applications": applications,
            "guided_practice": guided_practice,
            "pedagogical_stages": pedagogical_stages,
            "multimodal_prompts": multimodal_prompts,
            "storyboard": storyboard,
            "continuity_notes": continuity,
            "bloom_progression": bloom_progression,
            "retrieval_evidence": retrieval_evidence,
            "confidence": round(confidence, 4),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    def _degraded_result(
        self,
        module: PathModule,
        course: Course,
        orch_id: str,
        reason: str = "error",
    ) -> dict[str, Any]:
        """Minimal valid result returned when the pipeline fails completely."""
        topic = module.title
        bloom_target = module.bloom_level or 3
        return {
            "module_id": str(module.id),
            "module_title": topic,
            "course_id": str(course.id),
            "course_name": course.name,
            "orchestration_status": "degraded",
            "introduction": self._generate_introduction(topic, []),
            "pedagogical_explanation": self._generate_explanation(topic, [], bloom_target),
            "misconceptions": self._build_misconceptions([], topic),
            "examples": self._build_examples([], topic, bloom_target),
            "real_applications": self._build_real_applications([], topic),
            "guided_practice": self._generate_guided_practice(topic, bloom_target),
            "pedagogical_stages": self._build_pedagogical_stages(topic, bloom_target, []),
            "multimodal_prompts": self._build_multimodal_prompts([], topic),
            "storyboard": self._generate_storyboard(topic, []),
            "continuity_notes": self._generate_continuity_notes(topic, module, course),
            "bloom_progression": self._build_bloom_progression(topic),
            "retrieval_evidence": {"sources_count": 0, "confidence": 0.0, "degraded": True, "sources": []},
            "confidence": 0.0,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    # ------------------------------------------------------------------
    # Template builders (unchanged from original)
    # ------------------------------------------------------------------

    def _build_pedagogical_stages(
        self, topic: str, bloom_target: int, concepts: list[str]
    ) -> list[dict[str, Any]]:
        return [
            {
                "phase": "activacion",
                "focus": f"Activar conocimientos previos sobre {topic.lower()}",
                "bloom_level": 1,
                "content": (
                    f"Antes de abordar {topic.lower()}, reflexiona sobre lo que ya sabes. "
                    f"¿Has usado estructuras similares en otros contextos? "
                    f"Identifica qué conceptos previos (variables, tipos de datos, sintaxis básica) "
                    f"son necesarios para construir nuevo conocimiento."
                ),
                "examples": [
                    f"Pregunta guía: ¿Qué problemas cotidianos podrían resolverse organizando datos en {topic.lower()}?",
                    "Relaciona con conceptos previos de tu experiencia de programación básica.",
                ],
            },
            {
                "phase": "exploracion",
                "focus": f"Explorar {topic.lower()} desde múltiples fuentes",
                "bloom_level": 2,
                "content": (
                    f"Explora cómo se define y utiliza {topic.lower()} en diferentes contextos. "
                    f"Analiza sus propiedades fundamentales: declaración, inicialización, acceso, "
                    f"y operaciones básicas. Compara distintas formas de implementación."
                ),
                "examples": self._concepts_to_strings(concepts[:3]) or [
                    f"Concepto clave 1 de {topic.lower()}",
                    f"Concepto clave 2 de {topic.lower()}",
                ],
            },
            {
                "phase": "construccion",
                "focus": f"Construir soluciones usando {topic.lower()}",
                "bloom_level": min(bloom_target, 4),
                "content": (
                    f"Construye programas que utilicen {topic.lower()} para resolver problemas "
                    f"específicos. Aplica las operaciones de recorrido, búsqueda y modificación. "
                    f"Implementa algoritmos que aprovechen las ventajas de esta estructura."
                ),
                "examples": [
                    f"Ejercicio guiado: Crea un programa que use {topic.lower()} para almacenar y procesar datos.",
                    "Prueba diferentes enfoques y observa los resultados.",
                ],
            },
            {
                "phase": "transferencia",
                "focus": f"Aplicar {topic.lower()} en contextos reales",
                "bloom_level": min(bloom_target + 1, 6),
                "content": (
                    f"Aplica {topic.lower()} para resolver problemas del mundo real. "
                    f"Integra este conocimiento con otras estructuras de datos y patrones "
                    f"de diseño. Evalúa cuándo es la mejor opción y por qué."
                ),
                "examples": [
                    "Proyecto práctico: Implementa una solución completa usando esta estructura.",
                    "Reflexiona sobre las decisiones de diseño y su impacto en el rendimiento.",
                ],
            },
        ]

    def _generate_introduction(self, topic: str, concepts: list[str]) -> str:
        concept_list = ", ".join(self._concepts_to_strings(concepts[:3])) if concepts else topic.lower()
        concept_list = concept_list or topic.lower()
        return (
            f"Bienvenido al módulo de **{topic}**. Este tema es fundamental en la programación "
            f"porque te permite organizar y manipular datos de manera eficiente. "
            f"A lo largo de este módulo, explorarás conceptos como {concept_list}, "
            f"desarrollarás habilidades prácticas para implementar soluciones, "
            f"y comprenderás cómo aplicar estos conocimientos en problemas reales de ingeniería. "
            f"Prepárate para construir una base sólida que te acompañará en tu desarrollo profesional."
        )

    def _concepts_to_strings(self, raw: list) -> list[str]:
        """Extract a plain string from each concept item, whether str or dict."""
        result = []
        for item in raw:
            if isinstance(item, str) and item:
                result.append(item)
            elif isinstance(item, dict):
                text = (
                    item.get("concept")
                    or item.get("content_preview")
                    or item.get("title")
                    or item.get("name")
                    or item.get("example")
                    or item.get("text")
                    or ""
                )
                if text:
                    result.append(str(text))
        return result

    def _generate_explanation(self, topic: str, concepts: list[str], bloom_target: int) -> str:
        concept_strings = self._concepts_to_strings(concepts[:4]) if concepts else []
        concept_detail = ". ".join(
            f"{c}: aspecto clave para dominar {topic.lower()}" for c in concept_strings
        ) if concept_strings else (
            f"{topic} son una estructura de datos que permite almacenar "
            f"múltiples valores relacionados bajo un mismo nombre."
        )
        return (
            f"**{topic}** son una estructura de datos fundamental que permite almacenar "
            f"múltiples elementos del mismo tipo en posiciones contiguas de memoria. "
            f"{concept_detail}. "
            f"Dominarás la declaración, inicialización, recorrido, y operaciones comunes. "
            f"A nivel Bloom {bloom_target} ({BLOOM_LABELS.get(bloom_target, 'Aplicar')}), "
            f"podrás no solo comprender sino también aplicar y analizar "
            f"soluciones que utilicen esta estructura de manera óptima."
        )

    def _build_misconceptions(
        self, raw: list[dict[str, Any]], topic: str
    ) -> list[dict[str, str]]:
        if raw and len(raw) >= 2:
            return [
                {
                    "misconception": str(item.get("misconception") or f"Error conceptual sobre {topic.lower()}"),
                    "correction": str(item.get("correction") or "La forma correcta de entenderlo es..."),
                    "severity": str(item.get("severity") or "medium"),
                }
                for item in raw[:4]
                if isinstance(item, dict)
            ]
        return [
            {
                "misconception": f"Creer que {topic.lower()} solo sirve para datos simples",
                "correction": f"{topic} pueden almacenar cualquier tipo de dato y son la base de estructuras más complejas",
                "severity": "high",
            },
            {
                "misconception": f"Confundir el índice con el valor almacenado",
                "correction": "El índice es la posición (0-based), el valor es el dato en esa posición",
                "severity": "high",
            },
            {
                "misconception": "Pensar que el tamaño es dinámico sin costo",
                "correction": "En muchos lenguajes, los arreglos tienen tamaño fijo; para dinamismo se usan listas",
                "severity": "medium",
            },
        ]

    def _build_examples(self, raw: list, topic: str, bloom_target: int) -> list[str]:
        safe = self._concepts_to_strings(raw)
        if safe and len(safe) >= 2:
            return safe[:5]
        return [
            f"Ejemplo 1 (Recordar): Declara un {topic.lower()} de 5 enteros e imprime cada elemento.",
            f"Ejemplo 2 (Comprender): Explica qué hace el siguiente código que recorre un {topic.lower()}.",
            f"Ejemplo 3 (Aplicar): Escribe una función que busque el valor máximo en un {topic.lower()}.",
            f"Ejemplo 4 (Analizar): Compara el rendimiento de búsqueda en {topic.lower()} ordenado vs no ordenado.",
            f"Ejemplo 5 (Evaluar): Dado un problema, determina si {topic.lower()} es la estructura adecuada.",
        ]

    def _build_real_applications(self, raw: list, topic: str) -> list[str]:
        safe = self._concepts_to_strings(raw)
        if safe and len(safe) >= 2:
            return safe[:4]
        return [
            f"Procesamiento de imágenes: las imágenes digitales son {topic.lower()} bidimensionales de píxeles",
            f"Sistemas de notas: almacenar calificaciones de estudiantes en un {topic.lower()} para calcular promedios",
            f"Colas de procesos: el sistema operativo usa {topic.lower()} para gestionar procesos en memoria",
            f"Gráficos por computadora: las coordenadas de vértices se almacenan en {topic.lower()} para renderizado",
        ]

    def _generate_guided_practice(self, topic: str, bloom_target: int) -> str:
        return (
            f"**Práctica guiada: Explorando {topic}**\n\n"
            f"**Objetivo:** Aplicar los conceptos de {topic.lower()} en un ejercicio práctico.\n\n"
            f"**Instrucciones:**\n"
            f"1. Declara un {topic.lower()} con 10 elementos del tipo de tu elección.\n"
            f"2. Inicializa los elementos con valores de entrada del usuario.\n"
            f"3. Implementa una función que recorra el {topic.lower()} y calcule:\n"
            f"   a) La suma total de elementos\n"
            f"   b) El valor promedio\n"
            f"   c) El valor máximo y mínimo\n"
            f"4. Modifica el programa para que ordene el {topic.lower()} usando un algoritmo simple.\n"
            f"5. **Desafío:** Implementa una búsqueda binaria si el {topic.lower()} está ordenado.\n\n"
            f"**Preguntas de reflexión:**\n"
            f"- ¿Qué complejidad temporal tiene cada operación?\n"
            f"- ¿Cómo cambiaría tu solución si el {topic.lower()} fuera de tamaño dinámico?\n"
            f"- ¿Qué ventajas tiene {topic.lower()} frente a otras estructuras de datos?"
        )

    def _build_multimodal_prompts(
        self, raw: list[dict[str, str]], topic: str
    ) -> list[dict[str, Any]]:
        if isinstance(raw, list) and len(raw) >= 3:
            safe = []
            for p in raw[:4]:
                if isinstance(p, dict):
                    safe.append({
                        "modality": str(p.get("modality") or "text"),
                        "prompt": str(p.get("prompt") or ""),
                        "enabled": bool(p.get("enabled", True)),
                    })
            if len(safe) >= 3:
                return safe
        return [
            {
                "modality": "image",
                "prompt": (
                    f"Diagrama visual que muestre cómo se almacenan los elementos de un {topic.lower()} "
                    f"en memoria contigua, con índices etiquetados del 0 al n-1. "
                    f"Incluye una representación gráfica de la diferencia entre índice y valor. "
                    f"Estilo: diagrama educativo claro con colores distintivos para cada elemento."
                ),
                "enabled": True,
            },
            {
                "modality": "video",
                "prompt": (
                    f"Video explicativo de 5 minutos sobre {topic.lower()} en programación. "
                    f"Incluye: definición, declaración en código, recorrido con bucles, "
                    f"y ejemplos visuales animados de cómo se accede a cada posición. "
                    f"Narrativa clara con ejemplos prácticos de código en pantalla. "
                    f"Público: estudiantes de primer año de ingeniería."
                ),
                "enabled": True,
            },
            {
                "modality": "audio",
                "prompt": (
                    f"Podcast educativo de 8 minutos explicando {topic.lower()} en programación. "
                    f"Estilo conversacional: introduce el concepto, explica por qué es útil, "
                    f"describe operaciones comunes (recorrido, búsqueda, ordenamiento), "
                    f"y menciona aplicaciones reales. Incluye analogías cotidianas para facilitar "
                    f"la comprensión. Ideal para aprendizaje auditivo."
                ),
                "enabled": True,
            },
        ]

    def _generate_storyboard(self, topic: str, stages: list[dict[str, Any]]) -> str:
        stage_narratives = []
        for i, stage in enumerate(stages):
            stage_narratives.append(
                f"**Escena {i + 1}: {stage.get('phase', '').capitalize()}**\n"
                f"- Objetivo: {stage.get('focus', '')}\n"
                f"- Nivel Bloom: {stage.get('bloom_level', '')}\n"
            )
        return (
            f"**Storyboard Pedagógico: {topic}**\n\n"
            f"{chr(10).join(stage_narratives)}\n"
            f"**Transiciones:**\n"
            f"- De activación a exploración: conectar saberes previos con nuevo contenido\n"
            f"- De exploración a construcción: pasar de teoría a práctica guiada\n"
            f"- De construcción a transferencia: aplicar en contexto auténtico\n\n"
            f"**Duración estimada:** 2-3 sesiones de 45 minutos cada una."
        )

    def _generate_continuity_notes(
        self, topic: str, module: PathModule, course: Course
    ) -> str:
        return (
            f"**Notas de continuidad pedagógica**\n\n"
            f"Este módulo de **{topic}** forma parte del curso **{course.name}**. "
            f"Se conecta con módulos anteriores al requerir conceptos de variables y tipos de datos, "
            f"y sienta las bases para módulos posteriores sobre estructuras de datos más complejas "
            f"(listas enlazadas, pilas, colas, árboles).\n\n"
            f"**Prerrequisitos:**\n"
            f"- Variables y tipos de datos básicos\n"
            f"- Estructuras de control (if, for, while)\n"
            f"- Funciones básicas\n\n"
            f"**Conexión futura:**\n"
            f"- Los {topic.lower()} son la base para comprender la gestión de memoria\n"
            f"- Preparan el terreno para estructuras dinámicas y TADs\n"
            f"- Son esenciales para algoritmos de ordenamiento y búsqueda avanzados"
        )

    def _build_bloom_progression(self, topic: str) -> list[dict[str, Any]]:
        return [
            {"level": 1, "label": "Recordar", "description": f"Identificar y definir {topic.lower()}", "mastered": False},
            {"level": 2, "label": "Comprender", "description": f"Explicar cómo funcionan {topic.lower()}", "mastered": False},
            {"level": 3, "label": "Aplicar", "description": f"Implementar programas que usen {topic.lower()}", "mastered": False},
            {"level": 4, "label": "Analizar", "description": f"Comparar eficiencia y casos de uso de {topic.lower()}", "mastered": False},
            {"level": 5, "label": "Evaluar", "description": "Seleccionar la mejor estructura para un problema dado", "mastered": False},
            {"level": 6, "label": "Crear", "description": f"Diseñar soluciones novedosas usando {topic.lower()}", "mastered": False},
        ]

    def _build_retrieval_evidence(self, research: dict[str, Any]) -> dict[str, Any]:
        sources = research.get("sources", [])
        return {
            "sources_count": len(sources),
            "confidence": float(research.get("confidence_score", 0.0) or 0.0),
            "degraded": bool(research.get("degraded", True)),
            "sources": [
                {
                    "title": str(s.get("title") or ""),
                    "domain": str(s.get("domain") or ""),
                    "relevance": float(s.get("score") or s.get("relevance") or 0.0),
                }
                for s in sources[:5]
                if isinstance(s, dict)
            ],
        }


# Module-level singleton — holds NO per-request mutable state.
module_orchestration_service = ModuleOrchestrationService()
