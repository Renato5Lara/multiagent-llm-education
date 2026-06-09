"""Pedagogical ResearchAgent for grounded educational content generation."""

from __future__ import annotations

import logging
from typing import Any

from app.integrations.tavily.retrieval import PedagogicalRetrievalStrategy
from app.integrations.tavily.schemas import AggregatedResearch, RetrievalContext

logger = logging.getLogger(__name__)


class ResearchAgent:
    """Runs retrieval, consolidation, consistency validation, and prompt enrichment."""

    def __init__(self, retrieval_strategy: PedagogicalRetrievalStrategy | None = None, shared_memory_store: Any | None = None):
        self.retrieval_strategy = retrieval_strategy or PedagogicalRetrievalStrategy()
        self.shared_memory_store = shared_memory_store

    async def analyze(self, state: dict[str, Any]) -> dict[str, Any]:
        student_profile = state.get("student_profile") or {}

        context = RetrievalContext(
            topic=str(state.get("topic") or ""),
            objectives=list(state.get("objectives") or []),
            bloom_target=int(state.get("bloom_target") or 3),
            language=str(state.get("language") or "es"),
            learning_style=str(student_profile.get("learning_style", "")),
            preferred_analogies=list(student_profile.get("preferred_analogies", [])),
        )
        research = await self.retrieval_strategy.research(
            context,
            cache_only=bool(state.get("cache_only", False)),
        )
        validation = self._validate_consistency(research, context)
        memory_ids = self._publish_memory(research, state)
        return {
            **state,
            "research": research.to_dict(),
            "research_metrics": research.compute_pedagogical_metrics(context.bloom_target).to_dict(),
            "consistency_validation": validation,
            "memory_ids": memory_ids,
            "consensus_payload": self._build_consensus_payload(research, validation),
        }

    async def run(self, state: dict[str, Any]) -> dict[str, Any]:
        return await self.analyze(state)

    def _validate_consistency(self, research: AggregatedResearch, context: RetrievalContext) -> dict[str, Any]:
        metrics = research.compute_pedagogical_metrics(context.bloom_target)
        issues: list[dict[str, Any]] = []
        if metrics.retrieval_confidence < 0.45:
            issues.append({"type": "low_retrieval_confidence", "severity": "warning"})
        if metrics.diversity_score < 0.35 and research.total_sources >= 3:
            issues.append({"type": "low_source_diversity", "severity": "warning"})
        if metrics.contradiction_count:
            issues.append({"type": "contradictory_sources", "severity": "warning", "count": metrics.contradiction_count})
        if metrics.misconception_coverage < 0.5:
            issues.append({"type": "weak_misconception_coverage", "severity": "info"})
        if metrics.bloom_alignment_score < 0.5:
            issues.append({"type": "bloom_alignment_gap", "severity": "warning"})
        if metrics.prompt_grounding_score < 0.75:
            issues.append({"type": "weak_prompt_grounding", "severity": "warning"})
        if metrics.cognitive_load_score > 0.7:
            issues.append({"type": "cognitive_overload", "severity": "warning"})
        return {
            "valid": not any(issue["severity"] == "warning" for issue in issues),
            "issues": issues,
            "metrics": metrics.to_dict(),
        }

    def _publish_memory(self, research: AggregatedResearch, state: dict[str, Any]) -> list[str]:
        if self.shared_memory_store is None:
            return []
        ids: list[str] = []
        payloads = {
            "research:summary": {
                "topic": research.topic,
                "confidence": research.confidence_score,
                "total_sources": research.total_sources,
                "unique_domains": research.unique_domains,
            },
            "research:metrics": research.metrics.to_dict(),
            "research:misconceptions": {"items": research.misconceptions[:5]},
        }
        if state.get("student_profile"):
            payloads["research:student_profile"] = {
                k: v for k, v in (state.get("student_profile") or {}).items()
                if k in ("learning_style", "preferred_analogies", "preferred_modality", "pacing", "cognitive_load_trend")
            }
        for key, value in payloads.items():
            try:
                record_id = self.shared_memory_store.publish_observation_sync(
                    voter_name="research_agent",
                    key=key,
                    value=value,
                    confidence=research.confidence_score,
                    student_id=state.get("student_id"),
                    module_id=state.get("module_id"),
                    memory_type="research",
                )
                if record_id:
                    ids.append(record_id)
            except AttributeError:
                pass
            except Exception as exc:
                logger.warning("_publish_memory: write failed key=%s: %s", key, exc)
        return ids

    def _build_consensus_payload(self, research: AggregatedResearch, validation: dict[str, Any]) -> dict[str, Any]:
        metrics = research.metrics
        confidence = min(metrics.retrieval_confidence, metrics.pedagogical_confidence)
        decision = "approve" if validation["valid"] and confidence >= 0.55 else "abstain"
        if metrics.contradiction_score < 0.75 or metrics.retrieval_confidence < 0.25:
            decision = "reject"
        return {
            "voter_name": "research_agent",
            "decision": decision,
            "confidence": round(confidence, 4),
            "evidence": {
                "metrics": metrics.to_dict(),
                "source_count": research.total_sources,
                "contradictions": research.contradictions[:3],
            },
        }
