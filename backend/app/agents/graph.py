"""
Grafo LangGraph del sistema multiagente.
Define el flujo: diagnóstico -> planificador -> recomendador -> evaluador.
"""

import logging
from typing import Any

from app.agents.nodes import (
    diagnostic_analyzer,
    path_planner,
    content_recommender,
    evaluation_generator,
)

logger = logging.getLogger(__name__)


def build_agent_graph():
    """
    Construye el grafo de agentes usando StateGraph de LangGraph.

    El flujo es:
      diagnostic_analyzer -> path_planner -> content_recommender -> evaluation_generator

    Cada nodo recibe y actualiza un diccionario de estado compartido.
    """
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

        builder = StateGraph(AgentState)

        builder.add_node("diagnostic_analyzer", diagnostic_analyzer)
        builder.add_node("path_planner", path_planner)
        builder.add_node("content_recommender", content_recommender)
        builder.add_node("evaluation_generator", evaluation_generator)

        builder.set_entry_point("diagnostic_analyzer")
        builder.add_edge("diagnostic_analyzer", "path_planner")
        builder.add_edge("path_planner", "content_recommender")
        builder.add_edge("content_recommender", "evaluation_generator")
        builder.add_edge("evaluation_generator", END)

        return builder.compile()

    except ImportError:
        logger.warning("LangGraph no instalado. Usando ejecución secuencial directa.")
        return None


def run_agent_sequence(state: dict) -> dict:
    """
    Ejecuta la secuencia de agentes sin LangGraph (fallback).
    """
    logger.info("Ejecutando secuencia de agentes (modo fallback)")

    result = diagnostic_analyzer(state)
    state.update(result)

    result = path_planner(state)
    state.update(result)

    result = content_recommender(state)
    state.update(result)

    result = evaluation_generator(state)
    state.update(result)

    return state


agent_graph = build_agent_graph()


def run_agents(state: dict) -> dict:
    if agent_graph is not None:
        logger.info("Ejecutando agentes con LangGraph")
        return agent_graph.invoke(state)
    return run_agent_sequence(state)
