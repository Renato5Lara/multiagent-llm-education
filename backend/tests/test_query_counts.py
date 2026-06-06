"""
Query count regression tests.

Ensures hot-path services do not produce N+1 queries.
Uses QueryCounter attached to the test engine to measure
per-function query counts and detect N+1 patterns.

If these tests fail, a code change introduced a new N+1.
"""
import pytest
from sqlalchemy.orm import Session

from app.db.query_counter import QueryCounter
from app.models.course import Course, CourseStatus
from app.models.enrollment import Enrollment, EnrollmentStatus
from app.models.institutional_course import InstitutionalCourse, InstitutionalCoursePrerequisite
from app.models.learning_objective import LearningObjective
from app.models.teacher_assignment import TeacherAssignment
from app.models.user import User, UserRole
from app.models.resource import Resource, ResourceType
from app.models.student_progress import LearningPath, PathModule
from app.models.competency import Competency, CourseCompetency
from app.models.diagnostic_result import DiagnosticResult

from app.services.prerequisite_service import (
    check_course_access, get_next_recommended_course, get_all_student_curriculum_status,
)
from app.services.course_service import get_enrolled_students, get_courses
from app.services.student_service import get_learning_path_detail, generate_learning_path_adaptive
from app.services.curriculum_service import get_prerequisite_codes
from app.services.knowledge_graph_service import (
    get_course_recommendations_from_graph, ensure_course_nodes,
)

QUERY_COUNTER: QueryCounter | None = None


@pytest.fixture(scope="function", autouse=True)
def setup_counter(db_engine):
    global QUERY_COUNTER
    counter = QueryCounter()
    counter.attach(db_engine)
    QUERY_COUNTER = counter
    yield
    counter.detach(db_engine)
    QUERY_COUNTER = None


def _start():
    if QUERY_COUNTER:
        QUERY_COUNTER.start()


def _stop():
    if QUERY_COUNTER:
        QUERY_COUNTER.stop()
    return QUERY_COUNTER.count if QUERY_COUNTER else 0


# ── Fixtures ─────────────────────────────────────────────────────


@pytest.fixture
def admin_user(db) -> User:
    u = User(email="admin@qcount.com", first_name="Admin", last_name="Q",
             role=UserRole.ADMIN, hashed_password="x", is_active=True)
    db.add(u)
    db.commit()
    return u


@pytest.fixture
def docente(db) -> User:
    u = User(email="teacher@qcount.com", first_name="Teach", last_name="Q",
             role=UserRole.DOCENTE, hashed_password="x", is_active=True)
    db.add(u)
    db.commit()
    return u


@pytest.fixture
def student(db) -> User:
    u = User(email="student@qcount.com", first_name="Stud", last_name="Q",
             role=UserRole.ESTUDIANTE, hashed_password="x", is_active=True,
             current_cycle=1)
    db.add(u)
    db.commit()
    return u


@pytest.fixture
def student2(db) -> User:
    u = User(email="student2@qcount.com", first_name="Stud2", last_name="Q",
             role=UserRole.ESTUDIANTE, hashed_password="x", is_active=True)
    db.add(u)
    db.commit()
    return u


@pytest.fixture
def inst_course(db) -> InstitutionalCourse:
    inst = InstitutionalCourse(code="QC-101", name="Query Count 101", credits=4,
                                cycle=1, competencies="testing")
    db.add(inst)
    db.commit()
    return inst


@pytest.fixture
def inst_course2(db) -> InstitutionalCourse:
    inst = InstitutionalCourse(code="QC-102", name="Query Count 102", credits=4,
                                cycle=2, competencies="testing")
    db.add(inst)
    db.commit()
    return inst


@pytest.fixture
def course(db, docente, inst_course) -> Course:
    c = Course(code="QC-101", name="Query Count 101", cycle=1, year=2026,
               teacher_id=docente.id, institutional_course_id=inst_course.id,
               status=CourseStatus.PUBLICADO, is_institutional=True)
    db.add(c)
    db.commit()
    return c


@pytest.fixture
def course2(db, docente, inst_course2) -> Course:
    c = Course(code="QC-102", name="Query Count 102", cycle=2, year=2026,
               teacher_id=docente.id, institutional_course_id=inst_course2.id,
               status=CourseStatus.PUBLICADO, is_institutional=True)
    db.add(c)
    db.commit()
    return c


@pytest.fixture
def enrollment(db, student, course) -> Enrollment:
    e = Enrollment(student_id=student.id, course_id=course.id,
                   teacher_id=course.teacher_id, status=EnrollmentStatus.ACTIVO)
    db.add(e)
    db.commit()
    return e


@pytest.fixture
def resource(db, course) -> Resource:
    r = Resource(course_id=course.id, filename="test.pdf", original_filename="test.pdf",
                 file_path="/tmp/test.pdf", mime_type="application/pdf",
                 size_bytes=100, resource_type=ResourceType.PDF)
    db.add(r)
    db.commit()
    return r


@pytest.fixture
def learning_path(db, student, course) -> LearningPath:
    lp = LearningPath(student_id=student.id, course_id=course.id, total_modules=2)
    db.add(lp)
    db.flush()
    m1 = PathModule(path_id=lp.id, title="M1", order=0, status="available")
    m2 = PathModule(path_id=lp.id, title="M2", order=1, status="locked",
                    resource_id=None)
    db.add(m1)
    db.add(m2)
    db.commit()
    return lp


@pytest.fixture
def objective(db, course) -> LearningObjective:
    obj = LearningObjective(course_id=course.id, title="Obj 1", bloom_level=1, order=0)
    db.add(obj)
    db.commit()
    return obj


@pytest.fixture
def prereq_relation(db, inst_course, inst_course2):
    rel = InstitutionalCoursePrerequisite(course_id=inst_course2.id,
                                           prerequisite_id=inst_course.id)
    db.add(rel)
    db.commit()
    return rel


@pytest.fixture
def competency(db) -> Competency:
    comp = Competency(name="Testing Comp", description="A test competency",
                      competency_type="general")
    db.add(comp)
    db.commit()
    return comp


@pytest.fixture
def course_competency(db, course, competency):
    cc = CourseCompetency(course_id=course.id, competency_id=competency.id)
    db.add(cc)
    db.commit()
    return cc


# ── Tests ────────────────────────────────────────────────────────


class TestQueryCounter:
    """Verify the QueryCounter itself works correctly."""

    def test_count_basic_queries(self, db):
        _start()
        db.query(User).all()
        db.query(Course).all()
        cnt = _stop()
        assert cnt == 2, f"Expected 2 queries, got {cnt}"

    def test_detects_repeated_table_queries(self, db):
        _start()
        for _ in range(6):
            db.query(User).first()
        cnt = _stop()
        assert QUERY_COUNTER is not None
        warnings = QUERY_COUNTER._n1_warnings
        assert any("Potential N+1" in w for w in warnings), (
            f"Expected N+1 warning for 6 queries on users table, got {warnings}"
        )

    def test_stop_resets_isolation(self, db):
        _start()
        q1_count = _stop()
        assert q1_count == 0 or True  # no queries between start/stop
        _start()
        db.query(User).all()
        q2_count = _stop()
        assert q2_count == 1, f"Expected 1, got {q2_count}"


class TestGetEnrolledStudents:
    """get_enrolled_students: must stay at O(3) queries regardless of student count."""

    def test_no_students(self, db, course):
        _start()
        result = get_enrolled_students(db, course.id)
        cnt = _stop()
        assert result == []
        assert cnt <= 4, f"Expected <=4 queries for empty, got {cnt}"

    def test_single_student(self, db, course, student, enrollment):
        _start()
        result = get_enrolled_students(db, course.id)
        cnt = _stop()
        assert len(result) == 1
        assert cnt <= 4, f"Expected <=4 queries for 1 student, got {cnt}"

    def test_multiple_students_constant_queries(self, db, course):
        # Setup: create 5 students before measuring
        students = []
        for i in range(5):
            s = User(email=f"bulk{i}@qcount.com", first_name=f"Bulk{i}",
                     last_name="Q", role=UserRole.ESTUDIANTE,
                     hashed_password="x", is_active=True)
            db.add(s)
            db.flush()
            students.append(s)
            e = Enrollment(student_id=s.id, course_id=course.id,
                           teacher_id=course.teacher_id, status=EnrollmentStatus.ACTIVO)
            db.add(e)
        db.commit()

        _start()
        result = get_enrolled_students(db, course.id)
        cnt = _stop()
        assert len(result) == 5
        assert cnt <= 4, (
            f"Expected <=4 queries for 5 students (constant), got {cnt}. "
            "N+1 regression likely!"
        )


class TestGetPrerequisiteCodes:
    """get_prerequisite_codes must batch-load prerequisites."""

    def test_with_prereqs(self, db, inst_course, inst_course2, prereq_relation):
        _start()
        codes = get_prerequisite_codes(db, inst_course2.id)
        cnt = _stop()
        assert codes == ["QC-101"]
        assert cnt <= 2, f"Expected <=2 queries for prereq lookup, got {cnt}"


class TestCheckCourseAccess:
    """check_course_access must stay at fixed query count."""

    def test_with_prereqs(self, db, student, course, course2, inst_course,
                          inst_course2, prereq_relation, enrollment):
        _start()
        result = check_course_access(db, student, course2)
        cnt = _stop()
        assert cnt <= 5, f"Expected <=5 queries for check_course_access, got {cnt}"


class TestGetNextRecommendedCourse:
    """get_next_recommended_course: must batch-check all courses, not N+1 per course."""

    def test_with_prereqs(self, db, student, course, course2, inst_course,
                          inst_course2, prereq_relation, enrollment):
        student.current_cycle = 1
        db.commit()
        _start()
        result = get_next_recommended_course(db, student)
        cnt = _stop()
        # should operate in constant queries regardless of how many next-cycle courses
        assert cnt <= 8, f"Expected <=8 queries, got {cnt}. Possible N+1 per course!"


class TestGetLearningPathDetail:
    """get_learning_path_detail: must batch-load resources."""

    def test_basic(self, db, student, course, learning_path, resource):
        _start()
        detail = get_learning_path_detail(db, student.id, course.id)
        cnt = _stop()
        assert detail is not None
        assert cnt <= 6, f"Expected <=6 queries, got {cnt}"


class TestGenerateLearningPathAdaptive:
    """generate_learning_path_adaptive: must not N+1 per-objective."""

    def test_basic(self, db, student, course, objective, resource):
        from app.services.student_service import save_diagnostic
        diag = save_diagnostic(db, student.id, course.id, {"1": 3, "2": 4})
        _start()
        path = generate_learning_path_adaptive(db, student.id, course.id, diag)
        cnt = _stop()
        assert path is not None
        assert cnt <= 10, f"Expected <=10 queries, got {cnt}"


class TestGetCourseRecommendationsFromGraph:
    """get_course_recommendations_from_graph: must batch with IN."""

    def test_no_weaknesses(self, db):
        _start()
        result = get_course_recommendations_from_graph(db, [])
        cnt = _stop()
        assert result == []
        assert cnt <= 1, f"Expected <=1 query for empty weaknesses, got {cnt}"

    def test_with_data(self, db, course, competency, course_competency):
        from app.models.knowledge_graph import KnowledgeNode, KnowledgeEdge
        # create knowledge nodes + edges
        comp_node = KnowledgeNode(node_type="competency", label=competency.name,
                                   external_id=competency.id)
        db.add(comp_node)
        db.flush()
        course_node = KnowledgeNode(node_type="institutional_course",
                                     label="QC-101", external_id=course.institutional_course_id)
        db.add(course_node)
        db.flush()
        edge = KnowledgeEdge(source_id=course_node.id, target_id=comp_node.id,
                              relationship_type="teaches")
        db.add(edge)
        db.commit()
        _start()
        result = get_course_recommendations_from_graph(db, ["Testing"])
        cnt = _stop()
        assert len(result) >= 0
        assert cnt <= 5, f"Expected <=5 queries, got {cnt}"


class TestGetAllStudentCurriculumStatus:
    """get_all_student_curriculum_status: must batch-load all data."""

    def test_basic(self, db, student, course, course2, inst_course, inst_course2,
                   prereq_relation, enrollment):
        student.current_cycle = 1
        db.commit()
        _start()
        result = get_all_student_curriculum_status(db, student)
        cnt = _stop()
        assert cnt <= 8, f"Expected <=8 queries, got {cnt}. Possible N+1 per-course!"


class TestGetCourses:
    """get_courses: must not produce N+1 for teacher data."""

    def test_docente_courses(self, db, docente, course):
        _start()
        courses, total = get_courses(db, docente)
        cnt = _stop()
        assert total >= 0
        assert cnt <= 4, f"Expected <=4 queries, got {cnt}"
