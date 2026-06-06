class EventType:
    USER_REGISTERED = "user.registered"
    STUDENT_CYCLE_ASSIGNED = "student.cycle_assigned"

    ENROLLMENT_CREATED = "enrollment.created"
    ENROLLMENT_ACTIVATED = "enrollment.activated"
    ENROLLMENT_COMPLETED = "enrollment.completed"
    ENROLLMENT_SUSPENDED = "enrollment.suspended"

    COURSE_CREATED = "course.created"
    COURSE_TEACHER_ASSIGNED = "course.teacher_assigned"
    COURSE_PUBLISHED = "course.published"

    EDUCATIONAL_CONTEXT_ACTIVATED = "educational_context.activated"
    EDUCATIONAL_CONTEXT_SUSPENDED = "educational_context.suspended"
    EDUCATIONAL_CONTEXT_ARCHIVED = "educational_context.archived"

    SWARM_INITIALIZED = "swarm.initialized"


def emit_event(db, event_type: str, aggregate_id: str, payload: dict | None = None):
    from app.models.event_outbox import EventOutbox
    import uuid
    from datetime import datetime, timezone

    event = EventOutbox(
        event_type=event_type,
        aggregate_id=aggregate_id,
        correlation_id=str(uuid.uuid4()),
        payload=payload or {},
    )
    db.add(event)
    return event
