"""Fase de cierre del producto (jul 2026) — bug real encontrado en la
verificación de preparación experimental: el flujo continuo de ciclos
(ModuleExperienceView) nunca abría un LearningSession, así que
"¿se registra el tiempo?" respondía NO para el 100% del flujo real
(confirmado por consulta directa: 0 LearningSession para un estudiante
con 2 misiones reales completadas). record_completed_session() cierra
ese hueco usando la duración real que el cliente midió.
"""

from __future__ import annotations

from app.models.course import Course
from app.models.learning_session import LearningSession
from app.models.student_progress import LearningPath, PathModule
from app.models.user import User, UserRole
from app.services import active_mission_service


def _seed(db):
    student = User(
        id="estudiante-tiempo-real", email="tiempo@upao.edu.pe", hashed_password="x",
        first_name="Tiempo", last_name="Real", role=UserRole.ESTUDIANTE,
    )
    course = Course(id="curso-tiempo-real", code="IS301", name="Fundamentos", cycle=3, year=2026)
    path = LearningPath(id="ruta-tiempo-real", student_id=student.id, course_id=course.id)
    module = PathModule(id="modulo-tiempo-real", path_id=path.id, title="Fundamentos de Python", order=1)
    db.add_all([student, course, path, module])
    db.commit()
    return student, course, module


def test_record_completed_session_crea_una_sesion_con_la_duracion_real(db):
    student, course, module = _seed(db)

    assert db.query(LearningSession).filter(LearningSession.student_id == student.id).count() == 0

    active_mission_service.record_completed_session(db, student, course.id, module.id, 12.5)

    sessions = db.query(LearningSession).filter(LearningSession.student_id == student.id).all()
    assert len(sessions) == 1
    assert sessions[0].status == "completed"
    assert sessions[0].duration_minutes == 12.5
    assert sessions[0].ended_at is not None


def test_record_completed_session_es_best_effort_sin_duracion(db):
    """Sin duration_minutes (petición antigua, o 0) no se fabrica un tiempo —
    nunca se inventa evidencia de investigación."""
    student, course, module = _seed(db)

    active_mission_service.record_completed_session(db, student, course.id, module.id, None)
    active_mission_service.record_completed_session(db, student, course.id, module.id, 0)

    assert db.query(LearningSession).filter(LearningSession.student_id == student.id).count() == 0


def test_record_completed_session_no_duplica_si_ya_hay_mision_con_snapshot(db):
    """Cuando el flujo legacy (con snapshot) ya abrió y cerró su propia
    LearningSession, esta función no debe crear una segunda."""
    student, course, module = _seed(db)
    db.add(LearningSession(
        student_id=student.id, course_id=course.id, module_id=module.id, status="completed",
    ))
    db.commit()

    active_mission_service.record_completed_session(db, student, course.id, module.id, 8.0)

    assert db.query(LearningSession).filter(LearningSession.student_id == student.id).count() == 1
