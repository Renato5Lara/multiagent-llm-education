"""
Pydantic schemas for the weekly learning API.
"""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class CreatePlanRequest(BaseModel):
    thematic_line: str = Field(..., min_length=3, max_length=500, description="Línea temática del curso")
    objectives: list[str] = Field(..., min_length=1, max_length=10, description="Objetivos del curso")
    pedagogical_intention: str = Field(..., min_length=10, max_length=3000, description="Intención pedagógica")
    total_weeks: int = Field(default=5, ge=1, le=32, description="Número de semanas")


class WeekSummary(BaseModel):
    id: str
    week_number: int
    theme: str
    bloom_target: int
    bloom_label: str
    objectives: list[str]
    orchestration_status: str
    confidence: Optional[float] = None
    generated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class PlanResponse(BaseModel):
    id: str
    course_id: str
    teacher_id: str
    total_weeks: int
    thematic_line: str
    pedagogical_intention: str
    bloom_progression: list[int]
    week_themes: list[str]
    status: str
    weeks: list[WeekSummary]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PedagogicalStageItem(BaseModel):
    phase: str
    focus: str
    bloom_level: int
    content: str
    examples: list[str] = []


class MisconceptionItemSchema(BaseModel):
    misconception: str
    correction: str
    severity: str = "medium"


class MultimodalPromptSchema(BaseModel):
    modality: str
    prompt: str
    enabled: bool = True


class WeekContentResponse(BaseModel):
    id: str
    week_id: str
    introduction: str
    pedagogical_explanation: str
    examples: list[str]
    guided_practice: str
    storyboard: Optional[str] = None
    continuity_notes: Optional[str] = None
    pedagogical_stages: list[PedagogicalStageItem]
    retrieval_evidence: dict[str, Any]
    swarm_trace: dict[str, Any]
    created_at: datetime

    model_config = {"from_attributes": True}


class WeekDetailResponse(BaseModel):
    id: str
    week_number: int
    plan_id: str
    theme: str
    bloom_target: int
    bloom_label: str
    objectives: list[str]
    misconceptions: list[MisconceptionItemSchema]
    real_applications: list[str]
    recommended_modality: Optional[str] = None
    multimodal_prompts: list[MultimodalPromptSchema]
    evaluation_criteria: list[str]
    orchestration_status: str
    confidence: Optional[float] = None
    content: Optional[WeekContentResponse] = None
    generated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ValidationIssue(BaseModel):
    type: str
    severity: str
    message: str


class PlanValidationResponse(BaseModel):
    valid: bool
    issues: list[ValidationIssue]
    health_score: float


class StructureTemplateResponse(BaseModel):
    total_weeks: int
    name: str


class StructureTemplatesResponse(BaseModel):
    templates: list[StructureTemplateResponse]
