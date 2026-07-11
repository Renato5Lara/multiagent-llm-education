"""Productor de Adaptar — versión regla (RFC-0002 §3, R3; Walkthrough T9).

Propuesta única con alternativas EMBEBIDAS en el mismo claim (RFC-0002:
"con las alternativas que evaluó") — no una deliberación con rivales. Sin
propuesta rival ni evidencia en contra, no se convoca deliberación (P8).

Frontera dura: Adaptar decide categorías pedagógicas (modalidad,
profundidad) — NUNCA recursos físicos, IDs de contenido ni referencias de
plataforma. Eso pertenece al Boundary (RFC-0010) y ocurre después de que
esta propuesta se convierta en decisión.

Cobertura declarada: lee objetivo (vía el recorrido causal) y `accion` de
la decisión, y — cuando ya existe en el estado — la señal de sesión que
Tutorizar detectó sobre el mismo fact original (resolución causal, nunca
por posición: `senal_tutorizar_de_decision`), lo que amplía las
alternativas que evaluó y su respaldo. NO consume todavía el modelo del
estudiante (Modelar): estructuralmente no existe aún en esta misma pasada
del walkthrough (Modelar depende del veredicto de Validar, posterior a
Adaptar) — gap explícito, pendiente de la reanudación de sesión
(P10/RFC-0008), no de este PR.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Mapping

from runtime.domain.shared.causal import (
    competencia_de_decision,
    senal_tutorizar_de_decision,
)
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

# Refina las alternativas EMBEBIDAS cuando ya existe una señal de sesión
# (Tutorizar) causalmente ligada al mismo fact que originó la decisión —
# RFC-0002: "con las alternativas que evaluó" deja de ser una tabla fija
# por acción y pasa a considerar también la conducta observada. Solo
# cubre combinaciones alcanzables (p. ej. "reforzar" nunca coexiste con
# la señal "fluidez": exige ≥2 errores en el mismo fact); fuera de la
# tabla, se conserva el diseño por acción de `DISENO_POR_ACCION`.
ALTERNATIVAS_POR_SENAL: Mapping[tuple[str, str], tuple[Mapping, ...]] = {
    ("reforzar", "confusion"): (
        {"modalidad": "textual", "razon": "ya insuficiente en el intento anterior"},
        {"modalidad": "ejemplo-codigo", "razon": "prematuro sin el concepto consolidado"},
    ),
    ("reforzar", "frustracion"): (
        {"modalidad": "guiado", "razon": "riesgo de abandono: requiere acompañamiento antes que autonomía"},
        {"modalidad": "practica", "razon": "prematuro repetir ejercicios sin resolver la frustración"},
    ),
    ("avanzar-con-andamiaje", "fluidez"): (
        {"modalidad": "practica", "razon": "aún prematuro retirar el andamiaje sin una repetición más"},
        {"modalidad": "autonomo", "razon": "el estudiante todavía no demostró suficiente autonomía"},
    ),
    ("avanzar-con-andamiaje", "confusion"): (
        {"modalidad": "solo-texto", "razon": "el andamiaje requiere apoyo visual"},
    ),
}


def producir(estado: LearningState) -> tuple[TransitionIntent, ...]:
    for decision in estado.decisiones:
        if not decision.vigencia.vigente:
            continue
        accion = decision.contenido.get("accion")
        diseno = DISENO_POR_ACCION.get(accion)
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
        diseno = dict(diseno)
        respaldo: tuple = (decision.id,)
        senal_fact = senal_tutorizar_de_decision(estado, decision)
        if senal_fact is not None:
            alternativas = ALTERNATIVAS_POR_SENAL.get(
                (accion, senal_fact.contenido["senal"])
            )
            if alternativas is not None:
                diseno["alternativas_descartadas"] = alternativas
                respaldo = (decision.id, senal_fact.id)
        return (
            TransitionIntent(
                productor=Capacidad.ADAPTAR,
                operacion="registrar_claim",
                argumentos={
                    "autor": Capacidad.ADAPTAR,
                    "tipo": TipoClaim.PROPUESTA,
                    "asunto": f"modalidad({competencia})",
                    "afirmacion": diseno,
                    "respaldo": respaldo,
                    "confianza": Decimal("0.80"),
                    "provenance": Provenance.de(
                        OrigenProvenance.REGLA, id="adaptacion-v1"
                    ),
                },
                base=estado.transicion,
            ),
        )
    return ()
