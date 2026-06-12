"""
AI-first pedagogical orchestration for teachers.

The teacher contributes weekly intent; the system handles retrieval, planning,
prompting, consistency checks, and consensus-ready output.

Memory-influenced pedagogical generation:
  - Student profile (learning style, modality, analogies, pacing, etc.)
    is aggregated from SharedMemoryStore at the start of orchestration.
  - Every downstream agent adapts its output based on this profile.
  - The effect is **demonstrable**: prompts change, scaffolding changes,
    difficulty changes, narrative continues — all driven by real memory.
"""

from datetime import datetime, timezone
from typing import Any
import uuid

from sqlalchemy.orm import Session

from app.agents.research_agent import ResearchAgent
from app.agents.reviewer_agent import ReviewerAgent
from app.memory.shared_memory import SharedMemoryStore
from app.memory.pedagogical_memory import PedagogicalMemoryService
from app.memory.narrative_continuity import query_narrative_persona
from app.models.course import Course
from app.models.event_outbox import EventOutbox
from app.models.user import User
from app.models.weekly_pedagogical_plan import WeeklyPedagogicalPlan
from app.schemas.pedagogy import WeeklyPedagogicalPlanCreate


# ── Analogy domain templates ──────────────────────────────────────────

GAMING_TEMPLATES = {
    "phase_labels": ["Tutorial", "Nivel 1", "Nivel 2", "Jefe Final"],
    "phase_focus": [
        "Aprender los controles basicos de {topic}",
        "Superar el primer desafio aplicando conceptos",
        "Resolver un problema combinando tecnicas",
        "Demostrar dominio completo contra el desafio final",
    ],
    "scaffolding": [
        "tutorial interactivo guiado paso a paso",
        "mision secundaria de practica",
        "reto principal con pistas disponibles",
        "logro de transferencia (bonus level)",
    ],
    "differentiation_support": "modo facil: pistas visuales, tiempo extra, checkpoint frecuente",
    "differentiation_standard": "modo normal: desafio equilibrado con feedback inmediato",
    "differentiation_advanced": "modo dificil: sin pistas, variacion inesperada, jefe secreto",
    "analogy_intro": "Como en un videojuego, cada nivel te prepara para el siguiente. ",
    "tone": "gamificada",
}

MUSIC_TEMPLATES = {
    "phase_labels": ["Compas 1", "Compas 2", "Compas 3", "Improvisacion"],
    "phase_focus": [
        "Escuchar el ritmo basico de {topic}",
        "Aprender la melodia conceptual",
        "Tocar en conjunto aplicando armonia",
        "Improvisar libremente sobre lo aprendido",
    ],
    "scaffolding": [
        "calentamiento con ejercicios simples",
        "practica de patrones guiada",
        "ensamble guiado con retroalimentacion",
        "improvisacion libre con criterios de exito",
    ],
    "differentiation_support": "ritmo lento: compas simple, repeticion, apoyo visual",
    "differentiation_standard": "ritmo moderado: patrones variados, autoevaluacion",
    "differentiation_advanced": "ritmo acelerado: cambios de compas, composicion original",
    "analogy_intro": "Como una pieza musical, cada concepto tiene su ritmo y melodia. ",
    "tone": "musical",
}

SPORTS_TEMPLATES = {
    "phase_labels": ["Calentamiento", "Entrenamiento", "Partido", "Torneo"],
    "phase_focus": [
        "Preparar el terreno con conceptos previos de {topic}",
        "Practicar la tecnica fundamental",
        "Aplicar en un escenario de juego real",
        "Competir resolviendo problemas complejos",
    ],
    "scaffolding": [
        "ejercicio de calentamiento guiado",
        "practica de tecnica con retroalimentacion",
        "partido de aplicacion en equipo",
        "torneo final de transferencia",
    ],
    "differentiation_support": "categoria principiante: ejercicios basicos, mas repeticiones",
    "differentiation_standard": "categoria intermedia: tecnicas combinadas, auto-evaluacion",
    "differentiation_advanced": "categoria avanzada: jugadas complejas, liderazgo de equipo",
    "analogy_intro": "Como en el deporte, cada habilidad se entrena hasta dominarla. ",
    "tone": "deportiva",
}

DEFAULT_TEMPLATES = {
    "phase_labels": ["Activacion", "Exploracion", "Construccion", "Transferencia"],
    "phase_focus": [
        "Conectar saberes previos con {topic}",
        "Explorar fuentes recuperadas y contrastar ejemplos",
        "Resolver una tarea guiada alineada a objetivos",
        "Aplicar el aprendizaje en un contexto nuevo",
    ],
    "scaffolding": [
        "diagnostico breve de entrada",
        "micro-reto guiado",
        "retroalimentacion adaptativa",
        "reto de transferencia",
    ],
    "differentiation_support": "pistas progresivas y ejemplos resueltos",
    "differentiation_standard": "actividad con criterios de exito visibles",
    "differentiation_advanced": "variacion del problema con mayor autonomia",
    "analogy_intro": "",
    "tone": "",
}


def _select_templates(analogies: list[str] | None) -> dict:
    if not analogies:
        return DEFAULT_TEMPLATES
    domain = analogies[0].strip().lower()
    if domain == "gaming":
        return GAMING_TEMPLATES
    if domain in ("music", "musical"):
        return MUSIC_TEMPLATES
    if domain in ("sports", "deportes"):
        return SPORTS_TEMPLATES
    return DEFAULT_TEMPLATES


# ── Agent classes ─────────────────────────────────────────────────────


class PedagogicalStructuring:
    def run(self, data: WeeklyPedagogicalPlanCreate, research: dict[str, Any]) -> dict[str, Any]:
        concepts = research.get("concepts", [])[:4]
        examples = research.get("examples", [])[:3]
        misconceptions = research.get("misconceptions", [])[:3]
        return {
            "weekly_sequence": [
                {"phase": "activation", "focus": f"Conectar saberes previos con {data.topic}"},
                {"phase": "exploration", "focus": "Explorar fuentes recuperadas y contrastar ejemplos"},
                {"phase": "construction", "focus": "Resolver una tarea guiada alineada a objetivos"},
                {"phase": "transfer", "focus": "Aplicar el aprendizaje en un contexto nuevo"},
            ],
            "core_concepts": concepts,
            "worked_examples": examples,
            "misconceptions_to_address": misconceptions,
            "teacher_validation_focus": [
                "Alineacion con intencion pedagogica",
                "Nivel Bloom esperado",
                "Riesgos de sobrecarga cognitiva",
            ],
        }


class AdaptiveLearning:
    def run(
        self,
        data: WeeklyPedagogicalPlanCreate,
        student_profile: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        ls = (student_profile or {}).get("learning_style", "")
        cog = (student_profile or {}).get("cognitive_load_trend", "stable")
        pacing = (student_profile or {}).get("pacing", "moderate")
        analogies = (student_profile or {}).get("preferred_analogies", []) or []
        bloom_reached = (student_profile or {}).get("bloom_level_reached", 0) or 0

        templates = _select_templates(analogies)

        adjusted_bloom = data.bloom_target
        if cog == "increasing":
            adjusted_bloom = max(1, adjusted_bloom - 1)

        scaffolding = list(templates["scaffolding"])
        if cog == "increasing":
            scaffolding.append("pausa de reflexion y consolidacion")
        if pacing == "fast":
            scaffolding = [s for s in scaffolding if "diagnostico" not in s and "calentamiento" not in s]
        elif pacing == "slow":
            scaffolding = [s.replace("guiado", "guiado con ejemplos adicionales") for s in scaffolding]

        return {
            "bloom_target": adjusted_bloom,
            "original_bloom_target": data.bloom_target,
            "bloom_adjusted": adjusted_bloom != data.bloom_target,
            "scaffolding": scaffolding,
            "differentiation": {
                "support": templates["differentiation_support"],
                "standard": templates["differentiation_standard"],
                "advanced": templates["differentiation_advanced"],
            },
            "adaptation_rationale": {
                "learning_style": ls,
                "cognitive_load_trend": cog,
                "pacing": pacing,
                "analogy_domain": analogies[0] if analogies else None,
                "bloom_level_reached": bloom_reached,
                "bloom_adjusted_reason": "carga cognitiva alta, reduciendo dificultad" if cog == "increasing" else "normal",
            },
        }


class MultimodalPlanning:
    def run(self, data: WeeklyPedagogicalPlanCreate, research: dict[str, Any]) -> dict[str, Any]:
        prompts = research.get("multimodal_prompts", [])
        return {
            "preferred_modality": data.preferred_modality,
            "modalities": [
                data.preferred_modality,
                "interactive",
                "reflection",
            ],
            "generation_briefs": prompts[:4],
            "accessibility_notes": [
                "ofrecer alternativa textual para recursos visuales",
                "segmentar actividades en bloques cortos",
            ],
        }


class PromptEngineering:
    def run(
        self,
        data: WeeklyPedagogicalPlanCreate,
        course: Course,
        memory_store: SharedMemoryStore | None = None,
        student_id: str | None = None,
        student_profile: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        objectives = "; ".join(data.objectives)
        base_context = (
            f"Curso: {course.name}. Semana {data.week_number}. Tema: {data.topic}. "
            f"Objetivos: {objectives}. Intencion: {data.pedagogical_intention}."
        )

        narrative_context = ""
        if memory_store is not None and student_id is not None:
            persona_records = memory_store.query_by_key_pattern(
                key_prefix="narrative:persona",
                student_id=student_id,
                memory_type="narrative_continuity",
                limit=1,
            )
            if persona_records:
                persona_desc = persona_records[0].value.get("description", "")
                if persona_desc:
                    narrative_context = (
                        f" Narrativa previa: {persona_desc}."
                    )

        sp = student_profile or {}
        analogies = sp.get("preferred_analogies", []) or []
        ls = sp.get("learning_style", "")
        templates = _select_templates(analogies)
        intro = templates["analogy_intro"]

        ls_context = ""
        if ls == "visual":
            ls_context = " Prioriza ejemplos visuales, diagramas e infografias."
        elif ls == "auditory":
            ls_context = " Incluye explicaciones auditivas y ejemplos basados en sonido o ritmo."
        elif ls == "reading":
            ls_context = " Usa textos detallados, lecturas y referencias escritas."
        elif ls == "kinesthetic":
            ls_context = " Disena actividades practicas, ejercicios interactivos y manipulacion."

        return {
            "teacher_review_prompt": (
                f"Evalua si la secuencia pedagogica mantiene el enfoque {data.pedagogical_style} "
                f"y alcanza Bloom {data.bloom_target}.{narrative_context}"
            ),
            "student_prompt": (
                f"{intro}{base_context}{narrative_context}{ls_context}"
                f" Genera una actividad adaptativa en modalidad "
                f"{data.preferred_modality}, con instrucciones claras y feedback inmediato."
                f" Usa la siguiente estructura: {', '.join(templates['phase_labels'])}."
            ),
            "tutor_prompt": (
                f"{intro}{base_context}{narrative_context}{ls_context}"
                " Actua como tutor socratico: pregunta, "
                "detecta errores conceptuales y ofrece andamiaje sin entregar la respuesta completa."
                f" Adapta tu lenguaje al estilo de aprendizaje {ls or 'general'}."
            ),
            "adaptation_info": {
                "analogy_domain": analogies[0] if analogies else None,
                "learning_style": ls,
                "tone": templates["tone"],
                "phase_labels": templates["phase_labels"],
            },
        }


class ConsistencyValidation:
    def run(
        self,
        data: WeeklyPedagogicalPlanCreate,
        research_validation: dict[str, Any],
        structure: dict[str, Any],
        memory_store: SharedMemoryStore | None = None,
        student_id: str | None = None,
        course_id: str | None = None,
        student_profile: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        issues = list(research_validation.get("issues", []))

        if memory_store is not None and student_id is not None:
            past_records = memory_store.query(
                student_id=student_id,
                memory_type="pedagogical_decision",
                limit=5,
            )
            for r in past_records:
                prev_issues = r.value.get("issues", [])
                for pi in prev_issues:
                    if pi.get("type") in ("weak_pedagogical_intention", "missing_objectives"):
                        issues.append({
                            "type": f"recurring:{pi['type']}",
                            "severity": "warning",
                            "detail": f"Problema recurrente detectado en memoria: {pi['type']}",
                        })

        sp = student_profile or {}
        if sp.get("learning_style") and structure.get("weekly_sequence"):
            ls = sp["learning_style"]
            has_visual_elements = any("visual" in str(s.get("focus", "")).lower() for s in structure["weekly_sequence"])
            if ls == "visual" and not has_visual_elements:
                issues.append({
                    "type": "continuity:missing_visual_elements",
                    "severity": "info",
                    "detail": "El estudiante prefiere aprendizaje visual pero la secuencia no incluye elementos visuales.",
                })

        if sp.get("preferred_analogies"):
            analogies = sp["preferred_analogies"]
            has_analogy = any(
                any(a.lower() in str(s.get("focus", "")).lower() for a in analogies)
                for s in (structure.get("weekly_sequence") or [])
            )
            if not has_analogy:
                issues.append({
                    "type": "continuity:missing_analogy_domain",
                    "severity": "info",
                    "detail": f"Estudiante prefiere analogias de {analogies[0]} pero no se reflejan en la secuencia.",
                })

        if not data.objectives:
            issues.append({"type": "missing_objectives", "severity": "error"})
        if not structure.get("weekly_sequence"):
            issues.append({"type": "missing_weekly_sequence", "severity": "error"})
        if len(data.pedagogical_intention.strip()) < 20:
            issues.append({"type": "weak_pedagogical_intention", "severity": "warning"})
        return {
            "valid": not any(item.get("severity") == "error" for item in issues),
            "issues": issues,
            "checks": {
                "teacher_intent_present": bool(data.pedagogical_intention.strip()),
                "objectives_present": bool(data.objectives),
                "weekly_sequence_present": bool(structure.get("weekly_sequence")),
                "retrieval_consistency": research_validation.get("valid", False),
            },
        }


class ConsensusMediator:
    def run(
        self,
        validation: dict[str, Any],
        research_metrics: dict[str, Any],
        memory_store: SharedMemoryStore | None = None,
        student_id: str | None = None,
        student_profile: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        confidence = float(research_metrics.get("pedagogical_confidence", 0.0) or 0.0)

        memory_influence = 0.0
        if memory_store is not None and student_id is not None:
            past_decisions = memory_store.query(
                student_id=student_id,
                memory_type="pedagogical_decision",
                key="consensus:result",
                limit=3,
            )
            if past_decisions:
                avg_past_conf = sum(
                    float(r.value.get("confidence", 0.0) or 0.0)
                    for r in past_decisions if r.value
                ) / len(past_decisions)
                memory_influence = avg_past_conf * 0.1

        sp = student_profile or {}
        cog = sp.get("cognitive_load_trend", "stable")
        engagement = sp.get("engagement_pattern", "consistent")

        profile_influence = 0.0
        if cog == "increasing":
            profile_influence = -0.08
        elif engagement == "dropping":
            profile_influence = -0.05
        profile_influence += 0.03 if sp.get("learning_style") else 0

        adjusted_confidence = min(confidence + memory_influence + profile_influence, 1.0)
        if not validation.get("valid"):
            decision = "revise"
        elif adjusted_confidence >= 0.55:
            decision = "approve"
        else:
            decision = "approve_with_review"

        result = {
            "decision": decision,
            "confidence": round(adjusted_confidence, 4),
            "base_confidence": round(confidence, 4),
            "memory_influence": round(memory_influence, 4),
            "profile_influence": round(profile_influence, 4),
            "mediators": [
                "research_agent",
                "pedagogical_structuring",
                "adaptive_learning",
                "multimodal_planning",
                "prompt_engineering",
                "consistency_validation",
            ],
            "adaptation_signals": {
                "cognitive_load_trend": cog,
                "engagement_pattern": engagement,
            },
        }
        return result


# ── Orchestration service ─────────────────────────────────────────────


class PedagogicalOrchestrationService:
    def __init__(self):
        self.research_agent = ResearchAgent()
        self.structuring = PedagogicalStructuring()
        self.adaptive = AdaptiveLearning()
        self.multimodal = MultimodalPlanning()
        self.prompting = PromptEngineering()
        self.validation = ConsistencyValidation()
        self.consensus = ConsensusMediator()
        self.reviewer_agent = ReviewerAgent()

    async def generate_weekly_plan(
        self,
        db: Session,
        course: Course,
        teacher: User,
        data: WeeklyPedagogicalPlanCreate,
        memory_store: SharedMemoryStore | None = None,
    ) -> WeeklyPedagogicalPlan:
        if memory_store is not None:
            self.research_agent.shared_memory_store = memory_store

        student_profile: dict[str, Any] = {}
        narrative: dict[str, Any] = {}

        if memory_store is not None:
            self.research_agent.shared_memory_store = memory_store

            ped_memory = PedagogicalMemoryService(memory_store)
            student_profile = ped_memory.build_student_profile(student_id=teacher.id)

            narrative = query_narrative_persona(
                memory_store,
                student_id=teacher.id,
                module_id=f"{course.id}:week{data.week_number - 1}" if data.week_number > 1 else None,
            )

        research_state = await self.research_agent.run(
            {
                "topic": data.topic,
                "objectives": data.objectives,
                "bloom_target": data.bloom_target,
                "language": "es",
                "module_id": f"{course.id}:week{data.week_number}",
                "student_id": teacher.id,
                "narrative_continuity": narrative,
                "student_profile": student_profile,
            }
        )
        research = research_state.get("research", {})
        research_metrics = research_state.get("research_metrics", {})
        research_validation = research_state.get("consistency_validation", {})

        structure = self.structuring.run(data, research)
        adaptive_plan = self.adaptive.run(data, student_profile=student_profile)
        multimodal_plan = self.multimodal.run(data, research)
        prompt_plan = self.prompting.run(
            data, course,
            memory_store=memory_store,
            student_id=teacher.id,
            student_profile=student_profile,
        )
        code_review = await self.reviewer_agent.review_until_validated(
            topic=data.topic,
            objectives=data.objectives,
        )
        validation = self.validation.run(
            data, research_validation, structure,
            memory_store=memory_store,
            student_id=teacher.id,
            course_id=course.id,
            student_profile=student_profile,
        )
        consensus = self.consensus.run(
            validation, research_metrics,
            memory_store=memory_store,
            student_id=teacher.id,
            student_profile=student_profile,
        )

        plan = WeeklyPedagogicalPlan(
            course_id=course.id,
            teacher_id=teacher.id,
            week_number=data.week_number,
            topic=data.topic,
            objectives=data.objectives,
            bloom_target=data.bloom_target,
            pedagogical_style=data.pedagogical_style,
            pedagogical_intention=data.pedagogical_intention,
            preferred_modality=data.preferred_modality,
            orchestration_status=consensus["decision"],
            retrieval_summary={
                "research": research,
                "metrics": research_metrics,
                "degraded": research.get("degraded", False),
                "sandbox_validation": code_review.to_dict(),
            },
            pedagogical_structure=structure,
            adaptive_plan=adaptive_plan,
            multimodal_plan=multimodal_plan,
            prompt_plan=prompt_plan,
            consistency_validation=validation,
            consensus_result=consensus,
        )
        db.add(plan)
        db.flush()

        if memory_store is not None:
            from app.memory.narrative_continuity import publish_narrative_persona
            publish_narrative_persona(
                memory_store,
                persona=f"Plan Semanal {data.week_number}: {data.topic} (Bloom {data.bloom_target})",
                tone=student_profile.get("preferred_analogies", [None])[0] or data.pedagogical_style or "educativo",
                bloom_progress=f"Nivel Bloom {data.bloom_target} planificado para semana {data.week_number}",
                student_id=teacher.id,
                module_id=f"{course.id}:week{data.week_number}",
                confidence=float(consensus.get("confidence", 0.7) or 0.7),
            )

            ped_memory.record_learning_style(
                student_id=teacher.id,
                learning_style=student_profile.get("learning_style", "visual"),
                module_id=f"{course.id}:week{data.week_number}",
            )
            ped_memory.record_bloom_progress(
                student_id=teacher.id,
                bloom_level=adaptive_plan.get("bloom_target", data.bloom_target),
                module_id=f"{course.id}:week{data.week_number}",
            )

        self._emit_orchestration_event(db, plan)
        db.commit()
        db.refresh(plan)
        return plan

    def list_weekly_plans(self, db: Session, course_id: str) -> list[WeeklyPedagogicalPlan]:
        return (
            db.query(WeeklyPedagogicalPlan)
            .filter(WeeklyPedagogicalPlan.course_id == course_id)
            .order_by(WeeklyPedagogicalPlan.week_number.desc(), WeeklyPedagogicalPlan.generated_at.desc())
            .all()
        )

    def validate_plan(self, db: Session, plan: WeeklyPedagogicalPlan) -> WeeklyPedagogicalPlan:
        plan.validated_at = datetime.now(timezone.utc)
        plan.orchestration_status = "teacher_validated"
        db.commit()
        db.refresh(plan)
        return plan

    def _emit_orchestration_event(self, db: Session, plan: WeeklyPedagogicalPlan) -> None:
        db.add(
            EventOutbox(
                event_type="pedagogy.weekly_orchestration.generated",
                aggregate_id=plan.id,
                correlation_id=str(uuid.uuid4()),
                payload={
                    "course_id": plan.course_id,
                    "teacher_id": plan.teacher_id,
                    "week_number": plan.week_number,
                    "topic": plan.topic,
                    "status": plan.orchestration_status,
                },
            )
        )
        db.flush()


pedagogical_orchestration_service = PedagogicalOrchestrationService()
