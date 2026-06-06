# Auditoría Forense Completa del Swarm Runtime Educativo

**Date:** 2026-05-27  
**Scope:** Activation lifecycle, propagation, shared memory, consensus, collective inference, adaptive generation, session orchestration, event propagation, distributed coordination  
**Files Audited:** 28 files across `app/swarm/`, `app/memory/`, `app/core/`, `app/events/`, `app/services/`, `app/db/`, `app/agents/`, `app/tracing/`

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Bug Catalog](#2-bug-catalog)
3. [Activation Lifecycle Analysis](#3-activation-lifecycle-analysis)
4. [Propagation Diagnostics](#4-propagation-diagnostics)
5. [Shared Memory Analysis](#5-shared-memory-analysis)
6. [Consensus Analysis](#6-consensus-analysis)
7. [Collective Inference Analysis](#7-collective-inference-analysis)
8. [Event Propagation Analysis](#8-event-propagation-analysis)
9. [Distributed Coordination Analysis](#9-distributed-coordination-analysis)
10. [Bottlenecks & Race Conditions](#10-bottlenecks--race-conditions)
11. [Observability Recommendations](#11-observability-recommendations)
12. [Runtime Stabilization Recommendations](#12-runtime-stabilization-recommendations)

---

## 1. Architecture Overview

The swarm runtime implements a **9-phase sequential activation lifecycle** for each student-course context:

```
ENTERING → CONTEXT_LOADING → MEMORY_INIT → PEDAGOGICAL_ANALYSIS →
ADAPTIVE_ADJUSTMENT → RISK_ASSESSMENT → CONSENSUS → INFERENCE →
CONTENT_PRODUCTION → ACTIVE
```

### Key Components

| Component | File | Role |
|-----------|------|------|
| `SwarmOrchestrator` | `swarm/orchestrator.py` | Coordinates 9-phase lifecycle execution |
| `SwarmLifecycle` | `swarm/lifecycle.py` | Phase state machine with timeout/retry/rollback |
| `SwarmEventBus` | `swarm/events.py` | In-process event propagation with causation chains |
| `SharedMemoryStore` | `memory/shared_memory.py` | Deterministic collective memory backing |
| `ConsensusEngine` | `core/consensus.py` | Multi-voter consensus for progression decisions |
| `CollectiveInferenceEngine` | `memory/collective_inference.py` | Deterministic inference from memory + patterns |
| `SwarmEventBus` | `swarm/events.py` | In-process event bus with causation tracking |
| `PropagationTTLManager` | `events/propagation_ttl.py` | TTL/depth/decay controls for propagation |
| `ContextLock` | `swarm/synchronization.py` | Per-context mutex preventing concurrent activation |
| `UnitOfWork` | `db/uow.py` | Transactional boundary with savepoint support |
| `DistributedDedupEngine` | `events/distributed.py` | Cross-process dedup via content-hash + advisory locks |
| `BugDiagnosticsBridge` | `bug_reports/diagnostics_integration.py` | Anomaly → bug report auto-creation |

### Data Flow

```
HTTP Request
  → activation_service.activate_enrollment_with_swarm()
    → SwarmOrchestrator.activate()
      → ContextLock.acquire()
        → _run_lifecycle() [sequential phases]
          → _execute_phase(phase, handler)
            → PhaseGate (DEAD CODE — never .wait())
            → SwarmLifecycle.start_phase()
            → handler() [real agent + DB ops]
            → SwarmLifecycle.complete_phase()
            → SwarmEventBus.publish() [causation chain]
            → SharedMemoryStore.publish_observation()
            → bottleneck_detector.record_duration()
            → swarm_metrics.record_phase()
        → _collect_anomalies()
      → db.commit()
```

---

## 2. Bug Catalog

### BUG-SWARM-001 (CRITICAL) — `MagicMock` Objects Used in Production Consensus

**File:** `swarm/orchestrator.py:642-649`

```python
from unittest.mock import MagicMock
mock_module = MagicMock()
mock_module.id = self.course_id
mock_module.order = 1
mock_module.status = "in_progress"

mock_path = MagicMock()
mock_path.id = self.course_id
```

**Root Cause:** Real `unittest.mock.MagicMock` instances are created in production code and passed to `ConsensusEngine.run()` via `VoteContext`. These mocks are NOT real `PathModule`/`LearningPath` ORM instances. Any attribute or method accessed on them returns a new `MagicMock` instance silently.

**Impact:**
- `VoteContext.module.order` returns `1` (set explicitly) but `VoteContext.module.title`, `VoteContext.module.description`, etc. return new `MagicMock()` objects
- `VoteContext.path` — all attributes except `.id` return mocks
- `PrereqVoter.vote()` queries `PathModule` via `ctx.uow.db` (correct) but also uses `ctx.module.order` (might be correct since set explicitly)
- `SequenceVoter` and `TimeVoter` likely operate on mock data
- `CodeMasteryVoter` and `ProgressionVoter` from `programming_voters.py` receive mock `module` and `path` — their behavior is undefined

**Fix:** Replace with real DB queries or use proper factory functions:

```python
module = db.query(PathModule).filter(
    PathModule.path_id == path_id,
    PathModule.order == current_order
).first()
path = db.query(LearningPath).filter(
    LearningPath.student_id == self.student_id,
    LearningPath.course_id == self.course_id
).first()
```

---

### BUG-SWARM-002 (CRITICAL) — Nested Transaction Violation in Session Start

**Files:** `services/session_service.py:55-83`, `services/activation_service.py:160-172`

**Root Cause:** `session_service.start_module_session()`:
1. Creates `LearningSession` and calls `db.flush()` (line 55)
2. Calls `activate_enrollment_with_swarm()` (line 70) which creates its own `UnitOfWork(db)` and later calls `db.commit()` (line 165) or `db.rollback()` (line 168)
3. After swarm activation, calls `db.commit()` again (line 83)

If swarm activation fails, `activation_service.py:168` calls `db.rollback()`, which rolls back the `LearningSession` creation too. But `session_service.py` continues as if the session was created, returning `swarm_activated="failed"`.

**Impact:**
- On swarm failure: session is rolled back but function still returns `ok: True`
- If `db.commit()` at line 83 succeeds but the outbox events from `activate_enrollment_with_swarm` were already rolled back, the system has inconsistent state
- Double `db.commit()` on the same session — SQLAlchemy auto-starts a new implicit transaction after the first commit, but the second commit captures any subsequent changes

**Reproduction:**
1. Call `start_module_session()` 
2. Swarm activation throws exception
3. `db.rollback()` in activation_service rolls back both swarm work AND the LearningSession
4. `session_service.py` still returns `ok: True, session_id: <rolled-back-id>`

---

### BUG-SWARM-003 (CRITICAL) — Error Masking in Swarm Context Initialization

**File:** `services/swarm_activation_service.py:71-75`

```python
except Exception as e:
    ctx.status = EducationalContextStatus.ACTIVE
    ctx.activation_attempts = (ctx.activation_attempts or 0) + 1
    ctx.last_error = str(e)[:500]
    db.flush()
```

**Root Cause:** On ANY exception during initialization, the context status is set to `ACTIVE`. This masks the failure. Subsequent checks for `context.status == EducationalContextStatus.ACTIVE` will return `True`, causing the system to believe the swarm was properly initialized.

**Impact:** The system thinks the swarm context is initialized when it actually failed. All downstream operations (session start, adaptive generation, etc.) will assume the swarm is ready.

---

### BUG-SWARM-004 (HIGH) — PhaseGate Is Dead Code

**File:** `swarm/orchestrator.py:312-318`, `swarm/synchronization.py:21-87`

**Root Cause:** In `_execute_phase()`, a `PhaseGate` is constructed with preconditions and timeout but `.wait()` is NEVER called. The gate is instantiated and stored in `self._gates` but never used to actually block execution. The real precondition check happens in `SwarmLifecycle.can_transition_to()` which uses string-based `achieved_postconditions`.

```python
gate = PhaseGate(
    f"gate:{phase.value}",
    config["preconditions"],
    timeout_ms=timeout_ms,
)
self._gates[phase.value] = gate
# NEVER: gate.wait()
```

**Impact:** PhaseGate is 87 lines of dead code. The safety mechanism for phase synchronization is not actually enforced. If `can_transition_to()` has a bug, phases can execute out of order without detection.

---

### BUG-SWARM-005 (HIGH) — SwarmFence Is Completely Dead Code

**File:** `swarm/orchestrator.py:137`, `swarm/synchronization.py:90-155`

**Root Cause:** `self._fences` is initialized in `__init__` but never populated or used anywhere in the orchestrator. The `SwarmFence` class (65 lines) is never instantiated in the activation flow.

---

### BUG-SWARM-006 (HIGH) — `_last_event_id()` Returns Incorrect Causation Parent

**File:** `swarm/orchestrator.py:905-907`, `swarm/orchestrator.py:322-330`

```python
def _last_event_id(self) -> str | None:
    events = swarm_event_bus.get_events(context_key=self.context_key, limit=1)
    return events[0].event_id if events else None
```

**Root Cause:** `_last_event_id()` gets the LAST event published for the current context. But when ACTIVE phase publishes `ACTIVATION_COMPLETED`, `_execute_phase()` calls `_last_event_id()` BEFORE the current event is published. The causation_id from the event bus includes events from ALL phases, not just the causally relevant parent.

In `_execute_phase()`:
```python
causation_id = self._last_event_id()  # ← Gets PREVIOUS phase's "completed" event
# ... then publishes the STARTED event
```

**Impact:** Causation chains are miswired. Each phase's STARTED event references the previous phase's COMPLETED event, which is the reverse of the expected causal direction (STARTED should reference its CAUSE, not the previous completed phase).

**Fix:**
```python
# Publish started event first, then get its ID for causation
started_event = swarm_event_bus.publish(started_ev, ...)
causation_id = started_event.event_id
# Use causation_id in completed/failed events
```

---

### BUG-SWARM-007 (HIGH) — `ACTIVATION_COMPLETED` Published Twice

**File:** `swarm/events.py:126-131`

```python
SwarmPhase.ACTIVE: (
    SwarmEventType.ACTIVATION_COMPLETED,   # started event
    SwarmEventType.ACTIVATION_COMPLETED,   # completed event
    SwarmEventType.ACTIVATION_FAILED,      # failed event
),
```

**Root Cause:** The `PHASE_EVENT_MAP` for `ACTIVE` phase has `ACTIVATION_COMPLETED` for BOTH the started and completed event types. When `_execute_phase()` processes the ACTIVE phase, it publishes `ACTIVATION_COMPLETED` twice: once at start and once at completion.

**Impact:** Event consumers see two `ACTIVATION_COMPLETED` events. If they trigger side effects (e.g., notification, webhook), the side effect fires twice.

---

### BUG-SWARM-008 (MEDIUM) — `remove_stale()` Not Scheduled

**File:** `memory/shared_memory.py:515-541`

**Root Cause:** `SharedMemoryStore.remove_stale()` exists but is never called by any scheduler, cron, or lifecycle hook. TTL-based memory cleanup never actually triggers. Records with expired TTLs accumulate indefinitely.

**Impact:** SharedMemory table grows unbounded. Queries filter stale records out, but the underlying table still contains them. `count()` explicitly DOES NOT filter stale (documented at line 579), returning inflated counts.

---

### BUG-SWARM-009 (MEDIUM) — Dedup Engine Not Passing to SharedMemoryStore

**File:** `swarm/orchestrator.py:130`

```python
self.shared_memory = SharedMemoryStore(self.uow)
```

**Root Cause:** `SharedMemoryStore.__init__` accepts an optional `dedup_engine` parameter (line 57), but `SwarmOrchestrator` never passes one. All memory publications during swarm activation bypass dedup.

**Impact:** Identical observations can be published multiple times during the same activation (e.g., if a phase executes multiple times due to retry). No content-hash dedup protection during swarm lifecycle.

---

### BUG-SWARM-010 (MEDIUM) — Redundant Correlation Engine Spans in SharedMemoryStore

**File:** `memory/shared_memory.py:147-172`

**Root Cause:** Two separate `try/except` blocks attempt to create tracing child spans — the first checks `propagation_ctx`, the second checks `propagation_ctx is None`. Both do the same thing: create a child span via `correlation_engine.child()`. If `propagation_ctx` is falsy but `trace_ctx` is also None, the second block runs AND creates a span but also sets `propagation_ctx = True` (line 170), causing the `_ce.end()` at line 230 to pop the span.

**Impact:** Span lifecycle is mismatched: span created at line 164, but `propagation_ctx = True` causes the `end()` at line 230 to execute, while the first span's end is never called. Stack imbalance in the tracing context.

---

### BUG-SWARM-011 (MEDIUM) — No Propagation Depth Limit in `remove_stale()`

**File:** `memory/shared_memory.py:515-536`

```python
records = (
    self._db.query(SharedMemoryRecord)
    .filter(SharedMemoryRecord.ttl_seconds.isnot(None))
    .limit(batch_size)
    .all()
)
stale = [r for r in records if is_stale(r, now=now)]
```

**Impact:** `is_stale()` is evaluated in Python after pulling from DB. The `batch_size` is the SQL LIMIT, not the number of stale records. If only 1 out of 100 records is stale, only 1 gets deleted per call. In tables with millions of records, this would take millions of iterations. No index on `ttl_seconds` + `created_at`.

---

### BUG-SWARM-012 (MEDIUM) — Phase Timeout Check Runs After Handler Returns

**File:** `swarm/orchestrator.py:341-355`

```python
try:
    result = handler()
    elapsed_ms = (time.monotonic() - start_ts) * 1000

    if elapsed_ms > timeout_ms:
        self.lifecycle.timeout_phase(phase, elapsed_ms)
        # ... publishes PHASE_TIMEOUT
        return  # ← Silently exits without error
```

**Root Cause:** The timeout check happens AFTER the handler returns. If the handler took longer than the timeout, the phase is marked as timed out AFTER it already completed successfully. The handler's result is discarded, and the phase is not marked as completed.

**Impact:** A phase that succeeds after exceeding its timeout is treated as timed out. The result is lost. The lifecycle's `achieved_postconditions` are not set for the timed-out phase.

---

### BUG-SWARM-013 (LOW) — `compute_ttl` Can Return TTL Shorter Than Processing Time

**File:** `memory/memory_rules.py:183-185`

```python
factor = 0.5 + confidence
return max(60, int(base_ttl * factor))
```

For low-confidence observations (confidence=0.0), the factor is 0.5. For `signal` type with base TTL of 3 days (259200s), the result is 129600s (safe). But this is a minor issue — the minimum of 60 seconds is a safety net.

---

### BUG-SWARM-014 (LOW) — `_phase_risk_assessment` Calls `_init_agents()` Unconditionally

**File:** `swarm/orchestrator.py:603`

```python
def _phase_risk_assessment(self) -> dict[str, Any]:
    self._init_agents()
```

Unlike `_phase_pedagogical_analysis` and `_phase_adaptive_adjustment` which check `is_programming` before initializing agents, `_phase_risk_assessment` always initializes ALL agents (including pedagogical, adaptive, evaluation) even for non-programming courses. This triggers DB queries and resource allocation unnecessarily.

**Impact:** For general (non-programming) courses, 4 agents are still initialized and loaded into memory, even though only the risk agent is used.

---

## 3. Activation Lifecycle Analysis

### Flow Diagram with Race Annotations

```
activate_enrollment_with_swarm()
  ├── UnitOfWork(db)                          # activation_service.py:160
  ├── SwarmOrchestrator(db, context, uow)     # orchestrator.py:108
  ├── orchestrator.activate()
  │   ├── context_lock.acquire(context_key)   # Thread lock (process-local only)
  │   │   ⚠ Only protects within same process
  │   ├── _run_lifecycle()
  │   │   ├── _execute_phase(ENTERING, ...)
  │   │   ├── _execute_phase(CONTEXT_LOADING, ...)
  │   │   ├── _execute_phase(MEMORY_INIT, ...)
  │   │   ├── _execute_phase(PEDAGOGICAL_ANALYSIS, ...)
  │   │   │   ⚠ BUG-SWARM-014: agents initialized even for non-programming
  │   │   ├── _execute_phase(ADAPTIVE_ADJUSTMENT, ...)
  │   │   ├── _execute_phase(RISK_ASSESSMENT, ...)
  │   │   ├── _execute_phase(CONSENSUS, ...)
  │   │   │   ⚠ BUG-SWARM-001: MagicMock objects used
  │   │   ├── _execute_phase(INFERENCE, ...)
  │   │   ├── _execute_phase(CONTENT_PRODUCTION, ...)
  │   │   ├── _execute_phase(ACTIVE, ...)
  │   │   │   ⚠ BUG-SWARM-007: ACTIVATION_COMPLETED × 2
  │   │   │   ⚠ BUG-SWARM-012: timeout checks after handler returns
  │   │   └── swarm_event_bus.publish(ACTIVATION_COMPLETED)
  ├── db.commit()                             # activation_service.py:165
  │   ⚠ BUG-SWARM-002: nested transaction risk
  └── uow.close()
```

### Key Observations

1. **Sequential execution is correct by design** — phases never overlap for the same context
2. **ContextLock uses `threading.Lock`** — single-process only; multi-worker deployments have NO protection
3. **DistributedDedupEngine supports cross-process dedup** but is NOT used in the activation path
4. **No phase-level idempotency** — if `db.commit()` fails midway (phase 7/10), the next activation attempt starts from scratch with no partial-state detection
5. **Phase gate dead code** removes the only safety mechanism for out-of-order execution

---

## 4. Propagation Diagnostics

### Event Flow

```
SwarmEventBus (in-process, thread-safe)
  ├── publish() → creates SwarmEvent with causation_id chain
  ├── _deliver() → synchronous handler dispatch
  ├── detect_propagation_failures() → post-hoc check
  └── detect_event_storm() → rate-based detection
```

### Propagation TTL Controls

`PropagationTTLManager` provides:
- `max_hops` (default: 10)
- `ttl_seconds` (default: 300)
- `decay_factor` (default: 0.8)
- `min_strength` (default: 0.1)
- Feedback loop detection (visited agents)
- DAG cycle detection (visited events)
- Storm rate detection (threshold: 20 events/sec)

### Deficiencies

1. **No integration with SwarmEventBus** — the `ttl_event_guard()` function in `propagation_ttl.py:617` exists but is NOT wired into `SwarmEventBus._deliver()`. Events publish without TTL validation.

2. **No distributed propagation** — `SwarmEventBus` is in-process only. Events are not serialized or forwarded to other processes/services.

3. **Causation chain is in-memory only** — on process restart, all causation data is lost. No persistence of event causation chains.

4. **`_calculate_depth()` traverses the entire event list** — for each event, it walks the full causation chain. With many events, this is O(n²).

---

## 5. Shared Memory Analysis

### Write Path

```
SharedMemoryStore.publish_observation()
  ├── Optional: DistributedDedupEngine (NOT used in swarm path — BUG-SWARM-009)
  ├── Optional: CorrelationEngine.child() (mismatched span — BUG-SWARM-010)
  ├── compute_ttl() → deterministic TTL
  ├── SharedMemoryRecord created → session.add()
  ├── uow.flush()
  ├── diagnostics_engine.record_memory_op()
  └── return record.id
```

### Read Path

```
SharedMemoryStore.query()
  ├── Filters by: student_id, module_id, memory_type, key, voter_name
  ├── ORDER BY created_at DESC
  ├── LIMIT 50 (default)
  ├── Post-filter: exclude stale (is_stale() in Python)
  └── Returns records
```

### Issues

1. **`remove_stale()` NEVER runs** — TTL-based cleanup is dead code
2. **No composite index** on `(student_id, module_id, memory_type, created_at)` — queries scan + sort
3. **Stale filtering is post-query** — records are fetched from DB then filtered in Python; dead records waste I/O
4. **Confidence computation (`compute_memory_confidence`)** is O(n log n) due to sorting by `created_at` — fine for small n, but called in `aggregate_confidence()` which is called by the CollectiveInferenceEngine
5. **No write dedup** in swarm activation path (BUG-SWARM-009)

---

## 6. Consensus Analysis

### Voter Architecture

| Voter | Source | Decision Basis |
|-------|--------|----------------|
| `MasteryVoter` | `core/consensus.py:202` | Score vs threshold (0.6/0.4) |
| `PrereqVoter` | `core/consensus.py:276` | DB query for incomplete prereqs |
| `SequenceVoter` | `core/consensus.py` (not fully read) | Module ordering |
| `TimeVoter` | `core/consensus.py` (not fully read) | Engagement time heuristic |
| `CodeMasteryVoter` | `core/programming_voters.py` | Programming-specific |
| `ProgressionVoter` | `core/programming_voters.py` | Programming-specific |

### Critical Issues

1. **BUG-SWARM-001**: `CodeMasteryVoter` and `ProgressionVoter` receive `MagicMock` module/path objects
2. **No voter timeout** — individual voters run synchronously; one slow voter blocks the entire consensus
3. **Vote count hardcoded** — `orchestrator.py:630-636` always has 4-6 voters, no dynamic voter selection based on context
4. **Consensus result published to shared memory BEFORE shared memory is initialized with dedup** — memory records from consensus have no dedup protection

---

## 7. Collective Inference Analysis

### Engine Architecture

`CollectiveInferenceEngine.infer()`:
1. Detect patterns via `PatternDetector.detect_all()`
2. Aggregate confidence via `compute_memory_confidence()`
3. Blend pattern + base confidence (60/40 split)
4. Build reasoning chain
5. Form conclusion string

### Issues

1. **Pattern confidence formula** (`core/collective_inference.py:127-128`): `sum(p.confidence * p.strength) / max(len(patterns), 1)` — treats each pattern equally; doesn't account for contradictory patterns
2. **Single voter warning** (`core/collective_inference.py:287-289`): correctly flags single-voter observations but doesn't adjust confidence downward
3. **Conclusion string is not structured** — it's a human-readable sentence, not a structured decision. Downstream consumers must parse strings.
4. **No contradiction resolution** — contradictions are flagged in the conclusion but not resolved. The final conclusion includes both sides.

---

## 8. Event Propagation Analysis

### Outbox Pattern

The `OutboxService` persists events atomically in the same transaction as business data. Key flow:

```
Service → UoW.add_event() → EventOutbox (same TX)
OutboxService.publish_pending() → mark as published
```

### Issues

1. **`publish_pending()` uses `FOR UPDATE SKIP LOCKED`** but only for PostgreSQL — SQLite has no such mechanism
2. **No handler dispatch** — Phase 1 only marks events as "published". No actual handler invocation.
3. **No dead letter queue** — events that exceed `max_retries` stay as "failed" status; no alerting or DLQ
4. **`retry_failed()` resets status to "pending"** but doesn't limit retries beyond the original `max_retries` check in `publish_pending()`

### Distributed Dedup

`DistributedDedupEngine` provides:
- Content-hash dedup for events and memory
- 3 layers: advisory lock → DB constraint → baggage propagation
- Phase-level consensus dedup

### Issues

1. **Not wired into swarm activation** — `SwarmOrchestrator` doesn't pass `dedup_engine` to `SharedMemoryStore` (BUG-SWARM-009)
2. **`dedup_consensus()` not called** — the consensus phase has no dedup protection
3. **Baggage integration is reactive** — dedup keys are tagged into baggage after the fact, not checked from baggage proactively

---

## 9. Distributed Coordination Analysis

### Current Architecture

The system is **single-process only** for coordination:
- `ContextLock` uses `threading.Lock` — does NOT work across multiple workers
- `SwarmEventBus` is in-process memory — events are never serialized
- `PhaseGate` / `SwarmFence` use `threading.Condition` — same-process only
- `advisory_lock` in `db/locks.py` uses `pg_advisory_xact_lock` — works cross-process but is only used by `DistributedDedupEngine`

### Multi-Worker Risk

If deployed with multiple Uvicorn workers (or containers):
- TWO activations for the SAME context can run simultaneously (no cross-process lock)
- Phase gates don't block because they're never waited on AND they're per-process
- Event bus events are local to each worker

---

## 10. Bottlenecks & Race Conditions

### Identified Bottlenecks

| Location | Type | Severity | Description |
|----------|------|----------|-------------|
| `orchestrator.py:240-282` | Sequential | HIGH | 10 phases run sequentially; no parallelization |
| `orchestrator.py:630-636` | Voter execution | MEDIUM | All voters run synchronously in one thread |
| `shared_memory.py:515-541` | Cleanup | MEDIUM | `remove_stale()` queries ALL TTL records then filters in Python |
| `events/outbox.py:48-64` | Event publish | MEDIUM | `publish_pending()` processes one event at a time |
| `events/propagation_ttl.py:355-356` | Serialization | LOW | `to_baggage()` joins all visited_agents/events into single string → truncation at 768 chars |

### Identified Race Conditions

| Location | Type | Severity | Description |
|----------|------|----------|-------------|
| `orchestrator.py:906` | Causation race | HIGH | `_last_event_id()` returns wrong causation parent |
| `activation_service.py:160-168` | Transaction race | CRITICAL | Nested commit/rollback with session_service |
| `swarm/synchronization.py:166` | Lock race | MEDIUM | `ContextLock` uses thread locks — not process-safe |
| `swarm/events.py:183` | Event race | MEDIUM | `_events` list grows unbounded (no max limit enforced in publish) |
| `shared_memory.py:515-536` | Remove-then-delete | LOW | `remove_stale()` could delete records created between query and delete in concurrent sessions |

---

## 11. Observability Recommendations

### Critical (Implement Immediately)

1. **Add phase-level tracing spans** — each `_execute_phase()` should create a `CorrelationEngine.child()` span with `phase` as operation name. Currently only event bus publishing provides observability.

2. **Instrument consensus voters** — each voter should produce a timing metric and trace span. Currently no per-voter observability.

3. **Add memory TTL monitoring** — alert when stale record count exceeds threshold (indicates `remove_stale()` not keeping up).

4. **Add causation chain validation** — periodically validate that causation chains are complete (no missing intermediate events).

### High Priority

5. **Add activation duration metrics** — track total activation time, per-phase P50/P95/P99 via `SwarmActivationMetrics`

6. **Add agent health check** — `AgentFactory` should report agent initialization time and success/failure as a metric

7. **Add event bus size monitoring** — alert when in-memory event list exceeds threshold (memory leak detection)

8. **Add dedup hit rate metric** — track how often `DistributedDedupEngine` prevents duplicate processing

### Medium Priority

9. **Add shared memory lineage depth distribution** — histogram of lineage chain lengths for anomaly detection

10. **Add Voter decision distribution** — track APPROVE/REJECT/ABSTAIN ratios per voter over time

11. **Add TTL lifecycle events** — emit events when shared memory records expire or are removed

---

## 12. Runtime Stabilization Recommendations

### Critical (Fix Immediately)

1. **BUG-SWARM-001**: Replace `MagicMock` with real DB queries in `_phase_consensus()`. Use `orm_utils` or direct `db.query()` to load real `PathModule` and `LearningPath` instances.

2. **BUG-SWARM-002**: Restructure `session_service.start_module_session()` to use a single `UnitOfWork` that wraps both session creation AND swarm activation. Use savepoints if partial rollback recovery is needed.

3. **BUG-SWARM-003**: In `swarm_activation_service.py`, set status to a new `FAILED` state on exception. Never mark as `ACTIVE` when initialization fails.

### High Priority

4. **Wire PhaseGate.wait() into `_execute_phase()`** — call `gate.wait()` after constructing the gate but before `lifecycle.start_phase()`. This provides a real synchronization barrier for concurrent phase execution (future parallelization) and validates precondition completeness.

5. **Fix causation chain direction** — publish STARTED event first, capture its event_id, and use it as `causation_id` for COMPLETED/FAILED events. Reverse the current causation flow.

6. **Wire DistributedDedupEngine into SharedMemoryStore** in the orchestrator path — pass a `dedup_engine` instance to prevent duplicate memory publications during retry scenarios.

### Medium Priority

7. **Schedule `remove_stale()`** — add a periodic task (APSchedule or FastAPI lifespan background task) that calls `remove_stale()` every 5 minutes.

8. **Add composite index** on `SharedMemoryRecord(student_id, module_id, memory_type, created_at)` to speed up query performance.

9. **Fix `ACTIVATION_COMPLETED` double-publish** — change `PHASE_EVENT_MAP[ACTIVE]` started event to a new `ACTIVATION_STARTED` event type, or use empty string to skip the start event.

10. **Add DistributedDedupEngine.dedup_consensus()** call in `_phase_consensus()` to prevent duplicate consensus runs for the same (module, student, phase) combination.

### Low Priority

11. **Remove dead code**: `PhaseGate` (if not used), `SwarmFence` (if not used), the redundant second `correlation_engine.child()` block in `shared_memory.py`.

12. **Fix `compute_ttl`** to use a non-linear scaling function for low-confidence observations.

---

## Appendix: File Index

| File | Lines | Findings |
|------|-------|----------|
| `swarm/orchestrator.py` | 923 | BUG-001, BUG-004, BUG-005, BUG-006, BUG-012, BUG-014 |
| `swarm/lifecycle.py` | 286 | Correct state machine implementation |
| `swarm/events.py` | 367 | BUG-007; in-process event bus |
| `swarm/synchronization.py` | 219 | BUG-004, BUG-005; ContextLock (thread-local) |
| `swarm/detectors.py` | 444 | Theoretically correct; limited by phase gate dead code |
| `swarm/agent_factory.py` | 86 | Clean factory pattern |
| `swarm/metrics.py` | — | Not fully audited |
| `memory/shared_memory.py` | 606 | BUG-008, BUG-009, BUG-010, BUG-011 |
| `memory/collective_inference.py` | 379 | Clean; string-based conclusions |
| `memory/memory_rules.py` | 248 | BUG-013 |
| `core/consensus.py` | 1283+ | Voter architecture; MagicMock-input vulnerability |
| `events/propagation_ttl.py` | 715 | TTL controls exist but not wired into event bus |
| `events/distributed.py` | 365 | Dedup engine exists but not wired into activation |
| `events/outbox.py` | 163 | Phase-1 implementation; no handler dispatch |
| `services/activation_service.py` | 209 | BUG-002, BUG-003 |
| `services/session_service.py` | 172 | BUG-002 |
| `services/swarm_activation_service.py` | 80 | BUG-003 |
| `db/uow.py` | 326 | Correct; savepoint support |
| `db/locks.py` | 104 | Correct; pg_advisory_xact_lock |
