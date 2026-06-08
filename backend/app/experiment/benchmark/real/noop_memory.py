"""NoopMemoryStore — a SharedMemoryStore-compatible no-op for ablation experiments."""

from __future__ import annotations

from typing import Any


class NoopMemoryStore:
    """Drop-in replacement for SharedMemoryStore that performs no operations.

    Used by ablation conditions where memory is disabled (swarm_no_memory).
    Implements the same async interface as SharedMemoryStore so agents
    can use it transparently.
    """

    async def publish_observation(
        self,
        voter_name: str = "",
        key: str = "",
        value: dict[str, Any] | None = None,
        *,
        confidence: float = 1.0,
        student_id: str | None = None,
        module_id: str | None = None,
        memory_type: str = "observation",
        trace_ctx: Any = None,
        propagation_ctx: Any = None,
        parent_id: str | None = None,
        ttl_seconds: int | None = None,
        metadata_json: dict[str, Any] | None = None,
    ) -> str:
        return "noop"

    async def query(
        self,
        *,
        student_id: str | None = None,
        module_id: str | None = None,
        memory_type: str | None = None,
        key: str | None = None,
        voter_name: str | None = None,
        limit: int = 50,
        include_stale: bool = False,
        order_desc: bool = True,
        propagation_ctx: Any = None,
    ) -> list[Any]:
        return []

    async def query_by_key_pattern(
        self,
        key_prefix: str,
        *,
        student_id: str | None = None,
        module_id: str | None = None,
        memory_type: str | None = None,
        limit: int = 50,
        propagation_ctx: Any = None,
    ) -> list[Any]:
        return []

    async def get_by_id(
        self,
        record_id: str,
        propagation_ctx: Any = None,
    ) -> Any | None:
        return None

    async def get_lineage(
        self,
        record_id: str,
        max_depth: int = 100,
    ) -> list[Any]:
        return []

    async def resolve_conflicts(
        self,
        key: str,
        *,
        student_id: str | None = None,
        module_id: str | None = None,
        propagation_ctx: Any = None,
    ) -> dict[str, Any]:
        return {}

    async def remove_stale(self, batch_size: int = 100) -> int:
        return 0

    async def aggregate_confidence(
        self,
        key: str,
        *,
        student_id: str | None = None,
        module_id: str | None = None,
        propagation_ctx: Any = None,
    ) -> float:
        return 0.5

    async def count(
        self,
        *,
        student_id: str | None = None,
        module_id: str | None = None,
        memory_type: str | None = None,
    ) -> int:
        return 0
