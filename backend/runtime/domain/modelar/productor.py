"""Productor de Modelar — versión regla (RFC-0002 §3, R1).

Puro-de-estado. Dentro de la sesión, Modelar NO escribe el student
model — RFC-0005 §1 es explícito: la memoria persistente se consolida
al CERRAR la sesión, jamás durante. Lo que Modelar produce aquí es el
claim interpretativo que RFC-0005 §2 ya anticipó como su forma exacta:
*"la modalidad visual funcionó en condicionales" es una dimensión del
modelo, escrita por Modelar a partir de los veredictos de Validar* — esa
frase, literalmente, es este productor. La consolidación real en una
nueva versión del student model ocurre en `salidas`, al cierre — pieza
futura (RFC-0005, prioridad 3 de M2).

No recorre la cadena causal por su cuenta: lee `competencia` directamente
del claim de Validar (evita acoplar domain/modelar a domain/validar, P3;
evita repetir el recorrido, P6 ya lo hizo una vez).
"""

from __future__ import annotations

from decimal import Decimal

from runtime.kernel.state.entries import (
    Capacidad,
    OrigenProvenance,
    Provenance,
    TipoClaim,
)
from runtime.kernel.state.state import LearningState
from runtime.kernel.transitions import TransitionIntent


def producir(estado: LearningState) -> tuple[TransitionIntent, ...]:
    for validacion in estado.claims:
        if validacion.autor is not Capacidad.VALIDAR or not validacion.vigencia.vigente:
            continue
        ya_modele = any(
            c.autor is Capacidad.MODELAR
            and c.vigencia.vigente
            and validacion.id in c.respaldo
            for c in estado.claims
        )
        if ya_modele:
            continue
        competencia = validacion.afirmacion.get("competencia")
        funciono = validacion.afirmacion.get("funciono")
        if competencia is None or funciono is None:
            continue
        return (
            TransitionIntent(
                productor=Capacidad.MODELAR,
                operacion="registrar_claim",
                argumentos={
                    "autor": Capacidad.MODELAR,
                    "tipo": TipoClaim.INTERPRETACION,
                    "asunto": f"modelo-estudiante({competencia})",
                    "afirmacion": {
                        "competencia": competencia,
                        "efecto_positivo": funciono,
                    },
                    "respaldo": (validacion.id,),
                    "confianza": Decimal("0.80"),
                    "provenance": Provenance.de(
                        OrigenProvenance.REGLA, id="modelado-v1"
                    ),
                },
                base=estado.transicion,
            ),
        )
    return ()
