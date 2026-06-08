"""RealConditionExecutor — calls the actual PedagogicalOrchestrationService for each condition."""

from __future__ import annotations

import logging
import time
import uuid
from typing import Any

from app.db.session import AsyncSessionLocal
from app.experiment.benchmark.conditions import BenchmarkCondition
from app.experiment.benchmark.scenarios import BenchmarkScenario
from app.memory.shared_memory import SharedMemoryStore

from app.experiment.benchmark.real.noop_memory import NoopMemoryStore
from app.experiment.benchmark.real.safety import (
    ExperimentOutcome,
    SafetyConfig,
    safe_execute,
)

logger = logging.getLogger(__name__)


async def execute_condition_pipeline(
    scenario: BenchmarkScenario,
    condition: BenchmarkCondition,
    seed: int,
    safety: SafetyConfig,
) -> ExperimentOutcome:
    """Execute the REAL PedagogicalOrchestrationService for a scenario+condition.

    Unlike the old version that manually duplicated the agent pipeline,
    this creates the production service and calls orchestrate() directly.
    All wiring (replay, sandbox, SSE, observability) fires naturally.

    Ablation conditions are injected via state dict flags:
        _retrieval_enabled, _reviewer_enabled, _adaptive_pedagogy,
        _condition_name, _benchmark_seed, _sandbox_enabled
    """
    session_id = str(uuid.uuid4())[:12]
    label = f"{condition.name}_{scenario.scenario_id[:8]}_{session_id}"

    profile = scenario.student_profile or {}
    topic = _derive_topic(scenario)
    objectives = [o.get("description", "") for o in (scenario.learning_objectives or [])]
    if not objectives:
        objectives = [f"Master {c}" for c in (scenario.concepts or ["programming"])]

    pedagogical_intention = profile.get("pedagogical_intention", "")
    syllabus = scenario.metadata.get("syllabus", "")
    thematic_structure = scenario.concepts or []

    async def _execute() -> dict[str, Any]:
        from app.services.pedagogical_orchestration_service import (
            PedagogicalOrchestrationService,
        )
        from app.db.uow import AsyncUnitOfWork

        async with AsyncUnitOfWork(lambda: AsyncSessionLocal()) as uow:
            memory = (
                NoopMemoryStore()
                if not condition.memory_enabled
                else SharedMemoryStore(uow)
            )

            sandbox = _get_sandbox()

            service = PedagogicalOrchestrationService(
                uow=uow,
                shared_memory=memory,
                sandbox=sandbox,
            )

            condition_name = (
                condition.name.value
                if hasattr(condition.name, "value")
                else str(condition.name)
            )

            result = await service.orchestrate(
                topic=topic,
                learning_objectives=objectives,
                pedagogical_intention=pedagogical_intention,
                thematic_structure=thematic_structure,
                syllabus=syllabus,
                weekly_line="",
                student_id=scenario.student_id,
                course_id=scenario.course_id,
                multimodal_config={
                    "generate_text_directly": True,
                    "generate_image_directly": False,
                    "generate_audio_directly": False,
                    "generate_video_directly": False,
                    "generate_image_prompt": True,
                    "generate_audio_prompt": False,
                    "generate_video_prompt": False,
                    "section_modalities": {},
                },
                # Condition flags flow into orchestrate() so ablation conditions
                # actually skip the correct agents at runtime
                condition_flags={
                    "_retrieval_enabled": condition.retrieval_enabled,
                    "_reviewer_enabled": condition.reviewer_enabled,
                    "_adaptive_pedagogy": condition.adaptive_pedagogy,
                    "_consensus_enabled": condition.consensus_enabled,
                    "_condition_name": condition_name,
                    "_benchmark_seed": seed,
                },
            )

            result["_student_profile"] = profile
            result["_misconceptions"] = scenario.misconceptions
            result["_ground_truth"] = scenario.ground_truth
            result["_scenario_id"] = scenario.scenario_id
            result["_memory_enabled"] = condition.memory_enabled
            result["_sandbox_enabled"] = sandbox is not None

            return result

    return await safe_execute(
        _execute,
        safety=safety,
        experiment_label=label,
    )


def _derive_topic(scenario: BenchmarkScenario) -> str:
    """Derive a topic string from scenario fields."""
    concepts = scenario.concepts or []
    if concepts:
        return " & ".join(concepts[:3])
    if scenario.learning_objectives:
        first = scenario.learning_objectives[0]
        if isinstance(first, dict):
            return first.get("description", first.get("title", "Programming"))
        return str(first)
    return "Programming Concepts"


_SANDBOX_INSTANCE = None


def _get_sandbox():
    """Return a module-level singleton SandboxExecutor, or None if unavailable."""
    global _SANDBOX_INSTANCE
    if _SANDBOX_INSTANCE is not None:
        return _SANDBOX_INSTANCE
    try:
        from app.sandbox import SandboxExecutor
        _SANDBOX_INSTANCE = SandboxExecutor()
        return _SANDBOX_INSTANCE
    except Exception:
        return None
