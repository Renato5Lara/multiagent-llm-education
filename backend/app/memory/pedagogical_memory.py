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
        profile: StudentProfile = {"student_id": student_id}

        ls = self._store.query_by_key_pattern(key_prefix=PEDAGOGICAL_KEYS["learning_style"], student_id=student_id, memory_type="pedagogical_profile", limit=1)
        if ls:
            profile["learning_style"] = str(ls[0].value.get("learning_style", "visual"))

        mod = self._store.query_by_key_pattern(key_prefix=PEDAGOGICAL_KEYS["modality_preference"], student_id=student_id, memory_type="pedagogical_profile", limit=1)
        if mod:
            profile["preferred_modality"] = str(mod[0].value.get("modality", "image"))

        ad = self._store.query_by_key_pattern(key_prefix=PEDAGOGICAL_KEYS["analogy_domain"], student_id=student_id, memory_type="pedagogical_profile", limit=1)
        if ad:
            profile["preferred_analogies"] = list(ad[0].value.get("domains", []))

        pc = self._store.query_by_key_pattern(key_prefix=PEDAGOGICAL_KEYS["pacing"], student_id=student_id, memory_type="pedagogical_profile", limit=1)
        if pc:
            profile["pacing"] = str(pc[0].value.get("pacing", "moderate"))

        cl = self._store.query_by_key_pattern(key_prefix=PEDAGOGICAL_KEYS["cognitive_load"], student_id=student_id, memory_type="pedagogical_profile", limit=3)
        if cl:
            signals = [r.value.get("signal", 0.5) for r in cl if isinstance(r.value, dict)]
            avg_signal = sum(signals) / len(signals) if signals else 0.5
            profile["cognitive_load_trend"] = "increasing" if avg_signal > 0.7 else "stable" if avg_signal > 0.4 else "decreasing"

        bp = self._store.query_by_key_pattern(key_prefix=PEDAGOGICAL_KEYS["bloom_progress"], student_id=student_id, memory_type="pedagogical_profile", limit=1)
        if bp:
            profile["bloom_level_reached"] = int(bp[0].value.get("bloom_level", 3))

        en = self._store.query_by_key_pattern(key_prefix=PEDAGOGICAL_KEYS["engagement"], student_id=student_id, memory_type="pedagogical_profile", limit=1)
        if en:
            profile["engagement_pattern"] = str(en[0].value.get("pattern", "consistent"))

        ex = self._store.query_by_key_pattern(key_prefix=PEDAGOGICAL_KEYS["successful_example"], student_id=student_id, memory_type="pedagogical_profile", limit=3)
        if ex:
            profile["successful_example_types"] = [str(r.value.get("example_type", "")) for r in ex if isinstance(r.value, dict)]

        vc = self._store.query_by_key_pattern(key_prefix=PEDAGOGICAL_KEYS["visual_continuity"], student_id=student_id, memory_type="pedagogical_profile", limit=1)
        if vc:
            profile["visual_continuity"] = dict(vc[0].value) if isinstance(vc[0].value, dict) else {}

        return profile

    # ------------------------------------------------------------------
    # Adaptation metrics
    # ------------------------------------------------------------------

    def compute_metrics(self, student_id: str, weeks: int = 1) -> AdaptationMetrics:
        total_pedagogical = self._store.count(student_id=student_id, memory_type="pedagogical_profile")
        total_narrative = self._store.count(student_id=student_id, memory_type="narrative_continuity")
        total_decision = self._store.count(student_id=student_id, memory_type="pedagogical_decision")
        total_research = self._store.count(student_id=student_id, memory_type="research")
        memory_used = total_pedagogical + total_narrative + total_decision + total_research

        profile = self.build_student_profile(student_id)
        filled = sum(1 for v in profile.values() if v not in (None, "", [], {}, 0))
        total_slots = len(StudentProfile.__annotations__) if hasattr(StudentProfile, "__annotations__") else 12
        adaptation_consistency = min(1.0, filled / max(1, total_slots))

        has_personalization = bool(profile.get("learning_style") or profile.get("preferred_analogies") or profile.get("preferred_modality"))
        personalization_strength = 0.8 if has_personalization else 0.0

        narrative_count = self._store.count(student_id=student_id, memory_type="narrative_continuity")
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
