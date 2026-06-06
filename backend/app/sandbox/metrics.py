"""Sandbox metrics — exposed to observability and benchmark subsystems."""

from __future__ import annotations

from typing import Any

from app.sandbox.executor import SandboxExecutor
from app.sandbox.security_monitor import SecurityMonitor
from app.sandbox.docker_manager import DockerManager


def collect_sandbox_metrics(
    executor: SandboxExecutor | None = None,
    monitor: SecurityMonitor | None = None,
    docker: DockerManager | None = None,
) -> dict[str, Any]:
    """Collect all sandbox metrics for the observability dashboard."""
    metrics: dict[str, Any] = {
        "sandbox": {
            "version": "1.0.0",
            "status": "active" if executor else "unavailable",
        }
    }

    if executor:
        stats = executor.stats
        metrics["sandbox"]["executions"] = {
            "total": stats.get("total_executions", 0),
            "docker": stats.get("docker_executions", 0),
            "fallback": stats.get("fallback_executions", 0),
            "avg_time_ms": stats.get("avg_execution_time_ms", 0.0),
            "p95_time_ms": stats.get("p95_execution_time_ms", 0.0),
            "max_time_ms": stats.get("max_execution_time_ms", 0.0),
        }
        metrics["sandbox"]["errors"] = {
            "security_violations": stats.get("security_violations", 0),
            "timeouts": stats.get("timeouts", 0),
            "memory_exceeded": stats.get("memory_exceeded", 0),
            "execution_errors": stats.get("errors", 0),
        }
        if stats.get("violation_types"):
            metrics["sandbox"]["violation_types"] = stats["violation_types"]

    if monitor:
        metrics["sandbox"]["security"] = {
            "total_violations": monitor.total_violations,
            "classification": monitor.classification_breakdown(),
            "recent": monitor.latest_violations(limit=5),
        }

    if docker:
        metrics["sandbox"]["docker"] = {
            "available": docker.available,
            "active_containers": docker.active_count,
        }

    return metrics
