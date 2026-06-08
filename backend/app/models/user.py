"""
Modelo de Usuario.
Soporta roles: admin, docente, estudiante, investigador.
"""

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, Enum, Integer, String
from sqlalchemy.orm import relationship

from app.db.base import Base


class UserRole(str, enum.Enum):
    """Roles disponibles en el sistema."""
    ADMIN = "admin"
    DOCENTE = "docente"
    ESTUDIANTE = "estudiante"
    INVESTIGADOR = "investigador"


class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    role = Column(Enum(UserRole, name="userrole", use_enum_values=True, values_callable=lambda x: [e.value for e in x]), nullable=False)
    institutional_code = Column(String(50), nullable=True)
    area = Column(String(100), nullable=True)
    current_cycle = Column(Integer, nullable=True)
    token_version = Column(Integer, default=1, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    courses_taught = relationship("Course", back_populates="teacher", lazy="select")
    enrollments = relationship("Enrollment", back_populates="student", lazy="select", foreign_keys="Enrollment.student_id")
    audit_logs = relationship("AuditLog", back_populates="user", lazy="select")
    student_profile = relationship("StudentProfile", back_populates="student", uselist=False, lazy="select")
    teacher_assignments = relationship("TeacherAssignment", back_populates="teacher", lazy="select")

    def __repr__(self) -> str:
        return f"<User {self.email} ({self.role.value})>"
