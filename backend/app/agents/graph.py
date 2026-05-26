import logging
from typing import Any

from app.agents.nodes import (
    diagnostic_analyzer,
    path_planner,
    content_recommender,
    evaluation_generator,
    risk_analyzer,
)

logger = logging.getLogger(__name__)

# ── Distributed Tracing Integration ──────────────────────────────
try:
    from app.tracing import correlation_engine as _tracing_engine
    from app.tracing.langgraph import trace_langgraph_node as _trace_node
    from app.tracing.langgraph import TracingLangGraph as _TracingGraph
    _HAS_TRACING = True
except ImportError:
    _HAS_TRACING = False

if _HAS_TRACING:
    _traced = {
        name: _trace_node(_tracing_engine, name)(func)
        for name, func in [
            ("diagnostic_analyzer", diagnostic_analyzer),
            ("path_planner", path_planner),
            ("content_recommender", content_recommender),
            ("evaluation_generator", evaluation_generator),
            ("risk_analyzer", risk_analyzer),
        ]
    }
else:
    _traced = {
        "diagnostic_analyzer": diagnostic_analyzer,
        "path_planner": path_planner,
        "content_recommender": content_recommender,
        "evaluation_generator": evaluation_generator,
        "risk_analyzer": risk_analyzer,
    }


def build_agent_graph():
    try:
        from langgraph.graph import StateGraph, END
        from typing import TypedDict, Optional

        class AgentState(TypedDict):
            diagnostic_answers: Optional[dict]
            learning_profile: Optional[dict]
            profile_recommendations: Optional[list[str]]
            course_objectives: Optional[list[Any]]
            course_resources: Optional[list[Any]]
            learning_path_plan: Optional[dict]
            resource_recommendations: Optional[dict]
            evaluation_plan: Optional[list[dict]]
            prerequisites_completed: Optional[list[Any]]
            risk_data: Optional[dict]
            risk_prediction: Optional[dict]

        builder = StateGraph(AgentState)

        builder.add_node("diagnostic_analyzer", _traced["diagnostic_analyzer"])
        builder.add_node("path_planner", _traced["path_planner"])
        builder.add_node("content_recommender", _traced["content_recommender"])
        builder.add_node("evaluation_generator", _traced["evaluation_generator"])
        builder.add_node("risk_analyzer", _traced["risk_analyzer"])

        builder.set_entry_point("diagnostic_analyzer")
        builder.add_edge("diagnostic_analyzer", "path_planner")
        builder.add_edge("path_planner", "content_recommender")
        builder.add_edge("content_recommender", "evaluation_generator")

        builder.add_conditional_edges(
            "evaluation_generator",
            lambda s: "risk_analyzer" if (s.get("risk_data") is not None) else END,
            {"risk_analyzer": "risk_analyzer", END: END},
        )
        builder.add_edge("risk_analyzer", END)

        return builder.compile()

    except ImportError:
        logger.warning("LangGraph no instalado. Usando ejecución secuencial directa.")
        return None


def run_agent_sequence(state: dict) -> dict:
    logger.info("Ejecutando secuencia de agentes (modo fallback)")

    result = _traced["diagnostic_analyzer"](state)
    state.update(result)

    result = _traced["path_planner"](state)
    state.update(result)

    result = _traced["content_recommender"](state)
    state.update(result)

    result = _traced["evaluation_generator"](state)
    state.update(result)

    if state.get("risk_data"):
        result = _traced["risk_analyzer"](state)
        state.update(result)

    return state


agent_graph = build_agent_graph()


def run_agents(state: dict) -> dict:
    if agent_graph is not None:
        logger.info("Ejecutando agentes con LangGraph")
        if _HAS_TRACING and _tracing_engine.get_current() is not None:
            tg = _TracingGraph(_tracing_engine, agent_graph)
            return tg.invoke(state)
        return agent_graph.invoke(state)
    return run_agent_sequence(state)
