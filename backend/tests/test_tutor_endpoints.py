"""
Tests de integración para los endpoints del tutor inteligente.
"""

import json
from tests.conftest import auth_header


class TestTutorChat:
    def test_chat_returns_response(self, client, estudiante_token, db):
        resp = client.post("/api/tutor/chat", headers=auth_header(estudiante_token), json={
            "message": "¿Qué es un algoritmo?",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "response" in data
        assert "context" in data

    def test_chat_requires_auth(self, client):
        resp = client.post("/api/tutor/chat", json={"message": "hola"})
        assert resp.status_code == 401

    def test_chat_with_course_id(self, client, estudiante_token, estudiante_user, docente_token, db):
        from app.models.course import Course, CourseStatus
        from app.models.learning_objective import LearningObjective
        from app.models.enrollment import Enrollment, EnrollmentStatus
        cr = client.post("/api/courses", headers=auth_header(docente_token), json={
            "code": "TUT-CRS", "name": "Tutor Course", "cycle": 1, "year": 2026,
        })
        cid = cr.json()["id"]
        obj = LearningObjective(course_id=cid, title="Obj 1", bloom_level=1, order=0)
        db.add(obj)
        db.commit()
        client.post(f"/api/courses/{cid}/publish", headers=auth_header(docente_token))
        enroll = Enrollment(student_id=estudiante_user.id,
                            course_id=cid, status=EnrollmentStatus.ACTIVO)
        db.add(enroll)
        db.commit()

        resp = client.post("/api/tutor/chat", headers=auth_header(estudiante_token), json={
            "message": "¿Qué veremos en este curso?",
            "course_id": cid,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "response" in data


class TestTutorMemory:
    def test_get_memory_empty(self, client, estudiante_token):
        resp = client.get("/api/tutor/memory", headers=auth_header(estudiante_token))
        assert resp.status_code == 200
        data = resp.json()
        assert "weaknesses" in data
        assert "strengths" in data
        assert "persistent_memories" in data
        assert "recent_conversations" in data

    def test_get_memory_after_chat(self, client, estudiante_token):
        client.post("/api/tutor/chat", headers=auth_header(estudiante_token), json={
            "message": "Dime algo",
        })
        resp = client.get("/api/tutor/memory", headers=auth_header(estudiante_token))
        data = resp.json()
        assert len(data["recent_conversations"]) >= 2


class TestTutorHistory:
    def test_history_empty(self, client, estudiante_token):
        resp = client.get("/api/tutor/history", headers=auth_header(estudiante_token))
        assert resp.status_code == 200
        assert resp.json() == []

    def test_history_after_messages(self, client, estudiante_token):
        client.post("/api/tutor/chat", headers=auth_header(estudiante_token), json={
            "message": "Hola",
        })
        resp = client.get("/api/tutor/history", headers=auth_header(estudiante_token))
        data = resp.json()
        assert len(data) >= 2


class TestTutorExplain:
    def test_explain_topic(self, client, estudiante_token):
        resp = client.post("/api/tutor/explain", headers=auth_header(estudiante_token), json={
            "topic": "recursion",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "chunks" in data
        assert data["title"] == "recursion"

    def test_explain_empty_topic(self, client, estudiante_token):
        resp = client.post("/api/tutor/explain", headers=auth_header(estudiante_token), json={
            "topic": "",
        })
        assert resp.status_code == 400

    def test_explain_algorithm_quicksort(self, client, estudiante_token):
        resp = client.get("/api/tutor/explain/algorithm/quicksort",
                          headers=auth_header(estudiante_token))
        assert resp.status_code == 200
        data = resp.json()
        assert "Quicksort" in data["title"]

    def test_explain_algorithm_binary_search(self, client, estudiante_token):
        resp = client.get("/api/tutor/explain/algorithm/binary_search",
                          headers=auth_header(estudiante_token))
        assert resp.status_code == 200
        assert "Búsqueda Binaria" in resp.json()["title"]

    def test_explain_algorithm_not_found(self, client, estudiante_token):
        resp = client.get("/api/tutor/explain/algorithm/unknown",
                          headers=auth_header(estudiante_token))
        assert resp.status_code == 404


class TestTutorReplan:
    def test_replan_returns_structure(self, client, estudiante_token):
        resp = client.get("/api/tutor/replan", headers=auth_header(estudiante_token))
        assert resp.status_code == 200
        data = resp.json()
        assert "unlocks" in data
        assert "recommendation" in data
        assert "weak_areas" in data["recommendation"]

    def test_replan_requires_auth(self, client):
        resp = client.get("/api/tutor/replan")
        assert resp.status_code == 401


class TestTutorModuleComplete:
    def test_module_not_found(self, client, estudiante_token):
        resp = client.post("/api/tutor/module/non-existent-id/complete",
                           headers=auth_header(estudiante_token), json={"score": 0.8})
        assert resp.status_code == 200
        assert "error" in resp.json()


class TestTutorKnowledgeGraph:
    def test_knowledge_graph_returns_structure(self, client, estudiante_token):
        resp = client.get("/api/tutor/knowledge-graph",
                          headers=auth_header(estudiante_token))
        assert resp.status_code == 200
        data = resp.json()
        assert "nodes" in data
        assert "edges" in data

    def test_knowledge_graph_requires_auth(self, client):
        resp = client.get("/api/tutor/knowledge-graph")
        assert resp.status_code == 401
