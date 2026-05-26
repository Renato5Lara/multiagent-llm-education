import json
import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.db.uow import UnitOfWork
from app.models.course import Course
from app.models.diagnostic_result import DiagnosticResult
from app.models.enrollment import Enrollment, EnrollmentStatus
from app.models.student_memory import StudentMemory, ConversationMessage, WeaknessRecord, StrengthRecord
from app.models.student_progress import StudentProgress
from app.models.resource import Resource
from app.models.user import User
from app.services.prerequisite_service import predict_student_risk, get_student_strengths

logger = logging.getLogger(__name__)


def store_memory(
    uow: UnitOfWork,
    student_id: str,
    memory_type: str,
    key: str,
    value: str,
    score: Optional[float] = None,
    metadata_json: Optional[dict] = None,
):
    from app.db.locks import advisory_lock
    from sqlalchemy.exc import IntegrityError

    db = uow.db
    lock_key = f"memory:{student_id}:{memory_type}:{key}"

    with advisory_lock(db, lock_key):
        existing = (
            db.query(StudentMemory)
            .filter(
                StudentMemory.student_id == student_id,
                StudentMemory.memory_type == memory_type,
                StudentMemory.key == key,
            )
            .first()
        )
        if existing:
            existing.value = value
            existing.score = score
            existing.metadata_json = metadata_json
            existing.updated_at = datetime.now(timezone.utc)
            return existing

        # Use savepoint to isolate the INSERT from the parent TX.
        # If a concurrent request inserted first (IntegrityError),
        # the savepoint rolls back — the parent TX is untouched.
        try:
            with db.begin_nested():
                memory = StudentMemory(
                    student_id=student_id,
                    memory_type=memory_type,
                    key=key,
                    value=value,
                    score=score,
                    metadata_json=metadata_json,
                )
                db.add(memory)
                uow.flush()
        except IntegrityError:
            logger.warning(
                "Memory race: %s — re-reading after rollback", lock_key,
            )
            existing = (
                db.query(StudentMemory)
                .filter(
                    StudentMemory.student_id == student_id,
                    StudentMemory.memory_type == memory_type,
                    StudentMemory.key == key,
                )
                .with_for_update()
                .first()
            )
            if existing:
                existing.value = value
                existing.score = score
                existing.metadata_json = metadata_json
                existing.updated_at = datetime.now(timezone.utc)
                return existing
            raise
    return memory


def get_memory(db: Session, student_id: str, memory_type: str, key: str) -> Optional[StudentMemory]:
    return (
        db.query(StudentMemory)
        .filter(
            StudentMemory.student_id == student_id,
            StudentMemory.memory_type == memory_type,
            StudentMemory.key == key,
        )
        .first()
    )


def get_all_memories(db: Session, student_id: str, memory_type: Optional[str] = None) -> list[StudentMemory]:
    query = db.query(StudentMemory).filter(StudentMemory.student_id == student_id)
    if memory_type:
        query = query.filter(StudentMemory.memory_type == memory_type)
    return query.order_by(StudentMemory.updated_at.desc()).all()


def save_conversation_message(uow: UnitOfWork, student_id: str, course_id: Optional[str], role: str, content: str, metadata_json: Optional[dict] = None) -> ConversationMessage:
    db = uow.db
    msg = ConversationMessage(
        student_id=student_id,
        course_id=course_id,
        role=role,
        content=content,
        metadata_json=metadata_json,
    )
    db.add(msg)
    uow.flush()
    return msg


def get_conversation_history(db: Session, student_id: str, course_id: Optional[str] = None, limit: int = 20) -> list[ConversationMessage]:
    query = db.query(ConversationMessage).filter(ConversationMessage.student_id == student_id)
    if course_id:
        query = query.filter(ConversationMessage.course_id == course_id)
    return query.order_by(ConversationMessage.created_at.desc()).limit(limit).all()


def track_weakness(uow: UnitOfWork, student_id: str, topic: str, description: str, bloom_level: Optional[int] = None):
    db = uow.db
    existing = (
        db.query(WeaknessRecord)
        .filter(
            WeaknessRecord.student_id == student_id,
            WeaknessRecord.topic == topic,
            WeaknessRecord.resolved == False,
        )
        .first()
    )
    if existing:
        existing.detection_count = (existing.detection_count or 1) + 1
        existing.last_detected_at = datetime.now(timezone.utc)
        if bloom_level:
            existing.bloom_level = bloom_level
    else:
        record = WeaknessRecord(
            student_id=student_id,
            topic=topic,
            description=description,
            bloom_level=bloom_level,
        )
        db.add(record)
    uow.flush()


def resolve_weakness(uow: UnitOfWork, weakness_id: str) -> Optional[WeaknessRecord]:
    db = uow.db
    weakness = db.query(WeaknessRecord).filter(WeaknessRecord.id == weakness_id).first()
    if not weakness:
        return None
    weakness.resolved = True
    uow.flush()
    return weakness


def track_strength(uow: UnitOfWork, student_id: str, topic: str, description: str, bloom_level: Optional[int] = None):
    db = uow.db
    existing = (
        db.query(StrengthRecord)
        .filter(
            StrengthRecord.student_id == student_id,
            StrengthRecord.topic == topic,
        )
        .first()
    )
    if not existing:
        record = StrengthRecord(
            student_id=student_id,
            topic=topic,
            description=description,
            bloom_level=bloom_level,
        )
        db.add(record)
        uow.flush()


def get_active_weaknesses(db: Session, student_id: str) -> list[WeaknessRecord]:
    return (
        db.query(WeaknessRecord)
        .filter(
            WeaknessRecord.student_id == student_id,
            WeaknessRecord.resolved == False,
        )
        .order_by(WeaknessRecord.detection_count.desc())
        .all()
    )


def get_strengths(db: Session, student_id: str) -> list[StrengthRecord]:
    return (
        db.query(StrengthRecord)
        .filter(StrengthRecord.student_id == student_id)
        .order_by(StrengthRecord.created_at.desc())
        .all()
    )


def build_tutor_context(db: Session, student: User, course_id: Optional[str] = None) -> dict:
    context = {
        "student_name": student.first_name,
        "current_cycle": student.current_cycle,
        "weaknesses": [],
        "strengths": [],
        "recent_topics": [],
        "risk_status": None,
        "conversation_history": [],
        "course_context": None,
    }

    weaknesses = get_active_weaknesses(db, student.id)
    context["weaknesses"] = [
        {"topic": w.topic, "description": w.description, "count": w.detection_count, "bloom_level": w.bloom_level}
        for w in weaknesses
    ]

    strengths = get_strengths(db, student.id)
    context["strengths"] = [
        {"topic": s.topic, "description": s.description, "bloom_level": s.bloom_level}
        for s in strengths
    ]

    recent = (
        db.query(ConversationMessage)
        .filter(ConversationMessage.student_id == student.id)
        .order_by(ConversationMessage.created_at.desc())
        .limit(10)
        .all()
    )
    context["conversation_history"] = [
        {"role": m.role, "content": m.content[:200], "time": m.created_at.isoformat()}
        for m in reversed(recent)
    ]

    try:
        risk = predict_student_risk(db, student)
        context["risk_status"] = risk.get("risk_level")
    except Exception as e:
        logger.warning(f"Could not predict student risk: {e}")

    if course_id:
        course = db.query(Course).filter(Course.id == course_id).first()
        if course:
            progress_data = _get_course_progress_summary(db, student.id, course_id)
            context["course_context"] = {
                "course_name": course.name,
                "course_code": course.code,
                "cycle": course.cycle,
                **progress_data,
            }

    return context


def _get_course_progress_summary(db: Session, student_id: str, course_id: str) -> dict:
    total_resources = db.query(Resource).filter(Resource.course_id == course_id).count()
    completed = (
        db.query(StudentProgress)
        .filter(
            StudentProgress.student_id == student_id,
            StudentProgress.course_id == course_id,
            StudentProgress.completed == True,
        )
        .count()
    )
    progress_pct = round((completed / total_resources) * 100) if total_resources > 0 else 0

    diagnostic = (
        db.query(DiagnosticResult)
        .filter(
            DiagnosticResult.student_id == student_id,
            DiagnosticResult.course_id == course_id,
        )
        .first()
    )

    return {
        "progress_percentage": progress_pct,
        "completed_resources": completed,
        "total_resources": total_resources,
        "has_diagnostic": diagnostic is not None,
        "dominant_modality": diagnostic.dominant_modality if diagnostic else None,
    }


def get_memory_summary(db: Session, student_id: str) -> dict:
    weaknesses = get_active_weaknesses(db, student_id)
    strengths = get_strengths(db, student_id)
    memories = get_all_memories(db, student_id)

    memory_dict = {}
    for m in memories:
        memory_dict[m.key] = {"value": m.value, "score": m.score, "type": m.memory_type}

    return {
        "weaknesses": [
            {"topic": w.topic, "count": w.detection_count, "bloom_level": w.bloom_level}
            for w in weaknesses
        ],
        "strengths": [
            {"topic": s.topic, "bloom_level": s.bloom_level}
            for s in strengths
        ],
        "persistent_memories": memory_dict,
    }
