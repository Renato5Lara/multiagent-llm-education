"""Guardia de regresión: app/experiment/benchmark/ sigue siendo importable
sin app/experiment/__init__.py (retirado en ADR-0017 Fase 4+5).

app/experiment/benchmark/ está fuera del alcance de ADR-0017
(UNAUDITED_SUBDIRECTORIES en scripts/audit_consensus_cluster.py) y se
preservó deliberadamente. Su padre `app.experiment` ya no tiene
__init__.py propio, así que Python solo puede resolverlo como paquete de
espacio de nombres implícito (PEP 420). Este test existe para que una
limpieza futura de app/experiment/ (p.ej. borrar el directorio vacío
percibido, o "normalizar" el árbol) no rompa este subsistema en
silencio — ver ADR-0017 §7, punto 4+5.
"""

from __future__ import annotations

import os


def test_app_experiment_has_no_own_init():
    import app.experiment

    assert app.experiment.__file__ is None, (
        "app/experiment/__init__.py no debería existir — si este assert "
        "falla, alguien lo recreó y este test ya no protege nada útil, "
        "pero tampoco hay riesgo: el import explícito de abajo seguiría "
        "funcionando de cualquier forma."
    )


def test_app_experiment_benchmark_imports_as_namespace_subpackage():
    from app.experiment.benchmark import (
        BenchmarkCondition,
        BenchmarkOrchestrator,
        MetricsCalculator,
        StatisticalTestSuite,
    )

    assert BenchmarkCondition is not None
    assert BenchmarkOrchestrator is not None
    assert MetricsCalculator is not None
    assert StatisticalTestSuite is not None
