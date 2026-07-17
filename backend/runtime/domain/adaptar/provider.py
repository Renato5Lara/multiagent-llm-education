"""FakeLLMProvider de Adaptar — determinista, sin red (ADR-0005 §3).

El proveedor propone modalidad/profundidad/andamiaje/alternativas EN
CATEGORÍAS PEDAGÓGICAS — jamás recursos físicos, IDs de contenido ni
URLs. Esa frontera pertenece al Boundary (RFC-0010), no al dominio.
"""

from __future__ import annotations

import re

from runtime.domain.shared.llm import LLMProvider, LLMResponse

# El módulo estándar de serialización JSON está reservado a un único
# punto (`engine/checkpoint/canonical.py`, ADR-0001) — este texto se
# construye a mano, mismo criterio que la versión anterior de este
# archivo (literales JSON escritos directamente), solo que ahora armados
# desde las tablas de arriba en vez de repetidos por rama.
def _texto_json(respuesta: dict) -> str:
    alternativas = ", ".join(
        f'{{"modalidad": "{a["modalidad"]}", "razon": "{a["razon"]}"}}'
        for a in respuesta["alternativas_descartadas"]
    )
    campos = [
        f'"modalidad": "{respuesta["modalidad"]}"',
        f'"profundidad": "{respuesta["profundidad"]}"',
    ]
    if "andamiaje" in respuesta:
        campos.append(f'"andamiaje": "{respuesta["andamiaje"]}"')
    campos.append(f'"alternativas_descartadas": [{alternativas}]')
    campos.append(f'"confianza": "{respuesta["confianza"]}"')
    return "{" + ", ".join(campos) + "}"

__all__ = ["LLMProvider", "FakeLLMProvider"]

# Mismo vocabulario cerrado que `ANDAMIAJE_POR_SENAL` en `productor.py`
# (tensión canónica #3 aparte, resuelta solo por `_SENAL_CONTRADICE_
# AVANZAR` en la regla) — duplicado deliberadamente aquí: este proveedor
# es un doble determinista de la regla, no debe importarla (P13 compara
# dos caminos independientes, no el mismo código dos veces).
_ANDAMIAJE_POR_SENAL = {
    "confusion": "ejemplo",
    "frustracion": "alternar-modalidad",
    "fluidez": "reto",
}

_RESPUESTA_POR_ACCION = {
    "reforzar": {
        "modalidad": "visual",
        "profundidad": "fundamentos",
        "alternativas_descartadas": [
            {"modalidad": "textual", "razon": "ya insuficiente en el intento anterior"},
            {"modalidad": "ejemplo-codigo", "razon": "prematuro sin el concepto consolidado"},
        ],
    },
    "avanzar-con-andamiaje": {
        "modalidad": "mixta",
        "profundidad": "aplicacion",
        "alternativas_descartadas": [
            {"modalidad": "solo-texto", "razon": "el andamiaje requiere apoyo visual"},
        ],
    },
}

_ALTERNATIVAS_POR_SENAL = {
    ("reforzar", "confusion"): [
        {"modalidad": "textual", "razon": "ya insuficiente en el intento anterior"},
        {"modalidad": "ejemplo-codigo", "razon": "prematuro sin el concepto consolidado"},
    ],
    ("reforzar", "frustracion"): [
        {"modalidad": "guiado", "razon": "riesgo de abandono: requiere acompañamiento antes que autonomía"},
        {"modalidad": "practica", "razon": "prematuro repetir ejercicios sin resolver la frustración"},
    ],
    ("avanzar-con-andamiaje", "fluidez"): [
        {"modalidad": "practica", "razon": "aún prematuro retirar el andamiaje sin una repetición más"},
        {"modalidad": "autonomo", "razon": "el estudiante todavía no demostró suficiente autonomía"},
    ],
    ("avanzar-con-andamiaje", "confusion"): [
        {"modalidad": "solo-texto", "razon": "el andamiaje requiere apoyo visual"},
    ],
    ("avanzar-con-andamiaje", "frustracion"): [
        {"modalidad": "mixta", "razon": "el resultado puntual dominó, pero la sesión mostró frustración real: retirar el andamiaje ahora sería prematuro"},
    ],
}


class FakeLLMProvider:
    """Determinista: mismo criterio que la regla, por un camino distinto —
    incluida la variación por señal de sesión (`ALTERNATIVAS_POR_SENAL`/
    `ANDAMIAJE_POR_SENAL`/`_SENAL_CONTRADICE_AVANZAR` en `productor.py`),
    para que el guardián de P13 compare lo mismo."""

    modelo = "fake-adaptacion-v1"
    version = "1"

    def generar(self, prompt: str) -> LLMResponse:
        accion_match = re.search(r"accion=([\w-]+)", prompt)
        senal_match = re.search(r"senal=(\w+)", prompt)
        accion = accion_match.group(1) if accion_match else None
        senal = senal_match.group(1) if senal_match and senal_match.group(1) != "None" else None

        base = _RESPUESTA_POR_ACCION.get(accion, _RESPUESTA_POR_ACCION["avanzar-con-andamiaje"])
        respuesta = dict(base)
        if senal is not None:
            alternativas = _ALTERNATIVAS_POR_SENAL.get((accion, senal))
            if alternativas is not None:
                respuesta["alternativas_descartadas"] = alternativas
            andamiaje = _ANDAMIAJE_POR_SENAL.get(senal)
            if andamiaje is not None:
                respuesta["andamiaje"] = andamiaje
            # Tensión canónica #3 (RFC-0002 §4) — mismo criterio que
            # `_SENAL_CONTRADICE_AVANZAR` en la regla.
            if accion == "avanzar-con-andamiaje" and senal == "frustracion":
                respuesta["profundidad"] = "fundamentos"
        respuesta["confianza"] = "0.80" if accion == "reforzar" else "0.75"
        return LLMResponse(texto=_texto_json(respuesta))
