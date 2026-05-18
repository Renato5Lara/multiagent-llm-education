from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class PathModuleResponse(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    order: int
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
