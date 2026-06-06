"""Python REPL Sandbox — isolated, hardened code execution for UPAO-MAS-EDU.

Architecture:
  Layer 1: AST policy (static analysis, pre-execution)
  Layer 2: Docker container (OS-level isolation, primary)
  Layer 3: Subprocess + resource limits (fallback)
  Layer 4: Security monitoring + metrics
  Layer 5: Deterministic cleanup + orphan prevention
"""

from app.sandbox.ast_policy import ASTSafetyPolicy, ValidationResult
from app.sandbox.docker_manager import (
    DockerManager,
    ContainerSpec,
    ContainerResult,
)
from app.sandbox.executor import SandboxExecutor, SubprocessSandbox
from app.sandbox.security_monitor import SecurityMonitor
from app.sandbox.cleanup import CleanupManager
from app.sandbox.metrics import collect_sandbox_metrics
from app.sandbox.exceptions import (
    SandboxError,
    SandboxTimeout,
    SandboxSecurityViolation,
    SandboxDockerError,
    classify,
)

__all__ = [
    "ASTSafetyPolicy",
    "ValidationResult",
    "DockerManager",
    "ContainerSpec",
    "ContainerResult",
    "SandboxExecutor",
    "SubprocessSandbox",
    "SecurityMonitor",
    "CleanupManager",
    "collect_sandbox_metrics",
    "SandboxError",
    "SandboxTimeout",
    "SandboxSecurityViolation",
    "SandboxDockerError",
    "classify",
]
