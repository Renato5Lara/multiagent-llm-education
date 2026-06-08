"""
Tests for memory-influenced pedagogical generation.

Every test here proves that **shared memory changes generated content**.

We test at three levels:
  1. Unit – each agent adapts output when given a ``student_profile``
  2. Integration – ``PedagogicalMemoryService`` records & builds profiles
  3. Pipeline – ``PedagogicalOrchestrationService`` wires everything together
"""

from __future__ import annotations

import pytest
from app.memory.pedagogical_memory import PedagogicalMemoryService
from app.memory.shared_memory import memory_store_from_session
from app.services.pedagogical_orchestration_service import (
    AdaptiveLearning,
    ConsensusMediator,
    ConsistencyValidation,
    PromptEngineering,
)
from app.schemas.pedagogy import WeeklyPedagogicalPlanCreate


# =============================================================================
# 1. PromptEngineering – memory changes the prompts themselves
# =============================================================================


class TestPromptEngineeringAdaptation:
    """Same input → different prompts depending on student profile."""

    def _make_data(self, **overrides) -> WeeklyPedagogicalPlanCreate:
        params = dict(
            week_number=1,
            topic="Arreglos en Python",
            objectives=["Recorrer arreglos", "Buscar elementos"],
            bloom_target=3,
            pedagogical_style="abp",
            pedagogical_intention="Guiar al estudiante en la comprension de arreglos mediante practica progresiva",
            preferred_modality="visual",
        )
        params.update(overrides)
        return WeeklyPedagogicalPlanCreate(**params)

    def _fake_course(self):
        return type("Course", (), {"name": "Programacion I", "id": "c-1"})()

    def test_default_profile_no_adaptation(self, db):
        """No profile → no gaming/ music/ sports analogies, just default phase labels."""
        engine = PromptEngineering()
        data = self._make_data()
        result = engine.run(data, self._fake_course(), student_profile=None)

        sp = result["student_prompt"]
        # No analogy intro
        assert "Como en un videojuego" not in sp
        assert "Como una pieza musical" not in sp
        assert "Como en el deporte" not in sp
        # No learning-style context
        assert "Prioriza ejemplos visuales" not in sp
        assert "Incluye explicaciones auditivas" not in sp
        # Default phase labels ARE present
        assert "Activacion" in sp

    def test_visual_gaming_profile_adds_analogy_intro(self, db):
        """Visual + gaming profile → gaming intro is injected into prompts."""
        engine = PromptEngineering()
        data = self._make_data()
        profile = {
            "learning_style": "visual",
            "preferred_analogies": ["gaming"],
            "preferred_modality": "image",
        }
        result = engine.run(data, self._fake_course(), student_profile=profile)

        sp = result["student_prompt"]
        tp = result["tutor_prompt"]
        assert "Como en un videojuego" in sp, "gaming intro should appear in student_prompt"
        assert "Como en un videojuego" in tp, "gaming intro should appear in tutor_prompt"
        assert "Prioriza ejemplos visuales" in sp, "visual learning context should appear"
        assert "Prioriza ejemplos visuales" in tp, "visual learning context should appear in tutor_prompt"
        # Phase labels should be gaming-themed
        assert "Tutorial" in sp or "Nivel 1" in sp, "gaming phase labels should appear"

    def test_auditory_music_profile_adds_music_analogy(self, db):
        """Auditory + music profile → music intro is injected."""
        engine = PromptEngineering()
        data = self._make_data()
        profile = {
            "learning_style": "auditory",
            "preferred_analogies": ["music"],
        }
        result = engine.run(data, self._fake_course(), student_profile=profile)

        sp = result["student_prompt"]
        assert "Como una pieza musical" in sp, "music intro should appear"
        assert "Incluye explicaciones auditivas" in sp, "auditory context should appear"
        assert "Compas 1" in sp, "music phase labels should appear"

    def test_kinesthetic_sports_profile(self, db):
        """Kinesthetic + sports profile → sports intro."""
        engine = PromptEngineering()
        data = self._make_data()
        profile = {
            "learning_style": "kinesthetic",
            "preferred_analogies": ["sports"],
        }
        result = engine.run(data, self._fake_course(), student_profile=profile)

        sp = result["student_prompt"]
        assert "Como en el deporte" in sp, "sports intro should appear"
        assert "Disena actividades practicas" in sp, "kinesthetic context should appear"
        assert "Calentamiento" in sp or "Entrenamiento" in sp, "sports phase labels should appear"

    def test_profile_adds_adapation_info(self, db):
        """Result includes adaptation_info metadata block."""
        engine = PromptEngineering()
        data = self._make_data()
        profile = {
            "learning_style": "visual",
            "preferred_analogies": ["gaming"],
        }
        result = engine.run(data, self._fake_course(), student_profile=profile)

        info = result.get("adaptation_info")
        assert info is not None
        assert info["analogy_domain"] == "gaming"
        assert info["learning_style"] == "visual"
        assert info["tone"] == "gamificada"
        assert "Tutorial" in info["phase_labels"]


# =============================================================================
# 2. AdaptiveLearning – memory changes scaffolding and targets
# =============================================================================


class TestAdaptiveLearningAdaptation:
    """Same input → different scaffolding/bloom based on student profile."""

    def _make_data(self, **overrides) -> WeeklyPedagogicalPlanCreate:
        params = dict(
            week_number=2,
            topic="Busqueda Binaria",
            objectives=["Implementar busqueda"],
            bloom_target=4,
            pedagogical_style="abp",
            pedagogical_intention="Guiar al estudiante en comprension de busqueda binaria mediante ejercicios practicos",
            preferred_modality="interactive",
        )
        params.update(overrides)
        return WeeklyPedagogicalPlanCreate(**params)

    def test_no_profile_default_scaffolding(self, db):
        """No profile → no bloom adjustment, default scaffolding."""
        adaptive = AdaptiveLearning()
        data = self._make_data()
        result = adaptive.run(data)

        assert result["bloom_target"] == 4
        assert result["bloom_adjusted"] is False
        assert "diagnostico breve de entrada" in result["scaffolding"]
        assert "pausa de reflexion" not in " ".join(result["scaffolding"])

    def test_cognitive_overload_reduces_bloom(self, db):
        """Cognitive load increasing → bloom target reduced by 1, extra scaffolding."""
        adaptive = AdaptiveLearning()
        data = self._make_data()
        profile = {
            "cognitive_load_trend": "increasing",
            "learning_style": "visual",
        }
        result = adaptive.run(data, student_profile=profile)

        assert result["bloom_target"] == 3, "bloom should be reduced from 4 to 3"
        assert result["bloom_adjusted"] is True
        assert result["adaptation_rationale"]["bloom_adjusted_reason"] == "carga cognitiva alta, reduciendo dificultad"
        assert "pausa de reflexion y consolidacion" in result["scaffolding"]

    def test_fast_pacing_removes_diagnostic(self, db):
        """Fast pacing → diagnostic and warm-up scaffolding items are removed."""
        adaptive = AdaptiveLearning()
        data = self._make_data()
        profile = {
            "pacing": "fast",
        }
        result = adaptive.run(data, student_profile=profile)
        # diagnosis items should be filtered out
        scaffolding_text = " ".join(result["scaffolding"])
        assert "diagnostico" not in scaffolding_text, "diagnostic should be removed for fast pacing"

    def test_gaming_analogy_changes_phases(self, db):
        """Gaming analogies → phase labels are gaming-themed."""
        adaptive = AdaptiveLearning()
        data = self._make_data()
        profile = {
            "preferred_analogies": ["gaming"],
        }
        result = adaptive.run(data, student_profile=profile)

        diff = result["differentiation"]
        assert "modo facil" in diff["support"], "gaming-themed differentiation support"
        assert "modo normal" in diff["standard"], "gaming-themed differentiation standard"
        assert "modo dificil" in diff["advanced"], "gaming-themed differentiation advanced"
        assert "tutorial interactivo" in " ".join(result["scaffolding"])


# =============================================================================
# 3. ConsistencyValidation – profile triggers continuity issues
# =============================================================================


class TestConsistencyValidationAdaptation:
    """Student profile triggers continuity checks."""

    def _make_data(self, **overrides) -> WeeklyPedagogicalPlanCreate:
        params = dict(
            week_number=1,
            topic="Listas",
            objectives=["Insertar", "Eliminar"],
            bloom_target=3,
            pedagogical_style="abp",
            pedagogical_intention="Guiar al estudiante en comprension de listas enlazadas con ejercicios practicos progresivos",
            preferred_modality="visual",
        )
        params.update(overrides)
        return WeeklyPedagogicalPlanCreate(**params)

    def test_visual_profile_missing_visual_elements(self, db):
        """Visual learner but sequence has no visual focus → info issue emitted."""
        validator = ConsistencyValidation()
        data = self._make_data()
        profile = {"learning_style": "visual"}
        structure = {
            "weekly_sequence": [
                {"phase": "activation", "focus": "Repasar conceptos previos"},
            ]
        }
        result = validator.run(
            data,
            research_validation={"valid": True, "issues": []},
            structure=structure,
            student_profile=profile,
        )
        types = [i["type"] for i in result["issues"]]
        assert "continuity:missing_visual_elements" in types, "visual continuity issue should be flagged"

    def test_analogy_profile_missing_analogy_elements(self, db):
        """Gaming preference but no gaming focus in sequence → info issue."""
        validator = ConsistencyValidation()
        data = self._make_data()
        profile = {"preferred_analogies": ["gaming"]}
        structure = {
            "weekly_sequence": [
                {"phase": "exploration", "focus": "Explorar fuentes"},
            ]
        }
        result = validator.run(
            data,
            research_validation={"valid": True, "issues": []},
            structure=structure,
            student_profile=profile,
        )
        types = [i["type"] for i in result["issues"]]
        assert "continuity:missing_analogy_domain" in types

    def test_no_profile_no_continuity_issues(self, db):
        """No profile → no continuity issues."""
        validator = ConsistencyValidation()
        data = self._make_data()
        structure = {"weekly_sequence": [{"phase": "a", "focus": "Test"}]}
        result = validator.run(
            data,
            research_validation={"valid": True, "issues": []},
            structure=structure,
            student_profile=None,
        )
        types = [i["type"] for i in result["issues"]]
        assert "continuity:missing_visual_elements" not in types


# =============================================================================
# 4. ConsensusMediator – profile affects confidence
# =============================================================================


class TestConsensusMediatorAdaptation:
    """Student profile adjusts confidence weights."""

    def test_increasing_cognitive_load_lowers_confidence(self, db):
        """Cognitive load increasing → profile_influence is negative."""
        mediator = ConsensusMediator()
        result = mediator.run(
            validation={"valid": True},
            research_metrics={"pedagogical_confidence": 0.6},
            student_profile={"cognitive_load_trend": "increasing"},
        )
        assert result["profile_influence"] < 0, "increasing load should lower confidence"
        assert "profile_influence" in result

    def test_dropping_engagement_also_lowers(self, db):
        """Dropping engagement → profile_influence is negative."""
        mediator = ConsensusMediator()
        result = mediator.run(
            validation={"valid": True},
            research_metrics={"pedagogical_confidence": 0.6},
            student_profile={"engagement_pattern": "dropping"},
        )
        assert result["profile_influence"] < 0

    def test_known_profile_boosts_confidence(self, db):
        """Known learning style → small positive influence."""
        mediator = ConsensusMediator()
        result = mediator.run(
            validation={"valid": True},
            research_metrics={"pedagogical_confidence": 0.6},
            student_profile={"learning_style": "visual"},
        )
        assert result["profile_influence"] > 0, "known learning style should boost confidence"
        assert result["profile_influence"] > 0.02  # 0.03 boost for known style

    def test_adaptation_signals_in_result(self, db):
        """Result includes adaptation_signals for dashboard."""
        mediator = ConsensusMediator()
        result = mediator.run(
            validation={"valid": True},
            research_metrics={"pedagogical_confidence": 0.5},
            student_profile={
                "cognitive_load_trend": "stable",
                "engagement_pattern": "consistent",
            },
        )
        assert "adaptation_signals" in result
        assert result["adaptation_signals"]["cognitive_load_trend"] == "stable"


# =============================================================================
# 5. PedagogicalMemoryService – record and build profile
# =============================================================================


class TestPedagogicalMemoryService:
    """Full lifecycle: record pedagogical observations → build profile."""

    def test_build_profile_from_records(self, db):
        """After recording preferences, build_student_profile returns them."""
        store = memory_store_from_session(db)
        svc = PedagogicalMemoryService(store)

        svc.record_learning_style("stu-1", "visual", module_id="mod-1")
        svc.record_modality_preference("stu-1", "image", module_id="mod-1")
        svc.record_analogy_domain("stu-1", ["gaming"], module_id="mod-1")
        svc.record_pacing("stu-1", "moderate", module_id="mod-1")
        svc.record_cognitive_load("stu-1", 0.8, module_id="mod-1")  # > 0.7 → increasing
        svc.record_bloom_progress("stu-1", 4, module_id="mod-1")
        svc.record_engagement("stu-1", "consistent", module_id="mod-1")
        svc.record_successful_example("stu-1", "visual_diagram", module_id="mod-1")

        profile = svc.build_student_profile("stu-1")
        assert profile["student_id"] == "stu-1"
        assert profile.get("learning_style") == "visual"
        assert profile.get("preferred_modality") == "image"
        assert profile.get("preferred_analogies") == ["gaming"]
        assert profile.get("pacing") == "moderate"
        assert profile.get("cognitive_load_trend") == "increasing"
        assert profile.get("bloom_level_reached") == 4
        assert profile.get("engagement_pattern") == "consistent"
        assert profile.get("successful_example_types") == ["visual_diagram"]

    def test_empty_profile_returns_defaults(self, db):
        """No records → empty profile with just student_id."""
        store = memory_store_from_session(db)
        svc = PedagogicalMemoryService(store)
        profile = svc.build_student_profile("stu-unknown")
        assert profile["student_id"] == "stu-unknown"
        # All other fields should be absent (TypedDict allows missing keys)
        assert profile.get("learning_style") is None
        assert profile.get("preferred_analogies") is None

    def test_profile_scoped_by_student(self, db):
        """Records for student A do not leak into student B's profile."""
        store = memory_store_from_session(db)
        svc = PedagogicalMemoryService(store)

        svc.record_learning_style("stu-a", "visual", module_id="mod-1")
        svc.record_learning_style("stu-b", "auditory", module_id="mod-1")

        profile_a = svc.build_student_profile("stu-a")
        profile_b = svc.build_student_profile("stu-b")
        assert profile_a.get("learning_style") == "visual"
        assert profile_b.get("learning_style") == "auditory"


# =============================================================================
# 6. PedagogicalMemoryService – metrics
# =============================================================================


class TestPedagogicalMemoryMetrics:
    """compute_metrics returns coherent values."""

    def test_metrics_with_no_memory(self, db):
        store = memory_store_from_session(db)
        svc = PedagogicalMemoryService(store)
        metrics = svc.compute_metrics("stu-1")
        # student_id alone counts as 1 filled slot out of 13 → ~0.077
        assert 0.07 <= metrics["adaptation_consistency"] <= 0.09
        assert metrics["personalization_strength"] == 0.0
        assert metrics["continuity_score"] == 0.0
        assert metrics["memory_reuse_score"] == 0.0
        assert metrics["memory_records_used"] == 0

    def test_metrics_with_full_profile(self, db):
        store = memory_store_from_session(db)
        svc = PedagogicalMemoryService(store)

        svc.record_learning_style("stu-1", "visual", module_id="mod-1")
        svc.record_analogy_domain("stu-1", ["gaming"], module_id="mod-1")
        svc.record_modality_preference("stu-1", "image", module_id="mod-1")

        metrics = svc.compute_metrics("stu-1")
        assert metrics["adaptation_consistency"] > 0
        assert metrics["personalization_strength"] > 0.5
        assert metrics["memory_records_used"] > 0


# =============================================================================
# 7. Full pipeline: same input → different output with different memory
# =============================================================================


class TestFullPipelineAdaptation:
    """End-to-end: orchestrator produces qualitatively different plans
    when the student profile in shared memory changes."""

    @pytest.mark.asyncio
    async def test_pipeline_without_memory(self, db):
        """Smoke test: pipeline runs without memory store, produces default output."""
        from app.models.course import Course
        from app.models.user import User, UserRole
        from app.services.pedagogical_orchestration_service import (
            PedagogicalOrchestrationService,
        )

        teacher = User(id="tea-1", email="tea@test.com", hashed_password="x", first_name="Teacher", last_name="Test", role=UserRole.DOCENTE, is_active=True)
        db.add(teacher)
        course = Course(id="c-1", name="Curso Test", teacher_id="tea-1", code="PED-01", cycle=1, year=2026)
        db.add(course)
        db.flush()

        svc = PedagogicalOrchestrationService()
        data = WeeklyPedagogicalPlanCreate(
            week_number=1,
            topic="Arreglos",
            objectives=["Recorrer"],
            bloom_target=3,
            pedagogical_style="abp",
            pedagogical_intention="Guiar al estudiante en arreglos mediante practica progresiva con ejemplos claros y ejercicios guiados",
            preferred_modality="visual",
        )
        plan = await svc.generate_weekly_plan(db, course, teacher, data, memory_store=None)
        assert plan.topic == "Arreglos"
        # Should produce default prompts
        tp = plan.prompt_plan or {}
        assert "student_prompt" in tp

    @pytest.mark.asyncio
    async def test_pipeline_with_memory_changes_output(self, db):
        """Pipeline with student profile → prompts include adaptation."""
        from app.models.course import Course
        from app.models.user import User, UserRole
        from app.services.pedagogical_orchestration_service import (
            PedagogicalOrchestrationService,
        )

        teacher = User(id="tea-2", email="tea2@test.com", hashed_password="x", first_name="Teacher2", last_name="Test2", role=UserRole.DOCENTE, is_active=True)
        db.add(teacher)
        course = Course(id="c-2", name="Curso Test 2", teacher_id="tea-2", code="PED-02", cycle=1, year=2026)
        db.add(course)
        db.flush()

        store = memory_store_from_session(db)
        ped = PedagogicalMemoryService(store)

        ped.record_learning_style(teacher.id, "visual", module_id=f"{course.id}:week0")
        ped.record_analogy_domain(teacher.id, ["gaming"], module_id=f"{course.id}:week0")
        ped.record_modality_preference(teacher.id, "image", module_id=f"{course.id}:week0")

        svc = PedagogicalOrchestrationService()
        data = WeeklyPedagogicalPlanCreate(
            week_number=1,
            topic="Arreglos",
            objectives=["Recorrer"],
            bloom_target=3,
            pedagogical_style="abp",
            pedagogical_intention="Guiar al estudiante en arreglos mediante practica progresiva con ejemplos claros y ejercicios guiados",
            preferred_modality="visual",
        )
        plan = await svc.generate_weekly_plan(db, course, teacher, data, memory_store=store)
        assert plan.topic == "Arreglos"

        tp = plan.prompt_plan or {}
        sp = tp.get("student_prompt", "")
        assert "Como en un videojuego" in sp, "gaming intro should appear when profile is set"
        assert "Prioriza ejemplos visuales" in sp, "visual context should appear"

        ap = plan.adaptive_plan or {}
        diff = ap.get("differentiation", {})
        assert "modo facil" in str(diff), "gaming-themed differentiation should appear"


# =============================================================================
# 8. Cross-week continuity: memory persists across weeks
# =============================================================================


class TestCrossWeekContinuity:
    """Memory built in week N is available in week N+1."""

    def test_profile_persists_across_weeks(self, db):
        """Records from week 1 appear in week 2 profile."""
        store = memory_store_from_session(db)
        svc = PedagogicalMemoryService(store)

        svc.record_learning_style("stu-1", "visual", module_id="c-1:week1")
        svc.record_analogy_domain("stu-1", ["gaming"], module_id="c-1:week1")

        # Simulate week 2 — build profile from all previous memory
        profile = svc.build_student_profile("stu-1")
        assert profile.get("learning_style") == "visual", "learning style should persist"
        assert profile.get("preferred_analogies") == ["gaming"], "analogy domain should persist"

    def test_multiple_weeks_accumulate(self, db):
        """Multiple weeks of records produce richer profile."""
        store = memory_store_from_session(db)
        svc = PedagogicalMemoryService(store)

        # Week 1
        svc.record_learning_style("stu-1", "visual", module_id="c-1:week1")
        svc.record_analogy_domain("stu-1", ["gaming"], module_id="c-1:week1")
        svc.record_bloom_progress("stu-1", 2, module_id="c-1:week1")

        # Week 2
        svc.record_bloom_progress("stu-1", 4, module_id="c-1:week2")

        # Week 3 — should see latest bloom (4) and everything else
        profile = svc.build_student_profile("stu-1")
        assert profile.get("learning_style") == "visual"
        assert profile.get("preferred_analogies") == ["gaming"]
        assert profile.get("bloom_level_reached") == 4, "should get latest bloom level"

    def test_narrative_continuity_cross_week(self, db):
        """Narrative persona published in week 1 is queryable in week 2."""
        from app.memory.narrative_continuity import publish_narrative_persona, query_narrative_persona

        store = memory_store_from_session(db)

        # Week 1: publish persona
        publish_narrative_persona(
            store,
            persona="Profesor visual con camisa azul y gafas",
            tone="conversacional",
            student_id="stu-1",
            module_id="c-1:week1",
        )

        # Week 2: query should find it
        narrative = query_narrative_persona(store, student_id="stu-1", module_id="c-1:week1")
        assert "persona" in narrative
        assert narrative["persona"]["description"] == "Profesor visual con camisa azul y gafas"


# =============================================================================
# 9. Memory influence endpoint returns profile
# =============================================================================


def test_memory_profile_endpoint(client, docente_token, db):
    """GET /api/swarm/memory/profile/{student_id} returns profile + metrics."""
    store = memory_store_from_session(db)
    svc = PedagogicalMemoryService(store)
    svc.record_learning_style("profile-stu", "visual", module_id="mod-1")
    db.commit()

    resp = client.get(
        "/api/swarm/memory/profile/profile-stu",
        headers={"Authorization": f"Bearer {docente_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["student_id"] == "profile-stu"
    assert data["profile"]["learning_style"] == "visual"
    assert "metrics" in data
    assert data["metrics"]["adaptation_consistency"] > 0


# =============================================================================
# 10. ResearchAgent publishes pedagogical signals in state
# =============================================================================


@pytest.mark.asyncio
async def test_research_agent_publishes_student_profile_in_memory(db):
    """When student_profile is in state, ResearchAgent publishes it as memory."""
    from app.agents.research_agent import ResearchAgent

    store = memory_store_from_session(db)
    agent = ResearchAgent(shared_memory_store=store)
    state = await agent.analyze({
        "topic": "Prueba",
        "objectives": ["Test"],
        "bloom_target": 3,
        "language": "es",
        "student_id": "stu-profile",
        "module_id": "mod-1",
        "student_profile": {
            "learning_style": "visual",
            "preferred_analogies": ["gaming"],
        },
    })
    memory_ids = state.get("memory_ids", [])
    assert len(memory_ids) > 0

    # Check that research:student_profile was published
    from app.models.shared_memory_record import SharedMemoryRecord as SMR
    records = db.query(SMR).filter(SMR.id.in_(memory_ids)).all()
    keys = {r.key for r in records}
    assert "research:student_profile" in keys
    # Find the profile record and verify its contents
    profile_record = next(r for r in records if r.key == "research:student_profile")
    assert profile_record.value.get("learning_style") == "visual"
    assert profile_record.value.get("preferred_analogies") == ["gaming"]
