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
import re
import time
import unicodedata
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.core.config import settings
from app.llm.config import LLMConfig
from app.llm.service import LLMService

from app.agents.research_agent import ResearchAgent
from app.memory.narrative_continuity import (
    publish_narrative_persona,
    query_narrative_persona,
)
from app.memory.shared_memory import SharedMemoryStore
from app.models.course import Course
from app.models.student_progress import PathModule
from app.models.user import User
from app.services.runtime_bridge import consultar_decision_vigente
from runtime.boundary import Entrega, normalizar_asunto

logger = logging.getLogger(__name__)

BLOOM_LABELS = {
    1: "Recordar",
    2: "Comprender",
    3: "Aplicar",
    4: "Analizar",
    5: "Evaluar",
    6: "Crear",
}


def _bloom_target_desde_entrega(module: "PathModule", entrega: Entrega) -> int:
    """Épica 2: el runtime decide, este servicio ejecuta. Si la última
    decisión del runtime (`Entrega`, S1) es sobre la MISMA competencia
    que este módulo (`entrega.asunto == normalizar_asunto(module.title)`
    — ADR-0010), su `profundidad` gobierna el nivel de Bloom objetivo:
    "fundamentos" (accion "reforzar") nunca pide más que Comprender;
    "aplicacion" (accion "avanzar-con-andamiaje") conserva el nivel
    configurado del módulo — el andamiaje es una decisión de modalidad,
    no de profundidad, y queda fuera de este primer cambio.

    Sin decisión aplicable (estudiante nuevo, sin evaluaciones aún, o la
    última decisión es sobre otro módulo de la misma sesión de curso):
    se conserva el comportamiento previo — el nivel configurado del
    módulo, sin tocar."""
    base = module.bloom_level or 3
    if entrega.diseno is None or entrega.asunto is None:
        return base
    if entrega.asunto != normalizar_asunto(module.title):
        return base
    if entrega.diseno.get("profundidad") == "fundamentos":
        return min(base, 2)
    return base


def _bloom_target_para_modulo(
    orch_id: str, student: "User", course: "Course", module: "PathModule"
) -> int:
    """Lee la decisión del runtime (S3, best-effort) y la traduce a
    `bloom_target`. Nunca bloquea la orquestación: si el runtime no
    responde (Postgres caído, lo que sea), degrada al comportamiento
    previo — el nivel configurado del módulo — igual que cualquier otra
    fase de este pipeline (ver constraints del docstring del módulo)."""
    try:
        entrega_runtime = consultar_decision_vigente(
            student_id=student.id, course_id=course.id,
        )
        return _bloom_target_desde_entrega(module, entrega_runtime)
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "orchestrate[%s]: runtime_bridge read failed (%r) — "
            "usando module.bloom_level sin la decisión del runtime",
            orch_id, exc,
        )
        return module.bloom_level or 3


# Maximum time (seconds) for the entire orchestration.  If exceeded the
# pipeline returns a gracefully-degraded result rather than a 500.
_ORCHESTRATE_TIMEOUT_S = 60.0
# Timeout for the research-agent phase alone (Tavily + async gather).
_RESEARCH_TIMEOUT_S = 28.0
# Sprint M1: LLM timeout per block and max blocks.
# Blocks are generated CONCURRENTLY (asyncio.gather), so total time ≈ single
# block time (~8-10 s measured).  Outer asyncio.wait_for must exceed LLMConfig
# timeout_seconds (30 s) to let the httpx error surface cleanly.
_CONCEPT_LLM_TIMEOUT_S = 35.0
MAX_CONCEPT_BLOCKS: int = 3

# ── Sprint M1: LLM-based concept block enrichment ─────────────────────────────

_CONCEPT_BUILDER_SYSTEM_PROMPT = (
    "Eres un pedagogo universitario experto en diseño instruccional. "
    "Tu misión es transformar fragmentos de investigación en experiencias de aprendizaje "
    "ricas, narrativas y emocionalmente resonantes en español. "
    "Usa un lenguaje accesible, metáforas cotidianas y preguntas que activen la curiosidad. "
    "Devuelve ÚNICAMENTE el JSON solicitado, sin texto adicional, sin markdown."
)


def _build_context_snippets(
    concept_strings: list[str],
    examples_raw: list,
    misconceptions_raw: list,
) -> str:
    """Condense Tavily research into a short context string for the LLM."""
    lines: list[str] = []
    for c in concept_strings[:5]:
        if c:
            lines.append(f"- {c[:200]}")
    for item in examples_raw[:2]:
        if isinstance(item, dict):
            ex = item.get("example") or item.get("content_preview") or ""
            if ex:
                lines.append(f"  Ejemplo: {str(ex)[:150]}")
        elif isinstance(item, str) and item:
            lines.append(f"  Ejemplo: {item[:150]}")
    for item in misconceptions_raw[:1]:
        if isinstance(item, dict):
            mc = item.get("misconception") or item.get("content_preview") or ""
            if mc:
                lines.append(f"  Error común: {str(mc)[:100]}")
    return "\n".join(lines)

# ── Sprint L1: Domain tables for concept-block enrichment ─────────────────────
# These live in the backend so the frontend needs no domain intelligence.

def _norm(text: str) -> str:
    """Lowercase + strip accents for accent-insensitive keyword matching."""
    return "".join(
        c for c in unicodedata.normalize("NFD", text.lower())
        if unicodedata.category(c) != "Mn"
    )


# (keywords, analogy_data) — first match wins
_ANALOGY_DOMAINS: list[tuple[list[str], dict[str, str]]] = [
    (
        ["base de datos", "database", "sql", "relacional", "nosql"],
        {
            "source":      "una biblioteca",
            "explanation": "Así como una biblioteca organiza libros en estantes y catálogos para que los encuentres rápidamente, una base de datos organiza información en tablas e índices para recuperarla en milisegundos.",
            "image_hint":  "Una biblioteca con estantes etiquetados (tablas), libros (registros) y un catálogo central (índice). Flechas indican el camino desde una búsqueda hasta el registro correcto.",
        },
    ),
    (
        ["sistema operativo", "operativo", "linux", "windows", "kernel", "proceso", "planificacion"],
        {
            "source":      "un director de orquesta",
            "explanation": "Así como el director coordina cada sección de la orquesta para que suenen en armonía sin interferirse, el sistema operativo coordina CPU, memoria y procesos para que convivan sin conflictos.",
            "image_hint":  "Un director señalando secciones de una orquesta: percusión (CPU), cuerdas (memoria), viento (procesos de E/S).",
        },
    ),
    (
        ["red", "redes", "protocolo", "internet", "tcp", "ip", "enrutamiento", "topologia"],
        {
            "source":      "un sistema de carreteras",
            "explanation": "Así como las carreteras conectan ciudades y los semáforos regulan el tráfico, las redes conectan computadoras y los protocolos regulan cómo fluye la información entre ellas.",
            "image_hint":  "Un mapa de carreteras: ciudades (computadoras), autopistas (banda ancha), cruces (routers), semáforos (protocolos de control).",
        },
    ),
    (
        ["programacion", "algoritmo", "codigo", "funcion", "variable", "bucle"],
        {
            "source":      "una receta de cocina",
            "explanation": "Así como una receta indica ingredientes exactos y pasos en orden para obtener un plato, un programa define datos y instrucciones secuenciales para resolver un problema.",
            "image_hint":  "Una receta con ingredientes (variables) y pasos numerados (instrucciones) al lado del código equivalente.",
        },
    ),
    (
        ["estadistica", "probabilidad", "regresion", "muestra", "distribucion", "hipotesis"],
        {
            "source":      "una lupa científica",
            "explanation": "Así como una lupa revela detalles que el ojo no percibe, la estadística revela patrones y verdades ocultas dentro de grandes conjuntos de datos.",
            "image_hint":  "Una lupa apuntando a puntos dispersos que, vistos a través de ella, revelan una tendencia clara y una línea de regresión.",
        },
    ),
    (
        ["inteligencia artificial", "machine learning", "aprendizaje automatico", "red neuronal", "entrenamiento"],
        {
            "source":      "un niño aprendiendo a hablar",
            "explanation": "Así como un niño aprende a hablar escuchando miles de ejemplos y corrigiendo sus errores, un modelo de ML aprende analizando datos y ajustando parámetros hasta acertar.",
            "image_hint":  "Un niño escuchando palabras (datos de entrenamiento) y un robot a su lado realizando el mismo proceso con neuronas artificiales.",
        },
    ),
    (
        ["seguridad", "ciberseguridad", "cifrado", "autenticacion", "criptografia", "vulnerabilidad"],
        {
            "source":      "una caja fuerte bancaria",
            "explanation": "Así como un banco usa candados, cámaras y controles en capas para proteger el dinero, la ciberseguridad usa cifrado, autenticación y firewalls en capas para proteger la información.",
            "image_hint":  "Una caja fuerte con capas visibles: llave (contraseña), combinación (cifrado), guardia (firewall), cámara (monitoreo).",
        },
    ),
    (
        ["ingenieria de software", "metodologia", "agile", "scrum", "patron", "arquitectura de software"],
        {
            "source":      "los planos de un arquitecto",
            "explanation": "Así como un arquitecto dibuja planos antes de construir para evitar errores costosos, la ingeniería de software diseña la estructura antes de escribir código.",
            "image_hint":  "Planos de un edificio transformándose en código: cada piso es un módulo, las puertas son interfaces, los pilares son dependencias críticas.",
        },
    ),
    (
        ["arquitectura", "hardware", "procesador", "microprocesador", "circuito", "transistor"],
        {
            "source":      "una ciudad bien planificada",
            "explanation": "Así como una ciudad tiene calles (buses de datos), edificios (unidades de procesamiento) e infraestructura (energía), la arquitectura de computadoras organiza componentes interdependientes.",
            "image_hint":  "Una ciudad: el ayuntamiento es la CPU, los barrios son la RAM, los almacenes el disco, las autopistas los buses de datos.",
        },
    ),
    (
        ["calculo", "derivada", "integral", "limite", "diferencial", "matematica"],
        {
            "source":      "un velocímetro",
            "explanation": "Así como el velocímetro mide el cambio de posición en cada instante del viaje, el cálculo diferencial mide cómo cambia cualquier cantidad en cada instante de un proceso.",
            "image_hint":  "Un velocímetro con aguja moviéndose: la velocidad instantánea representa la derivada, el área bajo la curva representa la integral.",
        },
    ),
]

# (keywords, curiosity_data)
_CURIOSITY_DOMAINS: list[tuple[list[str], dict[str, str]]] = [
    (
        ["base de datos", "database", "sql", "relacional", "nosql"],
        {
            "fact":   "Netflix almacena más de 700 petabytes de datos y procesa millones de consultas por segundo. Cada recomendación que ves es el resultado de una base de datos bien diseñada.",
            "stat":   "700 PB",
            "source": "Netflix Tech Blog, 2023",
        },
    ),
    (
        ["sistema operativo", "operativo", "linux", "windows", "kernel", "proceso"],
        {
            "fact":   "Android, el sistema operativo más usado del mundo, está basado en el kernel Linux. Más del 70% de los supercomputadores del mundo también ejecutan Linux.",
            "stat":   "70%",
            "source": "Top500 & StatCounter, 2024",
        },
    ),
    (
        ["red", "redes", "protocolo", "internet", "tcp", "ip", "enrutamiento"],
        {
            "fact":   "Google opera más de 100,000 km de cables de fibra óptica submarinos y transporta cerca del 25% de todo el tráfico de Internet mundial.",
            "stat":   "25%",
            "source": "Google Network Infrastructure, 2023",
        },
    ),
    (
        ["programacion", "algoritmo", "codigo", "funcion"],
        {
            "fact":   "El algoritmo PageRank de Google nació como un proyecto universitario. Hoy procesa más de 8,500 millones de búsquedas diarias.",
            "stat":   "8.5B/día",
            "source": "Google Search Statistics, 2024",
        },
    ),
    (
        ["estadistica", "probabilidad", "regresion", "muestra", "distribucion"],
        {
            "fact":   "Los modelos estadísticos meteorológicos procesan más de 200 millones de observaciones diarias. Un pronóstico de 7 días hoy es más preciso que uno de 1 día hace 30 años.",
            "stat":   "200M obs/día",
            "source": "NOAA & ECMWF, 2023",
        },
    ),
    (
        ["inteligencia artificial", "machine learning", "aprendizaje automatico", "red neuronal"],
        {
            "fact":   "GPT-4 fue entrenado con aproximadamente 1 trillón de tokens de texto. El consumo energético equivale al de un hogar durante más de 1,000 años.",
            "stat":   "1T tokens",
            "source": "OpenAI & AI Energy Research, 2023",
        },
    ),
    (
        ["seguridad", "ciberseguridad", "cifrado", "autenticacion", "criptografia"],
        {
            "fact":   "El costo global del cibercrimen superó los 8 trillones de dólares en 2023. Una empresa es víctima de ransomware cada 11 segundos.",
            "stat":   "$8T",
            "source": "Cybersecurity Ventures, 2023",
        },
    ),
    (
        ["ingenieria de software", "metodologia", "agile", "scrum"],
        {
            "fact":   "Un bug en el software del cohete Ariane 5 causó la pérdida de $500 millones en 1996. La causa: reutilizar código de Ariane 4 sin verificar su compatibilidad.",
            "stat":   "$500M",
            "source": "ESA Post-Flight Investigation, 1996",
        },
    ),
    (
        ["arquitectura", "hardware", "procesador", "microprocesador", "transistor"],
        {
            "fact":   "El Intel 4004 (1971) tenía 2,300 transistores. Los procesadores modernos superan los 50,000 millones. Un crecimiento de 20 millones de veces en 50 años.",
            "stat":   "50B",
            "source": "Intel Architecture History, 2023",
        },
    ),
    (
        ["calculo", "derivada", "integral", "limite", "diferencial"],
        {
            "fact":   "Las ecuaciones diferenciales del cálculo describen el movimiento de planetas, la propagación de epidemias y el comportamiento de los mercados financieros.",
            "stat":   "350+ años",
            "source": "Historia de la Matemática, 2023",
        },
    ),
]

_MEDIA_STOPWORDS = frozenset([
    "que", "una", "los", "las", "del", "con", "para", "por", "son",
    "como", "este", "esta", "estos", "estas", "cuando", "puede", "pero",
    "mas", "entre", "tiene", "dentro", "traves", "siendo", "donde",
])


def _match_domain(title: str, domains: list[tuple[list[str], dict[str, str]]]) -> dict[str, str] | None:
    """Return the data dict of the first domain whose keywords appear in title.

    Matching rules:
    - Multi-word keyword: exact phrase substring match.
    - Single-word keyword: prefix match against each title word — handles
      plurals (sistema→sistemas, red→redes) and prevents substring false
      positives ("ip" inside "descriptiva" would NOT match because
      "descriptiva" does not start with "ip").
    """
    title_norm = _norm(title)
    title_words = title_norm.split()
    for keywords, data in domains:
        for kw in keywords:
            kw_norm = _norm(kw)
            if " " in kw_norm:
                # Multi-word: phrase must appear verbatim
                if kw_norm in title_norm:
                    return data
            else:
                # Single-word: any title word must start with the keyword
                if any(w.startswith(kw_norm) for w in title_words):
                    return data
    return None


def _extract_concept_terms(text: str, count: int = 5) -> str:
    """Extract up to `count` unique meaningful words from concept text."""
    clean = "".join(c if c.isalpha() or c.isspace() else " " for c in _norm(text))
    seen: set[str] = set()
    result: list[str] = []
    for word in clean.split():
        if len(word) >= 5 and word not in _MEDIA_STOPWORDS and word not in seen:
            seen.add(word)
            result.append(word)
        if len(result) >= count:
            break
    return ", ".join(result)


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
        bloom_target = _bloom_target_para_modulo(orch_id, student, course, module)
        session_id = uuid.uuid4().hex[:12]
        t0 = time.monotonic()

        def _elapsed() -> int:
            return int((time.monotonic() - t0) * 1000)

        def _db_state() -> str:
            try:
                return "active" if db.is_active else "closed"
            except Exception:
                return "unknown"

        logger.info(
            "orchestrate[%s]: start — module=%s topic=%r bloom=%d student=%s course=%s",
            orch_id, module.id[:8], topic[:40] if topic else "<none>", bloom_target,
            student.id[:8], course.id[:8],
        )

        # ── Phase 1: Narrative query (reads prior session context) ───────
        logger.debug("orchestrate[%s]: phase=narrative_query elapsed_ms=0 db=%s", orch_id, _db_state())
        narrative = self._phase_narrative_query(orch_id, memory_store, student, course)
        logger.debug("orchestrate[%s]: phase=narrative_query elapsed_ms=%d keys=%d", orch_id, _elapsed(), len(narrative))

        # ── Phase 2: Research (Tavily retrieval, degraded if no API key) ─
        logger.debug("orchestrate[%s]: phase=research start elapsed_ms=%d db=%s", orch_id, _elapsed(), _db_state())
        research_state = await self._phase_research(
            orch_id, topic, bloom_target, student, module, narrative,
            memory_store=memory_store,
            session_id=session_id,
        )
        logger.info(
            "orchestrate[%s]: phase=research done elapsed_ms=%d degraded=%s sources=%d db=%s",
            orch_id, _elapsed(),
            research_state.get("research", {}).get("degraded", True),
            research_state.get("research", {}).get("total_sources", 0),
            _db_state(),
        )

        # ── Phase 3: Content generation + LLM enrichment ────────────────
        logger.debug("orchestrate[%s]: phase=content_build start elapsed_ms=%d", orch_id, _elapsed())
        try:
            result = await self._build_orchestration_result(
                research_state, student, course, module, bloom_target, orch_id,
                session_id=session_id,
            )
        except Exception as build_exc:
            logger.error(
                "orchestrate[%s]: phase=content_build FAILED elapsed_ms=%d error=%r",
                orch_id, _elapsed(), build_exc, exc_info=True,
            )
            raise
        logger.debug(
            "orchestrate[%s]: phase=content_build done elapsed_ms=%d status=%s",
            orch_id, _elapsed(), result.get("orchestration_status"),
        )

        # ── Phase 4: Narrative publish (writes session context for future) ─
        logger.debug("orchestrate[%s]: phase=narrative_publish start elapsed_ms=%d db=%s", orch_id, _elapsed(), _db_state())
        self._phase_narrative_publish(orch_id, memory_store, student, module, course, result)

        elapsed_ms = _elapsed()
        logger.info(
            "orchestrate[%s]: complete elapsed_ms=%d status=%s confidence=%.3f module=%s db=%s",
            orch_id, elapsed_ms,
            result.get("orchestration_status", "?"),
            result.get("confidence", 0.0),
            module.id[:8],
            _db_state(),
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
        session_id: str | None = None,
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
                    "session_id": session_id,
                    "_trace_context": {
                        "session_id": session_id,
                        "correlation_id": session_id,
                        "sequence": 0,
                    },
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

    async def _build_orchestration_result(
        self,
        research_state: dict[str, Any],
        student: User,
        course: Course,
        module: PathModule,
        bloom_target: int,
        orch_id: str,
        session_id: str | None = None,
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
        logger.debug(
            "orchestrate[%s]: research results — concepts=%d misconceptions=%d examples=%d applications=%d",
            orch_id, len(concepts), len(misconceptions_raw), len(examples_raw), len(applications_raw),
        )

        introduction = self._generate_introduction(module.title, concepts)
        explanation = self._generate_explanation(module.title, concepts, bloom_target)
        misconceptions = self._build_misconceptions(misconceptions_raw, module.title)
        examples = self._build_examples(examples_raw, module.title, bloom_target)
        applications = self._build_real_applications(applications_raw, module.title)
        guided_practice = self._generate_guided_practice(module.title, bloom_target)
        multimodal_prompts = self._build_multimodal_prompts(multimodal_prompts_raw, module.title)
        concept_blocks = await self._build_concept_blocks(
            topic=module.title,
            concepts=concepts,
            examples_raw=examples_raw,
            misconceptions_raw=misconceptions_raw,
            bloom_target=bloom_target,
            orch_id=orch_id,
        )
        storyboard = self._generate_storyboard(module.title, pedagogical_stages)
        continuity = self._generate_continuity_notes(module.title, module, course)
        bloom_progression = self._build_bloom_progression(module.title)
        retrieval_evidence = self._build_retrieval_evidence(research)

        confidence = float(research_metrics.get("pedagogical_confidence", 0.0) or 0.0)
        valid = consistency.get("valid", False)
        semantic_ok = self._validate_generated_content(module.title, introduction, explanation, orch_id)
        if not semantic_ok:
            orchestration_status = "generated_with_warnings"
        else:
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
            "session_id": session_id,
            "concept_blocks": concept_blocks,
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
            "session_id": None,
            "concept_blocks": [],  # degraded — no blocks
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
                    f"¿Has tenido contacto con este tema antes? "
                    f"Identifica qué conceptos previos del curso son necesarios "
                    f"para construir nuevo conocimiento sobre este tema."
                ),
                "examples": [
                    f"Pregunta guía: ¿Qué problemas o situaciones reales se relacionan con {topic.lower()}?",
                    "Relaciona con los temas previos del curso que ya has estudiado.",
                ],
            },
            {
                "phase": "exploracion",
                "focus": f"Explorar {topic.lower()} desde múltiples perspectivas",
                "bloom_level": 2,
                "content": (
                    f"Explora cómo se define y utiliza {topic.lower()} en diferentes contextos. "
                    f"Analiza sus principios fundamentales y cómo se aplican. "
                    f"Compara distintas formas de entender y utilizar este tema."
                ),
                "examples": self._concepts_to_strings(concepts[:3]) or [
                    f"Concepto clave 1 de {topic.lower()}",
                    f"Concepto clave 2 de {topic.lower()}",
                ],
            },
            {
                "phase": "construccion",
                "focus": f"Construir comprensión profunda de {topic.lower()}",
                "bloom_level": min(bloom_target, 4),
                "content": (
                    f"Desarrolla tu comprensión de {topic.lower()} aplicando sus principios "
                    f"a casos concretos. Practica con ejercicios que requieran análisis "
                    f"y toma de decisiones basada en lo aprendido."
                ),
                "examples": [
                    f"Ejercicio guiado: analiza un caso real donde se aplique {topic.lower()}.",
                    "Prueba diferentes enfoques y justifica cuál es más adecuado.",
                ],
            },
            {
                "phase": "transferencia",
                "focus": f"Aplicar {topic.lower()} en contextos reales",
                "bloom_level": min(bloom_target + 1, 6),
                "content": (
                    f"Aplica {topic.lower()} para resolver problemas del ámbito del curso. "
                    f"Integra este conocimiento con otros temas ya estudiados. "
                    f"Evalúa cuándo y por qué es relevante aplicar lo aprendido."
                ),
                "examples": [
                    f"Proyecto integrador: diseña una solución que use los conceptos de {topic.lower()}.",
                    "Reflexiona sobre lo aprendido y cómo conecta con el resto del curso.",
                ],
            },
        ]

    def _generate_introduction(self, topic: str, concepts: list[str]) -> str:
        concept_list = ", ".join(self._concepts_to_strings(concepts[:3])) if concepts else ""
        if concept_list:
            return (
                f"Bienvenido al módulo de **{topic}**. "
                f"A lo largo de este módulo explorarás conceptos como {concept_list}, "
                f"desarrollarás habilidades prácticas y comprenderás cómo aplicar este conocimiento "
                f"en situaciones reales. Prepárate para construir una base sólida en este tema."
            )
        return (
            f"Bienvenido al módulo de **{topic}**. "
            f"Este módulo te introduce a los conceptos fundamentales de {topic.lower()}, "
            f"con el objetivo de que puedas comprenderlos, aplicarlos y analizarlos "
            f"en contextos académicos y profesionales. "
            f"Sigue el recorrido paso a paso para consolidar tu aprendizaje."
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
        bloom_label = BLOOM_LABELS.get(bloom_target, "Aplicar")
        if concept_strings:
            concept_detail = ". ".join(
                f"{c}: aspecto clave de {topic.lower()}" for c in concept_strings
            )
            return (
                f"**{topic}** abarca un conjunto de conceptos y principios fundamentales "
                f"dentro de esta área de estudio. {concept_detail}. "
                f"A nivel Bloom {bloom_target} ({bloom_label}), "
                f"podrás no solo comprender sino también aplicar y analizar "
                f"estos conceptos en situaciones concretas."
            )
        return (
            f"**{topic}** es un tema central dentro de este curso. "
            f"Comprender {topic.lower()} implica conocer sus principios fundamentales, "
            f"identificar sus usos en la práctica y ser capaz de aplicarlos con criterio. "
            f"A nivel Bloom {bloom_target} ({bloom_label}), "
            f"el objetivo es que puedas no solo reconocer los conceptos "
            f"sino también utilizarlos para resolver problemas reales."
        )

    def _build_misconceptions(
        self, raw: list[dict[str, Any]], topic: str
    ) -> list[dict[str, str]]:
        if raw:
            built = [
                {
                    "misconception": str(item.get("misconception") or f"Error conceptual sobre {topic.lower()}"),
                    "correction": str(item.get("correction") or "La comprensión correcta requiere revisar las fuentes del módulo."),
                    "severity": str(item.get("severity") or "medium"),
                }
                for item in raw[:4]
                if isinstance(item, dict)
            ]
            if built:
                logger.debug("_build_misconceptions: %d items from research for topic=%r", len(built), topic[:40])
                return built
        logger.debug("_build_misconceptions: using generic fallback for topic=%r", topic[:40])
        return [
            {
                "misconception": f"Creer que {topic.lower()} no tiene aplicaciones prácticas relevantes",
                "correction": f"{topic} tiene aplicaciones en múltiples contextos académicos y profesionales que vale la pena explorar.",
                "severity": "medium",
            },
            {
                "misconception": f"Pensar que dominar {topic.lower()} requiere memorizarlo todo",
                "correction": "La comprensión profunda viene de relacionar conceptos y aplicarlos, no de memorizar definiciones.",
                "severity": "medium",
            },
        ]

    def _build_examples(self, raw: list, topic: str, bloom_target: int) -> list[str]:
        safe = self._concepts_to_strings(raw)
        if safe:
            logger.debug("_build_examples: %d items from research for topic=%r", len(safe), topic[:40])
            return safe[:5]
        logger.debug("_build_examples: using generic fallback for topic=%r", topic[:40])
        return [
            f"Ejemplo introductorio: identifica los conceptos básicos de {topic.lower()} en un caso concreto.",
            f"Ejemplo de comprensión: explica con tus palabras cómo se relacionan los elementos de {topic.lower()}.",
            f"Ejemplo de aplicación: resuelve un problema sencillo usando los principios de {topic.lower()}.",
            f"Ejemplo de análisis: compara dos enfoques diferentes para abordar {topic.lower()} y justifica cuál es mejor.",
            f"Ejemplo de evaluación: dado un escenario real, determina cómo aplicar {topic.lower()} de manera óptima.",
        ]

    def _build_real_applications(self, raw: list, topic: str) -> list[str]:
        safe = self._concepts_to_strings(raw)
        if safe:
            logger.debug("_build_real_applications: %d items from research for topic=%r", len(safe), topic[:40])
            return safe[:4]
        logger.debug("_build_real_applications: using generic fallback for topic=%r", topic[:40])
        return [
            f"{topic} se aplica en entornos profesionales para resolver problemas concretos del área.",
            f"En investigación y academia, {topic.lower()} es base de múltiples metodologías de análisis.",
            f"El conocimiento de {topic.lower()} facilita la toma de decisiones informadas en proyectos reales.",
            f"Profesionales de diversas industrias utilizan {topic.lower()} como herramienta de trabajo cotidiana.",
        ]

    def _generate_guided_practice(self, topic: str, bloom_target: int) -> str:
        bloom_label = BLOOM_LABELS.get(bloom_target, "Aplicar")
        return (
            f"**Práctica guiada: Explorando {topic}**\n\n"
            f"**Objetivo:** Consolidar la comprensión de {topic.lower()} mediante un ejercicio práctico "
            f"orientado al nivel Bloom {bloom_target} ({bloom_label}).\n\n"
            f"**Instrucciones:**\n"
            f"1. Revisa los conceptos clave de {topic.lower()} vistos en el módulo.\n"
            f"2. Identifica al menos dos situaciones reales donde aplicarías lo aprendido.\n"
            f"3. Resuelve el siguiente ejercicio: dado un escenario del área de {topic.lower()}, "
            f"analiza el problema, propón una solución y justifica tu razonamiento.\n"
            f"4. Compara tu solución con un enfoque alternativo y señala ventajas y limitaciones.\n"
            f"5. **Desafío:** Diseña un mini-proyecto que integre los conceptos de {topic.lower()} "
            f"con otros temas del curso.\n\n"
            f"**Preguntas de reflexión:**\n"
            f"- ¿Qué aspectos de {topic.lower()} te resultaron más difíciles de comprender?\n"
            f"- ¿Cómo conectas lo aprendido sobre {topic.lower()} con otros temas del curso?\n"
            f"- ¿En qué situaciones cotidianas o profesionales podrías encontrar {topic.lower()}?"
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
            f"Se conecta con los módulos anteriores del curso y sienta las bases "
            f"para los temas que se abordarán más adelante.\n\n"
            f"**Para aprovechar mejor este módulo:**\n"
            f"- Repasa los conceptos fundamentales vistos en módulos previos del curso.\n"
            f"- Identifica cómo {topic.lower()} se relaciona con lo que ya has aprendido.\n"
            f"- Toma nota de los términos nuevos para consultarlos durante el módulo.\n\n"
            f"**Conexión con módulos futuros:**\n"
            f"- Los conceptos de {topic.lower()} serán base para temas más avanzados del curso.\n"
            f"- Mantén tus apuntes organizados; los necesitarás en actividades integradoras.\n"
            f"- Consulta con tu docente si algún concepto no queda claro antes de avanzar."
        )

    # Courses where CS-domain terms ("estructura de datos", "índice", etc.) are valid.
    _CS_COURSE_SIGNALS = frozenset([
        "arreglo", "array", "lista", "pila", "cola", "árbol", "grafo", "hash",
        "struct", "clase", "objeto", "algoritmo", "programaci",
        "base de datos", "database", "sql",
        "sistema operativo",
        "ingenieria", "ingenier",
        "software",
        "computaci",
        "desarrollo",
        "estructura",
    ])
    _FORBIDDEN_IN_NON_CS = [
        "estructura de datos",
        "búsqueda binaria",
        "busqueda binaria",
        "lista enlazada",
        "posición de memoria",
        "posicion de memoria",
        "arreglo",
        "indice es la posición",
    ]
    # Noise words skipped when checking topic presence in generated text.
    _TOPIC_STOPWORDS = frozenset(["de", "del", "la", "el", "los", "las", "y", "e", "i", "ii", "iii", "iv", "semana"])

    @staticmethod
    def _topic_keywords(topic: str) -> list[str]:
        """Return meaningful words from a topic title (len > 3, not stopwords)."""
        normalized = topic.lower().replace(":", " ").replace("-", " ")
        return [
            w for w in normalized.split()
            if len(w) > 3 and w not in ModuleOrchestrationService._TOPIC_STOPWORDS
        ]

    def _validate_generated_content(
        self, topic: str, introduction: str, explanation: str, orch_id: str
    ) -> bool:
        topic_lower = topic.lower()
        is_cs_topic = any(sig in topic_lower for sig in self._CS_COURSE_SIGNALS)

        intro_lower = introduction.lower()
        expl_lower  = explanation.lower()

        # 1. At least one meaningful keyword from the topic must appear in each text.
        keywords = self._topic_keywords(topic)
        if keywords:
            if not any(kw in intro_lower for kw in keywords):
                logger.warning(
                    "orchestrate[%s]: semantic_validation FAIL — no topic keyword %r found in introduction",
                    orch_id, keywords,
                )
                return False
            if not any(kw in expl_lower for kw in keywords):
                logger.warning(
                    "orchestrate[%s]: semantic_validation FAIL — no topic keyword %r found in explanation",
                    orch_id, keywords,
                )
                return False

        # 2. For non-CS courses, forbidden CS tokens must not appear.
        if not is_cs_topic:
            for token in self._FORBIDDEN_IN_NON_CS:
                if token in intro_lower or token in expl_lower:
                    logger.warning(
                        "orchestrate[%s]: semantic_validation FAIL — forbidden token %r found "
                        "in content for non-CS topic %r",
                        orch_id, token, topic[:40],
                    )
                    return False

        logger.debug("orchestrate[%s]: semantic_validation OK for topic=%r", orch_id, topic[:40])
        return True

    # ------------------------------------------------------------------
    # Sprint L1: ConceptBlock generation
    # ------------------------------------------------------------------

    async def _build_concept_blocks(
        self,
        topic: str,
        concepts: list[str],
        examples_raw: list,
        misconceptions_raw: list[dict[str, Any]],
        bloom_target: int,
        orch_id: str,
    ) -> list[dict[str, Any]]:
        """Generate up to MAX_CONCEPT_BLOCKS enriched ConceptBlocks.

        Sprint M1: LLM-first generation (gpt-4o-mini via LLMService), with
        domain-table / template fallback per block when the LLM is
        unavailable or fails.  Returns [] when concepts is empty.
        """
        concept_strings = self._concepts_to_strings(concepts[:MAX_CONCEPT_BLOCKS])
        if not concept_strings:
            logger.debug("orchestrate[%s]: _build_concept_blocks: no concepts — returning []", orch_id)
            return []

        examples         = self._concepts_to_strings(examples_raw)
        context_snippets = _build_context_snippets(concept_strings, examples_raw, misconceptions_raw)
        blocks: list[dict[str, Any]] = []

        # Create LLMService once for all blocks — avoids 3 httpx.AsyncClient instances.
        llm_svc: LLMService | None = None
        if settings.has_openai:
            llm_svc = LLMService(default_config=LLMConfig(
                model="gpt-4o-mini",
                api_key=settings.OPENAI_API_KEY or "",
                temperature=0.4,
                max_tokens=1500,
                timeout_seconds=30.0,  # Measured ~8s; 30s gives safe margin
                max_retries=1,
                budget_tokens_per_day=300_000,
            ))

        title_low   = topic.lower()
        bloom_label = BLOOM_LABELS.get(bloom_target, "Aplicar")

        # ── Sprint M1: fire all LLM calls CONCURRENTLY ───────────────────────
        # asyncio.gather makes 3 concurrent calls instead of sequential,
        # reducing total LLM time from ~3×8s to ~8s.
        # return_exceptions=True prevents one block failure from cancelling others.
        if llm_svc:
            llm_tasks = [
                asyncio.wait_for(
                    self._generate_concept_block_with_llm(
                        llm_svc=llm_svc,
                        topic=topic,
                        bloom_target=bloom_target,
                        bloom_label=bloom_label,
                        concept_text=ct,
                        context_snippets=context_snippets,
                        block_idx=idx,
                        orch_id=orch_id,
                    ),
                    timeout=_CONCEPT_LLM_TIMEOUT_S,
                )
                for idx, ct in enumerate(concept_strings)
            ]
            raw_results: list = await asyncio.gather(*llm_tasks, return_exceptions=True)
        else:
            raw_results = [None] * len(concept_strings)

        for i, concept_text in enumerate(concept_strings):
            block_id = f"block-{i}"
            title    = self._concept_title(concept_text, topic, i)
            learning_objective = (
                f"Al finalizar este bloque podrás {bloom_label.lower()} "
                f"los conceptos de {title_low} a nivel Bloom {bloom_target}."
            )
            example  = examples[i] if i < len(examples) else None

            raw = raw_results[i]
            if isinstance(raw, Exception):
                logger.warning(
                    "orchestrate[%s]: LLM concept_block_%d failed: %s — template fallback",
                    orch_id, i, raw,
                )
                raw = None
            llm_data: dict[str, Any] | None = raw if isinstance(raw, dict) else None

            if llm_data:
                # ── LLM path: use generated content, fill missing fields ──────
                block: dict[str, Any] = {
                    "id":                  block_id,
                    "title":               title,
                    "explanation":         llm_data.get("explanation") or concept_text,
                    "learning_objective":  learning_objective,
                    "example":             example,
                    "analogy":             llm_data.get("analogy") or self._template_analogy(topic),
                    "curiosity":           llm_data.get("curiosity") or self._template_curiosity(topic),
                    "media_prompt":        llm_data.get("media_prompt") or self._template_media_prompt(topic, concept_text, i),
                    "mini_activity":       llm_data.get("mini_activity") or self._template_mini_activity(title, topic),
                    "prediction_question": llm_data.get("prediction_question") or None,
                    "reflection_question": llm_data.get("reflection_question") or None,
                    "reflection":          None,
                    "knowledge_check":     None,
                }
                logger.debug(
                    "orchestrate[%s]: block-%d enriched via LLM (topic=%r)",
                    orch_id, i, topic[:40],
                )
            else:
                # ── Template fallback: domain tables + generic templates ───────
                analogy_domain = _match_domain(topic, _ANALOGY_DOMAINS)
                if analogy_domain:
                    analogy: dict[str, Any] | None = {
                        "source":      analogy_domain["source"],
                        "explanation": analogy_domain["explanation"],
                        "image_hint":  analogy_domain.get("image_hint"),
                    }
                else:
                    analogy = self._template_analogy(topic)

                curiosity_domain = _match_domain(topic, _CURIOSITY_DOMAINS)
                curiosity: dict[str, Any] | None = (
                    dict(curiosity_domain) if curiosity_domain
                    else self._template_curiosity(topic)
                )

                block = {
                    "id":                  block_id,
                    "title":               title,
                    "explanation":         concept_text,
                    "learning_objective":  learning_objective,
                    "example":             example,
                    "analogy":             analogy,
                    "curiosity":           curiosity,
                    "media_prompt":        self._template_media_prompt(topic, concept_text, i),
                    "mini_activity":       self._template_mini_activity(title, topic),
                    "prediction_question": None,
                    "reflection_question": None,
                    "reflection":          None,
                    "knowledge_check":     None,
                }

            blocks.append(block)

        logger.info(
            "orchestrate[%s]: _build_concept_blocks: %d blocks, llm_path=%s, topic=%r",
            orch_id, len(blocks),
            all(b.get("prediction_question") is not None for b in blocks),
            topic[:40],
        )
        return blocks

    async def _generate_concept_block_with_llm(
        self,
        *,
        llm_svc: LLMService,
        topic: str,
        bloom_target: int,
        bloom_label: str,
        concept_text: str,
        context_snippets: str,
        block_idx: int,
        orch_id: str,
    ) -> dict[str, Any] | None:
        """Call LLMService to generate a rich ConceptBlock.

        Receives the shared LLMService instance (created once per
        _build_concept_blocks call) to avoid re-creating httpx.AsyncClient
        for every block.

        Returns the parsed dict on success, None on any failure.
        The caller is responsible for the fallback.
        """
        user_prompt = (
            f"TEMA DEL MÓDULO: {topic}\n"
            f"NIVEL BLOOM: {bloom_target}/6 — {bloom_label}\n\n"
            f"CONTEXTO DE INVESTIGACIÓN (fragmentos recuperados de la web):\n"
            f"{context_snippets or '(sin contexto adicional)'}\n\n"
            f"CONCEPTO A ENRIQUECER:\n\"{concept_text}\"\n\n"
            f"Genera el bloque pedagógico en JSON con EXACTAMENTE estos campos:\n"
            f"{{\n"
            f"  \"explanation\": \"párrafo narrativo 4-6 oraciones. "
            f"OBLIGATORIO comenzar con Imagina que... o ¿Alguna vez te has preguntado...? o Piensa en... "
            f"Usa lenguaje accesible y una metáfora cotidiana concreta.\",\n"
            f"  \"analogy\": {{\"source\": \"elemento cotidiano del dominio {topic}\", "
            f"\"explanation\": \"por qué el concepto se parece a ese elemento, con detalles específicos\"}},\n"
            f"  \"curiosity\": {{\"fact\": \"dato sorprendente y real sobre {topic} (verificable)\", "
            f"\"stat\": \"cifra o porcentaje destacable, o null\", \"source\": \"fuente real con año\"}},\n"
            f"  \"mini_activity\": {{\"instructions\": \"descripción clara de una micro-actividad de 2 min\", "
            f"\"steps\": [\"paso concreto 1\", \"paso concreto 2\", \"paso concreto 3\"]}},\n"
            f"  \"prediction_question\": \"pregunta que el estudiante reflexiona ANTES de leer el concepto "
            f"(ej: ¿Qué crees que significa...? o ¿Cómo imaginas que funciona...?)\",\n"
            f"  \"reflection_question\": \"pregunta reflexión nivel Bloom {bloom_label}: "
            f"¿De qué manera podrías...? o ¿Cómo aplicarías esto en...?\",\n"
            f"  \"media_prompt\": {{\"type\": \"image\" o \"video\", "
            f"\"title\": \"título descriptivo de la actividad\", "
            f"\"prompt\": \"prompt detallado de 40-80 palabras para crear el recurso\", "
            f"\"learning_goal\": \"objetivo pedagógico en 1 oración\"}}\n"
            f"}}"
        )

        t = time.monotonic()
        response = await llm_svc.generate(
            messages=[
                {"role": "system", "content": _CONCEPT_BUILDER_SYSTEM_PROMPT},
                {"role": "user",   "content": user_prompt},
            ],
            voter_name="concept_builder",
            response_format="json",
        )
        elapsed_ms = int((time.monotonic() - t) * 1000)

        if not response.success or not response.parsed:
            logger.warning(
                "orchestrate[%s]: _generate_concept_block_with_llm block_%d: "
                "success=%s parsed=%s error=%s elapsed_ms=%d",
                orch_id, block_idx,
                response.success, bool(response.parsed), response.error, elapsed_ms,
            )
            return None

        logger.debug(
            "orchestrate[%s]: _generate_concept_block_with_llm block_%d OK "
            "tokens=%d elapsed_ms=%d",
            orch_id, block_idx, response.tokens_total, elapsed_ms,
        )
        return response.parsed

    # ── Template helpers used by both LLM-fallback and pure-template paths ────

    def _template_analogy(self, topic: str) -> dict[str, Any]:
        title_low = topic.lower()
        return {
            "source":      "una guía de viaje",
            "explanation": (
                f"Así como una guía de viaje te orienta con mapas y consejos prácticos, "
                f"{title_low} te proporciona los fundamentos para orientarte en su campo."
            ),
            "image_hint": None,
        }

    def _template_curiosity(self, topic: str) -> dict[str, Any]:
        return {
            "fact": (
                f"Profesionales de todo el mundo aplican los principios de "
                f"{topic.lower()} en industrias tan diversas como medicina, "
                f"finanzas y tecnología."
            ),
            "stat":   None,
            "source": "Tendencias profesionales, 2024",
        }

    def _template_media_prompt(
        self, topic: str, concept_text: str, block_idx: int
    ) -> dict[str, Any]:
        key_terms = _extract_concept_terms(concept_text, 5)
        title_low = topic.lower()
        if (block_idx % 3) != 1:
            prompt = (
                f"Crea una infografía educativa sobre \"{topic}\" que visualice: {key_terms}. "
                f"Usa íconos, flechas y colores para mostrar relaciones. Fondo blanco, estilo profesional."
            ) if key_terms else (
                f"Crea una infografía educativa que explique \"{topic}\" con ejemplos cotidianos. "
                f"Incluye íconos y flechas. Fondo blanco, estilo profesional."
            )
            return {
                "type":             "image",
                "title":            f"Visualiza: {topic}",
                "prompt":           prompt,
                "learning_goal":    (
                    f"Construir una imagen mental refuerza la memoria a largo plazo y facilita "
                    f"la comprensión de ideas abstractas en {title_low}."
                ),
                "duration_seconds": None,
            }
        prompt = (
            f"Escribe el guion de un video animado de 90 segundos sobre \"{topic}\" "
            f"enfocándose en: {key_terms}. Usa metáforas cotidianas y un ejemplo real."
        ) if key_terms else (
            f"Escribe el guion de un video animado de 90 segundos que explique \"{topic}\" "
            f"con una metáfora cotidiana al inicio y una aplicación práctica al final."
        )
        return {
            "type":             "video",
            "title":            f"Explora en video: {topic}",
            "prompt":           prompt,
            "learning_goal":    (
                f"Los videos activan múltiples canales sensoriales, incrementando la retención "
                f"de {title_low} hasta un 65%."
            ),
            "duration_seconds": 90,
        }

    def _template_mini_activity(self, title: str, topic: str) -> dict[str, Any]:
        return {
            "instructions": f"Refuerza la idea principal del concepto sobre {topic.lower()}.",
            "steps": [
                f"Lee nuevamente la explicación de '{title}'.",
                "Identifica el concepto clave que se presenta.",
                "Escribe mentalmente una frase que lo resuma con tus propias palabras.",
            ],
        }

    @staticmethod
    def _concept_title(text: str, topic: str, idx: int) -> str:
        """Derive a short title from the concept text."""
        bold = re.match(r"\*\*(.+?)\*\*", text)
        if bold:
            return bold.group(1)[:80]
        first = re.split(r"[.,;]", text.strip())[0]
        words = first.split()[:8]
        title = " ".join(words)
        return title[:80] if title else f"Concepto {idx + 1} sobre {topic}"

    def _build_bloom_progression(self, topic: str) -> list[dict[str, Any]]:
        return [
            {"level": 1, "label": "Recordar", "description": f"Identificar y definir {topic.lower()}", "mastered": False},
            {"level": 2, "label": "Comprender", "description": f"Explicar los principios de {topic.lower()}", "mastered": False},
            {"level": 3, "label": "Aplicar", "description": f"Usar {topic.lower()} para resolver casos concretos", "mastered": False},
            {"level": 4, "label": "Analizar", "description": f"Comparar enfoques y analizar implicaciones de {topic.lower()}", "mastered": False},
            {"level": 5, "label": "Evaluar", "description": f"Evaluar soluciones basadas en {topic.lower()} con criterio fundamentado", "mastered": False},
            {"level": 6, "label": "Crear", "description": f"Diseñar propuestas originales integrando {topic.lower()}", "mastered": False},
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
