"""Grafo LangGraph de AG0 (DEC-11): controla el ciclo de adaptación.

    receive → profile → seed → evaluate ─┬─(no converge)→ advance → evaluate …
                                          └─(ε o k_max)──→ finalize → persist → END
    (cualquier nodo con error explícito)  → fail → persist → END

Cada nodo delega en `SwarmOrchestrator.step_*`; la comunicación con AG1–AG4 ocurre por Redis.
"""

from __future__ import annotations

import logging
from typing import Any, Awaitable, Callable

from langgraph.graph import END, START, StateGraph

from adaptation_swarm.schemas.errors import SwarmError
from adaptation_swarm.schemas.states import CycleState

log = logging.getLogger(__name__)

Node = Callable[[dict], Awaitable[dict]]


def _guard(fn: Node) -> Node:
    """Errores explícitos: el nodo que falla deja `error` en el estado; el grafo va a `fail`."""

    async def wrapped(state: dict) -> dict:
        if state.get("error"):
            return {}
        try:
            return await fn(state)
        except Exception as exc:
            log.warning("nodo %s falló: %s", fn.__name__, exc)
            kind = "swarm" if isinstance(exc, SwarmError) else "unexpected"
            return {"error": {"code": type(exc).__name__, "message": str(exc)[:500], "kind": kind}}

    wrapped.__name__ = fn.__name__
    return wrapped


def build_cycle_graph(orch):
    g = StateGraph(CycleState)
    g.add_node("receive", _guard(orch.step_receive))
    g.add_node("profile", _guard(orch.step_profile))
    g.add_node("seed", _guard(orch.step_seed))
    g.add_node("evaluate", _guard(orch.step_evaluate))
    g.add_node("advance", _guard(orch.step_advance))
    g.add_node("finalize", _guard(orch.step_finalize))
    g.add_node("fail", orch.step_fail)
    g.add_node("persist", orch.step_persist)

    def after(next_node: str):
        return lambda st: "fail" if st.get("error") else next_node

    g.add_edge(START, "receive")
    g.add_conditional_edges("receive", after("profile"), {"profile": "profile", "fail": "fail"})
    g.add_conditional_edges("profile", after("seed"), {"seed": "seed", "fail": "fail"})
    g.add_conditional_edges("seed", after("evaluate"), {"evaluate": "evaluate", "fail": "fail"})

    def after_evaluate(st: dict) -> str:
        if st.get("error"):
            return "fail"
        return orch.route_after_evaluate(st)

    g.add_conditional_edges("evaluate", after_evaluate, {"advance": "advance", "finalize": "finalize", "fail": "fail"})
    g.add_conditional_edges("advance", after("evaluate"), {"evaluate": "evaluate", "fail": "fail"})
    g.add_conditional_edges("finalize", after("persist"), {"persist": "persist", "fail": "fail"})
    g.add_edge("fail", "persist")
    g.add_edge("persist", END)
    return g.compile()
