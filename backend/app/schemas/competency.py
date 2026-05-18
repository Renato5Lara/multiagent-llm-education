"""
Schemas Pydantic para competencias.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.models.competency import CompetencyType


class CompetencyBase(BaseModel):
    name: str = Field(..., max_length=255)
    description: Optional[str] = None
    competency_type: CompetencyType
    cycle: Optional[int] = None


class CompetencyCreate(CompetencyBase):
    pass


class CompetencyResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    competency_type: CompetencyType
    cycle: Optional[int] = None
    active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class CompetencyListResponse(BaseModel):
    competencies: list[CompetencyResponse]
    total: int


class CourseCompetencyAssign(BaseModel):
    competency_ids: list[str] = Field(..., min_length=1)


class CourseWithCompetenciesResponse(BaseModel):
    id: str
    code: str
    name: str
    description: Optional[str] = None
    cycle: int
    year: int
    status: str
    teacher_id: str
    created_at: datetime
    updated_at: datetime
    competencies: list[CompetencyResponse] = []

    model_config = {"from_attributes": True}
