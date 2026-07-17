"""Cuarentena de BaseAgent (CLAUDE.md 2026-07-12; Sprint 3.2).

`app/agents` está retirado del flujo en vivo: sus únicos consumidores
legítimos son el laboratorio experimental (`app/experiment`, grupo de
control CONCEPT-0001/D-001) y el swarm demo del Modo Evidencia
(`app/swarm`, `app/demo`). Este test convierte esa regla de auditoría
manual en una garantía ejecutable: si un import nuevo de `app.agents`
aparece en el flujo de producto, la suite falla nombrando el archivo.

La verificación es por AST (import exacto), no por grep de texto — la
lección de la corrección de auditoría del 2026-07-12: el grep por
nombre de clase produjo falsos positivos; el rastreo por import, no.
"""

from __future__ import annotations

import ast
from pathlib import Path

APP = Path(__file__).resolve().parent.parent / "app"

CUARENTENA = "app.agents"

CONSUMIDORES_LEGITIMOS = (
    APP / "agents",      # el propio paquete
    APP / "experiment",  # grupo de control D-001
    APP / "swarm",       # swarm demo (Modo Evidencia)
    APP / "demo",        # demo orchestrator (Modo Evidencia)
)


def _importa_cuarentena(archivo: Path) -> bool:
    arbol = ast.parse(archivo.read_text(encoding="utf-8"))
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Import):
            if any(
                alias.name == CUARENTENA or alias.name.startswith(CUARENTENA + ".")
                for alias in nodo.names
            ):
                return True
        elif isinstance(nodo, ast.ImportFrom):
            modulo = nodo.module or ""
            if modulo == CUARENTENA or modulo.startswith(CUARENTENA + "."):
                return True
    return False


def test_ningun_flujo_de_producto_importa_app_agents():
    violaciones = [
        str(archivo.relative_to(APP.parent))
        for archivo in sorted(APP.rglob("*.py"))
        if not any(archivo.is_relative_to(d) for d in CONSUMIDORES_LEGITIMOS)
        and _importa_cuarentena(archivo)
    ]
    assert violaciones == [], (
        "app.agents está en cuarentena (solo laboratorio/Modo Evidencia); "
        f"imports nuevos detectados en el flujo de producto: {violaciones}"
    )


def test_el_laboratorio_sigue_siendo_el_unico_consumidor_real():
    """Documenta el estado actual: hoy el único import directo vivo es
    `app/swarm/agent_factory.py`. Si este test falla porque la lista
    creció DENTRO del laboratorio, actualizarla es legítimo; si el
    consumo directo desapareció por completo, la épica de eliminación
    física de BaseAgent (decisión del tesista sobre D-001) tiene luz
    verde técnica."""
    consumidores = [
        str(archivo.relative_to(APP.parent))
        for archivo in sorted(APP.rglob("*.py"))
        if not archivo.is_relative_to(APP / "agents")
        and _importa_cuarentena(archivo)
    ]
    assert consumidores == ["app/swarm/agent_factory.py"]
