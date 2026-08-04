"""Calibración de confianza — infraestructura compartida (ADR-0013).

`evidence_strength` es matemática pura, sin conocimiento de dominio: el
límite inferior de un intervalo de Wilson (95%) sobre una proporción
`soporte/total`. Vive aquí, no en una capacidad concreta, por la misma
razón que `llm_roundtrip.py`/`propuestas.py`/`objetivos.py` — ninguna
capacidad la posee, todas pueden reutilizarla sin conocerse entre sí (P3).

Relocalizada desde `runtime/domain/diagnosticar/calibracion.py` (Iteración
5.5/5.8, H10) al generalizarse a Remediar y Orientar (ADR-0013) — el resto
de esa calibración (`calibrar_confianza_nueva`, la semántica de mejora/
retroceso contra un claim vigente del mismo asunto) es específica del
modelo temporal de Diagnosticar y permanece donde estaba.
"""

from __future__ import annotations

import math
from decimal import Decimal

_Z_95 = 1.96


def evidence_strength(soporte: int, total: int) -> Decimal:
    """Límite inferior de Wilson (95%) sobre `soporte/total` — fuerza
    estadística de UNA observación individual (Iteración 5.5). `total
    <= 0` devuelve `0` (sin evidencia, sin fuerza)."""
    if total <= 0:
        return Decimal("0")
    p = soporte / total
    n = total
    denom = 1 + _Z_95**2 / n
    centro = (p + _Z_95**2 / (2 * n)) / denom
    margen = _Z_95 * math.sqrt(p * (1 - p) / n + _Z_95**2 / (4 * n**2)) / denom
    return Decimal(str(max(0.0, centro - margen)))
