"""kernel.reducers — las operaciones del agregado (RFC-0003 §4).

Único punto de mutación del LearningState y único emisor de Domain
Events (INV-10). Exactamente dos resultados: aplicado o
rechazado-y-registrado — el aplazamiento es un resultado de deliberación,
jamás de reducer (RFC-0003 §4; P5).
"""

from runtime.kernel.reducers.resultado import Aplicado, Rechazado, ResultadoReducer
from runtime.kernel.reducers.facts import registrar_fact
from runtime.kernel.reducers.claims import registrar_claim
from runtime.kernel.reducers.supersesion import superseder_claim, superseder_fact

__all__ = [
    "Aplicado",
    "Rechazado",
    "ResultadoReducer",
    "registrar_claim",
    "registrar_fact",
    "superseder_claim",
    "superseder_fact",
]
