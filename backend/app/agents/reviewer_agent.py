from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.agents.programmer_agent import GeneratedEducationalCode, ProgrammerAgent
from app.sandbox import SandboxRequest, SandboxResult, SandboxRunner, SandboxStatus


@dataclass(frozen=True)
class ReviewIteration:
    iteration: int
    code: str
    explanation: str
    sandbox_result: SandboxResult
    feedback: str
    correction_applied: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "iteration": self.iteration,
            "code": self.code,
            "explanation": self.explanation,
            "sandbox_result": self.sandbox_result.to_replay_payload(),
            "feedback": self.feedback,
            "correction_applied": self.correction_applied,
        }


@dataclass(frozen=True)
class CodeReviewResult:
    approved: bool
    iterations: list[ReviewIteration] = field(default_factory=list)
    final_code: str = ""
    final_feedback: str = ""
    metrics: dict[str, Any] = field(default_factory=dict)
    explainability_trace: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "approved": self.approved,
            "iterations": [iteration.to_dict() for iteration in self.iterations],
            "final_code": self.final_code,
            "final_feedback": self.final_feedback,
            "metrics": self.metrics,
            "explainability_trace": self.explainability_trace,
        }


class ReviewerAgent:
    """Runs ProgrammerAgent candidates through the sandbox with a 4-turn cap."""

    name = "reviewer"

    def __init__(
        self,
        *,
        sandbox: SandboxRunner | None = None,
        programmer: ProgrammerAgent | None = None,
        max_iterations: int = 4,
    ):
        self.sandbox = sandbox or SandboxRunner()
        self.programmer = programmer or ProgrammerAgent()
        self.max_iterations = max(1, min(4, max_iterations))

    async def review_until_validated(
        self,
        *,
        topic: str,
        objectives: list[str],
        initial: GeneratedEducationalCode | None = None,
    ) -> CodeReviewResult:
        iterations: list[ReviewIteration] = []
        candidate = initial
        feedback = ""
        correction_count = 0
        explainability_trace: list[dict[str, Any]] = []

        for iteration in range(1, self.max_iterations + 1):
            if candidate is None:
                candidate = await self.programmer.generate_code(
                    topic=topic,
                    objectives=objectives,
                    iteration=iteration,
                    reviewer_feedback=feedback,
                )
                if iteration > 1:
                    correction_count += 1

            sandbox_result = await self.sandbox.run(
                SandboxRequest(
                    code=candidate.code,
                    test_code=candidate.tests,
                    metadata={
                        **candidate.metadata,
                        "reviewer": self.name,
                        "objectives": objectives,
                    },
                )
            )
            feedback = self._feedback(sandbox_result)
            explainability_trace.append(self._trace_iteration(iteration, candidate, sandbox_result, feedback))
            iterations.append(
                ReviewIteration(
                    iteration=iteration,
                    code=candidate.code,
                    explanation=candidate.explanation,
                    sandbox_result=sandbox_result,
                    feedback=feedback,
                    correction_applied=iteration > 1,
                )
            )
            if sandbox_result.success:
                return CodeReviewResult(
                    approved=True,
                    iterations=iterations,
                    final_code=candidate.code,
                    final_feedback=feedback,
                    metrics=self._metrics(iterations, correction_count),
                    explainability_trace=explainability_trace,
                )
            candidate = None

        return CodeReviewResult(
            approved=False,
            iterations=iterations,
            final_code=iterations[-1].code if iterations else "",
            final_feedback=feedback,
            metrics=self._metrics(iterations, correction_count),
            explainability_trace=explainability_trace,
        )

    def _feedback(self, result: SandboxResult) -> str:
        if result.success:
            return "Codigo validado por sandbox: pruebas educativas pasan y no hay violaciones de seguridad."
        if result.status == SandboxStatus.SECURITY_VIOLATION:
            symbols = ", ".join(v.symbol or v.rule for v in result.violations)
            return f"Rechazado por politica de seguridad: {symbols}."
        if result.status == SandboxStatus.TIMEOUT:
            return "Rechazado por timeout: reducir complejidad o eliminar bucles no acotados."
        if result.status == SandboxStatus.MEMORY_LIMIT:
            return "Rechazado por memoria: evitar estructuras enormes o crecimiento no controlado."
        if result.traceback:
            return f"Rechazado por error de ejecucion: {result.traceback[-500:]}"
        return f"Rechazado por infraestructura o salida invalida: {result.stderr[:500]}"

    def _metrics(self, iterations: list[ReviewIteration], correction_count: int) -> dict[str, Any]:
        latest = iterations[-1].sandbox_result if iterations else None
        compilation_success = bool(latest and latest.status not in {SandboxStatus.SECURITY_VIOLATION, SandboxStatus.INFRASTRUCTURE_ERROR})
        execution_success = bool(latest and latest.success)
        execution_times = [self._numeric_metric(item.sandbox_result.execution_time_ms) for item in iterations]
        memory_usages = [self._numeric_metric(item.sandbox_result.memory_usage_mb) for item in iterations]
        return {
            "trajectory_length": len(iterations),
            "correction_loops": max(0, len(iterations) - 1),
            "correction_count": correction_count,
            "execution_success": execution_success,
            "compilation_success": compilation_success,
            "pass_fail": "pass" if execution_success else "fail",
            "avg_execution_time_ms": round(
                sum(execution_times) / max(1, len(execution_times)),
                2,
            ),
            "max_memory_usage_mb": round(
                max(memory_usages, default=0.0),
                3,
            ),
        }

    def _numeric_metric(self, value: Any) -> float:
        return float(value) if isinstance(value, int | float) else 0.0

    def _trace_iteration(
        self,
        iteration: int,
        candidate: GeneratedEducationalCode,
        result: SandboxResult,
        feedback: str,
    ) -> dict[str, Any]:
        return {
            "step": f"review_iteration_{iteration}",
            "agent": self.name,
            "status": result.status.value,
            "success": result.success,
            "evidence": {
                "tests_present": bool(candidate.tests.strip()),
                "stdout_len": len(result.stdout),
                "stderr_len": len(result.stderr),
                "violations": [violation.model_dump() for violation in result.violations],
            },
            "decision": feedback,
        }
