"""BaseAgent — abstract base for all swarm agents with async tracing, shared memory, and metrics."""

from __future__ import annotations

import abc
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Any

from app.db.uow import UnitOfWork
from app.memory.shared_memory import SharedMemoryStore
from app.observability.metrics_exporter import exporter

logger = logging.getLogger(__name__)

try:
    from app.tracing import correlation_engine as _tracing_engine
    from app.tracing.models import PropagationContext
    _HAS_TRACING = True
except ImportError:
    _HAS_TRACING = False

try:
    from app.swarm_diagnostics import diagnostics_engine as _diag_engine
    _HAS_DIAGNOSTICS = True
except ImportError:
    _HAS_DIAGNOSTICS = False


class BaseAgent(abc.ABC):
    """Every swarm agent inherits from this.

    Fully async-safe:
    - run() is async, awaits analyze() and publish_observation()
    - publish_observation() properly awaits shared_memory
    - No asyncio.run() bridges needed
    - No silent coroutine discards

    Provides:
    - agent_id, agent_name
    - shared_memory access (async)
    - tracing spans per analyze() call
    - diagnostics recording
    - metrics (duration, success/failure)
    - causation chain linking
    """

    def __init__(
        self,
        agent_name: str,
        uow: UnitOfWork,
        student_id: str,
        course_id: str,
        context_key: str,
        shared_memory: SharedMemoryStore | None = None,
    ):
        self.agent_id = str(uuid.uuid4())[:12]
        self.agent_name = agent_name
        self.uow = uow
        self.student_id = student_id
        self.course_id = course_id
        self.context_key = context_key
        self.shared_memory = shared_memory or SharedMemoryStore(uow)
        self._metrics: dict[str, Any] = {
            "invocations": 0,
            "total_duration_ms": 0.0,
            "successes": 0,
            "failures": 0,
            "last_duration_ms": 0.0,
        }

    @property
    @abc.abstractmethod
    def agent_type(self) -> str:
        """Agent category: pedagogical, adaptive, risk, evaluation."""

    @abc.abstractmethod
    async def analyze(self, state: dict[str, Any]) -> dict[str, Any]:
        """Execute agent analysis. Subclasses implement this. Must be async."""
        ...

    async def run(self, state: dict[str, Any], causation_id: str | None = None) -> dict[str, Any]:
        """Instrumented async execution: tracing + diagnostics + metrics + shared memory.

        This is the ONLY entry point external callers should use.
        """
        start_ns = time.monotonic_ns()
        self._metrics["invocations"] += 1
        trace_ctx = self._start_trace(causation_id)
        propagate_start = time.monotonic()

        try:
            result = await self.analyze(state)
            elapsed_ms = (time.monotonic_ns() - start_ns) / 1_000_000
            self._metrics["successes"] += 1
            self._metrics["total_duration_ms"] += elapsed_ms
            self._metrics["last_duration_ms"] = elapsed_ms

            await self._publish_to_memory(result, elapsed_ms, success=True)
            self._record_diagnostics(elapsed_ms, error=None)
            self._end_trace(trace_ctx, error=None)

            propagate_ms = (time.monotonic() - propagate_start) * 1000
            exporter.observe_histogram("agent_async_propagate_ms", propagate_ms)
            exporter.inc_counter(f"agent_{self.agent_name}_success")

            result["_agent"] = {
                "agent_id": self.agent_id,
                "agent_name": self.agent_name,
                "elapsed_ms": elapsed_ms,
            }
            return result

        except Exception as e:
            elapsed_ms = (time.monotonic_ns() - start_ns) / 1_000_000
            self._metrics["failures"] += 1
            self._metrics["total_duration_ms"] += elapsed_ms
            self._metrics["last_duration_ms"] = elapsed_ms

            logger.error("Agent %s failed: %s", self.agent_name, e, exc_info=True)
            await self._publish_to_memory({"error": str(e)}, elapsed_ms, success=False)
            self._record_diagnostics(elapsed_ms, error=str(e))
            self._end_trace(trace_ctx, error=str(e))

            exporter.inc_counter(f"agent_{self.agent_name}_failure")
            raise

    async def publish_observation(
        self,
        key: str,
        value: Any,
        memory_type: str = "observation",
        confidence: float = 0.8,
    ) -> str | None:
        """Publish observation to shared memory. Async-safe — properly awaits the coroutine."""
        try:
            publish_start = time.monotonic()
            result = await self.shared_memory.publish_observation(
                voter_name=self.agent_name,
                key=key,
                value=value,
                confidence=confidence,
                student_id=self.student_id,
                module_id=self.course_id,
                memory_type=memory_type,
            )
            publish_ms = (time.monotonic() - publish_start) * 1000
            exporter.observe_histogram("agent_publish_observation_ms", publish_ms)
            return result
        except Exception as e:
            logger.warning("Agent %s: publish_observation failed: %s", self.agent_name, e)
            exporter.inc_counter("agent_publish_observation_errors")
            return None

    async def query_memory(
        self, memory_type: str | None = None, limit: int = 30,
    ) -> list[Any]:
        """Query shared memory. Async-safe."""
        try:
            return await self.shared_memory.query(
                student_id=self.student_id,
                module_id=self.course_id,
                memory_type=memory_type,
                limit=limit,
            )
        except Exception as e:
            logger.warning("Agent %s: query_memory failed: %s", self.agent_name, e)
            return []

    def metrics_snapshot(self) -> dict[str, Any]:
        return dict(self._metrics)

    # ── private helpers ──────────────────────────────────────────

    def _start_trace(self, causation_id: str | None) -> Any:
        if not _HAS_TRACING:
            return None
        try:
            current = _tracing_engine.get_current()
            if current is not None:
                return _tracing_engine.child(
                    operation_name=f"agent:{self.agent_name}",
                    causation_id=causation_id,
                    tags={
                        "agent_id": self.agent_id,
                        "agent_type": self.agent_type,
                        "student_id": self.student_id[:8],
                        "course_id": self.course_id[:8],
                    },
                )
            return _tracing_engine.start(
                operation_name=f"agent:{self.agent_name}",
                emitted_by=self.agent_name,
                tags={
                    "agent_id": self.agent_id,
                    "student_id": self.student_id[:8],
                    "course_id": self.course_id[:8],
                },
            )
        except Exception as e:
            logger.debug("Tracing start failed: %s", e)
            return None

    def _end_trace(self, trace_ctx: Any, error: str | None) -> None:
        if not _HAS_TRACING or trace_ctx is None:
            return
        try:
            if error:
                if hasattr(trace_ctx, "with_tag"):
                    trace_ctx = trace_ctx.with_tag("error", error)
            _tracing_engine.end()
        except Exception:
            pass

    async def _publish_to_memory(self, result: dict, elapsed_ms: float, success: bool) -> None:
        try:
            key = f"{self.context_key}:agent:{self.agent_name}:{self.agent_id}"
            await self.shared_memory.publish_observation(
                voter_name=self.agent_name,
                key=key,
                value={
                    "agent_name": self.agent_name,
                    "agent_type": self.agent_type,
                    "success": success,
                    "elapsed_ms": elapsed_ms,
                    "result_summary": self._summarize(result),
                },
                confidence=0.9 if success else 0.3,
                student_id=self.student_id,
                module_id=self.course_id,
                memory_type="observation",
                metadata_json={"agent_id": self.agent_id},
            )
        except Exception as e:
            logger.debug("Memory publish failed: %s", e)

    def _record_diagnostics(self, elapsed_ms: float, error: str | None) -> None:
        if not _HAS_DIAGNOSTICS:
            return
        try:
            _diag_engine.record_execution(
                agent_name=self.agent_name,
                duration_ms=elapsed_ms,
                success=error is None,
                error=error,
                scope={"student_id": self.student_id, "course_id": self.course_id},
            )
        except Exception:
            pass

    @staticmethod
    def _summarize(result: dict) -> dict:
        return {k: v for k, v in result.items() if not k.startswith("_")}
