"""S1 — Entregas (RFC-0010 §2): "la decisión de experiencia (qué
presentar, cómo) hacia la plataforma, que la renderiza". Es la propuesta
vigente más reciente de Adaptar — no `estado.salidas` (que es la
proyección de cierre para Memoria, RFC-0005 §2, un régimen distinto:
`[al cierre]` contra la Entrega, que vive durante toda la sesión).

Regla 2 del contrato: S3 expone el interior en vocabulario del runtime,
sin traducirlo a jerga de la plataforma ("el Modo Evidencia enseña el
vocabulario, no lo esconde"). Esta salida S1 sigue el mismo principio:
`diseno` es exactamente `afirmacion` del claim de Adaptar, sin
reinterpretar.
"""

from __future__ import annotations

import dataclasses
from typing import Any, Mapping

from runtime.kernel.state.entries import Capacidad
from runtime.kernel.state.state import LearningState


@dataclasses.dataclass(frozen=True, slots=True)
class Entrega:
    """`asunto`/`diseno` en `None` si el walkthrough todavía no llegó a
    adaptar — un estado válido (p. ej. justo después de E1, o mientras
    aún se delibera), no un error."""

    asunto: str | None
    diseno: Mapping[str, Any] | None


def proyectar_entrega(estado: LearningState) -> Entrega:
    vigentes = [
        claim
        for claim in estado.claims
        if claim.autor is Capacidad.ADAPTAR and claim.vigencia.vigente
    ]
    if not vigentes:
        return Entrega(asunto=None, diseno=None)
    mas_reciente = max(vigentes, key=lambda claim: claim.id.transicion)
    return Entrega(asunto=mas_reciente.asunto, diseno=mas_reciente.afirmacion)
