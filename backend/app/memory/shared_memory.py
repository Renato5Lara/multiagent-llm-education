"""
SharedMemoryStore — Deterministic collective memory for the consensus swarm.

Provides publish, query, lineage, and conflict-resolution operations
on SharedMemoryRecord, all scoped to UoW transactions.

Every operation is:
    - deterministic (same inputs → same results)
    - auditable (trace IDs, parent links, versioning)
    - thread-safe (via UoW / advisory locks)

All DB methods are async (AsyncSession-compatible).
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import and_, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.uow import AsyncUnitOfWork, UnitOfWork
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
    def __init__(self, uow: UnitOfWork | AsyncUnitOfWork, dedup_engine: Any | None = None):
        self._uow = uow
        self._dedup_engine = dedup_engine

    @property
    def _db(self) -> AsyncSession:
        return self._uow.db

    # ── Publish ──────────────────────────────────────────────────

    async def publish_observation(
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
        _dedup_content_key: str | None = None
        _dedup_acquired = False

        if self._dedup_engine is not None:
            if isinstance(self._uow, AsyncUnitOfWork):
                # The dedup engine uses synchronous DB operations (advisory_lock,
                # _idem.check, _idem.acquire) that are incompatible with AsyncSession.
                # Skip dedup in the async path to avoid sync/async ORM misuse.
                # TODO: implement async-compatible dedup (Phase 2).
                logger.warning(
                    "SharedMemoryStore: dedup_engine skipped (async UoW not supported) "
                    "voter=%s key=%s — duplicate records may be created",
                    voter_name, key,
                )
            else:
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
            source_event_id = None

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
            try:
                if isinstance(self._uow, AsyncUnitOfWork):
                    async with self._db.begin_nested():
                        self._db.add(record)
                        await self._db.flush()
                else:
                    self._uow.begin_savepoint()
                    try:
                        self._db.add(record)
                        self._uow.flush()
                    except IntegrityError:
                        self._uow.savepoint_rollback()
                        raise
            except IntegrityError:
                # Duplicate write (concurrent activation or retry after partial commit).
                # The savepoint was rolled back; the outer transaction is intact.
                # Return the ID of the already-persisted record so the caller is idempotent.
                _dedup_filters = [
                    SharedMemoryRecord.voter_name == voter_name,
                    SharedMemoryRecord.memory_type == memory_type,
                    SharedMemoryRecord.key == key,
                ]
                if student_id is not None:
                    _dedup_filters.append(SharedMemoryRecord.student_id == student_id)
                else:
                    _dedup_filters.append(SharedMemoryRecord.student_id.is_(None))
                if module_id is not None:
                    _dedup_filters.append(SharedMemoryRecord.module_id == module_id)
                else:
                    _dedup_filters.append(SharedMemoryRecord.module_id.is_(None))
                _lookup = select(SharedMemoryRecord).where(and_(*_dedup_filters))
                if isinstance(self._uow, AsyncUnitOfWork):
                    _existing = (await self._db.execute(_lookup)).scalar_one_or_none()
                else:
                    _existing = self._db.execute(_lookup).scalar_one_or_none()
                _existing_id = _existing.id if _existing else None
                if _existing_id is None:
                    logger.warning(
                        "Memory conflict: no existing record found after IntegrityError "
                        "voter=%s type=%s key=%s student=%s — concurrent race window",
                        voter_name, memory_type, key, student_id,
                    )
                else:
                    logger.info(
                        "Memory conflict resolved: voter=%s type=%s key=%s "
                        "student=%s → existing=%s",
                        voter_name, memory_type, key, student_id, _existing_id,
                    )
                return _existing_id or ""

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
        propagation_ctx: Any | None = None,
    ) -> list[SharedMemoryRecord]:
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

        stmt = select(SharedMemoryRecord)
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

        if filters:
            stmt = stmt.where(and_(*filters))

        order_col = SharedMemoryRecord.created_at.desc() if order_desc else SharedMemoryRecord.created_at.asc()
        stmt = stmt.order_by(order_col).limit(limit)

        result = await self._db.execute(stmt)
        records = list(result.scalars().all())

        if not include_stale:
            records = [r for r in records if not is_stale(r)]

        if _prop_ended:
            try:
                from app.tracing import correlation_engine as _ce
                _ce.end()
            except Exception:
                pass

        return records

    async def query_by_key_pattern(
        self,
        key_prefix: str,
        *,
        student_id: str | None = None,
        module_id: str | None = None,
        memory_type: str | None = None,
        limit: int = 50,
        propagation_ctx: Any | None = None,
    ) -> list[SharedMemoryRecord]:
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

        stmt = (
            select(SharedMemoryRecord)
            .where(and_(*filters))
            .order_by(SharedMemoryRecord.created_at.desc())
            .limit(limit)
        )
        result = await self._db.execute(stmt)
        result_list = [r for r in result.scalars().all() if not is_stale(r)]

        if _prop_ended:
            try:
                from app.tracing import correlation_engine as _ce
                _ce.end()
            except Exception:
                pass

        return result_list

    # ── Single Record Access ─────────────────────────────────────

    async def get_by_id(self, record_id: str, propagation_ctx: Any | None = None) -> SharedMemoryRecord | None:
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

        stmt = select(SharedMemoryRecord).where(SharedMemoryRecord.id == record_id)
        result = await self._db.execute(stmt)
        record = result.scalar_one_or_none()

        if _prop_ended:
            try:
                from app.tracing import correlation_engine as _ce
                _ce.end()
            except Exception:
                pass

        return record

    # ── Lineage ──────────────────────────────────────────────────

    async def get_lineage(
        self,
        record_id: str,
        max_depth: int = 100,
    ) -> list[SharedMemoryRecord]:
        chain: list[SharedMemoryRecord] = []
        current_id: str | None = record_id
        depth = 0
        while current_id is not None and depth < max_depth:
            record = await self.get_by_id(current_id)
            if record is None:
                break
            chain.append(record)
            current_id = record.parent_id
            depth += 1
        chain.reverse()
        return chain

    # ── Conflict Resolution ──────────────────────────────────────

    async def resolve_conflicts(
        self,
        key: str,
        *,
        student_id: str | None = None,
        module_id: str | None = None,
        propagation_ctx: Any | None = None,
    ) -> dict[str, Any]:
        records = await self.query(
            student_id=student_id,
            module_id=module_id,
            key=key,
            include_stale=False,
            limit=100,
            propagation_ctx=propagation_ctx,
        )
        return resolve_conflict(records)

    # ── Staleness Management ─────────────────────────────────────

    async def remove_stale(self, batch_size: int = 100) -> int:
        # remove_stale uses await self._db.execute() and await self._db.delete(),
        # so it requires an AsyncSession.  Calling it with a sync UoW would fail
        # on the first await with TypeError.
        if not isinstance(self._uow, AsyncUnitOfWork):
            raise TypeError(
                "remove_stale() requires AsyncUnitOfWork; "
                f"got {type(self._uow).__name__}"
            )

        now = datetime.now(timezone.utc)
        stmt = (
            select(SharedMemoryRecord)
            .where(SharedMemoryRecord.ttl_seconds.isnot(None))
            .limit(batch_size)
        )
        result = await self._db.execute(stmt)
        records = list(result.scalars().all())
        stale = [r for r in records if is_stale(r, now=now)]
        for r in stale:
            # AsyncSession.delete() is a coroutine in SQLAlchemy 2.0 (greenlet_spawn).
            await self._db.delete(r)
        await self._uow.flush()

        count = len(stale)
        if count > 0:
            logger.info("Memory cleanup: removed %d stale records", count)
        return count

    # ── Aggregation ──────────────────────────────────────────────

    async def aggregate_confidence(
        self,
        key: str,
        *,
        student_id: str | None = None,
        module_id: str | None = None,
        propagation_ctx: Any | None = None,
    ) -> float:
        records = await self.query(
            student_id=student_id,
            module_id=module_id,
            key=key,
            include_stale=False,
            limit=100,
            propagation_ctx=propagation_ctx,
        )
        return compute_memory_confidence(records)

    # ── Count ────────────────────────────────────────────────────

    async def count(
        self,
        *,
        student_id: str | None = None,
        module_id: str | None = None,
        memory_type: str | None = None,
    ) -> int:
        filters = []
        if student_id is not None:
            filters.append(SharedMemoryRecord.student_id == student_id)
        if module_id is not None:
            filters.append(SharedMemoryRecord.module_id == module_id)
        if memory_type is not None:
            filters.append(SharedMemoryRecord.memory_type == memory_type)

        stmt = select(func.count()).select_from(SharedMemoryRecord)
        if filters:
            stmt = stmt.where(and_(*filters))

        result = await self._db.execute(stmt)
        return result.scalar_one()


def _nullspan():
    class _NullSpan:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
    return _NullSpan()
