"""Productor de Tutorizar — versión LLM (provenance `llm`).

Mismo contrato que la versión regla: mismo `operacion` (registrar_fact),
mismas claves de `contenido` — únicamente cambia CÓMO se verifica la
señal (P13). Sin `confianza`: ese campo no existe en un fact (INV-4/5,
la asimetría estructural — ya visible en Evaluar, ahora en la segunda
capacidad fact-producer).

Igual que Evaluar (PR-5): `senal` es una función pura de datos ya
presentes en el estado (`incorrectos`/`total`, del fact de Evaluar) —
`_senal()` en la versión regla. Un sondeo real (Engineering Review
previa, M3 PR-6) mostró que, sin grounding, el modelo no solo falla en
la forma del JSON: contradice el umbral del dominio (responde
`frustracion` donde la regla exige `confusion` con los mismos números)
y rompe el vocabulario cerrado (`frustration`/`fluency` en inglés). Por
eso el roundtrip aquí valida solo forma/disponibilidad del proveedor;
`senal` se construye siempre con `_senal()` — el conocimiento del
dominio permanece anclado en la regla determinista.
"""

from __future__ import annotations

from runtime.domain.shared.llm_roundtrip import ejecutar_roundtrip
from runtime.domain.tutorizar.productor import _senal
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
            f"El sistema calculó incorrectos={incorrectos} total={total}. "
            f"Confirma que el proveedor está disponible respondiendo JSON "
            f'con esta forma EXACTA: "razonamiento" (STRING, breve), luego '
            f'"senal" (STRING, uno de exactamente estos tres valores: '
            f'"confusion", "frustracion", "fluidez").'
        )
        # El roundtrip solo verifica que el proveedor responde con la
        # forma esperada; el contenido del fact nunca proviene de esta
        # respuesta (ver docstring del módulo — el LLM confirma, no
        # clasifica).
        ejecutar_roundtrip(proveedor, prompt, campos_requeridos=("senal",))
        return (
            TransitionIntent(
                productor=Capacidad.TUTORIZAR,
                operacion="registrar_fact",
                argumentos={
                    "autor": Capacidad.TUTORIZAR,
                    "contenido": {
                        "senal": _senal(incorrectos, total),
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
