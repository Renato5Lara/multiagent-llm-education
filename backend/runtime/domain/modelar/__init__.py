"""Modelar (R1): conocer al estudiante (RFC-0002 §3).

Primera capacidad "actualizadora" (RFC-0002 la clasifica junto a las
demás como productora de conocimiento — su claim es la materia prima que
RFC-0005 consolidará en una nueva versión del student model al cierre;
Modelar no muta memoria persistente dentro de la sesión).

Dos implementaciones del mismo contrato (P13):

* `producir` — versión regla (provenance `regla`).
* `producir_llm` — versión LLM (provenance `llm`).

Puro-de-estado: lee `competencia` y `funciono` directamente del claim de
Validar (vía `respaldo`), sin recorrer la cadena causal por su cuenta.
"""

from runtime.domain.modelar.productor import producir
from runtime.domain.modelar.productor_llm import producir as producir_llm
from runtime.domain.modelar.provider import FakeLLMProvider, LLMProvider

__all__ = ["FakeLLMProvider", "LLMProvider", "producir", "producir_llm"]
