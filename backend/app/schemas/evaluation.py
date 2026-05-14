from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class EvaluationSubmit(BaseModel):
    answers: dict = Field(..., description="Mapa de question_index -> selected_answer")


class EvaluationResponse(BaseModel):
    id: str
    student_id: str
    course_id: str
    module_id: Optional[str] = None
    score: Optional[float] = None
    max_score: int
    passed: int
    attempted_at: datetime
    completed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
