"""Estados del ciclo de adaptación (estado del grafo LangGraph de AG0)."""

from __future__ import annotations

from enum import Enum
from typing import Any, TypedDict


class StopReason(str, Enum):
    EPSILON = "epsilon"
    K_MAX = "k_max"
    ERROR = "error"


class CycleStatus(str, Enum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class CycleState(TypedDict, total=False):
    """Estado que fluye por el grafo de AG0. Contiene estructuras propias del
    ciclo (PSO, W, trazas); el PSO vive como `pso_state` (ver pso/engine.py)."""

    cycle_id: str
    correlation_id: str
    profile: dict[str, Any]
    seed: int
    W: dict[str, float]
    pso: Any
    pso_params: dict[str, Any]
    fitness_weights: dict[str, float]
    realized: dict[str, Any]           # variante -> pieza realizada (código, diagrama, texto, audio)
    iteration_log: list[dict[str, Any]]
    status: str
    stop_reason: str | None
    k_stop: int | None
    t_start_ns: int
    t_conv_ms: float | None
    package: dict[str, Any] | None
    error: dict[str, str] | None
    library_version: str
    # ── memoria de trabajo del ciclo (en el estado del grafo) ──
    rng: Any
    heuristic_start: list[float]
    W_meta: dict[str, Any]
    t_search_ns: int
    g_best: dict[str, Any]
    pso_diagnostics: dict[str, Any]
