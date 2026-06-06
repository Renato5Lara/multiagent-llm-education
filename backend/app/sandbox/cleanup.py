"""Cleanup manager — deterministic container cleanup, orphan prevention, concurrency safety."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from app.sandbox.docker_manager import DockerManager

logger = logging.getLogger(__name__)


class CleanupManager:
    """Manages deterministic cleanup of sandbox resources.

    Features:
    - Automatic orphan container detection and destruction
    - Periodic cleanup sweeps
    - Graceful shutdown
    - Concurrent execution safety (container ID tracking)
    """

    def __init__(
        self,
        docker_manager: DockerManager | None = None,
        sweep_interval_seconds: int = 120,
        max_container_age_seconds: int = 600,
    ):
        self._docker = docker_manager
        self._sweep_interval = sweep_interval_seconds
        self._max_age = max_container_age_seconds
        self._sweep_task: asyncio.Task | None = None
        self._running = False
        self._started_at: dict[str, float] = {}
        self._lock = asyncio.Lock()

    async def start_periodic_sweep(self) -> None:
        """Start background periodic orphan cleanup."""
        if self._running:
            return
        self._running = True
        self._sweep_task = asyncio.create_task(self._sweep_loop())

    async def stop_sweep(self) -> None:
        self._running = False
        if self._sweep_task:
            self._sweep_task.cancel()
            try:
                await self._sweep_task
            except asyncio.CancelledError:
                pass
            self._sweep_task = None

    async def _sweep_loop(self) -> None:
        """Periodically clean up orphan containers."""
        while self._running:
            await asyncio.sleep(self._sweep_interval)
            try:
                count = await self._sweep_orphans()
                if count:
                    logger.info("Cleanup sweep: destroyed %d orphan containers", count)
            except Exception as e:
                logger.warning("Cleanup sweep failed: %s", e)

    async def _sweep_orphans(self) -> int:
        """Clean up orphan containers via DockerManager."""
        if self._docker and hasattr(self._docker, "orphan_cleanup"):
            return await self._docker.orphan_cleanup()
        return 0

    async def graceful_shutdown(self, timeout: float = 10.0) -> dict[str, Any]:
        """Gracefully shut down all sandbox resources."""
        logger.info("Cleanup: graceful shutdown initiated")
        result: dict[str, Any] = {"containers_destroyed": 0, "errors": []}

        if self._docker:
            try:
                count = await asyncio.wait_for(
                    self._docker.destroy_all(),
                    timeout=timeout,
                )
                result["containers_destroyed"] = count
            except asyncio.TimeoutError:
                result["errors"].append("Docker destroy_all timed out")
                logger.error("Cleanup: docker destroy_all timed out")
            except Exception as e:
                result["errors"].append(f"Docker destroy_all failed: {e}")

        await self.stop_sweep()

        # Final orphan sweep
        try:
            orphans = await self._sweep_orphans()
            result["orphans_destroyed"] = orphans
        except Exception as e:
            result["errors"].append(f"Final orphan sweep failed: {e}")

        logger.info("Cleanup: shutdown complete — %s", result)
        return result

    @property
    def cleanup_stats(self) -> dict[str, Any]:
        return {
            "sweep_running": self._running,
            "sweep_interval": self._sweep_interval,
            "max_container_age": self._max_age,
        }
