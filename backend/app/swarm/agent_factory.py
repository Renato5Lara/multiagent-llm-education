"""AgentFactory — creates and configures agent instances for a swarm context."""

from __future__ import annotations

import logging
from typing import Any

from app.db.uow import AsyncUnitOfWork, UnitOfWork
from app.memory.shared_memory import SharedMemoryStore

logger = logging.getLogger(__name__)


class AgentFactory:
    """Creates agent instances wired with shared dependencies.

    Ensures all agents use the same UoW, SharedMemory, and context identifiers.
    """

    def __init__(
        self,
        uow: UnitOfWork | AsyncUnitOfWork,
        student_id: str,
        course_id: str,
        context_key: str,
        shared_memory: SharedMemoryStore | None = None,
    ):
        self.uow = uow
        self.student_id = student_id
        self.course_id = course_id
        self.context_key = context_key
        self.shared_memory = shared_memory or SharedMemoryStore(uow)
        self._cache: dict[str, Any] = {}

    # ── Legacy agents (programming course pathway) ────────────────

    def create_pedagogical_agent(self):
        from app.agents.pedagogical_agent import PedagogicalAgent
        return PedagogicalAgent(
            agent_name="pedagogical_agent",
            uow=self.uow,
            student_id=self.student_id,
            course_id=self.course_id,
            context_key=self.context_key,
            shared_memory=self.shared_memory,
        )

    def create_structural_pedagogical_agent(self):
        from app.agents.structural_pedagogical_agent import StructuralPedagogicalAgent
        return StructuralPedagogicalAgent(
            agent_name="structural_pedagogical_agent",
            uow=self.uow,
            student_id=self.student_id,
            course_id=self.course_id,
            context_key=self.context_key,
            shared_memory=self.shared_memory,
        )

    def create_adaptive_agent(self):
        from app.agents.adaptive_agent import AdaptiveAgent
        return AdaptiveAgent(
            agent_name="adaptive_agent",
            uow=self.uow,
            student_id=self.student_id,
            course_id=self.course_id,
            context_key=self.context_key,
            shared_memory=self.shared_memory,
        )

    def create_risk_agent(self):
        from app.agents.risk_agent import RiskAgent
        return RiskAgent(
            agent_name="risk_agent",
            uow=self.uow,
            student_id=self.student_id,
            course_id=self.course_id,
            context_key=self.context_key,
            shared_memory=self.shared_memory,
        )

    def create_evaluation_agent(self):
        from app.agents.evaluation_agent import EvaluationAgent
        return EvaluationAgent(
            agent_name="evaluation_agent",
            uow=self.uow,
            student_id=self.student_id,
            course_id=self.course_id,
            context_key=self.context_key,
            shared_memory=self.shared_memory,
        )

    def create_all(self) -> dict[str, Any]:
        """Create all four legacy agents."""
        return {
            "pedagogical": self.create_pedagogical_agent(),
            "adaptive": self.create_adaptive_agent(),
            "risk": self.create_risk_agent(),
            "evaluation": self.create_evaluation_agent(),
        }

    # ── New pedagogical orchestration agents ──────────────────────

    def create_research_agent(self):
        from app.agents.research_agent import ResearchAgent
        return ResearchAgent(
            agent_name="research_agent",
            uow=self.uow,
            student_id=self.student_id,
            course_id=self.course_id,
            context_key=self.context_key,
            shared_memory=self.shared_memory,
        )

    def create_adaptive_learning_agent(self):
        from app.agents.adaptive_learning_agent import AdaptiveLearningAgent
        return AdaptiveLearningAgent(
            agent_name="adaptive_learning_agent",
            uow=self.uow,
            student_id=self.student_id,
            course_id=self.course_id,
            context_key=self.context_key,
            shared_memory=self.shared_memory,
        )

    def create_multimodal_planning_agent(self):
        from app.agents.multimodal_planning_agent import MultimodalPlanningAgent
        return MultimodalPlanningAgent(
            agent_name="multimodal_planning_agent",
            uow=self.uow,
            student_id=self.student_id,
            course_id=self.course_id,
            context_key=self.context_key,
            shared_memory=self.shared_memory,
        )

    def create_prompt_engineering_agent(self):
        from app.agents.prompt_engineering_agent import PromptEngineeringAgent
        return PromptEngineeringAgent(
            agent_name="prompt_engineering_agent",
            uow=self.uow,
            student_id=self.student_id,
            course_id=self.course_id,
            context_key=self.context_key,
            shared_memory=self.shared_memory,
        )

    def create_consistency_agent(self):
        from app.agents.consistency_agent import ConsistencyAgent
        return ConsistencyAgent(
            agent_name="consistency_agent",
            uow=self.uow,
            student_id=self.student_id,
            course_id=self.course_id,
            context_key=self.context_key,
            shared_memory=self.shared_memory,
        )

    def create_consensus_mediator(self):
        from app.agents.consensus_mediator import ConsensusMediator
        return ConsensusMediator(
            agent_name="consensus_mediator",
            uow=self.uow,
            student_id=self.student_id,
            course_id=self.course_id,
            context_key=self.context_key,
            shared_memory=self.shared_memory,
        )

    def create_all_orchestration_agents(self) -> dict[str, Any]:
        """Create all seven orchestration agents for the pedagogical pipeline."""
        return {
            "structural_pedagogical": self.create_structural_pedagogical_agent(),
            "research": self.create_research_agent(),
            "adaptive_learning": self.create_adaptive_learning_agent(),
            "multimodal_planning": self.create_multimodal_planning_agent(),
            "prompt_engineering": self.create_prompt_engineering_agent(),
            "consistency": self.create_consistency_agent(),
            "consensus_mediator": self.create_consensus_mediator(),
        }
