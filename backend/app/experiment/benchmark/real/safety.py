"""Safety layer — timeout, retry, cancellation, graceful degradation for real swarm benchmark."""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


class ExperimentTimedOut(Exception):
    """Raised when a single experiment run exceeds the timeout."""


class ExperimentCancelled(Exception):
    """Raised when the benchmark is cancelled externally."""


@dataclass
class SafetyConfig:
    timeout_per_experiment_seconds: float = 120.0
    max_retries: int = 2
    retry_delay_base_seconds: float = 2.0
    retry_delay_max_seconds: float = 30.0
    graceful_degradation: bool = True
    cancellation_flag: bool = False


@dataclass
class ExperimentOutcome:
    success: bool
    result: dict[str, Any] | None = None
    error: str | None = None
    duration_ms: float = 0.0
    retries: int = 0
    degraded: bool = False


async def safe_execute(
    coro_factory,
    safety: SafetyConfig,
    experiment_label: str = "",
) -> ExperimentOutcome:
    """Execute an async coroutine with timeout, retry, and cancellation.

    `coro_factory` must be a callable that returns an awaitable.
    It is called again on each retry so a fresh coroutine is created.
    """
    if safety.cancellation_flag:
        raise ExperimentCancelled(f"Experiment cancelled: {experiment_label}")

    last_error: str | None = None
    start = time.monotonic()

    for attempt in range(safety.max_retries + 1):
        if safety.cancellation_flag:
            raise ExperimentCancelled(f"Experiment cancelled: {experiment_label}")

        try:
            coro = coro_factory()
            result = await asyncio.wait_for(
                coro,
                timeout=safety.timeout_per_experiment_seconds,
            )
            elapsed = (time.monotonic() - start) * 1000
            return ExperimentOutcome(
                success=True,
                result=result,
                duration_ms=elapsed,
                retries=attempt,
            )

        except asyncio.TimeoutError:
            last_error = f"Timeout after {safety.timeout_per_experiment_seconds}s"
            logger.warning(
                "Experiment[%s] attempt %d/%d: %s",
                experiment_label, attempt + 1, safety.max_retries + 1, last_error,
            )
            if attempt < safety.max_retries:
                delay = min(
                    safety.retry_delay_base_seconds * (2 ** attempt),
                    safety.retry_delay_max_seconds,
                )
                await asyncio.sleep(delay)

        except ExperimentCancelled:
            raise

        except Exception as exc:
            last_error = f"{type(exc).__name__}: {exc}"
            logger.warning(
                "Experiment[%s] attempt %d/%d failed: %s",
                experiment_label, attempt + 1, safety.max_retries + 1, last_error,
            )
            if attempt < safety.max_retries:
                delay = min(
                    safety.retry_delay_base_seconds * (2 ** attempt),
                    safety.retry_delay_max_seconds,
                )
                await asyncio.sleep(delay)

    elapsed = (time.monotonic() - start) * 1000

    if safety.graceful_degradation:
        logger.info(
            "Experiment[%s] degraded after %d retries (%s)",
            experiment_label, safety.max_retries, last_error,
        )
        return ExperimentOutcome(
            success=False,
            result=_degraded_result(last_error),
            error=last_error,
            duration_ms=elapsed,
            retries=safety.max_retries,
            degraded=True,
        )

    return ExperimentOutcome(
        success=False,
        error=last_error,
        duration_ms=elapsed,
        retries=safety.max_retries,
    )


def _degraded_result(error: str) -> dict[str, Any]:
    """Produce a degraded output when execution fails."""
    return {
        "research_result": {"findings": [], "examples": [], "summary": f"Degraded: {error}"},
        "pedagogical_structure": {"sections": [], "topic": ""},
        "adaptation_plan": {"difficulty_level": "intermediate"},
        "multimodal_plan": {"decisions": [], "text_sections": [], "prompt_sections": {}},
        "prompts": [],
        "consistency_report": {"passed": True, "issues": [], "narrative_coherence_score": 0.5},
        "execution_summary": {
            "total_duration_ms": 0.0,
            "phase_timings_ms": {},
            "error": error,
            "degraded": True,
        },
        "warnings": [f"Execution degraded: {error}"],
        "_degraded": True,
        "_error": error,
    }
