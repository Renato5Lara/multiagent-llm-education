from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class WeeklyPedagogicalPlanCreate(BaseModel):
    week_number: int = Field(..., ge=1, le=32)
    topic: str = Field(..., min_length=3, max_length=255)
    objectives: list[str] = Field(..., min_length=1, max_length=8)
    bloom_target: int = Field(..., ge=1, le=6)
    pedagogical_style: str = Field(..., min_length=2, max_length=80)
    pedagogical_intention: str = Field(..., min_length=8, max_length=2000)
    preferred_modality: str = Field(..., min_length=2, max_length=80)


class WeeklyPedagogicalPlanResponse(BaseModel):
    id: str
    course_id: str
    teacher_id: str
    week_number: int
    topic: str
    objectives: list[str]
    bloom_target: int
    pedagogical_style: str
    pedagogical_intention: str
    preferred_modality: str
    orchestration_status: str
    retrieval_summary: dict[str, Any]
    pedagogical_structure: dict[str, Any]
    adaptive_plan: dict[str, Any]
    multimodal_plan: dict[str, Any]
    prompt_plan: dict[str, Any]
    consistency_validation: dict[str, Any]
    consensus_result: dict[str, Any]
    generated_at: datetime
    validated_at: datetime | None = None

    model_config = {"from_attributes": True}
