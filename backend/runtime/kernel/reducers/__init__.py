"""kernel.reducers — las operaciones del agregado (RFC-0003 §4).

Único punto de mutación del LearningState y único emisor de Domain
Events (INV-10). Exactamente dos resultados: aplicado o
rechazado-y-registrado — el aplazamiento es un resultado de deliberación,
jamás de reducer (RFC-0003 §4; P5).

Convención (tesista, 2026-07-10): **cada reducer responde exactamente una
pregunta** — registrar_fact: ¿puede existir este hecho?; registrar_claim:
¿puede existir este claim?; superseder_*: ¿puede dejar de ser vigente?;
registrar_decision: ¿puede existir esta decisión?; registrar_deliberacion:
¿puede existir este episodio? Cuando un reducer empiece a responder dos
preguntas distintas, es el momento de dividirlo.
"""

from runtime.kernel.reducers.resultado import Aplicado, Rechazado, ResultadoReducer
from runtime.kernel.reducers.facts import registrar_fact
from runtime.kernel.reducers.claims import registrar_claim
from runtime.kernel.reducers.supersesion import superseder_claim, superseder_fact
from runtime.kernel.reducers.decisiones import registrar_decision
from runtime.kernel.reducers.deliberaciones import registrar_deliberacion
from runtime.kernel.reducers.validacion import validar_decision

__all__ = [
    "Aplicado",
    "Rechazado",
    "ResultadoReducer",
    "registrar_claim",
    "registrar_decision",
    "registrar_deliberacion",
    "registrar_fact",
    "superseder_claim",
    "superseder_fact",
    "validar_decision",
]
