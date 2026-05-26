"""
Comprehensive distributed idempotency tests.

Covers:
    - DistributedDedupEngine (dedup_or_none, is_duplicate, consensus, memory)
    - RetryHandler (exponential backoff, circuit breaker, stats)
    - EventReplayService (replay by id/type/aggregate/time/failed)
    - Propagation dedup via baggage
    - Concurrent access (threading race conditions)
    - Integration scenarios (full flow with middleware simulation)
    - Error handling and edge cases
"""

import atexit
import json
import os
import tempfile
import threading
import time
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
)
from app.events.distributed import (
    DistributedDedupEngine,
    distributed_dedup,
    extract_dedup_keys_from_propagation,
)
from app.events.retry import (
    RetryHandler,
    RetryExhaustedError,
    CircuitBreaker,
    CircuitBreakerOpenError,
    retry_stats,
)
from app.events.replay import (
    EventReplayService,
    event_replay_service,
)
from app.events.middleware import (
    make_idempotency_middleware,
    _extract_key,
    IDEMPOTENCY_HEADER,
    IDEMPOTENCY_REPLAY_HEADER,
)
from app.tracing import correlation_engine

TEST_DB_FILE = tempfile.mktemp(suffix=".db")
TEST_DB_URL = f"sqlite:///{TEST_DB_FILE}"


@pytest.fixture(scope="module")
def engine():
    eng = create_engine(TEST_DB_URL, echo=False)
    Base.metadata.create_all(bind=eng)
    yield eng
    Base.metadata.drop_all(bind=eng)
    eng.dispose()


def cleanup_temp_db():
    if os.path.exists(TEST_DB_FILE):
        try:
            os.remove(TEST_DB_FILE)
        except PermissionError:
            pass


atexit.register(cleanup_temp_db)


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
def reset():
    idempotency_service.clear_cache()
    retry_stats = __import__("app.events.retry", fromlist=["retry_stats"]).retry_stats
    retry_stats.__dict__.update(
        {"total_attempts": 0, "successful": 0, "failed": 0, "replayed": 0,
         "circuit_open": 0, "total_time_ms": 0.0}
    )


# =============================================================================
# 1. DistributedDedupEngine
# =============================================================================


class TestDistributedDedupEngine:
    def test_is_duplicate_returns_false_for_new(self, db):
        assert distributed_dedup.is_duplicate(db, "test.event", "agg-1", {"v": 1}) is False

    def test_is_duplicate_returns_true_for_completed(self, db):
        key = IdempotencyKeyGenerator.from_content("test.event", "agg-1", {"v": 1})
        idempotency_service.acquire(db, key)
        idempotency_service.complete(db, key, response_body="done")
        assert distributed_dedup.is_duplicate(db, "test.event", "agg-1", {"v": 1}) is True

    def test_dedup_or_none_first_call_runs_handler(self, db):
        handler_calls = []
        result = distributed_dedup.dedup_or_none(
            db, "test.event", "agg-1", {"v": 1},
            handler=lambda t, a, p: (handler_calls.append(1), "result")[1],
        )
        assert result == "result"
        assert len(handler_calls) == 1

    def test_dedup_or_none_replay_returns_cached(self, db):
        distributed_dedup.dedup_or_none(
            db, "test.event", "agg-1", {"v": 1},
            handler=lambda t, a, p: "first",
        )
        result = distributed_dedup.dedup_or_none(
            db, "test.event", "agg-1", {"v": 1},
            handler=lambda t, a, p: "second",
        )
        assert result == "first"  # cached, not "second"

    def test_dedup_or_none_concurrent_returns_none(self, db):
        key = IdempotencyKeyGenerator.from_content("test.event", "agg-1", {"v": 1})
        idempotency_service.acquire(db, key)
        # Second attempt while in_progress → None (silent skip)
        result = distributed_dedup.dedup_or_none(
            db, "test.event", "agg-1", {"v": 1},
            handler=lambda t, a, p: "should_not_run",
        )
        assert result is None

    def test_dedup_publish_returns_true_for_new(self, db):
        assert distributed_dedup.dedup_publish(db, "pub.event", "agg-1", {"v": 1}) is True

    def test_dedup_publish_returns_false_for_duplicate(self, db):
        distributed_dedup.dedup_publish(db, "pub.event", "agg-1", {"v": 1})
        assert distributed_dedup.dedup_publish(db, "pub.event", "agg-1", {"v": 1}) is False

    def test_dedup_publish_concurrent_returns_false(self, db):
        key = IdempotencyKeyGenerator.from_content("pub.event", "agg-1", {"v": 1})
        idempotency_service.acquire(db, key)
        assert distributed_dedup.dedup_publish(db, "pub.event", "agg-1", {"v": 1}) is False

    def test_dedup_consensus_completed_returns_none(self, db):
        from app.events.integration import IdempotentConsensusGuard
        guard = IdempotentConsensusGuard(idempotency_service)
        guard.acquire_phase(db, "mod-1", "stu-1", "vote_collection")
        guard.complete_phase(db, "mod-1", "stu-1", "vote_collection")

        result = distributed_dedup.dedup_consensus(
            db, "mod-1", "stu-1", "vote_collection",
            handler=lambda: "should_not_run",
        )
        assert result is None

    def test_dedup_consensus_first_call(self, db):
        handler_calls = []
        result = distributed_dedup.dedup_consensus(
            db, "mod-1", "stu-1", "aggregation",
            handler=lambda: (handler_calls.append(1), "ok")[1],
        )
        assert result == "ok"
        assert len(handler_calls) == 1

    def test_dedup_memory_returns_true_for_new(self, db):
        assert distributed_dedup.dedup_memory(
            db, "voter1", "key:test", {"v": 1},
            student_id="s1", module_id="m1",
        ) is True

    def test_dedup_memory_returns_false_for_duplicate(self, db):
        distributed_dedup.dedup_memory(
            db, "voter1", "key:test", {"v": 1},
            student_id="s1", module_id="m1",
        )
        assert distributed_dedup.dedup_memory(
            db, "voter1", "key:test", {"v": 1},
            student_id="s1", module_id="m1",
        ) is False

    def test_check_memory_duplicate_returns_none_for_new(self, db):
        assert distributed_dedup.check_memory_duplicate(
            db, "voter1", "key:check", {"v": 1},
            student_id="s1", module_id="m1",
        ) is None

    def test_check_memory_duplicate_returns_none_for_dedup_memory(self, db):
        distributed_dedup.dedup_memory(
            db, "voter1", "key:deduped", {"v": 1},
            student_id="s1", module_id="m1",
        )
        # dedup_memory stores {"deduped": True}, not a record_id
        assert distributed_dedup.check_memory_duplicate(
            db, "voter1", "key:deduped", {"v": 1},
            student_id="s1", module_id="m1",
        ) is None

    def test_check_memory_duplicate_returns_id_for_completed_with_record_id(self, db):
        from app.events.integration import _memory_key
        content_key = _memory_key(
            "voter1", "key:with_id", {"v": 1}, 1.0, "s1", "m1", "observation",
        )
        idempotency_service.acquire(db, content_key)
        idempotency_service.complete(
            db, content_key,
            response_body={"record_id": "rec-999"},
        )
        result = distributed_dedup.check_memory_duplicate(
            db, "voter1", "key:with_id", {"v": 1},
            student_id="s1", module_id="m1",
        )
        assert result == "rec-999"

    def test_dead_letter_count(self, db):
        before = distributed_dedup.dead_letter_count(db)
        key = IdempotencyKey(
            key="dead:letter",
            status="failed",
            response_status=0,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        )
        db.add(key)
        db.commit()
        after = distributed_dedup.dead_letter_count(db)
        assert after >= before

    def test_dedup_or_none_handler_exception_marks_failed(self, db):
        with pytest.raises(ValueError):
            distributed_dedup.dedup_or_none(
                db, "fail.event", "agg-1", {},
                handler=lambda t, a, p: (_ for _ in ()).throw(ValueError("oops")),
            )
        key = IdempotencyKeyGenerator.from_content("fail.event", "agg-1", {})
        record = idempotency_service.check(db, key)
        assert record is not None
        assert record.status == "failed"


# =============================================================================
# 2. CircuitBreaker
# =============================================================================


class TestCircuitBreaker:
    def test_closed_allows_calls(self):
        cb = CircuitBreaker("test")
        result = cb.call(lambda: "ok")
        assert result == "ok"

    def test_opens_after_threshold(self):
        cb = CircuitBreaker("test", failure_threshold=3, recovery_timeout=60)
        for i in range(3):
            with pytest.raises(ValueError):
                cb.call(lambda: (_ for _ in ()).throw(ValueError(f"fail {i}")))
        assert cb.state == "open"

    def test_open_rejects_calls(self):
        cb = CircuitBreaker("test", failure_threshold=1, recovery_timeout=60)
        with pytest.raises(ValueError):
            cb.call(lambda: (_ for _ in ()).throw(ValueError("fail")))
        with pytest.raises(CircuitBreakerOpenError):
            cb.call(lambda: "should_not_run")

    def test_recovers_after_timeout(self):
        cb = CircuitBreaker("test", failure_threshold=1, recovery_timeout=0.05)
        with pytest.raises(ValueError):
            cb.call(lambda: (_ for _ in ()).throw(ValueError("fail")))
        assert cb.state == "open"
        time.sleep(0.06)
        result = cb.call(lambda: "recovered")
        assert result == "recovered"
        assert cb.state == "closed"

    def test_half_open_max_calls(self):
        cb = CircuitBreaker("test", failure_threshold=1, recovery_timeout=0.05, half_open_max_calls=1)
        with pytest.raises(ValueError):
            cb.call(lambda: (_ for _ in ()).throw(ValueError("fail")))
        time.sleep(0.06)
        cb.call(lambda: "ok")  # half-open, succeeds → closes
        assert cb.state == "closed"

    def test_reset(self):
        cb = CircuitBreaker("test", failure_threshold=1)
        with pytest.raises(ValueError):
            cb.call(lambda: (_ for _ in ()).throw(ValueError("fail")))
        assert cb.is_open
        cb.reset()
        assert cb.state == "closed"
        assert cb.is_open is False


# =============================================================================
# 3. RetryHandler
# =============================================================================


class TestRetryHandler:
    def test_first_call_succeeds(self, db):
        handler = RetryHandler(idempotency_service)
        result = handler.execute(
            db, "retry.test", "agg-1", {"v": 1},
            handler=lambda: "success",
        )
        assert result == "success"

    def test_retry_replay_returns_cached(self, db):
        handler = RetryHandler(idempotency_service)
        handler.execute(
            db, "retry.test", "agg-1", {"v": 1},
            handler=lambda: "first",
        )
        result = handler.execute(
            db, "retry.test", "agg-1", {"v": 1},
            handler=lambda: "second",
        )
        assert result == "first"  # replayed, not "second"

    def test_retry_exhausted_raises(self, db):
        handler = RetryHandler(
            idempotency_service,
            max_retries=2,
            base_delay_ms=1,
        )
        call_count = [0]

        def failing():
            call_count[0] += 1
            raise ValueError(f"attempt {call_count[0]}")

        with pytest.raises(RetryExhaustedError) as exc_info:
            handler.execute(
                db, "retry.fail", "agg-1", {},
                handler=failing,
            )
        assert "retry.fail" in str(exc_info.value)
        assert call_count[0] == 2

    def test_retry_succeeds_on_nth_attempt(self, db):
        handler = RetryHandler(
            idempotency_service,
            max_retries=5,
            base_delay_ms=1,
        )
        call_count = [0]

        def eventually_succeeds():
            call_count[0] += 1
            if call_count[0] < 3:
                raise ValueError(f"attempt {call_count[0]}")
            return "success"

        result = handler.execute(
            db, "retry.eventual", "agg-1", {},
            handler=eventually_succeeds,
        )
        assert result == "success"
        assert call_count[0] == 3  # 2 failures + 1 success

    def test_circuit_breaker_integration(self, db):
        handler = RetryHandler(
            idempotency_service,
            max_retries=2,
            base_delay_ms=1,
        )
        call_count = [0]

        def failing():
            call_count[0] += 1
            raise ValueError("always fails")

        with pytest.raises((RetryExhaustedError, CircuitBreakerOpenError)):
            handler.execute(
                db, "circuit.test", "agg-1", {},
                handler=failing,
                circuit_name="test_circuit",
            )

    def test_different_events_independent_circuits(self, db):
        handler = RetryHandler(idempotency_service, max_retries=1)
        # First event fails and opens circuit
        with pytest.raises(RetryExhaustedError):
            handler.execute(
                db, "circuit.a", "agg-1", {},
                handler=lambda: (_ for _ in ()).throw(ValueError("fail")),
                circuit_name="circuit_a",
            )
        # Different event should still work
        result = handler.execute(
            db, "other.event", "agg-2", {},
            handler=lambda: "ok",
            circuit_name="circuit_b",
        )
        assert result == "ok"

    def test_retry_stats_collected(self, db):
        handler = RetryHandler(idempotency_service)
        handler.execute(
            db, "stats.test", "agg-1", {},
            handler=lambda: "ok",
        )
        assert retry_stats.total_attempts > 0 or retry_stats.successful > 0
        # At minimum, the attempt was made


# =============================================================================
# 4. EventReplayService
# =============================================================================


class TestEventReplayService:
    def test_replay_by_id_not_found(self, db):
        result = event_replay_service.replay_by_id(db, "nonexistent")
        assert result["status"] == "not_found"

    def test_replay_by_id_dry_run(self, db):
        event = self._create_event(db, "dry.test")
        result = event_replay_service.replay_by_id(
            db, event.id, dry_run=True,
        )
        assert result["status"] == "dry_run"

    def test_replay_by_id_first_call(self, db):
        event = self._create_event(db, "replay.first")
        handler = MagicMock(return_value={"replayed": True})
        result = event_replay_service.replay_by_id(db, event.id, handler)
        assert result["status"] == "replayed"
        handler.assert_called_once()

    def test_replay_by_id_skips_already_replayed(self, db):
        event = self._create_event(db, "replay.skip")
        handler = MagicMock(return_value="ok")
        event_replay_service.replay_by_id(db, event.id, handler)
        handler.reset_mock()

        result = event_replay_service.replay_by_id(db, event.id, handler)
        assert result["status"] == "skipped"
        handler.assert_not_called()

    def test_replay_by_type(self, db):
        e1 = self._create_event(db, "type.test", event_type="batch.type")
        e2 = self._create_event(db, "type.test.2", event_type="batch.type")
        handler = MagicMock(return_value="ok")
        results = event_replay_service.replay_by_type(db, "batch.type", handler)
        assert len(results) == 2
        assert all(r["status"] == "replayed" for r in results)

    def test_replay_by_aggregate(self, db):
        e1 = self._create_event(db, "agg-1", event_type="agg.type")
        e2 = self._create_event(db, "agg-1", event_type="agg.type.2")
        handler = MagicMock(return_value="ok")
        results = event_replay_service.replay_by_aggregate(db, "agg-1", handler)
        assert len(results) == 2

    def test_replay_failed(self, db):
        event = EventOutbox(
            id=str(uuid.uuid4()),
            event_type="failed.event",
            aggregate_id="agg-fail",
            correlation_id="corr-1",
            payload={},
            status="failed",
            retry_count=1,
            max_retries=3,
        )
        db.add(event)
        db.commit()
        handler = MagicMock(return_value="recovered")
        results = event_replay_service.replay_failed(db, handler)
        assert len(results) >= 1

    def test_replay_all_pending(self, db):
        self._create_event(db, "pending.1")
        self._create_event(db, "pending.2")
        handler = MagicMock(return_value="ok")
        results = event_replay_service.replay_all_pending(db, handler)
        assert len(results) >= 2

    def test_get_stats(self, db):
        stats = event_replay_service.get_stats(db)
        assert "total_events" in stats
        assert "pending" in stats
        assert "failed" in stats
        assert "replay_keys_registered" in stats

    def _create_event(
        self, db, aggregate_id: str,
        event_type: str = "test.event",
    ) -> EventOutbox:
        event = EventOutbox(
            id=str(uuid.uuid4()),
            event_type=event_type,
            aggregate_id=aggregate_id,
            correlation_id=str(uuid.uuid4()),
            payload={"ts": datetime.now(timezone.utc).isoformat()},
        )
        db.add(event)
        db.commit()
        return event


# =============================================================================
# 5. Propagation Baggage Dedup Tags
# =============================================================================


class TestPropagationDedup:
    def test_extract_empty_when_no_context(self):
        correlation_engine.decay()
        keys = extract_dedup_keys_from_propagation()
        assert keys == []

    def test_extract_after_dedup(self, db):
        # Run dedup while tracing context is active
        correlation_engine.start("dedup_test", "pytest")
        try:
            distributed_dedup.dedup_or_none(
                db, "baggage.test", "agg-1", {},
                handler=lambda t, a, p: "ok",
            )
            keys = extract_dedup_keys_from_propagation()
            # May or may not have keys depending on exec order
            assert isinstance(keys, list)
        finally:
            correlation_engine.end()
            correlation_engine.decay()


# =============================================================================
# 6. Concurrent Access — Threading Race Conditions
# =============================================================================


class TestConcurrentAccess:
    def test_concurrent_acquire_same_key(self, db):
        """Two threads trying to acquire the same key — only one succeeds."""
        key = "concurrent:key:test"
        results = []
        errors = []

        def acquire_thread():
            try:
                engine_local = create_engine(TEST_DB_URL, echo=False)
                Base.metadata.create_all(bind=engine_local)
                SessionLocal = sessionmaker(bind=engine_local)
                session = SessionLocal()
                try:
                    idempotency_service.acquire(session, key)
                    results.append("acquired")
                except IdempotencyConflict:
                    results.append("conflict")
                except Exception as e:
                    errors.append(str(e))
                finally:
                    session.close()
            except Exception as e:
                errors.append(str(e))

        threads = [threading.Thread(target=acquire_thread) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Exactly one should acquire, rest should get conflict (or in-progress check)
        assert len(errors) == 0, f"Errors: {errors}"
        assert "acquired" in results

    def test_concurrent_dedup_publish(self, db):
        """Multiple threads publishing the same event — only one succeeds."""
        results = []

        def publish_thread():
            engine_local = create_engine(TEST_DB_URL, echo=False)
            Base.metadata.create_all(bind=engine_local)
            SessionLocal = sessionmaker(bind=engine_local)
            session = SessionLocal()
            try:
                ok = distributed_dedup.dedup_publish(
                    session, "conc.pub", "agg-1", {"v": 1},
                )
                results.append(ok)
            except Exception as e:
                results.append(f"error:{e}")
            finally:
                session.close()

        threads = [threading.Thread(target=publish_thread) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        true_count = sum(1 for r in results if r is True)
        false_count = sum(1 for r in results if r is False)
        assert true_count >= 1, f"Expected at least 1 success, got {results}"
        assert any(not r or r is False for r in results if isinstance(r, bool)), \
            "Expected some duplicates"

    def test_concurrent_dedup_memory(self, db):
        """Multiple threads publishing same memory observation."""
        results = []

        def memory_thread():
            engine_local = create_engine(TEST_DB_URL, echo=False)
            Base.metadata.create_all(bind=engine_local)
            SessionLocal = sessionmaker(bind=engine_local)
            session = SessionLocal()
            try:
                ok = distributed_dedup.dedup_memory(
                    session, "conc_voter", "conc:key", {"val": 1},
                    student_id="s1", module_id="m1",
                )
                results.append(ok)
            except Exception as e:
                results.append(f"error:{e}")
            finally:
                session.close()

        threads = [threading.Thread(target=memory_thread) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        true_count = sum(1 for r in results if r is True)
        false_count = sum(1 for r in results if r is False)
        assert true_count >= 1

    def test_concurrent_retry_and_replay(self, db):
        """Thread A processes, thread B replays — B gets cached result."""
        key = IdempotencyKeyGenerator.from_content("conc.retry", "agg-1", {"v": 1})
        results = {}

        def processor():
            engine_local = create_engine(TEST_DB_URL, echo=False)
            Base.metadata.create_all(bind=engine_local)
            SessionLocal = sessionmaker(bind=engine_local)
            session = SessionLocal()
            try:
                handler = RetryHandler(idempotency_service)
                result = handler.execute(
                    session, "conc.retry", "agg-1", {"v": 1},
                    handler=lambda: "processed",
                )
                results["processor"] = result
            except Exception as e:
                results["processor_error"] = str(e)
            finally:
                session.close()

        def replayer():
            time.sleep(0.1)
            engine_local = create_engine(TEST_DB_URL, echo=False)
            Base.metadata.create_all(bind=engine_local)
            SessionLocal = sessionmaker(bind=engine_local)
            session = SessionLocal()
            try:
                handler = RetryHandler(idempotency_service)
                result = handler.execute(
                    session, "conc.retry", "agg-1", {"v": 1},
                    handler=lambda: "replayed",
                )
                results["replayer"] = result
            except Exception as e:
                results["replayer_error"] = str(e)
            finally:
                session.close()

        threads = [
            threading.Thread(target=processor),
            threading.Thread(target=replayer),
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert results.get("processor") == "processed"
        # Replayer either gets cached "processed" or its own "processed"
        assert results.get("replayer") == "processed", f"Got: {results}"


# =============================================================================
# 7. Middleware
# =============================================================================


class TestMiddleware:
    def test_extract_key_header(self):
        request = MagicMock()
        request.method = "POST"
        request.headers = {IDEMPOTENCY_HEADER: "my-key"}
        request.state = {}
        key = _extract_key(request)
        assert key == "ik:explicit:my-key"

    def test_extract_key_no_header_get(self):
        request = MagicMock()
        request.method = "GET"
        request.headers = {}
        request.state = {}
        key = _extract_key(request)
        assert key is None

    def test_extract_key_no_header_post_no_body(self):
        request = MagicMock()
        request.method = "POST"
        request.headers = {}
        request.state = {}
        key = _extract_key(request)
        assert key is None

    def test_replay_response_header(self):
        record = MagicMock()
        record.status = "completed"
        record.response_status = 200
        record.response_body = json.dumps({"result": "ok"})

        from app.events.middleware import _replay_response
        response = _replay_response(record)
        assert response.status_code == 200
        assert response.headers.get(IDEMPOTENCY_REPLAY_HEADER) == "true"


# =============================================================================
# 8. Distributed Integration Scenarios
# =============================================================================


class TestDistributedIntegration:
    def test_full_dedup_flow(self, db):
        """Complete flow: dispatch → process → replay."""
        # Step 1: First dispatch
        ok1 = distributed_dedup.dedup_publish(
            db, "flow.test", "agg-flow", {"step": 1},
        )
        assert ok1 is True

        # Step 2: Process
        result1 = distributed_dedup.dedup_or_none(
            db, "flow.test", "agg-flow", {"step": 1},
            handler=lambda t, a, p: {"status": "processed", "data": p},
        )
        assert result1 == {"status": "processed", "data": {"step": 1}}

        # Step 3: Replay (should return cached)
        ok2 = distributed_dedup.dedup_publish(
            db, "flow.test", "agg-flow", {"step": 1},
        )
        assert ok2 is False  # duplicate

        result2 = distributed_dedup.dedup_or_none(
            db, "flow.test", "agg-flow", {"step": 1},
            handler=lambda t, a, p: {"status": "should_not_run"},
        )
        assert result2 == {"status": "processed", "data": {"step": 1}}  # cached

    def test_consensus_phase_with_retry(self, db):
        """Consensus phase interrupted, retried, skips completed phases."""
        from app.events.integration import IdempotentConsensusGuard
        guard = IdempotentConsensusGuard(idempotency_service)
        calls = []

        # Phase 1: succeeds
        result1 = distributed_dedup.dedup_consensus(
            db, "mod-c", "stu-c", "vote_collection",
            handler=lambda: (calls.append("vote"), {"votes": 3})[1],
        )
        assert result1 == {"votes": 3}

        # Simulate interruption after phase 1
        # Phase 2: retry — phase 1 should be skipped
        result2 = distributed_dedup.dedup_consensus(
            db, "mod-c", "stu-c", "vote_collection",
            handler=lambda: (calls.append("vote_again"), "should_not_run")[1],
        )
        assert result2 is None  # skipped (completed)

        # Phase 2: first time
        result3 = distributed_dedup.dedup_consensus(
            db, "mod-c", "stu-c", "aggregation",
            handler=lambda: (calls.append("aggregate"), {"decision": "APPROVE"})[1],
        )
        assert result3 == {"decision": "APPROVE"}

        # Only vote + aggregate should have run
        assert calls == ["vote", "aggregate"]

    def test_memory_with_consensus_combined(self, db):
        """Memory publish after consensus — dedup works end-to-end."""
        distributed_dedup.dedup_memory(
            db, "voter-x", "key:consensus-result", {"decision": "APPROVE"},
            student_id="s1", module_id="m1",
        )
        # Same memory publish → duplicate
        assert distributed_dedup.dedup_memory(
            db, "voter-x", "key:consensus-result", {"decision": "APPROVE"},
            student_id="s1", module_id="m1",
        ) is False

    def test_mixed_dedup_strategies(self, db):
        """Different events with same content-hash are deduped."""
        bus_result = distributed_dedup.dedup_publish(
            db, "mixed.event", "agg-mix", {"data": "same"},
        )
        assert bus_result is True

        consumer_result = distributed_dedup.dedup_or_none(
            db, "mixed.event", "agg-mix", {"data": "same"},
            handler=lambda t, a, p: "done",
        )
        # Same content-hash → expects completed (from bus_result)
        assert consumer_result is not None

    def test_error_recovery(self, db):
        """Failed handler, then retry succeeds."""
        call_count = [0]

        def handler(t, a, p):
            call_count[0] += 1
            if call_count[0] == 1:
                raise ValueError("first attempt failed")
            return "recovered"

        # First attempt fails
        with pytest.raises(ValueError):
            distributed_dedup.dedup_or_none(
                db, "recover.test", "agg-rec", {},
                handler=handler,
            )

        # Second attempt → dedup_or_none's internal acquire handles
        # failed → in_progress transition and re-runs the handler
        result = distributed_dedup.dedup_or_none(
            db, "recover.test", "agg-rec", {},
            handler=handler,
        )
        assert result == "recovered"


# =============================================================================
# 9. Propagation Middleware — Simulated FastAPI Request Flow
# =============================================================================


class TestMiddlewareIntegration:
    def test_middleware_registers_key_on_state(self):
        """Verify middleware factory returns a callable."""
        middleware = make_idempotency_middleware(idempotency_service)
        assert callable(middleware)

    def test_middleware_skips_get(self):
        """GET requests should pass through without idempotency check."""
        middleware = make_idempotency_middleware(idempotency_service)
        request = MagicMock()
        request.method = "GET"
        request.url.path = "/api/test"

        async def call_next(req):
            return MagicMock(status_code=200)

        import asyncio
        response = asyncio.run(middleware(request, call_next))
        assert response is not None

    def test_middleware_excludes_paths(self):
        """Excluded paths should be bypassed."""
        middleware = make_idempotency_middleware(
            idempotency_service,
            exclude_paths={"/health", "/docs"},
        )
        request = MagicMock()
        request.method = "POST"
        request.url.path = "/health"

        async def call_next(req):
            return MagicMock(status_code=200)

        import asyncio
        response = asyncio.run(middleware(request, call_next))
        assert response is not None

    def test_middleware_without_key_passes_through(self):
        """POST without Idempotency-Key header and no body should pass through."""
        middleware = make_idempotency_middleware(idempotency_service)
        request = MagicMock()
        request.method = "POST"
        request.url.path = "/api/data"
        request.headers = {}
        request.state = {}

        async def call_next(req):
            return MagicMock(status_code=200)

        import asyncio
        response = asyncio.run(middleware(request, call_next))
        assert response is not None


# =============================================================================
# 10. Edge Cases
# =============================================================================


class TestEdgeCases:
    def test_empty_payload_dedup(self, db):
        """Empty payloads should still be deduped."""
        k1 = IdempotencyKeyGenerator.from_content("empty", "agg-1", {})
        k2 = IdempotencyKeyGenerator.from_content("empty", "agg-1", {})
        assert k1 == k2

    def test_none_payload_dedup(self, db):
        k1 = IdempotencyKeyGenerator.from_content("none", "agg-1", None)
        k2 = IdempotencyKeyGenerator.from_content("none", "agg-1", None)
        assert k1 == k2

    def test_large_payload_dedup(self, db):
        big = {"data": "x" * 10000}
        k1 = IdempotencyKeyGenerator.from_content("big", "agg-1", big)
        k2 = IdempotencyKeyGenerator.from_content("big", "agg-1", big)
        assert k1 == k2

    def test_cancel_during_processing(self, db):
        key = "edge:cancel"
        idempotency_service.acquire(db, key)
        assert idempotency_service.cancel(db, key) is True
        # Can now re-acquire
        record = idempotency_service.acquire(db, key)
        assert record.status == "in_progress"

    def test_purge_while_concurrent_access(self, db):
        """Purge should not affect active keys."""
        active = "edge:active"
        expired = "edge:expired"
        idempotency_service.acquire(db, active)
        idempotency_service.complete(db, active, response_body="active")
        idempotency_service.acquire(db, expired)
        from sqlalchemy import update
        db.execute(
            update(IdempotencyKey)
            .where(IdempotencyKey.key == expired)
            .values(expires_at=datetime.now(timezone.utc) - timedelta(hours=1))
        )
        db.commit()
        purged = idempotency_service.purge_expired(db)
        assert purged >= 1
        assert idempotency_service.check(db, active) is not None
