"""
TraceStore — async persistence and retrieval of agent decision traces.

Persistence uses its own independent AsyncSession (separate from the agent's
UoW), so trace records are written even when the main operation fails.

Retrieval reconstructs the causal chain from agent_decision_traces
ordered by sequence, and builds the UI-ready TraceChainResponse.

Thread-safe: one TraceStore instance is shared across the app (singleton).
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.decision_trace import (
    AgentDecisionTrace,
    ConsensusTrace,
    ConsensusVoteTrace,
    TraceChainResponse,
    TraceEdgeUI,
    TraceNodeUI,
)

logger = logging.getLogger(__name__)

# Edge labels that describe what each agent passes to the next
_AGENT_EDGE_LABELS: dict[str, str] = {
    "research_agent": "research findings → topic enrichment",
    "pedagogical_agent": "pedagogical structure → learning plan",
    "adaptive_learning_agent": "adaptation plan → difficulty/bloom",
    "structural_pedagogical_agent": "section plan → content spec",
    "multimodal_planning_agent": "modality decisions → prompt config",
    "prompt_engineering_agent": "generated prompts → content",
    "consistency_agent": "consistency report → final output",
    "consensus_mediator": "consensus decision → pipeline gate",
}


class TraceStore:
    """Persists and retrieves AgentDecisionTrace records.

    Usage:
        store = TraceStore(AsyncSessionLocal)
        await store.persist(trace)
        chain = await store.get_chain_by_session(session_id)
    """

    def __init__(self, session_factory: Any):
        """
        session_factory: callable that returns an AsyncSession context manager.
        Typically AsyncSessionLocal from app.db.session.
        """
        self._session_factory = session_factory

    async def persist(self, trace: AgentDecisionTrace) -> str | None:
        """Write trace to DB in its own independent transaction.

        Returns the DB record ID, or None if persistence failed.
        Never raises — all errors are logged and swallowed.
        """
        from app.models.agent_decision_trace import AgentDecisionTraceRecord

        try:
            async with self._session_factory() as session:
                async with session.begin():
                    record = AgentDecisionTraceRecord(
                        trace_id=trace.trace_id,
                        agent_id=trace.agent_id,
                        agent_name=trace.agent_name,
                        agent_type=trace.agent_type,
                        session_id=trace.session_id,
                        context_key=trace.context_key,
                        student_id=trace.student_id,
                        course_id=trace.course_id,
                        correlation_id=trace.correlation_id,
                        causation_id=trace.causation_id,
                        sequence=trace.sequence,
                        state_inputs=trace.state_inputs,
                        memory_records_queried=trace.memory_records_queried,
                        evidence=[e.model_dump() for e in trace.evidence],
                        reasoning_steps=[s.model_dump() for s in trace.reasoning_steps],
                        dimensions=[d.model_dump() for d in trace.dimensions],
                        decision_summary=trace.decision_summary,
                        confidence=trace.confidence,
                        output_keys=trace.output_keys,
                        elapsed_ms=trace.elapsed_ms,
                        success=trace.success,
                        error=trace.error,
                        started_at=datetime.fromisoformat(trace.started_at),
                        completed_at=datetime.fromisoformat(trace.completed_at),
                    )
                    session.add(record)
                return record.id
        except SQLAlchemyError as e:
            logger.warning("TraceStore: DB persist failed: %s", e)
            return None
        except Exception as e:
            logger.warning("TraceStore: persist failed: %s", e)
            return None

    async def get_chain_by_session(
        self, session_id: str, limit: int = 50
    ) -> TraceChainResponse:
        """Reconstruct reasoning chain for a learning session."""
        from app.models.agent_decision_trace import AgentDecisionTraceRecord

        try:
            async with self._session_factory() as session:
                stmt = (
                    select(AgentDecisionTraceRecord)
                    .where(AgentDecisionTraceRecord.session_id == session_id)
                    .order_by(AgentDecisionTraceRecord.sequence)
                    .limit(limit)
                )
                result = await session.execute(stmt)
                records = result.scalars().all()
        except Exception as e:
            logger.error("TraceStore: get_chain_by_session failed: %s", e)
            records = []

        return self._build_response(records, session_id=session_id)

    async def get_chain_by_correlation(
        self, correlation_id: str, limit: int = 50
    ) -> TraceChainResponse:
        """Reconstruct reasoning chain for a full swarm run."""
        from app.models.agent_decision_trace import AgentDecisionTraceRecord

        try:
            async with self._session_factory() as session:
                stmt = (
                    select(AgentDecisionTraceRecord)
                    .where(AgentDecisionTraceRecord.correlation_id == correlation_id)
                    .order_by(AgentDecisionTraceRecord.sequence)
                    .limit(limit)
                )
                result = await session.execute(stmt)
                records = result.scalars().all()
        except Exception as e:
            logger.error("TraceStore: get_chain_by_correlation failed: %s", e)
            records = []

        session_id = records[0].session_id if records else None
        return self._build_response(records, session_id=session_id, correlation_id=correlation_id)

    async def get_chain_by_context_key(
        self, context_key: str, limit: int = 50
    ) -> TraceChainResponse:
        """Reconstruct reasoning chain by context key."""
        from app.models.agent_decision_trace import AgentDecisionTraceRecord

        try:
            async with self._session_factory() as session:
                stmt = (
                    select(AgentDecisionTraceRecord)
                    .where(AgentDecisionTraceRecord.context_key == context_key)
                    .order_by(AgentDecisionTraceRecord.sequence)
                    .limit(limit)
                )
                result = await session.execute(stmt)
                records = result.scalars().all()
        except Exception as e:
            logger.error("TraceStore: get_chain_by_context_key failed: %s", e)
            records = []

        session_id = records[0].session_id if records else None
        correlation_id = records[0].correlation_id if records else None
        return self._build_response(
            records, session_id=session_id, correlation_id=correlation_id
        )

    async def get_single_trace(self, trace_id: str) -> AgentDecisionTrace | None:
        """Retrieve one agent trace by its trace_id."""
        from app.models.agent_decision_trace import AgentDecisionTraceRecord

        try:
            async with self._session_factory() as session:
                stmt = select(AgentDecisionTraceRecord).where(
                    AgentDecisionTraceRecord.trace_id == trace_id
                )
                result = await session.execute(stmt)
                record = result.scalar_one_or_none()

            if record is None:
                return None

            return AgentDecisionTrace(**record.to_schema_dict())

        except Exception as e:
            logger.error("TraceStore: get_single_trace failed: %s", e)
            return None

    # ── Private builders ──────────────────────────────────────────

    def _build_response(
        self,
        records: list[Any],
        session_id: str | None = None,
        correlation_id: str | None = None,
    ) -> TraceChainResponse:
        """Convert ORM records to TraceChainResponse with UI nodes and edges."""
        if not records:
            return TraceChainResponse(
                session_id=session_id,
                correlation_id=correlation_id,
                context_key="",
                chain=[],
                nodes=[],
                edges=[],
                total_agents=0,
                total_elapsed_ms=0.0,
                retrieved_at=datetime.now(timezone.utc).isoformat(),
            )

        # Separate consensus from agent traces
        agent_records = [r for r in records if r.agent_type != "consensus"]
        consensus_records = [r for r in records if r.agent_type == "consensus"]

        context_key = records[0].context_key if records else ""
        correlation_id = correlation_id or (records[0].correlation_id if records else None)

        # Build AgentDecisionTrace objects
        chain: list[AgentDecisionTrace] = []
        for rec in agent_records:
            try:
                chain.append(AgentDecisionTrace(**rec.to_schema_dict()))
            except Exception as e:
                logger.warning("TraceStore: failed to deserialize trace %s: %s", rec.trace_id, e)

        # Build consensus trace (last consensus record)
        consensus_trace: ConsensusTrace | None = None
        if consensus_records:
            crec = consensus_records[-1]
            raw = crec.state_inputs or {}
            votes = [
                ConsensusVoteTrace(**v) for v in raw.get("votes", [])
                if isinstance(v, dict)
            ]
            try:
                consensus_trace = ConsensusTrace(
                    trace_id=crec.trace_id,
                    correlation_id=crec.correlation_id,
                    causation_id=crec.causation_id,
                    sequence=crec.sequence,
                    module_id=raw.get("module_id", ""),
                    student_id=crec.student_id,
                    decision=raw.get("decision", ""),
                    confidence=crec.confidence,
                    unanimous=raw.get("unanimous", False),
                    approve_ratio=float(raw.get("approve_ratio", 0.0)),
                    reject_ratio=float(raw.get("reject_ratio", 0.0)),
                    votes=votes,
                    weights_used=raw.get("weights_used", {}),
                    elapsed_ms=crec.elapsed_ms or 0.0,
                    computed_at=crec.completed_at.isoformat() if crec.completed_at else "",
                )
            except Exception as e:
                logger.warning("TraceStore: failed to build ConsensusTrace: %s", e)

        # Build UI nodes
        nodes = [t.to_ui_node() for t in chain]

        # Build UI edges
        edges: list[TraceEdgeUI] = []
        for i in range(1, len(chain)):
            prev = chain[i - 1]
            curr = chain[i]
            label = _AGENT_EDGE_LABELS.get(prev.agent_name, "output → input")
            edges.append(TraceEdgeUI(
                from_trace_id=prev.trace_id,
                to_trace_id=curr.trace_id,
                from_agent=prev.agent_name,
                to_agent=curr.agent_name,
                label=label,
                memory_keys=prev.output_keys,
            ))

        # Add edge from last agent to consensus if present
        if chain and consensus_trace:
            last = chain[-1]
            edges.append(TraceEdgeUI(
                from_trace_id=last.trace_id,
                to_trace_id=consensus_trace.trace_id,
                from_agent=last.agent_name,
                to_agent="consensus_engine",
                label="agent votes → consensus decision",
                memory_keys=[],
            ))

        total_elapsed = sum(t.elapsed_ms for t in chain)
        pipeline_decision = consensus_trace.decision if consensus_trace else None

        return TraceChainResponse(
            session_id=session_id,
            correlation_id=correlation_id,
            context_key=context_key,
            chain=chain,
            consensus=consensus_trace,
            nodes=nodes,
            edges=edges,
            total_agents=len(chain),
            total_elapsed_ms=total_elapsed,
            pipeline_decision=pipeline_decision,
            retrieved_at=datetime.now(timezone.utc).isoformat(),
        )


# ── Module-level singleton (lazy-initialized) ─────────────────────

_trace_store: TraceStore | None = None


def get_trace_store() -> TraceStore:
    """Get or create the global TraceStore singleton."""
    global _trace_store
    if _trace_store is None:
        from app.db.session import AsyncSessionLocal
        _trace_store = TraceStore(AsyncSessionLocal)
    return _trace_store
