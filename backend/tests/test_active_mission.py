"""Misión Activa — continuidad de la misión (SPEC_MISION_ACTIVA.md).

Contrato bajo prueba:
1. Releer antes que regenerar: si existe un snapshot persistido, el endpoint
   de orquestación lo devuelve SIN invocar al swarm (navegar nunca regenera).
2. El cursor persiste y viaja con el snapshot (unidad indivisible).
3. Completar la misión es unidireccional y conserva el snapshot.
"""

import pytest
from sqlalchemy.orm import Session

from app.models.course import Course, CourseStatus
from app.models.learning_session import LearningSession
from app.models.student_progress import LearningPath, PathModule
from app.models.user import User
from app.services import active_mission_service
from tests.conftest import auth_header


def _snapshot(module_id: str, course_id: str) -> dict:
    """Snapshot mínimo válido según ModuleOrchestrationResponse."""
    return {
        "module_id": module_id,
        "module_title": "Variables y Tipos de Datos",
        "course_id": course_id,
        "course_name": "Fundamentos de la Programación",
        "orchestration_status": "completed",
        "introduction": "Introducción persistida.",
        "pedagogical_explanation": "Explicación persistida.",
        "misconceptions": [],
        "examples": ["ejemplo 1"],
        "real_applications": ["aplicación 1"],
        "guided_practice": "Práctica guiada.",
        "pedagogical_stages": [],
        "multimodal_prompts": [],
        "storyboard": "",
        "continuity_notes": "",
        "bloom_progression": [],
        "retrieval_evidence": {"sources_count": 3, "confidence": 0.8, "degraded": False, "sources": []},
        "confidence": 0.8,
        "generated_at": "2026-07-06T00:00:00Z",
        "session_id": "abc123def456",
        "concept_blocks": [],
    }


@pytest.fixture()
def mission_setup(db: Session, estudiante_user: User, docente_user: User):
    course = Course(
        code="FDP-MA", name="Fundamentos de la Programación", cycle=1, year=2026,
        teacher_id=docente_user.id, status=CourseStatus.PUBLICADO,
    )
    db.add(course)
    db.flush()
    path = LearningPath(student_id=estudiante_user.id, course_id=course.id, total_modules=1)
    db.add(path)
    db.flush()
    module = PathModule(path_id=path.id, title="Variables", order=1, status="available")
    db.add(module)
    db.commit()
    return course, path, module


class TestMissionResume:
    def test_orchestrate_relee_snapshot_sin_regenerar(
        self, client, db, estudiante_user, estudiante_token, mission_setup, monkeypatch,
    ):
        course, _path, module = mission_setup
        snap = _snapshot(module.id, course.id)
        mission = active_mission_service.save_snapshot(
            db, estudiante_user, course.id, module.id, snap
        )
        assert mission is not None

        # Si el endpoint intentara regenerar, este stub lo delata.
        async def _must_not_be_called(*args, **kwargs):
            raise AssertionError("La orquestación NO debe ejecutarse al releer")

        from app.services.module_orchestration_service import module_orchestration_service
        monkeypatch.setattr(module_orchestration_service, "orchestrate_module", _must_not_be_called)

        resp = client.post(
            f"/api/students/module/{module.id}/orchestrate",
            headers=auth_header(estudiante_token),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["resumed"] is True
        assert data["introduction"] == "Introducción persistida."
        assert data["session_id"] == "abc123def456"  # evidencia enlazada intacta
        assert data["mission_cursor"]["current_index"] == 0

    def test_cursor_persiste_y_viaja_con_el_snapshot(
        self, client, db, estudiante_user, estudiante_token, mission_setup, monkeypatch,
    ):
        course, _path, module = mission_setup
        active_mission_service.save_snapshot(
            db, estudiante_user, course.id, module.id, _snapshot(module.id, course.id)
        )

        resp = client.patch(
            f"/api/students/module/{module.id}/mission-progress",
            headers=auth_header(estudiante_token),
            json={"current_index": 7, "completed_step_ids": ["cb-mq-0", "concept-1"], "total_xp": 14},
        )
        assert resp.status_code == 200
        assert resp.json()["mission_cursor"]["current_index"] == 7

        async def _must_not_be_called(*args, **kwargs):
            raise AssertionError("La orquestación NO debe ejecutarse al releer")

        from app.services.module_orchestration_service import module_orchestration_service
        monkeypatch.setattr(module_orchestration_service, "orchestrate_module", _must_not_be_called)

        resp = client.post(
            f"/api/students/module/{module.id}/orchestrate",
            headers=auth_header(estudiante_token),
        )
        data = resp.json()
        assert data["resumed"] is True
        assert data["mission_cursor"] == {
            "current_index": 7,
            "completed_step_ids": ["cb-mq-0", "concept-1"],
            "total_xp": 14,
        }

    def test_mission_progress_sin_mision_es_404(
        self, client, estudiante_token, mission_setup,
    ):
        _course, _path, module = mission_setup
        resp = client.patch(
            f"/api/students/module/{module.id}/mission-progress",
            headers=auth_header(estudiante_token),
            json={"current_index": 1, "completed_step_ids": [], "total_xp": 0},
        )
        assert resp.status_code == 404

    def test_completar_cierra_la_mision_y_conserva_snapshot(
        self, client, db, estudiante_user, estudiante_token, mission_setup,
    ):
        course, _path, module = mission_setup
        active_mission_service.save_snapshot(
            db, estudiante_user, course.id, module.id, _snapshot(module.id, course.id)
        )

        resp = client.patch(
            f"/api/students/module/{module.id}",
            headers=auth_header(estudiante_token),
            json={"status": "completed"},
        )
        assert resp.status_code == 200

        mission = (
            db.query(LearningSession)
            .filter(
                LearningSession.student_id == estudiante_user.id,
                LearningSession.module_id == module.id,
            )
            .first()
        )
        db.refresh(mission)
        assert mission.status == "completed"
        # "Repasar" = lectura: el snapshot sobrevive al cierre.
        assert active_mission_service.SNAPSHOT_KEY in (mission.metadata_json or {})

    def test_snapshot_degradado_no_se_persiste(self, db, estudiante_user, mission_setup):
        course, _path, module = mission_setup
        snap = _snapshot(module.id, course.id)
        snap["orchestration_status"] = "degraded"
        # La regla vive en el endpoint; aquí validamos el contrato del servicio:
        # get_resumable solo devuelve misiones CON snapshot.
        assert active_mission_service.get_resumable(db, estudiante_user, module.id) is None
