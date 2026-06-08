from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class PathModuleResponse(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    order: int
    week_number: Optional[int] = None
    status: str
    bloom_level: Optional[int] = None
    resource_id: Optional[str] = None
    score: Optional[float] = None
    completed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class LearningPathResponse(BaseModel):
    id: str
    student_id: str
    course_id: str
    total_modules: int
    completed_modules: int
    status: str
    modules: list[PathModuleResponse]

    model_config = {"from_attributes": True}


class ModuleUpdate(BaseModel):
    status: str
    score: Optional[float] = None


class StudentProgressCreate(BaseModel):
    resource_id: Optional[str] = None
    progress_percentage: Optional[int] = None


class StudentProgressResponse(BaseModel):
    id: str
    student_id: str
    course_id: str
    resource_id: Optional[str] = None
    completed: bool
    completed_at: Optional[datetime] = None
    progress_percentage: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CourseProgressResponse(BaseModel):
    course_id: str
    course_name: str
    course_code: str
    cycle: int
    total_resources: int
    completed_resources: int
    progress_percentage: int
    has_diagnostic: bool
    has_learning_path: bool
    dominant_modality: Optional[str] = None


class LearningPathItem(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    order: int
    status: str
    resource_id: Optional[str] = None
    resource_type: Optional[str] = None
    competencies: list[str] = []


class LearningPathDetailResponse(BaseModel):
    course_id: str
    course_name: str
    dominant_modality: Optional[str] = None
    preferred_modalities: list[str] = []
    items: list[LearningPathItem]


class PedagogicalStage(BaseModel):
    phase: str
    focus: str
    bloom_level: int
    content: str
    examples: list[str] = []


class MisconceptionItem(BaseModel):
    misconception: str
    correction: str
    severity: str = "medium"


class MultimodalPrompt(BaseModel):
    modality: str
    prompt: str
    enabled: bool = True


class ModuleOrchestrationResponse(BaseModel):
    module_id: str
    module_title: str
    course_id: str
    course_name: str
    orchestration_status: str
    introduction: str
    pedagogical_explanation: str
    misconceptions: list[MisconceptionItem]
    examples: list[str]
    real_applications: list[str]
    guided_practice: str
    pedagogical_stages: list[PedagogicalStage]
    multimodal_prompts: list[MultimodalPrompt]
    storyboard: str
    continuity_notes: str
    bloom_progression: list[dict]
    retrieval_evidence: dict
    confidence: float
    generated_at: str
