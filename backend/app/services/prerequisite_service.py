import logging
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.course import Course
from app.models.enrollment import Enrollment, EnrollmentStatus
from app.models.institutional_course import InstitutionalCourse, InstitutionalCoursePrerequisite
from app.models.user import User

logger = logging.getLogger(__name__)


def _load_prerequisite_map(db: Session, course_ids: list[str]) -> dict[str, list[InstitutionalCourse]]:
    if not course_ids:
        return {}
    courses = db.query(Course.id, Course.institutional_course_id).filter(Course.id.in_(course_ids)).all()
    inst_ids = [c.institutional_course_id for c in courses if c.institutional_course_id]
    if not inst_ids:
        return {}

    prereq_rels = (
        db.query(InstitutionalCoursePrerequisite)
        .filter(InstitutionalCoursePrerequisite.course_id.in_(inst_ids))
        .all()
    )
    all_prereq_ids = list({r.prerequisite_id for r in prereq_rels})
    if not all_prereq_ids:
        return {}

    prereq_lookup = {
        ic.id: ic
        for ic in db.query(InstitutionalCourse).filter(InstitutionalCourse.id.in_(all_prereq_ids)).all()
    }

    rel_map: dict[int, list[InstitutionalCourse]] = {}
    for r in prereq_rels:
        if r.prerequisite_id in prereq_lookup:
            rel_map.setdefault(r.course_id, []).append(prereq_lookup[r.prerequisite_id])

    result: dict[str, list[InstitutionalCourse]] = {}
    for c in courses:
        c_id: str = c.id if hasattr(c, 'id') else c[0]
        c_inst_id: int | None = c.institutional_course_id if hasattr(c, 'institutional_course_id') else c[1]
        if c_inst_id:
            result[c_id] = rel_map.get(c_inst_id, [])
    return result


def _load_enrollment_map(db: Session, student_id: str, course_ids: list[str]) -> dict[str, Enrollment]:
    if not course_ids:
        return {}
    enrollments = (
        db.query(Enrollment)
        .filter(Enrollment.student_id == student_id, Enrollment.course_id.in_(course_ids))
        .all()
    )
    return {e.course_id: e for e in enrollments}


def _batch_course_progress(db: Session, student_id: str, course_ids: list[str]) -> dict[str, int]:
    if not course_ids:
        return {}
    from app.models.resource import Resource
    from app.models.student_progress import StudentProgress

    total_rows = (
        db.query(Resource.course_id, func.count(Resource.id).label("total"))
        .filter(Resource.course_id.in_(course_ids))
        .group_by(Resource.course_id)
        .all()
    )
    total_map = {r.course_id: r.total for r in total_rows}

    completed_rows = (
        db.query(StudentProgress.course_id, func.count(StudentProgress.id).label("cnt"))
        .filter(
            StudentProgress.student_id == student_id,
            StudentProgress.course_id.in_(course_ids),
            StudentProgress.completed == True,
        )
        .group_by(StudentProgress.course_id)
        .all()
    )
    completed_map = {r.course_id: r.cnt for r in completed_rows}

    result = {}
    for cid in course_ids:
        total = total_map.get(cid, 0)
        completed = completed_map.get(cid, 0)
        result[cid] = round((completed / total) * 100) if total > 0 else 0
    return result


def _batch_check_course_access(
    db: Session,
    student_id: str,
    course_ids: list[str],
    prereq_map: dict[str, list[InstitutionalCourse]],
    enrollment_map: dict[str, Enrollment],
) -> dict[str, dict]:
    if not course_ids:
        return {}

    all_inst_ids = set()
    for cid in course_ids:
        for p in prereq_map.get(cid, []):
            all_inst_ids.add(p.id)

    if not all_inst_ids:
        return {cid: {"is_unlocked": True, "missing_prerequisites": [], "completed_prerequisites": [], "reason": None}
                for cid in course_ids}

    prereq_courses = {
        ic.id: ic
        for ic in db.query(InstitutionalCourse).filter(InstitutionalCourse.id.in_(list(all_inst_ids))).all()
    }

    result = {}
    for cid in course_ids:
        prereqs = prereq_map.get(cid, [])
        missing = []
        completed = []

        for prereq in prereqs:
            prereq_course = prereq_courses.get(prereq.id)
            if prereq_course:
                enrollment = enrollment_map.get(prereq_course.id)
                if enrollment and enrollment.status == EnrollmentStatus.COMPLETADO:
                    completed.append({
                        "course_id": prereq_course.id,
                        "code": prereq.code,
                        "name": prereq.name,
                    })
                else:
                    missing.append({
                        "course_id": prereq_course.id,
                        "code": prereq.code,
                        "name": prereq.name,
                        "status": "enrolled" if enrollment else "not_started",
                    })

        is_unlocked = len(missing) == 0
        reason = None
        if not is_unlocked:
            reason = f"Cursos prerequisitos pendientes: {', '.join(m['name'] for m in missing)}"

        result[cid] = {
            "course_id": cid,
            "is_unlocked": is_unlocked,
            "prerequisites_met": is_unlocked,
            "missing_prerequisites": missing,
            "completed_prerequisites": completed,
            "reason": reason,
        }

    return result


def get_institutional_prerequisite_codes(db: Session, course: Course) -> list[str]:
    if not course.institutional_course_id:
        return []
    prereq_ids = [
        p.prerequisite_id
        for p in db.query(InstitutionalCoursePrerequisite)
        .filter(InstitutionalCoursePrerequisite.course_id == course.institutional_course_id)
        .all()
    ]
    if not prereq_ids:
        return []
    courses = db.query(InstitutionalCourse).filter(InstitutionalCourse.id.in_(prereq_ids)).all()
    return [c.code for c in courses]


def get_institutional_prerequisites(db: Session, course: Course) -> list[InstitutionalCourse]:
    if not course.institutional_course_id:
        return []
    prereq_ids = [
        p.prerequisite_id
        for p in db.query(InstitutionalCoursePrerequisite)
        .filter(InstitutionalCoursePrerequisite.course_id == course.institutional_course_id)
        .all()
    ]
    return db.query(InstitutionalCourse).filter(InstitutionalCourse.id.in_(prereq_ids)).all() if prereq_ids else []


def has_student_completed_course(db: Session, student_id: str, course_id: str) -> bool:
    enrollment = (
        db.query(Enrollment)
        .filter(Enrollment.student_id == student_id, Enrollment.course_id == course_id)
        .first()
    )
    return enrollment is not None and enrollment.status == EnrollmentStatus.COMPLETADO


def is_student_enrolled_in_course(db: Session, student_id: str, course_id: str) -> bool:
    enrollment = (
        db.query(Enrollment)
        .filter(Enrollment.student_id == student_id, Enrollment.course_id == course_id)
        .first()
    )
    return enrollment is not None


def check_course_access(db: Session, student: User, course: Course) -> dict:
    prereq_inst_courses = get_institutional_prerequisites(db, course)
    if not prereq_inst_courses:
        return {
            "course_id": course.id,
            "course_code": course.code,
            "course_name": course.name,
            "is_unlocked": True,
            "prerequisites_met": True,
            "missing_prerequisites": [],
            "completed_prerequisites": [],
            "reason": None,
        }

    prereq_inst_ids = [p.id for p in prereq_inst_courses]
    prereq_inst_map = {p.id: p for p in prereq_inst_courses}

    prereq_courses = (
        db.query(Course)
        .filter(Course.institutional_course_id.in_(prereq_inst_ids))
        .all()
    )
    best_course_map: dict[str, Course] = {}
    for pc in prereq_courses:
        if pc.institutional_course_id:
            existing = best_course_map.get(pc.institutional_course_id)
            if not existing or (pc.year == course.year and existing.year != course.year):
                best_course_map[pc.institutional_course_id] = pc

    prereq_course_ids = [pc.id for pc in best_course_map.values()]
    enrollment_map = {}
    if prereq_course_ids:
        enrollments = (
            db.query(Enrollment)
            .filter(
                Enrollment.student_id == student.id,
                Enrollment.course_id.in_(prereq_course_ids),
            )
            .all()
        )
        enrollment_map = {e.course_id: e for e in enrollments}

    missing = []
    completed = []

    for inst_course in prereq_inst_courses:
        course_for_prereq = best_course_map.get(inst_course.id)
        if not course_for_prereq:
            missing.append({
                "course_id": None,
                "code": inst_course.code,
                "name": inst_course.name,
                "status": "not_started",
            })
            continue

        enrollment = enrollment_map.get(course_for_prereq.id)
        if enrollment and enrollment.status == EnrollmentStatus.COMPLETADO:
            completed.append({
                "course_id": course_for_prereq.id,
                "code": inst_course.code,
                "name": inst_course.name,
            })
        else:
            missing.append({
                "course_id": course_for_prereq.id,
                "code": inst_course.code,
                "name": inst_course.name,
                "status": "enrolled" if enrollment else "not_started",
            })

    is_unlocked = len(missing) == 0
    reason = None
    if not is_unlocked:
        reason = f"Cursos prerequisitos pendientes: {', '.join(m['name'] for m in missing)}"

    return {
        "course_id": course.id,
        "course_code": course.code,
        "course_name": course.name,
        "is_unlocked": is_unlocked,
        "prerequisites_met": is_unlocked,
        "missing_prerequisites": missing,
        "completed_prerequisites": completed,
        "reason": reason,
    }


def get_all_student_curriculum_status(db: Session, student: User) -> list[dict]:
    if not student.current_cycle:
        return []

    courses = (
        db.query(Course)
        .filter(Course.status != "archivado")
        .order_by(Course.cycle, Course.code)
        .all()
    )
    course_ids = [c.id for c in courses]

    prereq_map = _load_prerequisite_map(db, course_ids)
    enrollment_map = _load_enrollment_map(db, student.id, course_ids)
    progress_map = _batch_course_progress(db, student.id, course_ids)
    access_map = _batch_check_course_access(db, student.id, course_ids, prereq_map, enrollment_map)

    results = []
    for course in courses:
        enrollment = enrollment_map.get(course.id)
        is_enrolled = enrollment is not None
        is_completed = enrollment is not None and enrollment.status == EnrollmentStatus.COMPLETADO
        access = access_map.get(course.id, {})
        progress = progress_map.get(course.id, 0)

        results.append({
            "course_id": course.id,
            "course_code": course.code,
            "course_name": course.name,
            "cycle": course.cycle,
            "is_enrolled": is_enrolled,
            "is_completed": is_completed,
            "is_unlocked": access.get("is_unlocked", True),
            "progress_percentage": progress,
            "prerequisite_codes": [p.code for p in prereq_map.get(course.id, [])],
            "missing_prerequisites": access.get("missing_prerequisites", []),
        })

    return results


def predict_student_risk(db: Session, student: User) -> dict:
    from app.models.diagnostic_result import DiagnosticResult
    from app.models.resource import Resource
    from app.models.student_progress import StudentProgress

    enrollments = (
        db.query(Enrollment)
        .filter(Enrollment.student_id == student.id)
        .all()
    )

    total_enrolled = len(enrollments)
    completed_courses = sum(1 for e in enrollments if e.status == EnrollmentStatus.COMPLETADO)
    active_courses = sum(1 for e in enrollments if e.status == EnrollmentStatus.ACTIVO)
    active_course_ids = [e.course_id for e in enrollments if e.status == EnrollmentStatus.ACTIVO]

    total_progress = 0
    total_resources = 0
    if active_course_ids:
        completed_counts = (
            db.query(StudentProgress.course_id, func.count(StudentProgress.id).label("cnt"))
            .filter(
                StudentProgress.student_id == student.id,
                StudentProgress.course_id.in_(active_course_ids),
                StudentProgress.completed == True,
            )
            .group_by(StudentProgress.course_id)
            .all()
        )
        total_progress = sum(r.cnt for r in completed_counts)

        total_resources_result = (
            db.query(func.count(Resource.id))
            .filter(Resource.course_id.in_(active_course_ids))
            .scalar()
        )
        total_resources = total_resources_result or 0

    progress_rate = total_progress / total_resources if total_resources > 0 else 0
    completion_rate = completed_courses / total_enrolled if total_enrolled > 0 else 0

    diagnostics_done = (
        db.query(DiagnosticResult)
        .filter(DiagnosticResult.student_id == student.id)
        .count()
    )
    diag_rate = diagnostics_done / active_courses if active_courses > 0 else 1

    factors = []
    if progress_rate < 0.3:
        factors.append("Bajo progreso en cursos activos")
    if completion_rate < 0.2 and total_enrolled > 2:
        factors.append("Baja tasa de finalización")
    if diag_rate < 0.5 and active_courses > 0:
        factors.append("Diagnósticos pendientes")
    if total_enrolled == 0:
        factors.append("Sin cursos activos")

    if progress_rate >= 0.7 and completion_rate >= 0.5:
        risk_level = "bajo"
        risk_score = 0.2
    elif progress_rate >= 0.4 and completion_rate >= 0.3:
        risk_level = "medio"
        risk_score = 0.5
    else:
        risk_level = "alto"
        risk_score = 0.8

    recommendations = []
    if risk_level == "alto":
        recommendations.append("Revisar plan de estudios con tutor académico")
        recommendations.append("Establecer metas semanales de avance")
        if progress_rate < 0.3:
            recommendations.append("Dedicar tiempo adicional a los cursos activos")
    elif risk_level == "medio":
        recommendations.append("Mantener ritmo de estudio constante")
        recommendations.append("Completar diagnósticos pendientes")

    if risk_level == "bajo":
        recommendations.append("Continuar con el ritmo actual")
        recommendations.append("Explorar cursos avanzados o complementarios")

    explanation_parts = []
    if factors:
        explanation_parts.append("Factores detectados: " + "; ".join(factors[:3]))
    explanation_parts.append(f"Progreso: {int(progress_rate * 100)}%, Finalización: {int(completion_rate * 100)}%")

    return {
        "risk_level": risk_level,
        "risk_score": risk_score,
        "explanation": ". ".join(explanation_parts),
        "factors": factors[:5],
        "recommendations": recommendations[:4],
    }


def get_student_strengths(db: Session, student: User) -> list[str]:
    from app.models.diagnostic_result import DiagnosticResult
    from app.models.resource import Resource
    from app.models.student_progress import StudentProgress

    diagnostics = (
        db.query(DiagnosticResult)
        .filter(DiagnosticResult.student_id == student.id)
        .all()
    )

    strengths = []
    for d in diagnostics:
        if d.dominant_modality:
            strengths.append(f"Perfil {d.dominant_modality} para {d.course_id[:8]}")
    if not strengths:
        strengths.append("Inicio del programa académico")

    active_enrollments = (
        db.query(Enrollment)
        .filter(
            Enrollment.student_id == student.id,
            Enrollment.status == EnrollmentStatus.ACTIVO,
        )
        .all()
    )
    active_course_ids = [e.course_id for e in active_enrollments]

    if active_course_ids:
        completed_rows = (
            db.query(StudentProgress.course_id, func.count(StudentProgress.id).label("cnt"))
            .filter(
                StudentProgress.student_id == student.id,
                StudentProgress.course_id.in_(active_course_ids),
                StudentProgress.completed == True,
            )
            .group_by(StudentProgress.course_id)
            .all()
        )
        completed_map = {r.course_id: r.cnt for r in completed_rows}

        total_resource_rows = (
            db.query(Resource.course_id, func.count(Resource.id).label("total"))
            .filter(Resource.course_id.in_(active_course_ids))
            .group_by(Resource.course_id)
            .all()
        )
        total_map = {r.course_id: r.total for r in total_resource_rows}

        total_progress = 0
        count = 0
        for cid in active_course_ids:
            total_res = total_map.get(cid, 0)
            if total_res > 0:
                total_progress += completed_map.get(cid, 0) / total_res
                count += 1

        if count > 0:
            avg = total_progress / count
            if avg > 0.5:
                strengths.append(f"Progreso general del {int(avg * 100)}% en cursos activos")

    return strengths[:4]


def get_next_recommended_course(db: Session, student: User) -> Optional[dict]:
    if not student.current_cycle:
        return None

    next_cycle = student.current_cycle + 1
    if next_cycle > 10:
        return None

    next_courses = (
        db.query(Course)
        .filter(Course.cycle == next_cycle, Course.status != "archivado")
        .all()
    )
    if not next_courses:
        return None

    course_ids = [c.id for c in next_courses]
    prereq_map = _load_prerequisite_map(db, course_ids)
    enrollment_map = _load_enrollment_map(db, student.id, course_ids)
    access_map = _batch_check_course_access(db, student.id, course_ids, prereq_map, enrollment_map)

    for course in next_courses:
        access = access_map.get(course.id, {})
        if access.get("is_unlocked"):
            return {
                "course_id": course.id,
                "course_code": course.code,
                "course_name": course.name,
                "cycle": course.cycle,
            }

    return None


def get_course_analytics(db: Session, teacher_id: str) -> list[dict]:
    return get_course_analytics_batched(db, teacher_id)


def get_course_analytics_batched(db: Session, teacher_id: str) -> list[dict]:
    from app.models.resource import Resource
    from app.models.student_progress import StudentProgress

    courses = (
        db.query(Course)
        .filter(Course.teacher_id == teacher_id, Course.status != "archivado")
        .all()
    )
    if not courses:
        return []

    course_ids = [c.id for c in courses]
    course_lookup = {c.id: c for c in courses}

    enrollment_rows = (
        db.query(Enrollment.course_id, func.count(Enrollment.id).label("cnt"))
        .filter(Enrollment.course_id.in_(course_ids))
        .group_by(Enrollment.course_id)
        .all()
    )
    enrollment_counts = {r.course_id: r.cnt for r in enrollment_rows}

    student_enrollments = (
        db.query(Enrollment.course_id, Enrollment.student_id)
        .filter(Enrollment.course_id.in_(course_ids))
        .all()
    )
    course_students: dict[str, list[str]] = {}
    for r in student_enrollments:
        course_students.setdefault(r.course_id, []).append(r.student_id)

    all_student_ids = list({sid for sids in course_students.values() for sid in sids})

    resource_rows = (
        db.query(Resource.course_id, func.count(Resource.id).label("cnt"))
        .filter(Resource.course_id.in_(course_ids))
        .group_by(Resource.course_id)
        .all()
    )
    resource_counts = {r.course_id: r.cnt for r in resource_rows}

    progress_rows = (
        db.query(StudentProgress.course_id, StudentProgress.student_id)
        .filter(
            StudentProgress.course_id.in_(course_ids),
            StudentProgress.student_id.in_(all_student_ids) if all_student_ids else StudentProgress.student_id.isnot(None),
            StudentProgress.completed == True,
        )
        .all()
    )
    progress_per_course_student: dict[tuple[str, str], int] = {}
    for r in progress_rows:
        key = (r.course_id, r.student_id)
        progress_per_course_student[key] = progress_per_course_student.get(key, 0) + 1

    results = []
    for cid in course_ids:
        course = course_lookup[cid]
        enrolled_count = enrollment_counts.get(cid, 0)
        total_res = resource_counts.get(cid, 0)
        student_ids = course_students.get(cid, [])

        at_risk_count = 0
        total_pct = 0.0
        progress_count = 0

        for sid in student_ids:
            completed = progress_per_course_student.get((cid, sid), 0)
            if total_res > 0:
                pct = completed / total_res
                total_pct += pct
                progress_count += 1
                if pct < 0.3:
                    at_risk_count += 1

        avg_progress = round((total_pct / progress_count) * 100, 1) if progress_count > 0 else 0.0

        results.append({
            "course_id": cid,
            "course_name": course.name,
            "enrolled_count": enrolled_count,
            "avg_progress": avg_progress,
            "at_risk_count": at_risk_count,
            "difficult_topics": [],
            "competency_gaps": [],
            "recommendation": None,
        })

    return results
