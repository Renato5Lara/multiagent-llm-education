"""Tutorizar (R4): acompañar mientras aprende (RFC-0002 §3).

Contrato confirmado contra RFC-0002/RFC-0003 antes de implementar: es
productora de FACTS (como Evaluar), no de claims — detecta señales
conductuales (confusión, frustración, fluidez). No propone estrategias,
no redacta mensajes, no decide.

Dos implementaciones del mismo contrato (P13):

* `producir` — versión regla (clasificación determinista, provenance `regla`).
* `producir_llm` — versión LLM (provenance `llm`).
"""

from runtime.domain.tutorizar.productor import producir
from runtime.domain.tutorizar.productor_llm import producir as producir_llm
from runtime.domain.tutorizar.provider import FakeLLMProvider, LLMProvider

__all__ = ["FakeLLMProvider", "LLMProvider", "producir", "producir_llm"]
