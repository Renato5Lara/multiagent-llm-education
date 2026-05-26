"""
Consensus Timeout Policies — Adaptive timeout, degraded consensus,
hung-agent recovery, quorum fallback, and distributed deadline coordination.

Integrates into ConsensusEngine.run() via an optional `timeout_policy` kwarg.
When absent, existing behavior is completely unchanged (zero breaking change).

Architecture:
    ConsensusTimeoutConfig       — Tunable parameters
    TimeoutRecord                — Per-voter outcome in a single consensus run
    ConsensusTimeoutState        — Per-run mutable state
    ConsensusTimeoutPolicy       — Main policy: adaptive timeouts, fallback actions
"""
from __future__ import annotations

import logging
import math
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from threading import Lock
from typing import Any

from app.core.consensus import ConsensusVote, VoteDecision, TimeoutAction

logger = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────────────

BAGGAGE_TIMEOUT_PREFIX = "ctmo:"
DEFAULT_VOTER_TIMEOUT_MS = 5000.0
DEFAULT_OVERALL_DEADLINE_MS = 30000.0
ADAPTIVE_WINDOW_SIZE = 10
HUNG_MULTIPLIER_DEFAULT = 3.0

# ── Config ────────────────────────────────────────────────────────────


@dataclass
class ConsensusTimeoutConfig:
    """Tunable timeout parameters for distributed consensus."""

    default_voter_timeout_ms: float = DEFAULT_VOTER_TIMEOUT_MS
    """Per-voter base timeout in ms (adaptive multipliers are applied on top)."""

    overall_deadline_ms: float = DEFAULT_OVERALL_DEADLINE_MS
    """Total wall-clock deadline for the entire consensus run."""

    adaptive_enabled: bool = True
    """If True, voter timeouts adapt based on historical duration data."""

    degraded_voter_threshold: int = 2
    """Minimum number of timely voters required to avoid degraded mode.
    If fewer than this many voters complete within timeout, degraded mode
    is triggered for the overall result."""

    quorum_fallback_enabled: bool = True
    """If True, fall back to a reduced quorum when too few voters respond."""

    quorum_minimum: int = 1
    """Minimum number of valid (non-timed-out) votes required for a valid
    consensus decision.  If fewer than this remain after timeouts, the
    decision is ABSTAIN with 0 confidence."""

    hung_voter_timeout_multiplier: float = HUNG_MULTIPLIER_DEFAULT
    """A voter is considered "hung" if its elapsed time exceeds this
    multiplier times its adaptive timeout.  Hung voters are recorded and
    may be skipped on the next consensus run."""

    cascading_delay_threshold_ms: float = 10000.0
    """If cumulative elapsed time exceeds this threshold across consecutive
    voters, cascading delay is flagged."""

    timeout_granularity_ms: float = 100.0
    """Polling granularity for deadline checks (not used for preemption,
    only for state tracking)."""

    # ── Degraded mode vote generation ──────────────────────────
    degraded_vote_decision: str = "abstain"
    """Decision to use when a voter times out and no fallback is available."""
    degraded_vote_confidence: float = 0.0
    """Confidence for degraded/fallback votes."""
    degraded_vote_reason: str = "Voter timed out — fallback abstain"

    def __post_init__(self):
        if self.default_voter_timeout_ms <= 0:
            raise ValueError("default_voter_timeout_ms must be > 0")
        if self.overall_deadline_ms <= 0:
            raise ValueError("overall_deadline_ms must be > 0")
        if self.degraded_voter_threshold < 1:
            raise ValueError("degraded_voter_threshold must be >= 1")
        if self.quorum_minimum < 1:
            raise ValueError("quorum_minimum must be >= 1")
        if self.hung_voter_timeout_multiplier < 1.0:
            raise ValueError("hung_voter_timeout_multiplier must be >= 1.0")


# ── Enums ─────────────────────────────────────────────────────────────


class HungState(str, Enum):
    """State of a hung voter across consensus runs."""

    NORMAL = "normal"
    SUSPECTED = "suspected"   # Exceeded threshold once
    CONFIRMED = "confirmed"   # Exceeded threshold multiple times
    RECOVERED = "recovered"   # Previously hung, now responding normally


# ── Records ───────────────────────────────────────────────────────────


@dataclass
class TimeoutRecord:
    """Per-voter outcome in a single consensus run."""

    voter_name: str
    timed_out: bool
    duration_ms: float
    action: TimeoutAction = TimeoutAction.NONE
    adaptive_timeout_ms: float | None = None
    hung_state: HungState = HungState.NORMAL
    deadline_exceeded: bool = False
    reason: str = ""


@dataclass
class VoterTimeoutStats:
    """Sliding-window timing statistics for a single voter.

    Used by the adaptive timeout system to compute per-voter multipliers
    based on recent actual performance.
    """

    voter_name: str
    recent_durations: list[float] = field(default_factory=list)
    max_window_size: int = ADAPTIVE_WINDOW_SIZE
    _lock: Lock = field(default_factory=Lock)

    # ── Helper to share lock across properties ───────────────
    def _compute_p50(self, s: list[float]) -> float:
        n = len(s)
        if n == 0:
            return 0.0
        if n % 2 == 1:
            return s[n // 2]
        return (s[n // 2 - 1] + s[n // 2]) / 2.0

    def _compute_p95(self, s: list[float]) -> float:
        n = len(s)
        if n == 0:
            return 0.0
        idx = max(0, min(n - 1, int(n * 0.95)))
        return s[idx]

    def record_duration(self, duration_ms: float) -> None:
        with self._lock:
            self.recent_durations.append(duration_ms)
            if len(self.recent_durations) > self.max_window_size:
                self.recent_durations.pop(0)

    @property
    def p50(self) -> float:
        with self._lock:
            if not self.recent_durations:
                return 0.0
            s = sorted(self.recent_durations)
            return self._compute_p50(s)

    @property
    def p95(self) -> float:
        with self._lock:
            if not self.recent_durations:
                return 0.0
            s = sorted(self.recent_durations)
            return self._compute_p95(s)

    @property
    def max_duration(self) -> float:
        with self._lock:
            return max(self.recent_durations) if self.recent_durations else 0.0

    @property
    def count(self) -> int:
        with self._lock:
            return len(self.recent_durations)

    @property
    def adaptive_multiplier(self) -> float:
        """Compute a safe adaptive timeout multiplier.

        Uses p95 * 1.5 as the recommended timeout, divided by the base
        timeout to produce a multiplier.  Minimum 1.0, maximum 5.0.
        """
        with self._lock:
            if not self.recent_durations or len(self.recent_durations) < 3:
                return 1.0
            s = sorted(self.recent_durations)
            p95 = self._compute_p95(s)
            if p95 <= 0:
                return 1.0
            recommended = p95 * 1.5
            multiplier = recommended / p95
            return max(1.0, min(5.0, multiplier))


# ── State ─────────────────────────────────────────────────────────────


@dataclass
class ConsensusTimeoutState:
    """Mutable per-run state tracking timeouts, degraded mode, and deadlines.

    Not thread-safe; created per consensus run and used within a single
    thread.
    """

    config: ConsensusTimeoutConfig
    state_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    start_ns: int = field(default_factory=lambda: time.monotonic_ns())

    # Voter tracking
    voter_records: dict[str, TimeoutRecord] = field(default_factory=dict)
    voter_order: list[str] = field(default_factory=list)

    # Degraded mode
    degraded: bool = False
    degraded_reason: str = ""
    degraded_triggered_by: str | None = None

    # Hung tracking
    hung_voters: set[str] = field(default_factory=set)

    # Cascading delay
    cascading_delay_detected: bool = False
    cascading_delay_reason: str = ""

    # Quorum fallback
    quorum_met: bool = True
    quorum_fallback_triggered: bool = False
    effective_quorum: int | None = None

    # Deadline
    deadline_exceeded: bool = False

    # Distributed baggage (for downstream propagation)
    baggage: dict[str, str] = field(default_factory=dict)

    def elapsed_ms(self) -> float:
        return (time.monotonic_ns() - self.start_ns) / 1_000_000

    def remaining_deadline_ms(self) -> float:
        elapsed = self.elapsed_ms()
        return max(0.0, self.config.overall_deadline_ms - elapsed)


# ── Policy ────────────────────────────────────────────────────────────


class ConsensusTimeoutPolicy:
    """Timeout policy orchestration for distributed consensus.

    Usage:
        policy = ConsensusTimeoutPolicy(config)
        state = policy.create_state()
        # In the voter loop:
        is_timed_out, action = policy.check_voter(state, voter_name, elapsed_ms)
        if is_timed_out:
            fallback_vote = policy.build_fallback_vote(state, voter_name, ctx)
        policy.record_voter_result(state, voter_name, elapsed_ms, timed_out, action)
        policy.check_overall_deadline(state)
        if state.degraded:
            policy.handle_degraded(state, ...)
        if not policy.is_quorum_met(state):
            policy.trigger_quorum_fallback(state)
    """

    def __init__(self, config: ConsensusTimeoutConfig | None = None):
        self._config = config or ConsensusTimeoutConfig()
        self._voter_stats: dict[str, VoterTimeoutStats] = {}
        self._hung_state: dict[str, HungState] = {}
        self._hung_strike_count: dict[str, int] = {}
        self._lock = Lock()

    # ── Configuration access ────────────────────────────────────

    @property
    def config(self) -> ConsensusTimeoutConfig:
        return self._config

    # ── State creation ──────────────────────────────────────────

    def create_state(self) -> ConsensusTimeoutState:
        """Create a new per-run timeout state.

        Returns:
            A fresh ConsensusTimeoutState initialized with the policy config.
        """
        return ConsensusTimeoutState(config=self._config)

    # ── Voter timeout check ─────────────────────────────────────

    def check_voter(
        self,
        state: ConsensusTimeoutState,
        voter_name: str,
        elapsed_ms: float,
    ) -> tuple[bool, TimeoutAction]:
        """Check if a voter has exceeded its adaptive timeout.

        Args:
            state: The current per-run timeout state.
            voter_name: Name of the voter.
            elapsed_ms: How long the voter has been running.

        Returns:
            (timed_out, action) — whether the voter timed out and what
            action to take.
        """
        if state.deadline_exceeded:
            return True, TimeoutAction.DEADLINE_EXCEEDED

        adaptive_timeout = self._get_adaptive_timeout(voter_name)
        hung_threshold = adaptive_timeout * self._config.hung_voter_timeout_multiplier

        if elapsed_ms >= hung_threshold:
            with self._lock:
                current_hung = self._hung_state.get(voter_name, HungState.NORMAL)
                strikes = self._hung_strike_count.get(voter_name, 0) + 1
                self._hung_strike_count[voter_name] = strikes
                if current_hung == HungState.NORMAL and strikes >= 1:
                    self._hung_state[voter_name] = HungState.SUSPECTED
                if strikes >= 3:
                    self._hung_state[voter_name] = HungState.CONFIRMED
                state.hung_voters.add(voter_name)
            return True, TimeoutAction.HUNG_RECOVERY

        if elapsed_ms >= adaptive_timeout:
            return True, TimeoutAction.USE_FALLBACK_VOTE

        return False, TimeoutAction.NONE

    def check_overall_deadline(self, state: ConsensusTimeoutState) -> bool:
        """Check if the overall consensus deadline has been exceeded.

        If exceeded, marks the state accordingly.

        Returns:
            True if the deadline has been exceeded.
        """
        if state.deadline_exceeded:
            return True
        if state.elapsed_ms() >= self._config.overall_deadline_ms:
            state.deadline_exceeded = True
            state.degraded = True
            state.degraded_reason = "Overall deadline exceeded"
            logger.warning(
                "ConsensusTimeout[%s]: overall deadline %.0fms exceeded at %.0fms",
                state.state_id[:8],
                self._config.overall_deadline_ms,
                state.elapsed_ms(),
            )
            return True
        return False

    def check_cascading_delay(
        self,
        state: ConsensusTimeoutState,
        recent_timings: list[float],
    ) -> bool:
        """Detect cascading delays across consecutive voters.

        A cascading delay is flagged when the cumulative elapsed time
        exceeds the cascading_delay_threshold_ms.

        Args:
            state: Current per-run state.
            recent_timings: Duration of each voter completed so far, in order.

        Returns:
            True if cascading delay was detected.
        """
        if state.cascading_delay_detected:
            return True
        cumulative = sum(recent_timings)
        if cumulative >= self._config.cascading_delay_threshold_ms:
            state.cascading_delay_detected = True
            state.cascading_delay_reason = (
                f"Cumulative delay {cumulative:.0f}ms exceeds "
                f"threshold {self._config.cascading_delay_threshold_ms:.0f}ms"
            )
            logger.warning(
                "ConsensusTimeout[%s]: %s",
                state.state_id[:8],
                state.cascading_delay_reason,
            )
            return True
        return False

    # ── Voter result recording ─────────────────────────────────

    def record_voter_result(
        self,
        state: ConsensusTimeoutState,
        voter_name: str,
        duration_ms: float,
        timed_out: bool = False,
        action: TimeoutAction = TimeoutAction.NONE,
        hung_state: HungState = HungState.NORMAL,
        reason: str = "",
    ) -> TimeoutRecord:
        """Record a voter's result in the per-run state.

        This also updates the adaptive statistics for the voter.

        Args:
            state: Current per-run state.
            voter_name: Name of the voter.
            duration_ms: How long the voter took.
            timed_out: Whether the voter timed out.
            action: The action taken due to timeout.
            hung_state: Current hung state of the voter.
            reason: Human-readable reason for the outcome.

        Returns:
            The TimeoutRecord created.
        """
        if voter_name not in state.voter_order:
            state.voter_order.append(voter_name)

        adaptive_timeout = self._get_adaptive_timeout(voter_name)
        record = TimeoutRecord(
            voter_name=voter_name,
            timed_out=timed_out,
            duration_ms=duration_ms,
            action=action,
            adaptive_timeout_ms=adaptive_timeout,
            hung_state=hung_state,
            deadline_exceeded=state.deadline_exceeded,
            reason=reason,
        )
        state.voter_records[voter_name] = record
        return record

    def record_voter_duration(self, voter_name: str, duration_ms: float) -> None:
        """Record a successful voter duration for adaptive stats.

        This updates the sliding window used to compute adaptive timeouts.
        Should be called when a voter completes without timing out.
        """
        with self._lock:
            if voter_name not in self._voter_stats:
                self._voter_stats[voter_name] = VoterTimeoutStats(
                    voter_name=voter_name,
                )
            self._voter_stats[voter_name].record_duration(duration_ms)

            # If the voter was hung and now completes normally, mark recovered
            current = self._hung_state.get(voter_name, HungState.NORMAL)
            if current in (HungState.SUSPECTED, HungState.CONFIRMED):
                self._hung_state[voter_name] = HungState.RECOVERED

    # ── Degraded mode handling ──────────────────────────────────

    def check_degraded(
        self,
        state: ConsensusTimeoutState,
        completed_count: int,
        total_voters: int,
    ) -> bool:
        """Check if the consensus should enter degraded mode.

        Enters degraded mode if the number of voters that completed
        (within timeout) is below the degraded_voter_threshold.

        Args:
            state: Current per-run state.
            completed_count: Number of voters that completed normally.
            total_voters: Total number of registered voters.

        Returns:
            True if degraded mode was triggered.
        """
        if state.degraded:
            return True

        if completed_count < self._config.degraded_voter_threshold:
            remaining = total_voters - completed_count
            state.degraded = True
            state.degraded_reason = (
                f"Only {completed_count}/{total_voters} completed within timeout "
                f"(threshold={self._config.degraded_voter_threshold})"
            )
            logger.warning(
                "ConsensusTimeout[%s]: degraded mode — %s",
                state.state_id[:8],
                state.degraded_reason,
            )
            return True
        return False

    # ── Quorum fallback ─────────────────────────────────────────

    def is_quorum_met(
        self,
        state: ConsensusTimeoutState,
        completed_count: int | None = None,
    ) -> bool:
        """Check whether the minimum quorum has been met.

        Args:
            state: Current per-run state.
            completed_count: Override for the count of completed voters.
                            If None, computed from state.

        Returns:
            True if quorum is met.
        """
        if completed_count is None:
            completed_count = sum(
                1 for r in state.voter_records.values() if not r.timed_out
            )
        return completed_count >= self._config.quorum_minimum

    def trigger_quorum_fallback(
        self,
        state: ConsensusTimeoutState,
        completed_count: int | None = None,
    ) -> None:
        """Trigger emergency quorum fallback.

        Sets state flags so that the caller can respond with a reduced
        confidence decision.
        """
        if completed_count is None:
            completed_count = sum(
                1 for r in state.voter_records.values() if not r.timed_out
            )
        state.quorum_fallback_triggered = True
        state.quorum_met = completed_count >= self._config.quorum_minimum
        state.effective_quorum = self._config.quorum_minimum
        logger.warning(
            "ConsensusTimeout[%s]: quorum fallback — %d/%d met (min=%d)",
            state.state_id[:8],
            completed_count,
            len(state.voter_records),
            self._config.quorum_minimum,
        )

    # ── Fallback vote construction ──────────────────────────────

    def build_fallback_vote(
        self,
        state: ConsensusTimeoutState,
        voter_name: str,
        reason: str | None = None,
    ) -> ConsensusVote:
        """Construct a fallback ConsensusVote for a timed-out voter.

        Args:
            state: Current per-run state.
            voter_name: Name of the voter that timed out.
            reason: Optional reason for the fallback.

        Returns:
            A ConsensusVote with ABSTAIN decision and zero confidence.
        """
        return ConsensusVote(
            voter_name=voter_name,
            decision=VoteDecision.ABSTAIN,
            confidence=self._config.degraded_vote_confidence,
            reason=reason or self._config.degraded_vote_reason,
            evidence={
                "timeout": True,
                "degraded": state.degraded,
                "adaptive_timeout_ms": state.voter_records.get(
                    voter_name,
                    TimeoutRecord(voter_name=voter_name, timed_out=True, duration_ms=0.0),
                ).adaptive_timeout_ms,
            },
        )

    def build_degraded_vote(
        self,
        state: ConsensusTimeoutState,
        voter_name: str,
    ) -> ConsensusVote:
        """Construct a degraded-mode vote for a voter skipped due to degradation.

        Args:
            state: Current per-run state.
            voter_name: Name of the voter being skipped.

        Returns:
            A ConsensusVote reflecting the degraded decision.
        """
        return ConsensusVote(
            voter_name=voter_name,
            decision=VoteDecision.ABSTAIN,
            confidence=0.0,
            reason=f"Skipped in degraded mode: {state.degraded_reason}",
            evidence={
                "degraded": True,
                "degraded_reason": state.degraded_reason,
            },
        )

    # ── Adaptive timeout computation ────────────────────────────

    def _get_adaptive_timeout(self, voter_name: str) -> float:
        """Compute the effective timeout for a voter.

        If adaptive timeouts are enabled, uses p95 * 1.5 from the voter's
        sliding window.  Otherwise returns the static default.

        Args:
            voter_name: Name of the voter.

        Returns:
            Timeout in milliseconds.
        """
        if not self._config.adaptive_enabled:
            return self._config.default_voter_timeout_ms

        with self._lock:
            stats = self._voter_stats.get(voter_name)
            if stats is None or stats.count < 3:
                return self._config.default_voter_timeout_ms

            p95 = stats.p95
            if p95 <= 0:
                return self._config.default_voter_timeout_ms

            adaptive = p95 * 1.5
            clamped = max(
                10.0,  # hard lower bound (10ms)
                min(adaptive, self._config.default_voter_timeout_ms * 10.0),  # upper
            )
            return clamped

    def get_hung_state(self, voter_name: str) -> HungState:
        """Get the current hung state of a voter.

        Args:
            voter_name: Name of the voter.

        Returns:
            Current HungState enum value.
        """
        with self._lock:
            return self._hung_state.get(voter_name, HungState.NORMAL)

    def get_voter_stats(self, voter_name: str) -> VoterTimeoutStats | None:
        """Get the timing statistics for a voter.

        Args:
            voter_name: Name of the voter.

        Returns:
            VoterTimeoutStats or None if no data recorded yet.
        """
        with self._lock:
            return self._voter_stats.get(voter_name)

    def get_all_stats(self) -> dict[str, VoterTimeoutStats]:
        """Get timing statistics for all voters.

        Returns:
            Dict mapping voter name to its stats.
        """
        with self._lock:
            return dict(self._voter_stats)

    def get_state_summary(self, state: ConsensusTimeoutState) -> dict[str, Any]:
        """Produce a human-readable summary of the timeout state.

        Args:
            state: The per-run timeout state.

        Returns:
            Dict with summary fields.
        """
        return {
            "state_id": state.state_id[:8],
            "elapsed_ms": round(state.elapsed_ms(), 2),
            "remaining_ms": round(state.remaining_deadline_ms(), 2),
            "degraded": state.degraded,
            "degraded_reason": state.degraded_reason,
            "deadline_exceeded": state.deadline_exceeded,
            "cascading_delay_detected": state.cascading_delay_detected,
            "quorum_met": state.quorum_met,
            "quorum_fallback_triggered": state.quorum_fallback_triggered,
            "hung_voters": list(state.hung_voters),
            "voter_count": len(state.voter_records),
            "timed_out_count": sum(
                1 for r in state.voter_records.values() if r.timed_out
            ),
        }

    # ── Baggage propagation for distributed coordination ────────

    def to_baggage(self, state: ConsensusTimeoutState) -> dict[str, str]:
        """Serialize timeout state to baggage entries for distributed tracing.

        This allows downstream consumers (other services or agents) to
        know the timeout/deadline status of the consensus run.

        Args:
            state: Current per-run timeout state.

        Returns:
            Dict of baggage key-value pairs.
        """
        baggage: dict[str, str] = {}
        prefix = BAGGAGE_TIMEOUT_PREFIX

        baggage[f"{prefix}remaining_ms"] = str(round(state.remaining_deadline_ms(), 1))
        baggage[f"{prefix}deadline_ms"] = str(self._config.overall_deadline_ms)
        baggage[f"{prefix}elapsed_ms"] = str(round(state.elapsed_ms(), 1))
        baggage[f"{prefix}degraded"] = "1" if state.degraded else "0"
        baggage[f"{prefix}deadline_exceeded"] = "1" if state.deadline_exceeded else "0"
        baggage[f"{prefix}hung_count"] = str(len(state.hung_voters))
        baggage[f"{prefix}voter_count"] = str(len(state.voter_records))
        baggage[f"{prefix}quorum_met"] = "1" if state.quorum_met else "0"

        return baggage

    def from_baggage(self, baggage: dict[str, str]) -> dict[str, Any]:
        """Deserialize timeout information from baggage.

        Args:
            baggage: Dict of baggage entries.

        Returns:
            Dict with parsed timeout fields, or empty dict if no entries found.
        """
        prefix = BAGGAGE_TIMEOUT_PREFIX
        result: dict[str, Any] = {}

        remaining = baggage.get(f"{prefix}remaining_ms")
        deadline = baggage.get(f"{prefix}deadline_ms")
        degraded = baggage.get(f"{prefix}degraded")
        exceeded = baggage.get(f"{prefix}deadline_exceeded")

        if remaining is not None:
            result["remaining_ms"] = float(remaining)
        if deadline is not None:
            result["deadline_ms"] = float(deadline)
        if degraded is not None:
            result["degraded"] = degraded == "1"
        if exceeded is not None:
            result["deadline_exceeded"] = exceeded == "1"

        hung_count = baggage.get(f"{prefix}hung_count")
        if hung_count is not None:
            result["hung_count"] = int(hung_count)

        return result

    def check_baggage_timeout(
        self,
        baggage: dict[str, str],
        timeout_ms: float | None = None,
    ) -> bool:
        """Check whether baggage indicates a timed-out consensus upstream.

        Useful when a downstream agent receives baggage from a consensus
        run and needs to know if the deadline was already exceeded.

        Args:
            baggage: Baggage dict from the propagation context.
            timeout_ms: If provided, use this as the deadline instead of
                        the config default.

        Returns:
            True if the upstream consensus has exceeded its deadline.
        """
        info = self.from_baggage(baggage)
        if info.get("deadline_exceeded", False):
            return True

        remaining = info.get("remaining_ms")
        if remaining is not None and remaining <= 0:
            return True

        return False

    # ── Reset ───────────────────────────────────────────────────

    def reset(self) -> None:
        """Reset all adaptive state (statistics, hung tracking).

        Does not affect configuration.
        """
        with self._lock:
            self._voter_stats.clear()
            self._hung_state.clear()
            self._hung_strike_count.clear()


# ── Hung-Agent Recovery Manager ──────────────────────────────────


@dataclass
class HungAgentRecoveryConfig:
    """Configuration for hung-agent recovery behavior."""

    max_strikes: int = 3
    """Number of consecutive timeout strikes before agent is skipped."""

    backoff_factor: float = 2.0
    """Exponential backoff factor applied to timeout multiplier per strike."""

    recovery_threshold: int = 2
    """Number of successful completions needed to clear hung status."""

    skip_on_strikes: bool = True
    """If True, skip the agent entirely after max_strikes is reached."""

    skip_vote_decision: str = "abstain"
    """Decision to assign when a hung agent is skipped."""

    skip_vote_confidence: float = 0.0
    """Confidence when a hung agent is skipped."""

    skip_vote_reason: str = "Skipped — hung agent recovery"
    """Reason when a hung agent is skipped."""


class HungAgentRecoveryManager:
    """Tracks hung-agent strikes, applies exponential backoff, and
    decides whether to skip or allow a previously-hung voter.

    Lives across consensus runs (same instance used for multiple calls
    to `ConsensusEngine.run()`), accumulating strike counts over time.

    Usage:
        recovery = HungAgentRecoveryManager()
        # After a consensus run:
        for name, record in state.voter_records.items():
            if record.timed_out:
                recovery.record_timeout(name)
            else:
                recovery.record_success(name)
        # Before the next run:
        for voter in engine.voters:
            if recovery.should_skip(voter.voter_name):
                # produce fallback vote
                pass
    """

    def __init__(self, config: HungAgentRecoveryConfig | None = None):
        self._config = config or HungAgentRecoveryConfig()
        self._strikes: dict[str, int] = {}
        self._recovery_progress: dict[str, int] = {}
        self._lock = Lock()

    @property
    def config(self) -> HungAgentRecoveryConfig:
        return self._config

    def record_timeout(self, voter_name: str) -> None:
        """Record a timeout strike for a voter.

        Strikes accumulate up to max_strikes.  Recovery progress is
        reset when a new timeout occurs.
        """
        with self._lock:
            current = self._strikes.get(voter_name, 0)
            self._strikes[voter_name] = min(
                current + 1, self._config.max_strikes + 1
            )
            self._recovery_progress.pop(voter_name, None)

    def record_success(self, voter_name: str) -> None:
        """Record a successful (non-timeout) completion for a voter.

        If the voter has accumulated strikes, this advances recovery
        progress.  Once recovery_threshold successes are seen, strikes
        are cleared.
        """
        with self._lock:
            if self._strikes.get(voter_name, 0) == 0:
                return
            progress = self._recovery_progress.get(voter_name, 0) + 1
            if progress >= self._config.recovery_threshold:
                self._strikes.pop(voter_name, None)
                self._recovery_progress.pop(voter_name, None)
            else:
                self._recovery_progress[voter_name] = progress

    def get_strikes(self, voter_name: str) -> int:
        with self._lock:
            return self._strikes.get(voter_name, 0)

    def should_skip(self, voter_name: str) -> bool:
        """Determine whether a voter should be skipped due to hung status.

        A voter is skipped when:
            1. skip_on_strikes is True, AND
            2. strikes >= max_strikes
        """
        if not self._config.skip_on_strikes:
            return False
        with self._lock:
            return self._strikes.get(voter_name, 0) >= self._config.max_strikes

    def get_timeout_multiplier(self, voter_name: str) -> float:
        """Compute the exponential backoff multiplier for a voter.

        Returns:
            base_timeout * (backoff_factor ^ strikes)

        Example with defaults (backoff_factor=2.0):
            strikes=0 → 1.0x
            strikes=1 → 2.0x
            strikes=2 → 4.0x
            strikes=3 → 8.0x (then skipped)
        """
        with self._lock:
            strikes = self._strikes.get(voter_name, 0)
            return self._config.backoff_factor ** strikes

    def build_skip_vote(
        self,
        voter_name: str,
        strikes: int | None = None,
    ) -> tuple:
        """Build a tuple of (decision, confidence, reason) for a skipped vote.

        Returns:
            (VoteDecision, confidence, reason)
        """
        from app.core.consensus import VoteDecision  # avoid circular

        if strikes is None:
            strikes = self.get_strikes(voter_name)
        return (
            VoteDecision(self._config.skip_vote_decision),
            self._config.skip_vote_confidence,
            f"{self._config.skip_vote_reason} (strikes={strikes})",
        )

    def reset(self) -> None:
        """Reset all strikes and recovery progress."""
        with self._lock:
            self._strikes.clear()
            self._recovery_progress.clear()
