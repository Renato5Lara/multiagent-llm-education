"""R23→R26 — instrumento D1 graduado.

**Promovido a producción (R26)**: la implementación real vive ahora en
`app.services.cmg_evaluation_service` (`D1GraduadoResultado`,
`evaluar_d1_graduado`), reutilizada también dentro de `evaluar_d1()`
productivo — una única implementación, nunca copiada dos veces (R26
§2: "no copiar nuevamente la lógica").

Este módulo queda como RE-EXPORTACIÓN — preserva exactamente la ruta de
import que R23/R24 ya establecieron (`from experiments.d1_graduado_piloto
import evaluar_d1_graduado, D1GraduadoResultado`, y las funciones
auxiliares `_normalizar`/`_contiene_alguna_forma`/`_palabras_clave` que
`experiments/d1_adversarial_pilot.py` ya usa) — sus pilotos (R23/R24) y
tests (`tests/test_r23_*`, `tests/test_r24_*`) siguen funcionando sin
ningún cambio, ahora contra la MISMA implementación que Corrida 2 usará
en la ruta real de evaluación.
"""

from __future__ import annotations

from app.services.cmg_evaluation_service import (
    D1GraduadoResultado,
    _contiene_alguna_forma,
    _normalizar,
    _palabras_clave,
    evaluar_d1_graduado,
)

__all__ = [
    "D1GraduadoResultado",
    "evaluar_d1_graduado",
    "_contiene_alguna_forma",
    "_normalizar",
    "_palabras_clave",
]
