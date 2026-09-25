"""CR y resumen de convergencia (DECISION-CLOSURE §10, DEC-10):
CR = proporción de ciclos con stop_reason == "epsilon" (paró por convergencia real, no por agotar
iteraciones). T_conv se reporta en iteraciones (k_stop) y en milisegundos. La regla de parada NO se
modifica; solo se instrumenta su reporte."""

from __future__ import annotations

import statistics
from typing import Sequence

from adaptation_swarm.metrics.cycle import CycleMetrics


def convergence_rate(metrics: Sequence[CycleMetrics]) -> float:
    done = [m for m in metrics if m.status == "completed"]
    if not metrics:
        raise ValueError("sin ciclos")
    return sum(1 for m in done if m.stop_reason == "epsilon") / len(metrics)


def convergence_summary(metrics: Sequence[CycleMetrics]) -> dict:
    ok = [m for m in metrics if m.status == "completed"]
    iters = [m.k_stop for m in ok if m.k_stop is not None]
    ms = [m.t_conv_ms for m in ok if m.t_conv_ms is not None]
    by_reason = {r: sum(1 for m in metrics if m.stop_reason == r) for r in ("epsilon", "k_max", "error")}
    return {
        "n": len(metrics), "completed": len(ok), "failed": len(metrics) - len(ok),
        "CR": convergence_rate(metrics), "stop_reasons": by_reason,
        "k_stop": {"mean": statistics.fmean(iters) if iters else None, "median": statistics.median(iters) if iters else None,
                   "max": max(iters) if iters else None},
        "t_conv_ms": {"mean": statistics.fmean(ms) if ms else None, "median": statistics.median(ms) if ms else None,
                      "max": max(ms) if ms else None},
    }
