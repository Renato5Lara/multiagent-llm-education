"""Productor de Orientar — versión LLM (provenance `llm`).

Mismo contrato que la versión regla (`productor.py`): mismo tipo de
claim, mismo asunto, misma estructura de argumentos hacia
`registrar_claim` — únicamente cambia CÓMO se justifica la propuesta
(P13: cambia la implementación, nunca el contrato).

Confianza declarada calibrada (ADR-0013): la confianza que el LLM
declara no se usa directamente — se reemplaza por `evidence_strength`
sobre la MISMA evidencia que ya respalda la propuesta, midiendo cuánto
sostiene el DOMINIO (aciertos/total, no errores/total: "avanzar" es
optimista sobre el dominio, a diferencia de "reforzar" en Remediar).
Mismo principio que Diagnosticar (Iteración 5.8, H10), sin reutilizar
`calibrar_confianza_nueva` — ver `remediar/productor_llm.py` para la
misma nota, aplicable aquí sin cambios.
"""

from __future__ import annotations

from decimal import Decimal

from runtime.domain.orientar.productor import ASUNTO_SIGUIENTE_PASO
from runtime.domain.orientar.provider import FakeLLMProvider, LLMProvider
from runtime.domain.shared.calibracion import evidence_strength
from runtime.domain.shared.llm_roundtrip import ejecutar_roundtrip
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

_PROMPT_ID = "orientacion-siguiente-paso-v2"
_PROMPT_ID_OBJETIVO = "orientacion-por-objetivo-v1"


def _fuerza_avanzar(estado: LearningState, claim, errores: int) -> Decimal:
    """Fuerza de la evidencia que sostiene "avanzar" — cuánto respalda
    el fact original (vía `claim.respaldo`) el dominio (aciertos/total),
    no el fallo (ADR-0013). `claim` es la interpretación de Diagnosticar
    que esta propuesta respalda."""
    fact = estado.buscar(claim.respaldo[0]) if claim.respaldo else None
    total = fact.contenido.get("items_totales") if fact is not None else None
    total = total or 0
    aciertos = max(total - errores, 0)
    return evidence_strength(soporte=aciertos, total=total)


def producir(
    estado: LearningState,
    proveedor: LLMProvider | None = None,
    objetivos: tuple[ObjetivoOrdenado, ...] = (),
) -> tuple[TransitionIntent, ...]:
    """Misma guardia que la versión regla (`palabra_en_pie` — ciclo
    adaptativo continuo, 2026-07-13): re-propone solo si su palabra
    previa cayó con su respaldo o si el vencedor que la descartó cayó
    después (debate huérfano), jamás por el mero hecho de haber perdido
    una deliberación (anti-churn). Filtra por interpretaciones de
    DOMINIO ("dominada" en la afirmación) — no cualquier INTERPRETACION:
    respaldarse en un veredicto de Validar creó un bucle real
    (2026-07-13), mismo criterio de forma que Remediar.

    Sin `objetivos`: comportamiento histórico exacto (asunto de sesión).
    Con `objetivos`: una propuesta por objetivo (DESIGN-orientar-ruta-
    completa.md), mismo contrato P13 que la versión regla."""
    proveedor = proveedor or FakeLLMProvider()
    if objetivos:
        return _producir_por_objetivo(estado, objetivos, proveedor)
    if palabra_en_pie(estado, Capacidad.ORIENTAR, ASUNTO_SIGUIENTE_PASO):
        return ()
    for claim in estado.claims:
        if (
            claim.tipo is TipoClaim.INTERPRETACION
            and claim.vigencia.vigente
            and "dominada" in claim.afirmacion
        ):
            errores = claim.afirmacion.get("errores")
            prompt = (
                f"Existe una interpretación vigente sobre el estudiante "
                f"(claim {claim.id}, {errores} items incorrectos). La "
                f"política ruta-v1 propone avanzar al siguiente objetivo "
                f"con andamiaje adicional como "
                f"CANDIDATA en la deliberación — no es una decisión final "
                f"ni un juicio tuyo sobre si conviene: eso lo resuelve "
                f"después el Kernel comparando esta propuesta contra la "
                f'de Remediar. Responde JSON con esta forma EXACTA y en '
                f'este ORDEN: primero "razonamiento" (por qué '
                f"avanzar-con-andamiaje es una propuesta razonable aquí), "
                f'luego "accion" (STRING, debe ser exactamente '
                f'"avanzar-con-andamiaje"), luego "confianza" (STRING con '
                f'formato decimal entre "0.00" y "1.00", ejemplo "0.78").'
            )
            respuesta = ejecutar_roundtrip(
                proveedor, prompt, campos_requeridos=("accion", "confianza")
            )
            errores = errores or 0
            return (
                TransitionIntent(
                    productor=Capacidad.ORIENTAR,
                    operacion="registrar_claim",
                    argumentos={
                        "autor": Capacidad.ORIENTAR,
                        "tipo": TipoClaim.PROPUESTA,
                        "asunto": ASUNTO_SIGUIENTE_PASO,
                        "afirmacion": {
                            "accion": respuesta["accion"],
                            "razonamiento": respuesta.get("razonamiento", ""),
                        },
                        "respaldo": (claim.id,),
                        "confianza": _fuerza_avanzar(estado, claim, errores),
                        "provenance": Provenance.de(
                            OrigenProvenance.LLM,
                            modelo=proveedor.modelo,
                            version=proveedor.version,
                            prompt_id=_PROMPT_ID,
                        ),
                    },
                    base=estado.transicion,
                ),
            )
    return ()


def _producir_por_objetivo(
    estado: LearningState,
    objetivos: tuple[ObjetivoOrdenado, ...],
    proveedor: LLMProvider,
) -> tuple[TransitionIntent, ...]:
    """Mismo contrato que `orientar.productor._producir_por_objetivo` --
    únicamente cambia cómo se justifica la propuesta (P13)."""
    for objetivo in objetivos:
        asunto = asunto_avance(objetivo.asunto)
        if palabra_en_pie(estado, Capacidad.ORIENTAR, asunto):
            continue
        dominio_asunto = f"dominio({objetivo.asunto})"
        for claim in estado.claims:
            if not (
                claim.tipo is TipoClaim.INTERPRETACION
                and claim.vigencia.vigente
                and claim.asunto == dominio_asunto
                and claim.afirmacion.get("dominada") is True
            ):
                continue
            prompt = (
                f"Existe una interpretación vigente de dominio sobre el "
                f"objetivo {objetivo.id} (claim {claim.id}). La política "
                f"ruta-v2 propone avanzar a este objetivo como CANDIDATA "
                f"en la deliberación — no es una decisión final: eso lo "
                f"resuelve el Kernel comparando esta propuesta contra la "
                f'de Remediar sobre el mismo objetivo. Responde JSON con '
                f'esta forma EXACTA y en este ORDEN: primero '
                f'"razonamiento", luego "accion" (STRING, debe ser '
                f'exactamente "avanzar"), luego "confianza" (STRING con '
                f'formato decimal entre "0.00" y "1.00").'
            )
            respuesta = ejecutar_roundtrip(
                proveedor, prompt, campos_requeridos=("accion", "confianza")
            )
            errores = claim.afirmacion.get("errores") or 0
            return (
                TransitionIntent(
                    productor=Capacidad.ORIENTAR,
                    operacion="registrar_claim",
                    argumentos={
                        "autor": Capacidad.ORIENTAR,
                        "tipo": TipoClaim.PROPUESTA,
                        "asunto": asunto,
                        "afirmacion": {
                            "accion": respuesta["accion"],
                            "razonamiento": respuesta.get("razonamiento", ""),
                        },
                        "respaldo": (claim.id,),
                        "confianza": _fuerza_avanzar(estado, claim, errores),
                        "provenance": Provenance.de(
                            OrigenProvenance.LLM,
                            modelo=proveedor.modelo,
                            version=proveedor.version,
                            prompt_id=_PROMPT_ID_OBJETIVO,
                        ),
                    },
                    base=estado.transicion,
                ),
            )
    return ()
