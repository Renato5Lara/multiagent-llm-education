"""Diagnosticar (R2): ¿dónde está el estudiante? (RFC-0002 §3).

Dos implementaciones del mismo contrato (P13) — el interior de una
capacidad es libre; su única salida son TransitionIntents:

* `producir` — versión regla (determinista, provenance `regla`).
* `producir_llm` — versión LLM (provenance `llm`; ADR-0005 §7).
"""

from runtime.domain.diagnosticar.productor import producir
from runtime.domain.diagnosticar.productor_llm import producir as producir_llm
from runtime.domain.diagnosticar.provider import FakeLLMProvider, LLMProvider

__all__ = ["FakeLLMProvider", "LLMProvider", "producir", "producir_llm"]
