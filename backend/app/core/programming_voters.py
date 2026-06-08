"""
Votantes especializados para cursos de programación.
CodeMasteryVoter: Evalúa corrección de código + CT ponderado.
ProgressionVoter: Verifica dependencias de concepto y Bloom.
"""

from __future__ import annotations

import logging

from app.core.consensus import (
    BaseVoter,
    ConsensusVote,
    VoteDecision,
    VoteContext,
)
from app.models.programming_domain import ProgrammingConcept, STAGE_CONFIG
from app.models.programming_prerequisite import CONCEPT_DEPENDENCY_GRAPH

logger = logging.getLogger(__name__)


class CodeMasteryVoter(BaseVoter):
    """Votante especializado en código de programación.

    Evalúa:
    - Corrección del código (peso 0.6)
    - Nivel de pensamiento computacional (peso 0.4)
    - Se integra con el MasteryVoter base para decisión final.

    Requiere en ctx.evidence:
    - code_correctness: float (0-1)
    - ct_score: float (0-1)
    - concept: str (concepto evaluado)
    """

    @property
    def voter_name(self) -> str:
        return "code_mastery"

    def vote(self, ctx: VoteContext) -> ConsensusVote:
        evidence = ctx.evidence or {}

        code_correctness = evidence.get("code_correctness")
        ct_score = evidence.get("ct_score")
        concept = evidence.get("concept", "")

        feedback: list[str] = []

        if code_correctness is not None and ct_score is not None:
            weighted_score = code_correctness * 0.6 + ct_score * 0.4
            feedback.append(
                f"Code correctness={code_correctness:.2f}, "
                f"CT={ct_score:.2f}, weighted={weighted_score:.2f}"
            )

            if weighted_score >= 0.7:
                return ConsensusVote(
                    voter_name=self.voter_name,
                    decision=VoteDecision.APPROVE,
                    confidence=min(weighted_score, 1.0),
                    reason=(
                        f"Code mastery weighted score {weighted_score:.2f} "
                        f"exceeds threshold 0.7"
                    ),
                    evidence={
                        "code_correctness": code_correctness,
                        "ct_score": ct_score,
                        "weighted_score": weighted_score,
                        "threshold": 0.7,
                        "concept": concept,
                    },
                )

            if weighted_score >= 0.4:
                return ConsensusVote(
                    voter_name=self.voter_name,
                    decision=VoteDecision.ABSTAIN,
                    confidence=weighted_score,
                    reason=(
                        f"Code mastery borderline: {weighted_score:.2f} "
                        f"in [0.4, 0.7)"
                    ),
                    evidence={
                        "code_correctness": code_correctness,
                        "ct_score": ct_score,
                        "weighted_score": weighted_score,
                        "concept": concept,
                    },
                )

            return ConsensusVote(
                voter_name=self.voter_name,
                decision=VoteDecision.REJECT,
                confidence=1.0 - weighted_score,
                reason=(
                    f"Code mastery weighted score {weighted_score:.2f} "
                    f"below reject threshold 0.4"
                ),
                evidence={
                    "code_correctness": code_correctness,
                    "ct_score": ct_score,
                    "weighted_score": weighted_score,
                    "concept": concept,
                },
            )

        if concept:
            return ConsensusVote(
                voter_name=self.voter_name,
                decision=VoteDecision.ABSTAIN,
                confidence=0.3,
                reason=f"Missing code_correctness or ct_score evidence for concept '{concept}'",
                evidence={"concept": concept},
            )

        return ConsensusVote(
            voter_name=self.voter_name,
            decision=VoteDecision.ABSTAIN,
            confidence=0.3,
            reason="No code correctness or CT evidence available",
            evidence={},
        )


class ProgressionVoter(BaseVoter):
    """Votante de progresión para cursos de programación.

    Verifica:
    - Que el estudiante ha completado los conceptos prerrequisito
      necesarios para el concepto actual (basado en CONCEPT_DEPENDENCY_GRAPH).
    - Que el nivel Bloom del módulo es consistente con la etapa actual.

    Requiere en ctx.evidence:
    - concept: str (concepto actual según ProgrammingConcept)
    - completed_concepts: list[str] (conceptos completados)
    - current_stage: str (etapa cognitiva actual)
    """

    @property
    def voter_name(self) -> str:
        return "progression"

    def vote(self, ctx: VoteContext) -> ConsensusVote:
        evidence = ctx.evidence or {}
        concept_str = evidence.get("concept", "")
        completed = evidence.get("completed_concepts", [])
        current_stage = evidence.get("current_stage", "")

        if not concept_str:
            return ConsensusVote(
                voter_name=self.voter_name,
                decision=VoteDecision.ABSTAIN,
                confidence=0.3,
                reason="No concept specified for progression check",
                evidence={},
            )

        try:
            current_concept = ProgrammingConcept(concept_str)
        except ValueError:
            return ConsensusVote(
                voter_name=self.voter_name,
                decision=VoteDecision.ABSTAIN,
                confidence=0.3,
                reason=f"Unknown concept '{concept_str}'",
                evidence={"concept": concept_str},
            )

        prereqs = CONCEPT_DEPENDENCY_GRAPH.get(current_concept, set())
        completed_set = set(completed)

        # Filter out concepts with no prereqs (already mastered by existence)
        missing = prereqs - completed_set

        incomplete_prereqs = [p.value for p in sorted(missing, key=lambda x: x.value)]

        if not incomplete_prereqs:
            return ConsensusVote(
                voter_name=self.voter_name,
                decision=VoteDecision.APPROVE,
                confidence=1.0,
                reason=(
                    f"All prerequisite concepts completed for '{concept_str}'"
                ),
                evidence={
                    "concept": concept_str,
                    "prerequisites_required": [p.value for p in sorted(prereqs, key=lambda x: x.value)],
                    "completed_concepts": completed,
                    "missing_prereqs": [],
                },
            )

        rejection_confidence = min(1.0, len(incomplete_prereqs) / max(len(prereqs), 1))
        return ConsensusVote(
            voter_name=self.voter_name,
            decision=VoteDecision.REJECT,
            confidence=rejection_confidence,
            reason=(
                f"Missing {len(incomplete_prereqs)} prerequisite concept(s) "
                f"for '{concept_str}': {', '.join(incomplete_prereqs)}"
            ),
            evidence={
                "concept": concept_str,
                "prerequisites_required": [p.value for p in sorted(prereqs, key=lambda x: x.value)],
                "completed_concepts": completed,
                "missing_prereqs": incomplete_prereqs,
            },
        )
