"""Adaptar (R3): diseñar la experiencia de aprendizaje (RFC-0002 §3).

El corazón de la hipótesis de la tesis — "adaptación multimodal". Decide
categorías pedagógicas (modalidad × profundidad × ritmo × andamiaje) con
sus alternativas embebidas en el mismo claim; NUNCA recursos físicos, IDs
de contenido ni referencias de plataforma (eso es RFC-0010, Boundary).

Dos implementaciones del mismo contrato (P13):

* `producir` — versión regla (mapeo determinista, provenance `regla`).
* `producir_llm` — versión LLM (provenance `llm`).
"""

from runtime.domain.adaptar.productor import producir
from runtime.domain.adaptar.productor_llm import producir as producir_llm
from runtime.domain.adaptar.provider import FakeLLMProvider, LLMProvider

__all__ = ["FakeLLMProvider", "LLMProvider", "producir", "producir_llm"]
