"""Schemas del instrumento experimental de conocimiento (pre/post-test)."""

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


class KnowledgeTestStartRequest(BaseModel):
    kind: Literal["pre", "post"] = Field(..., description="Tipo de test: pre o post")


class KnowledgeTestQuestionOut(BaseModel):
    """Pregunta servida al estudiante — nunca incluye la respuesta correcta."""

    id: str
    module_number: int
    topic: str
    text: str
    options: list[str]
    difficulty: str


class KnowledgeTestStartResponse(BaseModel):
    attempt_id: str
    kind: str
    status: str
    started_at: datetime
    total_questions: int
    resumed: bool
    questions: list[KnowledgeTestQuestionOut]


class KnowledgeTestSubmit(BaseModel):
    answers: dict[str, int] = Field(
        ..., description="Mapa de question_id -> índice de opción seleccionada (0-3)"
    )


class KnowledgeTestResultOut(BaseModel):
    attempt_id: str
    kind: str
    status: str
    score: Optional[int] = None
    total_questions: Optional[int] = None
    percentage: Optional[float] = None
    level: Optional[str] = None
    level_label: Optional[str] = None
    duration_seconds: Optional[int] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    module_breakdown: Optional[dict] = None
    mastered_modules: list[int] = []
    critical_modules: list[int] = []
    # Dimensión cognitiva: perfil por competencia + prioridad adaptativa.
    # None cuando el banco no tiene competencias (legacy).
    competency_profile: Optional[dict] = None


class KnowledgeTestStatusOut(BaseModel):
    bank_available: bool
    pretest_required: bool
    has_learning_path: bool
    pretest: Optional[dict] = None
    posttest: Optional[dict] = None


class ExperimentComparisonOut(BaseModel):
    student_id: str
    course_id: str
    pre_percentage: float
    post_percentage: float
    absolute_gain: float
    percent_gain: Optional[float] = None
    normalized_gain: Optional[float] = None
    pre_level: str
    post_level: str
    pre_duration_seconds: Optional[int] = None
    post_duration_seconds: Optional[int] = None
    group_label: str
    computed_at: datetime
