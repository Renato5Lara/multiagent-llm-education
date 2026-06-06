"""SwarmDeliberationOrchestrator — multi-round consensus with real deliberation.

Architecture:
    Round 1 (FIRST_VOTE):
        All voters vote independently.
        Results are aggregated; reasoning is shared via deliberation context.

    Round 2..N (DELIBERATION + REVOTE):
        LLM voters receive each other's reasoning from previous round.
        Each LLM voter produces a revised vote (or maintains position).
        Heuristic voters keep their original vote (they don't deliberate).

    Final (MEDIATE):
        If max_rounds reached without convergence, invoke MediatorVoter
        with full vote history and agent agendas.

Convergence = unanimous decision + weighted confidence >= threshold
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from app.core.consensus import (
    BaseVoter,
    ConsensusEngine,
    ConsensusResult,
    ConsensusVote,
    VoteContext,
    VoteDecision,
)

logger = logging.getLogger(__name__)


class DeliberationPhase(str, Enum):
    FIRST_VOTE = "first_vote"
    DELIBERATE = "deliberate"
    REVOTE = "revote"
    MEDIATE = "mediate"
    FINALIZE = "finalize"


@dataclass
class RoundResult:
    """Result of a single deliberation round."""

    round_number: int
    phase: DeliberationPhase
    votes: list[ConsensusVote]
    converged: bool = False
    confidence: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "round": self.round_number,
            "phase": self.phase.value,
            "n_votes": len(self.votes),
            "converged": self.converged,
            "confidence": round(self.confidence, 4),
            "decisions": {v.voter_name: v.decision.value for v in self.votes},
        }


@dataclass
class DeliberationResult:
    """Full result of a deliberation process."""

    ctx: VoteContext
    rounds: list[RoundResult] = field(default_factory=list)
    final_result: ConsensusResult | None = None
    total_rounds: int = 0
    converged: bool = False
    mediation_used: bool = False

    @property
    def vote_shift_rate(self) -> float:
        """Fraction of LLM voters that changed vote between first and last round."""
        if len(self.rounds) < 2:
            return 0.0
        first = {v.voter_name: v.decision for v in self.rounds[0].votes}
        last = {v.voter_name: v.decision for v in self.rounds[-1].votes}
        changes = sum(1 for name, dec in first.items() if name in last and last[name] != dec)
        return changes / max(len(first), 1)

    @property
    def rounds_to_converge(self) -> int:
        if not self.converged:
            return self.total_rounds
        for i, r in enumerate(self.rounds):
            if r.converged:
                return i + 1
        return self.total_rounds

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_rounds": self.total_rounds,
            "converged": self.converged,
            "mediation_used": self.mediation_used,
            "vote_shift_rate": round(self.vote_shift_rate, 4),
            "rounds_to_converge": self.rounds_to_converge,
            "rounds": [r.to_dict() for r in self.rounds],
            "final_decision": (
                self.final_result.decision.value if self.final_result else None
            ),
            "final_confidence": (
                round(self.final_result.confidence, 4) if self.final_result else 0.0
            ),
        }


class SwarmDeliberationOrchestrator:
    """Multi-round deliberation orchestrator for hybrid LLM + heuristic voters.

    Usage:
        orchestrator = SwarmDeliberationOrchestrator(engine, convergence_threshold=0.85)
        result = await orchestrator.deliberate(ctx, llm_voters, heuristic_voters)
    """

    def __init__(
        self,
        engine: ConsensusEngine,
        *,
        max_rounds: int = 3,
        convergence_threshold: float = 0.85,
        min_convergence_confidence: float = 0.6,
        mediator: BaseVoter | None = None,
    ):
        self._engine = engine
        self._max_rounds = max_rounds
        self._convergence_threshold = convergence_threshold
        self._min_convergence_confidence = min_convergence_confidence
        self._mediator = mediator

    # ── Public API ────────────────────────────────────────────

    async def deliberate(
        self,
        ctx: VoteContext,
        llm_voters: list[BaseVoter],
        heuristic_voters: list[BaseVoter] | None = None,
        *,
        shared_memory_store: Any | None = None,
    ) -> DeliberationResult:
        """Run multi-round deliberation until convergence or max_rounds.

        Args:
            ctx: The vote context (shared across all rounds)
            llm_voters: Voters that can deliberate (revote per round)
            heuristic_voters: Voters that vote once (heuristic only)
            shared_memory_store: Optional SharedMemoryStore for publishing
                                 round results as observations.

        Returns:
            DeliberationResult with full round history + final ConsensusResult
        """
        all_voters = list(llm_voters) + list(heuristic_voters or [])
        result = DeliberationResult(ctx=ctx)
        current_ctx = ctx

        # ── Round 1: First vote ───────────────────────────────
        loop = asyncio.get_running_loop()
        round1_votes = await self._run_voting_round(loop, current_ctx, all_voters)
        round1 = RoundResult(
            round_number=1, phase=DeliberationPhase.FIRST_VOTE,
            votes=round1_votes,
        )

        if self._is_converged(round1_votes):
            round1.converged = True
            round1.confidence = self._compute_consensus_confidence(round1_votes)
            result.rounds.append(round1)
            result.total_rounds = 1
            result.converged = True
            result.final_result = self._aggregate(ctx, round1_votes)
            await self._publish_round_observations(shared_memory_store, ctx, 1, round1_votes)
            await self._publish_final_result(shared_memory_store, ctx, result)
            return result

        result.rounds.append(round1)
        await self._publish_round_observations(shared_memory_store, ctx, 1, round1_votes)

        # ── Rounds 2..N: Deliberation ─────────────────────────
        for round_num in range(2, self._max_rounds + 1):
            delib_context = self._build_deliberation_context(round_num, result.rounds)
            current_ctx = self._enrich_ctx(ctx, delib_context)
            round_votes = await self._run_voting_round(loop, current_ctx, llm_voters)
            heuristic_results = self._get_heuristic_votes(result.rounds[0].votes, heuristic_voters)
            all_round_votes = round_votes + heuristic_results

            round_result = RoundResult(
                round_number=round_num, phase=DeliberationPhase.REVOTE,
                votes=all_round_votes,
            )

            await self._publish_round_observations(
                shared_memory_store, ctx, round_num, all_round_votes,
            )

            if self._is_converged(all_round_votes):
                round_result.converged = True
                round_result.confidence = self._compute_consensus_confidence(all_round_votes)
                result.rounds.append(round_result)
                result.total_rounds = round_num
                result.converged = True
                result.final_result = self._aggregate(ctx, all_round_votes)
                await self._publish_final_result(shared_memory_store, ctx, result)
                return result

            result.rounds.append(round_result)

        # ── Mediation (if not converged) ───────────────────────
        result.mediation_used = True
        mediated_vote = await self._mediate(ctx, result.rounds)
        final_votes = self._merge_mediated_vote(
            result.rounds[-1].votes if result.rounds else [],
            mediated_vote,
            heuristic_voters,
        )
        result.total_rounds = self._max_rounds
        result.final_result = self._aggregate(ctx, final_votes)
        await self._publish_final_result(shared_memory_store, ctx, result)
        return result

    # ── Internal: voting rounds ───────────────────────────────

    async def _run_voting_round(
        self, loop: asyncio.AbstractEventLoop,
        ctx: VoteContext, voters: list[BaseVoter],
    ) -> list[ConsensusVote]:
        """Run a single voting round, executing each voter in a thread."""
        tasks = []
        for voter in voters:
            tasks.append(
                loop.run_in_executor(None, voter.vote, ctx)
            )
        return await asyncio.gather(*tasks)

    def _build_deliberation_context(
        self, round_num: int, rounds: list[RoundResult],
    ) -> str:
        """Build deliberation context string from previous round votes."""
        parts = []
        prev = rounds[-1] if rounds else None
        if not prev:
            return ""

        for v in prev.votes:
            reasoning = v.evidence.get("reasoning", v.reason) if v.evidence else v.reason
            parts.append(
                f"Agent: {v.voter_name}\n"
                f"  Decisión: {v.decision.value}\n"
                f"  Confianza: {v.confidence:.2f}\n"
                f"  Razonamiento: {reasoning[:500]}\n"
            )
        return "\n".join(parts)

    def _enrich_ctx(self, ctx: VoteContext, delib_context: str) -> VoteContext:
        """Return a new VoteContext with deliberation context injected into evidence."""
        new_evidence = dict(ctx.evidence)
        new_evidence["deliberation_context"] = delib_context
        return VoteContext(
            uow=ctx.uow,
            student_id=ctx.student_id,
            module_id=ctx.module_id,
            path_id=ctx.path_id,
            course_id=ctx.course_id,
            score=ctx.score,
            module=ctx.module,
            path=ctx.path,
            evidence=new_evidence,
            timestamp=ctx.timestamp,
            shared_memory=ctx.shared_memory,
        )

    # ── Convergence detection ─────────────────────────────────

    def _is_converged(self, votes: list[ConsensusVote]) -> bool:
        """Check if votes are unanimous with sufficient confidence."""
        if not votes:
            return False
        if len(votes) == 1:
            return votes[0].confidence >= self._min_convergence_confidence

        first_decision = votes[0].decision
        all_same = all(v.decision == first_decision for v in votes)
        if not all_same:
            return False

        avg_conf = self._compute_consensus_confidence(votes)
        return avg_conf >= self._convergence_threshold

    @staticmethod
    def _compute_consensus_confidence(votes: list[ConsensusVote]) -> float:
        """Weighted average confidence of non-abstain votes."""
        relevant = [v for v in votes if v.decision != VoteDecision.ABSTAIN]
        if not relevant:
            return sum(v.confidence for v in votes) / max(len(votes), 1)
        return sum(v.confidence for v in relevant) / len(relevant)

    # ── Mediation ─────────────────────────────────────────────

    async def _mediate(
        self, ctx: VoteContext, rounds: list[RoundResult],
    ) -> ConsensusVote:
        """Invoke mediator with full vote history and agent agendas."""
        if self._mediator is None:
            return ConsensusVote(
                voter_name="mediator",
                decision=VoteDecision.ABSTAIN,
                confidence=0.3,
                reason="No mediator configured",
            )

        vote_history_lines = []
        for r in rounds:
            line = f"Round {r.round_number} ({r.phase.value}): "
            line += ", ".join(f"{v.voter_name}={v.decision.value}({v.confidence:.2f})" for v in r.votes)
            vote_history_lines.append(line)

        agent_agendas_lines = []
        prev = rounds[-1] if rounds else None
        if prev:
            for v in prev.votes:
                reasoning = v.evidence.get("reasoning", v.reason) if v.evidence else v.reason
                agent_agendas_lines.append(
                    f"{v.voter_name}: {reasoning[:300]}"
                )

        med_evidence = dict(ctx.evidence)
        med_evidence["vote_history"] = "\n".join(vote_history_lines)
        med_evidence["agent_agendas"] = "\n".join(agent_agendas_lines)

        med_ctx = VoteContext(
            uow=ctx.uow,
            student_id=ctx.student_id,
            module_id=ctx.module_id,
            path_id=ctx.path_id,
            course_id=ctx.course_id,
            score=ctx.score,
            module=ctx.module,
            path=ctx.path,
            evidence=med_evidence,
            timestamp=ctx.timestamp,
            shared_memory=ctx.shared_memory,
        )

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._mediator.vote, med_ctx)

    @staticmethod
    def _merge_mediated_vote(
        previous_votes: list[ConsensusVote],
        mediated_vote: ConsensusVote,
        heuristic_voters: list[BaseVoter] | None,
    ) -> list[ConsensusVote]:
        """Replace LLM voter votes with mediated vote."""
        non_llm_names = set()
        if heuristic_voters:
            non_llm_names = {v.voter_name for v in heuristic_voters}

        merged = []
        for v in previous_votes:
            if v.voter_name not in non_llm_names and v.voter_name != "mediator":
                continue
            merged.append(v)
        merged.append(mediated_vote)
        return merged

    @staticmethod
    def _get_heuristic_votes(
        round1_votes: list[ConsensusVote],
        heuristic_voters: list[BaseVoter] | None,
    ) -> list[ConsensusVote]:
        """Extract heuristic voter votes from round 1 (they stay constant)."""
        if not heuristic_voters:
            return []
        names = {v.voter_name for v in heuristic_voters}
        return [v for v in round1_votes if v.voter_name in names]

    @staticmethod
    def _aggregate(ctx: VoteContext, votes: list[ConsensusVote]) -> ConsensusResult:
        """Simple aggregation without running full engine run()."""
        decisions = [v.decision for v in votes]
        approves = [v for v in votes if v.decision == VoteDecision.APPROVE]
        rejects = [v for v in votes if v.decision == VoteDecision.REJECT]
        non_abstain = approves + rejects

        if not non_abstain:
            decision = VoteDecision.ABSTAIN
            confidence = 0.0
        elif any(v.decision == VoteDecision.REJECT for v in votes):
            decision = VoteDecision.REJECT
            confidence = sum(v.confidence for v in rejects) / len(rejects)
        else:
            decision = VoteDecision.APPROVE
            confidence = sum(v.confidence for v in approves) / len(approves)

        return ConsensusResult(
            module_id=ctx.module_id,
            student_id=ctx.student_id,
            decision=decision,
            confidence=confidence,
            votes=votes,
        )

    # ── Shared memory publishing ───────────────────────────

    async def _publish_round_observations(
        self,
        store: Any | None,
        ctx: VoteContext,
        round_num: int,
        votes: list[ConsensusVote],
    ) -> None:
        """Publish each vote as an observation to shared memory (if store provided)."""
        if store is None:
            return
        for vote in votes:
            try:
                await store.publish_observation(
                    voter_name=vote.voter_name,
                    key=f"deliberation:round:{round_num}:{vote.voter_name}",
                    value={
                        "decision": vote.decision.value,
                        "confidence": vote.confidence,
                        "reason": vote.reason or "",
                        "evidence": vote.evidence or {},
                        "round": round_num,
                    },
                    confidence=vote.confidence,
                    student_id=ctx.student_id,
                    module_id=ctx.module_id,
                    memory_type="deliberation_vote",
                    ttl_seconds=86400 * 7,
                )
            except Exception:
                logger.warning(
                    "Failed to publish round %d vote for %s to shared memory",
                    round_num, vote.voter_name,
                )

    async def _publish_final_result(
        self,
        store: Any | None,
        ctx: VoteContext,
        result: DeliberationResult,
    ) -> None:
        """Publish the final deliberation result as an inference."""
        if store is None or result.final_result is None:
            return
        try:
            await store.publish_observation(
                voter_name="_deliberation",
                key=f"deliberation:result:{ctx.module_id[:12]}",
                value={
                    "converged": result.converged,
                    "total_rounds": result.total_rounds,
                    "mediation_used": result.mediation_used,
                    "vote_shift_rate": result.vote_shift_rate,
                    "final_decision": result.final_result.decision.value,
                    "final_confidence": result.final_result.confidence,
                },
                confidence=result.final_result.confidence,
                student_id=ctx.student_id,
                module_id=ctx.module_id,
                memory_type="deliberation_result",
                ttl_seconds=86400 * 14,
                metadata_json={
                    "rounds": [r.to_dict() for r in result.rounds],
                    "vote_shift_rate": result.vote_shift_rate,
                },
            )
        except Exception:
            logger.warning("Failed to publish deliberation result to shared memory")
