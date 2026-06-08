"""
Tests for shared memory wiring in the pedagogical swarm pipeline.

Covers:
    1. memory_store_from_session() factory
    2. Narrative continuity query + publish
    3. ResearchAgent publishes memory when wired
    4. PromptEngineering consumes memory
    5. ConsistencyValidation consumes memory
    6. ConsensusMediator factors in prior memory
    7. ModuleOrchestrationService publishes narrative memory
    8. PedagogicalOrchestrationService publishes narrative memory
    9. SSE memory stream endpoint
"""

from __future__ import annotations

import pytest
from app.memory.narrative_continuity import (
    NARRATIVE_MEMORY_TYPE,
    publish_narrative_persona,
    query_narrative_persona,
)
from app.memory.shared_memory import SharedMemoryStore, memory_store_from_session
from app.models.course import Course
from app.models.shared_memory_record import SharedMemoryRecord
from app.models.user import User, UserRole
from app.weekly_learning.models import CourseWeek, WeeklyPlan


# =============================================================================
# 1. Factory
# =============================================================================


class TestMemoryStoreFromSession:
    def test_creates_store_from_session(self, db):
        store = memory_store_from_session(db)
        assert isinstance(store, SharedMemoryStore)
        assert store._uow.db is db

    def test_store_uses_same_transaction(self, db):
        store = memory_store_from_session(db)
        record_id = store.publish_observation(
            voter_name="test",
            key="test:tx",
            value={"tx": True},
        )
        record = db.query(SharedMemoryRecord).filter(SharedMemoryRecord.id == record_id).first()
        assert record is not None
        assert record.voter_name == "test"

    def test_multiple_stores_same_session(self, db):
        store1 = memory_store_from_session(db)
        store2 = memory_store_from_session(db)
        id1 = store1.publish_observation(voter_name="a", key="x", value={"n": 1})
        id2 = store2.publish_observation(voter_name="b", key="y", value={"n": 2})
        assert id1 != id2
        assert db.query(SharedMemoryRecord).count() == 2


# =============================================================================
# 2. Narrative Continuity
# =============================================================================


class TestNarrativeContinuity:
    def test_query_returns_empty_when_no_memory(self, db):
        store = memory_store_from_session(db)
        result = query_narrative_persona(store, student_id="stu-1", module_id="mod-1")
        assert result == {}

    def test_publish_and_query_persona(self, db):
        store = memory_store_from_session(db)
        ids = publish_narrative_persona(
            store,
            persona="Profesor visual con camisa azul",
            tone="conversacional",
            character="Profesor Miguel",
            bloom_progress="Nivel 2 alcanzado",
            student_id="stu-1",
            module_id="mod-1",
            confidence=0.85,
        )
        assert len(ids) >= 3  # persona + tone + bloom_progress, optionally character

        result = query_narrative_persona(store, student_id="stu-1", module_id="mod-1")
        assert "persona" in result
        assert result["persona"]["description"] == "Profesor visual con camisa azul"
        assert "tone" in result
        assert result["tone"]["tone"] == "conversacional"

    def test_narrative_scoped_by_student(self, db):
        store = memory_store_from_session(db)
        publish_narrative_persona(
            store, persona="P1", student_id="stu-1", module_id="mod-1",
        )
        publish_narrative_persona(
            store, persona="P2", student_id="stu-2", module_id="mod-1",
        )

        r1 = query_narrative_persona(store, student_id="stu-1", module_id="mod-1")
        r2 = query_narrative_persona(store, student_id="stu-2", module_id="mod-1")
        assert r1["persona"]["description"] == "P1"
        assert r2["persona"]["description"] == "P2"

    def test_narrative_memory_type(self, db):
        store = memory_store_from_session(db)
        publish_narrative_persona(
            store, persona="Test", student_id="stu-1", module_id="mod-1",
        )
        records = store.query(
            student_id="stu-1",
            memory_type=NARRATIVE_MEMORY_TYPE,
        )
        assert len(records) >= 2
        for r in records:
            assert r.memory_type == NARRATIVE_MEMORY_TYPE


# =============================================================================
# 3. ResearchAgent publishes memory when wired
# =============================================================================


@pytest.mark.asyncio
async def test_research_agent_publishes_memory(db):
    from app.agents.research_agent import ResearchAgent

    store = memory_store_from_session(db)
    agent = ResearchAgent(shared_memory_store=store)
    state = await agent.analyze({
        "topic": "Prueba",
        "objectives": ["Test"],
        "bloom_target": 3,
        "language": "es",
        "student_id": "stu-1",
        "module_id": "mod-1",
    })
    memory_ids = state.get("memory_ids", [])
    assert len(memory_ids) > 0, "ResearchAgent should publish memory when store is wired"

    records = db.query(SharedMemoryRecord).filter(
        SharedMemoryRecord.id.in_(memory_ids)
    ).all()
    assert len(records) == len(memory_ids)
    keys = {r.key for r in records}
    assert "research:summary" in keys
    assert "research:metrics" in keys
    assert "research:misconceptions" in keys


@pytest.mark.asyncio
async def test_research_agent_no_memory_when_no_store(db):
    from app.agents.research_agent import ResearchAgent

    agent = ResearchAgent(shared_memory_store=None)
    state = await agent.analyze({
        "topic": "Prueba",
        "objectives": ["Test"],
        "bloom_target": 3,
        "language": "es",
    })
    assert state.get("memory_ids") == []


# =============================================================================
# 4. PromptEngineering consumes memory
# =============================================================================


def test_prompt_engineering_consumes_narrative_memory(db):
    from app.services.pedagogical_orchestration_service import PromptEngineering
    from app.schemas.pedagogy import WeeklyPedagogicalPlanCreate

    store = memory_store_from_session(db)
    publish_narrative_persona(
        store, persona="Profesor amigable",
        student_id="tea-1", module_id="course:week1",
    )

    engine = PromptEngineering()
    data = WeeklyPedagogicalPlanCreate(
        week_number=1,
        topic="Matematicas",
        objectives=["Sumar"],
        bloom_target=2,
        pedagogical_style="socratico",
        pedagogical_intention="Fomentar el pensamiento critico en matematicas basicas",
        preferred_modality="visual",
    )
    course = type("Course", (), {"name": "Matematicas", "id": "c-1"})()

    result = engine.run(data, course, memory_store=store, student_id="tea-1")
    assert "Profesor amigable" in result["student_prompt"]
    assert "Profesor amigable" in result["tutor_prompt"]
    assert "Profesor amigable" in result["teacher_review_prompt"]


def test_prompt_engineering_no_memory_fallback(db):
    from app.services.pedagogical_orchestration_service import PromptEngineering
    from app.schemas.pedagogy import WeeklyPedagogicalPlanCreate

    engine = PromptEngineering()
    data = WeeklyPedagogicalPlanCreate(
        week_number=1, topic="Test", objectives=["O"],
        bloom_target=2, pedagogical_style="socratico",
        pedagogical_intention="Intencion clara para el curso de prueba",
        preferred_modality="text",
    )
    course = type("Course", (), {"name": "Curso", "id": "c-1"})()
    result = engine.run(data, course, memory_store=None)
    # Should still work without memory
    assert "Curso" in result["student_prompt"]


# =============================================================================
# 5. ConsistencyValidation consumes memory
# =============================================================================


def test_consistency_validation_checks_memory(db):
    from app.services.pedagogical_orchestration_service import ConsistencyValidation
    from app.schemas.pedagogy import WeeklyPedagogicalPlanCreate

    store = memory_store_from_session(db)
    # Publish a past record with an issue
    store.publish_observation(
        voter_name="consistency_agent",
        key="consensus:result",
        value={"issues": [{"type": "missing_objectives", "severity": "error"}]},
        confidence=0.9,
        student_id="tea-1",
        memory_type="pedagogical_decision",
    )

    validator = ConsistencyValidation()
    data = WeeklyPedagogicalPlanCreate(
        week_number=2, topic="Test", objectives=["O1", "O2"],
        bloom_target=3, pedagogical_style="abp",
        pedagogical_intention="Intencion clara y suficientemente larga para aprobar",
        preferred_modality="text",
    )
    result = validator.run(
        data,
        research_validation={"valid": True, "issues": []},
        structure={"weekly_sequence": [{"phase": "a"}]},
        memory_store=store,
        student_id="tea-1",
        course_id="c-1",
    )
    issues = [i["type"] for i in result["issues"]]
    assert "recurring:missing_objectives" in issues


def test_consistency_validation_no_memory_fallback(db):
    from app.services.pedagogical_orchestration_service import ConsistencyValidation
    from app.schemas.pedagogy import WeeklyPedagogicalPlanCreate

    validator = ConsistencyValidation()
    data = WeeklyPedagogicalPlanCreate(
        week_number=1, topic="Test", objectives=["O"],
        bloom_target=2, pedagogical_style="socratico",
        pedagogical_intention="Intencion clara para curso de prueba",
        preferred_modality="text",
    )
    result = validator.run(
        data,
        research_validation={"valid": True, "issues": []},
        structure={"weekly_sequence": [{"phase": "a"}]},
        memory_store=None,
    )
    assert result["valid"] is True


# =============================================================================
# 6. ConsensusMediator factors prior memory
# =============================================================================


def test_consensus_uses_past_confidence(db):
    from app.services.pedagogical_orchestration_service import ConsensusMediator

    store = memory_store_from_session(db)
    # Publish past high-confidence decisions
    for conf in [0.9, 0.85]:
        store.publish_observation(
            voter_name="consensus",
            key="consensus:result",
            value={"confidence": conf},
            confidence=conf,
            student_id="stu-1",
            memory_type="pedagogical_decision",
        )

    mediator = ConsensusMediator()
    result = mediator.run(
        validation={"valid": True},
        research_metrics={"pedagogical_confidence": 0.5},
        memory_store=store,
        student_id="stu-1",
    )
    # Past confidence (avg 0.875 * 0.1 = 0.0875) should boost base 0.5 → ~0.5875
    assert result["confidence"] > 0.5
    assert result["memory_influence"] > 0.0
    assert result["base_confidence"] == 0.5


def test_consensus_no_memory_fallback(db):
    from app.services.pedagogical_orchestration_service import ConsensusMediator

    mediator = ConsensusMediator()
    result = mediator.run(
        validation={"valid": True},
        research_metrics={"pedagogical_confidence": 0.6},
        memory_store=None,
    )
    assert result["decision"] == "approve"
    assert result["memory_influence"] == 0.0


# =============================================================================
# 7. Narrative persistence through orchestrators
# =============================================================================


@pytest.mark.asyncio
async def test_module_orchestrator_publishes_narrative(db):
    from app.services.module_orchestration_service import ModuleOrchestrationService
    from app.models.user import User, UserRole

    store = memory_store_from_session(db)
    student = User(id="stu-1", role=UserRole.ESTUDIANTE)
    course = type("Course", (), {"id": "c-1", "name": "Curso"})()
    module = type("PathModule", (), {"id": "mod-1", "title": "Arreglos", "bloom_level": 3})()

    svc = ModuleOrchestrationService()
    result = await svc.orchestrate_module(
        db=db, student=student, course=course, module=module,
        memory_store=store,
    )
    assert result["module_id"] == "mod-1"

    records = store.query(
        student_id="stu-1",
        memory_type=NARRATIVE_MEMORY_TYPE,
    )
    assert len(records) >= 2


@pytest.mark.asyncio
async def test_pedagogical_orchestrator_publishes_narrative(db):
    from app.services.pedagogical_orchestration_service import (
        pedagogical_orchestration_service,
    )
    from app.schemas.pedagogy import WeeklyPedagogicalPlanCreate
    from app.models.course import Course
    from app.models.user import User, UserRole

    store = memory_store_from_session(db)
    teacher = User(id="tea-1", email="tea@test.com", hashed_password="x", first_name="Teacher", last_name="Test", role=UserRole.DOCENTE, is_active=True)
    db.add(teacher)
    course = Course(id="c-1", name="Curso Test", teacher_id="tea-1", code="PED-01", cycle=1, year=2026)
    db.add(course)
    db.flush()

    data = WeeklyPedagogicalPlanCreate(
        week_number=1,
        topic="Listas Enlazadas",
        objectives=["Insertar", "Buscar"],
        bloom_target=3,
        pedagogical_style="abp",
        pedagogical_intention="Guiar al estudiante en la comprension de listas enlazadas mediante ejercicios practicos progresivos",
        preferred_modality="interactive",
    )

    plan = await pedagogical_orchestration_service.generate_weekly_plan(
        db=db, course=course, teacher=teacher, data=data,
        memory_store=store,
    )
    assert plan.topic == "Listas Enlazadas"

    records = store.query(
        student_id="tea-1",
        memory_type=NARRATIVE_MEMORY_TYPE,
    )
    assert len(records) >= 2


# =============================================================================
# 8. Memory dashboard query endpoint
# =============================================================================


def test_memory_query_endpoint(client, docente_token, db):
    from app.memory.shared_memory import memory_store_from_session

    store = memory_store_from_session(db)
    store.publish_observation(
        voter_name="test", key="test:hello", value={"msg": "world"},
        student_id="stu-1", memory_type="observation",
    )
    db.commit()

    resp = client.get(
        "/api/swarm/memory?student_id=stu-1&memory_type=observation",
        headers={"Authorization": f"Bearer {docente_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] >= 1
    assert any(r["key"] == "test:hello" for r in data["records"])


# =============================================================================
# 9. Week orchestrator wires memory into ResearchAgent
# =============================================================================


@pytest.mark.asyncio
async def test_week_orchestrator_publishes_memory(db):
    from app.weekly_learning.orchestration import week_orchestrator
    from app.weekly_learning.models import CourseWeek, WeeklyPlan
    from app.models.course import Course

    store = memory_store_from_session(db)
    teacher = User(id="tea-1", email="tea@test.com", hashed_password="x", first_name="Teacher", last_name="Test", role=UserRole.DOCENTE, is_active=True)
    db.add(teacher)
    course = Course(id="c-1", name="Curso", teacher_id="tea-1", code="WEEK-01", cycle=1, year=2026)
    db.add(course)
    plan = WeeklyPlan(
        id="plan-1", course_id="c-1", teacher_id="tea-1",
        total_weeks=5, thematic_line="Test", pedagogical_intention="Test",
        bloom_progression=[2, 2, 2, 2, 2], week_themes=["T1", "T2", "T3", "T4", "T5"],
    )
    db.add(plan)
    week = CourseWeek(
        id="w-1",
        plan_id="plan-1",
        week_number=1,
        theme="Introduccion a Python",
        objectives=["Entender variables"],
        bloom_target=2,
        evaluation_criteria=["Criterio 1"],
        orchestration_status="pending",
    )
    db.add(week)

    content = await week_orchestrator.orchestrate_week(
        db=db, course=course, week=week,
        memory_store=store, student_id="tea-1",
    )
    assert content.week_id == "w-1"

    memory_ids = content.memory_ids
    if memory_ids:
        records = db.query(SharedMemoryRecord).filter(
            SharedMemoryRecord.id.in_(memory_ids)
        ).all()
        assert len(records) == len(memory_ids)

    narratives = store.query(
        memory_type=NARRATIVE_MEMORY_TYPE,
    )
    assert len(narratives) >= 2
