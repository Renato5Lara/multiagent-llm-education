"""Utilidades compartidas de los reducers (RFC-0003 §4; ADR-0004 E-1).

Solo mecanismo de rechazo-registrado: aquí no vive —ni vivirá— lógica de
negocio (pregunta anti-deriva n.º 1 del Prompt Maestro).
"""

from __future__ import annotations

import re

from runtime.kernel.events import TransicionRechazada
from runtime.kernel.reducers.resultado import Rechazado

_TOKEN_NORMA = re.compile(r"^[A-Z][A-Z0-9-]*$")


def norma_de(violacion: ValueError, por_defecto: str = "INV-5") -> str:
    """Extrae la norma del mensaje del sobre ("INV-5: …", "A1: …")."""
    prefijo = str(violacion).split(":", 1)[0].split()[0]
    return prefijo if _TOKEN_NORMA.match(prefijo) else por_defecto


def rechazo(indice: int, norma: str, motivo: str) -> Rechazado:
    """Construye el rechazo con su evento — jamás una excepción silenciosa."""
    return Rechazado(
        invariante=norma,
        motivo=motivo,
        eventos=(
            TransicionRechazada(transicion=indice, invariante=norma, motivo=motivo),
        ),
    )
