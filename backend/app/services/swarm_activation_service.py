import json
import logging
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.uow import AsyncUnitOfWork
from app.models.educational_context import EducationalContext, EducationalContextStatus
from app.models.enrollment import Enrollment
from app.events.types import emit_event, EventType

logger = logging.getLogger(__name__)


async def initialize_swarm_context(db: AsyncSession, ctx: EducationalContext) -> dict:
    try:
        from app.memory.shared_memory import SharedMemoryStore

        uow = AsyncUnitOfWork(lambda: db)
        memory = SharedMemoryStore(uow)

        memory_key = ctx.shared_memory_key

        await memory.publish_observation(
            voter_name="system",
            key=f"{memory_key}:swarm:initialized",
            value={
                "context_id": ctx.id,
                "student_id": ctx.student_id,
                "course_id": ctx.course_id,
                "teacher_id": ctx.teacher_id,
                "agents": ctx.swarm_config.get("agents", []),
                "voters": ctx.swarm_config.get("consensus_voters", []),
                "adaptive": ctx.swarm_config.get("adaptive_params", {}),
                "initialized_at": datetime.now(timezone.utc).isoformat(),
            },
            confidence=1.0,
            memory_type="signal",
        )

        await memory.publish_observation(
            voter_name="system",
            key=f"{memory_key}:student:baseline",
            value={
                "status": "onboarded",
                "requires_diagnostic": True,
                "requires_profile": True,
                "adaptive_ready": False,
            },
            confidence=1.0,
            memory_type="observation",
        )

        await db.flush()

        emit_event(db, EventType.SWARM_INITIALIZED, ctx.id, {
            "context_id": ctx.id,
            "shared_memory_key": memory_key,
            "student_id": ctx.student_id,
            "course_id": ctx.course_id,
        })

        logger.info(
            "Swarm context initialized for student=%s course=%s key=%s",
            ctx.student_id, ctx.course_id, memory_key,
        )

        return {"status": "initialized", "memory_key": memory_key}

    except Exception as e:
        ctx.status = EducationalContextStatus.FAILED
        ctx.activation_attempts = (ctx.activation_attempts or 0) + 1
        ctx.last_error = str(e)[:500]
        await db.flush()
        logger.error(
            "Swarm context initialization FAILED for context %s: %s",
            ctx.id, e, exc_info=True,
        )
        return {"status": "failed", "error": str(e)[:200]}
