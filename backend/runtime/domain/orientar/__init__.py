"""Orientar (R2): ¿a dónde ir? (RFC-0002 §3).

Dos implementaciones del mismo contrato (P13):

* `producir` — versión regla (determinista, provenance `regla`).
* `producir_llm` — versión LLM (provenance `llm`; ADR-0005 §7).
"""

from runtime.domain.orientar.productor import producir
from runtime.domain.orientar.productor_llm import producir as producir_llm
from runtime.domain.orientar.provider import FakeLLMProvider, LLMProvider

__all__ = ["FakeLLMProvider", "LLMProvider", "producir", "producir_llm"]
