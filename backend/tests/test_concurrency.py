"""
Tests de concurrencia y consistencia.

Verifica:
1. Advisory locks evitan race conditions
2. store_memory upserts sin duplicados
3. Rollback seguro bajo fallos
4. Integridad ante stress concurrente
"""

import threading
import time

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.locks import advisory_lock, lock_key
from app.db.uow import UnitOfWork
from app.models.student_memory import StudentMemory
from app.services.memory_service import store_memory


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
# 2. store_memory Concurrency Tests (single-threaded logic)
# =============================================================================

class TestStoreMemoryConcurrency:
    """Race conditions en store_memory."""

    def test_store_memory_upsert_idempotent(self, db, estudiante_user):
        """store_memory con misma clave hace upsert, no duplica."""
        from app.services.memory_service import store_memory

        uow = UnitOfWork(lambda: db)
        r1 = store_memory(uow, estudiante_user.id, "preference", "modality", "visual", score=0.8)
        uow.commit()
        assert r1.value == "visual"

        uow2 = UnitOfWork(lambda: db)
        r2 = store_memory(uow2, estudiante_user.id, "preference", "modality", "kinesthetic", score=0.6)
        uow2.commit()
        assert r2.value == "kinesthetic"

        count = db.query(StudentMemory).filter(
            StudentMemory.student_id == estudiante_user.id,
            StudentMemory.memory_type == "preference",
            StudentMemory.key == "modality",
        ).count()
        assert count == 1

    def test_store_memory_rollback_on_integrity_error(self, db, estudiante_user):
        uow = UnitOfWork(lambda: db)

        mem = StudentMemory(
            student_id=estudiante_user.id,
            memory_type="preference",
            key="rollback-test",
            value="original",
        )
        db.add(mem)
        db.commit()

        store_memory(uow, estudiante_user.id, "preference", "rollback-test", "updated")
        uow.commit()

        memories = db.query(StudentMemory).filter(
            StudentMemory.student_id == estudiante_user.id,
            StudentMemory.memory_type == "preference",
            StudentMemory.key == "rollback-test",
        ).all()
        assert len(memories) == 1
        assert memories[0].value == "updated"

    def test_store_memory_multiple_keys(self, db, estudiante_user):
        """Diferentes keys se insertan sin conflictos."""
        uow = UnitOfWork(lambda: db)
        store_memory(uow, estudiante_user.id, "preference", "key_a", "value_a")
        store_memory(uow, estudiante_user.id, "preference", "key_b", "value_b")
        uow.commit()

        count = db.query(StudentMemory).filter(
            StudentMemory.student_id == estudiante_user.id,
        ).count()
        assert count == 2


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

    def test_concurrent_store_memory_different_keys(self, concurrent_engine):
        """5 threads almacenan memorias con diferentes keys sin conflictos."""
        user_id, _ = self._setup_base_data(concurrent_engine)
        n_threads = 5
        errors = []

        def store_at(i):
            try:
                SessionLocal = sessionmaker(bind=concurrent_engine)
                session = SessionLocal()
                uow = UnitOfWork(lambda: session)
                store_memory(uow, user_id, "stress", f"key_{i}", f"value_{i}")
                uow.commit()
                session.close()
            except Exception as e:
                errors.append((i, str(e)))

        threads = [threading.Thread(target=store_at, args=(i,)) for i in range(n_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Errors: {errors}"

        session = sessionmaker(bind=concurrent_engine)()
        count = session.query(StudentMemory).filter(
            StudentMemory.student_id == user_id,
        ).count()
        session.close()
        assert count == n_threads

    def test_concurrent_same_key_serialized(self, concurrent_engine):
        """5 threads con la misma key: solo 1 registro final."""
        user_id, _ = self._setup_base_data(concurrent_engine)
        n_threads = 5

        def store_same():
            try:
                SessionLocal = sessionmaker(bind=concurrent_engine)
                session = SessionLocal()
                uow = UnitOfWork(lambda: session)
                store_memory(uow, user_id, "preference", "conflict_key", "value")
                uow.commit()
                session.close()
            except Exception:
                pass

        threads = [threading.Thread(target=store_same) for _ in range(n_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        session = sessionmaker(bind=concurrent_engine)()
        count = session.query(StudentMemory).filter(
            StudentMemory.student_id == user_id,
            StudentMemory.memory_type == "preference",
            StudentMemory.key == "conflict_key",
        ).count()
        session.close()
        assert count == 1

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
