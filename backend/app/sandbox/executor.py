"""Code execution orchestrator — runs untrusted Python code with layered defense.

Defense layers:
1. AST policy (static analysis, pre-execution)
2. Docker container (OS-level isolation)
3. Subprocess fallback (when Docker unavailable) with resource limits
4. Timeout enforcement (asyncio + SIGKILL)
5. Memory limits (cgroups / setrlimit)
6. Cleanup guarantees (always destroy container)
"""

from __future__ import annotations

import asyncio
import logging
import os
import signal
import time
import uuid
from typing import Any

from app.sandbox.ast_policy import ASTSafetyPolicy, ValidationResult
from app.sandbox.docker_manager import (
    ContainerResult,
    ContainerSpec,
    DockerManager,
    DEFAULT_TIMEOUT,
    DEFAULT_MEMORY_LIMIT,
    DEFAULT_CPU_LIMIT,
)
from app.sandbox.exceptions import (
    SandboxError,
    SandboxSecurityViolation,
    SandboxTimeout,
    SandboxMemoryExceeded,
    SandboxResourceExhaustion,
    classify,
)
from app.sandbox.security_monitor import SecurityMonitor
from app.sandbox.cleanup import CleanupManager

logger = logging.getLogger(__name__)


class SubprocessSandbox:
    """Fallback sandbox using subprocess with resource limits.

    Used when Docker is not available. Provides weaker isolation
    but still enforces timeouts, memory limits, and AST policy.
    """

    def __init__(
        self,
        timeout: float = DEFAULT_TIMEOUT,
        memory_limit_mb: int = 256,
        max_output_bytes: int = 65536,
    ):
        self._timeout = timeout
        self._memory_limit_mb = memory_limit_mb
        self._max_output = max_output_bytes

    async def execute(self, code: str, stdin: str = "") -> ContainerResult:
        cid = str(uuid.uuid4())[:12]
        start = time.monotonic()

        wrapper = _build_subprocess_wrapper(code, self._memory_limit_mb)

        proc = await asyncio.create_subprocess_exec(
            sys_executable := _find_python(),
            "-c", wrapper,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            preexec_fn=_preexec_limits(self._memory_limit_mb),
        )

        try:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                proc.communicate(stdin.encode() if stdin else b""),
                timeout=self._timeout + 1.0,
            )
            stdout = stdout_bytes.decode("utf-8", errors="replace")[:self._max_output]
            stderr = stderr_bytes.decode("utf-8", errors="replace")[:self._max_output]
            elapsed = (time.monotonic() - start) * 1000

            return ContainerResult(
                container_id=cid,
                success=proc.returncode == 0,
                stdout=stdout,
                stderr=stderr,
                exit_code=proc.returncode,
                duration_ms=elapsed,
            )

        except asyncio.TimeoutError:
            try:
                proc.kill()
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            except (ProcessLookupError, AttributeError):
                pass
            elapsed = (time.monotonic() - start) * 1000
            return ContainerResult(
                container_id=cid, success=False,
                stdout="", stderr="",
                exit_code=None, duration_ms=elapsed,
                error="Execution timed out", timeout=True,
            )


class SandboxExecutor:
    """Unified sandbox executor with automatic fallback.

    Primary: Docker container (full isolation)
    Fallback: subprocess with resource limits (limited isolation)
    Always: AST policy validation first
    """

    def __init__(
        self,
        docker_manager: DockerManager | None = None,
        ast_policy: ASTSafetyPolicy | None = None,
        security_monitor: SecurityMonitor | None = None,
        cleanup: CleanupManager | None = None,
        timeout: float = DEFAULT_TIMEOUT,
        memory_limit_mb: int = 256,
        max_nodes: int = 500,
    ):
        self._docker = docker_manager or DockerManager()
        self._ast = ast_policy or ASTSafetyPolicy(max_nodes=max_nodes)
        self._monitor = security_monitor or SecurityMonitor()
        self._cleanup = cleanup or CleanupManager()
        self._timeout = timeout
        self._memory_limit_mb = memory_limit_mb
        self._fallback = SubprocessSandbox(
            timeout=timeout,
            memory_limit_mb=memory_limit_mb,
        )
        self._stats: dict[str, Any] = {
            "total_executions": 0,
            "docker_executions": 0,
            "fallback_executions": 0,
            "security_violations": 0,
            "timeouts": 0,
            "memory_exceeded": 0,
            "errors": 0,
            "violation_types": {},
            "execution_times_ms": [],
        }

    async def execute(
        self,
        code: str,
        stdin: str = "",
        timeout: float | None = None,
    ) -> dict[str, Any]:
        """Execute untrusted code with full sandbox defense."""
        exec_id = str(uuid.uuid4())[:12]
        effective_timeout = timeout or self._timeout
        start = time.monotonic()

        # ── Layer 1: AST policy ───────────────────────────────────
        validation: ValidationResult = self._ast.validate(code)
        if not validation:
            self._monitor.record_violation("ast_policy", validation.violations[0])
            self._stats["security_violations"] += 1
            vtype = "ast_policy"
            self._stats.setdefault("violation_types", {}).setdefault(vtype, 0)
            self._stats["violation_types"][vtype] += 1

            return {
                "exec_id": exec_id,
                "success": False,
                "stdout": "",
                "stderr": "",
                "error": f"Security violation: {validation.violations[0]}",
                "violation": True,
                "violation_type": vtype,
                "violation_detail": validation.violations[0],
                "duration_ms": 0.0,
                "method": "ast_policy",
            }

        # ── Layer 2: Docker (primary) ─────────────────────────────
        docker_ok = self._docker.available
        result: ContainerResult | None = None
        method = "docker"

        if docker_ok:
            spec = ContainerSpec(
                code=code,
                stdin=stdin,
                timeout=effective_timeout,
                memory_limit=f"{self._memory_limit_mb}m",
                memory_swap=f"{self._memory_limit_mb}m",
            )
            result = await self._docker.execute(spec)
            self._stats["docker_executions"] += 1

        # ── Layer 3: subprocess fallback ──────────────────────────
        if result is None or (not result.success and result.error and "Docker" in result.error):
            logger.info("Falling back to subprocess sandbox for %s", exec_id)
            result = await self._fallback.execute(code, stdin)
            method = "subprocess"
            self._stats["fallback_executions"] += 1

        self._stats["total_executions"] += 1
        elapsed = (time.monotonic() - start) * 1000
        self._stats["execution_times_ms"].append(elapsed)

        # ── Classify errors ───────────────────────────────────────
        error_type = ""
        if result.timeout:
            self._stats["timeouts"] += 1
            self._monitor.record_violation("timeout", f"Execution timed out after {effective_timeout}s")
            error_type = "timeout"
        elif result.oom_killed:
            self._stats["memory_exceeded"] += 1
            error_type = "memory_exceeded"
        elif result.error:
            self._stats["errors"] += 1
            error_type = "execution_error"

        return {
            "exec_id": exec_id,
            "success": result.success,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "exit_code": result.exit_code,
            "error": result.error or "",
            "violation": False,
            "violation_type": error_type,
            "duration_ms": round(elapsed, 2),
            "container_duration_ms": round(result.duration_ms, 2),
            "method": method,
            "exec_timeout_sec": effective_timeout,
            "memory_limit_mb": self._memory_limit_mb,
            "ast_nodes": validation.node_count,
        }

    @property
    def stats(self) -> dict[str, Any]:
        s = dict(self._stats)
        times = s.get("execution_times_ms", [])
        s["avg_execution_time_ms"] = round(sum(times) / len(times), 1) if times else 0.0
        s["max_execution_time_ms"] = round(max(times), 1) if times else 0.0
        s["p95_execution_time_ms"] = (
            sorted(times)[int(len(times) * 0.95)] if len(times) >= 20 else 0.0
        )
        return s

    async def shutdown(self) -> None:
        await self._docker.close()


def _find_python() -> str:
    """Find the Python interpreter path."""
    import sys
    return sys.executable


def _build_subprocess_wrapper(code: str, memory_limit_mb: int) -> str:
    """Wrap code in a subprocess sandbox with resource limits."""
    return (
        f"import resource, sys, os\n"
        f"os.nice(19)\n"
        f"resource.setrlimit(resource.RLIMIT_AS, "
        f"({memory_limit_mb * 1024 * 1024}, {memory_limit_mb * 1024 * 1024}))\n"
        f"resource.setrlimit(resource.RLIMIT_NPROC, (0, 0))\n"
        f"resource.setrlimit(resource.RLIMIT_NOFILE, (16, 16))\n"
        f"sys.setrecursionlimit(50)\n"
        f"del os, resource, sys\n"
        f"exec({code!r})\n"
    )


def _preexec_limits(memory_limit_mb: int):
    """preexec_fn for subprocess — set process group and limits."""
    def _set_limits():
        try:
            import resource
            os.setsid()
            resource.setrlimit(resource.RLIMIT_AS, (
                memory_limit_mb * 1024 * 1024,
                memory_limit_mb * 1024 * 1024,
            ))
            resource.setrlimit(resource.RLIMIT_NPROC, (0, 0))
            resource.setrlimit(resource.RLIMIT_NOFILE, (16, 16))
        except Exception:
            pass

    return _set_limits
