"""
Tests del flujo estudiantil completo.
Cubre: onboarding, diagnóstico, perfil, ruta adaptativa, evaluación.
"""

from tests.conftest import auth_header
from app.models.user import User, UserRole
from app.models.enrollment import Enrollment, EnrollmentStatus
from app.models.course import Course, CourseStatus
from app.models.learning_objective import LearningObjective
from app.core.security import get_password_hash


def _create_published_course(client, docente_token, db, code="TEST-01", cycle=1):
    cr = client.post("/api/courses", headers=auth_header(docente_token), json={
        "code": code, "name": f"Curso {code}", "cycle": cycle, "year": 2026,
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


class TestOnboarding:
    """Tests del flujo de onboarding del estudiante."""

    def test_onboarding_status_sin_ciclo(self, client, estudiante_token, estudiante_user):
        estudiante_user.current_cycle = None
        resp = client.get("/api/students/onboarding/status", headers=auth_header(estudiante_token))
        assert resp.status_code == 200
        data = resp.json()
        assert data["has_cycle"] is False
        assert data["onboarding_completed"] is False

    def test_set_cycle_exitoso(self, client, estudiante_token, estudiante_user):
        resp = client.patch(
            "/api/students/onboarding/cycle",
            headers=auth_header(estudiante_token),
            json={"cycle": 3},
        )
        assert resp.status_code == 200
        assert resp.json()["message"] == "Ciclo 3 asignado exitosamente"

    def test_onboarding_status_con_ciclo(self, client, estudiante_token, estudiante_user, db):
        estudiante_user.current_cycle = 5
        db.commit()
        resp = client.get("/api/students/onboarding/status", headers=auth_header(estudiante_token))
        assert resp.status_code == 200
        data = resp.json()
        assert data["has_cycle"] is True
        assert data["current_cycle"] == 5
        assert data["onboarding_completed"] is True

    def test_set_cycle_invalido(self, client, estudiante_token):
        resp = client.patch(
            "/api/students/onboarding/cycle",
            headers=auth_header(estudiante_token),
            json={"cycle": 0},
        )
        assert resp.status_code == 422

    def test_set_cycle_demasiado_alto(self, client, estudiante_token):
        resp = client.patch(
            "/api/students/onboarding/cycle",
            headers=auth_header(estudiante_token),
            json={"cycle": 11},
        )
        assert resp.status_code == 422


class TestAcademicSummary:
    """Tests del resumen académico del estudiante."""

    def test_academic_summary_sin_cursos(self, client, estudiante_token, estudiante_user, db):
        estudiante_user.current_cycle = 3
        db.commit()
        resp = client.get("/api/students/academic/summary", headers=auth_header(estudiante_token))
        assert resp.status_code == 200
        data = resp.json()
        assert data["current_cycle"] == 3
        assert data["total_courses"] == 0
        assert data["has_onboarded"] is True

    def test_academic_summary_con_cursos(self, client, docente_token, estudiante_token, estudiante_user, db):
        estudiante_user.current_cycle = 1
        db.commit()
        cid = _create_published_course(client, docente_token, db, "SUM-01", cycle=1)
        # Enroll student
        client.post(f"/api/courses/{cid}/enroll", headers=auth_header(docente_token),
                     json={"student_ids": [estudiante_user.id]})

        resp = client.get("/api/students/academic/summary", headers=auth_header(estudiante_token))
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_courses"] >= 1
        assert data["has_onboarded"] is True


class TestDiagnosticFlow:
    """Tests del flujo de diagnóstico del estudiante."""

    DIAGNOSTIC_ANSWERS = {
        "1": 4, "2": 3, "3": 5, "4": 4,
        "5": 3, "6": 4, "7": 2, "8": 4,
        "9": 3, "10": 5, "11": 4, "12": 3,
    }

    def test_enviar_diagnostico(self, client, docente_token, estudiante_token, estudiante_user, db):
        estudiante_user.current_cycle = 1
        db.commit()
        cid = _create_published_course(client, docente_token, db, "DIA-01", cycle=1)
        client.post(f"/api/courses/{cid}/enroll", headers=auth_header(docente_token),
                     json={"student_ids": [estudiante_user.id]})

        resp = client.post(
            f"/api/students/diagnostic/{cid}",
            headers=auth_header(estudiante_token),
            json={"answers": self.DIAGNOSTIC_ANSWERS},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["course_id"] == cid
        assert data["dominant_modality"] is not None
        assert data["profile"] is not None

    def test_obtener_diagnostico(self, client, docente_token, estudiante_token, estudiante_user, db):
        estudiante_user.current_cycle = 1
        db.commit()
        cid = _create_published_course(client, docente_token, db, "DIA-02", cycle=1)
        client.post(f"/api/courses/{cid}/enroll", headers=auth_header(docente_token),
                     json={"student_ids": [estudiante_user.id]})
        client.post(
            f"/api/students/diagnostic/{cid}",
            headers=auth_header(estudiante_token),
            json={"answers": self.DIAGNOSTIC_ANSWERS},
        )
        resp = client.get(f"/api/students/diagnostic/{cid}", headers=auth_header(estudiante_token))
        assert resp.status_code == 200
        assert resp.json()["course_id"] == cid

    def test_diagnostico_curso_inexistente(self, client, estudiante_token, db):
        resp = client.post(
            "/api/students/diagnostic/00000000-0000-0000-0000-000000000000",
            headers=auth_header(estudiante_token),
            json={"answers": self.DIAGNOSTIC_ANSWERS},
        )
        assert resp.status_code in (404, 500)

    def test_diagnostico_sin_curso(self, client, estudiante_token, db):
        resp = client.get(
            "/api/students/diagnostic/fake-id-123",
            headers=auth_header(estudiante_token),
        )
        assert resp.status_code == 404


class TestLearningPathFlow:
    """Tests del flujo de ruta de aprendizaje."""

    DIAGNOSTIC_ANSWERS = {
        "1": 4, "2": 3, "3": 5, "4": 4,
        "5": 3, "6": 4, "7": 2, "8": 4,
        "9": 3, "10": 5, "11": 4, "12": 3,
    }

    def _setup(self, client, docente_token, estudiante_token, estudiante_user, db, code="PATH-01"):
        estudiante_user.current_cycle = 1
        db.commit()
        cid = _create_published_course(client, docente_token, db, code, cycle=1)
        client.post(f"/api/courses/{cid}/enroll", headers=auth_header(docente_token),
                     json={"student_ids": [estudiante_user.id]})
        client.post(
            f"/api/students/diagnostic/{cid}",
            headers=auth_header(estudiante_token),
            json={"answers": self.DIAGNOSTIC_ANSWERS},
        )
        return cid

    def test_generar_ruta(self, client, docente_token, estudiante_token, estudiante_user, db):
        cid = self._setup(client, docente_token, estudiante_token, estudiante_user, db, "PATH-01")
        resp = client.post(
            f"/api/students/learning-path/{cid}",
            headers=auth_header(estudiante_token),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "active"
        assert data["total_modules"] >= 1

    def test_obtener_ruta(self, client, docente_token, estudiante_token, estudiante_user, db):
        cid = self._setup(client, docente_token, estudiante_token, estudiante_user, db, "PATH-02")
        client.post(f"/api/students/learning-path/{cid}", headers=auth_header(estudiante_token))
        resp = client.get(f"/api/students/learning-path/{cid}", headers=auth_header(estudiante_token))
        assert resp.status_code == 200
        data = resp.json()
        assert data["course_id"] == cid
        assert len(data["items"]) >= 1

    def test_ruta_sin_diagnostico(self, client, estudiante_token, db):
        resp = client.post(
            "/api/students/learning-path/no-diagnostic",
            headers=auth_header(estudiante_token),
        )
        assert resp.status_code == 400
        assert "diagnóstico" in resp.json()["detail"]

    def test_generar_ruta_dos_veces(self, client, docente_token, estudiante_token, estudiante_user, db):
        cid = self._setup(client, docente_token, estudiante_token, estudiante_user, db, "PATH-03")
        client.post(f"/api/students/learning-path/{cid}", headers=auth_header(estudiante_token))
        resp = client.post(f"/api/students/learning-path/{cid}", headers=auth_header(estudiante_token))
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "active"


class TestMyCourses:
    """Tests del endpoint my-courses."""

    def test_my_courses_sin_ciclo(self, client, estudiante_token, estudiante_user, db):
        estudiante_user.current_cycle = None
        db.commit()
        resp = client.get("/api/students/my-courses", headers=auth_header(estudiante_token))
        assert resp.status_code == 200
        assert resp.json() == []

    def test_my_courses_con_ciclo_sin_cursos(self, client, estudiante_token, estudiante_user, db):
        estudiante_user.current_cycle = 99
        db.commit()
        resp = client.get("/api/students/my-courses", headers=auth_header(estudiante_token))
        assert resp.status_code == 200
        assert resp.json() == []

    def test_my_courses_con_inscripcion(self, client, docente_token, estudiante_token, estudiante_user, db):
        estudiante_user.current_cycle = 1
        db.commit()
        cid = _create_published_course(client, docente_token, db, "MYC-01", cycle=1)
        client.post(f"/api/courses/{cid}/enroll", headers=auth_header(docente_token),
                     json={"student_ids": [estudiante_user.id]})

        resp = client.get("/api/students/my-courses", headers=auth_header(estudiante_token))
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1
        assert data[0]["course_id"] == cid
        assert data[0]["has_diagnostic"] is False


class TestAgentEndpoints:
    """Tests de los endpoints de agentes IA."""

    def test_analyze_diagnostic(self, client, docente_token, estudiante_token, estudiante_user, db):
        estudiante_user.current_cycle = 1
        db.commit()
        cid = _create_published_course(client, docente_token, db, "AGT-01", cycle=1)
        client.post(f"/api/courses/{cid}/enroll", headers=auth_header(docente_token),
                     json={"student_ids": [estudiante_user.id]})

        resp = client.post(
            f"/api/agents/analyze-diagnostic",
            headers=auth_header(estudiante_token),
            json={
                "answers": {"1": 4, "2": 3, "3": 5},
                "course_id": cid,
                "objectives": [],
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "learning_profile" in data
        assert "recommendations" in data

    def test_analyze_diagnostic_sin_datos(self, client, estudiante_token):
        resp = client.post(
            "/api/agents/analyze-diagnostic",
            headers=auth_header(estudiante_token),
            json={"answers": {}, "course_id": ""},
        )
        assert resp.status_code == 400
