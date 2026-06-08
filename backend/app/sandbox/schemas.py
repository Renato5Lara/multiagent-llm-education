from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class SandboxStatus(str, Enum):
    SUCCESS = "success"
    RUNTIME_ERROR = "runtime_error"
    TIMEOUT = "timeout"
    MEMORY_LIMIT = "memory_limit"
    SECURITY_VIOLATION = "security_violation"
    INFRASTRUCTURE_ERROR = "infrastructure_error"


class SecurityViolation(BaseModel):
    rule: str
    message: str
    line: int | None = None
    symbol: str | None = None


class SandboxLimits(BaseModel):
    timeout_seconds: int = Field(default=10, ge=1, le=10)
    memory_mb: int = Field(default=512, ge=64, le=512)
    pids_limit: int = Field(default=64, ge=16, le=128)
    stdout_limit_chars: int = Field(default=20_000, ge=1_000, le=100_000)
    stderr_limit_chars: int = Field(default=20_000, ge=1_000, le=100_000)


class SandboxRequest(BaseModel):
    code: str = Field(..., min_length=1)
    stdin: str = ""
    test_code: str = ""
    filename: str = "student_code.py"
    limits: SandboxLimits = Field(default_factory=SandboxLimits)
    metadata: dict[str, Any] = Field(default_factory=dict)


class SandboxResult(BaseModel):
    status: SandboxStatus
    success: bool
    stdout: str = ""
    stderr: str = ""
    traceback: str = ""
    execution_time_ms: float = 0.0
    memory_usage_mb: float = 0.0
    exit_code: int | None = None
    timed_out: bool = False
    violations: list[SecurityViolation] = Field(default_factory=list)
    metrics: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)

    def to_replay_payload(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "success": self.success,
            "execution_time_ms": self.execution_time_ms,
            "memory_usage_mb": self.memory_usage_mb,
            "exit_code": self.exit_code,
            "timed_out": self.timed_out,
            "violations": [violation.model_dump() for violation in self.violations],
            "metrics": self.metrics,
            "stdout_preview": self.stdout[:500],
            "stderr_preview": self.stderr[:500],
            "traceback_preview": self.traceback[:1000],
            "metadata": self.metadata,
        }
