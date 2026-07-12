from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.schemas.concept_block import ConceptBlock  # Sprint L1


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
    # Marca (server-side) cuál de los cursos matriculados es la experiencia activa,
    # para que el frontend nunca tenga que buscar por código (IS301) ni por "curso".
    is_active_experience: bool = False


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
    session_id: Optional[str] = None
    # Sprint L1 — enriched per-concept blocks; empty list on legacy/degraded responses
    concept_blocks: list[ConceptBlock] = []
    # Misión Activa — continuidad: True si la adaptación fue releída (no regenerada)
    resumed: bool = False
    # Posición persistida del recorrido: {current_index, completed_step_ids, total_xp}
    mission_cursor: Optional[dict] = None
    # Épica 2 (RFC-0010 S1): la decisión completa del runtime que informó
    # bloom_target/modalidad — incluye alternativas_descartadas, para que
    # Modo Evidencia "enseñe el vocabulario, no lo esconda" (RFC-0010
    # regla 2). None si no hubo decisión aplicable (o resultado degradado).
    runtime_decision: Optional[dict] = None


class MissionProgressUpdate(BaseModel):
    """Cursor de la Misión Activa: dónde va el estudiante dentro de su recorrido."""
    current_index: int = 0
    completed_step_ids: list[str] = []
    total_xp: int = 0
