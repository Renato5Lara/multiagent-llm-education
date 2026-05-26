import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, JSON, String, Text, Boolean, UniqueConstraint
from sqlalchemy.orm import relationship

from app.db.base import Base


class StudentMemory(Base):
    __tablename__ = "student_memories"
    __table_args__ = (
        UniqueConstraint("student_id", "memory_type", "key", name="uq_student_memory_type_key"),
    )

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    student_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    memory_type = Column(String(50), nullable=False, index=True)
    key = Column(String(255), nullable=False)
    value = Column(Text, nullable=True)
    score = Column(Float, nullable=True)
    metadata_json = Column(JSON, nullable=True)
    version = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    student = relationship("User", backref="academic_memories")


class ConversationMessage(Base):
    __tablename__ = "conversation_messages"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    student_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    course_id = Column(String(36), ForeignKey("courses.id"), nullable=True, index=True)
    role = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)
    metadata_json = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    student = relationship("User", backref="conversations")
    course = relationship("Course")


class WeaknessRecord(Base):
    __tablename__ = "weakness_records"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    student_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    topic = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    bloom_level = Column(Integer, nullable=True)
    detection_count = Column(Integer, default=1, nullable=False)
    last_detected_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    resolved = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    student = relationship("User", backref="weakness_records")


class StrengthRecord(Base):
    __tablename__ = "strength_records"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    student_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    topic = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    bloom_level = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    student = relationship("User", backref="strength_records")
