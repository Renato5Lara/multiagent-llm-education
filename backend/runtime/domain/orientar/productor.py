"""Productor de Orientar — versión regla: propone avanzar con andamiaje
(el otro lado de la tensión canónica n.º 1). No conoce a Remediar (P3):
solo lee el estado que Diagnosticar modificó."""

from __future__ import annotations

from decimal import Decimal

from runtime.domain.shared.objetivos import ObjetivoOrdenado, asunto_avance
from runtime.domain.shared.propuestas import palabra_en_pie
from runtime.kernel.state.entries import (
    Capacidad,
    OrigenProvenance,
    Provenance,
    TipoClaim,
)
from runtime.kernel.state.state import LearningState
from runtime.kernel.transitions import TransitionIntent

ASUNTO_SIGUIENTE_PASO = "siguiente-paso(sesion)"


def producir(
    estado: LearningState,
    objetivos: tuple[ObjetivoOrdenado, ...] = (),
) -> tuple[TransitionIntent, ...]:
    """Sin `objetivos`: comportamiento histórico exacto (adaptación en
    vivo dentro de la sesión, asunto único `siguiente-paso(sesion)`). Con
    `objetivos` (DESIGN-orientar-ruta-completa.md): una propuesta por
    objetivo, asunto `avance(objetivo.asunto)` -- para que la
    planificación de ruta pueda leer, por objetivo, si el Runtime ya
    decidió avanzar. Ambos asuntos coexisten; uno no reemplaza al otro."""
    if objetivos:
        return _producir_por_objetivo(estado, objetivos)
    # Misma guardia que Remediar (ver domain/shared/propuestas.py):
    # re-propone si su palabra cayó con su respaldo o si el vencedor
    # que la descartó cayó después (debate huérfano) — jamás por el
    # mero hecho de haber perdido una deliberación (anti-churn).
    if palabra_en_pie(estado, Capacidad.ORIENTAR, ASUNTO_SIGUIENTE_PASO):
        return ()
    for claim in estado.claims:
        # Solo interpretaciones de DOMINIO (la forma que Diagnosticar
        # produce: afirmacion con "dominada") — no cualquier
        # INTERPRETACION: los veredictos de Validar (asunto "efecto(…)")
        # también son interpretaciones y respaldarse en uno creó un
        # bucle real (2026-07-13): la cascada de la decisión superseded
        # tumbaba el veredicto y, con él, el respaldo de la propuesta
        # nueva. Mismo criterio de forma que ya usa Remediar.
        if (
            claim.tipo is TipoClaim.INTERPRETACION
            and claim.vigencia.vigente
            and "dominada" in claim.afirmacion
        ):
            return (
                TransitionIntent(
                    productor=Capacidad.ORIENTAR,
                    operacion="registrar_claim",
                    argumentos={
                        "autor": Capacidad.ORIENTAR,
                        "tipo": TipoClaim.PROPUESTA,
                        "asunto": ASUNTO_SIGUIENTE_PASO,
                        "afirmacion": {"accion": "avanzar-con-andamiaje"},
                        "respaldo": (claim.id,),
                        "confianza": Decimal("0.75"),
                        "provenance": Provenance.de(
                            OrigenProvenance.REGLA, id="ruta-v1"
                        ),
                    },
                    base=estado.transicion,
                ),
            )
    return ()


def _producir_por_objetivo(
    estado: LearningState, objetivos: tuple[ObjetivoOrdenado, ...]
) -> tuple[TransitionIntent, ...]:
    """Un intent por activación (mismo patrón que Diagnosticar y que la
    rama de sesión arriba): recorre los objetivos en orden y propone
    sobre el primero con evidencia de dominio pendiente y sin palabra en
    pie propia -- ver `_pendiente_objetivo` en walkthrough.py, MISMA
    función que usa el guard del router (patrón PR-2..PR-5)."""
    for objetivo in objetivos:
        asunto = asunto_avance(objetivo.asunto)
        if palabra_en_pie(estado, Capacidad.ORIENTAR, asunto):
            continue
        dominio_asunto = f"dominio({objetivo.asunto})"
        for claim in estado.claims:
            if (
                claim.tipo is TipoClaim.INTERPRETACION
                and claim.vigencia.vigente
                and claim.asunto == dominio_asunto
                and claim.afirmacion.get("dominada") is True
            ):
                return (
                    TransitionIntent(
                        productor=Capacidad.ORIENTAR,
                        operacion="registrar_claim",
                        argumentos={
                            "autor": Capacidad.ORIENTAR,
                            "tipo": TipoClaim.PROPUESTA,
                            "asunto": asunto,
                            "afirmacion": {"accion": "avanzar"},
                            "respaldo": (claim.id,),
                            "confianza": Decimal("0.75"),
                            "provenance": Provenance.de(
                                OrigenProvenance.REGLA, id="ruta-v2"
                            ),
                        },
                        base=estado.transicion,
                    ),
                )
    return ()
