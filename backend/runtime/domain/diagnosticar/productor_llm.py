"""Productor de Diagnosticar — versión LLM (provenance `llm`).

Mismo contrato que la versión regla (`productor.py`): mismo tipo de
claim, mismo asunto, misma estructura de argumentos hacia
`registrar_claim` — únicamente cambia CÓMO se interpreta el hecho (P13:
cambia la implementación, nunca el contrato). El runtime no distingue
esta capacidad de su versión regla: ambas producen exclusivamente
`TransitionIntent`s hacia el mismo reducer.

Confianza declarada calibrada (RESEARCH_ITERATIONS.md Iteración 5.8,
cadena H10): la confianza que el LLM declara no se usa directamente
como `confianza` del claim — Diagnosticar la reemplaza por la fuerza de
evidencia calibrada (`calibracion.py`), comparada contra el claim
vigente del mismo asunto cuando existe. Esto no cambia el contrato
(P13): mismo tipo de claim, mismo reducer, mismo asunto — solo cómo se
calcula un valor que el productor ya declaraba.
"""

from __future__ import annotations

from runtime.domain.diagnosticar.calibracion import (
    calibrar_confianza_nueva,
    evidence_strength,
)
from runtime.domain.diagnosticar.productor import _UMBRAL_ERRORES
from runtime.domain.diagnosticar.provider import FakeLLMProvider, LLMProvider
from runtime.domain.shared.llm_roundtrip import ejecutar_roundtrip
from runtime.kernel.deliberation.confianza import calcular_confianza_efectiva
from runtime.kernel.deliberation.politica import resolver_politica
from runtime.kernel.state.entries import (
    Capacidad,
    OrigenProvenance,
    Provenance,
    TipoClaim,
)
from runtime.kernel.state.state import LearningState
from runtime.kernel.transitions import TransitionIntent

_PROMPT_ID = "diagnostico-competencia-v1"


def _claim_vigente_de(estado: LearningState, asunto: str):
    """El claim INTERPRETACION vigente de `asunto`, si existe — a lo
    sumo uno por construcción (Iteración 5.8): `enrutar()` resuelve
    `tension_bloqueante` antes de rutear hacia "diagnosticar"
    (`walkthrough.py`), así que nunca hay una tensión D1 pendiente en el
    momento en que este productor se ejecuta."""
    for claim in estado.claims:
        if (
            claim.tipo is TipoClaim.INTERPRETACION
            and claim.asunto == asunto
            and claim.vigencia.vigente
        ):
            return claim
    return None


def producir(
    estado: LearningState, proveedor: LLMProvider | None = None
) -> tuple[TransitionIntent, ...]:
    """LEER → INTERPRETAR → PRODUCIR (RFC-0004 §1, pasos 1–3).

    Interpreta CADA hecho evaluativo una sola vez (guardia por hecho,
    mismo patrón que la versión regla — 2026-07-13, "mapa completo"): un
    guardián global (cualquier claim vigente de Diagnosticar silencia la
    capacidad entera) dejaba sin interpretar el resto de competencias de
    un mismo diagnóstico. "Interpretado" es HISTÓRICO (P14/ADR-0007: la
    historia jamás se reejecuta), no de vigencia — reinterpretar el
    mismo hecho tras perder una deliberación D1 produciría oscilación
    eterna."""
    proveedor = proveedor or FakeLLMProvider()
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
        prompt = (
            f"Competencia={fact.contenido['competencia']} "
            f"items_incorrectos={errores}. Una competencia se considera "
            f"DOMINADA cuando tiene menos de {_UMBRAL_ERRORES} items "
            f"incorrectos (regla scoring-v1). Responde JSON con esta "
            f'forma EXACTA y en este ORDEN: primero "razonamiento" '
            f"(explica el criterio y aplica la regla paso a paso), luego "
            f'"errores" (el número de items incorrectos), luego '
            f'"dominada" (booleano, DEBE ser consistente con la '
            f'conclusión de tu razonamiento), luego "confianza" (STRING '
            f'con formato decimal entre "0.00" y "1.00", ejemplo "0.80", '
            f"nunca como palabra ni como número)."
        )
        respuesta = ejecutar_roundtrip(
            proveedor, prompt, campos_requeridos=("dominada", "errores", "confianza")
        )
        dominada = respuesta["dominada"]
        asunto = f"dominio({fact.contenido['competencia']})"

        total = fact.contenido.get("items_totales") or 0
        soporte = (total - errores) if dominada else errores
        fuerza_nueva = evidence_strength(soporte, total)

        vigente = _claim_vigente_de(estado, asunto)
        vigente_dominada = vigente.afirmacion.get("dominada") if vigente else None
        fuerza_vigente = (
            calcular_confianza_efectiva(
                vigente, estado, resolver_politica(estado.identidad.version_politica)
            )
            if vigente
            else None
        )

        confianza_final = calibrar_confianza_nueva(
            nueva_dominada=dominada,
            fuerza_nueva=fuerza_nueva,
            vigente_dominada=vigente_dominada,
            fuerza_vigente=fuerza_vigente,
        )

        return (
            TransitionIntent(
                productor=Capacidad.DIAGNOSTICAR,
                operacion="registrar_claim",
                argumentos={
                    "autor": Capacidad.DIAGNOSTICAR,
                    "tipo": TipoClaim.INTERPRETACION,
                    "asunto": asunto,
                    "afirmacion": {
                        "dominada": dominada,
                        "errores": respuesta["errores"],
                        "razonamiento": respuesta.get("razonamiento", ""),
                    },
                    "respaldo": (fact.id,),
                    "confianza": confianza_final,
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
