from __future__ import annotations

import asyncio
import json
import logging
import shutil
import tempfile
import time
import uuid
from pathlib import Path
from typing import Any

from app.sandbox.policy import SandboxPolicy
from app.sandbox.schemas import SandboxRequest, SandboxResult, SandboxStatus

logger = logging.getLogger(__name__)


class SandboxRunner:
    """Async Docker-backed runner for untrusted educational Python snippets."""

    IMAGE = "upao-python-repl-sandbox:latest"

    def __init__(
        self,
        *,
        image: str | None = None,
        docker_bin: str = "docker",
        policy: SandboxPolicy | None = None,
        auto_build: bool = False,
    ):
        self.image = image or self.IMAGE
        self.docker_bin = docker_bin
        self.policy = policy or SandboxPolicy()
        self.auto_build = auto_build

    async def run(self, request: SandboxRequest) -> SandboxResult:
        start = time.perf_counter()
        combined_code = request.code if not request.test_code else f"{request.code}\n\n{request.test_code}"
        violations = self.policy.validate(combined_code)
        if violations:
            return SandboxResult(
                status=SandboxStatus.SECURITY_VIOLATION,
                success=False,
                violations=violations,
                execution_time_ms=self._elapsed_ms(start),
                metadata={**request.metadata, "sandbox": "static_policy"},
            )

        if shutil.which(self.docker_bin) is None:
            return SandboxResult(
                status=SandboxStatus.INFRASTRUCTURE_ERROR,
                success=False,
                stderr="Docker CLI is not available. Install Docker or run this service on a Docker-enabled host.",
                execution_time_ms=self._elapsed_ms(start),
                metadata={**request.metadata, "sandbox": "docker_unavailable"},
            )

        if self.auto_build:
            try:
                await self.build_image()
            except RuntimeError as exc:
                return SandboxResult(
                    status=SandboxStatus.INFRASTRUCTURE_ERROR,
                    success=False,
                    stderr=str(exc),
                    execution_time_ms=self._elapsed_ms(start),
                    metadata={**request.metadata, "sandbox": "docker_build_failed"},
                )

        with tempfile.TemporaryDirectory(prefix="edu-sandbox-") as temp_dir:
            temp_path = Path(temp_dir)
            (temp_path / "code.py").write_text(request.code, encoding="utf-8")
            (temp_path / "tests.py").write_text(request.test_code or "", encoding="utf-8")
            (temp_path / "stdin.txt").write_text(request.stdin or "", encoding="utf-8")

            container_name = f"edu-sandbox-{uuid.uuid4().hex[:12]}"
            cmd = self._docker_command(temp_path, container_name, request)
            logger.info(
                "sandbox.execution.start container=%s timeout=%ss memory=%smb metadata=%s",
                container_name,
                request.limits.timeout_seconds,
                request.limits.memory_mb,
                request.metadata,
            )
            try:
                proc = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    proc.communicate(),
                    timeout=request.limits.timeout_seconds + 2,
                )
            except asyncio.TimeoutError:
                await self._cleanup_container(container_name)
                return SandboxResult(
                    status=SandboxStatus.TIMEOUT,
                    success=False,
                    stderr=f"Execution exceeded {request.limits.timeout_seconds}s timeout.",
                    execution_time_ms=self._elapsed_ms(start),
                    timed_out=True,
                    metadata={**request.metadata, "sandbox": "host_timeout"},
                )

        stdout = stdout_bytes.decode("utf-8", errors="replace")
        stderr = stderr_bytes.decode("utf-8", errors="replace")
        result = self._parse_result(stdout, stderr, proc.returncode, request, start)
        logger.info(
            "sandbox.execution.complete status=%s success=%s exit_code=%s duration_ms=%.2f memory_mb=%.2f",
            result.status.value,
            result.success,
            result.exit_code,
            result.execution_time_ms,
            result.memory_usage_mb,
        )
        return result

    async def build_image(self) -> None:
        dockerfile_dir = Path(__file__).resolve().parent / "docker"
        proc = await asyncio.create_subprocess_exec(
            self.docker_bin,
            "build",
            "-t",
            self.image,
            str(dockerfile_dir),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            raise RuntimeError(
                "Could not build sandbox image: "
                + stderr.decode("utf-8", errors="replace")
                + stdout.decode("utf-8", errors="replace")
            )

    def _docker_command(self, temp_path: Path, container_name: str, request: SandboxRequest) -> list[str]:
        return [
            self.docker_bin,
            "run",
            "--rm",
            "--name",
            container_name,
            "--network",
            "none",
            "--memory",
            f"{request.limits.memory_mb}m",
            "--memory-swap",
            f"{request.limits.memory_mb}m",
            "--pids-limit",
            str(request.limits.pids_limit),
            "--cpus",
            "1",
            "--read-only",
            "--tmpfs",
            "/tmp:rw,noexec,nosuid,nodev,size=64m",
            "--cap-drop",
            "ALL",
            "--security-opt",
            "no-new-privileges",
            "--user",
            "65534:65534",
            "-e",
            f"SANDBOX_TIMEOUT={request.limits.timeout_seconds}",
            "-e",
            f"SANDBOX_MEMORY_MB={request.limits.memory_mb}",
            "-e",
            f"SANDBOX_STDOUT_LIMIT={request.limits.stdout_limit_chars}",
            "-e",
            f"SANDBOX_STDERR_LIMIT={request.limits.stderr_limit_chars}",
            "-v",
            f"{temp_path.as_posix()}:/sandbox/input:ro",
            self.image,
        ]

    async def _cleanup_container(self, container_name: str) -> None:
        try:
            proc = await asyncio.create_subprocess_exec(
                self.docker_bin,
                "rm",
                "-f",
                container_name,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await proc.communicate()
        except Exception:
            logger.exception("sandbox.cleanup.failed container=%s", container_name)

    def _parse_result(
        self,
        stdout: str,
        stderr: str,
        exit_code: int | None,
        request: SandboxRequest,
        start: float,
    ) -> SandboxResult:
        marker = "===SANDBOX_RESULT==="
        payload: dict[str, Any] | None = None
        visible_stdout = stdout
        if marker in stdout:
            visible_stdout, raw = stdout.rsplit(marker, 1)
            try:
                payload = json.loads(raw.strip())
            except json.JSONDecodeError:
                payload = None

        if payload:
            status = SandboxStatus(payload.get("status") or SandboxStatus.RUNTIME_ERROR.value)
            if status == SandboxStatus.RUNTIME_ERROR and "MemoryError" in str(payload.get("traceback", "")):
                status = SandboxStatus.MEMORY_LIMIT
            return SandboxResult(
                status=status,
                success=bool(payload.get("success")),
                stdout=str(payload.get("stdout", visible_stdout))[: request.limits.stdout_limit_chars],
                stderr=(str(payload.get("stderr", "")) + stderr)[: request.limits.stderr_limit_chars],
                traceback=str(payload.get("traceback", "")),
                execution_time_ms=float(payload.get("execution_time_ms") or self._elapsed_ms(start)),
                memory_usage_mb=float(payload.get("memory_usage_mb") or 0.0),
                exit_code=exit_code,
                timed_out=status == SandboxStatus.TIMEOUT,
                metrics=dict(payload.get("metrics") or {}),
                metadata={**request.metadata, "sandbox": "docker"},
            )

        infrastructure_markers = (
            "failed to connect to the docker api",
            "cannot connect to the docker daemon",
            "is the docker daemon running",
            "pull access denied",
            "unable to find image",
            "no such image",
        )
        if exit_code and any(marker in stderr.lower() for marker in infrastructure_markers):
            return SandboxResult(
                status=SandboxStatus.INFRASTRUCTURE_ERROR,
                success=False,
                stderr=stderr[: request.limits.stderr_limit_chars],
                execution_time_ms=self._elapsed_ms(start),
                exit_code=exit_code,
                metadata={**request.metadata, "sandbox": "docker_infrastructure"},
            )

        status = SandboxStatus.RUNTIME_ERROR if exit_code else SandboxStatus.SUCCESS
        if exit_code == 137:
            status = SandboxStatus.MEMORY_LIMIT
        return SandboxResult(
            status=status,
            success=exit_code == 0,
            stdout=visible_stdout[: request.limits.stdout_limit_chars],
            stderr=stderr[: request.limits.stderr_limit_chars],
            execution_time_ms=self._elapsed_ms(start),
            exit_code=exit_code,
            metadata={**request.metadata, "sandbox": "docker_unstructured"},
        )

    def _elapsed_ms(self, start: float) -> float:
        return round((time.perf_counter() - start) * 1000, 2)
