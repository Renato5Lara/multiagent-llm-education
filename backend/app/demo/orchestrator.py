from __future__ import annotations

import asyncio
import os
import uuid
from dataclasses import dataclass
from typing import Any

import httpx

from app.agents.reviewer_agent import ReviewerAgent
from app.core.consensus import ConsensusEngine, ConsensusVote, VoteDecision
from app.core.trust import TrustSystem
from app.demo.events import DemoEventEmitter
from app.demo.memory import SQLiteSharedMemoryStore
from app.demo.synthetic import SyntheticGenerator, SyntheticModule, SyntheticStudent
from app.sandbox import SandboxRunner


OLLAMA_SEMAPHORE = asyncio.Semaphore(1)


@dataclass(frozen=True)
class DemoAgent:
    name: str
    role: str
    model: str | None = None


DEMO_AGENTS = [
    DemoAgent("pedagogical", "llm", "qwen2.5-coder:7b"),
    DemoAgent("mediator", "llm", "llama3.2:3b"),
    DemoAgent("adaptive", "heuristic"),
    DemoAgent("evaluation", "heuristic"),
    DemoAgent("risk", "heuristic"),
]


class SwarmDemoOrchestrator:
    """Runs the Level 1 visual swarm demo with sequential inference."""

    def __init__(self, store: SQLiteSharedMemoryStore, emitter: DemoEventEmitter):
        self.store = store
        self.emitter = emitter
        self.trust = TrustSystem(decay_rate=0.0, min_trust=0.2)
        self.consensus = ConsensusEngine(voters=[])
        self.reviewer = ReviewerAgent(
            sandbox=SandboxRunner(auto_build=os.getenv("SANDBOX_AUTO_BUILD", "0") == "1")
        )

    async def start(self, seed: int = 42) -> dict[str, Any]:
        generator = SyntheticGenerator(seed)
        student = generator.student()
        module = generator.module()
        session_id = f"demo-{uuid.uuid4().hex[:10]}"
        self.store.create_session(session_id, seed, student.to_dict(), module.to_dict())
        asyncio.create_task(self.run(session_id, student, module))
        return {
            "session_id": session_id,
            "seed": seed,
            "student": student.to_dict(),
            "module": module.to_dict(),
            "events_url": f"/api/swarm/demo/events/{session_id}",
            "replay_url": f"/api/swarm/demo/replay/{session_id}",
        }

    async def run(self, session_id: str, student: SyntheticStudent, module: SyntheticModule) -> None:
        await self._emit(session_id, "session.started", {
            "student": student.to_dict(),
            "module": module.to_dict(),
            "runtime": {
                "ollama_num_parallel": os.getenv("OLLAMA_NUM_PARALLEL", "1"),
                "ollama_max_loaded_models": os.getenv("OLLAMA_MAX_LOADED_MODELS", "1"),
                "semaphore": 1,
                "strategy": "1-2 real LLMs + heuristic voters",
            },
        })
        await self._sleep()

        await self._emit(session_id, "swarm.activated", {
            "agents": [agent.__dict__ for agent in DEMO_AGENTS],
            "hardware_policy": "single sequential inference; automatic heuristic fallback",
        })
        await self._sleep()

        retrieval_summary = await self._run_pedagogical_retrieval(session_id, student, module)
        sandbox_summary = await self._run_code_validation(session_id, module)

        votes: list[ConsensusVote] = []
        timeline: list[dict[str, Any]] = []
        for index, agent in enumerate(DEMO_AGENTS, start=1):
            await self._emit(session_id, "agent.thinking", {
                "agent": agent.name,
                "role": agent.role,
                "model": agent.model,
                "step": index,
            })
            vote, latency_ms, used_fallback = await self._vote(agent, student, module)
            votes.append(vote)

            provisional_decision, provisional_confidence = self.consensus._aggregate(votes)
            point = {
                "step": index,
                "agent": agent.name,
                "decision": provisional_decision.value,
                "confidence": round(provisional_confidence, 3),
                "approve": sum(1 for vote_item in votes if vote_item.decision == VoteDecision.APPROVE),
                "reject": sum(1 for vote_item in votes if vote_item.decision == VoteDecision.REJECT),
                "abstain": sum(1 for vote_item in votes if vote_item.decision == VoteDecision.ABSTAIN),
            }
            timeline.append(point)

            await self._emit(session_id, "vote.cast", {
                "agent": vote.voter_name,
                "decision": vote.decision.value,
                "confidence": vote.confidence,
                "reason": vote.reason,
                "evidence": vote.evidence,
                "latency_ms": latency_ms,
                "fallback": used_fallback,
            })

            memory = self.store.publish_memory(
                session_id=session_id,
                agent=vote.voter_name,
                key=f"vote:{vote.voter_name}:{module.module_id}",
                value={
                    "decision": vote.decision.value,
                    "reason": vote.reason,
                    "evidence": vote.evidence,
                },
                confidence=vote.confidence,
            )
            await self._emit(session_id, "memory.published", {
                "memory_id": memory.id,
                "agent": memory.agent,
                "key": memory.key,
                "value": memory.value,
                "confidence": memory.confidence,
            })

            self.trust.record_vote_outcome(
                voter_name=vote.voter_name,
                decision=vote.decision,
                confidence=vote.confidence,
                latency_ms=latency_ms,
                final_decision=provisional_decision,
            )
            await self._emit(session_id, "trust.updated", {
                "agent": vote.voter_name,
                "trust": self.trust.get_record(vote.voter_name).to_dict(),
                "all_trust": self.trust.get_snapshot(),
            })
            await self._emit(session_id, "consensus.updated", {
                "current": point,
                "timeline": timeline,
            })

            if used_fallback:
                await self._emit(session_id, "anomaly.detected", {
                    "agent": vote.voter_name,
                    "severity": "medium",
                    "signal": "llm_unavailable_or_invalid",
                    "resilience": "heuristic fallback vote used; session continues",
                })
            await self._sleep()

        final_decision, final_confidence = self.consensus._aggregate(votes)
        await self._emit(session_id, "session.completed", {
            "decision": final_decision.value,
            "confidence": round(final_confidence, 3),
            "research": retrieval_summary,
            "sandbox": sandbox_summary,
            "votes": [
                {
                    "agent": vote.voter_name,
                    "decision": vote.decision.value,
                    "confidence": vote.confidence,
                    "reason": vote.reason,
                    "evidence": vote.evidence,
                }
                for vote in votes
            ],
            "trust": self.trust.get_snapshot(),
            "replay": f"/api/swarm/demo/replay/{session_id}",
        })
        self.store.complete_session(session_id)

    async def _run_pedagogical_retrieval(
        self,
        session_id: str,
        student: SyntheticStudent,
        module: SyntheticModule,
    ) -> dict[str, Any]:
        topic = module.topic or module.title
        objectives = [
            "comprender recorrido",
            "comprender busqueda",
            "comprender insercion",
        ]
        queries = [
            {"id": "q1", "category": "conceptual", "query": f"{topic} explicacion introductoria arreglos programacion"},
            {"id": "q2", "category": "procedural", "query": f"{topic} recorrido busqueda insercion ejemplos codigo"},
            {"id": "q3", "category": "misconception", "query": f"{topic} errores comunes estudiantes arreglos indices"},
            {"id": "q4", "category": "application", "query": f"{topic} aplicaciones reales software estructuras de datos"},
            {"id": "q5", "category": "bloom", "query": f"{topic} progresion Bloom comprender aplicar analizar"},
            {"id": "q6", "category": "multimodal", "query": f"{topic} prompts multimodales diagramas simulacion codigo"},
        ]
        await self._emit(session_id, "retrieval:start", {
            "topic": topic,
            "teacher_objective": "Disenar una explicacion multimodal sobre arreglos en programacion",
            "objectives": objectives,
            "bloom_target": 3,
            "queries": queries,
            "narrative_step": "docente define objetivo; swarm inicia investigacion",
        })

        sources = [
            {
                "query_id": "q1",
                "title": "Array fundamentals for beginners",
                "domain": "cs50.harvard.edu",
                "url": "https://cs50.harvard.edu/x/notes/arrays",
                "score": 0.92,
                "confidence": 0.9,
                "category": "conceptual",
                "summary": "Un arreglo organiza valores por indice y permite recorrerlos con bucles.",
            },
            {
                "query_id": "q2",
                "title": "Linear search and insertion in arrays",
                "domain": "geeksforgeeks.org",
                "url": "https://www.geeksforgeeks.org/array-data-structure-guide/",
                "score": 0.84,
                "confidence": 0.82,
                "category": "procedural",
                "summary": "Busqueda lineal compara elemento por elemento; insertar puede requerir desplazar posiciones.",
            },
            {
                "query_id": "q3",
                "title": "Common array indexing mistakes",
                "domain": "developer.mozilla.org",
                "url": "https://developer.mozilla.org/en-US/docs/Learn/JavaScript/First_steps/Arrays",
                "score": 0.88,
                "confidence": 0.86,
                "category": "misconception",
                "summary": "La confusion entre indice y posicion humana produce errores off-by-one.",
            },
            {
                "query_id": "q4",
                "title": "Arrays in real systems",
                "domain": "oracle.com",
                "url": "https://docs.oracle.com/javase/tutorial/java/nutsandbolts/arrays.html",
                "score": 0.79,
                "confidence": 0.78,
                "category": "application",
                "summary": "Los arreglos se usan en buffers, tablas, procesamiento de datos y estructuras compuestas.",
            },
            {
                "query_id": "q5",
                "title": "Bloom-aligned programming tasks",
                "domain": "teachingcommons.stanford.edu",
                "url": "https://teachingcommons.stanford.edu/teaching-guides/foundations-course-design/theory-practice/blooms-taxonomy",
                "score": 0.81,
                "confidence": 0.8,
                "category": "bloom",
                "summary": "La progresion inicia recordando definiciones, luego explicando, aplicando y analizando casos.",
            },
            {
                "query_id": "q6",
                "title": "Visualizing array operations",
                "domain": "visualgo.net",
                "url": "https://visualgo.net/en/list",
                "score": 0.86,
                "confidence": 0.84,
                "category": "multimodal",
                "summary": "Las operaciones se comprenden mejor con movimiento de indices, resaltado y pasos discretos.",
            },
        ]

        for index, source in enumerate(sources, start=1):
            await self._emit(session_id, "retrieval:source", {
                **source,
                "rank": index,
                "grounded_objectives": objectives[:2] if index <= 3 else objectives[1:],
            })
            if source["category"] == "misconception":
                await self._emit(session_id, "misconception:detected", {
                    "misconception": "Confundir indice base cero con posicion ordinal del estudiante.",
                    "impact": "Provoca recorridos incompletos, IndexError y busquedas que omiten el primer o ultimo elemento.",
                    "remediation": "Usar una tabla indice-valor y pedir prediccion antes de ejecutar el bucle.",
                    "confidence": 0.86,
                    "source_url": source["url"],
                })
            await self._sleep()

        contradiction = {
            "claim_a": "Insertar en un arreglo siempre es O(1).",
            "claim_b": "Insertar en medio de un arreglo requiere desplazar elementos y puede ser O(n).",
            "resolution": "La afirmacion O(1) solo aplica al final cuando hay capacidad disponible; la explicacion pedagogica debe explicitar el caso.",
            "severity": "medium",
            "confidence": 0.77,
            "sources": [sources[1]["url"], sources[3]["url"]],
        }
        await self._emit(session_id, "contradiction:detected", contradiction)

        prompts = [
            {
                "id": "prompt-visual-array-map",
                "modality": "visual",
                "bloom_level": 2,
                "prompt": "Muestra una tabla indice-valor y anima el recorrido desde i=0 hasta i=n-1.",
                "grounded_sources": [sources[0]["url"], sources[2]["url"]],
                "grounding_score": 0.94,
            },
            {
                "id": "prompt-code-linear-search",
                "modality": "code",
                "bloom_level": 3,
                "prompt": "Genera codigo de busqueda lineal y pide predecir el indice retornado antes de ejecutarlo.",
                "grounded_sources": [sources[1]["url"]],
                "grounding_score": 0.89,
            },
            {
                "id": "prompt-interactive-insertion",
                "modality": "interactive",
                "bloom_level": 3,
                "prompt": "Permite insertar un valor en una posicion y visualizar cada desplazamiento.",
                "grounded_sources": [sources[1]["url"], sources[5]["url"]],
                "grounding_score": 0.91,
            },
            {
                "id": "prompt-reflection-complexity",
                "modality": "reflection",
                "bloom_level": 4,
                "prompt": "Compara insertar al final vs insertar en medio y justifica la complejidad.",
                "grounded_sources": [sources[1]["url"], sources[4]["url"]],
                "grounding_score": 0.87,
            },
        ]
        for prompt in prompts:
            await self._emit(session_id, "prompt:generated", prompt)

        summary = {
            "topic": topic,
            "retrieval_confidence": 0.84,
            "pedagogical_confidence": 0.88,
            "diversity_score": 1.0,
            "contradiction_score": 0.83,
            "prompt_grounding_score": 0.9,
            "misconception_coverage": 0.75,
            "bloom_alignment_score": 0.92,
            "source_count": len(sources),
            "unique_domains": len({source["domain"] for source in sources}),
            "bloom_progression": [
                {"level": 1, "label": "Recordar", "activity": "Identificar indice, valor y longitud", "status": "grounded"},
                {"level": 2, "label": "Comprender", "activity": "Explicar recorrido paso a paso", "status": "grounded"},
                {"level": 3, "label": "Aplicar", "activity": "Implementar busqueda e insercion", "status": "target"},
                {"level": 4, "label": "Analizar", "activity": "Comparar costos segun posicion", "status": "extension"},
            ],
            "pedagogical_structure": [
                {"phase": "Activacion", "goal": "Conectar arreglos con listas cotidianas", "load": "low"},
                {"phase": "Conceptualizacion", "goal": "Indice, valor, longitud y recorrido", "load": "medium"},
                {"phase": "Practica guiada", "goal": "Busqueda lineal con prediccion", "load": "medium"},
                {"phase": "Transferencia", "goal": "Insercion y aplicaciones reales", "load": "medium"},
                {"phase": "Metacognicion", "goal": "Detectar off-by-one y complejidad", "load": "low"},
            ],
            "multimodal_plan": prompts,
        }
        await self._emit(session_id, "retrieval:complete", summary)

        memory = self.store.publish_memory(
            session_id=session_id,
            agent="research",
            key=f"research:{module.module_id}:grounding",
            value={
                "topic": topic,
                "metrics": summary,
                "continuity": "sources, misconceptions and prompts are available to downstream agents",
            },
            confidence=summary["pedagogical_confidence"],
        )
        await self._emit(session_id, "memory.published", {
            "memory_id": memory.id,
            "agent": memory.agent,
            "key": memory.key,
            "value": memory.value,
            "confidence": memory.confidence,
        })

        await self._emit(session_id, "consistency:validated", {
            "status": "validated",
            "continuity_score": 0.91,
            "memory_coherence": 0.88,
            "narrative_consistency": 0.9,
            "issues": [
                {
                    "type": "resolved_contradiction",
                    "detail": contradiction["resolution"],
                    "severity": "info",
                }
            ],
            "shared_memory_keys": [memory.key],
            "next_step": "agentes deliberan usando investigacion y memoria compartida",
        })
        return summary

    async def _run_code_validation(self, session_id: str, module: SyntheticModule) -> dict[str, Any]:
        topic = module.topic or module.title
        objectives = [
            "comprender recorrido",
            "comprender busqueda",
            "comprender insercion",
        ]
        await self._emit(session_id, "sandbox:start", {
            "agent": "reviewer",
            "phase": "code_verification",
            "topic": topic,
            "objectives": objectives,
            "limits": {"timeout_seconds": 10, "memory_mb": 512},
            "narrative_step": "ReviewerAgent verifica codigo educativo en Python REPL Sandbox",
        })
        review = await self.reviewer.review_until_validated(topic=topic, objectives=objectives)
        latest = review.iterations[-1].sandbox_result if review.iterations else None
        payload = {
            "agent": "reviewer",
            "phase": "code_verification",
            "approved": review.approved,
            "iterations": len(review.iterations),
            "final_feedback": review.final_feedback,
            "status": latest.status.value if latest else "not_executed",
            "success": latest.success if latest else False,
            "confidence": 0.93 if review.approved else 0.42,
            "sandbox_result": latest.to_replay_payload() if latest else {},
            "code_preview": review.final_code[:1000],
        }
        await self._emit(session_id, "sandbox:complete", payload)
        memory = self.store.publish_memory(
            session_id=session_id,
            agent="reviewer",
            key=f"sandbox:{module.module_id}:code_validation",
            value=payload,
            confidence=payload["confidence"],
        )
        await self._emit(session_id, "memory.published", {
            "memory_id": memory.id,
            "agent": memory.agent,
            "key": memory.key,
            "value": memory.value,
            "confidence": memory.confidence,
        })
        return payload

    async def _vote(
        self,
        agent: DemoAgent,
        student: SyntheticStudent,
        module: SyntheticModule,
    ) -> tuple[ConsensusVote, float, bool]:
        start = asyncio.get_running_loop().time()
        fallback = False
        if agent.role == "llm" and agent.model:
            try:
                vote = await self._llm_vote(agent, student, module)
            except Exception as exc:
                fallback = True
                vote = self._heuristic_vote(agent.name, student, module, str(exc))
        else:
            vote = self._heuristic_vote(agent.name, student, module)
        latency_ms = round((asyncio.get_running_loop().time() - start) * 1000, 2)
        return vote, latency_ms, fallback

    async def _llm_vote(
        self,
        agent: DemoAgent,
        student: SyntheticStudent,
        module: SyntheticModule,
    ) -> ConsensusVote:
        prompt = (
            "Responde SOLO JSON con keys decision, confidence, reason, evidence. "
            "decision debe ser approve, reject o abstain. "
            f"Agente={agent.name}. Estudiante={student.to_dict()}. Modulo={module.to_dict()}."
        )
        async with OLLAMA_SEMAPHORE:
            async with httpx.AsyncClient(timeout=18) as client:
                response = await client.post(
                    "http://localhost:11434/api/generate",
                    json={
                        "model": agent.model,
                        "prompt": prompt,
                        "stream": False,
                        "options": {"temperature": 0.1, "num_predict": 180},
                    },
                )
                response.raise_for_status()
                raw = response.json().get("response", "{}")

        import json

        data = json.loads(raw[raw.find("{"): raw.rfind("}") + 1])
        decision = VoteDecision(data.get("decision", "abstain"))
        confidence = float(data.get("confidence", 0.5))
        return ConsensusVote(
            voter_name=agent.name,
            decision=decision,
            confidence=max(0.0, min(1.0, confidence)),
            reason=str(data.get("reason", "LLM vote")),
            evidence=data.get("evidence", {"model": agent.model}),
        )

    def _heuristic_vote(
        self,
        agent: str,
        student: SyntheticStudent,
        module: SyntheticModule,
        fallback_reason: str | None = None,
    ) -> ConsensusVote:
        readiness = (student.mastery * 0.45) + (student.motivation * 0.2) + (module.assessment_score * 0.35)
        if agent == "risk":
            confidence = round(max(student.risk, module.prerequisite_gap), 2)
            decision = VoteDecision.REJECT if confidence > 0.38 else VoteDecision.ABSTAIN
            reason = "Risk gate detected prerequisite or academic risk pressure"
        elif agent == "evaluation":
            confidence = round(module.assessment_score, 2)
            decision = VoteDecision.APPROVE if confidence >= 0.6 else VoteDecision.REJECT
            reason = "Evaluation heuristic compared assessment score against mastery threshold"
        elif agent == "adaptive":
            confidence = round(readiness, 2)
            decision = VoteDecision.APPROVE if readiness >= 0.57 else VoteDecision.ABSTAIN
            reason = "Adaptive heuristic estimated readiness from mastery, motivation and score"
        elif agent == "mediator":
            confidence = round(0.54 + (student.motivation * 0.18), 2)
            decision = VoteDecision.ABSTAIN if module.prerequisite_gap > 0.32 else VoteDecision.APPROVE
            reason = "Mediator fallback balanced learning pace against prerequisite gap"
        else:
            confidence = round(readiness, 2)
            decision = VoteDecision.APPROVE if readiness >= 0.58 else VoteDecision.REJECT
            reason = "Pedagogical fallback estimated concept readiness"

        evidence = {
            "student_mastery": student.mastery,
            "motivation": student.motivation,
            "risk": student.risk,
            "module_difficulty": module.difficulty,
            "prerequisite_gap": module.prerequisite_gap,
            "assessment_score": module.assessment_score,
        }
        if fallback_reason:
            evidence["fallback_reason"] = fallback_reason[:240]
        return ConsensusVote(agent, decision, max(0.0, min(1.0, confidence)), reason, evidence)

    async def _emit(self, session_id: str, event_type: str, payload: dict[str, Any]) -> None:
        await self.emitter.emit(session_id, event_type, payload)

    async def _sleep(self) -> None:
        await asyncio.sleep(float(os.getenv("SWARM_DEMO_STEP_DELAY", "0.75")))
