"""Pedagogical memory — student profiling, adaptation metrics, and memory-driven generation."""

from __future__ import annotations

from typing import Any, TypedDict

from app.memory.shared_memory import SharedMemoryStore


class StudentProfile(TypedDict, total=False):
    student_id: str
    learning_style: str
    preferred_modality: str
    preferred_analogies: list[str]
    pacing: str
    cognitive_load_trend: str
    bloom_level_reached: int
    common_misconceptions: list[dict]
    engagement_pattern: str
    narrative_persona: str
    successful_example_types: list[str]
    visual_continuity: dict
    adaptation_history: list[dict]


class AdaptationMetrics(TypedDict, total=False):
    adaptation_consistency: float
    personalization_strength: float
    continuity_score: float
    memory_reuse_score: float
    pedagogical_adaptation_quality: float
    longitudinal_coherence: float
    total_weeks: int
    adaptation_count: int
    memory_records_used: int


PEDAGOGICAL_KEYS = {
    "learning_style": "pedagogical:learning_style",
    "modality_preference": "pedagogical:modality_preference",
    "misconception": "pedagogical:misconception",
    "pacing": "pedagogical:pacing",
    "cognitive_load": "pedagogical:cognitive_load",
    "bloom_progress": "pedagogical:bloom_progress",
    "engagement": "pedagogical:engagement",
    "successful_example": "pedagogical:successful_example",
    "visual_continuity": "pedagogical:visual_continuity",
    "analogy_domain": "pedagogical:analogy_domain",
}


class PedagogicalMemoryService:
    """Facade over SharedMemoryStore for student-level pedagogical profiling.

    Each method maps to a fixed memory key pattern so that ``build_student_profile``
    can aggregate scattered observations into a single ``StudentProfile`` dict.

    The profile is consumed downstream by ``PromptEngineering``, ``AdaptiveLearning``,
    ``ConsistencyValidation``, and ``ConsensusMediator`` to produce *real* content
    adaptation (different prompts, scaffolding, decisions depending on history).
    """

    def __init__(self, memory_store: SharedMemoryStore):
        self._store = memory_store

    # ------------------------------------------------------------------
    # Record helpers – each publishes one observation to shared memory
    # ------------------------------------------------------------------

    def record_learning_style(self, student_id: str, learning_style: str, *, confidence: float = 0.8, module_id: str | None = None) -> str:
        return self._store.publish_observation(
            voter_name="pedagogical_memory",
            key=PEDAGOGICAL_KEYS["learning_style"],
            value={"learning_style": learning_style, "inferred_from": "history"},
            confidence=confidence,
            student_id=student_id,
            module_id=module_id,
            memory_type="pedagogical_profile",
        )

    def record_modality_preference(self, student_id: str, modality: str, *, confidence: float = 0.8, module_id: str | None = None) -> str:
        return self._store.publish_observation(
            voter_name="pedagogical_memory",
            key=PEDAGOGICAL_KEYS["modality_preference"],
            value={"modality": modality, "inferred_from": "history"},
            confidence=confidence,
            student_id=student_id,
            module_id=module_id,
            memory_type="pedagogical_profile",
        )

    def record_analogy_domain(self, student_id: str, domains: list[str], *, confidence: float = 0.7, module_id: str | None = None) -> str:
        return self._store.publish_observation(
            voter_name="pedagogical_memory",
            key=PEDAGOGICAL_KEYS["analogy_domain"],
            value={"domains": domains, "inferred_from": "history"},
            confidence=confidence,
            student_id=student_id,
            module_id=module_id,
            memory_type="pedagogical_profile",
        )

    def record_pacing(self, student_id: str, pacing: str, *, confidence: float = 0.7, module_id: str | None = None) -> str:
        return self._store.publish_observation(
            voter_name="pedagogical_memory",
            key=PEDAGOGICAL_KEYS["pacing"],
            value={"pacing": pacing, "inferred_from": "history"},
            confidence=confidence,
            student_id=student_id,
            module_id=module_id,
            memory_type="pedagogical_profile",
        )

    def record_cognitive_load(self, student_id: str, signal: float, *, confidence: float = 0.6, module_id: str | None = None) -> str:
        return self._store.publish_observation(
            voter_name="pedagogical_memory",
            key=PEDAGOGICAL_KEYS["cognitive_load"],
            value={"signal": signal, "trend": "increasing" if signal > 0.7 else "stable" if signal > 0.4 else "decreasing"},
            confidence=confidence,
            student_id=student_id,
            module_id=module_id,
            memory_type="pedagogical_profile",
        )

    def record_bloom_progress(self, student_id: str, bloom_level: int, *, confidence: float = 0.9, module_id: str | None = None) -> str:
        return self._store.publish_observation(
            voter_name="pedagogical_memory",
            key=PEDAGOGICAL_KEYS["bloom_progress"],
            value={"bloom_level": bloom_level},
            confidence=confidence,
            student_id=student_id,
            module_id=module_id,
            memory_type="pedagogical_profile",
        )

    def record_engagement(self, student_id: str, pattern: str, *, confidence: float = 0.6, module_id: str | None = None) -> str:
        return self._store.publish_observation(
            voter_name="pedagogical_memory",
            key=PEDAGOGICAL_KEYS["engagement"],
            value={"pattern": pattern},
            confidence=confidence,
            student_id=student_id,
            module_id=module_id,
            memory_type="pedagogical_profile",
        )

    def record_successful_example(self, student_id: str, example_type: str, *, confidence: float = 0.7, module_id: str | None = None) -> str:
        return self._store.publish_observation(
            voter_name="pedagogical_memory",
            key=PEDAGOGICAL_KEYS["successful_example"],
            value={"example_type": example_type},
            confidence=confidence,
            student_id=student_id,
            module_id=module_id,
            memory_type="pedagogical_profile",
        )

    # ------------------------------------------------------------------
    # Profile aggregation – read all pedagogical observations back
    # ------------------------------------------------------------------

    def build_student_profile(self, student_id: str) -> StudentProfile:
        """Aggregate pedagogical observations into a single StudentProfile dict.

        Uses ``query_sync`` (synchronous) so this method is safe to call from
        both sync FastAPI route handlers and async contexts that explicitly
        run it via ``run_in_executor``.  Calling the async ``query_by_key_pattern``
        without ``await`` was the root cause of the 500 error on
        ``GET /api/swarm/memory/profile/{student_id}``.
        """
        profile: StudentProfile = {"student_id": student_id}

        def _q(key_prefix: str, limit: int = 1) -> list:
            """Sync query helper: returns records whose key starts with key_prefix."""
            try:
                return [
                    r for r in self._store.query_sync(
                        student_id=student_id,
                        memory_type="pedagogical_profile",
                        limit=limit,
                        include_stale=False,
                    )
                    if isinstance(r.key, str) and r.key.startswith(key_prefix)
                ]
            except Exception:  # noqa: BLE001
                return []

        ls = _q(PEDAGOGICAL_KEYS["learning_style"])
        if ls:
            profile["learning_style"] = str(ls[0].value.get("learning_style", "visual"))

        mod = _q(PEDAGOGICAL_KEYS["modality_preference"])
        if mod:
            profile["preferred_modality"] = str(mod[0].value.get("modality", "image"))

        ad = _q(PEDAGOGICAL_KEYS["analogy_domain"])
        if ad:
            profile["preferred_analogies"] = list(ad[0].value.get("domains", []))

        pc = _q(PEDAGOGICAL_KEYS["pacing"])
        if pc:
            profile["pacing"] = str(pc[0].value.get("pacing", "moderate"))

        cl = _q(PEDAGOGICAL_KEYS["cognitive_load"], limit=3)
        if cl:
            signals = [r.value.get("signal", 0.5) for r in cl if isinstance(r.value, dict)]
            avg_signal = sum(signals) / len(signals) if signals else 0.5
            profile["cognitive_load_trend"] = "increasing" if avg_signal > 0.7 else "stable" if avg_signal > 0.4 else "decreasing"

        bp = _q(PEDAGOGICAL_KEYS["bloom_progress"])
        if bp:
            profile["bloom_level_reached"] = int(bp[0].value.get("bloom_level", 3))

        en = _q(PEDAGOGICAL_KEYS["engagement"])
        if en:
            profile["engagement_pattern"] = str(en[0].value.get("pattern", "consistent"))

        ex = _q(PEDAGOGICAL_KEYS["successful_example"], limit=3)
        if ex:
            profile["successful_example_types"] = [str(r.value.get("example_type", "")) for r in ex if isinstance(r.value, dict)]

        vc = _q(PEDAGOGICAL_KEYS["visual_continuity"])
        if vc:
            profile["visual_continuity"] = dict(vc[0].value) if isinstance(vc[0].value, dict) else {}

        return profile

    # ------------------------------------------------------------------
    # Adaptation metrics
    # ------------------------------------------------------------------

    def compute_metrics(self, student_id: str, weeks: int = 1) -> AdaptationMetrics:
        """Compute adaptation quality metrics using synchronous DB queries.

        Replaces the previous async ``count()`` calls (which returned unawaited
        coroutines in sync contexts) with sync ``query_sync`` counts.
        """
        def _count_sync(memory_type: str) -> int:
            try:
                return len(self._store.query_sync(
                    student_id=student_id,
                    memory_type=memory_type,
                    limit=500,
                    include_stale=False,
                ))
            except Exception:  # noqa: BLE001
                return 0

        total_pedagogical = _count_sync("pedagogical_profile")
        total_narrative = _count_sync("narrative_continuity")
        total_decision = _count_sync("pedagogical_decision")
        total_research = _count_sync("research")
        memory_used = total_pedagogical + total_narrative + total_decision + total_research

        profile = self.build_student_profile(student_id)
        filled = sum(1 for v in profile.values() if v not in (None, "", [], {}, 0))
        total_slots = len(StudentProfile.__annotations__) if hasattr(StudentProfile, "__annotations__") else 12
        adaptation_consistency = min(1.0, filled / max(1, total_slots))

        has_personalization = bool(profile.get("learning_style") or profile.get("preferred_analogies") or profile.get("preferred_modality"))
        personalization_strength = 0.8 if has_personalization else 0.0

        narrative_count = total_narrative
        continuity_score = min(1.0, narrative_count / max(1, weeks))

        reuse = min(1.0, (total_decision + total_pedagogical) / max(1, weeks * 3))
        ped_quality = (adaptation_consistency * 0.4 + personalization_strength * 0.3 + continuity_score * 0.3)
        longitudinal = continuity_score * 0.5 + adaptation_consistency * 0.3 + reuse * 0.2

        return AdaptationMetrics(
            adaptation_consistency=round(adaptation_consistency, 4),
            personalization_strength=round(personalization_strength, 4),
            continuity_score=round(continuity_score, 4),
            memory_reuse_score=round(reuse, 4),
            pedagogical_adaptation_quality=round(ped_quality, 4),
            longitudinal_coherence=round(longitudinal, 4),
            total_weeks=weeks,
            adaptation_count=filled,
            memory_records_used=memory_used,
        )
