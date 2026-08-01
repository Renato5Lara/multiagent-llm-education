"""Estructura de curso como parámetro externo de Orientar/Remediar
(DESIGN-orientar-ruta-completa.md) — igual patrón que `politica`/
`urgente` en `_nodo_deliberar`: información que el Boundary conoce y el
Kernel/Engine no necesita interpretar, nunca un nuevo tipo de fact (la
estructura del curso no es evidencia observada del estudiante, RFC-0003).
"""

from __future__ import annotations

from typing import NamedTuple


class ObjetivoOrdenado(NamedTuple):
    """Un objetivo de aprendizaje de la plataforma, reducido a lo que
    Orientar/Remediar necesitan saber de él."""

    id: str
    asunto: str  # normalizar_asunto(objetivo.title) -- mismo slug que usa
    # Diagnosticar para "dominio(...)" -- ver runtime/domain/diagnosticar/productor.py
    orden: int


def asunto_avance(asunto_objetivo: str) -> str:
    """Asunto por objetivo para la tensión avanzar/reforzar -- distinto de
    `"siguiente-paso(sesion)"` (adaptación en vivo dentro de una sesión):
    este es por objetivo, para la planificación de ruta. Ambos coexisten;
    ninguno reemplaza al otro."""
    return f"avance({asunto_objetivo})"
