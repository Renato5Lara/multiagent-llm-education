"""Productor de Adaptar — versión regla (RFC-0002 §3, R3; Walkthrough T9).

Propuesta única con alternativas EMBEBIDAS en el mismo claim (RFC-0002:
"con las alternativas que evaluó") — no una deliberación con rivales. Sin
propuesta rival ni evidencia en contra, no se convoca deliberación (P8).

Frontera dura: Adaptar decide categorías pedagógicas (modalidad,
profundidad) — NUNCA recursos físicos, IDs de contenido ni referencias de
plataforma. Eso pertenece al Boundary (RFC-0010) y ocurre después de que
esta propuesta se convierta en decisión.

Cobertura declarada: lee objetivo (vía el recorrido causal) y `accion`
de la decisión. NO consume todavía el modelo del estudiante (Modelar) ni
señales de sesión (Tutorizar, aún no existe) para refinar la elección —
gap explícito, no silencioso: RFC-0002 exige ambas entradas; esta versión
las tiene pendientes hasta que Tutorizar exista.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Mapping

from runtime.domain.shared.causal import competencia_de_decision
from runtime.kernel.state.entries import (
    Capacidad,
    OrigenProvenance,
    Provenance,
    TipoClaim,
)
from runtime.kernel.state.state import LearningState
from runtime.kernel.transitions import TransitionIntent

DISENO_POR_ACCION: Mapping[str, Mapping] = {
    "reforzar": {
        "modalidad": "visual",
        "profundidad": "fundamentos",
        "alternativas_descartadas": (
            {"modalidad": "textual", "razon": "ya insuficiente en el intento anterior"},
            {"modalidad": "ejemplo-codigo", "razon": "prematuro sin el concepto consolidado"},
        ),
    },
    "avanzar-con-andamiaje": {
        "modalidad": "mixta",
        "profundidad": "aplicacion",
        "alternativas_descartadas": (
            {"modalidad": "solo-texto", "razon": "el andamiaje requiere apoyo visual"},
        ),
    },
}


def producir(estado: LearningState) -> tuple[TransitionIntent, ...]:
    for decision in estado.decisiones:
        if not decision.vigencia.vigente:
            continue
        diseno = DISENO_POR_ACCION.get(decision.contenido.get("accion"))
        if diseno is None:
            continue
        ya_adapte = any(
            c.autor is Capacidad.ADAPTAR
            and c.vigencia.vigente
            and decision.id in c.respaldo
            for c in estado.claims
        )
        if ya_adapte:
            continue
        competencia = competencia_de_decision(estado, decision)
        if competencia is None:
            continue
        return (
            TransitionIntent(
                productor=Capacidad.ADAPTAR,
                operacion="registrar_claim",
                argumentos={
                    "autor": Capacidad.ADAPTAR,
                    "tipo": TipoClaim.PROPUESTA,
                    "asunto": f"modalidad({competencia})",
                    "afirmacion": dict(diseno),
                    "respaldo": (decision.id,),
                    "confianza": Decimal("0.80"),
                    "provenance": Provenance.de(
                        OrigenProvenance.REGLA, id="adaptacion-v1"
                    ),
                },
                base=estado.transicion,
            ),
        )
    return ()
