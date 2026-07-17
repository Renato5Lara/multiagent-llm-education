"""Productor de Diagnosticar — versión regla (provenance `regla`).

Capacidad real y determinista: interpreta los resultados evaluativos con
la regla de scoring de politica-v1. Cuando llegue la versión LLM, cambia
la provenance y el interior — jamás la salida (P13: la capacidad es
estable; su implementación, intercambiable).
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

_UMBRAL_ERRORES = 2  # regla scoring-v1: ≥2 errores ⇒ competencia no dominada


def producir(estado: LearningState) -> tuple[TransitionIntent, ...]:
    """LEER → INTERPRETAR → PRODUCIR (RFC-0004 §1, pasos 1–3).

    Interpreta CADA hecho evaluativo una sola vez (guardia por hecho,
    mismo patrón que Tutorizar: `fact.id` en el respaldo de un claim
    vigente propio) — no "una vez por sesión": RFC-0002 R1 encarga a
    Diagnosticar interpretar los resultados evaluativos, todos. La
    guardia global anterior dejaba 7 de 8 competencias de un
    diagnóstico sin interpretar (mapa incompleto — bug de producto,
    2026-07-13). Un intent por activación: el ciclo
    aplicar→diagnosticar recorre la evidencia pendiente hecho a hecho."""
    # "Interpretado" es HISTÓRICO, no de vigencia (P14/ADR-0007: la
    # historia jamás se reejecuta): un hecho se interpreta UNA vez;
    # si su interpretación luego pierde una deliberación D1, la
    # corrección del paisaje ya ocurrió por consenso — reinterpretar el
    # mismo hecho produciría una oscilación eterna (cada reinterpretación
    # "más nueva" ganaría el desempate y supersedería a la rival).
    interpretados = {
        ref
        for c in estado.claims
        if c.autor is Capacidad.DIAGNOSTICAR
        for ref in c.respaldo
    }
    for fact in estado.facts:
        if not fact.vigencia.vigente or "competencia" not in fact.contenido:
            continue
        if fact.id in interpretados:
            continue
        errores = len(fact.contenido.get("items_incorrectos", ()))
        return (
            TransitionIntent(
                productor=Capacidad.DIAGNOSTICAR,
                operacion="registrar_claim",
                argumentos={
                    "autor": Capacidad.DIAGNOSTICAR,
                    "tipo": TipoClaim.INTERPRETACION,
                    "asunto": f"dominio({fact.contenido['competencia']})",
                    "afirmacion": {
                        "dominada": errores < _UMBRAL_ERRORES,
                        "errores": errores,
                    },
                    "respaldo": (fact.id,),
                    "confianza": Decimal("0.78"),
                    "provenance": Provenance.de(
                        OrigenProvenance.REGLA, id="scoring-v1"
                    ),
                },
                base=estado.transicion,
            ),
        )
    return ()
