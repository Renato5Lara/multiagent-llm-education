import logging

from sqlalchemy.orm import Session

from app.models.user import User
from app.services.prerequisite_service import get_course_analytics

logger = logging.getLogger(__name__)


async def get_docente_ia_analytics(db: Session, teacher: User) -> dict:
    analytics = get_course_analytics(db, teacher.id)
    total_students = sum(a["enrolled_count"] for a in analytics)
    total_at_risk = sum(a["at_risk_count"] for a in analytics)

    courses_with_issues = [a for a in analytics if a["at_risk_count"] > 0]
    general_issues = []
    if courses_with_issues:
        worst = max(courses_with_issues, key=lambda x: x["at_risk_count"])
        n = worst["at_risk_count"]
        general_issues.append(
            f"{worst['course_name']}: {n} estudiante{'s' if n > 1 else ''} en riesgo"
        )

    return {
        "course_analytics": analytics,
        "total_students": total_students,
        "total_at_risk": total_at_risk,
        "general_issues": general_issues,
    }
