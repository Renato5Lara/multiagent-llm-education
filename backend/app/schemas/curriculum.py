from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class InstitutionalCourseResponse(BaseModel):
    id: str
    code: str
    name: str
    credits: int
    cycle: int
    hours_theory: Optional[int] = None
    hours_practice: Optional[int] = None
    hours_lab: Optional[int] = None
    competencies: Optional[str] = None
    created_at: datetime
    prerequisite_codes: list[str] = []

    model_config = {"from_attributes": True}


class TeacherAssignmentResponse(BaseModel):
    id: str
    teacher_id: str
    institutional_course_id: str
    created_at: datetime
    course: Optional[InstitutionalCourseResponse] = None

    model_config = {"from_attributes": True}


class TeacherAssignmentCreate(BaseModel):
    institutional_course_id: str = Field(..., description="ID del curso institucional a asignar")


class CycleResponse(BaseModel):
    cycle: int
    total_courses: int
    courses: list[InstitutionalCourseResponse]
