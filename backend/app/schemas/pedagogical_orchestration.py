"""Schemas para la orquestación pedagógica multimodal inteligente."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# ── Input del docente ─────────────────────────────────────────────

class TeacherInput(BaseModel):
    topic: str = Field(..., description="Tema principal de la sesión")
    learning_objectives: list[str] = Field(..., description="Objetivos de aprendizaje")
    pedagogical_intention: str = Field(..., description="Intención pedagógica del docente")
    thematic_structure: list[str] = Field(default_factory=list, description="Estructura temática")
    syllabus: str = Field(default="", description="Sílabo del curso")
    weekly_line: str = Field(default="", description="Línea semanal")
    student_id: str | None = Field(default=None, description="ID del estudiante (opcional)")
    course_id: str | None = Field(default=None, description="ID del curso (opcional)")


# ── Resultados de investigación ───────────────────────────────────

class ResearchFinding(BaseModel):
    source: str = Field(..., description="Fuente del hallazgo")
    content: str = Field(..., description="Contenido encontrado")
    relevance: float = Field(default=0.5, ge=0.0, le=1.0)
    category: str = Field(default="general", description="Categoría: example, analogy, application, reference")


class ResearchResult(BaseModel):
    topic: str
    findings: list[ResearchFinding] = Field(default_factory=list)
    examples: list[str] = Field(default_factory=list, description="Ejemplos encontrados")
    real_applications: list[str] = Field(default_factory=list, description="Aplicaciones reales")
    analogies: list[str] = Field(default_factory=list, description="Analogías identificadas")
    references: list[str] = Field(default_factory=list, description="Referencias educativas")
    summary: str = Field(default="", description="Resumen de la investigación")


# ── Estructura pedagógica ─────────────────────────────────────────

class PedagogicalSection(str, Enum):
    INTRODUCTION = "introduction"
    CONCEPTUAL_EXPLANATION = "conceptual_explanation"
    EXAMPLE = "example"
    PRACTICAL_APPLICATION = "practical_application"
    REAL_CASE = "real_case"
    EVALUATION = "evaluation"


class SectionPlan(BaseModel):
    section_type: PedagogicalSection
    title: str
    description: str
    estimated_duration_minutes: int = 10
    bloom_level: int = Field(default=2, ge=1, le=6)
    content: str | None = None
    modality: str = Field(default="text", description="Modalidad principal para esta sección")


class PedagogicalStructure(BaseModel):
    topic: str
    sections: list[SectionPlan] = Field(default_factory=list)
    progression_logic: str = Field(default="", description="Justificación de la progresión")
    total_duration_minutes: int = 0
    recommended_prerequisites: list[str] = Field(default_factory=list)


# ── Adaptación de aprendizaje ─────────────────────────────────────

class AdaptationPlan(BaseModel):
    difficulty_level: str = Field(default="intermediate", description="beginner/intermediate/advanced")
    pace_adjustment: str = Field(default="moderate", description="slow/moderate/fast")
    bloom_range: list[int] = Field(default=[1, 3], ge=1, le=6)
    modality_preferences: list[str] = Field(default_factory=list)
    explanation_depth: str = Field(default="standard", description="basic/standard/detailed")
    concept_sequence: list[str] = Field(default_factory=list)
    reinforcement_frequency: str = Field(default="normal", description="low/normal/high")


# ── Planificación multimodal ──────────────────────────────────────

class ModalityDecision(BaseModel):
    section: str = Field(..., description="Sección a la que aplica")
    modality: str = Field(..., description="Modalidad elegida: text, image, audio, video, interactive")
    generate_directly: bool = Field(default=False, description="¿Generar directamente?")
    generate_prompt: bool = Field(default=True, description="¿Generar prompt especializado?")
    reason: str = Field(default="", description="Razón pedagógica de la decisión")
    prompt_type: str | None = Field(default=None, description="Tipo de prompt si aplica")


class MultimodalPlan(BaseModel):
    decisions: list[ModalityDecision] = Field(default_factory=list)
    text_sections: list[str] = Field(default_factory=list, description="Secciones que se generan como texto directo")
    prompt_sections: dict[str, str] = Field(default_factory=dict, description="Sección -> tipo de prompt")
    efficiency_ratio: float = Field(default=0.0, description="Ratio de eficiencia (prompts vs directo)")


# ── Prompts generados ─────────────────────────────────────────────

class GeneratedPrompt(BaseModel):
    prompt_type: str = Field(..., description="Tipo: cinematic, visual, narrative, audio, pedagogical")
    target_section: str = Field(..., description="Sección objetivo")
    content: str = Field(..., description="Prompt detallado")
    parameters: dict[str, Any] = Field(default_factory=dict)
    model_recommendation: str = Field(default="", description="Modelo recomendado para este prompt")


class PromptEngineeringResult(BaseModel):
    prompts: list[GeneratedPrompt] = Field(default_factory=list)
    narrative_thread: str = Field(default="", description="Hilo narrativo transversal")
    visual_continuity: str = Field(default="", description="Notas de continuidad visual")
    audio_atmosphere: str | None = Field(default=None, description="Atmósfera de audio sugerida")


# ── Verificación de consistencia ──────────────────────────────────

class ConsistencyIssue(BaseModel):
    severity: str = Field(default="warning", description="error/warning/info")
    category: str = Field(default="coherence", description="Tipo: coherence, redundancy, progression, character, tone")
    description: str
    affected_sections: list[str] = Field(default_factory=list)
    suggestion: str = Field(default="")


class ConsistencyReport(BaseModel):
    passed: bool = True
    issues: list[ConsistencyIssue] = Field(default_factory=list)
    narrative_coherence_score: float = Field(default=1.0, ge=0.0, le=1.0)
    pedagogical_progression_score: float = Field(default=1.0, ge=0.0, le=1.0)
    multimodal_consistency_score: float = Field(default=1.0, ge=0.0, le=1.0)
    character_continuity: dict[str, Any] = Field(default_factory=dict)
    style_continuity: dict[str, Any] = Field(default_factory=dict)
    resolved_issues: list[str] = Field(default_factory=list)


# ── Memoria compartida ────────────────────────────────────────────

class NarrativeMemory(BaseModel):
    characters: dict[str, Any] = Field(default_factory=dict)
    visual_styles: dict[str, Any] = Field(default_factory=dict)
    narrative_threads: list[str] = Field(default_factory=list)
    previous_prompts: list[str] = Field(default_factory=list)
    pedagogical_constraints: list[str] = Field(default_factory=list)
    progression_state: dict[str, Any] = Field(default_factory=dict)


# ── Resultado final de orquestación ───────────────────────────────

class OrchestrationResult(BaseModel):
    topic: str
    pedagogical_structure: PedagogicalStructure | None = None
    multimodal_plan: MultimodalPlan | None = None
    prompts: list[GeneratedPrompt] = Field(default_factory=list)
    direct_text: dict[str, str] = Field(default_factory=dict, description="Texto generado directamente por sección")
    consistency_report: ConsistencyReport | None = None
    research_result: ResearchResult | None = None
    adaptation_plan: AdaptationPlan | None = None
    narrative_memory: NarrativeMemory | None = None
    warnings: list[str] = Field(default_factory=list)
    execution_summary: dict[str, Any] = Field(default_factory=dict)
    generated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
