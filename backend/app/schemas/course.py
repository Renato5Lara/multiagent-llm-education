"""
Schemas Pydantic para cursos.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.models.course import CourseStatus


class CourseBase(BaseModel):
    """Campos base de curso."""
    code: str = Field(..., max_length=50, description="Código del curso")
    name: str = Field(..., min_length=1, max_length=255, description="Nombre")
    description: Optional[str] = Field(None, description="Descripción")
    cycle: str = Field(..., max_length=20, description="Ciclo académico, ej: 2026-I")
    year: int = Field(..., ge=2020, le=2100, description="Año académico")


class CourseCreate(CourseBase):
    """Schema para crear curso."""
    pass


class CourseUpdate(BaseModel):
    """Schema para actualizar curso. Todos opcionales."""
    code: Optional[str] = Field(None, max_length=50)
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    cycle: Optional[str] = Field(None, max_length=20)
    year: Optional[int] = Field(None, ge=2020, le=2100)


class CourseResponse(BaseModel):
    """Respuesta de curso."""
    id: str
    code: str
    name: str
    description: Optional[str] = None
    cycle: str
    year: int
    status: CourseStatus
    teacher_id: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CourseListResponse(BaseModel):
    """Lista paginada de cursos."""
    courses: list[CourseResponse]
    total: int
    page: int
    size: int


class EnrollRequest(BaseModel):
    """Solicitud de inscripción en lote."""
    student_ids: list[str] = Field(
        ..., min_length=1, description="Lista de IDs de estudiantes"
    )
