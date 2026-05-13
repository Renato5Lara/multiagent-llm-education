"""
Schemas Pydantic para recursos educativos.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.models.resource import ResourceType


class ResourceResponse(BaseModel):
    """Respuesta de recurso."""
    id: str
    course_id: str
    filename: str
    original_filename: str
    mime_type: str
    size_bytes: int
    resource_type: ResourceType
    uploaded_at: datetime

    model_config = {"from_attributes": True}


class ResourceObjectiveAssociation(BaseModel):
    """Asociación de recurso con objetivos."""
    objective_ids: list[str] = Field(
        ..., min_length=1, description="Lista de IDs de objetivos"
    )
    relevance_score: float = Field(1.0, ge=0.0, le=1.0)
