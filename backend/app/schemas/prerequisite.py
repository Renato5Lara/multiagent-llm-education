from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class CoursePrerequisiteCreate(BaseModel):
    course_id: str = Field(..., description="ID del curso que requiere prerrequisito")
    prerequisite_course_id: str = Field(..., description="ID del curso prerrequisito")


class CoursePrerequisiteResponse(BaseModel):
    id: str
    course_id: str
    prerequisite_course_id: str
    prerequisite_course_code: Optional[str] = None
    prerequisite_course_name: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class CourseAccessStatus(BaseModel):
    course_id: str
    course_code: str
    course_name: str
    is_unlocked: bool
    prerequisites_met: bool
    missing_prerequisites: list[dict] = []
    completed_prerequisites: list[dict] = []
    reason: Optional[str] = None


class StudentRiskPrediction(BaseModel):
    risk_level: str
    risk_score: float
    explanation: str
    factors: list[str] = []
    recommendations: list[str] = []


class CourseAnalytics(BaseModel):
    course_id: str
    course_name: str
    enrolled_count: int
    avg_progress: float
    at_risk_count: int
    difficult_topics: list[str] = []
    competency_gaps: list[str] = []
    recommendation: Optional[str] = None


class IAAnalyticsResponse(BaseModel):
    student_risk: Optional[StudentRiskPrediction] = None
    course_analytics: list[CourseAnalytics] = []
    next_recommended_course: Optional[dict] = None
    strengths: list[str] = []
    warnings: list[str] = []
