import logging
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.uow import AsyncUnitOfWork
from app.models.course import Course
from app.models.enrollment import Enrollment, EnrollmentStatus
from app.models.educational_context import EducationalContext, EducationalContextStatus
from app.models.learning_session import LearningSession
from app.models.student_progress import PathModule, StudentProgress
from app.models.user import User
from app.services.activation_service import activate_enrollment_with_swarm

logger = logging.getLogger(__name__)


async def start_module_session(
    db: AsyncSession,
    student: User,
    module_id: str,
) -> dict[str, Any]:
    result = await db.execute(select(PathModule).where(PathModule.id == module_id))
    module = result.scalar_one_or_none()
    if not module:
        return {"ok": False, "error": "Module not found"}

    path = module.path
    if not path or path.student_id != student.id:
        return {"ok": False, "error": "Module does not belong to student"}

    course_id = path.course_id
    result = await db.execute(
        select(Enrollment).where(
            Enrollment.student_id == student.id,
            Enrollment.course_id == course_id,
            Enrollment.status == EnrollmentStatus.ACTIVO,
        )
    )
    enrollment = result.scalar_one_or_none()

    context_key = f"ctx:{student.id}:{course_id}"

    session = LearningSession(
        student_id=student.id,
        course_id=course_id,
        module_id=module_id,
        enrollment_id=enrollment.id if enrollment else None,
        status="active",
        context_key=context_key,
        swarm_activated="pending",
    )
    db.add(session)
    await db.flush()

    result = await db.execute(
        select(EducationalContext).where(
            EducationalContext.student_id == student.id,
            EducationalContext.course_id == course_id,
        )
    )
    context = result.scalar_one_or_none()

    swarm_result = None
    if context and context.status == EducationalContextStatus.ACTIVE:
        try:
            result = await db.execute(select(Course).where(Course.id == course_id))
            course = result.scalar_one_or_none()
            swarm_result = await activate_enrollment_with_swarm(db, enrollment, course, context)
            session.swarm_activated = "completed" if swarm_result.get("ok") else "failed"
            await db.flush()
        except Exception as e:
            logger.error("Swarm activation failed on session start: %s", e, exc_info=True)
            session.swarm_activated = "failed"
            await db.flush()

    resource_id = module.resource_id
    resource_url = None
    if resource_id:
        resource_url = f"/api/resources/{resource_id}"

    await db.commit()

    return {
        "ok": True,
        "session_id": session.id,
        "status": session.status,
        "resource_id": resource_id,
        "resource_url": resource_url,
        "module_title": module.title,
        "module_status": module.status,
        "swarm_activated": session.swarm_activated,
        "swarm_result": swarm_result,
        "context_key": context_key,
    }


async def end_session(db: AsyncSession, session_id: str) -> dict[str, Any]:
    result = await db.execute(select(LearningSession).where(LearningSession.id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        return {"ok": False, "error": "Session not found"}
    session.end()
    await db.commit()
    return {
        "ok": True,
        "session_id": session.id,
        "duration_minutes": session.duration_minutes,
        "status": session.status,
    }


async def get_active_session(db: AsyncSession, student_id: str, course_id: str) -> Optional[LearningSession]:
    result = await db.execute(
        select(LearningSession).where(
            LearningSession.student_id == student_id,
            LearningSession.course_id == course_id,
            LearningSession.status == "active",
        )
    )
    return result.scalar_one_or_none()


async def get_module_entry_data(
    db: AsyncSession, student_id: str, module_id: str
) -> dict[str, Any]:
    result = await db.execute(select(PathModule).where(PathModule.id == module_id))
    module = result.scalar_one_or_none()
    if not module:
        return {"ok": False, "error": "Módulo no encontrado"}

    path = module.path
    if not path or path.student_id != student_id:
        return {"ok": False, "error": "Módulo no pertenece al estudiante"}

    course_id = path.course_id
    resource = None
    if module.resource_id:
        from app.models.resource import Resource
        result = await db.execute(select(Resource).where(Resource.id == module.resource_id))
        resource = result.scalar_one_or_none()

    result = await db.execute(
        select(StudentProgress).where(
            StudentProgress.student_id == student_id,
            StudentProgress.course_id == course_id,
            StudentProgress.resource_id == module.resource_id,
        )
    )
    progress = result.scalar_one_or_none()

    active_session = await get_active_session(db, student_id, course_id)

    return {
        "ok": True,
        "session": active_session,
        "module": {
            "id": module.id,
            "title": module.title,
            "description": module.description,
            "status": module.status,
            "order": module.order,
            "bloom_level": module.bloom_level,
        },
        "resource": {
            "id": resource.id if resource else None,
            "type": resource.resource_type.value if resource else None,
            "filename": resource.original_filename if resource else None,
        } if resource else None,
        "progress": {
            "completed": progress.completed if progress else False,
            "percentage": progress.progress_percentage if progress else 0,
        },
    }
