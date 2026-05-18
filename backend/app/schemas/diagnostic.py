from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class DiagnosticSubmit(BaseModel):
    answers: dict = Field(..., description="Mapa de question_id -> likert_value (1-5)")


class DiagnosticResponse(BaseModel):
    id: str
    student_id: str
    course_id: str
    answers: dict
    profile: Optional[dict] = None
    modality_scores: Optional[dict] = None
    dominant_modality: Optional[str] = None
    completed_at: datetime

    model_config = {"from_attributes": True}


class DiagnosticProfile(BaseModel):
    learning_style: str
    pace: str
    collaboration: str
    motivation: str
    recommendations: list[str]


class StudentProfileCreate(BaseModel):
    preferred_modalities: list[str] = Field(..., description="Lista de modalidades preferidas")
    dominant_style: Optional[str] = None


class StudentProfileResponse(BaseModel):
    id: str
    student_id: str
    preferred_modalities: list[str]
    dominant_style: Optional[str] = None
    updated_at: datetime

    model_config = {"from_attributes": True}
