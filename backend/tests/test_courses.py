"""
Tests de CRUD de cursos.
Cubre: crear, listar, actualizar, publicar (con/sin objetivos), inscribir.
"""

from tests.conftest import auth_header
from app.models.learning_objective import LearningObjective


class TestCourseCRUD:
    """Tests CRUD de cursos."""

    def _create_course(self, client, token):
        return client.post("/api/courses", headers=auth_header(token), json={
            "code": "IS-101", "name": "Intro a IS", "cycle": 1, "year": 2026,
            "description": "Curso de introducción",
        })

    def test_crear_curso(self, client, docente_token):
        resp = self._create_course(client, docente_token)
        assert resp.status_code == 201
        assert resp.json()["code"] == "IS-101"
        assert resp.json()["status"] == "borrador"

    def test_listar_cursos(self, client, docente_token):
        self._create_course(client, docente_token)
        resp = client.get("/api/courses", headers=auth_header(docente_token))
        assert resp.status_code == 200
        assert resp.json()["total"] >= 1

    def test_obtener_curso(self, client, docente_token):
        cr = self._create_course(client, docente_token)
        cid = cr.json()["id"]
        resp = client.get(f"/api/courses/{cid}", headers=auth_header(docente_token))
        assert resp.status_code == 200

    def test_actualizar_curso(self, client, docente_token):
        cr = self._create_course(client, docente_token)
        cid = cr.json()["id"]
        resp = client.put(f"/api/courses/{cid}", headers=auth_header(docente_token), json={
            "name": "Curso Actualizado",
        })
        assert resp.status_code == 200
        assert resp.json()["name"] == "Curso Actualizado"

    def test_archivar_curso(self, client, docente_token):
        cr = self._create_course(client, docente_token)
        cid = cr.json()["id"]
        resp = client.delete(f"/api/courses/{cid}", headers=auth_header(docente_token))
        assert resp.status_code == 200
        assert resp.json()["status"] == "archivado"


class TestPublishCourse:
    """Tests de publicación de curso."""

    def test_publicar_sin_objetivos_falla(self, client, docente_token):
        cr = client.post("/api/courses", headers=auth_header(docente_token), json={
            "code": "PUB-01", "name": "Test Pub", "cycle": 1, "year": 2026,
        })
        cid = cr.json()["id"]
        resp = client.post(f"/api/courses/{cid}/publish", headers=auth_header(docente_token))
        assert resp.status_code == 400
        assert "3 objetivos" in resp.json()["detail"]

    def test_publicar_con_3_objetivos(self, client, docente_token, db):
        cr = client.post("/api/courses", headers=auth_header(docente_token), json={
            "code": "PUB-02", "name": "Test Pub OK", "cycle": 1, "year": 2026,
        })
        cid = cr.json()["id"]

        # Crear 3 objetivos directamente en BD
        for i in range(3):
            obj = LearningObjective(
                course_id=cid, title=f"Objetivo {i+1}", bloom_level=i+1, order=i,
            )
            db.add(obj)
        db.commit()

        resp = client.post(f"/api/courses/{cid}/publish", headers=auth_header(docente_token))
        assert resp.status_code == 200
        assert "publicado" in resp.json()["message"].lower()


class TestEnrollment:
    """Tests de inscripción de estudiantes."""

    def _create_published_course(self, client, docente_token, db, code):
        cr = client.post("/api/courses", headers=auth_header(docente_token), json={
            "code": code, "name": "Curso Enroll", "cycle": 1, "year": 2026,
        })
        cid = cr.json()["id"]
        for i in range(3):
            obj = LearningObjective(
                course_id=cid, title=f"Obj {i+1}", bloom_level=i+1, order=i,
            )
            db.add(obj)
        db.commit()
        client.post(f"/api/courses/{cid}/publish", headers=auth_header(docente_token))
        return cid

    def test_inscribir_estudiantes(self, client, docente_token, estudiante_user, db):
        cid = self._create_published_course(client, docente_token, db, "ENR-01")

        resp = client.post(
            f"/api/courses/{cid}/enroll",
            headers=auth_header(docente_token),
            json={"student_ids": [estudiante_user.id]},
        )
        assert resp.status_code == 200
        assert resp.json()["success"] == 1

    def test_inscribir_estudiante_duplicado(self, client, docente_token, estudiante_user, db):
        cid = self._create_published_course(client, docente_token, db, "ENR-02")

        # Primera inscripción
        client.post(f"/api/courses/{cid}/enroll", headers=auth_header(docente_token),
                     json={"student_ids": [estudiante_user.id]})
        # Segunda inscripción (duplicada)
        resp = client.post(f"/api/courses/{cid}/enroll", headers=auth_header(docente_token),
                           json={"student_ids": [estudiante_user.id]})
        assert resp.json()["errors"][0]["message"] == "Ya está inscrito en este curso"
