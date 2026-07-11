"""Productor de Adaptar — versión LLM (provenance `llm`).

Mismo contrato que la versión regla: mismo `asunto`, mismo respaldo
(incluida la señal de Tutorizar cuando existe, resuelta por el mismo
recorrido causal), las alternativas embebidas en la misma afirmación —
únicamente cambia CÓMO se elige la modalidad (P13). El proveedor razona
en categorías pedagógicas; jamás en recursos físicos (misma frontera que
la regla).
"""

from __future__ import annotations

from decimal import Decimal

from runtime.domain.adaptar.productor import DISENO_POR_ACCION
from runtime.domain.adaptar.provider import FakeLLMProvider, LLMProvider
from runtime.domain.shared.causal import (
    competencia_de_decision,
    senal_tutorizar_de_decision,
)
from runtime.domain.shared.llm_roundtrip import ejecutar_roundtrip
from runtime.kernel.state.entries import (
    Capacidad,
    OrigenProvenance,
    Provenance,
    TipoClaim,
)
from runtime.kernel.state.state import LearningState
from runtime.kernel.transitions import TransitionIntent

_PROMPT_ID = "adaptacion-diseno-v1"


def producir(
    estado: LearningState, proveedor: LLMProvider | None = None
) -> tuple[TransitionIntent, ...]:
    proveedor = proveedor or FakeLLMProvider()
    for decision in estado.decisiones:
        if not decision.vigencia.vigente:
            continue
        accion = decision.contenido.get("accion")
        if accion not in DISENO_POR_ACCION:
            # Qué acciones son válidas es conocimiento de dominio
            # compartido — el mismo conjunto que la regla, aunque el
            # DISEÑO (modalidad/profundidad) lo razone el LLM (P13).
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
        senal_fact = senal_tutorizar_de_decision(estado, decision)
        senal = senal_fact.contenido["senal"] if senal_fact is not None else None
        prompt = (
            f"accion={accion} competencia={competencia} senal={senal}. "
            f"Diseña la experiencia (modalidad, profundidad) con "
            f"alternativas descartadas y su razón, considerando la señal "
            f"de sesión si existe. Responde JSON."
        )
        respuesta = ejecutar_roundtrip(
            proveedor,
            prompt,
            campos_requeridos=("modalidad", "profundidad", "confianza"),
        )
        respaldo = (decision.id,) if senal_fact is None else (decision.id, senal_fact.id)
        return (
            TransitionIntent(
                productor=Capacidad.ADAPTAR,
                operacion="registrar_claim",
                argumentos={
                    "autor": Capacidad.ADAPTAR,
                    "tipo": TipoClaim.PROPUESTA,
                    "asunto": f"modalidad({competencia})",
                    "afirmacion": {
                        "modalidad": respuesta["modalidad"],
                        "profundidad": respuesta["profundidad"],
                        "alternativas_descartadas": respuesta.get(
                            "alternativas_descartadas", []
                        ),
                    },
                    "respaldo": respaldo,
                    "confianza": Decimal(str(respuesta["confianza"])),
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
