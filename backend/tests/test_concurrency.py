"""
Tests de concurrencia y consistencia.

Verifica:
1. Advisory locks evitan race conditions
2. Rollback seguro bajo fallos
3. Integridad ante stress concurrente
"""

import threading
import time

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.orm.exc import StaleDataError
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.locks import advisory_lock, lock_key
from app.db.uow import UnitOfWork
from app.models.student_memory import StudentMemory


@pytest.fixture(scope="function")
def concurrent_engine(tmp_path):
    """Crea una BD SQLite archivo aislada para tests de concurrencia pura."""
    db_path = tmp_path / "test_concurrent.db"
    engine = create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False},
    )
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.close()
    Base.metadata.create_all(bind=engine)
    yield engine
    engine.dispose()


# =============================================================================
# 1. Advisory Lock Tests
# =============================================================================

class TestAdvisoryLock:
    """Verifica que advisory_lock serializa accesos."""

    def test_lock_key_unique(self):
        k1 = lock_key("memory:a:b:c")
        k2 = lock_key("memory:a:b:c")
        k3 = lock_key("memory:x:y:z")
        assert k1 == k2
        assert k1 != k3

    def test_advisory_lock_acquire_release(self, db):
        with advisory_lock(db, "test:lock:1"):
            pass
        with advisory_lock(db, "test:lock:1"):
            pass

    def test_advisory_lock_serializes(self, db):
        results = []
        lock_name = "test:serialize"

        def worker():
            with advisory_lock(db, lock_name):
                results.append("enter")
                time.sleep(0.05)
                results.append("exit")

        t1 = threading.Thread(target=worker)
        t2 = threading.Thread(target=worker)
        t1.start()
        time.sleep(0.01)
        t2.start()
        t1.join()
        t2.join()

        assert results == ["enter", "exit", "enter", "exit"], f"Got {results}"

    def test_advisory_lock_different_keys_parallel(self, db):
        results = []

        def worker1():
            with advisory_lock(db, "lock:a"):
                results.append("a1")
                time.sleep(0.05)
                results.append("a2")

        def worker2():
            with advisory_lock(db, "lock:b"):
                results.append("b1")
                time.sleep(0.05)
                results.append("b2")

        t1 = threading.Thread(target=worker1)
        t2 = threading.Thread(target=worker2)
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        assert "a1" in results
        assert "b1" in results
        assert len(results) == 4

    def test_lock_cleanup_on_exception(self, db):
        try:
            with advisory_lock(db, "except:lock"):
                raise ValueError("Simulated error")
        except ValueError:
            pass
        with advisory_lock(db, "except:lock"):
            pass

    def test_nested_locks(self, db):
        with advisory_lock(db, "outer"):
            with advisory_lock(db, "inner"):
                pass


# =============================================================================
# 3. Enroll Students Concurrency Tests
# =============================================================================

class TestEnrollStudentsConcurrency:
    """Race conditions en enroll_students."""

    def test_enroll_returns_duplicate_error(self, db, curso_publicado, estudiante_user):
        from app.services.course_service import enroll_students

        r1 = enroll_students(db, curso_publicado.id, [estudiante_user.id])
        assert r1["success"] == 1

        r2 = enroll_students(db, curso_publicado.id, [estudiante_user.id])
        assert r2["success"] == 0
        assert len(r2["errors"]) == 1
        assert "Ya está inscrito" in r2["errors"][0]["message"]

    def test_enroll_invalid_student(self, db, curso_publicado):
        from app.services.course_service import enroll_students

        result = enroll_students(db, curso_publicado.id, ["invalid-id"])
        assert result["success"] == 0
        assert "Estudiante no encontrado" in result["errors"][0]["message"]

    def test_enroll_unpublished_course(self, db, curso_publicado, estudiante_user):
        from app.services.course_service import enroll_students
        curso_publicado.status = "borrador"
        db.commit()

        result = enroll_students(db, curso_publicado.id, [estudiante_user.id])
        assert result["success"] == 0

    def test_enroll_multiple_students(self, db, curso_publicado):
        from app.services.course_service import enroll_students

        student_a = __import__('app.models.user', fromlist=['User']).User(
            email="sa@test.com", hashed_password="x", first_name="S", last_name="A",
            role=__import__('app.models.user', fromlist=['UserRole']).UserRole.ESTUDIANTE,
            is_active=True,
        )
        student_b = __import__('app.models.user', fromlist=['User']).User(
            email="sb@test.com", hashed_password="x", first_name="S", last_name="B",
            role=__import__('app.models.user', fromlist=['UserRole']).UserRole.ESTUDIANTE,
            is_active=True,
        )
        db.add_all([student_a, student_b])
        db.commit()

        result = enroll_students(db, curso_publicado.id, [student_a.id, student_b.id])
        assert result["success"] == 2


# =============================================================================
# 5. save_diagnostic Concurrency Tests
# =============================================================================

class TestSaveDiagnosticConcurrency:
    """Race conditions en save_diagnostic."""

    def test_diagnostic_save_and_retrieve(self, db, estudiante_user, curso_publicado):
        from app.services.student_service import save_diagnostic

        answers = {"1": 3, "2": 2, "3": 4}
        result = save_diagnostic(db, estudiante_user.id, curso_publicado.id, answers)
        assert result.student_id == estudiante_user.id
        assert result.course_id == curso_publicado.id

        from app.models.diagnostic_result import DiagnosticResult
        count = db.query(DiagnosticResult).filter(
            DiagnosticResult.student_id == estudiante_user.id,
            DiagnosticResult.course_id == curso_publicado.id,
        ).count()
        assert count == 1

    def test_diagnostic_returns_existing_on_duplicate(self, db, estudiante_user, curso_publicado):
        from app.services.student_service import save_diagnostic

        answers1 = {"1": 3, "2": 2, "3": 4}
        save_diagnostic(db, estudiante_user.id, curso_publicado.id, answers1)

        answers2 = {"1": 5, "2": 5, "3": 5}
        result2 = save_diagnostic(db, estudiante_user.id, curso_publicado.id, answers2)

        from app.models.diagnostic_result import DiagnosticResult
        results = db.query(DiagnosticResult).filter(
            DiagnosticResult.student_id == estudiante_user.id,
            DiagnosticResult.course_id == curso_publicado.id,
        ).all()
        assert len(results) == 1
        assert results[0].dominant_modality == result2.dominant_modality


# =============================================================================
# 6. Unit of Work + Advisory Lock Integration Tests
# =============================================================================

class TestUoWLockIntegration:
    """UoW + advisory lock trabajan juntos."""

    def test_uow_commit_releases_lock(self, db, estudiante_user):
        with advisory_lock(db, "uow:test"):
            uow = UnitOfWork(lambda: db)
            mem = StudentMemory(
                student_id=estudiante_user.id,
                memory_type="test",
                key="lock-test",
                value="value",
            )
            uow.db.add(mem)
            uow.commit()

        with advisory_lock(db, "uow:test"):
            pass

    def test_uow_rollback_releases_lock(self, db):
        with advisory_lock(db, "uow:rollback-test"):
            uow = UnitOfWork(lambda: db)
            mem = StudentMemory(
                student_id="rollback-student",
                memory_type="test",
                key="rollback-lock",
                value="value",
            )
            uow.db.add(mem)
            uow.rollback()

        with advisory_lock(db, "uow:rollback-test"):
            pass


# =============================================================================
# 7. Concurrent Thread Tests (separate sessions per thread)
# =============================================================================

class TestConcurrentThreadSafety:
    """Tests con hilos reales y sesiones separadas."""

    def _setup_base_data(self, engine):
        """Crea datos base, retorna IDs como strings (evita objetos detached)."""
        SessionLocal = sessionmaker(bind=engine)
        session = SessionLocal()
        from app.models.user import User, UserRole
        from app.core.security import get_password_hash
        from app.models.course import Course, CourseStatus
        from app.models.learning_objective import LearningObjective

        user = User(
            email="conc@test.com", hashed_password=get_password_hash("123"),
            first_name="Con", last_name="Current",
            role=UserRole.ESTUDIANTE, institutional_code="CONC001",
            is_active=True,
        )
        session.add(user)
        session.flush()

        course = Course(
            code="CONC-01", name="Concurrent Course", cycle=1, year=2026,
            teacher_id=user.id, status=CourseStatus.PUBLICADO,
        )
        session.add(course)
        session.flush()

        for i in range(3):
            session.add(LearningObjective(course_id=course.id, title=f"Obj {i+1}", bloom_level=i+1, order=i))
        session.commit()
        user_id = user.id
        course_id = course.id
        session.close()
        return user_id, course_id

    def test_concurrent_enroll_same_student(self, concurrent_engine):
        """2 threads inscriben al mismo estudiante: solo 1 enrollment."""
        user_id, course_id = self._setup_base_data(concurrent_engine)

        def enroll():
            try:
                from app.services.course_service import enroll_students
                SessionLocal = sessionmaker(bind=concurrent_engine)
                session = SessionLocal()
                enroll_students(session, course_id, [user_id])
                session.close()
            except Exception:
                pass

        t1 = threading.Thread(target=enroll)
        t2 = threading.Thread(target=enroll)
        t1.start()
        time.sleep(0.02)
        t2.start()
        t1.join()
        t2.join()

        from app.models.enrollment import Enrollment
        session = sessionmaker(bind=concurrent_engine)()
        count = session.query(Enrollment).filter(
            Enrollment.course_id == course_id,
            Enrollment.student_id == user_id,
        ).count()
        session.close()
        assert count == 1


# =============================================================================
# 8. UoW Transaction Boundary Tests
# =============================================================================


class TestUoWOperationGuards:
    """Verify UoW raises on invalid state transitions."""

    def test_can_access_db_after_commit(self, db):
        uow = UnitOfWork(lambda: db)
        uow.commit()
        # db access is allowed after commit for read-back queries
        assert uow.db is not None

    def test_can_access_db_after_rollback(self, db):
        uow = UnitOfWork(lambda: db)
        uow.rollback()
        # db access is allowed after rollback for verification queries
        assert uow.db is not None

    def test_cannot_add_event_after_commit(self, db):
        uow = UnitOfWork(lambda: db)
        uow.commit()
        with pytest.raises(RuntimeError, match="already committed"):
            uow.add_event("test", "agg")

    def test_cannot_add_event_after_rollback(self, db):
        uow = UnitOfWork(lambda: db)
        uow.rollback()
        with pytest.raises(RuntimeError, match="already rolled back"):
            uow.add_event("test", "agg")

    def test_commit_is_idempotent(self, db):
        uow = UnitOfWork(lambda: db)
        uow.commit()
        # commit after commit is a no-op (idempotent), matching SQLAlchemy behavior
        uow.commit()
        assert uow._committed is True

    def test_rollback_after_commit_is_noop(self, db):
        uow = UnitOfWork(lambda: db)
        uow.commit()
        uow.rollback()  # should not raise
        assert uow._committed is True
        assert uow._rolled_back is False


class TestUoWSavepoint:
    """Verify savepoint isolation within UoW."""

    def test_savepoint_rollback_does_not_lose_parent_changes(self, db, estudiante_user):
        from app.models.student_memory import StudentMemory

        uow = UnitOfWork(lambda: db)
        s = StudentMemory(
            student_id=estudiante_user.id,
            memory_type="test",
            key="parent_key",
            value="parent_value",
        )
        db.add(s)
        uow.flush()

        # Create a savepoint, make changes, rollback
        try:
            with db.begin_nested():
                child = StudentMemory(
                    student_id=estudiante_user.id,
                    memory_type="test",
                    key="child_key",
                    value="child_value",
                )
                db.add(child)
                uow.flush()
                raise RuntimeError("Simulated failure")
        except RuntimeError:
            pass

        # Parent change should still be present
        parent = db.query(StudentMemory).filter(
            StudentMemory.key == "parent_key",
        ).first()
        assert parent is not None
        assert parent.value == "parent_value"

        # Child change should NOT be present (rolled back by savepoint)
        child = db.query(StudentMemory).filter(
            StudentMemory.key == "child_key",
        ).first()
        assert child is None

        uow.rollback()


# =============================================================================
# 9. P0 — completed_modules eliminado (Fase 1, auditoría de concurrencia
#    2026-08-09, commit 11f6f20). El arnés original de reproducción HTTP
#    real fue temporal y se borró tras usarse; este test reemplaza esa
#    verificación con una regresión permanente: PathModule.version
#    (optimistic lock) debe impedir que dos escritores concurrentes
#    apliquen ambos el efecto de completitud sobre el mismo módulo.
# =============================================================================

class TestP0ModuleProgressConcurrency:
    def _setup(self, engine):
        SessionLocal = sessionmaker(bind=engine)
        session = SessionLocal()
        from app.models.user import User, UserRole
        from app.core.security import get_password_hash
        from app.models.course import Course, CourseStatus
        from app.models.student_progress import LearningPath, PathModule

        user = User(
            email="p0conc@test.com", hashed_password=get_password_hash("123"),
            first_name="P0", last_name="Conc",
            role=UserRole.ESTUDIANTE, institutional_code="P0CONC01",
            is_active=True,
        )
        session.add(user)
        session.flush()

        course = Course(
            code="P0-CONC", name="P0 Concurrency Course", cycle=1, year=2026,
            teacher_id=user.id, status=CourseStatus.PUBLICADO,
        )
        session.add(course)
        session.flush()

        path = LearningPath(student_id=user.id, course_id=course.id, total_modules=2)
        session.add(path)
        session.flush()

        module = PathModule(path_id=path.id, title="Modulo 1", order=1, status="available")
        next_module = PathModule(path_id=path.id, title="Modulo 2", order=2, status="locked")
        session.add_all([module, next_module])
        session.commit()

        ids = (user.id, module.id, next_module.id)
        session.close()
        return ids

    def test_dos_escritores_concurrentes_solo_uno_completa(self, concurrent_engine):
        from app.services.student_service import update_module_progress

        student_id, module_id, next_module_id = self._setup(concurrent_engine)
        SessionLocal = sessionmaker(bind=concurrent_engine)
        # autoflush=False en los hilos de la carrera: con autoflush por
        # defecto, la consulta a LearningPath inmediatamente después de
        # mutar module.status dispara el flush (y por tanto el UPDATE con
        # chequeo de versión) ANTES de llegar al commit() explícito, lo
        # que deja el barrier de commit() sincronizando el punto
        # equivocado. Desactivarlo aquí garantiza que el único flush
        # ocurra dentro del commit() ya sincronizado — el mismo efecto
        # observable (una sola escritura gana), pero determinista de
        # reproducir en el test.
        WorkerSession = sessionmaker(bind=concurrent_engine, autoflush=False)

        resultados = []
        # Sincronizar solo el `wait()` inicial no basta: sin sincronizar
        # también el commit, el scheduler puede dejar que un hilo lea,
        # mute Y comitee ANTES de que el otro siquiera consulte — en ese
        # caso el segundo lee el estado YA "completed" y no hay carrera
        # que probar. Se sincroniza el commit en sí: así ambos hilos
        # garantizadamente leen el módulo en su estado "available" ANTES
        # de que cualquiera de los dos persista.
        barrera_commit = threading.Barrier(2)
        commit_original = Session.commit

        def commit_sincronizado(self, *args, **kwargs):
            barrera_commit.wait()
            return commit_original(self, *args, **kwargs)

        def worker():
            db = WorkerSession()
            try:
                update_module_progress(db, module_id, "completed", student_id, score=10.0)
                resultados.append("ok")
            except StaleDataError:
                db.rollback()
                resultados.append("stale")
            finally:
                db.close()

        Session.commit = commit_sincronizado
        try:
            t1 = threading.Thread(target=worker)
            t2 = threading.Thread(target=worker)
            t1.start()
            t2.start()
            t1.join()
            t2.join()
        finally:
            Session.commit = commit_original

        # Ambos hilos leyeron el módulo en status="available" (sincronizado
        # justo antes del commit), así que ambos intentan aplicar el efecto
        # de completitud — el optimistic lock (version_id_col) debe frenar
        # al segundo, no dejarlo aplicar un segundo efecto silencioso.
        assert resultados.count("ok") == 1
        assert resultados.count("stale") == 1

        verify = SessionLocal()
        from app.models.student_progress import PathModule
        mod = verify.query(PathModule).filter(PathModule.id == module_id).first()
        assert mod.status == "completed"
        next_mod = verify.query(PathModule).filter(PathModule.id == next_module_id).first()
        assert next_mod.status == "available"
        verify.close()


# =============================================================================
# 10. P1 — Engagement (Fase 1, auditoría de concurrencia 2026-08-09,
#     commits fbf84ac + 0ffae50). Los arneses originales de reproducción
#     HTTP real fueron temporales y se borraron tras usarse ("sin test
#     dedicado" en ambos commits); estos tests son la regresión permanente
#     que faltaba.
# =============================================================================

class TestP1EngagementConcurrency:
    """Caso A (interact): xp_earned/resources_shown son read-modify-write
    protegidos por advisory_lock. Caso B (complete): idempotencia — una
    sesión ya terminal no vuelve a aplicar el bonus de completitud."""

    def _setup(self, engine):
        SessionLocal = sessionmaker(bind=engine)
        session = SessionLocal()
        from app.models.user import User, UserRole
        from app.core.security import get_password_hash
        from app.models.course import Course, CourseStatus
        from app.models.student_progress import LearningPath, PathModule
        from app.models.engagement import EngagementSession, EngagementResource

        user = User(
            email="p1conc@test.com", hashed_password=get_password_hash("123"),
            first_name="P1", last_name="Conc",
            role=UserRole.ESTUDIANTE, institutional_code="P1CONC01",
            is_active=True,
        )
        session.add(user)
        session.flush()

        course = Course(
            code="P1-CONC", name="P1 Concurrency Course", cycle=1, year=2026,
            teacher_id=user.id, status=CourseStatus.PUBLICADO,
        )
        session.add(course)
        session.flush()

        path = LearningPath(student_id=user.id, course_id=course.id, total_modules=1)
        session.add(path)
        session.flush()

        module = PathModule(path_id=path.id, title="Modulo 1", order=1, status="available")
        session.add(module)
        session.flush()

        eng_session = EngagementSession(
            student_id=user.id, module_id=module.id, status="active",
            modality_profile="visual", resources_shown=0, resources_interacted=0,
            xp_earned=5,  # XP_TABLE["session_started"]
            earned_badges=[],
        )
        session.add(eng_session)
        session.flush()

        resource_a = EngagementResource(
            session_id=eng_session.id, resource_type="did_you_know",
            title="R1", content="contenido", display_order=0,
        )
        resource_b = EngagementResource(
            session_id=eng_session.id, resource_type="did_you_know",
            title="R2", content="contenido", display_order=1,
        )
        session.add_all([resource_a, resource_b])
        session.commit()

        ids = (user.id, eng_session.id, resource_a.id, resource_b.id)
        session.close()
        return ids

    def test_caso_a_interact_concurrente_no_pierde_acumuladores(self, concurrent_engine):
        from app.services.engagement_service import EngagementService
        from app.schemas.engagement import InteractRequest

        student_id, session_id, resource_a_id, resource_b_id = self._setup(concurrent_engine)
        SessionLocal = sessionmaker(bind=concurrent_engine)

        barrera = threading.Barrier(2)

        def worker(resource_id: str):
            db = SessionLocal()
            student = db.get(__import__("app.models.user", fromlist=["User"]).User, student_id)
            svc = EngagementService(db)
            req = InteractRequest(
                session_id=session_id, resource_id=resource_id,
                interaction_type="view", time_spent_seconds=3,
            )
            barrera.wait()
            svc.interact(req, student)
            db.close()

        t1 = threading.Thread(target=worker, args=(resource_a_id,))
        t2 = threading.Thread(target=worker, args=(resource_b_id,))
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        verify = SessionLocal()
        from app.models.engagement import EngagementSession
        eng_session = verify.query(EngagementSession).filter(EngagementSession.id == session_id).first()
        # Antes del fix (sin advisory_lock): 4/5 corridas perdían un
        # incremento (resources_shown=1, xp_earned=7 en vez de 9).
        assert eng_session.resources_shown == 2
        assert eng_session.xp_earned == 9  # 5 inicio + 2 vistas x 2 XP
        verify.close()

    def test_caso_b_complete_es_idempotente_bajo_llamadas_concurrentes(self, concurrent_engine):
        from app.services.engagement_service import EngagementService
        from app.schemas.engagement import CompleteRequest

        student_id, session_id, _, _ = self._setup(concurrent_engine)
        SessionLocal = sessionmaker(bind=concurrent_engine)

        resultados = []
        barrera = threading.Barrier(2)

        def worker():
            db = SessionLocal()
            student = db.get(__import__("app.models.user", fromlist=["User"]).User, student_id)
            svc = EngagementService(db)
            req = CompleteRequest(session_id=session_id, skipped=False)
            barrera.wait()
            resp = svc.complete(req, student)
            resultados.append(resp.xp_earned)
            db.close()

        t1 = threading.Thread(target=worker)
        t2 = threading.Thread(target=worker)
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        # Antes del fix: completed_events=2 siempre, xp_earned variable
        # (55-80) según el interleaving. Con el guard de idempotencia +
        # advisory_lock: el bonus de completitud y la insignia "explorador"
        # se aplican UNA sola vez, ambas respuestas ven el mismo total ya
        # persistido (5 inicio + 25 bonus + 25 insignia explorador).
        assert resultados[0] == resultados[1] == 55

        verify = SessionLocal()
        from app.models.engagement import EngagementEvent
        completed_events = verify.query(EngagementEvent).filter(
            EngagementEvent.session_id == session_id,
            EngagementEvent.event_type == "session_completed",
        ).count()
        assert completed_events == 1
        verify.close()


# =============================================================================
# 11. P0 (conteo derivado) y P1 (idempotencia secuencial) — complementan las
#     secciones 9 y 10: cubren el caso de dos módulos DISTINTOS completados
#     concurrentemente (no el mismo módulo, ya cubierto en la sección 9) y el
#     caso puramente secuencial de complete() (el bug de fbf84ac ocurría
#     incluso sin ninguna concurrencia real).
# =============================================================================

class TestP0AcademicSummaryLiveCount:
    """P0: LearningPath.completed_modules (contador cacheado) fue eliminado
    — get_academic_summary() deriva el conteo en vivo desde PathModule.status
    (student_service.py). Dos módulos completados por hilos concurrentes
    deben reflejarse ambos: no hay contador persistido que pueda perder una
    escritura."""

    def _setup(self, engine):
        SessionLocal = sessionmaker(bind=engine)
        session = SessionLocal()
        from app.models.user import User, UserRole
        from app.core.security import get_password_hash
        from app.models.course import Course, CourseStatus
        from app.models.enrollment import Enrollment, EnrollmentStatus
        from app.models.student_progress import LearningPath, PathModule

        student = User(
            email="p0conc@test.com", hashed_password=get_password_hash("123"),
            first_name="P0", last_name="Concurrencia",
            role=UserRole.ESTUDIANTE, institutional_code="P0CONC01",
            is_active=True,
        )
        session.add(student)
        session.flush()

        course = Course(
            code="P0-CONC", name="Curso P0 Concurrencia", cycle=1, year=2026,
            status=CourseStatus.PUBLICADO,
        )
        session.add(course)
        session.flush()

        session.add(Enrollment(
            student_id=student.id, course_id=course.id, status=EnrollmentStatus.ACTIVO,
        ))

        path = LearningPath(student_id=student.id, course_id=course.id, total_modules=2)
        session.add(path)
        session.flush()

        module_a = PathModule(path_id=path.id, title="Módulo A", order=0, status="available")
        module_b = PathModule(path_id=path.id, title="Módulo B", order=1, status="available")
        session.add_all([module_a, module_b])
        session.commit()

        ids = (student.id, module_a.id, module_b.id)
        session.close()
        return ids

    def test_dos_modulos_completados_concurrentemente_se_cuentan_ambos(self, concurrent_engine):
        student_id, module_a_id, module_b_id = self._setup(concurrent_engine)

        def complete(module_id):
            from app.services.student_service import update_module_progress
            SessionLocal = sessionmaker(bind=concurrent_engine)
            session = SessionLocal()
            update_module_progress(session, module_id, "completed", student_id, score=100)
            session.commit()
            session.close()

        t1 = threading.Thread(target=complete, args=(module_a_id,))
        t2 = threading.Thread(target=complete, args=(module_b_id,))
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        from app.services.student_service import get_academic_summary
        from app.models.user import User

        SessionLocal = sessionmaker(bind=concurrent_engine)
        session = SessionLocal()
        student = session.query(User).filter(User.id == student_id).first()
        summary = get_academic_summary(session, student)
        session.close()

        assert summary["completed_modules"] == 2, (
            "Ambos módulos completados concurrentemente deben contarse — "
            "un valor menor indicaría que volvió un contador cacheado con lost update."
        )


class TestP1EngagementIdempotency:
    """P1 Caso B: complete() aplicaba el bonus de completitud sin verificar
    session.status — dos llamadas, incluso puramente secuenciales (sin
    ninguna concurrencia real), duplicaban XP y el evento session_completed.
    El caso concurrente equivalente ya está cubierto, con sincronización
    real vía Barrier, en TestP1EngagementConcurrency.test_caso_b_*."""

    def _setup(self, engine):
        SessionLocal = sessionmaker(bind=engine)
        session = SessionLocal()
        from app.models.user import User, UserRole
        from app.core.security import get_password_hash
        from app.models.course import Course, CourseStatus
        from app.models.student_progress import LearningPath, PathModule
        from app.models.engagement import EngagementSession, _uuid as engagement_uuid

        student = User(
            email="p1conc@test.com", hashed_password=get_password_hash("123"),
            first_name="P1", last_name="Concurrencia",
            role=UserRole.ESTUDIANTE, institutional_code="P1CONC01",
            is_active=True,
        )
        session.add(student)
        session.flush()

        course = Course(code="P1-CONC", name="Curso P1", cycle=1, year=2026, status=CourseStatus.PUBLICADO)
        session.add(course)
        session.flush()

        path = LearningPath(student_id=student.id, course_id=course.id, total_modules=1)
        session.add(path)
        session.flush()

        module = PathModule(path_id=path.id, title="Módulo Engage", order=0, status="available")
        session.add(module)
        session.flush()

        engagement_session = EngagementSession(
            id=engagement_uuid(),
            student_id=student.id,
            module_id=module.id,
            status="active",
            resources_shown=0,
            resources_interacted=0,
            xp_earned=5,  # session_started
            earned_badges=[],
        )
        session.add(engagement_session)
        session.commit()

        ids = (student.id, engagement_session.id)
        session.close()
        return ids

    def test_complete_dos_veces_secuencial_no_duplica_bonus(self, concurrent_engine):
        student_id, session_id = self._setup(concurrent_engine)

        from app.services.engagement_service import EngagementService
        from app.schemas.engagement import CompleteRequest

        SessionLocal = sessionmaker(bind=concurrent_engine)
        db_session = SessionLocal()
        student = db_session.query(__import__('app.models.user', fromlist=['User']).User).get(student_id)

        service = EngagementService(db_session)
        req = CompleteRequest(session_id=session_id, skipped=False)

        first = service.complete(req, student)
        second = service.complete(req, student)
        db_session.close()

        assert first.xp_earned == second.xp_earned, (
            "La segunda llamada a complete() no debe volver a aplicar el bonus de completitud."
        )
        assert second.xp_breakdown["bonus_completitud"] == 25
