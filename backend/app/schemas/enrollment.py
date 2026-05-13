"""
Schemas Pydantic para inscripciones.
"""

from datetime import datetime

from pydantic import BaseModel

from app.models.enrollment import EnrollmentStatus


class EnrollmentResponse(BaseModel):
    """Respuesta de inscripción."""
    id: str
    course_id: str
    student_id: str
    enrolled_at: datetime
    status: EnrollmentStatus

    model_config = {"from_attributes": True}
