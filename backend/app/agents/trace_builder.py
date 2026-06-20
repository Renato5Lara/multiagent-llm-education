"""
TraceBuilder — fluent helper for constructing AgentDecisionTrace.

Agents use self._trace_evidence(), self._trace_step(), self._trace_dimension()
on the BaseAgent instance during analyze(). BaseAgent.run() creates a
TraceBuilder at the start and finalizes it after analyze() returns.

Design constraints:
  - Zero overhead if agent doesn't call any _trace_* methods
  - Thread/async safe: one TraceBuilder per run() invocation
  - Value sanitization: large values are truncated before storing
  - No exceptions escape — all errors are swallowed with warnings
"""

from __future__ import annotations

import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Any

from app.schemas.decision_trace import (
    AgentDecisionTrace,
    AgentEvidence,
    AgentReasoningStep,
    DecisionDimension,
    EvidenceSource,
    StepType,
)

logger = logging.getLogger(__name__)

_MAX_VALUE_STR_LEN = 512
_MAX_LIST_ITEMS = 5
_MAX_DICT_KEYS = 10


def _sanitize(value: Any) -> Any:
    """Truncate large values to avoid bloating trace storage."""
    if isinstance(value, str):
        return value[:_MAX_VALUE_STR_LEN] + "…" if len(value) > _MAX_VALUE_STR_LEN else value
    if isinstance(value, list):
        truncated = value[:_MAX_LIST_ITEMS]
        return truncated if len(value) <= _MAX_LIST_ITEMS else truncated + ["…"]
    if isinstance(value, dict):
        keys = list(value.keys())[:_MAX_DICT_KEYS]
        result = {k: _sanitize(value[k]) for k in keys}
        if len(value) > _MAX_DICT_KEYS:
            result["__truncated__"] = f"{len(value) - _MAX_DICT_KEYS} more keys"
        return result
    return value


def _sanitize_state(state: dict[str, Any]) -> dict[str, Any]:
    """Extract only non-private, non-large keys from state dict."""
    out: dict[str, Any] = {}
    for k, v in state.items():
        if k.startswith("_"):
            continue
        if isinstance(v, str) and len(v) > 200:
            out[k] = v[:200] + "…"
        elif isinstance(v, (list, dict)):
            out[k] = f"<{type(v).__name__} len={len(v)}>"
        else:
            out[k] = v
    return out


class TraceBuilder:
    """Collects trace data during one agent.analyze() invocation.

    Created by BaseAgent.run() and accessed via self._current_trace_builder.
    Agents should use the helper methods on BaseAgent rather than
    instantiating this directly.
    """

    def __init__(
        self,
        agent_id: str,
        agent_name: str,
        agent_type: str,
        context_key: str,
        student_id: str,
        course_id: str,
        correlation_id: str | None,
        causation_id: str | None,
        sequence: int,
        session_id: str | None,
    ):
        self.trace_id = str(uuid.uuid4())
        self.agent_id = agent_id
        self.agent_name = agent_name
        self.agent_type = agent_type
        self.context_key = context_key
        self.student_id = student_id
        self.course_id = course_id
        self.correlation_id = correlation_id
        self.causation_id = causation_id
        self.sequence = sequence
        self.session_id = session_id

        self._started_at = datetime.now(timezone.utc).isoformat()
        self._started_ns = time.monotonic_ns()

        self._evidence: list[AgentEvidence] = []
        self._steps: list[AgentReasoningStep] = []
        self._dimensions: list[DecisionDimension] = []
        self._step_counter = 0
        self._memory_records_queried = 0

    # ── Evidence ──────────────────────────────────────────────────

    def add_evidence(
        self,
        source: str | EvidenceSource,
        key: str,
        value: Any,
        confidence: float = 1.0,
        memory_type: str | None = None,
        record_id: str | None = None,
    ) -> None:
        try:
            if isinstance(source, str):
                source = EvidenceSource(source)
            self._evidence.append(AgentEvidence(
                source=source,
                key=key,
                value_summary=_sanitize(value),
                confidence=confidence,
                memory_type=memory_type,
                record_id=record_id,
            ))
            if source == EvidenceSource.SHARED_MEMORY:
                self._memory_records_queried += 1
        except Exception as e:
            logger.debug("TraceBuilder.add_evidence failed: %s", e)

    def add_memory_batch(self, records: list[Any]) -> None:
        """Add a batch of SharedMemoryRecord objects as evidence."""
        try:
            for rec in records:
                self.add_evidence(
                    source=EvidenceSource.SHARED_MEMORY,
                    key=getattr(rec, "key", "unknown"),
                    value=getattr(rec, "value", {}),
                    confidence=float(getattr(rec, "confidence", 1.0)),
                    memory_type=getattr(rec, "memory_type", None),
                    record_id=getattr(rec, "id", None),
                )
        except Exception as e:
            logger.debug("TraceBuilder.add_memory_batch failed: %s", e)

    # ── Reasoning steps ───────────────────────────────────────────

    def add_step(
        self,
        step_type: str | StepType,
        description: str,
        inputs: dict[str, Any] | None = None,
        outputs: dict[str, Any] | None = None,
        elapsed_ms: float | None = None,
        notes: str | None = None,
    ) -> None:
        try:
            if isinstance(step_type, str):
                step_type = StepType(step_type)
            self._step_counter += 1
            self._steps.append(AgentReasoningStep(
                step_number=self._step_counter,
                step_type=step_type,
                description=description,
                inputs=_sanitize(inputs or {}),
                outputs=_sanitize(outputs or {}),
                elapsed_ms=elapsed_ms,
                notes=notes,
            ))
        except Exception as e:
            logger.debug("TraceBuilder.add_step failed: %s", e)

    # ── Decision dimensions ───────────────────────────────────────

    def add_dimension(
        self,
        dimension: str,
        result: str,
        signal: str,
        rule: str,
        confidence: float,
        evidence: dict[str, Any] | None = None,
        alternative_considered: str | None = None,
        alternative_reason: str | None = None,
    ) -> None:
        try:
            self._dimensions.append(DecisionDimension(
                dimension=dimension,
                result=result,
                signal=signal,
                rule=rule,
                confidence=min(1.0, max(0.0, confidence)),
                evidence=_sanitize(evidence or {}),
                alternative_considered=alternative_considered,
                alternative_reason=alternative_reason,
            ))
        except Exception as e:
            logger.debug("TraceBuilder.add_dimension failed: %s", e)

    def add_dimensions_from_rationale(self, rationale: dict[str, Any]) -> None:
        """Import from AdaptiveLearningAgent-style rationale dict.

        Rationale format:
            {"difficulty_decision": {"result": "...", "signal": "...", "rule": "..."}, ...}
        """
        try:
            for key, val in rationale.items():
                if not isinstance(val, dict):
                    continue
                self.add_dimension(
                    dimension=key.replace("_decision", ""),
                    result=str(val.get("result", "")),
                    signal=str(val.get("signal", "")),
                    rule=str(val.get("rule", "")),
                    confidence=float(val.get("confidence", 0.7)),
                    evidence=val.get("evidence", {}),
                )
        except Exception as e:
            logger.debug("TraceBuilder.add_dimensions_from_rationale failed: %s", e)

    # ── Finalization ──────────────────────────────────────────────

    def build(
        self,
        state_inputs: dict[str, Any],
        decision_summary: str,
        confidence: float,
        output_keys: list[str],
        success: bool,
        error: str | None = None,
    ) -> AgentDecisionTrace:
        elapsed_ns = time.monotonic_ns() - self._started_ns
        elapsed_ms = elapsed_ns / 1_000_000

        return AgentDecisionTrace(
            trace_id=self.trace_id,
            agent_id=self.agent_id,
            agent_name=self.agent_name,
            agent_type=self.agent_type,
            session_id=self.session_id,
            context_key=self.context_key,
            student_id=self.student_id,
            course_id=self.course_id,
            correlation_id=self.correlation_id,
            causation_id=self.causation_id,
            sequence=self.sequence,
            state_inputs=_sanitize_state(state_inputs),
            memory_records_queried=self._memory_records_queried,
            evidence=list(self._evidence),
            reasoning_steps=list(self._steps),
            dimensions=list(self._dimensions),
            decision_summary=decision_summary,
            confidence=min(1.0, max(0.0, confidence)),
            output_keys=output_keys,
            elapsed_ms=elapsed_ms,
            success=success,
            error=error,
            started_at=self._started_at,
            completed_at=datetime.now(timezone.utc).isoformat(),
        )
