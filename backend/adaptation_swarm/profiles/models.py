"""Modelos de perfil (RF01) y del vector de pesos W (RF02).

W = [w_v, w_a, w_t, w_c]: necesidad cognitiva por modalidad Visual (diagrama),
Auditiva (audio), Textual (texto) y Código (asesoría §3.3.1, AG1).
Invariante: cada w ∈ [0,1] y Σw = 1.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field, field_validator, model_validator

from adaptation_swarm.pso.space import MODALITIES

PROFILE_SCHEMA_VERSION = "profile-v1"
_TOL = 1e-6


class Archetype(str, Enum):
    VISUAL_DOMINANT = "visual_dominant"
    LOGICAL_SYNTACTIC = "logical_syntactic"
    EXPLANATORY_CONCEPTUAL = "explanatory_conceptual"
    BALANCED_MULTIMODAL = "balanced_multimodal"


class Difficulty(str, Enum):
    SEQUENTIAL = "sequential"
    CONDITIONAL = "conditional"
    REPETITIVE = "repetitive"
    ARRAYS_VECTORS = "arrays_vectors"
    FUNCTIONS = "functions"


class ModalityWeights(BaseModel):
    w_v: float = Field(ge=0.0, le=1.0)   # visual  → diagrama
    w_a: float = Field(ge=0.0, le=1.0)   # auditiva → audio
    w_t: float = Field(ge=0.0, le=1.0)   # textual → texto
    w_c: float = Field(ge=0.0, le=1.0)   # código

    @model_validator(mode="after")
    def _sum_to_one(self) -> "ModalityWeights":
        total = self.w_v + self.w_a + self.w_t + self.w_c
        if abs(total - 1.0) > _TOL:
            raise ValueError(f"Σw debe ser 1 (±{_TOL}): {total}")
        return self

    def as_list(self) -> list[float]:
        """[w_v, w_a, w_t, w_c] — orden de la asesoría."""
        return [self.w_v, self.w_a, self.w_t, self.w_c]

    def by_modality(self) -> tuple[float, ...]:
        """En el orden de MODALITIES (code, diagram, text, audio) que usa el espacio del PSO."""
        return (self.w_c, self.w_v, self.w_t, self.w_a)

    @classmethod
    def from_raw(cls, w_v: float, w_a: float, w_t: float, w_c: float) -> "ModalityWeights":
        total = w_v + w_a + w_t + w_c
        if total <= 0:
            raise ValueError("los pesos crudos deben sumar > 0")
        return cls(w_v=w_v / total, w_a=w_a / total, w_t=w_t / total, w_c=w_c / total)


class ProfileRequest(BaseModel):
    """Payload RF01: nivel de conocimiento, estilo preferido, tasa de error previa,
    en JSON estandarizado. `archetype`/`difficulty` son metadatos de trazabilidad
    (AG1 NO los usa para calcular W; el gold tampoco lee W)."""

    schema_version: str = PROFILE_SCHEMA_VERSION
    profile_id: str = Field(min_length=1)
    nivel: float = Field(ge=0.0, le=1.0)
    estilo: ModalityWeights
    tasa_error_previa: float = Field(ge=0.0, le=1.0)
    concept_id: str = Field(min_length=1)
    archetype: Archetype | None = None
    difficulty: Difficulty | None = None
    metadata: dict = Field(default_factory=dict)

    @field_validator("schema_version")
    @classmethod
    def _check_version(cls, v: str) -> str:
        if v != PROFILE_SCHEMA_VERSION:
            raise ValueError(f"schema_version {v!r} != {PROFILE_SCHEMA_VERSION!r}")
        return v


assert MODALITIES == ("code", "diagram", "text", "audio")
