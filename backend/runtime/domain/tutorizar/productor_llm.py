"""Productor de Tutorizar — versión LLM (provenance `llm`).

Mismo contrato que la versión regla: mismo `operacion` (registrar_fact),
mismas claves de `contenido` — únicamente cambia CÓMO se clasifica la
señal (P13). Sin `confianza`: ese campo no existe en un fact (INV-4/5,
la asimetría estructural — ya visible en Evaluar, ahora en la segunda
capacidad fact-producer).
"""

from __future__ import annotations

from runtime.domain.shared.llm_roundtrip import ejecutar_roundtrip
from runtime.domain.tutorizar.provider import FakeLLMProvider, LLMProvider
from runtime.kernel.state.entries import Capacidad, OrigenProvenance, Provenance
from runtime.kernel.state.state import LearningState
from runtime.kernel.transitions import TransitionIntent

_PROMPT_ID = "deteccion-conductual-v1"


def producir(
    estado: LearningState, proveedor: LLMProvider | None = None
) -> tuple[TransitionIntent, ...]:
    proveedor = proveedor or FakeLLMProvider()
    for fact in estado.facts:
        if fact.autor is not Capacidad.EVALUAR or not fact.vigencia.vigente:
            continue
        ya_detecte = any(
            f.autor is Capacidad.TUTORIZAR
            and f.vigencia.vigente
            and f.contenido.get("fact_origen") == str(fact.id)
            for f in estado.facts
        )
        if ya_detecte:
            continue
        incorrectos = len(fact.contenido.get("items_incorrectos", ()))
        total = fact.contenido.get("items_totales")
        if not total:
            continue
        prompt = (
            f"incorrectos={incorrectos} total={total}. Clasifica la señal "
            f"conductual (confusion, frustracion o fluidez). Responde JSON."
        )
        respuesta = ejecutar_roundtrip(proveedor, prompt, campos_requeridos=("senal",))
        return (
            TransitionIntent(
                productor=Capacidad.TUTORIZAR,
                operacion="registrar_fact",
                argumentos={
                    "autor": Capacidad.TUTORIZAR,
                    "contenido": {
                        "senal": respuesta["senal"],
                        "fact_origen": str(fact.id),
                        "items_incorrectos": incorrectos,
                        "items_totales": total,
                    },
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
