"""
SharedMemoryStore — Deterministic collective memory for the consensus swarm.

Provides publish, query, lineage, and conflict-resolution operations
on SharedMemoryRecord, all scoped to UoW transactions.

Every operation is:
    - deterministic (same inputs → same results)
    - auditable (trace IDs, parent links, versioning)
    - thread-safe (via UoW / advisory locks)
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.db.uow import UnitOfWork
from app.memory.memory_rules import (
    compute_memory_confidence,
    compute_ttl,
    is_stale,
    merge_observations,
    resolve_conflict,
)
from app.models.shared_memory_record import SharedMemoryRecord
from app.observability.tracing import TraceContext, TracingSpan

logger = logging.getLogger(__name__)


def memory_store_from_session(session: Session, dedup_engine: Any | None = None) -> SharedMemoryStore:
    """Create a SharedMemoryStore scoped to an existing SQLAlchemy Session.

    The returned store shares the caller's transactional context — flush
    commits go to the same session, and the session lifecycle (commit /
    rollback / close) remains the caller's responsibility.

    Usage in route handlers::

        store = memory_store_from_session(db)
        await week_orchestrator.orchestrate_week(db, course, week, memory_store=store)
    """
    uow = UnitOfWork(lambda: session)
    return SharedMemoryStore(uow, dedup_engine=dedup_engine)


class SharedMemoryStore:
    """Deterministic shared memory store backed by SQLAlchemy + UoW.

    All operations run inside the caller's UnitOfWork, sharing the
    same transaction as the consensus run.

    Usage:
        store = SharedMemoryStore(uow)
        record_id = store.publish_observation(
            voter_name="mastery",
            student_id="stu-1",
            module_id="mod-1",
            key="performance:trend",
            value={"trend": "improving", "slope": 0.05},
            confidence=0.85,
            trace_ctx=trace_ctx,
        )
        records = store.query(student_id="stu-1", memory_type="observation")
    """

    def __init__(self, uow: UnitOfWork, dedup_engine: Any | None = None):
        self._uow = uow
        self._dedup_engine = dedup_engine

    @property
    def _db(self) -> Session:
        return self._uow.db

    # ── Publish ──────────────────────────────────────────────────

    def publish_observation(
        self,
        voter_name: str,
        key: str,
        value: dict[str, Any],
        *,
        confidence: float = 1.0,
        student_id: str | None = None,
        module_id: str | None = None,
        memory_type: str = "observation",
        trace_ctx: TraceContext | None = None,
        propagation_ctx: Any | None = None,
        parent_id: str | None = None,
        ttl_seconds: int | None = None,
        metadata_json: dict[str, Any] | None = None,
    ) -> str:
        """Publish an observation to shared memory.

        If ttl_seconds is None, computes a default from memory_type
        and confidence.

        When a DistributedDedupEngine is configured via the constructor,
        the publish is protected by content-hash dedup: duplicate
        observations return the existing record ID instead of creating
        a new record.

        Args:
            propagation_ctx: Optional PropagationContext for distributed
                             tracing. If provided, creates a child span
                             and derives trace_ctx from it.
        Returns:
            str: The record ID.
        """
        _dedup_content_key: str | None = None
        _dedup_acquired = False

        if self._dedup_engine is not None:
            from app.events.integration import _memory_key
            _db = self._uow.db
            _dedup_content_key = _memory_key(
                voter_name, key, value, confidence,
                student_id, module_id, memory_type,
            )

            existing_id = self._dedup_engine.check_memory_duplicate(
                _db, voter_name, key, value,
                confidence=confidence,
                student_id=student_id,
                module_id=module_id,
                memory_type=memory_type,
            )
            if existing_id is not None:
                logger.info(
                    "Dedup memory: %s/%s → existing record %s",
                    voter_name, key, existing_id,
                )
                return existing_id

            from app.db.locks import advisory_lock
            with advisory_lock(_db, f"idempotency:memory:{_dedup_content_key}"):
                existing_under_lock = self._dedup_engine._idem.check(
                    _db, _dedup_content_key,
                )
                if existing_under_lock and existing_under_lock.status == "completed":
                    cached = (
                        json.loads(existing_under_lock.response_body)
                        if existing_under_lock.response_body else None
                    )
                    if cached and "record_id" in cached:
                        return cached["record_id"]
                try:
                    self._dedup_engine._idem.acquire(
                        _db, _dedup_content_key,
                        event_type=f"memory:{memory_type}",
                        aggregate_id=f"{voter_name}:{key}",
                    )
                    _dedup_acquired = True
                except Exception:
                    pass

        if propagation_ctx is not None and trace_ctx is None:
            try:
                from app.tracing import correlation_engine as _ce
                _child = _ce.child(
                    operation_name=f"memory:{memory_type}",
                    tags={"voter": voter_name, "key": key[:40]},
                )
                if _child is not None:
                    trace_ctx = _child.to_legacy_trace_context()
            except Exception:
                pass

        if propagation_ctx is None and trace_ctx is None:
            try:
                from app.tracing import correlation_engine as _ce
                current = _ce.get_current()
                if current is not None:
                    _child = _ce.child(
                        operation_name=f"memory:{memory_type}",
                        tags={"voter": voter_name, "key": key[:40]},
                    )
                    if _child is not None:
                        trace_ctx = _child.to_legacy_trace_context()
                        propagation_ctx = True
            except Exception:
                pass

        with TracingSpan(trace_ctx, "memory.publish") if trace_ctx else _nullspan():
            actual_ttl = ttl_seconds
            if actual_ttl is None:
                actual_ttl = compute_ttl(memory_type, confidence)

            source_trace_id = trace_ctx.trace_id if trace_ctx else None
            source_event_id = None  # Set externally if needed

            record = SharedMemoryRecord(
                voter_name=voter_name,
                student_id=student_id,
                module_id=module_id,
                memory_type=memory_type,
                key=key,
                value=value or {},
                confidence=max(0.0, min(1.0, confidence)),
                source_trace_id=source_trace_id,
                source_event_id=source_event_id,
                parent_id=parent_id,
                ttl_seconds=actual_ttl,
                metadata_json=metadata_json or {},
            )
            self._db.add(record)
            self._uow.flush()

            if _dedup_acquired and _dedup_content_key is not None:
                try:
                    self._dedup_engine._idem.complete(
                        self._uow.db, _dedup_content_key,
                        response_body={"record_id": record.id},
                    )
                except Exception:
                    pass

            try:
                from app.swarm_diagnostics import diagnostics_engine as _diag
                _diag.record_memory_op(
                    op=f"publish:{memory_type}",
                    voter_name=voter_name,
                    student_id=student_id,
                    module_id=module_id,
                    key=key,
                    trace_id=source_trace_id,
                )
            except Exception:
                pass

            logger.debug(
                "Memory published: voter=%s type=%s key=%s "
                "confidence=%.2f student=%s",
                voter_name, memory_type, key, confidence, student_id,
            )

            if propagation_ctx is not None:
                try:
                    from app.tracing import correlation_engine as _ce
                    _ce.end()
                except Exception:
                    pass

            return record.id

    # ── Query ────────────────────────────────────────────────────

    def query(
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
        propagation_ctx: Any | None = None,
    ) -> list[SharedMemoryRecord]:
        """Query shared memory by scope and type.

        Args:
            student_id: Filter by student (None = any).
            module_id: Filter by module (None = any).
            memory_type: Filter by type (None = all).
            key: Filter by exact key (None = all).
            voter_name: Filter by publisher (None = all).
            limit: Max records to return.
            include_stale: If True, include expired records.
            order_desc: If True, newest first.
            propagation_ctx: Optional PropagationContext for distributed
                             tracing. Creates a child span if provided.

        Returns:
            List of SharedMemoryRecord matching the criteria.
        """
        _prop_ended = False
        if propagation_ctx is not None:
            try:
                from app.tracing import correlation_engine as _ce
                _ce.child(
                    operation_name="memory:query",
                    tags={
                        "student_id": str(student_id or ""),
                        "module_id": str(module_id or ""),
                        "memory_type": memory_type or "",
                    },
                )
                _prop_ended = True
            except Exception:
                pass

        if propagation_ctx is None:
            try:
                from app.tracing import correlation_engine as _ce
                current = _ce.get_current()
                if current is not None:
                    _ce.child(
                        operation_name="memory:query",
                        tags={
                            "student_id": str(student_id or ""),
                            "module_id": str(module_id or ""),
                            "memory_type": memory_type or "",
                        },
                    )
                    _prop_ended = True
            except Exception:
                pass

        filters = []
        if student_id is not None:
            filters.append(SharedMemoryRecord.student_id == student_id)
        if module_id is not None:
            filters.append(SharedMemoryRecord.module_id == module_id)
        if memory_type is not None:
            filters.append(SharedMemoryRecord.memory_type == memory_type)
        if key is not None:
            filters.append(SharedMemoryRecord.key == key)
        if voter_name is not None:
            filters.append(SharedMemoryRecord.voter_name == voter_name)

        q = self._db.query(SharedMemoryRecord).filter(
            and_(True, *filters) if not filters else and_(*filters)
        )

        order = SharedMemoryRecord.created_at.desc() if order_desc else SharedMemoryRecord.created_at.asc()
        q = q.order_by(order).limit(limit)

        records = q.all()

        if not include_stale:
            records = [r for r in records if not is_stale(r)]

        if _prop_ended:
            try:
                from app.tracing import correlation_engine as _ce
                _ce.end()
            except Exception:
                pass

        return records

    def query_by_key_pattern(
        self,
        key_prefix: str,
        *,
        student_id: str | None = None,
        module_id: str | None = None,
        memory_type: str | None = None,
        limit: int = 50,
        propagation_ctx: Any | None = None,
    ) -> list[SharedMemoryRecord]:
        """Query memory by key prefix (e.g., 'performance:').

        Uses SQL LIKE.

        Args:
            key_prefix: Prefix to match (appended with '%').
            student_id: Optional student scope.
            module_id: Optional module scope.
            memory_type: Optional type filter.
            limit: Max records.
            propagation_ctx: Optional PropagationContext for distributed tracing.

        Returns:
            List of matching records.
        """
        _prop_ended = False
        if propagation_ctx is not None:
            try:
                from app.tracing import correlation_engine as _ce
                _ce.child(
                    operation_name="memory:query_pattern",
                    tags={"key_prefix": key_prefix[:30], "student_id": str(student_id or "")},
                )
                _prop_ended = True
            except Exception:
                pass

        if propagation_ctx is None:
            try:
                from app.tracing import correlation_engine as _ce
                current = _ce.get_current()
                if current is not None:
                    _ce.child(
                        operation_name="memory:query_pattern",
                        tags={"key_prefix": key_prefix[:30], "student_id": str(student_id or "")},
                    )
                    _prop_ended = True
            except Exception:
                pass

        filters = [
            SharedMemoryRecord.key.like(f"{key_prefix}%"),
        ]
        if student_id is not None:
            filters.append(SharedMemoryRecord.student_id == student_id)
        if module_id is not None:
            filters.append(SharedMemoryRecord.module_id == module_id)
        if memory_type is not None:
            filters.append(SharedMemoryRecord.memory_type == memory_type)

        q = (
            self._db.query(SharedMemoryRecord)
            .filter(and_(*filters))
            .order_by(SharedMemoryRecord.created_at.desc())
            .limit(limit)
        )
        result = [r for r in q.all() if not is_stale(r)]

        if _prop_ended:
            try:
                from app.tracing import correlation_engine as _ce
                _ce.end()
            except Exception:
                pass

        return result

    # ── Single Record Access ─────────────────────────────────────

    def get_by_id(self, record_id: str, propagation_ctx: Any | None = None) -> SharedMemoryRecord | None:
        """Fetch a single record by ID.

        Args:
            propagation_ctx: Optional PropagationContext for distributed tracing.
        """
        _prop_ended = False
        if propagation_ctx is not None:
            try:
                from app.tracing import correlation_engine as _ce
                _ce.child(operation_name="memory:get_by_id", tags={"record_id": record_id[:20]})
                _prop_ended = True
            except Exception:
                pass

        if propagation_ctx is None:
            try:
                from app.tracing import correlation_engine as _ce
                current = _ce.get_current()
                if current is not None:
                    _ce.child(operation_name="memory:get_by_id", tags={"record_id": record_id[:20]})
                    _prop_ended = True
            except Exception:
                pass

        result = (
            self._db.query(SharedMemoryRecord)
            .filter(SharedMemoryRecord.id == record_id)
            .first()
        )

        if _prop_ended:
            try:
                from app.tracing import correlation_engine as _ce
                _ce.end()
            except Exception:
                pass

        return result

    # ── Lineage ──────────────────────────────────────────────────

    def get_lineage(
        self,
        record_id: str,
        max_depth: int = 100,
    ) -> list[SharedMemoryRecord]:
        """Walk the parent_id chain to build the full lineage.

        Args:
            record_id: Starting record ID.
            max_depth: Safety limit.

        Returns:
            List from oldest ancestor to the given record.
        """
        chain: list[SharedMemoryRecord] = []
        current_id: str | None = record_id
        depth = 0
        while current_id is not None and depth < max_depth:
            record = self.get_by_id(current_id)
            if record is None:
                break
            chain.append(record)
            current_id = record.parent_id
            depth += 1
        chain.reverse()
        return chain

    # ── Conflict Resolution ──────────────────────────────────────

    def resolve_conflicts(
        self,
        key: str,
        *,
        student_id: str | None = None,
        module_id: str | None = None,
        propagation_ctx: Any | None = None,
    ) -> dict[str, Any]:
        """Find all records with the same key and resolve conflicts.

        Args:
            key: The key to resolve.
            student_id: Scope filter.
            module_id: Scope filter.
            propagation_ctx: Optional PropagationContext for distributed tracing.

        Returns:
            The resolved value dict.
        """
        records = self.query(
            student_id=student_id,
            module_id=module_id,
            key=key,
            include_stale=False,
            limit=100,
            propagation_ctx=propagation_ctx,
        )
        return resolve_conflict(records)

    # ── Staleness Management ─────────────────────────────────────

    def remove_stale(self, batch_size: int = 100) -> int:
        """Delete all stale records from the database.

        Should be called periodically (e.g., via a scheduled job).

        Args:
            batch_size: Max records to delete in one call.

        Returns:
            int: Number of deleted records.
        """
        now = datetime.now(timezone.utc)
        records = (
            self._db.query(SharedMemoryRecord)
            .filter(SharedMemoryRecord.ttl_seconds.isnot(None))
            .limit(batch_size)
            .all()
        )
        stale = [r for r in records if is_stale(r, now=now)]
        for r in stale:
            self._db.delete(r)
        self._uow.flush()

        count = len(stale)
        if count > 0:
            logger.info("Memory cleanup: removed %d stale records", count)
        return count

    # ── Aggregation ──────────────────────────────────────────────

    def aggregate_confidence(
        self,
        key: str,
        *,
        student_id: str | None = None,
        module_id: str | None = None,
        propagation_ctx: Any | None = None,
    ) -> float:
        """Compute aggregated confidence for all records with a key.

        Args:
            propagation_ctx: Optional PropagationContext for distributed tracing.
        """
        records = self.query(
            student_id=student_id,
            module_id=module_id,
            key=key,
            include_stale=False,
            limit=100,
            propagation_ctx=propagation_ctx,
        )
        return compute_memory_confidence(records)

    # ── Count ────────────────────────────────────────────────────

    def count(
        self,
        *,
        student_id: str | None = None,
        module_id: str | None = None,
        memory_type: str | None = None,
    ) -> int:
        """Count records matching scope.

        Does NOT filter stale records for performance.
        """
        filters = []
        if student_id is not None:
            filters.append(SharedMemoryRecord.student_id == student_id)
        if module_id is not None:
            filters.append(SharedMemoryRecord.module_id == module_id)
        if memory_type is not None:
            filters.append(SharedMemoryRecord.memory_type == memory_type)

        return (
            self._db.query(SharedMemoryRecord)
            .filter(and_(True, *filters) if not filters else and_(*filters))
            .count()
        )


def _nullspan():
    """No-op context manager for when trace_ctx is None."""

    class _NullSpan:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

    return _NullSpan()
