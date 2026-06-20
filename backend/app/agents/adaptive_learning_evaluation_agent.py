"""AdaptiveLearningEvaluationAgent — assesses student learning state and produces a pedagogical recommendation."""

from __future__ import annotations

import logging
import math
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select

from app.agents.base import BaseAgent
from app.memory.pedagogical_memory import PEDAGOGICAL_KEYS
from app.models.evaluation_attempt import EvaluationAttempt

logger = logging.getLogger(__name__)

# ── Ebbinghaus stability constants ────────────────────────────────────────────
# S (hours) until retention decays to L × 1/e (~37%) at each Bloom level.
# Higher Bloom levels represent deeper encoding → slower forgetting.
_S_BY_BLOOM: dict[int, float] = {
    1: 24.0,    # Remember
    2: 48.0,    # Understand
    3: 72.0,    # Apply
    4: 120.0,   # Analyze
    5: 168.0,   # Evaluate
    6: 240.0,   # Create
}
_DEFAULT_S = 48.0

# EWMA: each older attempt has weight multiplied by this factor
_EWMA_ALPHA = 0.7

# Engagement pattern → numeric score
_ENGAGEMENT_SCORES: dict[str, float] = {
    "high": 0.90,
    "consistent": 0.80,
    "erratic": 0.55,
    "declining": 0.40,
    "low": 0.25,
}

# Cognitive Load Theory zone boundaries
_CL_OVERLOAD = 0.70
_CL_UNDERLOAD = 0.40


class AdaptiveLearningEvaluationAgent(BaseAgent):
    """Evaluates student learning state from historical DB and cross-session SharedMemory.

    Pipeline position: Fase 3.5 — after AdaptiveLearningAgent, before MultimodalPlanningAgent.

    DB source (async):
        EvaluationAttempt — learning history for this student_id.

    SharedMemory sources (query_by_key_pattern, NO module_id filter):
        pedagogical:cognitive_load      → {signal: float, trend: str}
        pedagogical:bloom_progress      → {bloom_level: int}
        pedagogical:engagement          → {pattern: str}
        pedagogical:modality_preference → {modality: str}
        pedagogical:successful_example  → {example_type: str}

    Produces:
        learning_score, cognitive_load_score, retention_score,
        engagement_score, modality_effectiveness,
        recommendation, recommendation_rationale,
        bloom_readiness_level, difficulty_override,
        confidence, cold_start, session_count,
        time_since_last_session_hours.

    Does NOT use: PedagogicalMemoryService, self.uow.db.query(), query_memory().
    """

    @property
    def agent_type(self) -> str:
        return "adaptive_evaluation"

    async def analyze(self, state: dict[str, Any]) -> dict[str, Any]:

        # ── 1. Load DB history ───────────────────────────────────────────────
        attempts = await self._load_evaluation_attempts()
        session_count = len(attempts)
        cold_start = session_count == 0

        # ── 2. Learning score via EWMA ───────────────────────────────────────
        learning_score, last_attempted_at = self._compute_learning_score(attempts)

        # ── 3. Cross-session SharedMemory reads (no module_id) ───────────────
        cl_records = await self.shared_memory.query_by_key_pattern(
            key_prefix=PEDAGOGICAL_KEYS["cognitive_load"],
            student_id=self.student_id,
            memory_type="pedagogical_profile",
            limit=5,
        )
        bloom_records = await self.shared_memory.query_by_key_pattern(
            key_prefix=PEDAGOGICAL_KEYS["bloom_progress"],
            student_id=self.student_id,
            memory_type="pedagogical_profile",
            limit=1,
        )
        engagement_records = await self.shared_memory.query_by_key_pattern(
            key_prefix=PEDAGOGICAL_KEYS["engagement"],
            student_id=self.student_id,
            memory_type="pedagogical_profile",
            limit=1,
        )
        modality_records = await self.shared_memory.query_by_key_pattern(
            key_prefix=PEDAGOGICAL_KEYS["modality_preference"],
            student_id=self.student_id,
            memory_type="pedagogical_profile",
            limit=1,
        )
        example_records = await self.shared_memory.query_by_key_pattern(
            key_prefix=PEDAGOGICAL_KEYS["successful_example"],
            student_id=self.student_id,
            memory_type="pedagogical_profile",
            limit=3,
        )

        # ── 4. Individual scores ─────────────────────────────────────────────
        cognitive_load_score, cl_zone, cl_signals = self._compute_cognitive_load(cl_records)
        bloom_level = self._extract_bloom_level(bloom_records)
        retention_score, t_hours, S = self._compute_retention(
            learning_score, last_attempted_at, bloom_level, cold_start,
        )
        engagement_score, engagement_pattern = self._compute_engagement(engagement_records)
        modality_effectiveness, preferred_modality = self._compute_modality_effectiveness(
            modality_records, example_records,
        )

        # ── 5. Evidence registration ─────────────────────────────────────────
        self._trace_evidence(
            source="db",
            key="evaluation_attempts",
            value={
                "session_count": session_count,
                "cold_start": cold_start,
                "learning_score": round(learning_score, 4),
                "last_attempted_at": last_attempted_at.isoformat() if last_attempted_at else None,
            },
            confidence=0.90 if not cold_start else 0.20,
        )
        self._trace_evidence(
            source="shared_memory",
            key=PEDAGOGICAL_KEYS["cognitive_load"],
            value={
                "signals_count": len(cl_signals),
                "avg_signal": round(sum(cl_signals) / len(cl_signals), 4) if cl_signals else None,
                "zone": cl_zone,
            },
            confidence=0.80 if cl_records else 0.30,
            memory_type="pedagogical_profile",
        )
        self._trace_evidence(
            source="shared_memory",
            key=PEDAGOGICAL_KEYS["bloom_progress"],
            value={"bloom_level_reached": bloom_level},
            confidence=0.85 if bloom_records else 0.30,
            memory_type="pedagogical_profile",
        )
        self._trace_evidence(
            source="shared_memory",
            key=PEDAGOGICAL_KEYS["engagement"],
            value={"pattern": engagement_pattern, "score": round(engagement_score, 4)},
            confidence=0.75 if engagement_records else 0.30,
            memory_type="pedagogical_profile",
        )
        self._trace_evidence(
            source="shared_memory",
            key=PEDAGOGICAL_KEYS["modality_preference"],
            value={
                "preferred_modality": preferred_modality,
                "effectiveness": {k: round(v, 3) for k, v in modality_effectiveness.items()},
            },
            confidence=0.70 if modality_records else 0.40,
            memory_type="pedagogical_profile",
        )

        # ── 6. Decision tree → recommendation ────────────────────────────────
        recommendation, rationale, bloom_readiness, difficulty_override = self._decide(
            learning_score=learning_score,
            cognitive_load_score=cognitive_load_score,
            retention_score=retention_score,
            engagement_score=engagement_score,
            bloom_level=bloom_level,
            cl_zone=cl_zone,
            cold_start=cold_start,
        )
        confidence = self._compute_confidence(cold_start, session_count, cl_records, engagement_records)

        # ── 7. Dimension registration ─────────────────────────────────────────
        self._trace_dimension(
            dimension="learning_assessment",
            result=f"learning_score={learning_score:.2f} ({session_count} attempts)",
            signal=f"EWMA α={_EWMA_ALPHA} over {session_count} attempts, newest-first",
            rule="normalize score/max_score per attempt; if no score use passed flag; cold_start → 0.50",
            confidence=0.90 if not cold_start else 0.20,
            evidence={
                "session_count": session_count,
                "learning_score": round(learning_score, 4),
                "cold_start": cold_start,
            },
        )
        self._trace_dimension(
            dimension="cognitive_load_assessment",
            result=f"load={cognitive_load_score:.2f}, zone={cl_zone}",
            signal=f"avg({len(cl_signals)} signals)={cognitive_load_score:.2f}",
            rule=f"avg≥{_CL_OVERLOAD}→overload; ≥{_CL_UNDERLOAD}→optimal; else→underload; no records→0.55 optimal",
            confidence=0.80 if cl_records else 0.30,
            evidence={
                "signals_count": len(cl_signals),
                "avg": round(cognitive_load_score, 4),
                "zone": cl_zone,
            },
        )
        self._trace_dimension(
            dimension="retention_assessment",
            result=f"retention={retention_score:.2f} (t={t_hours:.1f}h, bloom={bloom_level}, S={S}h)",
            signal=f"R={learning_score:.2f}×exp(-{t_hours:.1f}/{S})={retention_score:.2f}",
            rule="Ebbinghaus R=L×exp(-t/S); S=_S_BY_BLOOM[bloom]; normalize tz before delta; cold_start→0.50",
            confidence=0.75 if not cold_start else 0.20,
            evidence={
                "t_hours": round(t_hours, 2),
                "bloom_level": bloom_level,
                "S": S,
                "R": round(retention_score, 4),
            },
        )
        self._trace_dimension(
            dimension="engagement_assessment",
            result=f"engagement={engagement_score:.2f} (pattern='{engagement_pattern}')",
            signal=f"'{engagement_pattern}'→{engagement_score:.2f}",
            rule="high=0.90, consistent=0.80, erratic=0.55, declining=0.40, low=0.25; unknown→0.60",
            confidence=0.75 if engagement_records else 0.30,
            evidence={
                "pattern": engagement_pattern,
                "score": round(engagement_score, 4),
                "from_memory": bool(engagement_records),
            },
        )
        _best_m = max(modality_effectiveness, key=lambda k: modality_effectiveness[k])
        self._trace_dimension(
            dimension="modality_effectiveness",
            result=f"best={_best_m}({modality_effectiveness[_best_m]:.2f}), preferred='{preferred_modality}'",
            signal=f"base=0.50; preferred_modality+0.30; each successful_example_type+0.15 (capped at 1.0)",
            rule="init all modalities at 0.50; boost preferred modality; boost confirmed example types",
            confidence=0.70 if modality_records else 0.40,
            evidence={
                "preferred": preferred_modality,
                "scores": {k: round(v, 3) for k, v in modality_effectiveness.items()},
            },
        )
        self._trace_dimension(
            dimension="pedagogical_recommendation",
            result=f"recommendation={recommendation}, bloom_readiness={bloom_readiness}, difficulty_override={difficulty_override}",
            signal=f"learning={learning_score:.2f}, cl={cognitive_load_score:.2f}({cl_zone}), retention={retention_score:.2f}, engagement={engagement_score:.2f}",
            rule=rationale,
            confidence=confidence,
            evidence={
                "learning_score": round(learning_score, 4),
                "cognitive_load_score": round(cognitive_load_score, 4),
                "retention_score": round(retention_score, 4),
                "engagement_score": round(engagement_score, 4),
                "cl_zone": cl_zone,
                "cold_start": cold_start,
            },
        )

        # ── 8. Build result, publish, annotate ────────────────────────────────
        result: dict[str, Any] = {
            "learning_score": round(learning_score, 4),
            "cognitive_load_score": round(cognitive_load_score, 4),
            "retention_score": round(retention_score, 4),
            "engagement_score": round(engagement_score, 4),
            "modality_effectiveness": {k: round(v, 4) for k, v in modality_effectiveness.items()},
            "recommendation": recommendation,
            "recommendation_rationale": rationale,
            "bloom_readiness_level": bloom_readiness,
            "difficulty_override": difficulty_override,
            "confidence": round(confidence, 4),
            "cold_start": cold_start,
            "session_count": session_count,
            "time_since_last_session_hours": round(t_hours, 2),
        }

        await self.publish_observation(
            f"{self.context_key}:evaluation:assessment",
            result,
            memory_type="inference",
            confidence=confidence,
        )

        # _decision_summary and _confidence MUST come after publish_observation
        result["_decision_summary"] = (
            f"AdaptiveEval: recommendation={recommendation}, "
            f"learning={learning_score:.2f}, cl={cognitive_load_score:.2f}({cl_zone}), "
            f"retention={retention_score:.2f}, engagement={engagement_score:.2f}, "
            f"bloom_readiness={bloom_readiness}, cold_start={cold_start}"
        )
        result["_confidence"] = confidence

        return result

    # ── DB ────────────────────────────────────────────────────────────────────

    async def _load_evaluation_attempts(self) -> list[EvaluationAttempt]:
        """Load last 10 attempts for this student via async SQLAlchemy 2.0 API."""
        try:
            stmt = (
                select(EvaluationAttempt)
                .where(EvaluationAttempt.student_id == self.student_id)
                .order_by(EvaluationAttempt.attempted_at.desc())
                .limit(10)
            )
            result = await self.uow.db.execute(stmt)
            return list(result.scalars().all())
        except Exception as exc:
            logger.debug("AdaptiveEval._load_evaluation_attempts: %s", exc)
            return []

    # ── Score helpers ─────────────────────────────────────────────────────────

    def _compute_learning_score(
        self,
        attempts: list[EvaluationAttempt],
    ) -> tuple[float, datetime | None]:
        """EWMA of normalized scores. Attempts are ordered DESC (newest first).
        Most recent attempt gets weight=1.0; each older attempt weight×=_EWMA_ALPHA.
        """
        if not attempts:
            return 0.50, None

        last_attempted_at = attempts[0].attempted_at

        scores: list[float] = []
        for a in attempts:
            if a.score is not None and a.max_score:
                scores.append(float(a.score) / float(a.max_score))
            elif a.passed is not None:
                scores.append(1.0 if a.passed else 0.0)

        if not scores:
            return 0.50, last_attempted_at

        # attempts are newest-first (DESC order); iterate newest-first so
        # weight=1.0 applies to the most recent attempt.
        weight = 1.0
        weighted_sum = 0.0
        total_weight = 0.0
        for s in scores:
            weighted_sum += s * weight
            total_weight += weight
            weight *= _EWMA_ALPHA

        ewma = weighted_sum / total_weight if total_weight > 0 else 0.50
        return min(1.0, max(0.0, ewma)), last_attempted_at

    def _compute_cognitive_load(
        self,
        cl_records: list,
    ) -> tuple[float, str, list[float]]:
        """Average of cognitive load signals. Returns (avg, zone, raw_signals)."""
        signals: list[float] = []
        for r in cl_records:
            val = r.value if hasattr(r, "value") else {}
            if isinstance(val, dict):
                try:
                    signals.append(float(val["signal"]))
                except (KeyError, TypeError, ValueError):
                    pass

        if not signals:
            return 0.55, "optimal", signals

        avg = sum(signals) / len(signals)
        zone = (
            "overload" if avg >= _CL_OVERLOAD
            else ("optimal" if avg >= _CL_UNDERLOAD else "underload")
        )
        return min(1.0, max(0.0, avg)), zone, signals

    def _extract_bloom_level(self, bloom_records: list) -> int:
        """Most recent Bloom level reached from SharedMemory. Defaults to 3."""
        for r in bloom_records:
            val = r.value if hasattr(r, "value") else {}
            if isinstance(val, dict):
                try:
                    return max(1, min(6, int(val["bloom_level"])))
                except (KeyError, TypeError, ValueError):
                    pass
        return 3

    def _compute_retention(
        self,
        learning_score: float,
        last_attempted_at: datetime | None,
        bloom_level: int,
        cold_start: bool,
    ) -> tuple[float, float, float]:
        """Ebbinghaus: R = L × exp(-t/S). Returns (retention, t_hours, S)."""
        S = _S_BY_BLOOM.get(bloom_level, _DEFAULT_S)

        if cold_start or last_attempted_at is None:
            return 0.50, 0.0, S

        ts = last_attempted_at
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)

        t_hours = max(0.0, (datetime.now(timezone.utc) - ts).total_seconds() / 3600.0)
        R = learning_score * math.exp(-t_hours / S)
        return min(1.0, max(0.0, R)), t_hours, S

    def _compute_engagement(
        self,
        engagement_records: list,
    ) -> tuple[float, str]:
        """Map engagement pattern string to numeric score. Returns (score, pattern)."""
        for r in engagement_records:
            val = r.value if hasattr(r, "value") else {}
            if isinstance(val, dict) and "pattern" in val:
                pattern = str(val["pattern"])
                return _ENGAGEMENT_SCORES.get(pattern, 0.60), pattern
        return 0.60, "unknown"

    def _compute_modality_effectiveness(
        self,
        modality_records: list,
        example_records: list,
    ) -> tuple[dict[str, float], str]:
        """Build per-modality effectiveness scores.

        Base: 0.50 for all five modalities.
        Boost +0.30 for the student's preferred modality (modality_preference record).
        Boost +0.15 per confirmed successful_example_type that matches a modality key.
        All scores clamped to [0.0, 1.0].
        """
        modalities = ["text", "video", "image", "interactive", "audio"]
        scores: dict[str, float] = {m: 0.50 for m in modalities}
        preferred_modality = "text"

        for r in modality_records:
            val = r.value if hasattr(r, "value") else {}
            if isinstance(val, dict) and "modality" in val:
                preferred_modality = str(val["modality"])
                if preferred_modality in scores:
                    scores[preferred_modality] = min(1.0, scores[preferred_modality] + 0.30)
                break

        for r in example_records:
            val = r.value if hasattr(r, "value") else {}
            if isinstance(val, dict) and "example_type" in val:
                example_type = str(val["example_type"])
                if example_type in scores:
                    scores[example_type] = min(1.0, scores[example_type] + 0.15)

        return scores, preferred_modality

    # ── Decision tree ─────────────────────────────────────────────────────────

    def _decide(
        self,
        learning_score: float,
        cognitive_load_score: float,
        retention_score: float,
        engagement_score: float,
        bloom_level: int,
        cl_zone: str,
        cold_start: bool,
    ) -> tuple[str, str, int, str | None]:
        """Priority decision tree. Returns (recommendation, rationale, bloom_readiness, difficulty_override).

        Rule order (first match wins):
            1. cold_start                → continuar (no evidence to act on)
            2. learning_score < 0.40     → retroceder
            3. cl_zone == "overload"     → simplificar
            4. engagement_score < 0.45   → cambiar_modalidad
            5. learning_score < 0.65     → reforzar
            6. default                   → continuar
        """
        if cold_start:
            return (
                "continuar",
                "cold_start=True: no prior history — proceed with default progression",
                bloom_level,
                None,
            )

        if learning_score < 0.40:
            return (
                "retroceder",
                f"learning_score={learning_score:.2f} < 0.40: mastery insufficient — return to prerequisite material",
                max(1, bloom_level - 1),
                "beginner",
            )

        if cl_zone == "overload":
            override = "beginner" if bloom_level <= 2 else "intermediate"
            return (
                "simplificar",
                f"cognitive_load={cognitive_load_score:.2f} ≥ {_CL_OVERLOAD} (overload): reduce complexity to prevent ceiling effect",
                bloom_level,
                override,
            )

        if engagement_score < 0.45:
            return (
                "cambiar_modalidad",
                f"engagement={engagement_score:.2f} < 0.45: sustained low engagement — switch delivery modality",
                bloom_level,
                None,
            )

        if learning_score < 0.65:
            return (
                "reforzar",
                f"learning_score={learning_score:.2f} in [0.40, 0.65): partial mastery — reinforce before advancing",
                bloom_level,
                None,
            )

        difficulty_override = "advanced" if learning_score >= 0.85 else None
        return (
            "continuar",
            f"learning_score={learning_score:.2f} ≥ 0.65, cl={cl_zone}, engagement={engagement_score:.2f} ≥ 0.45 — advance to Bloom {min(6, bloom_level + 1)}",
            min(6, bloom_level + 1),
            difficulty_override,
        )

    # ── Confidence ────────────────────────────────────────────────────────────

    def _compute_confidence(
        self,
        cold_start: bool,
        session_count: int,
        cl_records: list,
        engagement_records: list,
    ) -> float:
        """Accumulates signal confidence from available evidence sources."""
        if cold_start:
            return 0.20
        base = 0.50
        if session_count >= 3:
            base += 0.25
        elif session_count >= 1:
            base += 0.15
        if cl_records:
            base += 0.15
        if engagement_records:
            base += 0.10
        return min(0.95, base)
