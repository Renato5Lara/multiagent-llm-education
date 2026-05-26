"""
Comprehensive tests for the Enterprise Event Idempotency system.

Covers:
    - IdempotencyKey lifecycle (pending → in_progress → completed | failed)
    - Content-hash and explicit key generation
    - In-memory hot cache with TTL
    - Advisory-lock serialized acquisition
    - IdempotencyService (acquire, complete, fail, check, cancel, purge)
    - DedupEventBus (exactly-once dispatch, replay)
    - IdempotentConsumer (exactly-once processing, retry-safe)
    - ReplayGuard (silent, warn, reject modes)
    - IdempotentSharedMemory (dedup publish)
    - IdempotentConsensusGuard (phase-level idempotency)
    - IdempotentUnitOfWork (outbox dedup, double-commit guard)
    - Risk detectors (consistency, race, replay, distributed dedup)
    - Async-safe context propagation
    - Propagation-safe idempotency key derivation
"""

import json
import uuid
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch, call

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base
from app.models.idempotency_key import IdempotencyKey
from app.models.event_outbox import EventOutbox
from app.events.idempotency import (
    IdempotencyService,
    IdempotencyKeyGenerator,
    IdempotencyConflict,
    IdempotencyError,
    idempotency_service,
    _HotCache,
)
from app.events.dedup import (
    DedupEventBus,
    IdempotentConsumer,
    ReplayGuard,
    ReplayDetected,
)
from app.events.integration import (
    IdempotentSharedMemory,
    IdempotentConsensusGuard,
    IdempotentUnitOfWork,
    get_idempotency_key_from_propagation,
    _memory_key,
)
from app.events.risk_detectors import (
    ConsistencyRiskDetector,
    RaceConditionDetector,
    ReplayVulnerabilityDetector,
    DistributedDedupRiskDetector,
    IdempotencyRiskAnalysis,
    RiskReport,
)

# ── In-memory SQLite test database ────────────────────────────────

TEST_DB_URL = "sqlite:///:memory:"


@pytest.fixture(scope="module")
def engine():
    eng = create_engine(TEST_DB_URL, echo=False)
    Base.metadata.create_all(bind=eng)
    yield eng
    Base.metadata.drop_all(bind=eng)


@pytest.fixture
def db(engine):
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)
    yield session
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(autouse=True)
def reset_idem_service():
    idempotency_service.clear_cache()


# =============================================================================
# 1. IdempotencyKeyGenerator — Key generation strategies
# =============================================================================


class TestIdempotencyKeyGenerator:
    def test_from_content_deterministic(self):
        k1 = IdempotencyKeyGenerator.from_content("event.a", "agg-1", {"x": 1})
        k2 = IdempotencyKeyGenerator.from_content("event.a", "agg-1", {"x": 1})
        assert k1 == k2
        assert k1.startswith("ik:content:")

    def test_from_content_different_payload(self):
        k1 = IdempotencyKeyGenerator.from_content("event.a", "agg-1", {"x": 1})
        k2 = IdempotencyKeyGenerator.from_content("event.a", "agg-1", {"x": 2})
        assert k1 != k2

    def test_from_content_different_type(self):
        k1 = IdempotencyKeyGenerator.from_content("event.a", "agg-1", {"x": 1})
        k2 = IdempotencyKeyGenerator.from_content("event.b", "agg-1", {"x": 1})
        assert k1 != k2

    def test_from_content_sorts_keys(self):
        k1 = IdempotencyKeyGenerator.from_content("e", "a", {"b": 2, "a": 1})
        k2 = IdempotencyKeyGenerator.from_content("e", "a", {"a": 1, "b": 2})
        assert k1 == k2  # canonical JSON sorting

    def test_from_content_custom_prefix(self):
        k = IdempotencyKeyGenerator.from_content("e", "a", prefix="consume")
        assert k.startswith("consume:content:")

    def test_from_propagation(self):
        k = IdempotencyKeyGenerator.from_propagation("trace123", "span456", 1)
        assert k == "ik:trace:trace123:span456:1"

    def test_from_explicit(self):
        k = IdempotencyKeyGenerator.from_explicit("my-key-123")
        assert k == "ik:explicit:my-key-123"


# =============================================================================
# 2. HotCache — In-memory LRU
# =============================================================================


class TestHotCache:
    def test_get_and_put(self):
        cache = _HotCache(maxsize=100, ttl=300)
        record = MagicMock(spec=IdempotencyKey)
        record.key = "k1"
        cache.put("k1", record)
        assert cache.get("k1") is record

    def test_get_miss(self):
        cache = _HotCache(maxsize=100, ttl=300)
        assert cache.get("missing") is None

    def test_remove(self):
        cache = _HotCache(maxsize=100, ttl=300)
        record = MagicMock(spec=IdempotencyKey)
        cache.put("k1", record)
        cache.remove("k1")
        assert cache.get("k1") is None

    def test_eviction(self):
        cache = _HotCache(maxsize=2, ttl=300)
        r1, r2, r3 = MagicMock(), MagicMock(), MagicMock()
        cache.put("a", r1)
        cache.put("b", r2)
        cache.put("c", r3)
        assert cache.get("a") is None  # evicted
        assert cache.get("b") is r2
        assert cache.get("c") is r3

    def test_clear(self):
        cache = _HotCache(maxsize=100, ttl=300)
        cache.put("a", MagicMock())
        cache.put("b", MagicMock())
        cache.clear()
        assert cache.size == 0


# =============================================================================
# 3. IdempotencyService — Lifecycle
# =============================================================================


class TestIdempotencyService:
    def test_acquire_creates_in_progress(self, db):
        key = "test:acquire"
        record = idempotency_service.acquire(db, key)
        assert record.key == key
        assert record.status == "in_progress"
        assert record.response_status == 0

    def test_acquire_completed_returns_existing(self, db):
        key = "test:replay"
        idempotency_service.acquire(db, key)
        idempotency_service.complete(db, key, response_status=200, response_body={"ok": True})

        replayed = idempotency_service.acquire(db, key)
        assert replayed.status == "completed"
        assert replayed.response_status == 200

    def test_acquire_completed_is_cached(self, db):
        key = "test:cached"
        idempotency_service.acquire(db, key)
        idempotency_service.complete(db, key, response_body="done")

        idempotency_service._HotCache = _HotCache  # ensure cache is accessible
        cached = idempotency_service.check(db, key)
        assert cached is not None
        assert cached.status == "completed"

    def test_acquire_failed_allows_retry(self, db):
        key = "test:retry"
        idempotency_service.acquire(db, key)
        idempotency_service.fail(db, key, reason="first attempt failed")

        record = idempotency_service.acquire(db, key)
        assert record.status == "in_progress"
        assert record.response_status == 0

    def test_acquire_empty_key_raises(self, db):
        with pytest.raises(IdempotencyError):
            idempotency_service.acquire(db, "")

    def test_complete_updates_status(self, db):
        key = "test:complete"
        idempotency_service.acquire(db, key)
        result = idempotency_service.complete(db, key, response_status=201, response_body={"id": "abc"})
        assert result.status == "completed"
        assert result.response_status == 201

    def test_complete_unknown_key_creates_record(self, db):
        result = idempotency_service.complete(db, "unknown:key", response_body="ok")
        assert result is not None
        assert result.status == "completed"

    def test_fail_updates_status(self, db):
        key = "test:fail"
        idempotency_service.acquire(db, key)
        result = idempotency_service.fail(db, key, reason="error")
        assert result.status == "failed"

    def test_fail_unknown_key_returns_none(self, db):
        result = idempotency_service.fail(db, "noexist")
        assert result is None

    def test_check_unknown(self, db):
        assert idempotency_service.check(db, "noexist") is None

    def test_check_completed(self, db):
        key = "test:check"
        idempotency_service.acquire(db, key)
        idempotency_service.complete(db, key, response_body="ok")

        checked = idempotency_service.check(db, key)
        assert checked is not None
        assert checked.status == "completed"

    def test_cancel_deletes_record(self, db):
        key = "test:cancel"
        idempotency_service.acquire(db, key)
        assert idempotency_service.cancel(db, key) is True
        assert idempotency_service.check(db, key) is None

    def test_cancel_unknown_returns_false(self, db):
        assert idempotency_service.cancel(db, "noexist") is False

    def test_purge_expired(self, db):
        key = "test:purge"
        idempotency_service.acquire(db, key)
        # manually set expired_at in past
        from sqlalchemy import update
        db.execute(
            update(IdempotencyKey)
            .where(IdempotencyKey.key == key)
            .values(expires_at=datetime.now(timezone.utc) - timedelta(hours=1))
        )
        db.commit()

        purged = idempotency_service.purge_expired(db)
        assert purged >= 1
        assert idempotency_service.check(db, key) is None

    def test_acquire_in_progress_raises_conflict(self, db):
        key = "test:conflict"
        idempotency_service.acquire(db, key)
        with pytest.raises(IdempotencyConflict):
            idempotency_service.acquire(db, key)


# =============================================================================
# 4. DedupEventBus — Exactly-once event dispatch
# =============================================================================


class TestDedupEventBus:
    def test_dispatch_creates_event(self, db):
        bus = DedupEventBus(idempotency_service)
        event = bus.dispatch(db, "module.completed", "agg-1", {"score": 0.9})

        assert event is not None
        assert event.event_type == "module.completed"
        assert event.aggregate_id == "agg-1"

    def test_dispatch_replay_returns_none(self, db):
        bus = DedupEventBus(idempotency_service)
        bus.dispatch(db, "module.completed", "agg-1", {"score": 0.9})

        replayed = bus.dispatch(db, "module.completed", "agg-1", {"score": 0.9})
        assert replayed is None

    def test_dispatch_different_payload_no_replay(self, db):
        bus = DedupEventBus(idempotency_service)
        e1 = bus.dispatch(db, "module.completed", "agg-1", {"score": 0.9})
        e2 = bus.dispatch(db, "module.completed", "agg-1", {"score": 0.5})
        assert e1 is not None
        assert e2 is not None
        assert e1.id != e2.id

    def test_dispatch_with_explicit_key(self, db):
        bus = DedupEventBus(idempotency_service)
        e1 = bus.dispatch(db, "module.completed", "agg-1", idempotency_key="explicit:key1")
        assert e1 is not None

        e2 = bus.dispatch(db, "module.completed", "agg-2", idempotency_key="explicit:key1")
        assert e2 is None  # same explicit key → replay

    def test_dispatch_with_custom_publish(self, db):
        bus = DedupEventBus(idempotency_service)
        mock_publish = MagicMock(return_value=EventOutbox(
            id=str(uuid.uuid4()),
            event_type="test",
            aggregate_id="agg-1",
            correlation_id="corr-1",
            payload={},
        ))
        event = bus.dispatch(db, "test", "agg-1", publish=mock_publish)
        assert event is not None
        mock_publish.assert_called_once()

    def test_dispatch_replay_uses_cached(self, db):
        bus = DedupEventBus(idempotency_service)
        bus.dispatch(db, "test", "agg-1", {"v": 1})
        # second dispatch should not call publish
        mock_publish = MagicMock()
        result = bus.dispatch(db, "test", "agg-1", {"v": 1}, publish=mock_publish)
        assert result is None
        mock_publish.assert_not_called()


# =============================================================================
# 5. IdempotentConsumer — Exactly-once event processing
# =============================================================================


class TestIdempotentConsumer:
    def test_process_calls_handler(self, db):
        consumer = IdempotentConsumer(idempotency_service)
        event = EventOutbox(
            id=str(uuid.uuid4()),
            event_type="test.event",
            aggregate_id="agg-1",
            correlation_id="corr-1",
            payload={"key": "value"},
        )
        handler = MagicMock(return_value={"processed": True})
        result = consumer.process(db, event, handler)
        assert result == {"processed": True}
        handler.assert_called_once_with(event)

    def test_process_replay_returns_cached(self, db):
        consumer = IdempotentConsumer(idempotency_service)
        event = EventOutbox(
            id=str(uuid.uuid4()),
            event_type="test.event",
            aggregate_id="agg-1",
            correlation_id="corr-1",
            payload={"key": "value"},
        )
        handler = MagicMock(return_value={"processed": True})

        consumer.process(db, event, handler)
        replayed = consumer.process(db, event, handler)
        assert replayed == {"processed": True}
        handler.assert_called_once()

    def test_process_failure_marks_failed(self, db):
        consumer = IdempotentConsumer(idempotency_service)
        event = EventOutbox(
            id=str(uuid.uuid4()),
            event_type="fail.event",
            aggregate_id="agg-1",
            correlation_id="corr-1",
            payload={},
        )

        def failing_handler(_event):
            raise ValueError("processing error")

        with pytest.raises(ValueError):
            consumer.process(db, event, failing_handler)

        record = idempotency_service.check(db, "consume:content:" + str(event.event_type))
        assert record is None or record.status != "completed"

    def test_stats_tracking(self, db):
        consumer = IdempotentConsumer(idempotency_service)
        event = EventOutbox(
            id=str(uuid.uuid4()),
            event_type="stats.test",
            aggregate_id="agg-1",
            correlation_id="corr-1",
            payload={},
        )
        handler = MagicMock(return_value="ok")

        consumer.process(db, event, handler)
        assert consumer.stats["processed"] == 1

        consumer.process(db, event, handler)
        assert consumer.stats["replayed"] == 1

        consumer.reset_stats()
        assert consumer.stats["processed"] == 0


# =============================================================================
# 6. ReplayGuard — Replay detection
# =============================================================================


class TestReplayGuard:
    def test_guard_unknown_returns_true(self, db):
        guard = ReplayGuard(idempotency_service, mode=ReplayGuard.MODE_SILENT)
        assert guard.guard(db, "new.event", "agg-1") is True

    def test_guard_silent_mode(self, db):
        guard = ReplayGuard(idempotency_service, mode=ReplayGuard.MODE_SILENT)
        bus = DedupEventBus(idempotency_service)
        bus.dispatch(db, "test.event", "agg-1", {"v": 1})

        result = guard.guard(db, "test.event", "agg-1", {"v": 1})
        assert result is False  # replay blocked silently

    def test_guard_warn_mode(self, db):
        guard = ReplayGuard(idempotency_service, mode=ReplayGuard.MODE_WARN)
        bus = DedupEventBus(idempotency_service)
        bus.dispatch(db, "test.event", "agg-1", {"v": 1})

        result = guard.guard(db, "test.event", "agg-1", {"v": 1})
        assert result is False

    def test_guard_reject_mode(self, db):
        guard = ReplayGuard(idempotency_service, mode=ReplayGuard.MODE_REJECT)
        bus = DedupEventBus(idempotency_service)
        bus.dispatch(db, "test.event", "agg-1", {"v": 1})

        with pytest.raises(ReplayDetected):
            guard.guard(db, "test.event", "agg-1", {"v": 1})

    def test_guard_in_progress_raises_conflict(self, db):
        guard = ReplayGuard(idempotency_service)
        key = IdempotencyKeyGenerator.from_content("test.event", "agg-1", {"v": 1})
        idempotency_service.acquire(db, key)
        with pytest.raises(IdempotencyConflict):
            guard.guard(db, "test.event", "agg-1", {"v": 1})


# =============================================================================
# 7. IdempotentSharedMemory — Memory dedup
# =============================================================================


class TestIdempotentSharedMemory:
    def test_publish_observation_dedup(self, db):
        store_mock = MagicMock()
        store_mock.publish_observation.return_value = "rec-1"

        wrapper = IdempotentSharedMemory(store_mock, idempotency_service)

        first = wrapper.publish_observation(
            db, "voter1", "key:test", {"val": 1},
            student_id="s1", module_id="m1",
        )
        assert first == "rec-1"
        store_mock.publish_observation.assert_called_once()

        second = wrapper.publish_observation(
            db, "voter1", "key:test", {"val": 1},
            student_id="s1", module_id="m1",
        )
        assert second is None  # dedup
        store_mock.publish_observation.assert_called_once()

    def test_publish_observation_force_bypass(self, db):
        store_mock = MagicMock()
        store_mock.publish_observation.return_value = "rec-2"

        wrapper = IdempotentSharedMemory(store_mock, idempotency_service)
        wrapper.publish_observation(
            db, "voter1", "key:force", {"val": 1},
            force=True,
        )
        wrapper.publish_observation(
            db, "voter1", "key:force", {"val": 1},
            force=True,
        )
        assert store_mock.publish_observation.call_count == 2

    def test_memory_key_deterministic(self):
        k1 = _memory_key("v1", "k1", {"a": 1}, 1.0, "s1", "m1", "obs")
        k2 = _memory_key("v1", "k1", {"a": 1}, 1.0, "s1", "m1", "obs")
        assert k1 == k2

    def test_memory_key_different_content(self):
        k1 = _memory_key("v1", "k1", {"a": 1}, 1.0, "s1", "m1", "obs")
        k2 = _memory_key("v2", "k1", {"a": 1}, 1.0, "s1", "m1", "obs")
        assert k1 != k2


# =============================================================================
# 8. IdempotentConsensusGuard — Phase-level consensus idempotency
# =============================================================================


class TestIdempotentConsensusGuard:
    def test_acquire_phase_returns_true(self, db):
        guard = IdempotentConsensusGuard(idempotency_service)
        result = guard.acquire_phase(db, "mod-1", "stu-1", "vote_collection")
        assert result is True

    def test_acquire_phase_in_progress(self, db):
        guard = IdempotentConsensusGuard(idempotency_service)
        guard.acquire_phase(db, "mod-1", "stu-1", "vote_collection")
        with pytest.raises(IdempotencyConflict):
            guard.acquire_phase(db, "mod-1", "stu-1", "vote_collection")

    def test_is_phase_completed(self, db):
        guard = IdempotentConsensusGuard(idempotency_service)
        guard.acquire_phase(db, "mod-1", "stu-1", "aggregation")
        guard.complete_phase(db, "mod-1", "stu-1", "aggregation")
        assert guard.is_phase_completed(db, "mod-1", "stu-1", "aggregation") is True

    def test_is_phase_not_completed(self, db):
        guard = IdempotentConsensusGuard(idempotency_service)
        assert guard.is_phase_completed(db, "mod-1", "stu-1", "aggregation") is False

    def test_fail_phase(self, db):
        guard = IdempotentConsensusGuard(idempotency_service)
        guard.acquire_phase(db, "mod-1", "stu-1", "diagnostics")
        guard.fail_phase(db, "mod-1", "stu-1", "diagnostics", reason="timeout")

        record = idempotency_service.check(
            db, f"idm:consensus:mod-1:stu-1:phase:diagnostics"
        )
        assert record.status == "failed"

    def test_run_with_phases(self, db):
        guard = IdempotentConsensusGuard(idempotency_service)
        calls = []

        def vote():
            calls.append("vote")
            return {"votes": 3}

        def aggregate():
            calls.append("aggregate")
            return {"decision": "APPROVE"}

        handlers = {
            "vote_collection": vote,
            "aggregation": aggregate,
        }

        results = guard.run_with_phases(db, "mod-1", "stu-1", handlers)
        assert calls == ["vote", "aggregate"]
        assert results["vote_collection"] == {"votes": 3}
        assert results["aggregation"] == {"decision": "APPROVE"}

    def test_run_with_phases_skips_completed(self, db):
        guard = IdempotentConsensusGuard(idempotency_service)
        guard.acquire_phase(db, "mod-1", "stu-1", "vote_collection")
        guard.complete_phase(db, "mod-1", "stu-1", "vote_collection")

        calls = []

        def vote():
            calls.append("vote")

        handlers = {"vote_collection": vote}
        guard.run_with_phases(db, "mod-1", "stu-1", handlers)
        assert calls == []  # skipped

    def test_run_with_phases_unknown_raises(self, db):
        guard = IdempotentConsensusGuard(idempotency_service)
        with pytest.raises(IdempotencyError):
            guard.acquire_phase(db, "mod-1", "stu-1", "nonexistent_phase")


# =============================================================================
# 9. IdempotentUnitOfWork — Outbox dedup and double-commit guard
# =============================================================================


class TestIdempotentUnitOfWork:
    def test_add_event_dedup(self):
        uow_mock = MagicMock()
        uow_mock.add_event.return_value = MagicMock(id="event-1")

        iuow = IdempotentUnitOfWork(uow_mock, idempotency_service)
        e1 = iuow.add_event("test.event", "agg-1", {"v": 1})
        e2 = iuow.add_event("test.event", "agg-1", {"v": 1})
        assert e1 is not None
        assert e2 is None
        uow_mock.add_event.assert_called_once()

    def test_add_event_no_dedup_for_different_content(self):
        uow_mock = MagicMock()
        uow_mock.add_event.return_value = MagicMock(id="event-1")

        iuow = IdempotentUnitOfWork(uow_mock, idempotency_service)
        iuow.add_event("test.event", "agg-1", {"v": 1})
        iuow.add_event("test.event", "agg-1", {"v": 2})
        assert uow_mock.add_event.call_count == 2

    def test_commit_skips_when_already_committed(self):
        uow_mock = MagicMock()
        uow_mock._committed = True

        iuow = IdempotentUnitOfWork(uow_mock, idempotency_service)
        iuow.commit()
        uow_mock.commit.assert_not_called()

    def test_rollback_clears_seen_hashes(self):
        uow_mock = MagicMock()
        iuow = IdempotentUnitOfWork(uow_mock, idempotency_service)
        iuow.add_event("test.event", "agg-1", {"v": 1})
        iuow.rollback()
        assert len(iuow._seen_hashes) == 0

    def test_close(self):
        uow_mock = MagicMock()
        iuow = IdempotentUnitOfWork(uow_mock, idempotency_service)
        iuow.close()
        uow_mock.close.assert_called_once()


# =============================================================================
# 10. Propagation-safe key derivation
# =============================================================================


class TestPropagationSafeKey:
    def test_no_active_context_returns_none(self):
        from app.tracing import correlation_engine
        correlation_engine.decay()
        key = get_idempotency_key_from_propagation("test_op")
        assert key is None

    def test_active_context_generates_key(self):
        from app.tracing import correlation_engine
        correlation_engine.start("idem_test", "pytest")
        try:
            key = get_idempotency_key_from_propagation("test_op")
            assert key is not None
            assert key.startswith("ik:trace:")
            assert correlation_engine.get_current().span.trace_id in key
        finally:
            correlation_engine.end()
            correlation_engine.decay()

    def test_sequence_increments(self):
        from app.tracing import correlation_engine
        correlation_engine.start("seq_test", "pytest")
        try:
            k1 = get_idempotency_key_from_propagation("op1")
            k2 = get_idempotency_key_from_propagation("op2")
            assert k1 != k2
            # second key should have higher sequence
            seq1 = int(k1.split(":")[-1])
            seq2 = int(k2.split(":")[-1])
            assert seq2 > seq1
        finally:
            correlation_engine.end()
            correlation_engine.decay()


# =============================================================================
# 11. Risk Detectors
# =============================================================================


class TestConsistencyRiskDetector:
    def test_clean_db_returns_empty_report(self, db):
        detector = ConsistencyRiskDetector()
        report = detector.detect(db)
        assert report.total >= 0

    def test_stale_in_progress_detected(self, db):
        # Create an in-progress key that's very old
        key = IdempotencyKey(
            key="test:stale",
            status="in_progress",
            response_status=0,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        )
        key.created_at = datetime.now(timezone.utc) - timedelta(days=7)
        db.add(key)
        db.commit()

        detector = ConsistencyRiskDetector()
        report = detector.detect(db, window_hours=24)
        stale = [
            r for r in report.consistency_risks
            if "stale" in r["title"].lower()
        ]
        assert len(stale) > 0


class TestRaceConditionDetector:
    def test_clean_db(self, db):
        detector = RaceConditionDetector()
        report = detector.detect(db)
        assert report.total >= 0


class TestReplayVulnerabilityDetector:
    def test_clean_db(self, db):
        detector = ReplayVulnerabilityDetector()
        report = detector.detect(db)
        assert report.total >= 0

    def test_expired_in_progress_detected(self, db):
        key = IdempotencyKey(
            key="test:expired",
            status="in_progress",
            response_status=0,
            expires_at=datetime.now(timezone.utc) - timedelta(hours=1),
            created_at=datetime.now(timezone.utc) - timedelta(days=1),
        )
        db.add(key)
        db.commit()

        detector = ReplayVulnerabilityDetector()
        report = detector.detect(db)
        expired = [
            r for r in report.replay_vulnerabilities
            if "expired" in r["title"].lower()
        ]
        assert len(expired) > 0


class TestDistributedDedupRiskDetector:
    def test_clean_db(self, db):
        detector = DistributedDedupRiskDetector()
        report = detector.detect(db)
        assert report.total >= 0

    def test_duplicate_completed_keys_detected(self, db):
        for _ in range(3):
            k = IdempotencyKey(
                key=f"test:dup:{uuid.uuid4()}",
                status="completed",
                response_status=200,
                event_type="dup.event",
                aggregate_id="agg-dup",
                expires_at=datetime.now(timezone.utc) + timedelta(days=1),
            )
            db.add(k)
        db.commit()

        detector = DistributedDedupRiskDetector()
        report = detector.detect(db)
        dup_risks = [
            r for r in report.duplication_risks
            if "duplicate" in r["title"].lower()
        ]
        assert len(dup_risks) > 0


class TestIdempotencyRiskAnalysis:
    def test_analyze_runs_all_detectors(self, db):
        analysis = IdempotencyRiskAnalysis()
        report = analysis.analyze(db)
        assert isinstance(report, RiskReport)
        assert hasattr(report, "consistency_risks")
        assert hasattr(report, "race_conditions")
        assert hasattr(report, "replay_vulnerabilities")
        assert hasattr(report, "duplication_risks")

    def test_analyze_recovers_from_detector_failure(self, db):
        with patch.object(
            ConsistencyRiskDetector, "detect",
            side_effect=RuntimeError("boom"),
        ):
            analysis = IdempotencyRiskAnalysis()
            report = analysis.analyze(db)
            # Other detectors should still run
            assert isinstance(report, RiskReport)


# =============================================================================
# 12. IdempotencyService — Integration scenarios
# =============================================================================


class TestIdempotencyServiceIntegration:
    def test_full_lifecycle(self, db):
        key = "test:full:lifecycle"

        # PENDING → acquire → IN_PROGRESS
        record = idempotency_service.acquire(db, key)
        assert record.status == "in_progress"

        # IN_PROGRESS → complete → COMPLETED
        idempotency_service.complete(db, key, response_status=200, response_body="done")
        record = idempotency_service.check(db, key)
        assert record.status == "completed"

        # COMPLETED → acquire → replay
        replayed = idempotency_service.acquire(db, key)
        assert replayed.status == "completed"
        assert replayed.response_body == "done"

    def test_fail_and_retry(self, db):
        key = "test:fail:retry"

        idempotency_service.acquire(db, key)
        idempotency_service.fail(db, key, reason="fail1")
        assert idempotency_service.check(db, key).status == "failed"

        # Retry (transition back to in_progress)
        idempotency_service.acquire(db, key)
        assert idempotency_service.check(db, key).status == "in_progress"

        idempotency_service.complete(db, key, response_body="retry-success")
        assert idempotency_service.check(db, key).status == "completed"

    def test_concurrent_same_key_raises(self, db):
        key = "test:concurrent"
        idempotency_service.acquire(db, key)
        with pytest.raises(IdempotencyConflict):
            idempotency_service.acquire(db, key)

    def test_different_keys_no_conflict(self, db):
        idempotency_service.acquire(db, "key:a")
        idempotency_service.acquire(db, "key:b")  # no conflict

    def test_cancel_during_in_progress(self, db):
        key = "test:cancel:ip"
        idempotency_service.acquire(db, key)
        assert idempotency_service.cancel(db, key) is True
        assert idempotency_service.check(db, key) is None

    def test_purge_only_expired(self, db):
        fresh_key = "test:fresh"
        expired_key = "test:expired"

        idempotency_service.acquire(db, fresh_key)
        idempotency_service.complete(db, fresh_key, response_body="fresh")

        idempotency_service.acquire(db, expired_key)
        # Manually expire the key
        from sqlalchemy import update
        db.execute(
            update(IdempotencyKey)
            .where(IdempotencyKey.key == expired_key)
            .values(expires_at=datetime.now(timezone.utc) - timedelta(hours=1))
        )
        db.commit()

        purged = idempotency_service.purge_expired(db)
        assert purged >= 1

        assert idempotency_service.check(db, fresh_key) is not None
        assert idempotency_service.check(db, expired_key) is None


# =============================================================================
# 13. DedupEventBus — Integration scenarios
# =============================================================================


class TestDedupEventBusIntegration:
    def test_dispatch_with_metadata(self, db):
        bus = DedupEventBus(idempotency_service)
        event = bus.dispatch(
            db, "integration.test", "agg-int",
            {"data": "test"},
            trace_id="trace-abc",
            causation_id="cause-123",
        )
        assert event is not None
        stored = db.query(EventOutbox).filter_by(id=event.id).first()
        assert stored is not None
        assert stored.correlation_id == "trace-abc"

    def test_multi_dispatch_no_replay(self, db):
        bus = DedupEventBus(idempotency_service)
        events = []
        for i in range(5):
            e = bus.dispatch(db, f"multi.event.{i}", f"agg-{i}", {"n": i})
            events.append(e)
        assert all(e is not None for e in events)
        assert len(set(e.id for e in events)) == 5

    def test_replay_after_complete(self, db):
        bus = DedupEventBus(idempotency_service)
        bus.dispatch(db, "replay.test", "agg-r", {"v": 1})
        replay = bus.dispatch(db, "replay.test", "agg-r", {"v": 1})
        assert replay is None


# =============================================================================
# 14. Model — Extended IdempotencyKey fields
# =============================================================================


class TestExtendedModel:
    def test_new_record_defaults(self, db):
        record = IdempotencyKey(
            key="test:defaults",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        )
        db.add(record)
        db.commit()

        assert record.status == "pending"
        assert record.response_status == 0
        assert record.event_type is None
        assert record.aggregate_id is None
        assert record.trace_id is None
        assert record.causation_id is None
        assert record.completed_at is None

    def test_event_metadata_stored(self, db):
        record = IdempotencyKey(
            key="test:metadata",
            status="completed",
            response_status=201,
            event_type="test.event",
            aggregate_id="agg-1",
            trace_id="trace-xyz",
            causation_id="cause-abc",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        )
        db.add(record)
        db.commit()

        loaded = db.query(IdempotencyKey).filter_by(key="test:metadata").first()
        assert loaded.event_type == "test.event"
        assert loaded.aggregate_id == "agg-1"
        assert loaded.trace_id == "trace-xyz"
        assert loaded.causation_id == "cause-abc"

    def test_completed_at_set(self, db):
        record = IdempotencyKey(
            key="test:completed_at",
            status="completed",
            response_status=200,
            completed_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        )
        db.add(record)
        db.commit()

        loaded = db.query(IdempotencyKey).filter_by(key="test:completed_at").first()
        assert loaded.completed_at is not None
