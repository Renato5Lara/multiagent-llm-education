"""Validar (R7): metaevaluación — ¿funcionó la adaptación? (RFC-0002 §3).

Dos implementaciones del mismo contrato (P13):

* `producir` — versión regla (comparación determinista, provenance `regla`).
* `producir_llm` — versión LLM (juicio por prompt, provenance `llm`).

Puro-de-estado (a diferencia de Evaluar): recorre la cadena causal de la
decisión para hallar su competencia, sin parámetros externos.
"""

from runtime.domain.validar.productor import producir
from runtime.domain.validar.productor_llm import producir as producir_llm
from runtime.domain.validar.provider import FakeLLMProvider, LLMProvider

__all__ = ["FakeLLMProvider", "LLMProvider", "producir", "producir_llm"]
