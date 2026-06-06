"""Multi-agent educational swarm — agent implementations for pedagogical orchestration."""

from app.agents.base import BaseAgent

# Legacy agents (kept for backward compatibility with programming pathway)
from app.agents.pedagogical_agent import PedagogicalAgent
from app.agents.adaptive_agent import AdaptiveAgent
from app.agents.risk_agent import RiskAgent
from app.agents.evaluation_agent import EvaluationAgent

# New pedagogical orchestration agents
from app.agents.structural_pedagogical_agent import StructuralPedagogicalAgent
from app.agents.research_agent import ResearchAgent
from app.agents.adaptive_learning_agent import AdaptiveLearningAgent
from app.agents.multimodal_planning_agent import MultimodalPlanningAgent
from app.agents.prompt_engineering_agent import PromptEngineeringAgent
from app.agents.consistency_agent import ConsistencyAgent
from app.agents.consensus_mediator import ConsensusMediator

__all__ = [
    "BaseAgent",
    # Legacy
    "PedagogicalAgent",
    "AdaptiveAgent",
    "RiskAgent",
    "EvaluationAgent",
    # New
    "StructuralPedagogicalAgent",
    "ResearchAgent",
    "AdaptiveLearningAgent",
    "MultimodalPlanningAgent",
    "PromptEngineeringAgent",
    "ConsistencyAgent",
    "ConsensusMediator",
]
