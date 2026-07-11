"""El trío repetido en las cuatro capacidades LLM: prompt → texto → JSON.

Infraestructura, no dominio (no depende de Claim, Fact, ni de ninguna
capacidad concreta) — por eso vive en `domain/shared/`, no en cada
capacidad. Lo que NO se extrae, deliberadamente, es todo lo que Evaluar
demostró que varía por capacidad: la firma de `producir`, la operación
del reducer, el tipo de salida, el provenance por defecto. Ver
ADR-0005 §7 y el registro de la revisión post-Evaluar (memoria del
proyecto) — una clase base habría tenido que ramificar exactamente en
esos puntos.
"""

from __future__ import annotations

import json
from typing import Any

from runtime.domain.shared.llm import LLMProvider


def ejecutar_roundtrip(
    proveedor: LLMProvider, prompt: str, campos_requeridos: tuple[str, ...] = ()
) -> dict[str, Any]:
    """Prompt → texto del proveedor → JSON, con validación mínima de forma.

    No interpreta el contenido (P13: interpretar es trabajo de la
    capacidad). Una respuesta incompleta es un bug del prompt o del
    proveedor — E-2 (ADR-0004): se propaga, jamás se disfraza de rechazo
    de dominio (E-1).

    Solo lee `.texto` de la `LLMResponse` (M3): `usage`/`latencia_ms`/
    `finish_reason` son observabilidad futura, no dominio.
    """
    datos = json.loads(proveedor.generar(prompt).texto)
    faltantes = [campo for campo in campos_requeridos if campo not in datos]
    if faltantes:
        raise ValueError(
            f"ADR-0004 E-2: respuesta del proveedor LLM incompleta — "
            f"faltan campos {faltantes}"
        )
    return datos
