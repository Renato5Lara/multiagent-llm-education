"""
ConsensusTimeoutMiddleware — Composable middleware wrapping ConsensusEngine
with async cancellation, per-voter timeouts, hung-agent recovery, and metrics.

Pattern:
    engine = ConsensusEngine(voters)
    middleware = ConsensusTimeoutMiddleware(engine, timeout_policy, cancellation_ctx)
    result = await middleware.run_async(ctx, ...)

The middleware wraps the engine's run/run_async method to provide:
    - Per-voter async cancellation via asyncio.wait_for + asyncio.to_thread
    - Hung-agent recovery (skip voters with excessive strikes)
    - Automatic metrics collection
    - Deadline enforcement
    - Graceful fallback vote generation for timed-out voters
"""
from __future__ import annotations

import asyncio
import functools
import logging
import time
from dataclasses import dataclass, field
from typing import Any

from app.core.consensus import (
    ConsensusEngine,
    ConsensusResult,
    ConsensusVote,
    TimeoutAction,
    VoteContext,
    VoteDecision,
)
from app.core.consensus_cancellation import (
    CancellationReason,
    CancellationToken,
    ConsensusCancellationContext,
    get_current_cancellation_ctx,
    set_current_cancellation_ctx,
)
from app.core.consensus_timeout_metrics import ConsensusTimeoutMetrics
from app.core.consensus_timeouts import (
    ConsensusTimeoutConfig,
    ConsensusTimeoutPolicy,
    ConsensusTimeoutState,
    HungAgentRecoveryConfig,
    HungAgentRecoveryManager,
)

logger = logging.getLogger(__name__)


@dataclass
class MiddlewareResult:
    """Result of a middleware-wrapped consensus run."""

    result: ConsensusResult
    timed_out_voters: list[str] = field(default_factory=list)
    skipped_voters: list[str] = field(default_factory=list)
    cancellation_reason: str | None = None
    metrics_snapshot: dict[str, Any] = field(default_factory=dict)


class ConsensusTimeoutMiddleware:
    """Wraps a ConsensusEngine with async timeout enforcement.

    Usage:
        engine = ConsensusEngine()
        policy = ConsensusTimeoutPolicy()
        recovery = HungAgentRecoveryManager()
        metrics = ConsensusTimeoutMetrics()

        middleware = ConsensusTimeoutMiddleware(
            engine=engine,
            timeout_policy=policy,
            recovery_manager=recovery,
            metrics=metrics,
        )

        mw_result = await middleware.run_async(ctx, propagation_ctx=...)
        # mw_result.result is the standard ConsensusResult
        # mw_result.timed_out_voters lists which voters were cancelled
    """

    def __init__(
        self,
        engine: ConsensusEngine,
        timeout_policy: ConsensusTimeoutPolicy | None = None,
        recovery_manager: HungAgentRecoveryManager | None = None,
        metrics: ConsensusTimeoutMetrics | None = None,
        per_voter_timeout_ms: float = 5000.0,
        overall_deadline_ms: float = 30000.0,
    ):
        self._engine = engine
        self._timeout_policy = timeout_policy or ConsensusTimeoutPolicy(
            ConsensusTimeoutConfig(
                default_voter_timeout_ms=per_voter_timeout_ms,
                overall_deadline_ms=overall_deadline_ms,
            )
        )
        self._recovery_manager = recovery_manager or HungAgentRecoveryManager()
        self._metrics = metrics or ConsensusTimeoutMetrics()
        self._per_voter_timeout_ms = per_voter_timeout_ms
        self._overall_deadline_ms = overall_deadline_ms

    @property
    def engine(self) -> ConsensusEngine:
        return self._engine

    @property
    def timeout_policy(self) -> ConsensusTimeoutPolicy:
        return self._timeout_policy

    @property
    def recovery_manager(self) -> HungAgentRecoveryManager:
        return self._recovery_manager

    @property
    def metrics(self) -> ConsensusTimeoutMetrics:
        return self._metrics

    # ── Synchronous run (delegates to engine, adds metrics + recovery) ──

    def run(
        self,
        ctx: VoteContext,
        **kwargs: Any,
    ) -> ConsensusResult:
        """Synchronous consensus run with timeout policy integration.

        Falls back to engine.run() with the timeout_policy attached.
        """
        # Check for hung-agent skips
        recovery_skips = []
        for voter in self._engine.voters:
            if self._recovery_manager.should_skip(voter.voter_name):
                recovery_skips.append(voter.voter_name)

        result = self._engine.run(
            ctx,
            timeout_policy=self._timeout_policy,
            **kwargs,
        )

        # Update recovery manager from timeout state
        tmo_state = getattr(self._timeout_policy, "_last_state", None)
        if result.timeout_info:
            for record in getattr(self._timeout_policy, "_last_state", {}).get("voter_records", {}).values():
                if record.timed_out:
                    self._recovery_manager.record_timeout(record.voter_name)
                else:
                    self._recovery_manager.record_success(record.voter_name)

        # Record metrics
        self._record_metrics_from_result(result, len(self._engine.voters))

        return result

    # ── Async run with per-voter preemption ──────────────────────────

    async def run_async(
        self,
        ctx: VoteContext,
        trace_ctx: Any | None = None,
        propagation_ctx: Any | None = None,
        trust_system: Any | None = None,
        specialization_tracker: Any | None = None,
        shared_memory_store: Any | None = None,
    ) -> MiddlewareResult:
        """Async consensus run with per-voter cancellation.

        Each voter runs in a thread via asyncio.to_thread with a timeout.
        If the timeout fires, the thread future is cancelled and a fallback
        vote is generated.

        Args:
            ctx: Vote context.
            trace_ctx: Optional trace context for observability.
            propagation_ctx: Optional propagation context.
            trust_system: Optional trust system.
            specialization_tracker: Optional specialization tracker.
            shared_memory_store: Optional shared memory store.

        Returns:
            A MiddlewareResult containing the consensus result and
            cancellation metadata.
        """
        deadline_ns = time.monotonic_ns() + int(self._overall_deadline_ms * 1_000_000)

        # Create cancellation context and propagate via ContextVar
        cancel_ctx = ConsensusCancellationContext()
        cancel_ctx.remaining_voters = [v.voter_name for v in self._engine.voters]
        token = set_current_cancellation_ctx(cancel_ctx)

        timed_out_voters: list[str] = []
        skipped_voters: list[str] = []
        votes: list[ConsensusVote] = []
        voter_timings: list[dict] = []
        overall_start_ns = time.monotonic_ns()

        try:
            for voter in self._engine.voters:
                vname = voter.voter_name

                # ── Check overall deadline ─────────────────────
                if time.monotonic_ns() >= deadline_ns:
                    cancel_ctx.cancel(CancellationReason.OVERALL_DEADLINE, source=vname)
                    skipped_voters.append(vname)
                    votes.append(
                        ConsensusVote(
                            voter_name=vname,
                            decision=VoteDecision.ABSTAIN,
                            confidence=0.0,
                            reason="Skipped — overall deadline exceeded",
                            evidence={"deadline_exceeded": True},
                        )
                    )
                    voter_timings.append({
                        "voter_name": vname,
                        "decision": "abstain",
                        "confidence": 0.0,
                        "duration_ms": 0.0,
                        "status": "deadline_skipped",
                    })
                    continue

                # ── Check hung-agent skip ──────────────────────
                if self._recovery_manager.should_skip(vname):
                    strikes = self._recovery_manager.get_strikes(vname)
                    decision, confidence, reason = (
                        self._recovery_manager.build_skip_vote(vname, strikes)
                    )
                    skipped_voters.append(vname)
                    cancel_ctx.mark_skipped(vname)
                    self._metrics.record_hung_agent(vname, strikes, action="skipped")
                    votes.append(
                        ConsensusVote(
                            voter_name=vname,
                            decision=decision,
                            confidence=confidence,
                            reason=reason,
                            evidence={"hung_skip": True, "strikes": strikes},
                        )
                    )
                    voter_timings.append({
                        "voter_name": vname,
                        "decision": decision.value,
                        "confidence": confidence,
                        "duration_ms": 0.0,
                        "status": "hung_skipped",
                    })
                    continue

                # ── Compute adaptive timeout ───────────────────
                voter_timeout = self._get_voter_timeout(vname)

                # ── Run voter with async timeout ───────────────
                v_start_ns = time.monotonic_ns()
                try:
                    v = await asyncio.wait_for(
                        asyncio.to_thread(voter.vote, ctx),
                        timeout=voter_timeout / 1000.0,
                    )
                    elapsed_ms = (time.monotonic_ns() - v_start_ns) / 1_000_000

                    # Check if cancellation was requested during execution
                    if cancel_ctx.cancelled:
                        timed_out_voters.append(vname)
                        cancel_ctx.mark_timed_out(vname)
                        v = self._timeout_policy.build_fallback_vote(
                            self._get_or_create_tmo_state(),
                            vname,
                            reason=f"Cancelled ({cancel_ctx.token.reason.value})",
                        )
                        status = "cancelled"
                    else:
                        self._timeout_policy.record_voter_duration(vname, elapsed_ms)
                        self._recovery_manager.record_success(vname)
                        cancel_ctx.mark_completed(vname)
                        status = "ok"

                except asyncio.TimeoutError:
                    elapsed_ms = (time.monotonic_ns() - v_start_ns) / 1_000_000
                    timed_out_voters.append(vname)
                    cancel_ctx.mark_timed_out(vname)
                    self._timeout_policy.record_voter_result(
                        self._get_or_create_tmo_state(),
                        vname, elapsed_ms,
                        timed_out=True,
                        action=TimeoutAction.USE_FALLBACK_VOTE,
                    )
                    self._recovery_manager.record_timeout(vname)
                    self._metrics.record_timeout(CancellationReason.VOTER_TIMEOUT, vname)

                    v = self._timeout_policy.build_fallback_vote(
                        self._get_or_create_tmo_state(),
                        vname,
                        reason=f"Async timeout after {elapsed_ms:.0f}ms (limit={voter_timeout:.0f}ms)",
                    )
                    status = "timeout"

                except Exception as exc:
                    elapsed_ms = (time.monotonic_ns() - v_start_ns) / 1_000_000
                    timed_out_voters.append(vname)
                    logger.error(
                        "Voter %s raised %s: %s", vname, type(exc).__name__, exc
                    )
                    v = ConsensusVote(
                        voter_name=vname,
                        decision=VoteDecision.ABSTAIN,
                        confidence=0.0,
                        reason=f"Voter error: {exc}",
                        evidence={"error": str(exc)},
                    )
                    status = "error"

                votes.append(v)
                voter_timings.append({
                    "voter_name": vname,
                    "decision": v.decision.value,
                    "confidence": v.confidence,
                    "duration_ms": round(elapsed_ms, 3),
                    "status": status,
                })

                # ── Check cascading delay ──────────────────────
                if len(voter_timings) >= 2:
                    timings_sofar = [t.get("duration_ms", 0.0) for t in voter_timings]
                    if self._timeout_policy.check_cascading_delay(
                        self._get_or_create_tmo_state(), timings_sofar
                    ):
                        self._metrics.record_cascading_delay()

            # ── Aggregate votes ──────────────────────────────────
            decision, confidence = self._engine._aggregate(votes)

            overall_elapsed_ms = (time.monotonic_ns() - overall_start_ns) / 1_000_000

            result = ConsensusResult(
                module_id=ctx.module_id,
                student_id=ctx.student_id,
                decision=decision,
                confidence=confidence,
                votes=votes,
                voter_timings=voter_timings,
            )

            # Update metrics
            self._metrics.record_consensus_run(
                total_voters=len(self._engine.voters),
                timed_out=len(timed_out_voters),
                skipped=len(skipped_voters),
            )

            snapshot = self._metrics.snapshot()

            return MiddlewareResult(
                result=result,
                timed_out_voters=timed_out_voters,
                skipped_voters=skipped_voters,
                cancellation_reason=(
                    cancel_ctx.token.reason.value if cancel_ctx.cancelled else None
                ),
                metrics_snapshot=snapshot.to_dict(),
            )

        finally:
            # Restore previous ContextVar value
            set_current_cancellation_ctx(token)

    # ── Private helpers ─────────────────────────────────────────────

    def _get_voter_timeout(self, voter_name: str) -> float:
        """Compute effective per-voter timeout in ms."""
        base = self._timeout_policy.config.default_voter_timeout_ms

        # Apply hung-agent exponential backoff
        strikes = self._recovery_manager.get_strikes(voter_name)
        if strikes > 0:
            multiplier = self._recovery_manager.get_timeout_multiplier(voter_name)
            return base * multiplier

        # Apply adaptive timeout
        adaptive = self._timeout_policy._get_adaptive_timeout(voter_name)
        return max(base, adaptive)

    def _get_or_create_tmo_state(self) -> ConsensusTimeoutState:
        """Get or create a timeout state for the middleware's policy."""
        if not hasattr(self, "_tmo_state") or self._tmo_state is None:
            self._tmo_state = self._timeout_policy.create_state()
        return self._tmo_state

    def _record_metrics_from_result(
        self,
        result: ConsensusResult,
        total_voters: int,
    ) -> None:
        """Record metrics from a completed consensus result."""
        if not result.timeout_info:
            return
        info = result.timeout_info
        if info.get("degraded"):
            self._metrics.record_degraded()
        if info.get("quorum_fallback_triggered"):
            self._metrics.record_quorum_fallback()
        if info.get("cascading_delay_detected"):
            self._metrics.record_cascading_delay()
        timed_out = info.get("timed_out_count", 0)
        self._metrics.record_consensus_run(
            total_voters=total_voters,
            timed_out=timed_out,
            skipped=0,
        )

