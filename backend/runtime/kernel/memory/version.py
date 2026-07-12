"""Kernel de Memoria — qué debe persistirse (RFC-0005, ADR-0008). M4 PR-4.

Separación de responsabilidades (ADR-0008, precisión del tesista): el
Kernel decide QUÉ memoria debe persistirse — prepara y valida el
contenido; el Engine (`AlmacenMemoria`, `engine/checkpoint/`) decide
DÓNDE y CÓMO, incluida la numeración de versión (ADR-0008 §2.2: quien
escribe deriva el índice, nunca se declara desde fuera). Ningún
símbolo de este módulo toca SQL ni importa `engine/` — el Kernel es
puro (BLUEPRINT, verificado por
`test_BLUEPRINT_reglas_de_importacion.py::test_el_kernel_es_puro`).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from runtime.kernel.state.state import Identidad

#: RFC-0005 §2 — catálogo cerrado, exactamente estas cuatro claves.
_CLAVES_CATALOGO = frozenset(
    {"modelo_propuesto", "ruta_actualizada", "deuda_abierta", "resumen_destilado"}
)


@dataclass(frozen=True, slots=True)
class VersionMemoria:
    """Una versión de memoria, sin número asignado todavía — lo asigna
    `AlmacenMemoria.consolidar` (ADR-0008 §2.2)."""

    student_id: str
    session_id: str
    catalogo: Mapping[str, Any]


def preparar_version(identidad: Identidad, salidas: Mapping[str, Any]) -> VersionMemoria:
    """Envuelve exactamente el resultado de `proyectar_salidas()` (M4
    PR-2) con su procedencia — no recalcula nada, no reinterpreta
    claims ni decisiones (ADR-0008 §4)."""
    return VersionMemoria(
        student_id=identidad.student_id,
        session_id=identidad.session_id,
        catalogo=salidas,
    )


def validar_version(version: VersionMemoria) -> None:
    """Guardia de forma (ADR-0004 E-2): el catálogo debe tener
    exactamente las claves de RFC-0005 §2 — ni más ni menos. Una forma
    distinta es un defecto del software, se aborta ruidosamente antes
    de que `AlmacenMemoria` la toque."""
    claves = set(version.catalogo)
    if claves != _CLAVES_CATALOGO:
        raise ValueError(
            f"ADR-0008: el catálogo de la versión no tiene la forma de "
            f"RFC-0005 §2 — esperado {sorted(_CLAVES_CATALOGO)}, "
            f"recibido {sorted(claves)}"
        )
