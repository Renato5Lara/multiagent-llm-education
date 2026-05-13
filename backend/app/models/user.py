"""
Modelo de Usuario.
Soporta roles: admin, docente, estudiante, investigador.
"""

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, Enum, String
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
    role = Column(Enum(UserRole, name="userrole"), nullable=False)
    institutional_code = Column(String(50), nullable=True)
    area = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relaciones
    courses_taught = relationship("Course", back_populates="teacher", lazy="selectin")
    enrollments = relationship("Enrollment", back_populates="student", lazy="selectin")
    audit_logs = relationship("AuditLog", back_populates="user", lazy="selectin")

    def __repr__(self) -> str:
        return f"<User {self.email} ({self.role.value})>"
