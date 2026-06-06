"""
ConsensusEngine V1 — Deterministic consensus for module progression.

Architecture:
    ConsensusEngine orchestrates multiple Voters, each producing a ConsensusVote.
    Votes are aggregated into a ConsensusResult with deterministic decision logic.

    Voters:
        MasteryVoter  — Based on evaluation score vs mastery threshold
        PrereqVoter   — Checks prerequisite module completion
        SequenceVoter — Ensures sequential ordering
        TimeVoter     — Minimum engagement time check (V1: heuristic)

    Deterministic: same inputs → same outputs (no LLMs, no randomness).
    Async-safe: uses UnitOfWork, advisory locks, no shared mutable state.
    Idempotent: locked by (module_id, student_id), voters are pure functions of DB state.
    Auditable: every vote records voter_name, decision, confidence, reason, evidence.
"""

from __future__ import annotations

import abc
import asyncio
import logging
import time
import warnings
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from app.db.uow import UnitOfWork
from app.models.student_progress import LearningPath, PathModule

logger = logging.getLogger(__name__)


class VoteDecision(str, Enum):
    APPROVE = "approve"
    REJECT = "reject"
    ABSTAIN = "abstain"


class TimeoutAction(str, Enum):
    """Action taken when a voter times out during consensus."""

    NONE = "none"
    USE_FALLBACK_VOTE = "use_fallback_vote"
    SKIP_VOTER = "skip_voter"
    TRIGGER_DEGRADED = "trigger_degraded"
    HUNG_RECOVERY = "hung_recovery"
    EMERGENCY_QUORUM = "emergency_quorum"
    DEADLINE_EXCEEDED = "deadline_exceeded"
    CASCADE_CANCEL = "cascade_cancel"


@dataclass
class ConsensusVote:
    """A single vote from one voter in the consensus process."""

    voter_name: str
    decision: VoteDecision
    confidence: float = 1.0
    reason: str = ""
    evidence: dict = field(default_factory=dict)

    def __post_init__(self):
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(
                f"confidence must be in [0,1], got {self.confidence}"
            )


@dataclass
class ConsensusResult:
    """Aggregated result of the consensus process."""

    module_id: str
    student_id: str
    decision: VoteDecision
    confidence: float
    votes: list[ConsensusVote] = field(default_factory=list)
    computed_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    trace_id: str | None = None
    voter_timings: list[dict] = field(default_factory=list)
    weights_used: dict[str, float] = field(default_factory=dict)
    trust_scores: dict[str, float] = field(default_factory=dict)
    specialization_affinities: dict[str, float] = field(default_factory=dict)
    memory_ids: list[str] = field(default_factory=list)
    """IDs of SharedMemoryRecords published during this run."""
    inference_ids: list[str] = field(default_factory=list)
    """IDs of CollectiveInferences generated from this run."""
    timeout_info: dict | None = None
    """Timeout/deadline/degraded state from the timeout policy, if used."""

    @property
    def unanimous(self) -> bool:
        return (
            len(self.votes) > 0
            and all(v.decision == self.votes[0].decision for v in self.votes)
        )

    @property
    def approve_ratio(self) -> float:
        if not self.votes:
            return 0.0
        approvals = sum(
            1 for v in self.votes if v.decision == VoteDecision.APPROVE
        )
        non_abstain = sum(
            1 for v in self.votes if v.decision != VoteDecision.ABSTAIN
        )
        return approvals / non_abstain if non_abstain > 0 else 0.0

    @property
    def reject_ratio(self) -> float:
        if not self.votes:
            return 0.0
        rejects = sum(
            1 for v in self.votes if v.decision == VoteDecision.REJECT
        )
        non_abstain = sum(
            1 for v in self.votes if v.decision != VoteDecision.ABSTAIN
        )
        return rejects / non_abstain if non_abstain > 0 else 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "module_id": self.module_id,
            "student_id": self.student_id,
            "decision": self.decision.value,
            "confidence": self.confidence,
            "unanimous": self.unanimous,
            "approve_ratio": self.approve_ratio,
            "reject_ratio": self.reject_ratio,
            "num_votes": len(self.votes),
            "votes": [
                {
                    "voter_name": v.voter_name,
                    "decision": v.decision.value,
                    "confidence": v.confidence,
                    "reason": v.reason,
                    "evidence": v.evidence,
                }
                for v in self.votes
            ],
            "computed_at": self.computed_at.isoformat(),
            "trace_id": self.trace_id,
            "voter_timings": self.voter_timings,
            "weights_used": self.weights_used,
            "trust_scores": self.trust_scores,
            "specialization_affinities": self.specialization_affinities,
            "memory_ids": list(self.memory_ids),
            "inference_ids": list(self.inference_ids),
            "timeout_info": self.timeout_info,
        }


@dataclass
class VoteContext:
    """Context provided to every voter for decision-making."""

    uow: UnitOfWork
    student_id: str
    module_id: str
    path_id: str
    course_id: str
    score: float
    module: PathModule
    path: LearningPath
    evidence: dict = field(default_factory=dict)
    """Evidence dict for specialized voters (code_correctness, ct_score, concept, etc.)."""
    timestamp: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    shared_memory: list | None = None
    """Shared memory records relevant to this decision."""

    def __post_init__(self):
        if not 0.0 <= self.score <= 1.0:
            raise ValueError(
                f"score must be in [0,1], got {self.score}"
            )


class BaseVoter(abc.ABC):
    """Abstract base for all consensus voters."""

    @property
    @abc.abstractmethod
    def voter_name(self) -> str:
        """Unique name identifying this voter."""

    @abc.abstractmethod
    def vote(self, ctx: VoteContext) -> ConsensusVote:
        """Produce a vote based on the context.

        Must be deterministic: same ctx → same vote.
        Must not have side effects outside the current UoW transaction.
        """


class MasteryVoter(BaseVoter):
    """Votes based on evaluation score vs mastery threshold.

    - score >= 0.6 → APPROVE (confidence proportional to score)
    - score >= 0.4 → ABSTAIN (borderline, let other voters decide)
    - score < 0.4  → REJECT (insufficient mastery)
    """

    def __init__(
        self,
        approve_threshold: float = 0.6,
        reject_threshold: float = 0.4,
    ):
        if not 0 <= reject_threshold <= approve_threshold <= 1:
            raise ValueError(
                f"Expected 0 <= reject_threshold ({reject_threshold}) "
                f"<= approve_threshold ({approve_threshold}) <= 1"
            )
        self._approve_threshold = approve_threshold
        self._reject_threshold = reject_threshold

    @property
    def voter_name(self) -> str:
        return "mastery"

    def vote(self, ctx: VoteContext) -> ConsensusVote:
        score = ctx.score

        if score >= self._approve_threshold:
            return ConsensusVote(
                voter_name=self.voter_name,
                decision=VoteDecision.APPROVE,
                confidence=min(score, 1.0),
                reason=(
                    f"Score {score:.2f} >= "
                    f"approve threshold {self._approve_threshold}"
                ),
                evidence={
                    "score": score,
                    "threshold": self._approve_threshold,
                },
            )

        if score < self._reject_threshold:
            return ConsensusVote(
                voter_name=self.voter_name,
                decision=VoteDecision.REJECT,
                confidence=1.0 - score,
                reason=(
                    f"Score {score:.2f} < "
                    f"reject threshold {self._reject_threshold}"
                ),
                evidence={
                    "score": score,
                    "threshold": self._reject_threshold,
                },
            )

        return ConsensusVote(
            voter_name=self.voter_name,
            decision=VoteDecision.ABSTAIN,
            confidence=0.5,
            reason=(
                f"Score {score:.2f} in borderline zone "
                f"[{self._reject_threshold}, {self._approve_threshold})"
            ),
            evidence={
                "score": score,
                "approve_threshold": self._approve_threshold,
                "reject_threshold": self._reject_threshold,
            },
        )


class PrereqVoter(BaseVoter):
    """Votes based on prerequisite module completion.

    Checks that all lower-order modules in the same path
    are completed before allowing progression.
    """

    @property
    def voter_name(self) -> str:
        return "prerequisite"

    def vote(self, ctx: VoteContext) -> ConsensusVote:
        db = ctx.uow.db

        incomplete_prereqs = (
            db.query(PathModule)
            .filter(
                PathModule.path_id == ctx.path_id,
                PathModule.order < ctx.module.order,
                PathModule.status != "completed",
            )
            .count()
        )

        if incomplete_prereqs == 0:
            return ConsensusVote(
                voter_name=self.voter_name,
                decision=VoteDecision.APPROVE,
                confidence=1.0,
                reason="All prerequisite modules completed",
                evidence={
                    "incomplete_prereqs": 0,
                    "module_order": ctx.module.order,
                },
            )

        prereq_list = (
            db.query(PathModule)
            .filter(
                PathModule.path_id == ctx.path_id,
                PathModule.order < ctx.module.order,
                PathModule.status != "completed",
            )
            .order_by(PathModule.order)
            .all()
        )

        return ConsensusVote(
            voter_name=self.voter_name,
            decision=VoteDecision.REJECT,
            confidence=1.0,
            reason=(
                f"{incomplete_prereqs} prerequisite module(s) "
                f"not completed"
            ),
            evidence={
                "incomplete_prereqs": incomplete_prereqs,
                "module_order": ctx.module.order,
                "prerequisite_titles": [m.title for m in prereq_list],
                "prerequisite_ids": [m.id for m in prereq_list],
            },
        )


class SequenceVoter(BaseVoter):
    """Votes based on sequential ordering.

    Ensures modules are completed in order (no skipping ahead).
    """

    @property
    def voter_name(self) -> str:
        return "sequence"

    def vote(self, ctx: VoteContext) -> ConsensusVote:
        db = ctx.uow.db
        module = ctx.module

        if module.status == "completed":
            return ConsensusVote(
                voter_name=self.voter_name,
                decision=VoteDecision.ABSTAIN,
                confidence=1.0,
                reason="Module already completed",
                evidence={
                    "module_status": module.status,
                    "module_order": module.order,
                },
            )

        if module.order > 1:
            prev_module = (
                db.query(PathModule)
                .filter(
                    PathModule.path_id == ctx.path_id,
                    PathModule.order == module.order - 1,
                )
                .first()
            )
            if prev_module and prev_module.status != "completed":
                return ConsensusVote(
                    voter_name=self.voter_name,
                    decision=VoteDecision.REJECT,
                    confidence=1.0,
                    reason=(
                        f"Previous module '{prev_module.title}' "
                        f"(order {module.order - 1}) not completed"
                    ),
                    evidence={
                        "previous_module_id": prev_module.id,
                        "previous_module_title": prev_module.title,
                        "previous_module_status": prev_module.status,
                        "module_order": module.order,
                    },
                )

        return ConsensusVote(
            voter_name=self.voter_name,
            decision=VoteDecision.APPROVE,
            confidence=1.0,
            reason=(
                f"Module order {module.order} "
                f"is valid for progression"
            ),
            evidence={
                "module_order": module.order,
                "module_status": module.status,
            },
        )


class TimeVoter(BaseVoter):
    """Votes based on minimum engagement time.

    V1: heuristic — always approve with moderate confidence.
    Future: check actual time spent via engagement events.
    """

    @property
    def voter_name(self) -> str:
        return "time"

    def vote(self, ctx: VoteContext) -> ConsensusVote:
        return ConsensusVote(
            voter_name=self.voter_name,
            decision=VoteDecision.APPROVE,
            confidence=0.6,
            reason=(
                "V1 time heuristic: minimum engagement assumed "
                "(no real-time tracking yet)"
            ),
            evidence={"voter_version": "v1_heuristic"},
        )


class ConsensusEngine:
    """Orchestrates consensus for module progression decisions.

    Runs all registered voters and aggregates their votes into
    a deterministic ConsensusResult.

    Decision aggregation rules:
        Any REJECT vote     → overall REJECT
        All ABSTAIN         → overall ABSTAIN
        All APPROVE         → overall APPROVE (unanimous)
        Majority APPROVE    → overall APPROVE (with proportional confidence)
    """

    def __init__(self, voters: list[BaseVoter] | None = None):
        self._voters: list[BaseVoter] = voters or [
            MasteryVoter(),
            PrereqVoter(),
            SequenceVoter(),
            TimeVoter(),
        ]

    @property
    def voters(self) -> list[BaseVoter]:
        return list(self._voters)

    def register_voter(self, voter: BaseVoter) -> None:
        self._voters.append(voter)

    def run(
        self,
        ctx: VoteContext,
        trace_ctx: Any | None = None,
        propagation_ctx: Any | None = None,
        trust_system: Any | None = None,
        specialization_tracker: Any | None = None,
        shared_memory_store: Any | None = None,
        timeout_policy: Any | None = None,
    ) -> ConsensusResult:
        """Run consensus: gather votes, aggregate decision.

        Deterministic: voters are executed in fixed order.
        Async-safe: no shared mutable state between voters.

        Args:
            ctx: Vote context with all decision inputs.
            trace_ctx: Optional TraceContext for observability.
                       If provided, each voter is timed and results
                       are attached to the ConsensusResult.
            propagation_ctx: Optional PropagationContext for distributed
                             tracing. If provided, creates a child span
                             and derives trace_ctx from it.
            trust_system: Optional TrustSystem for adaptive trust scoring.
                          When provided, each voter's trust score is used
                          as weight, and scores are updated post-decision.
            specialization_tracker: Optional SpecializationTracker for
                                    domain-specific affinity scores.
            shared_memory_store: Optional SharedMemoryStore for collective
                                 memory. When provided, relevant memory
                                 records are attached to ctx before voting,
                                 and each vote is published as an observation
                                 after decision.
        """
        warnings.warn(
            "ConsensusEngine.run() is deprecated. "
            "Use async_run() from async callers; "
            "wrap with asyncio.run() from sync callers that have no running event loop.",
            DeprecationWarning,
            stacklevel=2,
        )

        votes: list[ConsensusVote] = []
        voter_timings: list[dict] = []
        trace_id: str | None = None

        # ── Derive trace_ctx from propagation_ctx ─────────────────
        if propagation_ctx is not None and trace_ctx is None:
            try:
                from app.tracing import correlation_engine as _ce
                _child = _ce.child(
                    operation_name="consensus:run",
                    tags={
                        "module_id": ctx.module_id[:20],
                        "student_id": ctx.student_id[:20],
                    },
                )
                if _child is not None:
                    trace_ctx = _child.to_legacy_trace_context()
            except Exception:
                pass

        # Auto-detect from active propagation context if not provided
        if propagation_ctx is None and trace_ctx is None:
            try:
                from app.tracing import correlation_engine as _ce
                current = _ce.get_current()
                if current is not None:
                    _child = _ce.child(
                        operation_name="consensus:run",
                        tags={
                            "module_id": ctx.module_id[:20],
                            "student_id": ctx.student_id[:20],
                        },
                    )
                    if _child is not None:
                        trace_ctx = _child.to_legacy_trace_context()
                        propagation_ctx = True
            except Exception:
                pass

        if trace_ctx is not None:
            trace_id = trace_ctx.trace_id

        # ── Initialize timeout policy state ────────────────────
        tmo_state = None
        if timeout_policy is not None:
            tmo_state = timeout_policy.create_state()
            timeout_policy.check_overall_deadline(tmo_state)

        # ── Enrich context with shared memory ────────────────────
        memory_ids: list[str] = []
        inference_ids: list[str] = []

        if shared_memory_store is not None:
            logger.warning(
                "Consensus.run() received shared_memory_store=%s — sync method "
                "cannot await async store methods. Memory enrichment and "
                "publication are SKIPPED. Use async_run() for shared memory.",
                type(shared_memory_store).__name__,
            )
            shared_memory_store = None  # type: ignore[assignment]
            ctx.shared_memory = []

        for voter in self._voters:
            start_ns = time.monotonic_ns() if (trace_ctx is not None or tmo_state is not None) else 0

            # ── Skip if deadline exceeded or degraded ──────────
            if tmo_state is not None and tmo_state.deadline_exceeded:
                v = ConsensusVote(
                    voter_name=voter.voter_name,
                    decision=VoteDecision.ABSTAIN,
                    confidence=0.0,
                    reason="Skipped — overall consensus deadline exceeded",
                    evidence={"deadline_exceeded": True, "elapsed_ms": tmo_state.elapsed_ms()},
                )
                elapsed_ms = 0.0
                status = "deadline_skipped"
                timeout_policy.record_voter_result(
                    tmo_state, voter.voter_name, elapsed_ms,
                    timed_out=True, reason="Deadline exceeded",
                )
                votes.append(v)
                if trace_ctx is not None:
                    voter_timings.append({
                        "voter_name": voter.voter_name,
                        "decision": v.decision.value,
                        "confidence": v.confidence,
                        "duration_ms": 0.0,
                        "status": status,
                        "timeout": True,
                    })
                continue

            try:
                v = voter.vote(ctx)
                if trace_ctx is not None or tmo_state is not None:
                    elapsed_ms = (time.monotonic_ns() - start_ns) / 1_000_000
                else:
                    elapsed_ms = 0.0

                # ── Check voter timeout ────────────────────────
                timed_out = False
                timeout_action = "none"
                if tmo_state is not None:
                    is_timed_out, action = timeout_policy.check_voter(
                        tmo_state, voter.voter_name, elapsed_ms,
                    )
                    if is_timed_out:
                        timed_out = True
                        timeout_action = action.value
                        # Record the timeout in state
                        timeout_policy.record_voter_result(
                            tmo_state, voter.voter_name, elapsed_ms,
                            timed_out=True, action=action, reason=action.value,
                        )
                        # Determine fallback vote
                        if action.value in ("hung_recovery", "use_fallback_vote", "deadline_exceeded"):
                            v = timeout_policy.build_fallback_vote(
                                tmo_state, voter.voter_name,
                                reason=f"Timed out ({action.value}) after {elapsed_ms:.0f}ms",
                            )
                        elif action.value == "skip_voter":
                            continue
                    else:
                        timeout_policy.record_voter_duration(voter.voter_name, elapsed_ms)
                        timeout_policy.record_voter_result(
                            tmo_state, voter.voter_name, elapsed_ms,
                        )

                logger.debug(
                    "Consensus[%s/%s]: voter=%s decision=%s "
                    "confidence=%.2f reason=%s%s",
                    ctx.module_id[:8],
                    ctx.student_id[:8],
                    voter.voter_name,
                    v.decision.value,
                    v.confidence,
                    v.reason,
                    " [TIMEOUT]" if timed_out else "",
                )
                votes.append(v)
                if trace_ctx is not None:
                    timing_entry: dict[str, Any] = {
                        "voter_name": voter.voter_name,
                        "decision": v.decision.value,
                        "confidence": v.confidence,
                        "duration_ms": round(elapsed_ms, 3),
                        "status": "timeout" if timed_out else "ok",
                    }
                    if timed_out:
                        timing_entry["timeout"] = True
                        timing_entry["timeout_action"] = timeout_action
                    voter_timings.append(timing_entry)

                # Check cascading delay after each voter
                if tmo_state is not None and not tmo_state.cascading_delay_detected:
                    timings_sofar = [t.get("duration_ms", 0.0) for t in voter_timings]
                    timeout_policy.check_cascading_delay(tmo_state, timings_sofar)

                # Check overall deadline after each voter
                if tmo_state is not None:
                    timeout_policy.check_overall_deadline(tmo_state)

            except Exception as exc:
                if trace_ctx is not None or tmo_state is not None:
                    elapsed_ms = (time.monotonic_ns() - start_ns) / 1_000_000
                else:
                    elapsed_ms = 0.0
                logger.error(
                    "Consensus[%s/%s]: voter=%s failed: %s",
                    ctx.module_id[:8],
                    ctx.student_id[:8],
                    voter.voter_name,
                    exc,
                    exc_info=True,
                )

                # Voter error is treated as a timeout — use fallback
                if tmo_state is not None:
                    timeout_policy.record_voter_result(
                        tmo_state, voter.voter_name, elapsed_ms,
                        timed_out=True,
                        action=TimeoutAction.USE_FALLBACK_VOTE,
                        reason=f"Voter error: {exc}",
                    )

                votes.append(
                    ConsensusVote(
                        voter_name=voter.voter_name,
                        decision=VoteDecision.ABSTAIN,
                        confidence=0.0,
                        reason=f"Voter error: {exc}",
                        evidence={"error": str(exc)},
                    )
                )
                if trace_ctx is not None:
                    voter_timings.append({
                        "voter_name": voter.voter_name,
                        "decision": "abstain",
                        "confidence": 0.0,
                        "duration_ms": round(elapsed_ms, 3),
                        "status": "error",
                        "error": str(exc),
                    })
                # Record error in trust system
                if trust_system is not None:
                    trust_system.record_error(voter.voter_name)

        # ── Final timeout state checks ──────────────────────────
        if tmo_state is not None:
            timeout_policy.check_overall_deadline(tmo_state)
            completed_count = sum(
                1 for r in tmo_state.voter_records.values() if not r.timed_out
            )
            timeout_policy.check_degraded(tmo_state, completed_count, len(self._voters))
            if not timeout_policy.is_quorum_met(tmo_state, completed_count):
                timeout_policy.trigger_quorum_fallback(tmo_state, completed_count)

            # Attach timeout baggage to propagation_ctx if available
            if propagation_ctx is not None:
                try:
                    baggage = timeout_policy.to_baggage(tmo_state)
                    for k, v in baggage.items():
                        if hasattr(propagation_ctx, "set_baggage"):
                            propagation_ctx.set_baggage(k, v)
                except Exception:
                    pass

        # ── Compute adaptive weights ─────────────────────────────
        voter_names = [v.voter_name for v in self._voters]
        weights_used: dict[str, float] = {}
        trust_scores: dict[str, float] = {}
        specialization_affinities: dict[str, float] = {}

        if trust_system is not None or specialization_tracker is not None:
            from app.core.weighting import compute_weights_detailed

            ctx_key = None
            if specialization_tracker is not None:
                from app.core.specialization import context_key as spec_ctx_key
                ctx_key = spec_ctx_key(ctx)

            weight_details = compute_weights_detailed(
                voter_names,
                trust_system=trust_system,
                specialization_tracker=specialization_tracker,
                context_key=ctx_key,
            )
            for name in voter_names:
                weights_used[name] = weight_details[name]["final_weight"]
                trust_scores[name] = weight_details[name]["trust"]
                specialization_affinities[name] = weight_details[name]["affinity"]

        # ── Aggregate with weights ───────────────────────────────
        weights_for_agg = weights_used if weights_used else None
        decision, confidence = self._aggregate(votes, weights=weights_for_agg)

        # ── Update trust and specialization post-decision ─────────
        if trust_system is not None:
            for vote in votes:
                trust_system.record_vote_outcome(
                    voter_name=vote.voter_name,
                    decision=vote.decision,
                    confidence=vote.confidence,
                    latency_ms=next(
                        (t.get("duration_ms", 0.0) for t in voter_timings
                         if t.get("voter_name") == vote.voter_name),
                        0.0,
                    ),
                    final_decision=decision,
                )

        if specialization_tracker is not None:
            ctx_key = None
            if specialization_tracker is not None:
                from app.core.specialization import context_key as spec_ctx_key
                ctx_key = spec_ctx_key(ctx)
            for vote in votes:
                if vote.decision == VoteDecision.ABSTAIN:
                    continue  # abstentions don't affect specialization
                agreed = vote.decision == decision
                specialization_tracker.record_vote(
                    voter_name=vote.voter_name,
                    context_key=ctx_key,
                    agreed_with_consensus=agreed,
                )

        # ── Shared memory publication skipped in sync run() ─────
        # Use async_run() which properly awaits publish_observation().

        result = ConsensusResult(
            module_id=ctx.module_id,
            student_id=ctx.student_id,
            decision=decision,
            confidence=confidence,
            votes=votes,
            trace_id=trace_id,
            voter_timings=voter_timings,
            weights_used=weights_used,
            trust_scores=trust_scores,
            specialization_affinities=specialization_affinities,
            memory_ids=memory_ids,
            inference_ids=inference_ids,
            timeout_info=(
                timeout_policy.get_state_summary(tmo_state)
                if timeout_policy is not None and tmo_state is not None
                else None
            ),
        )

        if trace_ctx is not None:
            latency = sum(t.get("duration_ms", 0) for t in voter_timings)
            logger.info(
                "Consensus[%s/%s]: decision=%s confidence=%.2f votes=%d "
                "trace=%s latency=%.2fms weights=%s",
                ctx.module_id[:8],
                ctx.student_id[:8],
                decision.value,
                confidence,
                len(votes),
                trace_id[:8],
                latency,
                {k: round(v, 3) for k, v in weights_used.items()} if weights_used else "none",
            )

        # ── Record swarm diagnostics ─────────────────────────────
        try:
            from app.swarm_diagnostics import diagnostics_engine as _diag_engine
            _diag_engine.record_consensus(
                decision=decision.value,
                confidence=confidence,
                votes=[{
                    "voter_name": v.voter_name,
                    "decision": v.decision.value,
                    "confidence": v.confidence,
                } for v in votes],
                student_id=ctx.student_id,
                module_id=ctx.module_id,
                trace_id=trace_id,
                duration_ms=latency if trace_ctx else None,
            )
            for v in votes:
                timing = next(
                    (t for t in voter_timings if t.get("voter_name") == v.voter_name),
                    None,
                )
                _diag_engine.record_vote(
                    voter_name=v.voter_name,
                    decision=v.decision.value,
                    confidence=v.confidence,
                    student_id=ctx.student_id,
                    module_id=ctx.module_id,
                    trace_id=trace_id,
                    duration_ms=timing.get("duration_ms") if timing else None,
                )
        except Exception:
            logger.debug("Swarm diagnostics recording failed (non-fatal)", exc_info=True)

        # ── End propagation span ─────────────────────────────────
        if propagation_ctx is not None:
            try:
                from app.tracing import correlation_engine as _ce
                _ce.end()
            except Exception:
                pass

        return result

    async def async_run(
        self,
        ctx: VoteContext,
        trace_ctx: Any | None = None,
        propagation_ctx: Any | None = None,
        trust_system: Any | None = None,
        specialization_tracker: Any | None = None,
        shared_memory_store: Any | None = None,
        timeout_policy: Any | None = None,
        per_voter_timeout_ms: float | None = None,
        overall_deadline_ms: float | None = None,
    ) -> ConsensusResult:
        """Async consensus with per-voter asyncio-based preemption.

        Functionally IDENTICAL to run() for the same inputs:
        - same adaptive weights (trust system + specialization)
        - same shared memory enrichment + publication
        - same diagnostics recording
        - same propagation span management

        Additionally adds per-voter asyncio timeout via wait_for(),
        enabling preemptive cancellation of hung voters.

        Args:
            ctx: Vote context.
            trace_ctx: Optional trace context.
            propagation_ctx: Optional propagation context.
            trust_system: Optional trust system.
            specialization_tracker: Optional specialization tracker.
            shared_memory_store: Optional shared memory store.
            timeout_policy: Optional ConsensusTimeoutPolicy.
            per_voter_timeout_ms: Per-voter timeout in ms (default 5000).
            overall_deadline_ms: Overall deadline in ms (default 30000).

        Returns:
            A ConsensusResult with all fields populated identically to run().
        """
        from app.core.consensus_cancellation import (
            CancellationReason,
            ConsensusCancellationContext,
            set_current_cancellation_ctx,
        )
        from app.core.consensus_timeouts import ConsensusTimeoutPolicy

        pvt = per_voter_timeout_ms or 5000.0
        odl = overall_deadline_ms or 30000.0
        deadline_ns = time.monotonic_ns() + int(odl * 1_000_000)

        use_tmo = timeout_policy or (
            ConsensusTimeoutPolicy() if timeout_policy is not None else None
        )
        tmo_state = use_tmo.create_state() if use_tmo else None

        cancel_ctx = ConsensusCancellationContext()
        cancel_ctx.remaining_voters = [v.voter_name for v in self._voters]
        _prev_token = set_current_cancellation_ctx(cancel_ctx)

        votes: list[ConsensusVote] = []
        voter_timings: list[dict] = []
        trace_id: str | None = None

        # ── Derive trace_ctx from propagation_ctx (same as run()) ─
        if propagation_ctx is not None and trace_ctx is None:
            try:
                from app.tracing import correlation_engine as _ce
                _child = _ce.child(
                    operation_name="consensus:async_run",
                    tags={
                        "module_id": ctx.module_id[:20],
                        "student_id": ctx.student_id[:20],
                    },
                )
                if _child is not None:
                    trace_ctx = _child.to_legacy_trace_context()
            except Exception:
                pass

        if propagation_ctx is None and trace_ctx is None:
            try:
                from app.tracing import correlation_engine as _ce
                current = _ce.get_current()
                if current is not None:
                    _child = _ce.child(
                        operation_name="consensus:async_run",
                        tags={
                            "module_id": ctx.module_id[:20],
                            "student_id": ctx.student_id[:20],
                        },
                    )
                    if _child is not None:
                        trace_ctx = _child.to_legacy_trace_context()
                        propagation_ctx = True
            except Exception:
                pass

        if trace_ctx is not None:
            trace_id = trace_ctx.trace_id

        # ── Enrich context with shared memory (same as run()) ────
        memory_ids: list[str] = []
        inference_ids: list[str] = []

        if shared_memory_store is not None and ctx.shared_memory is None:
            try:
                ctx.shared_memory = await shared_memory_store.query(
                    student_id=ctx.student_id,
                    module_id=ctx.module_id,
                    limit=30,
                    propagation_ctx=propagation_ctx,
                )
            except Exception:
                logger.warning(
                    "Consensus[%s/%s]: shared memory query failed",
                    ctx.module_id[:8], ctx.student_id[:8],
                )
                ctx.shared_memory = []

        try:
            for voter in self._voters:
                vname = voter.voter_name
                start_ns = time.monotonic_ns()

                # Deadline check
                if time.monotonic_ns() >= deadline_ns:
                    cancel_ctx.cancel(CancellationReason.OVERALL_DEADLINE, source=vname)
                    if tmo_state:
                        tmo_state.deadline_exceeded = True
                    v = ConsensusVote(
                        voter_name=vname,
                        decision=VoteDecision.ABSTAIN,
                        confidence=0.0,
                        reason="Skipped — overall deadline exceeded",
                        evidence={"deadline_exceeded": True},
                    )
                    votes.append(v)
                    voter_timings.append({
                        "voter_name": vname, "decision": v.decision.value,
                        "confidence": v.confidence, "duration_ms": 0.0,
                        "status": "deadline_skipped", "timeout": True,
                    })
                    continue

                # Hung check from timeout policy
                if use_tmo and tmo_state and tmo_state.deadline_exceeded:
                    v = ConsensusVote(
                        voter_name=vname,
                        decision=VoteDecision.ABSTAIN,
                        confidence=0.0,
                        reason="Skipped — deadline exceeded",
                        evidence={"deadline_exceeded": True},
                    )
                    votes.append(v)
                    voter_timings.append({
                        "voter_name": vname, "decision": v.decision.value,
                        "confidence": v.confidence, "duration_ms": 0.0,
                        "status": "deadline_skipped", "timeout": True,
                    })
                    continue

                try:
                    v = await asyncio.wait_for(
                        asyncio.to_thread(voter.vote, ctx),
                        timeout=pvt / 1000.0,
                    )
                    elapsed_ms = (time.monotonic_ns() - start_ns) / 1_000_000

                    if cancel_ctx.cancelled:
                        if use_tmo and tmo_state:
                            use_tmo.record_voter_result(
                                tmo_state, vname, elapsed_ms,
                                timed_out=True,
                                action=TimeoutAction.CASCADE_CANCEL,
                            )
                            v = use_tmo.build_fallback_vote(
                                tmo_state, vname,
                                reason=f"Cancelled ({cancel_ctx.token.reason.value})",
                            )
                        status = "cancelled"
                    else:
                        if use_tmo and tmo_state:
                            use_tmo.record_voter_result(tmo_state, vname, elapsed_ms)
                            use_tmo.record_voter_duration(vname, elapsed_ms)
                        cancel_ctx.mark_completed(vname)
                        status = "ok"

                except asyncio.TimeoutError:
                    elapsed_ms = (time.monotonic_ns() - start_ns) / 1_000_000
                    cancel_ctx.mark_timed_out(vname)
                    if use_tmo and tmo_state:
                        use_tmo.record_voter_result(
                            tmo_state, vname, elapsed_ms,
                            timed_out=True,
                            action=TimeoutAction.USE_FALLBACK_VOTE,
                        )
                        v = use_tmo.build_fallback_vote(
                            tmo_state, vname,
                            reason=f"Async timeout after {elapsed_ms:.0f}ms",
                        )
                    else:
                        v = ConsensusVote(
                            voter_name=vname,
                            decision=VoteDecision.ABSTAIN,
                            confidence=0.0,
                            reason=f"Async timeout after {elapsed_ms:.0f}ms",
                            evidence={"timeout": True, "timeout_ms": pvt},
                        )
                    status = "timeout"

                except Exception as exc:
                    elapsed_ms = (time.monotonic_ns() - start_ns) / 1_000_000
                    logger.error("Voter %s failed: %s", vname, exc, exc_info=True)
                    if use_tmo and tmo_state:
                        use_tmo.record_voter_result(
                            tmo_state, vname, elapsed_ms,
                            timed_out=True,
                            action=TimeoutAction.USE_FALLBACK_VOTE,
                            reason=f"Voter error: {exc}",
                        )
                    v = ConsensusVote(
                        voter_name=vname,
                        decision=VoteDecision.ABSTAIN,
                        confidence=0.0,
                        reason=f"Voter error: {exc}",
                        evidence={"error": str(exc)},
                    )
                    status = "error"
                    # Record error in trust system (same as run())
                    if trust_system is not None:
                        trust_system.record_error(vname)

                votes.append(v)
                voter_timings.append({
                    "voter_name": vname,
                    "decision": v.decision.value,
                    "confidence": v.confidence,
                    "duration_ms": round(elapsed_ms, 3),
                    "status": status,
                    "timeout": status in ("timeout", "cancelled", "deadline_skipped"),
                })

                # Check cascading delay after each voter
                if use_tmo and tmo_state and len(voter_timings) >= 2:
                    timings = [t.get("duration_ms", 0.0) for t in voter_timings[:-1]]
                    use_tmo.check_cascading_delay(tmo_state, timings)

                # Check overall deadline after each voter (same as run())
                if use_tmo and tmo_state:
                    use_tmo.check_overall_deadline(tmo_state)

            # ── Final timeout state checks (same as run()) ───────
            timeout_info = None
            if use_tmo and tmo_state:
                use_tmo.check_overall_deadline(tmo_state)
                completed_count = sum(
                    1 for r in tmo_state.voter_records.values() if not r.timed_out
                )
                use_tmo.check_degraded(tmo_state, completed_count, len(self._voters))
                if not use_tmo.is_quorum_met(tmo_state, completed_count):
                    use_tmo.trigger_quorum_fallback(tmo_state, completed_count)

                # Attach timeout baggage to propagation_ctx (same as run())
                if propagation_ctx is not None:
                    try:
                        baggage = use_tmo.to_baggage(tmo_state)
                        for k, v in baggage.items():
                            if hasattr(propagation_ctx, "set_baggage"):
                                propagation_ctx.set_baggage(k, v)
                    except Exception:
                        pass

                timeout_info = use_tmo.get_state_summary(tmo_state)

            # ── Compute adaptive weights (same as run()) ──────────
            voter_names = [v.voter_name for v in self._voters]
            weights_used: dict[str, float] = {}
            trust_scores: dict[str, float] = {}
            specialization_affinities: dict[str, float] = {}

            if trust_system is not None or specialization_tracker is not None:
                from app.core.weighting import compute_weights_detailed

                ctx_key = None
                if specialization_tracker is not None:
                    from app.core.specialization import context_key as spec_ctx_key
                    ctx_key = spec_ctx_key(ctx)

                weight_details = compute_weights_detailed(
                    voter_names,
                    trust_system=trust_system,
                    specialization_tracker=specialization_tracker,
                    context_key=ctx_key,
                )
                for name in voter_names:
                    weights_used[name] = weight_details[name]["final_weight"]
                    trust_scores[name] = weight_details[name]["trust"]
                    specialization_affinities[name] = weight_details[name]["affinity"]

            # ── Aggregate with weights (same as run()) ────────────
            weights_for_agg = weights_used if weights_used else None
            decision, confidence = self._aggregate(votes, weights=weights_for_agg)

            # ── Update trust and specialization post-decision (same as run()) ──
            if trust_system is not None:
                for vote in votes:
                    trust_system.record_vote_outcome(
                        voter_name=vote.voter_name,
                        decision=vote.decision,
                        confidence=vote.confidence,
                        latency_ms=next(
                            (t.get("duration_ms", 0.0) for t in voter_timings
                             if t.get("voter_name") == vote.voter_name),
                            0.0,
                        ),
                        final_decision=decision,
                    )

            if specialization_tracker is not None:
                ctx_key = None
                if specialization_tracker is not None:
                    from app.core.specialization import context_key as spec_ctx_key
                    ctx_key = spec_ctx_key(ctx)
                for vote in votes:
                    if vote.decision == VoteDecision.ABSTAIN:
                        continue
                    agreed = vote.decision == decision
                    specialization_tracker.record_vote(
                        voter_name=vote.voter_name,
                        context_key=ctx_key,
                        agreed_with_consensus=agreed,
                    )

            # ── Publish vote observations to shared memory (same as run()) ──
            if shared_memory_store is not None:
                try:
                    for vote in votes:
                        mem_key = f"vote:{vote.voter_name}:{ctx.module_id[:12]}"
                        rec_id = await shared_memory_store.publish_observation(
                            voter_name=vote.voter_name,
                            key=mem_key,
                            value={
                                "decision": vote.decision.value,
                                "confidence": vote.confidence,
                                "reason": vote.reason,
                                "evidence": vote.evidence,
                            },
                            confidence=vote.confidence,
                            student_id=ctx.student_id,
                            module_id=ctx.module_id,
                            memory_type="observation",
                            trace_ctx=trace_ctx,
                            propagation_ctx=propagation_ctx,
                            metadata_json={
                                "path_id": ctx.path_id,
                                "course_id": ctx.course_id,
                                "consensus_decision": decision.value,
                                "consensus_confidence": confidence,
                            },
                        )
                        memory_ids.append(rec_id)

                    result_key = f"consensus:{ctx.module_id[:12]}"
                    rec_id = await shared_memory_store.publish_observation(
                        voter_name="_engine",
                        key=result_key,
                        value={
                            "decision": decision.value,
                            "confidence": confidence,
                            "num_votes": len(votes),
                            "unanimous": decision == VoteDecision.APPROVE and all(
                                v.decision == VoteDecision.APPROVE for v in votes
                            ),
                        },
                        confidence=confidence,
                        student_id=ctx.student_id,
                        module_id=ctx.module_id,
                        memory_type="inference",
                        trace_ctx=trace_ctx,
                        propagation_ctx=propagation_ctx,
                        ttl_seconds=86400 * 14,
                        metadata_json={
                            "voter_names": [v.voter_name for v in votes],
                            "voter_decisions": [v.decision.value for v in votes],
                        },
                    )
                    memory_ids.append(rec_id)

                    if ctx.shared_memory:
                        from app.memory.patterns import PatternDetector
                        detector = PatternDetector()
                        contradictions = detector.detect_contradictions(ctx.shared_memory)
                        for c in contradictions:
                            await shared_memory_store.publish_observation(
                                voter_name="_engine",
                                key=f"pattern:contradiction:{ctx.module_id[:8]}",
                                value={
                                    "contradiction_key": c.metadata.get("key"),
                                    "unique_values": c.metadata.get("unique_values"),
                                    "num_records": c.metadata.get("total_records"),
                                },
                                confidence=c.confidence,
                                student_id=ctx.student_id,
                                module_id=ctx.module_id,
                                memory_type="pattern",
                                trace_ctx=trace_ctx,
                                propagation_ctx=propagation_ctx,
                                ttl_seconds=86400 * 7,
                            )

                    if ctx.shared_memory and len(votes) >= 2:
                        try:
                            from app.memory.collective_inference import (
                                CollectiveInferenceEngine,
                            )
                            inf_engine = CollectiveInferenceEngine()
                            inference = inf_engine.infer_from_votes(
                                votes, result,
                                shared_memory_records=ctx.shared_memory,
                            )
                            inference_ids.append(inference.inference_id)
                            await shared_memory_store.publish_observation(
                                voter_name="_engine",
                                key=f"inference:{ctx.module_id[:12]}",
                                value=inference.to_dict(),
                                confidence=inference.confidence,
                                student_id=ctx.student_id,
                                module_id=ctx.module_id,
                                memory_type="inference",
                                trace_ctx=trace_ctx,
                                propagation_ctx=propagation_ctx,
                                ttl_seconds=86400 * 7,
                                metadata_json={
                                    "inference_id": inference.inference_id,
                                    "reasoning_chain": inference.reasoning_chain,
                                },
                            )
                        except Exception:
                            logger.warning(
                                "Consensus[%s/%s]: collective inference failed",
                                ctx.module_id[:8], ctx.student_id[:8],
                            )
                except Exception:
                    logger.warning(
                        "Consensus[%s/%s]: shared memory publish failed",
                        ctx.module_id[:8], ctx.student_id[:8],
                    )

            result = ConsensusResult(
                module_id=ctx.module_id,
                student_id=ctx.student_id,
                decision=decision,
                confidence=confidence,
                votes=votes,
                trace_id=trace_id,
                voter_timings=voter_timings,
                weights_used=weights_used,
                trust_scores=trust_scores,
                specialization_affinities=specialization_affinities,
                memory_ids=memory_ids,
                inference_ids=inference_ids,
                timeout_info=timeout_info,
            )

            # ── Log with weights (same as run()) ─────────────────
            if trace_ctx is not None:
                latency = sum(t.get("duration_ms", 0) for t in voter_timings)
                logger.info(
                    "Consensus[%s/%s]: decision=%s confidence=%.2f votes=%d "
                    "trace=%s latency=%.2fms weights=%s",
                    ctx.module_id[:8],
                    ctx.student_id[:8],
                    decision.value,
                    confidence,
                    len(votes),
                    trace_id[:8],
                    latency,
                    {k: round(v, 3) for k, v in weights_used.items()} if weights_used else "none",
                )

            # ── Record swarm diagnostics (same as run()) ─────────
            try:
                from app.swarm_diagnostics import diagnostics_engine as _diag_engine
                _diag_engine.record_consensus(
                    decision=decision.value,
                    confidence=confidence,
                    votes=[{
                        "voter_name": v.voter_name,
                        "decision": v.decision.value,
                        "confidence": v.confidence,
                    } for v in votes],
                    student_id=ctx.student_id,
                    module_id=ctx.module_id,
                    trace_id=trace_id,
                    duration_ms=latency if trace_ctx else None,
                )
                for v in votes:
                    timing = next(
                        (t for t in voter_timings if t.get("voter_name") == v.voter_name),
                        None,
                    )
                    _diag_engine.record_vote(
                        voter_name=v.voter_name,
                        decision=v.decision.value,
                        confidence=v.confidence,
                        student_id=ctx.student_id,
                        module_id=ctx.module_id,
                        trace_id=trace_id,
                        duration_ms=timing.get("duration_ms") if timing else None,
                    )
            except Exception:
                logger.debug("Swarm diagnostics recording failed (non-fatal)", exc_info=True)

            # ── End propagation span (same as run()) ─────────────
            if propagation_ctx is not None:
                try:
                    from app.tracing import correlation_engine as _ce
                    _ce.end()
                except Exception:
                    pass

            return result

        finally:
            set_current_cancellation_ctx(_prev_token)

    def _aggregate(
        self,
        votes: list[ConsensusVote],
        weights: dict[str, float] | None = None,
    ) -> tuple[VoteDecision, float]:
        """Deterministic vote aggregation with optional adaptive weights.

        When weights are provided, confidence is computed as a weighted
        average (trust-score-weighted). This makes high-trust voters
        have more influence on the final confidence value.

        When weights are None (default), behaves identically to V1
        (unweighted average), ensuring backward compatibility.

        Returns (decision, confidence).
        """
        if not votes:
            return VoteDecision.ABSTAIN, 0.0

        has_approve = any(
            v.decision == VoteDecision.APPROVE for v in votes
        )
        has_reject = any(
            v.decision == VoteDecision.REJECT for v in votes
        )
        all_approve = all(
            v.decision == VoteDecision.APPROVE for v in votes
        )
        all_abstain = all(
            v.decision == VoteDecision.ABSTAIN for v in votes
        )

        if has_reject:
            avg_confidence = self._weighted_confidence(
                votes, VoteDecision.REJECT, weights,
            )
            return VoteDecision.REJECT, avg_confidence

        if all_abstain:
            return VoteDecision.ABSTAIN, 0.0

        if all_approve:
            avg_confidence = self._weighted_confidence(
                votes, VoteDecision.APPROVE, weights,
            )
            return VoteDecision.APPROVE, avg_confidence

        if has_approve:
            approve_weight = sum(
                weights.get(v.voter_name, 1.0) if weights else 1.0
                for v in votes if v.decision == VoteDecision.APPROVE
            )
            non_abstain_weight = sum(
                weights.get(v.voter_name, 1.0) if weights else 1.0
                for v in votes if v.decision != VoteDecision.ABSTAIN
            )
            ratio = (
                approve_weight / non_abstain_weight
                if non_abstain_weight > 0 else 0.0
            )
            avg_confidence = self._weighted_confidence(
                votes, VoteDecision.APPROVE, weights,
            )
            confidence = avg_confidence * ratio
            return VoteDecision.APPROVE, confidence

        return VoteDecision.ABSTAIN, 0.0

    @staticmethod
    def _weighted_confidence(
        votes: list[ConsensusVote],
        target: VoteDecision,
        weights: dict[str, float] | None = None,
    ) -> float:
        matching = [v for v in votes if v.decision == target]
        if not matching:
            return 0.0
        if weights is None:
            return sum(v.confidence for v in matching) / len(matching)
        total_weight = sum(weights.get(v.voter_name, 1.0) for v in matching)
        if total_weight == 0:
            return 0.0
        weighted_sum = sum(
            v.confidence * weights.get(v.voter_name, 1.0)
            for v in matching
        )
        return weighted_sum / total_weight
