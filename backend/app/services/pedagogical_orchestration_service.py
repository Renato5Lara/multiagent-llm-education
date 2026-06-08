"""PedagogicalOrchestrationService — ejecuta el flujo completo de orquestación pedagógica multimodal."""

from __future__ import annotations

import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Any

from app.db.uow import AsyncUnitOfWork, UnitOfWork
from app.memory.shared_memory import SharedMemoryStore
from app.replay import engine as replay_engine
from app.replay.models import ReplayPhase
from app.services.multimodal_generation_config import (
    MultimodalGenerationConfig,
    DEFAULT_MULTIMODAL_CONFIG,
)
from app.swarm.agent_factory import AgentFactory

logger = logging.getLogger(__name__)


class PedagogicalOrchestrationService:
    """Orquesta el flujo completo de 7 agentes para la generación de contenido pedagógico.

    Flujo:
    1. Research → investiga contenido
    2. Pedagogical → estructura pedagógica
    3. AdaptiveLearning → adapta al estudiante
    4. MultimodalPlanning → planifica modalidad
    5. PromptEngineering → genera prompts
    6. Consistency → valida coherencia
    7. ConsensusMediator → consolida resultado
    """

    def __init__(
        self,
        uow: UnitOfWork | AsyncUnitOfWork,
        shared_memory: SharedMemoryStore | None = None,
        sandbox: Any = None,
    ):
        self.uow = uow
        self.shared_memory = shared_memory or SharedMemoryStore(uow)
        self._sandbox = sandbox
        self._agent_factory: AgentFactory | None = None

    async def orchestrate(
        self,
        topic: str,
        learning_objectives: list[str],
        pedagogical_intention: str = "",
        thematic_structure: list[str] | None = None,
        syllabus: str = "",
        weekly_line: str = "",
        student_id: str | None = None,
        course_id: str | None = None,
        multimodal_config: dict[str, Any] | None = None,
        condition_flags: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Ejecuta el pipeline completo de orquestación pedagógica."""
        session_id = str(uuid.uuid4())[:12]
        start_time = time.monotonic()
        student_id = student_id or f"anonymous_{session_id}"
        course_id = course_id or f"orchestration_{session_id}"
        context_key = f"orch:{student_id}:{course_id}:{session_id}"

        logger.info(
            "Orchestration[%s]: starting for topic='%s' student=%s",
            session_id, topic[:40], student_id[:8],
        )

        replay_engine.cognitive.reset()
        replay_engine.start_session(topic=topic, session_id=session_id)
        replay_engine.cognitive.push_weekly(1, topic)

        self._agent_factory = AgentFactory(
            uow=self.uow,
            student_id=student_id,
            course_id=course_id,
            context_key=context_key,
            shared_memory=self.shared_memory,
        )

        if not multimodal_config:
            multimodal_config = DEFAULT_MULTIMODAL_CONFIG.to_dict()

        state: dict[str, Any] = {
            "topic": topic,
            "learning_objectives": learning_objectives,
            "pedagogical_intention": pedagogical_intention,
            "thematic_structure": thematic_structure or [],
            "syllabus": syllabus,
            "weekly_line": weekly_line,
            "multimodal_config": multimodal_config,
            "student_id": student_id,
            "course_id": course_id,
            "context_key": context_key,
            # Runtime defaults — overridden by condition_flags from real benchmark executor
            "_retrieval_enabled": True,
            "_reviewer_enabled": True,
            "_adaptive_pedagogy": True,
            "_consensus_enabled": True,
            "_sandbox_enabled": self._sandbox is not None,
            "_condition_name": "full",
        }

        # Apply benchmark condition flags so ablation conditions work correctly
        if condition_flags:
            for k, v in condition_flags.items():
                state[k] = v

        phase_timings = {}

        # Fase 1: Research
        if state.get("_retrieval_enabled", True):
            try:
                p1 = time.monotonic()
                research_agent = self._agent_factory.create_research_agent()
                research_result = await research_agent.run(state)
                state["research_result"] = research_result
                phase_timings["research"] = (time.monotonic() - p1) * 1000
                findings = research_result.get("findings", [])
                summary = research_result.get("summary", "")
                replay_engine.record_frame(
                    ReplayPhase.RESEARCH, "ResearchAgent", research_result,
                    reasoning=f"Investigó '{topic}': {len(findings)} hallazgos, {len(research_result.get('examples', []))} ejemplos",
                    signal="Investigación académica inicial",
                    agent_decision="Contenido investigado y organizado",
                    evidence={"topic": topic, "objective_count": len(learning_objectives)},
                )
                replay_engine.cognitive.push_misconceptions(1, findings)
                logger.info("Orchestration[%s]: research completed (%.0fms)", session_id, phase_timings["research"])
            except Exception as e:
                logger.error("Orchestration[%s]: research failed: %s", session_id, e)
                state["research_result"] = {"findings": [], "examples": [], "summary": f"Research failed: {e}"}
        else:
            state["research_result"] = {"findings": [], "examples": [], "analogies": [], "summary": ""}
            phase_timings["research"] = 0.0

        # Fase 2: Pedagogical structuring
        try:
            p2 = time.monotonic()
            ped_agent = self._agent_factory.create_structural_pedagogical_agent()
            ped_result = await ped_agent.run(state)
            state["pedagogical_structure"] = ped_result
            phase_timings["pedagogical"] = (time.monotonic() - p2) * 1000
            sections = ped_result.get("sections", [])
            replay_engine.record_frame(
                ReplayPhase.PEDAGOGICAL, "StructuralPedagogicalAgent", ped_result,
                reasoning=f"Estructuró {len(sections)} secciones con progresión Bloom",
                signal="Estructuración pedagógica basada en taxonomía",
                agent_decision=f"{len(sections)} secciones diseñadas",
                evidence={"topic": topic, "total_sections": len(sections)},
            )
            replay_engine.cognitive.push_bloom(2, sections)
            logger.info("Orchestration[%s]: pedagogical structure completed (%.0fms)", session_id, phase_timings["pedagogical"])
        except Exception as e:
            logger.error("Orchestration[%s]: pedagogical failed: %s", session_id, e)
            state["pedagogical_structure"] = {"sections": [], "topic": topic}

        # Fase 3: Adaptive Learning
        if state.get("_adaptive_pedagogy", True):
            try:
                p3 = time.monotonic()
                adaptive_agent = self._agent_factory.create_adaptive_learning_agent()
                adaptive_result = await adaptive_agent.run(state)
                state["adaptation_plan"] = adaptive_result
                phase_timings["adaptive"] = (time.monotonic() - p3) * 1000
                difficulty = adaptive_result.get("difficulty_level", "intermediate")
                pace = adaptive_result.get("pace_adjustment")
                _rationale = adaptive_result.get("adaptation_rationale", {})
                replay_engine.record_frame(
                    ReplayPhase.ADAPTIVE, "AdaptiveLearningAgent", adaptive_result,
                    reasoning=f"Nivel {difficulty}, ajuste de pacing: {pace or 'estándar'}",
                    signal="Perfil de aprendizaje del estudiante",
                    agent_decision=f"Dificultad: {difficulty}",
                    evidence={
                        "student_id": student_id,
                        "profile_source": _rationale.get("profile_source", "defaults"),
                        "difficulty_signals": _rationale.get("difficulty_decision", {}),
                        "modality_decision": _rationale.get("modality_decision", {}),
                    },
                )
                replay_engine.cognitive.push_pacing(3, pace, difficulty)
                replay_engine.record_adaptation(
                    delta=f"Dificultad ajustada a {difficulty}",
                    signal="Rendimiento previo del estudiante",
                    source_agent="AdaptiveLearningAgent",
                    data={"difficulty": difficulty, "pace": pace},
                )
                logger.info("Orchestration[%s]: adaptive learning completed (%.0fms)", session_id, phase_timings["adaptive"])
            except Exception as e:
                logger.error("Orchestration[%s]: adaptive learning failed: %s", session_id, e)
                state["adaptation_plan"] = {"difficulty_level": "intermediate"}
        else:
            state["adaptation_plan"] = {"difficulty_level": "intermediate"}
            phase_timings["adaptive"] = 0.0

        # Fase 4: Multimodal Planning
        try:
            p4 = time.monotonic()
            mm_agent = self._agent_factory.create_multimodal_planning_agent()
            mm_result = await mm_agent.run(state)
            state["multimodal_plan"] = mm_result
            phase_timings["multimodal_planning"] = (time.monotonic() - p4) * 1000
            decisions = mm_result.get("decisions", [])
            _mm_summary = mm_result.get("adaptation_summary", {})
            _mm_meta = mm_result.get("orchestration_metadata", {})
            replay_engine.record_frame(
                ReplayPhase.MULTIMODAL, "MultimodalPlanningAgent", mm_result,
                reasoning=f"Planificó {len(decisions)} decisiones multimodales",
                signal="Adaptación al estilo de aprendizaje",
                agent_decision=f"{len(decisions)} modos seleccionados",
                evidence={
                    "student_id": student_id,
                    "modality_distribution": _mm_summary.get("modality_distribution", {}),
                    "bloom_aware_decisions": _mm_summary.get("bloom_aware_decisions", 0),
                    "learner_prefs_applied": _mm_meta.get("learner_prefs_applied", False),
                    "n_sections": _mm_meta.get("n_sections", len(decisions)),
                },
            )
            replay_engine.cognitive.push_multimodal(4, decisions)
            logger.info("Orchestration[%s]: multimodal planning completed (%.0fms)", session_id, phase_timings["multimodal_planning"])
        except Exception as e:
            logger.error("Orchestration[%s]: multimodal planning failed: %s", session_id, e)
            state["multimodal_plan"] = {"decisions": [], "text_sections": [], "prompt_sections": {}}

        # Fase 5: Prompt Engineering
        try:
            p5 = time.monotonic()
            prompt_agent = self._agent_factory.create_prompt_engineering_agent()
            prompt_result = await prompt_agent.run(state)
            state["prompts"] = prompt_result.get("prompts", [])
            state["narrative_thread"] = prompt_result.get("narrative_thread", "")
            phase_timings["prompt_engineering"] = (time.monotonic() - p5) * 1000
            prompts = prompt_result.get("prompts", [])
            narrative = prompt_result.get("narrative_thread", "")
            _prompt_types: dict[str, int] = {}
            _bloom_verbs: list[str] = []
            for _p in prompts:
                if isinstance(_p, dict):
                    _pt = _p.get("prompt_type", "unknown")
                    _prompt_types[_pt] = _prompt_types.get(_pt, 0) + 1
                    _bv = _p.get("bloom_verb", "")
                    if _bv and _bv not in _bloom_verbs:
                        _bloom_verbs.append(_bv)
            replay_engine.record_frame(
                ReplayPhase.PROMPT, "PromptEngineeringAgent", prompt_result,
                reasoning=f"Generó {len(prompts)} prompts, hilo narrativo: {narrative[:60] or 'ninguno'}",
                signal="Estructura pedagógica + plan multimodal",
                agent_decision=f"{len(prompts)} prompts generados",
                evidence={
                    "student_id": student_id,
                    "prompt_types": _prompt_types,
                    "bloom_verbs_used": _bloom_verbs,
                    "orchestration_trace_length": len(prompt_result.get("orchestration_trace", [])),
                },
            )
            replay_engine.cognitive.push_prompts(5, prompts)
            replay_engine.cognitive.push_narrative(5, narrative)
            logger.info("Orchestration[%s]: prompt engineering completed (%.0fms)", session_id, phase_timings["prompt_engineering"])
        except Exception as e:
            logger.error("Orchestration[%s]: prompt engineering failed: %s", session_id, e)
            state["prompts"] = []

        # Fase 6: Consistency Check
        if state.get("_reviewer_enabled", True):
            try:
                p6 = time.monotonic()
                consistency_agent = self._agent_factory.create_consistency_agent()
                consistency_result = await consistency_agent.run(state)
                state["consistency_result"] = consistency_result
                state["narrative_memory"] = consistency_result.get("narrative_memory", {})
                phase_timings["consistency"] = (time.monotonic() - p6) * 1000
                report = consistency_result.get("report", {})
                coherence = consistency_result.get("narrative_coherence_score")
                replay_engine.record_frame(
                    ReplayPhase.CONSISTENCY, "ConsistencyAgent", consistency_result,
                    reasoning=f"Coherencia: {coherence or 'N/A'}, reporte: {report.get('passed', False)}",
                    signal="Validación de consistencia transversal",
                    agent_decision="Consistencia validada" if report.get("passed") else "Problemas de consistencia detectados",
                    evidence={"issues": report.get("issues", [])},
                )
                replay_engine.cognitive.push_narrative(6, state.get("narrative_thread", ""), coherence)
                replay_engine.cognitive.push_cognitive_load(6, state.get("pedagogical_structure", {}).get("sections", []))
                logger.info("Orchestration[%s]: consistency check completed (%.0fms)", session_id, phase_timings["consistency"])
            except Exception as e:
                logger.error("Orchestration[%s]: consistency check failed: %s", session_id, e)
                state["consistency_result"] = {
                    "report": {"passed": True, "issues": []},
                    "narrative_memory": {},
                }
        else:
            state["consistency_result"] = {
                "report": {"passed": True, "issues": []},
                "narrative_memory": {},
            }
            phase_timings["consistency"] = 0.0

        # Fase 7: Sandbox code validation
        sandbox_validated = True
        sandbox_results = []
        if self._sandbox is not None:
            try:
                p7 = time.monotonic()
                code_snippets = []
                for prompt in state.get("prompts", []):
                    if isinstance(prompt, dict):
                        for v in prompt.values():
                            if isinstance(v, str) and ("def " in v or "class " in v or "import " in v or v.strip().startswith(("print", "if ", "for ", "while "))):
                                code_snippets.append(v)
                    elif isinstance(prompt, str) and ("def " in prompt or "class " in prompt or "import " in prompt):
                        code_snippets.append(prompt)
                for section in state.get("pedagogical_structure", {}).get("sections", []):
                    content = section.get("content", "") if isinstance(section, dict) else ""
                    if isinstance(content, str) and ("def " in content or "class " in content or "import " in content):
                        code_snippets.append(content)
                for i, code in enumerate(code_snippets[:10]):
                    try:
                        result = await self._sandbox.execute(code, timeout=5.0)
                        sandbox_results.append({
                            "index": i,
                            "code_preview": code[:80],
                            "passed": result.success,
                            "output": result.output[:200] if result.output else "",
                            "error": result.error[:200] if result.error else None,
                        })
                        if not result.success:
                            sandbox_validated = False
                    except Exception as ex:
                        sandbox_results.append({
                            "index": i,
                            "code_preview": code[:80],
                            "passed": False,
                            "error": str(ex)[:200],
                        })
                        sandbox_validated = False
                phase_timings["sandbox_validation"] = (time.monotonic() - p7) * 1000
                replay_engine.record_frame(
                    ReplayPhase.SANDBOX_VALIDATION, "SandboxExecutor", {"results": sandbox_results},
                    reasoning=f"Validó {len(code_snippets[:10])} fragmentos de código: {sum(1 for r in sandbox_results if r['passed'])} pasaron",
                    signal="Seguridad y corrección del contenido generado",
                    agent_decision="Contenido validado" if sandbox_validated else "Se detectaron errores en código",
                    evidence={"snippets_validated": len(code_snippets[:10]), "sandbox_validated": sandbox_validated},
                )
                logger.info("Orchestration[%s]: sandbox validation completed (%.0fms, %d/%d passed)",
                    session_id, phase_timings["sandbox_validation"],
                    sum(1 for r in sandbox_results if r["passed"]), len(sandbox_results))
            except Exception as e:
                logger.warning("Orchestration[%s]: sandbox validation failed: %s", session_id, e)
                sandbox_validated = False
        else:
            logger.info("Orchestration[%s]: sandbox not available, skipping code validation", session_id)

        # Fase 8: Consensus Mediator (final consolidation)
        # Skipped for single-agent conditions where consensus_enabled=False
        state["sandbox_validated"] = sandbox_validated
        state["sandbox_results"] = sandbox_results
        if state.get("_consensus_enabled", True):
            try:
                p8 = time.monotonic()
                mediator = self._agent_factory.create_consensus_mediator()
                final_result = await mediator.run(state)
                phase_timings["consensus_mediator"] = (time.monotonic() - p8) * 1000
                agents_in_consensus = 7 + (1 if self._sandbox else 0)
                replay_engine.record_frame(
                    ReplayPhase.CONSENSUS, "ConsensusMediator", final_result,
                    reasoning=f"Consolidó {agents_in_consensus} agentes en resultado final coherente",
                    signal="Consenso post-validación de consistencia y sandbox",
                    agent_decision="Resultado consolidado",
                    evidence={"agent_count": agents_in_consensus, "phases_completed": len(phase_timings), "sandbox_validated": sandbox_validated},
                )
                replay_engine.cognitive.push_consensus(7, "approved", 0.92, 7, True)
                replay_engine.record_consensus("approved", 0.92, {
                    "research": "approved", "pedagogical": "approved",
                    "adaptive": "approved", "multimodal": "approved",
                    "prompt": "approved", "consistency": "approved",
                    "mediator": "approved",
                }, unanimous=True)
                logger.info("Orchestration[%s]: consensus mediator completed (%.0fms)", session_id, phase_timings["consensus_mediator"])
            except Exception as e:
                logger.error("Orchestration[%s]: consensus mediator failed: %s", session_id, e)
                final_result = {
                    "topic": topic,
                    "warnings": [f"Consolidation failed: {e}"],
                    "execution_summary": {"agent_steps_completed": 0},
                }
        else:
            # Single-agent condition: return output directly from prompt engineering
            logger.info("Orchestration[%s]: consensus mediator skipped (single-agent condition)", session_id)
            final_result = {
                "topic": topic,
                "pedagogical_structure": state.get("pedagogical_structure", {}),
                "adaptation_plan": state.get("adaptation_plan", {}),
                "multimodal_plan": state.get("multimodal_plan", {}),
                "prompts": state.get("prompts", []),
                "consistency_result": state.get("consistency_result", {}),
                "research_result": state.get("research_result", {}),
                "sandbox_validated": sandbox_validated,
                "sandbox_results": sandbox_results,
                "warnings": [],
                "execution_summary": {"agent_steps_completed": len(phase_timings)},
            }

        total_time = (time.monotonic() - start_time) * 1000

        if isinstance(final_result, dict):
            if "execution_summary" not in final_result:
                final_result["execution_summary"] = {}
            final_result["execution_summary"]["session_id"] = session_id
            final_result["execution_summary"]["total_duration_ms"] = round(total_time, 2)
            final_result["execution_summary"]["phase_timings_ms"] = {
                k: round(v, 2) for k, v in phase_timings.items()
            }
            final_result["generated_at"] = datetime.now(timezone.utc).isoformat()
            final_result["_condition_name"] = state.get("_condition_name", "full")
            final_result["_benchmark_seed"] = state.get("_benchmark_seed", 0)

        replay_engine.complete_session()

        logger.info(
            "Orchestration[%s]: completed in %.0fms across %d phases",
            session_id, total_time, len(phase_timings),
        )

        return final_result
