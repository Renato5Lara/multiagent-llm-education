"""Evaluar (R5): comprobar que aprendió (RFC-0002 §3).

Dos implementaciones del mismo contrato (P13):

* `producir` — versión regla (conteo determinista, provenance `regla`).
* `producir_llm` — versión LLM (confirmación por prompt, provenance `llm`).

A diferencia de Diagnosticar/Remediar/Orientar: produce FACTS, no
claims, y requiere `respuestas` como parámetro explícito — no puede
derivarlas del estado (P12; ver productor.py).
"""

from runtime.domain.evaluar.productor import producir
from runtime.domain.evaluar.productor_llm import producir as producir_llm
from runtime.domain.evaluar.provider import FakeLLMProvider, LLMProvider

__all__ = ["FakeLLMProvider", "LLMProvider", "producir", "producir_llm"]
