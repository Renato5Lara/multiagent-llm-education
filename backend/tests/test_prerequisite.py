"""
Tests para prerrequisitos curriculares, control de acceso y analítica IA.
"""

from tests.conftest import auth_header
from app.models.course import Course, CourseStatus
from app.models.enrollment import Enrollment, EnrollmentStatus
from app.models.learning_objective import LearningObjective
from app.models.institutional_course import InstitutionalCourse, InstitutionalCoursePrerequisite
from app.models.student_progress import StudentProgress
from app.models.resource import Resource


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


class TestCourseAccess:
    """Tests para verificación de acceso a cursos por prerrequisitos."""

    def test_course_access_unlocked(self, client, docente_token, estudiante_token, estudiante_user, db):
        estudiante_user.current_cycle = 1
        db.commit()
        cid = _create_published_course(client, docente_token, db, "ACC-01", cycle=1)

        resp = client.get(f"/api/analytics/course-access/{cid}", headers=auth_header(estudiante_token))
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_unlocked"] is True
        assert data["course_id"] == cid

    def test_course_access_not_found(self, client, estudiante_token):
        resp = client.get("/api/analytics/course-access/00000000-0000-0000-0000-000000000000",
                          headers=auth_header(estudiante_token))
        assert resp.status_code == 404

    def test_curriculum_status_returns_list(self, client, docente_token, estudiante_token, estudiante_user, db):
        estudiante_user.current_cycle = 1
        db.commit()
        _create_published_course(client, docente_token, db, "CUR-01", cycle=1)

        resp = client.get("/api/analytics/curriculum-status", headers=auth_header(estudiante_token))
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    def test_risk_prediction_returns_risk(self, client, estudiante_token, estudiante_user, db):
        estudiante_user.current_cycle = 1
        db.commit()

        resp = client.get("/api/analytics/risk-prediction", headers=auth_header(estudiante_token))
        assert resp.status_code == 200
        data = resp.json()
        assert "risk_level" in data
        assert data["risk_level"] in ("bajo", "medio", "alto")
        assert "risk_score" in data


class TestIADashboard:
    """Tests para el dashboard IA del estudiante."""

    def test_ia_dashboard_estudiante(self, client, estudiante_token, estudiante_user, db):
        estudiante_user.current_cycle = 1
        db.commit()

        resp = client.get("/api/analytics/dashboard", headers=auth_header(estudiante_token))
        assert resp.status_code == 200
        data = resp.json()
        assert "student_risk" in data
        assert "curriculum_status" in data
        assert "strengths" in data
        assert "warnings" in data
        assert "stats" in data

    def test_ia_dashboard_docente(self, client, docente_token, db):
        resp = client.get("/api/analytics/dashboard", headers=auth_header(docente_token))
        assert resp.status_code == 200
        data = resp.json()
        assert "course_analytics" in data
        assert "total_students" in data

    def test_ia_dashboard_with_enrollments(self, client, docente_token, estudiante_token, estudiante_user, db):
        estudiante_user.current_cycle = 1
        db.commit()
        cid = _create_published_course(client, docente_token, db, "DIA-01", cycle=1)
        client.post(f"/api/courses/{cid}/enroll", headers=auth_header(docente_token),
                     json={"student_ids": [estudiante_user.id]})

        resp = client.get("/api/analytics/dashboard", headers=auth_header(estudiante_token))
        assert resp.status_code == 200
        data = resp.json()
        assert data["stats"]["enrolled"] >= 1

    def test_docente_analytics_shows_courses(self, client, docente_token, db):
        _create_published_course(client, docente_token, db, "DOC-ANA-01", cycle=1)

        resp = client.get("/api/analytics/dashboard", headers=auth_header(docente_token))
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["course_analytics"]) >= 1
        assert data["course_analytics"][0]["course_name"] == "Curso DOC-ANA-01"


class TestCoursePrerequisiteModel:
    """Tests para el modelo CoursePrerequisite."""

    def test_create_prerequisite(self, client, docente_token, db):
        cr1 = client.post("/api/courses", headers=auth_header(docente_token), json={
            "code": "PRE-01", "name": "Curso Base", "cycle": 1, "year": 2026,
        })
        cr2 = client.post("/api/courses", headers=auth_header(docente_token), json={
            "code": "PRE-02", "name": "Curso Avanzado", "cycle": 2, "year": 2026,
        })
        cid1 = cr1.json()["id"]
        cid2 = cr2.json()["id"]

        from app.models.course_prerequisite import CoursePrerequisite
        prereq = CoursePrerequisite(
            course_id=cid2,
            prerequisite_course_id=cid1,
        )
        db.add(prereq)
        db.commit()

        stored = db.query(CoursePrerequisite).filter(
            CoursePrerequisite.course_id == cid2
        ).first()
        assert stored is not None
        assert stored.prerequisite_course_id == cid1


class TestRiskAnalyzerAgent:
    """Tests para el agente analizador de riesgo."""

    def test_risk_analyzer_node(self):
        from app.agents.nodes import risk_analyzer

        state = {
            "risk_data": {
                "progress_rate": 0.8,
                "completion_rate": 0.6,
                "diagnostic_rate": 1.0,
                "prerequisite_gaps": [],
            }
        }
        result = risk_analyzer(state)
        assert "risk_prediction" in result
        assert result["risk_prediction"]["risk_level"] == "bajo"

    def test_risk_analyzer_high_risk(self):
        from app.agents.nodes import risk_analyzer

        state = {
            "risk_data": {
                "progress_rate": 0.1,
                "completion_rate": 0.0,
                "diagnostic_rate": 0.2,
                "prerequisite_gaps": ["MAT-101"],
            }
        }
        result = risk_analyzer(state)
        assert result["risk_prediction"]["risk_level"] == "alto"
        assert len(result["risk_prediction"]["factors"]) >= 1

    def test_path_planner_with_prerequisites(self):
        from app.agents.nodes import path_planner
        from app.agents.schemas import LearningProfile

        state = {
            "learning_profile": LearningProfile(
                learning_style="visual",
                pace="moderate",
                collaboration="mixed",
                motivation="challenge",
                preferred_bloom_levels=[3, 4, 5],
                preferred_modalities=["video", "reading"],
            ).model_dump(),
            "course_objectives": [],
            "prerequisites_completed": [],
        }
        result = path_planner(state)
        assert "learning_path_plan" in result


class TestInstitutionalPrerequisiteResolution:
    """Tests para la resolución de prerrequisitos institucionales."""

    def test_prerequisite_resolution_service(self, db):
        from app.services.prerequisite_service import get_institutional_prerequisite_codes

        inst_course = InstitutionalCourse(
            code="TEST-ADV", name="Avanzado", credits=4, cycle=3,
        )
        db.add(inst_course)
        db.flush()

        inst_base = InstitutionalCourse(
            code="TEST-BASE", name="Base", credits=4, cycle=2,
        )
        db.add(inst_base)
        db.flush()

        link = InstitutionalCoursePrerequisite(
            course_id=inst_course.id,
            prerequisite_id=inst_base.id,
        )
        db.add(link)
        db.commit()

        course = Course(
            code="INST-TEST", name="Curso Test", cycle=3, year=2026,
            institutional_course_id=inst_course.id,
            is_institutional=True,
        )
        db.add(course)
        db.commit()

        codes = get_institutional_prerequisite_codes(db, course)
        assert "TEST-BASE" in codes
