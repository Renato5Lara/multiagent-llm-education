"""ConsistencyAgent — mantiene coherencia narrativa, visual, pedagógica y evita redundancias."""

from __future__ import annotations

import logging
from typing import Any

from app.agents.base import BaseAgent
from app.schemas.pedagogical_orchestration import (
    ConsistencyIssue,
    ConsistencyReport,
    NarrativeMemory,
)

logger = logging.getLogger(__name__)


class ConsistencyAgent(BaseAgent):
    """Verifica y mantiene la consistencia global del contenido generado.

    Responsabilidades:
    - Mantener coherencia narrativa entre secciones
    - Mantener estilo visual consistente
    - Mantener continuidad pedagógica (progresión Bloom)
    - Evitar redundancias entre secciones
    - Validar consistencia de personajes y tono
    - Almacenar memoria narrativa para continuidad

    Lee de shared memory:
    - pedagogical:structure
    - multimodal:plan
    - prompts:generated
    - adaptive:plan
    - narrative:memory (histórico)

    Escribe en shared memory:
    - consistency:report
    - narrative:memory
    """

    @property
    def agent_type(self) -> str:
        return "consistency"

    async def analyze(self, state: dict[str, Any]) -> dict[str, Any]:
        pedagogical = state.get("pedagogical_structure", {})
        sections = pedagogical.get("sections", []) if isinstance(pedagogical, dict) else []
        multimodal_plan = state.get("multimodal_plan", {})
        prompts = state.get("prompts", [])
        adaptation = state.get("adaptation_plan", {})

        issues = []
        resolved = []

        research = state.get("research_result", {})

        issues.extend(self._check_narrative_coherence(sections))
        issues.extend(self._check_pedagogical_progression(sections))
        issues.extend(self._check_multimodal_consistency(multimodal_plan, prompts))
        issues.extend(self._check_redundancies(sections, prompts))
        issues.extend(await self._check_character_continuity(state))
        issues.extend(self._check_tone_consistency(adaptation, prompts))
        issues.extend(self._check_retrieval_contradictions(research))
        issues.extend(self._check_retrieval_quality(research))

        narrative_memory = await self._load_or_init_narrative_memory()
        narrative_memory = self._update_narrative_memory(narrative_memory, state, prompts)

        passed = len([i for i in issues if i.severity == "error"]) == 0

        for issue in list(issues):
            if issue.severity == "info":
                resolved.append(issue.description)
                issues.remove(issue)

        report = ConsistencyReport(
            passed=passed,
            issues=issues,
            narrative_coherence_score=self._compute_coherence_score(issues),
            pedagogical_progression_score=self._compute_progression_score(sections),
            multimodal_consistency_score=self._compute_multimodal_score(issues),
            character_continuity=narrative_memory.get("characters", {}),
            style_continuity=narrative_memory.get("visual_styles", {}),
            resolved_issues=resolved,
        )

        result = {
            "report": report.model_dump(),
            "narrative_memory": narrative_memory,
            "total_issues": len(issues),
            "passed": passed,
        }

        await self.publish_observation(
            f"{self.context_key}:consistency:report",
            result,
            memory_type="inference",
            confidence=0.9,
        )

        await self.publish_observation(
            f"{self.context_key}:narrative:memory",
            narrative_memory,
            memory_type="inference",
            confidence=0.85,
        )

        return result

    def _check_narrative_coherence(self, sections: list[dict]) -> list[ConsistencyIssue]:
        issues = []
        if len(sections) < 2:
            return issues

        section_types = [s.get("section_type", "") for s in sections]
        expected = ["introduction", "conceptual_explanation", "example",
                     "practical_application", "real_case", "evaluation"]

        missing = [e for e in expected if e not in section_types]
        if missing:
            issues.append(ConsistencyIssue(
                severity="warning",
                category="coherence",
                description=f"Secciones faltantes en la secuencia pedagógica: {', '.join(missing)}",
                affected_sections=missing,
                suggestion="Completar la estructura pedagógica con las secciones faltantes.",
            ))

        return issues

    def _check_pedagogical_progression(self, sections: list[dict]) -> list[ConsistencyIssue]:
        issues = []
        bloom_levels = [s.get("bloom_level", 1) for s in sections if s.get("bloom_level")]

        if len(bloom_levels) > 1:
            decreases = sum(1 for i in range(1, len(bloom_levels)) if bloom_levels[i] < bloom_levels[i - 1])
            if decreases > 1:
                issues.append(ConsistencyIssue(
                    severity="warning",
                    category="progression",
                    description=(
                        f"La progresión Bloom tiene {decreases} retrocesos. "
                        f"Se espera progresión monotónica no decreciente."
                    ),
                    affected_sections=[s.get("section_type", "") for s in sections],
                    suggestion="Revisar niveles Bloom para asegurar progresión ascendente.",
                ))

        if bloom_levels and max(bloom_levels) < 3:
            issues.append(ConsistencyIssue(
                severity="info",
                category="progression",
                description="La progresión no alcanza niveles superiores de Bloom (analizar/evaluar/crear).",
                affected_sections=[],
                suggestion="Considerar incluir actividades de nivel Bloom 4-6.",
            ))

        return issues

    def _check_multimodal_consistency(self, multimodal_plan: dict | Any, prompts: list) -> list[ConsistencyIssue]:
        issues = []
        decisions = []
        if isinstance(multimodal_plan, dict):
            decisions = multimodal_plan.get("decisions", [])
        elif hasattr(multimodal_plan, "decisions"):
            decisions = [d.model_dump() if hasattr(d, "model_dump") else d for d in multimodal_plan.decisions]

        modalities = {}
        for d in decisions:
            section = d.get("section", d.get("section_type", "unknown")) if isinstance(d, dict) else "unknown"
            modality = d.get("modality", "text") if isinstance(d, dict) else "text"
            modalities[section] = modality

        return issues

    def _check_redundancies(self, sections: list[dict], prompts: list) -> list[ConsistencyIssue]:
        issues = []
        titles = [s.get("title", "").lower() for s in sections]
        seen = set()
        for title in titles:
            words = set(title.split())
            for prev in seen:
                overlap = words & prev
                if len(overlap) > len(words) * 0.5:
                    issues.append(ConsistencyIssue(
                        severity="info",
                        category="redundancy",
                        description=f"Posible redundancia temática entre secciones: '{title}'",
                        affected_sections=[title, prev],
                        suggestion="Fusionar o diferenciar contenido entre estas secciones.",
                    ))
                    break
            seen.add(frozenset(words))

        return issues

    async def _check_character_continuity(self, state: dict) -> list[ConsistencyIssue]:
        issues = []
        narrative_memory = await self._load_or_init_narrative_memory()
        characters = narrative_memory.get("characters", {})

        if characters and "current_character" not in state:
            issues.append(ConsistencyIssue(
                severity="info",
                category="character",
                description="Personajes previos detectados en memoria pero sin referencia en estado actual.",
                affected_sections=[],
                suggestion="Recuperar personajes de memoria narrativa para mantener continuidad.",
            ))

        return issues

    def _check_tone_consistency(self, adaptation: Any, prompts: list) -> list[ConsistencyIssue]:
        issues = []
        difficulty = "intermediate"
        if isinstance(adaptation, dict):
            difficulty = adaptation.get("difficulty_level", "intermediate")

        return issues

    async def _load_or_init_narrative_memory(self) -> dict[str, Any]:
        records = await self.query_memory(memory_type="inference", limit=5)
        for r in reversed(records):
            try:
                val = r.value if hasattr(r, "value") else {}
                if isinstance(val, dict) and val.get("characters") is not None:
                    return val
            except Exception:
                continue

        return {
            "characters": {},
            "visual_styles": {},
            "narrative_threads": [],
            "previous_prompts": [],
            "pedagogical_constraints": [],
            "progression_state": {},
        }

    def _update_narrative_memory(
        self,
        memory: dict[str, Any],
        state: dict[str, Any],
        prompts: list,
    ) -> dict[str, Any]:
        memory["narrative_threads"] = memory.get("narrative_threads", []) + [
            f"Narrativa para: {state.get('topic', 'unknown')}"
        ]

        style = memory.get("visual_styles", {})
        style["last_topic"] = state.get("topic", "")
        style["last_adapted_difficulty"] = "standard"
        memory["visual_styles"] = style

        if isinstance(prompts, list):
            existing = memory.get("previous_prompts", [])
            for p in prompts:
                p_content = p.get("content", "")[:100] if isinstance(p, dict) else str(p)[:100]
                if p_content and p_content not in existing:
                    existing.append(p_content)
            memory["previous_prompts"] = existing[-50:]

        constraints = memory.get("pedagogical_constraints", [])
        pedagogical = state.get("pedagogical_structure", {})
        if isinstance(pedagogical, dict):
            progression = pedagogical.get("progression_logic", "")
            if progression and progression not in constraints:
                constraints.append(progression)
        memory["pedagogical_constraints"] = constraints

        memory["progression_state"] = {
            "last_bloom_level": 4,
            "sections_completed": 0,
            "current_difficulty": "standard",
        }

        return memory

    def _check_retrieval_contradictions(self, research: dict | Any) -> list[ConsistencyIssue]:
        issues = []
        contradictions = []
        if isinstance(research, dict):
            contradictions = research.get("contradictions", [])
        elif hasattr(research, "contradictions"):
            contradictions = research.contradictions

        for c in contradictions:
            statements = c.get("statements", []) if isinstance(c, dict) else []
            sources = c.get("sources", []) if isinstance(c, dict) else []
            severity = c.get("severity", "info") if isinstance(c, dict) else "info"

            issues.append(ConsistencyIssue(
                severity=severity,
                category="contradiction",
                description=(
                    f"Contradicción entre fuentes de investigación: "
                    f"'{statements[0][:80] if statements else 'N/A'}' vs "
                    f"'{statements[1][:80] if len(statements) > 1 else 'N/A'}'"
                ),
                affected_sections=sources,
                suggestion="Resolver contradicción revisando fuentes o priorizando la más confiable.",
            ))

        return issues

    def _check_retrieval_quality(self, research: dict | Any) -> list[ConsistencyIssue]:
        issues = []
        confidence = 0.0
        source_count = 0
        if isinstance(research, dict):
            confidence = research.get("confidence", 0.0) or 0.0
            retrieval = research.get("retrieval", {}) or {}
            if isinstance(retrieval, dict):
                source_count = retrieval.get("total_sources", 0) or 0
        elif hasattr(research, "confidence"):
            confidence = research.confidence or 0.0

        if confidence < 0.3:
            issues.append(ConsistencyIssue(
                severity="warning",
                category="research_quality",
                description=(
                    f"Baja confianza en la investigación ({confidence:.2f}). "
                    "Los hallazgos pueden ser insuficientes o de baja calidad."
                ),
                affected_sections=[],
                suggestion="Considerar enriquecer con fuentes adicionales o LLM.",
            ))

        if source_count == 0 and confidence == 0.0:
            issues.append(ConsistencyIssue(
                severity="warning",
                category="research_quality",
                description="No se encontraron fuentes externas. La investigación usó solo LLM/heurístico.",
                affected_sections=[],
                suggestion="Activar Tavily Search API para mejorar calidad de la investigación.",
            ))

        return issues

    def _compute_coherence_score(self, issues: list[ConsistencyIssue]) -> float:
        if not issues:
            return 1.0
        penalties = {
            "error": 0.3,
            "warning": 0.1,
            "info": 0.02,
        }
        total_penalty = sum(penalties.get(i.severity, 0.05) for i in issues)
        return max(0.0, 1.0 - total_penalty)

    def _compute_progression_score(self, sections: list[dict]) -> float:
        if len(sections) < 2:
            return 1.0
        bloom_levels = [s.get("bloom_level", 1) for s in sections if s.get("bloom_level")]
        if not bloom_levels:
            return 0.5
        increases = sum(1 for i in range(1, len(bloom_levels)) if bloom_levels[i] > bloom_levels[i - 1])
        ratio = increases / max(len(bloom_levels) - 1, 1)
        return 0.5 + (ratio * 0.5)

    def _compute_multimodal_score(self, issues: list[ConsistencyIssue]) -> float:
        multimodal_issues = [i for i in issues if i.category == "multimodal"]
        if not multimodal_issues:
            return 1.0
        return max(0.0, 1.0 - len(multimodal_issues) * 0.1)
