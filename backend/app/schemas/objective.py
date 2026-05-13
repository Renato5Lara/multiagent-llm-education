"""
Schemas Pydantic para objetivos de aprendizaje.
"""

from typing import Optional

from pydantic import BaseModel, Field


class ObjectiveBase(BaseModel):
    """Campos base de objetivo."""
    title: str = Field(..., min_length=1, max_length=255, description="Título")
    description: Optional[str] = Field(None, description="Descripción")
    bloom_level: int = Field(..., ge=1, le=6, description="Nivel de Bloom (1-6)")
    order: int = Field(0, ge=0, description="Orden de presentación")


class ObjectiveCreate(ObjectiveBase):
    """Schema para crear objetivo."""
    pass


class ObjectiveUpdate(BaseModel):
    """Schema para actualizar objetivo. Todos opcionales."""
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    bloom_level: Optional[int] = Field(None, ge=1, le=6)
    order: Optional[int] = Field(None, ge=0)


class ObjectiveResponse(ObjectiveBase):
    """Respuesta de objetivo."""
    id: str
    course_id: str

    model_config = {"from_attributes": True}
