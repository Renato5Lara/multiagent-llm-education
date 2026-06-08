"""Docker container lifecycle manager for sandboxed code execution.

Manages a reusable pool of sandbox containers with:
- Read-only root filesystem
- No network (--network none)
- Memory/CPU/pids limits
- Deterministic cleanup with orphan prevention
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from app.sandbox.exceptions import SandboxDockerError, SandboxCleanupError, SandboxTimeout

logger = logging.getLogger(__name__)

SANDBOX_IMAGE = "upao-mas-edu-sandbox:latest"

CONTAINER_MOUNT_BASE = "/tmp/sandbox_mounts"

DEFAULT_MEMORY_LIMIT = "256m"
DEFAULT_MEMORY_SWAP = "256m"
DEFAULT_CPU_LIMIT = 1.0
DEFAULT_PIDS_LIMIT = 20
DEFAULT_TIMEOUT = 10.0


@dataclass
class ContainerSpec:
    code: str
    stdin: str = ""
    memory_limit: str = DEFAULT_MEMORY_LIMIT
    memory_swap: str = DEFAULT_MEMORY_SWAP
    cpu_limit: float = DEFAULT_CPU_LIMIT
    pids_limit: int = DEFAULT_PIDS_LIMIT
    timeout: float = DEFAULT_TIMEOUT
    network_disabled: bool = True
    read_only_root: bool = True
    container_id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    temp_dir: str = ""


@dataclass
class ContainerResult:
    container_id: str
    success: bool
    stdout: str
    stderr: str
    exit_code: int | None
    duration_ms: float
    error: str = ""
    oom_killed: bool = False
    timeout: bool = False


class DockerManager:
    """Manages Docker sandbox containers with pooling and cleanup."""

    def __init__(
        self,
        image: str = SANDBOX_IMAGE,
        max_containers: int = 10,
        pool_size: int = 3,
        pool_ttl_seconds: int = 300,
    ):
        self._image = image
        self._max_containers = max_containers
        self._pool_size = pool_size
        self._pool_ttl = pool_ttl_seconds
        self._active_containers: set[str] = set()
        self._warm_pool: asyncio.Queue[str] = asyncio.Queue()
        self._lock = asyncio.Lock()
        self._cleanup_task: asyncio.Task | None = None
        self._docker_available = False

    async def ensure_available(self) -> bool:
        """Check if Docker is available and the sandbox image exists."""
        try:
            proc = await asyncio.create_subprocess_exec(
                "docker", "info",
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await proc.wait()
            if proc.returncode != 0:
                logger.warning("Docker is not available — sandbox cannot run")
                self._docker_available = False
                return False

            proc2 = await asyncio.create_subprocess_exec(
                "docker", "image", "inspect", self._image,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await proc2.wait()
            if proc2.returncode != 0:
                logger.warning("Sandbox image '%s' not found — build with: "
                               "docker build -f Dockerfile.sandbox -t %s .",
                               self._image, self._image)
                self._docker_available = False
                return False

            self._docker_available = True
            return True

        except FileNotFoundError:
            logger.warning("Docker CLI not found — sandbox cannot run")
            self._docker_available = False
            return False

    @property
    def available(self) -> bool:
        return self._docker_available

    async def start_pool_warmup(self) -> None:
        """Pre-warm containers in background."""
        if not self._docker_available:
            return
        for _ in range(min(self._pool_size, self._max_containers)):
            try:
                cid = await self._create_container()
                await self._warm_pool.put(cid)
            except Exception as e:
                logger.warning("Pool warmup failed: %s", e)

    async def execute(self, spec: ContainerSpec) -> ContainerResult:
        """Execute code in a sandbox container."""
        start = time.monotonic()
        container_id = spec.container_id

        if not self._docker_available:
            return ContainerResult(
                container_id=container_id,
                success=False,
                stdout="",
                stderr="",
                exit_code=None,
                duration_ms=0.0,
                error="Docker not available",
            )

        # Try to get a warm container, or create one
        try:
            if not self._warm_pool.empty():
                cid = self._warm_pool.get_nowait()
            else:
                cid = await self._create_container(spec)
        except Exception as e:
            return ContainerResult(
                container_id=container_id,
                success=False,
                stdout="", stderr="",
                exit_code=None,
                duration_ms=0.0,
                error=f"Container creation failed: {e}",
            )

        async with self._lock:
            self._active_containers.add(cid)

        try:
            # Write code to a temp file and copy it in
            code_hash = hashlib.sha256(spec.code.encode()).hexdigest()[:16]
            host_path = f"/tmp/sandbox_{code_hash}_{container_id}.py"
            with open(host_path, "w") as f:
                f.write(spec.code)
            os.chmod(host_path, 0o444)

            copy_proc = await asyncio.create_subprocess_exec(
                "docker", "cp", host_path, f"{cid}:/tmp/script.py",
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.PIPE,
            )
            _, copy_err = await copy_proc.communicate()

            if copy_proc.returncode != 0:
                raise SandboxDockerError(f"Copy failed: {copy_err.decode()[:200]}")

            # Execute in container with timeout
            exec_proc = await asyncio.create_subprocess_exec(
                "docker", "exec",
                "--env", "PYTHONUNBUFFERED=1",
                "--env", f"TIMEOUT={spec.timeout}",
                cid, "python3", "-u", "/tmp/script.py",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            try:
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    exec_proc.communicate(),
                    timeout=spec.timeout + 2.0,
                )
                stdout = stdout_bytes.decode("utf-8", errors="replace")
                stderr = stderr_bytes.decode("utf-8", errors="replace")

            except asyncio.TimeoutError:
                try:
                    exec_proc.kill()
                except ProcessLookupError:
                    pass
                elapsed = (time.monotonic() - start) * 1000
                return ContainerResult(
                    container_id=cid, success=False,
                    stdout="", stderr="",
                    exit_code=None,
                    duration_ms=elapsed,
                    error="Execution timed out",
                    timeout=True,
                )

            elapsed = (time.monotonic() - start) * 1000
            exit_code = exec_proc.returncode

            # Check for OOM
            oom = False
            if exit_code == 137:
                oom = True

            return ContainerResult(
                container_id=cid,
                success=exit_code == 0,
                stdout=stdout,
                stderr=stderr,
                exit_code=exit_code,
                duration_ms=elapsed,
                oom_killed=oom,
            )

        finally:
            try:
                os.unlink(host_path)
            except OSError:
                pass

            # Async cleanup (don't block)
            asyncio.create_task(self._destroy_container(cid))

    async def _create_container(self, spec: ContainerSpec | None = None) -> str:
        """Create a new sandbox container."""
        mem = spec.memory_limit if spec else DEFAULT_MEMORY_LIMIT
        mem_swap = spec.memory_swap if spec else DEFAULT_MEMORY_SWAP
        cpu = spec.cpu_limit if spec else DEFAULT_CPU_LIMIT
        pids = spec.pids_limit if spec else DEFAULT_PIDS_LIMIT

        name = f"sandbox-{uuid.uuid4()[:8]}"

        cmd = [
            "docker", "create",
            "--name", name,
            "--network", "none",
            "--read-only",
            "--tmpfs", "/tmp:size=64m,noexec,nosuid,nodev",
            "--tmpfs", "/run:size=32m,noexec,nosuid,nodev",
            "--memory", mem,
            "--memory-swap", mem_swap,
            "--cpus", str(cpu),
            "--pids-limit", str(pids),
            "--cap-drop", "ALL",
            "--security-opt", "no-new-privileges:true",
            "--security-opt", "seccomp=unconfined",
            "--stop-signal", "SIGKILL",
            "--stop-timeout", "5",
            self._image,
            "sleep", "3600",
        ]

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()

        if proc.returncode != 0:
            raise SandboxDockerError(
                f"docker create failed: {stderr.decode()[:200]}"
            )

        cid = stdout.decode().strip()

        # Start the container
        start_proc = await asyncio.create_subprocess_exec(
            "docker", "start", cid,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE,
        )
        _, start_err = await start_proc.communicate()

        if start_proc.returncode != 0:
            raise SandboxDockerError(
                f"docker start failed: {start_err.decode()[:200]}"
            )

        return cid

    async def _destroy_container(self, container_id: str) -> None:
        """Destroy a container and track cleanup."""
        try:
            kill_proc = await asyncio.create_subprocess_exec(
                "docker", "kill", container_id,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await kill_proc.wait()

            rm_proc = await asyncio.create_subprocess_exec(
                "docker", "rm", "--force", "--volumes", container_id,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await rm_proc.wait()
        except Exception as e:
            logger.warning("Container cleanup[%s] failed: %s", container_id, e)

        async with self._lock:
            self._active_containers.discard(container_id)

    async def destroy_all(self) -> int:
        """Destroy all active containers. Returns count destroyed."""
        async with self._lock:
            targets = list(self._active_containers)
            self._active_containers.clear()

        # Drain warm pool
        while not self._warm_pool.empty():
            try:
                cid = self._warm_pool.get_nowait()
                targets.append(cid)
            except asyncio.QueueEmpty:
                break

        count = 0
        for cid in set(targets):
            try:
                await self._destroy_container(cid)
                count += 1
            except Exception as e:
                logger.error("Failed to destroy container %s: %s", cid, e)
        return count

    async def orphan_cleanup(self) -> int:
        """Find and destroy orphan sandbox containers."""
        try:
            proc = await asyncio.create_subprocess_exec(
                "docker", "ps", "-a", "--filter", "name=sandbox-",
                "--format", "{{.ID}}",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL,
            )
            stdout, _ = await proc.communicate()
            orphans = stdout.decode().strip().split()

            count = 0
            for oid in orphans:
                if not oid:
                    continue
                try:
                    await self._destroy_container(oid)
                    count += 1
                except Exception:
                    pass
            return count

        except Exception as e:
            logger.warning("Orphan cleanup failed: %s", e)
            return 0

    async def close(self) -> None:
        """Clean shutdown — destroy all containers."""
        await self.destroy_all()

    @property
    def active_count(self) -> int:
        return len(self._active_containers)
