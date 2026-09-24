"""Diagnóstico del comportamiento del PSO (por iteración y por ciclo). Solo lectura sobre el estado del enjambre:
permite explicar científicamente qué hace el PSO sin modificar la especificación (ε, k_max, ecuaciones, φ, p_best, g_best)."""

from __future__ import annotations

from typing import Any, Sequence

import numpy as np


def _mean_pairwise(a: np.ndarray, metric: str) -> float:
    n = len(a)
    if n < 2:
        return 0.0
    diff = a[:, None, :] - a[None, :, :]
    d = np.sqrt((diff ** 2).sum(-1)) if metric == "l2" else np.abs(diff).sum(-1)
    return float(d[np.triu_indices(n, 1)].mean())


def swarm_diagnostics(x: np.ndarray, S: np.ndarray, F: np.ndarray) -> dict[str, Any]:
    """Estado del enjambre en una iteración: 𝓕 por partícula, posiciones discretas únicas, duplicadas y distancias."""
    n = len(S)
    unique_S = len({tuple(int(v) for v in row) for row in S})
    return {
        "F_min": float(F.min()), "F_mean": float(F.mean()), "F_max": float(F.max()), "F_std": float(F.std()),
        "unique_F": int(len(np.unique(np.round(F, 12)))),
        "unique_positions_S": unique_S,
        "duplicate_particles_pct": round(100.0 * (n - unique_S) / n, 3),
        "mean_pairwise_distance_x_l2": _mean_pairwise(np.asarray(x, float), "l2"),
        "mean_pairwise_distance_S_l1": _mean_pairwise(np.asarray(S, float), "l1"),
    }


def cycle_diagnostics(iterations: Sequence[dict[str, Any]], pbest_updates: Sequence[int],
                      gbest_updates: Sequence[bool], first_gbest_change_k: int | None) -> dict[str, Any]:
    """Resumen por ciclo: cuántos p_best/g_best se actualizaron y cuándo cambió g_best por primera vez."""
    return {
        "iterations_run": len(iterations),
        "pbest_updates_by_iteration": list(pbest_updates),
        "pbest_updates_after_init": int(sum(pbest_updates[1:])),
        "gbest_updates_after_init": int(sum(1 for u in gbest_updates[1:] if u)),
        "first_gbest_change_k": first_gbest_change_k,
        "gbest_never_changed_after_init": first_gbest_change_k is None,
        "mean_duplicate_particles_pct": float(np.mean([i["diagnostics"]["duplicate_particles_pct"] for i in iterations if "diagnostics" in i]))
        if iterations else None,
    }
