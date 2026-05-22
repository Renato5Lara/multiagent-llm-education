"""
Modelo de Recurso educativo.
Archivos subidos por docentes: PDF, video, imágenes, texto, documentos.
"""

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.db.base import Base


class ResourceType(str, enum.Enum):
    """Tipos de recurso permitidos."""
    PDF = "pdf"
    VIDEO = "video"
    IMAGE = "image"
    TEXT = "text"
    DOCUMENT = "document"
    AUDIO = "audio"
    GAME = "game"
    INTERACTIVE = "interactive"


class Resource(Base):
    __tablename__ = "resources"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    course_id = Column(String(36), ForeignKey("courses.id"), nullable=False)
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_path = Column(String(512), nullable=False)
    mime_type = Column(String(100), nullable=False)
    size_bytes = Column(Integer, nullable=False)
    resource_type = Column(
        Enum(ResourceType, name="resourcetype"), nullable=False
    )
    uploaded_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    course = relationship("Course", back_populates="resources")
    objective_associations = relationship(
        "ResourceObjective", back_populates="resource", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Resource {self.original_filename} ({self.resource_type.value})>"
