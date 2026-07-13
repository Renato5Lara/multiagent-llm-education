"""Qué implementación de cada capacidad corre en las invocaciones reales
del walkthrough (P13: "el modelo de lenguaje es una dependencia
inyectada en el borde — cambiar de proveedor no toca el Kernel, el
Engine ni el grafo"; ADR-0007 clasifica Diagnosticar, Remediar y
Orientar como CLAIM: el LLM sí puede ser la fuente del veredicto o la
propuesta, declarando la regla de dominio en el prompt).

LLM si hay credencial real configurada (mismo criterio de detección que
`OpenAIProvider`/M3: `OPENAI_API_KEY`); si no, la regla — el
comportamiento de hoy, sin degradación silenciosa a mitad de sesión (la
credencial no cambia dentro de una misma petición HTTP).

`runtime/engine/graph/walkthrough.py` NO cambia sus valores por
defecto — siguen siendo la regla, para que la suite determinista (P12)
no dependa de red. Esta selección vive en el Boundary porque es quien
construye cada invocación real de `ejecutar_walkthrough`; los tests que
exigen una implementación concreta (P13, guardianes ADR-0005 §7) siguen
pasándola explícitamente, sin pasar por aquí.
"""

from __future__ import annotations

import os
from functools import partial
from typing import Callable

from runtime.domain.diagnosticar import producir as producir_diagnostico_regla
from runtime.domain.diagnosticar import producir_llm as producir_diagnostico_llm
from runtime.domain.orientar import producir as producir_orientacion_regla
from runtime.domain.orientar import producir_llm as producir_orientacion_llm
from runtime.domain.remediar import producir as producir_remediacion_regla
from runtime.domain.remediar import producir_llm as producir_remediacion_llm
from runtime.domain.shared.llm_openai import OpenAIProvider


def productor_diagnostico_activo() -> Callable:
    if os.environ.get("OPENAI_API_KEY"):
        return partial(producir_diagnostico_llm, proveedor=OpenAIProvider())
    return producir_diagnostico_regla


def productor_remediar_activo() -> Callable:
    if os.environ.get("OPENAI_API_KEY"):
        return partial(producir_remediacion_llm, proveedor=OpenAIProvider())
    return producir_remediacion_regla


def productor_orientar_activo() -> Callable:
    if os.environ.get("OPENAI_API_KEY"):
        return partial(producir_orientacion_llm, proveedor=OpenAIProvider())
    return producir_orientacion_regla
