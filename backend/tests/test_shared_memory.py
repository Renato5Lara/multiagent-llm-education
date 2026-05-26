"""
Tests for Shared Collective Memory — SharedMemoryStore, memory_rules.

Covers:
    - publish_observation (scoped, with trace, with TTL)
    - query (by student, module, type, key, voter, stale filtering)
    - query_by_key_pattern
    - get_lineage (parent chain)
    - resolve_conflicts
    - remove_stale
    - aggregate_confidence
    - count
    - Memory rules: compute_memory_confidence, resolve_conflict,
      is_stale, compute_ttl, merge_observations, compute_source_reliability
    - Concurrency: thread safety
"""

import json
import threading
import time
from datetime import datetime, timedelta, timezone

import pytest

from app.events.distributed import distributed_dedup
from app.memory.memory_rules import (
    compute_memory_confidence,
    resolve_conflict,
    is_stale,
    compute_ttl,
    merge_observations,
    compute_source_reliability,
    DEFAULT_TTL_SECONDS,
    MEMORY_TYPE_TTL,
)
from app.memory.shared_memory import SharedMemoryStore
from app.models.shared_memory_record import SharedMemoryRecord
from app.observability.tracing import TraceContext


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mem_store(test_uow):
    return SharedMemoryStore(test_uow)


def _make_record(**kw):
    """Helper to create a SharedMemoryRecord in memory (not DB)."""
    defaults = dict(
        voter_name="test",
        memory_type="observation",
        key="test:key",
        value={"data": 1},
        confidence=1.0,
        created_at=datetime.now(timezone.utc),
    )
    defaults.update(kw)
    return SharedMemoryRecord(**defaults)


# =============================================================================
# 1. Memory Rules — compute_memory_confidence
# =============================================================================


class TestComputeMemoryConfidence:
    def test_empty_records(self):
        assert compute_memory_confidence([]) == 0.0

    def test_single_record(self):
        r = _make_record(confidence=0.8)
        assert compute_memory_confidence([r]) == 0.8

    def test_weighted_by_recency(self):
        now = datetime.now(timezone.utc)
        old = _make_record(confidence=0.5, created_at=now - timedelta(hours=10))
        new = _make_record(confidence=1.0, created_at=now - timedelta(hours=1))
        conf = compute_memory_confidence([old, new])
        # Newer has higher weight
        assert 0.5 < conf < 1.0
        assert conf > 0.75  # closer to new


class TestResolveConflict:
    def test_empty(self):
        assert resolve_conflict([]) == {}

    def test_single(self):
        r = _make_record(value={"winner": True})
        assert resolve_conflict([r]) == {"winner": True}

    def test_majority_wins(self):
        r1 = _make_record(value={"color": "red"}, confidence=0.9)
        r2 = _make_record(value={"color": "red"}, confidence=0.8)
        r3 = _make_record(value={"color": "blue"}, confidence=0.9)
        result = resolve_conflict([r1, r2, r3])
        assert result == {"color": "red"}

    def test_confidence_tiebreak(self):
        r1 = _make_record(value={"color": "red"}, confidence=0.5)
        r2 = _make_record(value={"color": "blue"}, confidence=0.9)
        result = resolve_conflict([r1, r2])
        assert result == {"color": "blue"}  # higher confidence


class TestIsStale:
    def test_no_ttl(self):
        r = _make_record(ttl_seconds=None)
        assert is_stale(r) is False

    def test_not_stale(self):
        r = _make_record(ttl_seconds=100, created_at=datetime.now(timezone.utc) - timedelta(seconds=10))
        assert is_stale(r) is False

    def test_stale(self):
        r = _make_record(ttl_seconds=1, created_at=datetime.now(timezone.utc) - timedelta(seconds=5))
        assert is_stale(r) is True


class TestComputeTTL:
    def test_default_for_unknown(self):
        assert compute_ttl("unknown") == DEFAULT_TTL_SECONDS

    def test_observation_ttl(self):
        ttl = compute_ttl("observation")
        assert ttl == MEMORY_TYPE_TTL["observation"]

    def test_confidence_scales_up(self):
        low = compute_ttl("observation", confidence=0.3)
        high = compute_ttl("observation", confidence=1.0)
        assert high > low

    def test_minimum_ttl(self):
        assert compute_ttl("signal", confidence=0.0) >= 60


class TestMergeObservations:
    def test_new_keys_added(self):
        result = merge_observations({"a": 1}, {"b": 2})
        assert result == {"a": 1, "b": 2}

    def test_existing_overwritten(self):
        result = merge_observations({"a": 1}, {"a": 2})
        assert result["a"] == 2

    def test_nested_merge(self):
        result = merge_observations(
            {"nested": {"x": 1}},
            {"nested": {"y": 2}},
        )
        assert result["nested"] == {"x": 1, "y": 2}


class TestComputeSourceReliability:
    def test_empty(self):
        assert compute_source_reliability([]) == {}

    def test_single_voter(self):
        r = _make_record(voter_name="v1")
        rel = compute_source_reliability([r])
        assert rel["v1"] == 1.0

    def test_with_trust(self):
        r1 = _make_record(voter_name="v1")
        r2 = _make_record(voter_name="v2")
        r3 = _make_record(voter_name="v2")
        rel = compute_source_reliability([r1, r2, r3], trust_scores={"v1": 0.5, "v2": 1.0})
        # v2 has more records AND higher trust
        assert rel["v2"] > rel["v1"]


# =============================================================================
# 2. SharedMemoryStore — publish
# =============================================================================


class TestPublishObservation:
    def test_publish_returns_id(self, mem_store):
        rid = mem_store.publish_observation(
            voter_name="mastery",
            key="test:publish",
            value={"msg": "hello"},
            student_id="stu-1",
        )
        assert rid is not None
        assert len(rid) == 36  # UUID

    def test_published_record_stored(self, mem_store):
        rid = mem_store.publish_observation(
            voter_name="sequence",
            key="test:stored",
            value={"result": "ok"},
            confidence=0.85,
            student_id="stu-1",
            module_id="mod-1",
            memory_type="observation",
        )
        record = mem_store.get_by_id(rid)
        assert record is not None
        assert record.voter_name == "sequence"
        assert record.key == "test:stored"
        assert record.value == {"result": "ok"}
        assert record.confidence == 0.85
        assert record.student_id == "stu-1"
        assert record.module_id == "mod-1"
        assert record.memory_type == "observation"

    def test_publish_with_trace(self, mem_store):
        trace = TraceContext.new(correlation_id="corr-1", emitted_by="test")
        rid = mem_store.publish_observation(
            voter_name="mastery",
            key="test:trace",
            value={"data": 1},
            student_id="stu-1",
            trace_ctx=trace,
        )
        record = mem_store.get_by_id(rid)
        assert record.source_trace_id == trace.trace_id

    def test_publish_with_ttl(self, mem_store):
        rid = mem_store.publish_observation(
            voter_name="mastery",
            key="test:ttl",
            value={"data": 1},
            student_id="stu-1",
            ttl_seconds=60,
        )
        record = mem_store.get_by_id(rid)
        assert record.ttl_seconds == 60

    def test_publish_auto_ttl(self, mem_store):
        rid = mem_store.publish_observation(
            voter_name="mastery",
            key="test:auto_ttl",
            value={"data": 1},
            student_id="stu-1",
            confidence=0.8,
            memory_type="observation",
        )
        record = mem_store.get_by_id(rid)
        assert record.ttl_seconds is not None
        expected = int(MEMORY_TYPE_TTL["observation"] * (0.5 + 0.8))
        assert record.ttl_seconds == expected

    def test_publish_with_parent(self, mem_store):
        parent_id = mem_store.publish_observation(
            voter_name="mastery", key="test:parent", value={"v": 1},
            student_id="stu-1",
        )
        child_id = mem_store.publish_observation(
            voter_name="sequence", key="test:child", value={"v": 2},
            student_id="stu-1", parent_id=parent_id,
        )
        child = mem_store.get_by_id(child_id)
        assert child.parent_id == parent_id


# =============================================================================
# 3. SharedMemoryStore — query
# =============================================================================


class TestQuery:
    def test_query_by_student(self, mem_store):
        mem_store.publish_observation(voter_name="v1", key="k1", value={}, student_id="stu-1")
        mem_store.publish_observation(voter_name="v1", key="k2", value={}, student_id="stu-2")
        results = mem_store.query(student_id="stu-1")
        assert len(results) == 1
        assert results[0].key == "k1"

    def test_query_by_module(self, mem_store):
        mem_store.publish_observation(voter_name="v1", key="k1", value={}, module_id="mod-1")
        mem_store.publish_observation(voter_name="v1", key="k2", value={}, module_id="mod-2")
        results = mem_store.query(module_id="mod-1")
        assert len(results) == 1

    def test_query_by_type(self, mem_store):
        mem_store.publish_observation(voter_name="v1", key="k1", value={},
                                       memory_type="observation")
        mem_store.publish_observation(voter_name="v1", key="k2", value={},
                                       memory_type="inference")
        results = mem_store.query(memory_type="inference")
        assert len(results) == 1

    def test_query_by_key(self, mem_store):
        mem_store.publish_observation(voter_name="v1", key="exact_match", value={})
        mem_store.publish_observation(voter_name="v1", key="other", value={})
        results = mem_store.query(key="exact_match")
        assert len(results) == 1

    def test_query_by_voter(self, mem_store):
        mem_store.publish_observation(voter_name="voter_a", key="k1", value={})
        mem_store.publish_observation(voter_name="voter_b", key="k2", value={})
        results = mem_store.query(voter_name="voter_a")
        assert len(results) == 1

    def test_query_excludes_stale(self, mem_store):
        mem_store.publish_observation(voter_name="v1", key="fresh", value={},
                                       ttl_seconds=1000)
        mem_store.publish_observation(voter_name="v1", key="stale", value={},
                                       ttl_seconds=0)  # will be stale immediately
        import time
        time.sleep(0.01)
        results = mem_store.query(include_stale=False)
        assert any(r.key == "fresh" for r in results)
        assert not any(r.key == "stale" for r in results)

    def test_query_includes_stale(self, mem_store):
        mem_store.publish_observation(voter_name="v1", key="stale", value={},
                                       ttl_seconds=0)
        time.sleep(0.01)
        results = mem_store.query(include_stale=True)
        assert any(r.key == "stale" for r in results)

    def test_query_limit(self, mem_store):
        for i in range(5):
            mem_store.publish_observation(voter_name="v1", key=f"k{i}", value={})
        assert len(mem_store.query(limit=3)) == 3

    def test_query_order(self, mem_store):
        ids = []
        for i in range(3):
            rid = mem_store.publish_observation(voter_name="v1", key=f"k{i}", value={})
            ids.append(rid)
        results = mem_store.query(order_desc=True)
        # Newest first
        assert results[0].id == ids[-1]


class TestQueryByKeyPattern:
    def test_prefix_match(self, mem_store):
        mem_store.publish_observation(voter_name="v1", key="performance:math", value={})
        mem_store.publish_observation(voter_name="v1", key="performance:science", value={})
        mem_store.publish_observation(voter_name="v1", key="vote:math", value={})
        results = mem_store.query_by_key_pattern("performance:")
        assert len(results) == 2

    def test_with_student_filter(self, mem_store):
        mem_store.publish_observation(voter_name="v1", key="perf:a", value={}, student_id="stu-1")
        mem_store.publish_observation(voter_name="v1", key="perf:b", value={}, student_id="stu-2")
        results = mem_store.query_by_key_pattern("perf:", student_id="stu-1")
        assert len(results) == 1


# =============================================================================
# 4. SharedMemoryStore — lineage
# =============================================================================


class TestLineage:
    def test_single_record(self, mem_store):
        rid = mem_store.publish_observation(voter_name="v1", key="k1", value={})
        lineage = mem_store.get_lineage(rid)
        assert len(lineage) == 1
        assert lineage[0].id == rid

    def test_parent_chain(self, mem_store):
        r1 = mem_store.publish_observation(voter_name="v1", key="k1", value={})
        r2 = mem_store.publish_observation(voter_name="v2", key="k2", value={}, parent_id=r1)
        r3 = mem_store.publish_observation(voter_name="v3", key="k3", value={}, parent_id=r2)
        lineage = mem_store.get_lineage(r3)
        assert len(lineage) == 3
        assert lineage[0].id == r1  # oldest first
        assert lineage[-1].id == r3

    def test_nonexistent_record(self, mem_store):
        assert mem_store.get_lineage("nonexistent") == []


# =============================================================================
# 5. SharedMemoryStore — conflict resolution
# =============================================================================


class TestStoreResolveConflicts:
    def test_no_conflict(self, mem_store):
        result = mem_store.resolve_conflicts("nonexistent")
        assert result == {}

    def test_single_value(self, mem_store):
        mem_store.publish_observation(voter_name="v1", key="conflict:test",
                                       value={"color": "red"}, confidence=0.9)
        result = mem_store.resolve_conflicts("conflict:test")
        assert result == {"color": "red"}

    def test_majority_wins(self, mem_store):
        mem_store.publish_observation(voter_name="v1", key="conflict:color",
                                       value={"color": "red"}, confidence=0.9)
        mem_store.publish_observation(voter_name="v2", key="conflict:color",
                                       value={"color": "red"}, confidence=0.8)
        mem_store.publish_observation(voter_name="v3", key="conflict:color",
                                       value={"color": "blue"}, confidence=0.9)
        result = mem_store.resolve_conflicts("conflict:color")
        assert result == {"color": "red"}


# =============================================================================
# 6. SharedMemoryStore — stale removal
# =============================================================================


class TestRemoveStale:
    def test_removes_expired(self, mem_store):
        mem_store.publish_observation(voter_name="v1", key="fresh", value={},
                                       ttl_seconds=1000)
        mem_store.publish_observation(voter_name="v1", key="expired", value={},
                                       ttl_seconds=0)
        time.sleep(0.01)
        count = mem_store.remove_stale()
        assert count >= 1
        remaining = mem_store.query(include_stale=True)
        assert all(r.key != "expired" for r in remaining)

    def test_no_stale(self, mem_store):
        mem_store.publish_observation(voter_name="v1", key="k1", value={},
                                       ttl_seconds=1000)
        count = mem_store.remove_stale()
        assert count == 0


# =============================================================================
# 7. SharedMemoryStore — aggregation
# =============================================================================


class TestAggregateConfidence:
    def test_no_records(self, mem_store):
        assert mem_store.aggregate_confidence("nonexistent") == 0.0

    def test_multiple_records(self, mem_store):
        mem_store.publish_observation(voter_name="v1", key="agg:test",
                                       value={}, confidence=0.5)
        mem_store.publish_observation(voter_name="v2", key="agg:test",
                                       value={}, confidence=1.0)
        conf = mem_store.aggregate_confidence("agg:test")
        assert 0.5 < conf < 1.0


# =============================================================================
# 8. SharedMemoryStore — count
# =============================================================================


class TestCount:
    def test_empty(self, mem_store):
        assert mem_store.count() == 0

    def test_count_by_type(self, mem_store):
        mem_store.publish_observation(voter_name="v1", key="k1", value={},
                                       memory_type="observation")
        mem_store.publish_observation(voter_name="v1", key="k2", value={},
                                       memory_type="inference")
        assert mem_store.count(memory_type="observation") == 1
        assert mem_store.count() == 2

    def test_count_by_student(self, mem_store):
        mem_store.publish_observation(voter_name="v1", key="k1", value={}, student_id="stu-1")
        mem_store.publish_observation(voter_name="v1", key="k2", value={}, student_id="stu-2")
        assert mem_store.count(student_id="stu-1") == 1


# =============================================================================
# 9. SharedMemoryStore — concurrency
# =============================================================================


class TestConcurrency:
    def test_thread_safe_publish(self, tmp_path):
        """Each thread uses its own Session + WAL-enabled file-based SQLite.
        A file DB is required instead of :memory: because StaticPool shares a
        single connection across all sessions, making concurrent writes fail."""
        from app.db.uow import UnitOfWork
        from sqlalchemy import create_engine, event
        from sqlalchemy.orm import sessionmaker

        db_path = tmp_path / "test_concurrent_memory.db"
        wal_engine = create_engine(
            f"sqlite:///{db_path}",
            connect_args={"check_same_thread": False},
        )
        @event.listens_for(wal_engine, "connect")
        def _wal_pragma(dbapi_conn, _conn_record):
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()
        from app.db.base import Base
        Base.metadata.create_all(bind=wal_engine)
        try:
            SessionLocal = sessionmaker(bind=wal_engine)

            errors = []
            n_threads = 4
            pubs_per_thread = 10

            def worker():
                session = SessionLocal()
                try:
                    uow = UnitOfWork(lambda: session)
                    store = SharedMemoryStore(uow)
                    for i in range(pubs_per_thread):
                        store.publish_observation(
                            voter_name=f"thread_{threading.get_ident()}",
                            key=f"concurrent:{i}",
                            value={"i": i},
                        )
                    uow.commit()
                except Exception as e:
                    errors.append(e)
                finally:
                    session.close()

            threads = [threading.Thread(target=worker) for _ in range(n_threads)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()

            assert len(errors) == 0, f"Concurrency errors: {errors}"
            total = SessionLocal().query(SharedMemoryRecord).count()
            assert total == n_threads * pubs_per_thread
        finally:
            Base.metadata.drop_all(bind=wal_engine)
            wal_engine.dispose()


# =============================================================================
# 10. SharedMemoryRecord model properties
# =============================================================================


class TestModelProperties:
    def test_is_stale_no_ttl(self):
        r = SharedMemoryRecord(voter_name="v1", memory_type="observation", key="k",
                                value={})
        assert r.is_stale is False

    def test_is_stale_expired(self):
        r = SharedMemoryRecord(voter_name="v1", memory_type="observation", key="k",
                                value={}, ttl_seconds=1,
                                created_at=datetime.now(timezone.utc) - timedelta(seconds=10))
        assert r.is_stale is True

    def test_age_seconds(self):
        r = SharedMemoryRecord(voter_name="v1", memory_type="observation", key="k",
                                value={})
        assert r.age_seconds >= 0

    def test_repr(self):
        r = SharedMemoryRecord(voter_name="mastery", memory_type="observation",
                                key="test:repr", value={}, confidence=0.85)
        rep = repr(r)
        assert "mastery" in rep
        assert "observation" in rep
        assert "test:repr" in rep


# =============================================================================
# 11. SharedMemoryStore + DistributedDedupEngine Integration
# =============================================================================


class TestSharedMemoryStoreDedup:
    """Wiring: DistributedDedupEngine integrated into
    SharedMemoryStore.publish_observation()."""

    def test_creates_record(self, test_uow):
        store = SharedMemoryStore(test_uow, dedup_engine=distributed_dedup)
        rid = store.publish_observation(
            voter_name="voter1", key="dedup:test:1",
            value={"result": "ok"}, confidence=0.9,
            student_id="stu-1", module_id="mod-1",
        )
        assert rid is not None and isinstance(rid, str)

    def test_returns_same_id_on_duplicate(self, test_uow):
        store = SharedMemoryStore(test_uow, dedup_engine=distributed_dedup)
        rid1 = store.publish_observation(
            voter_name="voter1", key="dedup:test:2",
            value={"result": "same"}, confidence=0.9,
            student_id="stu-1", module_id="mod-1",
        )
        rid2 = store.publish_observation(
            voter_name="voter1", key="dedup:test:2",
            value={"result": "same"}, confidence=0.9,
            student_id="stu-1", module_id="mod-1",
        )
        assert rid1 == rid2

    def test_different_values_different_ids(self, test_uow):
        store = SharedMemoryStore(test_uow, dedup_engine=distributed_dedup)
        rid1 = store.publish_observation(
            voter_name="voter1", key="dedup:test:3a",
            value={"result": "first"}, confidence=0.9,
            student_id="stu-1", module_id="mod-1",
        )
        rid2 = store.publish_observation(
            voter_name="voter1", key="dedup:test:3b",
            value={"result": "second"}, confidence=0.9,
            student_id="stu-1", module_id="mod-1",
        )
        assert rid1 != rid2

    def test_differs_by_voter(self, test_uow):
        store = SharedMemoryStore(test_uow, dedup_engine=distributed_dedup)
        rid1 = store.publish_observation(
            voter_name="voter_a", key="dedup:test:4",
            value={"result": "ok"}, confidence=0.9,
            student_id="stu-1", module_id="mod-1",
        )
        rid2 = store.publish_observation(
            voter_name="voter_b", key="dedup:test:4",
            value={"result": "ok"}, confidence=0.9,
            student_id="stu-1", module_id="mod-1",
        )
        assert rid1 != rid2

    def test_stores_record_id_in_idempotency_key(self, test_uow):
        from app.events.integration import _memory_key
        store = SharedMemoryStore(test_uow, dedup_engine=distributed_dedup)
        rid = store.publish_observation(
            voter_name="voter1", key="dedup:test:5",
            value={"result": "check"}, confidence=0.9,
            student_id="stu-1", module_id="mod-1",
        )
        content_key = _memory_key(
            "voter1", "dedup:test:5", {"result": "check"}, 0.9,
            "stu-1", "mod-1", "observation",
        )
        record = distributed_dedup._idem.check(test_uow.db, content_key)
        assert record is not None
        assert record.status == "completed"
        body = json.loads(record.response_body)
        assert body["record_id"] == rid

    def test_without_dedup_engine_still_prevents_duplicates(self, test_uow):
        """Without dedup engine, the unique constraint still prevents
        duplicate records with the same (voter, key, student, module, type)."""
        store = SharedMemoryStore(test_uow)
        store.publish_observation(
            voter_name="voter1", key="dedup:test:6",
            value={"result": "dup"}, confidence=0.9,
            student_id="stu-1", module_id="mod-1",
        )
        with pytest.raises(Exception):
            store.publish_observation(
                voter_name="voter1", key="dedup:test:6",
                value={"result": "dup"}, confidence=0.9,
                student_id="stu-1", module_id="mod-1",
            )
