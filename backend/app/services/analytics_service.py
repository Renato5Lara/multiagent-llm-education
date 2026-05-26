import logging
from typing import Optional

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.course import Course
from app.models.enrollment import Enrollment, EnrollmentStatus
from app.models.student_progress import StudentProgress, LearningPath
from app.models.resource import Resource
from app.models.diagnostic_result import DiagnosticResult
from app.models.user import User
from app.services.prerequisite_service import (
    check_course_access,
    get_all_student_curriculum_status,
    predict_student_risk,
    get_student_strengths,
    get_next_recommended_course,
    get_course_analytics,
)

logger = logging.getLogger(__name__)


async def get_student_ia_dashboard(db: Session, student: User) -> dict:
    risk = predict_student_risk(db, student)
    strengths = get_student_strengths(db, student)
    next_course = get_next_recommended_course(db, student)
    curriculum_status = get_all_student_curriculum_status(db, student)
    course_analytics_result = get_course_analytics(db, student.id)

    blocked_count = sum(1 for c in curriculum_status if not c["is_unlocked"])
    enrolled_count = sum(1 for c in curriculum_status if c["is_enrolled"])
    completed_count = sum(1 for c in curriculum_status if c["is_completed"])

    warnings = []
    if risk["risk_level"] == "alto":
        warnings.append("Riesgo académico alto detectado")
    if blocked_count > 0:
        warnings.append(f"{blocked_count} curso(s) bloqueados por prerrequisitos")
    if risk["risk_level"] == "medio":
        warnings.append("Riesgo académico moderado, monitorear progreso")

    return {
        "student_risk": risk,
        "course_analytics": course_analytics_result,
        "next_recommended_course": next_course,
        "strengths": strengths,
        "warnings": warnings,
        "curriculum_status": curriculum_status,
        "stats": {
            "total": len(curriculum_status),
            "enrolled": enrolled_count,
            "completed": completed_count,
            "blocked": blocked_count,
            "progress_percentage": risk.get("risk_score", 0) * 100,
        },
    }


async def get_docente_ia_analytics(db: Session, teacher: User) -> dict:
    analytics = get_course_analytics(db, teacher.id)
    total_students = sum(a["enrolled_count"] for a in analytics)
    total_at_risk = sum(a["at_risk_count"] for a in analytics)

    courses_with_issues = [a for a in analytics if a["at_risk_count"] > 0]
    general_issues = []
    if courses_with_issues:
        worst = max(courses_with_issues, key=lambda x: x["at_risk_count"])
        general_issues.append(
            f"{worst['course_name']}: {worst['at_risk_count']} estudiantes en riesgo"
        )

    return {
        "course_analytics": analytics,
        "total_students": total_students,
        "total_at_risk": total_at_risk,
        "general_issues": general_issues,
    }
