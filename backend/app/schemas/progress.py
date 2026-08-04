from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

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
    # Fase de cierre del producto (jul 2026) — bug real encontrado en la
    # verificación de preparación experimental: el flujo continuo de ciclos
    # (ModuleExperienceView) nunca abría un LearningSession, así que
    # `duration_minutes` quedaba en 0 para el 100% de los estudiantes reales.
    # El cliente sí conoce el tiempo real transcurrido (desde que se montó
    # el módulo); se envía explícito en vez de intentar reconstruirlo aquí.
    duration_minutes: Optional[float] = None


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
    # Distingue, dentro de los ítems `status="available"`, cuál es el
    # frente de trabajo real (a dónde debe navegar el estudiante) de los
    # que están disponibles por ya estar dominados y ser saltables.
    # Corrección de adaptación por nivel (auditoría causal, ago. 2026).
    is_frontier: bool = False
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


class CycleEvidenceSubmit(BaseModel):
    """Evidencia real de haber resuelto la práctica de UN ciclo de aprendizaje
    (ModuleExperienceView) — traducción fiel de intentos a items, mismo
    patrón que ya usa `_registrar_diagnostico_en_runtime` para el Likert del
    diagnóstico: cada intento es un item; los intentos antes de resolver
    (o todos, si se reveló la solución) son incorrectos."""
    course_id: str
    competencia: str
    attempts: int = Field(..., ge=1)
    solved: bool
    hints_used: int | None = Field(None, ge=0)
    time_ms: int | None = Field(None, ge=0)
    #: Memoria del Ciclo activo (Documento 6 §1, Arquitectura Pedagógica) —
    #: formas del catálogo de PP4 ya mostradas en este mismo ciclo, para que
    #: seleccionar_forma() no repita contenido ya visto (Adenda A). Nunca
    #: información del runtime — viene del frontend, distinta procedencia
    #: que `diseno.alternativas_descartadas`.
    formas_ya_mostradas: list[str] = Field(default_factory=list)


class ConsentResponseSubmit(BaseModel):
    """Adenda B (Semántica del Rechazo, Documento 5 §4.1 — Arquitectura
    Pedagógica v1.0): respuesta del estudiante a una forma "con
    consentimiento" ofrecida por el sistema (`categoria_consentimiento`
    de `seleccionar_forma()`, Adenda A). Contrato puro de registro —
    nunca produce un fact/claim del runtime (NOTA-INTERACCION-
    CONSENTIMIENTO.md §3, punto 2 de Adenda B: tratar el rechazo como
    evidencia formal excede esta pieza, exigiría RFC sobre
    backend/runtime/). Gobierna únicamente ofertas proactivas del
    sistema — nunca solicitudes voluntarias del estudiante (botón Ayuda,
    NOTA §7), que no pasan por este contrato."""
    course_id: str
    competencia: str
    #: Forma del catálogo de PP4 que se ofreció (p. ej. "codigo_guiado",
    #: "narracion_tutor") — la que `seleccionar_forma()` ya devolvió con
    #: categoria_consentimiento="consentimiento".
    forma_tipo: str
    respuesta: Literal["aceptado", "rechazado"]


class RecursoReferenciaUpdate(BaseModel):
    """RFC-0011/3 (ROADMAP-RFC-0011.md, Parte D): asocia la referencia de
    un recurso generado externamente (imagen/audio/video/documento) a un
    `RegistroRecurso` ya existente — nunca en la misma llamada que
    genera el prompt (`POST /cycle-evidence`), porque ocurre en un
    momento posterior e independiente (el prompt se copia, se genera
    externamente, y solo entonces se pega la referencia). Solo modifica
    `referencia_recurso`; `texto_prompt`, `origen` y `version_plantilla`
    son inmutables. Sin validación automática de que el recurso
    corresponde al prompt (decisión del tesista, ROADMAP-RFC-0011.md
    §2, punto 5)."""
    referencia_recurso: str = Field(..., min_length=1, max_length=512)
