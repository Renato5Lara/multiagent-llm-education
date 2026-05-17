from typing import Optional

from pydantic import BaseModel, Field


class DiagnosticAnswers(BaseModel):
    answers: dict[int, int] = Field(..., description="question_id -> likert_value")


class LearningProfile(BaseModel):
    learning_style: str = Field(..., description="visual/auditory/reading/kinesthetic")
    pace: str = Field(..., description="slow/moderate/fast")
    collaboration: str = Field(..., description="solo/group/mixed")
    motivation: str = Field(..., description="challenge/practical/theory")
    preferred_bloom_levels: list[int] = Field(
        ..., description="Preferred Bloom levels based on profile"
    )
    preferred_modalities: list[str] = Field(
        default=["visual", "reading"],
        description="Preferred content modalities: video, audio, visual, reading, game, kinesthetic, interactive",
    )


class ModulePlan(BaseModel):
    title: str
    description: str
    order: int
    bloom_level: int
    recommended_resource_types: list[str] = []
    estimated_duration: str = ""


class LearningPathPlan(BaseModel):
    modules: list[ModulePlan]


class EvaluationQuestion(BaseModel):
    question: str
    options: list[str]
    correct: int


class EvaluationPlan(BaseModel):
    module_title: str
    questions: list[EvaluationQuestion]
    passing_score: float = 0.6
