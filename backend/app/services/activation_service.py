import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.db.uow import AsyncUnitOfWork, UnitOfWork
from app.models.course import Course
from app.models.enrollment import Enrollment, EnrollmentStatus
from app.models.educational_context import EducationalContext, EducationalContextStatus
from app.events.types import emit_event, EventType
from app.services.programming_course_service import (
    detect_programming_course as detect_programming_course_async,
    get_programming_swarm_config,
)
from app.swarm.orchestrator import SwarmOrchestrator

logger = logging.getLogger(__name__)

# ═════════════════════════════════════════════════════════════════
# Sync versions (for legacy sync callers: student_service, curriculum_service)
# ═════════════════════════════════════════════════════════════════


def activate_enrollments_for_course_sync(db: Session, course_id: str) -> int:
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course or not course.teacher_id:
        return 0

    pending = (
        db.query(Enrollment)
        .filter(
            Enrollment.course_id == course_id,
            Enrollment.status == EnrollmentStatus.PENDING_ACTIVATION,
        )
        .all()
    )

    activated = 0
    for enrollment in pending:
        try:
            _activate_enrollment_sync(db, enrollment, course)
            activated += 1
        except Exception as e:
            logger.error(
                "Failed to activate enrollment %s: %s",
                enrollment.id, e, exc_info=True,
            )

    if activated > 0:
        db.commit()

    return activated


def _get_swarm_config_for_course_sync(db: Session, course: Course) -> dict:
    try:
        from app.services.programming_course_service import detect_programming_course as _detect_sync
        profile = _detect_sync(db, course)
        if profile.is_programming_course:
            return get_programming_swarm_config()
    except Exception:
        pass
    return {
        "agents": ["diagnostic_analyzer", "path_planner", "content_recommender", "evaluation_generator"],
        "consensus_voters": ["mastery", "prereq", "sequence", "time"],
        "adaptive_params": {"enabled": True, "replan_threshold": 0.6, "max_replans": 3},
    }


def _activate_enrollment_sync(
    db: Session, enrollment: Enrollment, course: Course, run_swarm: bool = True,
) -> dict[str, Any] | None:
    now = datetime.now(timezone.utc)
    context_key = f"ctx:{enrollment.student_id}:{enrollment.course_id}"

    enrollment.status = EnrollmentStatus.ACTIVO
    enrollment.teacher_id = course.teacher_id
    enrollment.context_key = context_key

    existing_ctx = (
        db.query(EducationalContext)
        .filter(EducationalContext.enrollment_id == enrollment.id)
        .first()
    )
    if existing_ctx:
        existing_ctx.status = EducationalContextStatus.INITIALIZING
        existing_ctx.teacher_id = course.teacher_id
        existing_ctx.activated_at = now
        existing_ctx.shared_memory_key = context_key
        ctx = existing_ctx
    else:
        swarm_config = _get_swarm_config_for_course_sync(db, course)
        ctx = EducationalContext(
            enrollment_id=enrollment.id,
            student_id=enrollment.student_id,
            course_id=enrollment.course_id,
            teacher_id=course.teacher_id,
            status=EducationalContextStatus.INITIALIZING,
            shared_memory_key=context_key,
            activated_at=now,
            swarm_config=swarm_config,
            adaptive_params={"dominant_modality": None, "pace": "moderate", "preferred_bloom_levels": [2, 3, 4]},
        )
        db.add(ctx)
        db.flush()

    emit_event(db, EventType.ENROLLMENT_ACTIVATED, enrollment.id, {
        "enrollment_id": enrollment.id, "student_id": enrollment.student_id,
        "course_id": enrollment.course_id, "teacher_id": course.teacher_id,
        "context_key": context_key, "activated_at": now.isoformat(),
    })
    emit_event(db, EventType.EDUCATIONAL_CONTEXT_ACTIVATED, enrollment.id, {
        "context_key": context_key, "student_id": enrollment.student_id,
        "course_id": enrollment.course_id, "teacher_id": course.teacher_id,
    })

    if run_swarm:
        return activate_enrollment_with_swarm_sync(db, enrollment, course, ctx)
    ctx.status = EducationalContextStatus.ACTIVE
    db.flush()
    return None


def activate_enrollment_with_swarm_sync(
    db: Session,
    enrollment: Enrollment,
    course: Course,
    context: EducationalContext | None = None,
) -> dict[str, Any]:
    if context is None:
        context = (
            db.query(EducationalContext)
            .filter(EducationalContext.enrollment_id == enrollment.id)
            .first()
        )
    if not context:
        return {"ok": False, "error": "EducationalContext not found"}

    enrollment_id = enrollment.id
    logger.info(
        "Sync activation path for enrollment=%s "
        "(legacy — setting ACTIVE directly, no swarm)",
        enrollment_id,
    )
    try:
        context.status = EducationalContextStatus.ACTIVE
        db.flush()
        return {"ok": True, "activation_id": None, "sync_path": True}
    except Exception as e:
        context.status = EducationalContextStatus.FAILED
        context.last_error = str(e)[:500]
        context.activation_attempts = (context.activation_attempts or 0) + 1
        logger.error("Sync activation FAILED for context %s: %s", context.id, e, exc_info=True)
        return {"ok": False, "error": str(e)}


def activate_all_pending_for_student_sync(db: Session, student_id: str) -> int:
    pending = (
        db.query(Enrollment)
        .filter(
            Enrollment.student_id == student_id,
            Enrollment.status == EnrollmentStatus.PENDING_ACTIVATION,
        )
        .all()
    )
    if not pending:
        return 0

    course_ids = [e.course_id for e in pending]
    course_map = {
        c.id: c
        for c in db.query(Course).filter(Course.id.in_(course_ids)).all()
    }

    activated = 0
    for enrollment in pending:
        course = course_map.get(enrollment.course_id)
        if course and course.teacher_id:
            try:
                _activate_enrollment_sync(db, enrollment, course)
                activated += 1
            except Exception as e:
                logger.error("Failed to activate enrollment %s: %s", enrollment.id, e, exc_info=True)
    if activated > 0:
        db.commit()
    return activated


def can_activate(enrollment: Enrollment, course: Course) -> bool:
    return (
        enrollment.status == EnrollmentStatus.PENDING_ACTIVATION
        and course is not None
        and course.teacher_id is not None
    )


# ═════════════════════════════════════════════════════════════════
# Async versions (for async runtime — DB-002 migration)
# ═════════════════════════════════════════════════════════════════


async def _get_swarm_config_for_course(db: AsyncSession, course: Course) -> dict:
    try:
        profile = await detect_programming_course_async(db, course)
        if profile.is_programming_course:
            return get_programming_swarm_config()
    except Exception:
        pass
    return {
        "agents": ["diagnostic_analyzer", "path_planner", "content_recommender", "evaluation_generator"],
        "consensus_voters": ["mastery", "prereq", "sequence", "time"],
        "adaptive_params": {"enabled": True, "replan_threshold": 0.6, "max_replans": 3},
    }


async def _activate_enrollment(
    db: AsyncSession, enrollment: Enrollment, course: Course, run_swarm: bool = True,
) -> dict[str, Any] | None:
    now = datetime.now(timezone.utc)
    context_key = f"ctx:{enrollment.student_id}:{enrollment.course_id}"

    enrollment.status = EnrollmentStatus.ACTIVO
    enrollment.teacher_id = course.teacher_id
    enrollment.context_key = context_key

    result = await db.execute(
        select(EducationalContext).where(EducationalContext.enrollment_id == enrollment.id)
    )
    existing_ctx = result.scalar_one_or_none()
    if existing_ctx:
        existing_ctx.status = EducationalContextStatus.INITIALIZING
        existing_ctx.teacher_id = course.teacher_id
        existing_ctx.activated_at = now
        existing_ctx.shared_memory_key = context_key
        ctx = existing_ctx
    else:
        swarm_config = await _get_swarm_config_for_course(db, course)
        ctx = EducationalContext(
            enrollment_id=enrollment.id,
            student_id=enrollment.student_id,
            course_id=enrollment.course_id,
            teacher_id=course.teacher_id,
            status=EducationalContextStatus.INITIALIZING,
            shared_memory_key=context_key,
            activated_at=now,
            swarm_config=swarm_config,
            adaptive_params={"dominant_modality": None, "pace": "moderate", "preferred_bloom_levels": [2, 3, 4]},
        )
        db.add(ctx)
        await db.flush()

    emit_event(db, EventType.ENROLLMENT_ACTIVATED, enrollment.id, {
        "enrollment_id": enrollment.id, "student_id": enrollment.student_id,
        "course_id": enrollment.course_id, "teacher_id": course.teacher_id,
        "context_key": context_key, "activated_at": now.isoformat(),
    })
    emit_event(db, EventType.EDUCATIONAL_CONTEXT_ACTIVATED, enrollment.id, {
        "context_key": context_key, "student_id": enrollment.student_id,
        "course_id": enrollment.course_id, "teacher_id": course.teacher_id,
    })

    if run_swarm:
        return await activate_enrollment_with_swarm(db, enrollment, course, ctx)
    ctx.status = EducationalContextStatus.ACTIVE
    await db.flush()
    return None


async def activate_enrollment_with_swarm(
    db: AsyncSession,
    enrollment: Enrollment,
    course: Course,
    context: EducationalContext | None = None,
) -> dict[str, Any]:
    if context is None:
        result = await db.execute(
            select(EducationalContext).where(EducationalContext.enrollment_id == enrollment.id)
        )
        context = result.scalar_one_or_none()
    if not context:
        return {"ok": False, "error": "EducationalContext not found"}

    uow = AsyncUnitOfWork(lambda: db)
    orchestrator = SwarmOrchestrator(db, context, uow=uow)

    enrollment_id = enrollment.id
    try:
        async with db.begin_nested():
            result = await orchestrator.activate()
        return result
    except Exception as e:
        context.status = EducationalContextStatus.FAILED
        context.last_error = str(e)[:500]
        context.activation_attempts = (context.activation_attempts or 0) + 1
        logger.error("Swarm activation FAILED for context %s: %s", context.id, e, exc_info=True)
        return {"ok": False, "error": str(e)}


async def activate_enrollments_for_course(db: AsyncSession, course_id: str) -> int:
    result = await db.execute(select(Course).where(Course.id == course_id))
    course = result.scalar_one_or_none()
    if not course or not course.teacher_id:
        return 0

    result = await db.execute(
        select(Enrollment).where(
            Enrollment.course_id == course_id,
            Enrollment.status == EnrollmentStatus.PENDING_ACTIVATION,
        )
    )
    pending = list(result.scalars().all())

    activated = 0
    for enrollment in pending:
        try:
            await _activate_enrollment(db, enrollment, course)
            activated += 1
        except Exception as e:
            logger.error("Failed to activate enrollment %s: %s", enrollment.id, e, exc_info=True)
    if activated > 0:
        await db.commit()
    return activated


async def activate_all_pending_for_student(db: AsyncSession, student_id: str) -> int:
    result = await db.execute(
        select(Enrollment).where(
            Enrollment.student_id == student_id,
            Enrollment.status == EnrollmentStatus.PENDING_ACTIVATION,
        )
    )
    pending = list(result.scalars().all())
    if not pending:
        return 0

    course_ids = [e.course_id for e in pending]
    result = await db.execute(
        select(Course).where(Course.id.in_(course_ids))
    )
    course_map = {c.id: c for c in result.scalars().all()}

    activated = 0
    for enrollment in pending:
        course = course_map.get(enrollment.course_id)
        if course and course.teacher_id:
            try:
                await _activate_enrollment(db, enrollment, course)
                activated += 1
            except Exception as e:
                logger.error("Failed to activate enrollment %s: %s", enrollment.id, e, exc_info=True)
    if activated > 0:
        await db.commit()
    return activated
