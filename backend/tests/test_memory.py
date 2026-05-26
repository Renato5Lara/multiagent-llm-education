"""
Tests para el servicio de memoria académica persistente.

NOTA: Los tests de escritura usan test_uow en lugar de db
porque los servicios refactorizados ahora reciben UnitOfWork.
Cada test hace commit explícito para persistir y verificar.
"""

from app.models.user import User
from app.models.course import Course
from app.services.memory_service import (
    store_memory,
    get_memory,
    get_all_memories,
    save_conversation_message,
    get_conversation_history,
    track_weakness,
    track_strength,
    get_active_weaknesses,
    get_strengths,
    build_tutor_context,
    get_memory_summary,
)


class TestStoreMemory:
    def test_store_new_memory(self, test_uow, estudiante_user):
        store_memory(test_uow, estudiante_user.id, "preference", "modality", "visual")
        test_uow.commit()
        mem = get_memory(test_uow.db, estudiante_user.id, "preference", "modality")
        assert mem is not None
        assert mem.value == "visual"

    def test_store_memory_with_score(self, test_uow, estudiante_user):
        store_memory(test_uow, estudiante_user.id, "competency", "python", "intermedio", score=0.75)
        test_uow.commit()
        mem = get_memory(test_uow.db, estudiante_user.id, "competency", "python")
        assert mem.score == 0.75
        assert mem.memory_type == "competency"

    def test_store_memory_upsert(self, test_uow, estudiante_user):
        store_memory(test_uow, estudiante_user.id, "preference", "pace", "slow")
        store_memory(test_uow, estudiante_user.id, "preference", "pace", "fast")
        test_uow.commit()
        mems = get_all_memories(test_uow.db, estudiante_user.id, "preference")
        assert len(mems) == 1
        assert mems[0].value == "fast"

    def test_get_all_memories_by_type(self, test_uow, estudiante_user):
        store_memory(test_uow, estudiante_user.id, "preference", "a", "x")
        store_memory(test_uow, estudiante_user.id, "competency", "b", "y")
        test_uow.commit()
        prefs = get_all_memories(test_uow.db, estudiante_user.id, "preference")
        comps = get_all_memories(test_uow.db, estudiante_user.id, "competency")
        assert len(prefs) == 1
        assert len(comps) == 1


class TestConversationMessages:
    def test_save_and_retrieve_messages(self, test_uow, estudiante_user):
        save_conversation_message(test_uow, estudiante_user.id, None, "user", "Hola")
        save_conversation_message(test_uow, estudiante_user.id, None, "assistant", "Hola, soy tu tutor")
        test_uow.commit()
        history = get_conversation_history(test_uow.db, estudiante_user.id)
        assert len(history) == 2
        assert history[0].role == "assistant"
        assert history[1].role == "user"

    def test_messages_with_course_filter(self, test_uow, estudiante_user, docente_token, client):
        cr = client.post("/api/courses", headers={"Authorization": f"Bearer {docente_token}"}, json={
            "code": "MEM-CRS", "name": "Memory Course", "cycle": 1, "year": 2026,
        })
        cid = cr.json()["id"]
        save_conversation_message(test_uow, estudiante_user.id, cid, "user", "Duda del curso")
        save_conversation_message(test_uow, estudiante_user.id, None, "user", "Duda general")
        test_uow.commit()
        filtered = get_conversation_history(test_uow.db, estudiante_user.id, course_id=cid)
        assert len(filtered) == 1
        assert filtered[0].content == "Duda del curso"

    def test_message_limit(self, test_uow, estudiante_user):
        for i in range(5):
            save_conversation_message(test_uow, estudiante_user.id, None, "user", f"msg {i}")
        test_uow.commit()
        history = get_conversation_history(test_uow.db, estudiante_user.id, limit=2)
        assert len(history) == 2


class TestWeaknessTracking:
    def test_track_new_weakness(self, test_uow, estudiante_user):
        track_weakness(test_uow, estudiante_user.id, "recursion", "Dificultad con casos base", bloom_level=2)
        test_uow.commit()
        weaknesses = get_active_weaknesses(test_uow.db, estudiante_user.id)
        assert len(weaknesses) == 1
        assert weaknesses[0].topic == "recursion"
        assert weaknesses[0].detection_count == 1

    def test_track_weakness_increments_count(self, test_uow, estudiante_user):
        track_weakness(test_uow, estudiante_user.id, "recursion", "Dificultad con casos base")
        track_weakness(test_uow, estudiante_user.id, "recursion", "Dificultad con casos base")
        test_uow.commit()
        weaknesses = get_active_weaknesses(test_uow.db, estudiante_user.id)
        assert len(weaknesses) == 1
        assert weaknesses[0].detection_count >= 2

    def test_resolved_weakness_allows_new(self, test_uow, estudiante_user):
        from app.models.student_memory import WeaknessRecord
        track_weakness(test_uow, estudiante_user.id, "recursion", "test")
        test_uow.commit()
        existing = test_uow.db.query(WeaknessRecord).first()
        existing.resolved = True
        test_uow.db.commit()
        track_weakness(test_uow, estudiante_user.id, "recursion", "new instance")
        test_uow.commit()
        weaknesses = get_active_weaknesses(test_uow.db, estudiante_user.id)
        assert len(weaknesses) == 1
        assert weaknesses[0].detection_count == 1


class TestStrengthTracking:
    def test_track_new_strength(self, test_uow, estudiante_user):
        track_strength(test_uow, estudiante_user.id, "python", "Buen manejo de listas", bloom_level=3)
        test_uow.commit()
        strengths = get_strengths(test_uow.db, estudiante_user.id)
        assert len(strengths) == 1
        assert strengths[0].topic == "python"

    def test_track_strength_dedup(self, test_uow, estudiante_user):
        track_strength(test_uow, estudiante_user.id, "python", "first")
        track_strength(test_uow, estudiante_user.id, "python", "second")
        test_uow.commit()
        strengths = get_strengths(test_uow.db, estudiante_user.id)
        assert len(strengths) == 1


class TestBuildTutorContext:
    def test_basic_context(self, db, estudiante_user):
        context = build_tutor_context(db, estudiante_user)
        assert context["student_name"] == "María"
        assert context["weaknesses"] == []
        assert context["strengths"] == []
        assert context["conversation_history"] == []
        assert context["course_context"] is None

    def test_context_with_weaknesses(self, test_uow, estudiante_user):
        track_weakness(test_uow, estudiante_user.id, "sorting", "Dificultad con algoritmos", bloom_level=2)
        test_uow.commit()
        context = build_tutor_context(test_uow.db, estudiante_user)
        assert len(context["weaknesses"]) == 1
        assert context["weaknesses"][0]["topic"] == "sorting"

    def test_context_with_course(self, db, estudiante_user, docente_token, client):
        cr = client.post("/api/courses", headers={"Authorization": f"Bearer {docente_token}"}, json={
            "code": "CTX-CRS", "name": "Context Course", "cycle": 1, "year": 2026,
        })
        cid = cr.json()["id"]
        context = build_tutor_context(db, estudiante_user, course_id=cid)
        assert context["course_context"] is not None
        assert context["course_context"]["course_name"] == "Context Course"


class TestMemorySummary:
    def test_empty_summary(self, db, estudiante_user):
        summary = get_memory_summary(db, estudiante_user.id)
        assert summary["weaknesses"] == []
        assert summary["strengths"] == []
        assert summary["persistent_memories"] == {}

    def test_summary_with_data(self, test_uow, estudiante_user):
        store_memory(test_uow, estudiante_user.id, "competency", "python", "dominado", score=0.9)
        track_weakness(test_uow, estudiante_user.id, "recursion", "test")
        track_strength(test_uow, estudiante_user.id, "python", "test")
        test_uow.commit()
        summary = get_memory_summary(test_uow.db, estudiante_user.id)
        assert len(summary["weaknesses"]) == 1
        assert len(summary["strengths"]) == 1
        assert "python" in summary["persistent_memories"]
