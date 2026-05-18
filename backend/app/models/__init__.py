"""
Exporta todos los modelos para que Alembic los descubra automáticamente.
"""

from app.models.user import User, UserRole
from app.models.course import Course, CourseStatus
from app.models.learning_objective import LearningObjective
from app.models.resource import Resource, ResourceType
from app.models.resource_objective import ResourceObjective
from app.models.enrollment import Enrollment, EnrollmentStatus
from app.models.audit_log import AuditLog
from app.models.login_attempt import LoginAttempt
from app.models.diagnostic_result import DiagnosticResult
from app.models.student_progress import LearningPath, PathModule, StudentProgress
from app.models.evaluation_attempt import EvaluationAttempt
from app.models.competency import Competency, CompetencyType, CourseCompetency
from app.models.student_profile import StudentProfile

__all__ = [
    "User",
    "UserRole",
    "Course",
    "CourseStatus",
    "LearningObjective",
    "Resource",
    "ResourceType",
    "ResourceObjective",
    "Enrollment",
    "EnrollmentStatus",
    "AuditLog",
    "LoginAttempt",
    "DiagnosticResult",
    "LearningPath",
    "PathModule",
    "StudentProgress",
    "EvaluationAttempt",
    "Competency",
    "CompetencyType",
    "CourseCompetency",
    "StudentProfile",
]
