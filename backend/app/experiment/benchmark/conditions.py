"""
Benchmark Conditions — 6 configuraciones experimentales para evaluación
académica del sistema multi-agente pedagógico.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class BenchmarkConditions(str, Enum):
    """Las 6 condiciones del benchmark académico."""

    SINGLE_AGENT_STATIC = "single-agent_static"
    SWARM_FULL = "swarm_full"
    SWARM_NO_RETRIEVAL = "swarm_no_retrieval"
    SWARM_NO_MEMORY = "swarm_no_memory"
    SWARM_NO_REVIEWER = "swarm_no_reviewer"
    SWARM_STATIC_PEDAGOGY = "swarm_static_pedagogy"


CONDITION_METADATA: dict[BenchmarkConditions, dict[str, Any]] = {
    BenchmarkConditions.SINGLE_AGENT_STATIC: {
        "label": "Agente Único Estático",
        "description": "Agente pedagógico único sin adaptación, recuperación, memoria ni revisión.",
        "type": "control",
        "agents_enabled": [
            "PedagogicalAgent",
        ],
        "retrieval_enabled": False,
        "memory_enabled": False,
        "reviewer_enabled": False,
        "adaptive_pedagogy": False,
        "consensus_enabled": False,
    },
    BenchmarkConditions.SWARM_FULL: {
        "label": "Enjambre Completo",
        "description": "Sistema completo con todos los agentes, recuperación, memoria y revisión.",
        "type": "treatment",
        "agents_enabled": [
            "ResearchAgent",
            "PedagogicalAgent",
            "AdaptiveLearningAgent",
            "MultimodalPlanningAgent",
            "PromptEngineeringAgent",
            "ConsistencyAgent",
            "ConsensusMediatorAgent",
        ],
        "retrieval_enabled": True,
        "memory_enabled": True,
        "reviewer_enabled": True,
        "adaptive_pedagogy": True,
        "consensus_enabled": True,
    },
    BenchmarkConditions.SWARM_NO_RETRIEVAL: {
        "label": "Enjambre sin Recuperación",
        "description": "Enjambre completo sin ResearchAgent (Tavily/retrieval).",
        "type": "ablation",
        "agents_enabled": [
            "PedagogicalAgent",
            "AdaptiveLearningAgent",
            "MultimodalPlanningAgent",
            "PromptEngineeringAgent",
            "ConsistencyAgent",
            "ConsensusMediatorAgent",
        ],
        "retrieval_enabled": False,
        "memory_enabled": True,
        "reviewer_enabled": True,
        "adaptive_pedagogy": True,
        "consensus_enabled": True,
    },
    BenchmarkConditions.SWARM_NO_MEMORY: {
        "label": "Enjambre sin Memoria",
        "description": "Enjambre completo sin memoria compartida (SharedMemoryStore desactivado).",
        "type": "ablation",
        "agents_enabled": [
            "ResearchAgent",
            "PedagogicalAgent",
            "AdaptiveLearningAgent",
            "MultimodalPlanningAgent",
            "PromptEngineeringAgent",
            "ConsistencyAgent",
            "ConsensusMediatorAgent",
        ],
        "retrieval_enabled": True,
        "memory_enabled": False,
        "reviewer_enabled": True,
        "adaptive_pedagogy": True,
        "consensus_enabled": True,
    },
    BenchmarkConditions.SWARM_NO_REVIEWER: {
        "label": "Enjambre sin Revisor",
        "description": "Enjambre completo sin ConsistencyAgent (revisor de coherencia).",
        "type": "ablation",
        "agents_enabled": [
            "ResearchAgent",
            "PedagogicalAgent",
            "AdaptiveLearningAgent",
            "MultimodalPlanningAgent",
            "PromptEngineeringAgent",
            "ConsensusMediatorAgent",
        ],
        "retrieval_enabled": True,
        "memory_enabled": True,
        "reviewer_enabled": False,
        "adaptive_pedagogy": True,
        "consensus_enabled": True,
    },
    BenchmarkConditions.SWARM_STATIC_PEDAGOGY: {
        "label": "Enjambre con Pedagogía Estática",
        "description": "Enjambre completo pero con pedagogía no-adaptativa (sin ajuste por perfil).",
        "type": "ablation",
        "agents_enabled": [
            "ResearchAgent",
            "PedagogicalAgent",
            "MultimodalPlanningAgent",
            "PromptEngineeringAgent",
            "ConsistencyAgent",
            "ConsensusMediatorAgent",
        ],
        "retrieval_enabled": True,
        "memory_enabled": True,
        "reviewer_enabled": True,
        "adaptive_pedagogy": False,
        "consensus_enabled": True,
    },
}


@dataclass(frozen=True)
class BenchmarkCondition:
    """Condición experimental del benchmark."""

    name: BenchmarkConditions
    label: str
    description: str
    type: str  # control, treatment, ablation
    agents_enabled: list[str] = field(default_factory=list)
    retrieval_enabled: bool = True
    memory_enabled: bool = True
    reviewer_enabled: bool = True
    adaptive_pedagogy: bool = True
    consensus_enabled: bool = True

    @classmethod
    def from_enum(cls, condition: BenchmarkConditions) -> BenchmarkCondition:
        md = CONDITION_METADATA[condition]
        return cls(
            name=condition,
            label=md["label"],
            description=md["description"],
            type=md["type"],
            agents_enabled=list(md["agents_enabled"]),
            retrieval_enabled=md["retrieval_enabled"],
            memory_enabled=md["memory_enabled"],
            reviewer_enabled=md["reviewer_enabled"],
            adaptive_pedagogy=md["adaptive_pedagogy"],
            consensus_enabled=md["consensus_enabled"],
        )

    def config_dict(self) -> dict[str, Any]:
        return {
            "agents_enabled": list(self.agents_enabled),
            "retrieval_enabled": self.retrieval_enabled,
            "memory_enabled": self.memory_enabled,
            "reviewer_enabled": self.reviewer_enabled,
            "adaptive_pedagogy": self.adaptive_pedagogy,
            "consensus_enabled": self.consensus_enabled,
        }


def get_all_conditions() -> list[BenchmarkCondition]:
    return [BenchmarkCondition.from_enum(c) for c in BenchmarkConditions]


def get_condition(name: str) -> BenchmarkCondition | None:
    try:
        return BenchmarkCondition.from_enum(BenchmarkConditions(name))
    except ValueError:
        return None
