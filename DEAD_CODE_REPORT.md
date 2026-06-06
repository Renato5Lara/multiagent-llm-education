# Dead Code Report — UPAO-MAS-EDU

Generated: 2026-06-02  
Scope: `backend/app/` (291 Python files, excluding tests, scripts, and alembic)

---

## Classification Legend

| Tag | Meaning |
|-----|---------|
| **ORPHAN** | Written but never imported or wired in production |
| **SUPERSEDED** | Replaced by a newer implementation |
| **DUPLICATE** | Direct copy or near-copy of another file |
| **LEGACY** | Was used but is no longer reachable from any active business flow |

---

## 1. ORPHAN — Entirely Unused in Production

### 1.1 `backend/app/core/consensus_timeout_middleware.py` (414 lines)

- **Classes:** `ConsensusTimeoutMiddleware`, `MiddlewareResult`
- **Contains:** Async-per-voter cancellation with `asyncio.wait_for`, hung-agent skip, metrics collection, deadline enforcement.
- **Evidence:** Zero imports from production code. Only references are in `tests/test_consensus_timeouts.py`. The `consensus.py` engine has its own inline timeout handling and does not use this middleware.
- **Classification:** ORPHAN

### 1.2 `backend/app/core/consensus_timeout_metrics.py` (243 lines)

- **Classes:** `ConsensusTimeoutMetrics`, `TimeoutMetricSnapshot`
- **Contains:** Thread-safe counters for timeouts, degraded mode, quorum fallback, hung agents, cascading delays.
- **Evidence:** Only imported by `consensus_timeout_middleware.py`, which is itself orphaned. No direct production import exists.
- **Classification:** ORPHAN (transitive through 1.1)

### 1.3 `backend/app/swarm_diagnostics/middleware/fastapi.py` (80 lines)

- **Classes:** `SwarmDiagnosticsMiddleware`
- **Functions:** `instrument_app`
- **Contains:** Auto-instrumentation middleware that injects diagnostic events per HTTP request.
- **Evidence:** `main.py` does **not** wire this middleware. The `instrument_app()` function exists but is never called. Only reference is within the file's own docstring example.
- **Classification:** ORPHAN

### 1.4 `backend/app/events/outbox.py` (163 lines)

- **Classes:** `OutboxService`
- **Singleton:** `outbox_service`
- **Contains:** Poll-and-publish loop for `EventOutbox` table rows.
- **Evidence:** Imported only via `events/__init__.py` barrel and in `tests/`. The only production file that references `outbox_service` is `dedup.py` (line 145), which is itself orphaned. Events are created via `events/types.py` but **never consumed** by any active service.
- **Classification:** ORPHAN

### 1.5 `backend/app/events/dedup.py` (320 lines)

- **Classes:** `DedupEventBus`, `IdempotentConsumer`, `ReplayGuard`
- **Exception:** `ReplayDetected`
- **Contains:** Exactly-once event dispatch on top of `OutboxService` and `IdempotencyService`.
- **Evidence:** Only imported by `events/__init__.py` barrel and in `tests/`. Zero production imports outside the barrel.
- **Classification:** ORPHAN

### 1.6 `backend/app/events/retry.py` (344 lines)

- **Classes:** `RetryHandler`, `CircuitBreaker`, `retry_stats`
- **Exceptions:** `RetryExhaustedError`, `CircuitBreakerOpenError`
- **Contains:** Retry-safe processing with exponential backoff. Note: this file's `CircuitBreaker` is **not** the same as `core/circuit_breaker.py`.
- **Evidence:** Only imported by `events/__init__.py` barrel and in `tests/`. Zero production imports outside the barrel.
- **Classification:** ORPHAN

### 1.7 `backend/app/events/propagation_ttl.py` (722 lines)

- **Classes:** `PropagationTTL`, `PropagationTTLManager`, `PropagationLifecycle`, `PropagationState`, `PropagationStopReason`, `PropagationRateTracker`, `propagation_lifecycle`
- **Functions:** `ttl_event_guard`, `ttl_consensus_hook`
- **Exceptions:** `PropagationError`, `PropagationStoppedError`, `FeedbackLoopError`, `DAGCycleError`, `PropagationStormError`
- **Contains:** Depth-aware TTL, hop counting, decay, anti-feedback-loop and DAG-cycle detection.
- **Evidence:** Only imported by `events/__init__.py` barrel. Referenced only in **docstrings/comments** in swarm diagnostics detectors (PropagationStormDetector, RecursiveAmplificationDetector, DAGTraversalPitfallDetector). Never actually instantiated or called from production code.
- **Classification:** ORPHAN

### 1.8 `backend/app/core/agent_health/` — Entire Directory (1,463 lines, 8 files)

| File | Lines | Contents |
|------|-------|----------|
| `__init__.py` | 0 | Empty — no exports |
| `monitor.py` | 277 | `AgentHealthMonitor` |
| `models.py` | 184 | `AgentHealthProfile`, `DegradationLevel`, `HealthSignal`, `BehavioralBaseline`, `AgentSlidingStats` |
| `meta_monitor.py` | 265 | `MetaMonitor`, `AnomalyOutcome`, `Intervention`, `MetaMonitorReport` |
| `health_scorer.py` | 150 | `HealthScorer`, `compute_health_score` |
| `health_score_voter.py` | 80 | `HealthScoreVoter` |
| `collective_stability.py` | 212 | `CollectiveStabilityScorer` |
| `behavioral_baseline.py` | 107 | `BehavioralBaselineManager` |
| `adaptive_degradation.py` | 188 | `AdaptiveDegradationManager` |

- **Evidence:** All intra-package imports are self-referential. The only external references to `agent_health` symbols come from `tests/test_agent_health.py`. The `__init__.py` is deliberately empty, making it impossible to import `AgentHealthMonitor` via `from app.core.agent_health import AgentHealthMonitor` without knowing the submodule.
- **Classification:** ORPHAN

---

## 2. SUPERSEDED — Replaced or Shadowed

### 2.1 `backend/app/api/routes/estudiantes.py` (145 lines)

- **Prefix:** `/api/estudiante`
- **Endpoints:** `POST/GET /diagnostic/{course_id}`, `POST/GET /path/{course_id}`, `PATCH /module/{module_id}`, `POST /evaluate/{module_id}`, `GET /progress/{course_id}`
- **Comparison:** `students.py` (418 lines) provides a **superset** of student functionality under `/api/students` with session management, swarm orchestration, and richer diagnostic/progress flows. Despite being superseded, `estudiantes.py` **is still wired** in `main.py` line 288, presumably for backward compatibility.
- **Evidence:** Both routers are registered. `students.py` has 2.9× more code.
- **Classification:** SUPERSEDED (kept for backward compatibility)

### 2.2 `backend/app/experiment/replay.py` (117 lines)

- **Functions:** `replay_from_config`, `verify_reproducibility`
- **Comparison:** This is **not** a duplicate of `events/replay.py`. Both serve different concerns (experiment replay vs. event replay). However, `experiment/replay.py` is only imported from `experiment/__init__.py` barrel and from `scripts/run_experiment.py`. No production endpoint or service calls it. The `experiment` package as a whole is a research/benchmarking tool, not a production dependency.
- **Classification:** LEGACY (only reachable via scripts)

---

## 3. LEGACY — Wired but Inactive in Core Business Flow

### 3.1 `backend/app/events/replay.py` (327 lines)

- **Classes:** `EventReplayService`
- **Singleton:** `event_replay_service`
- **Contains:** Safe replay of outbox events with idempotency protection.
- **Usage:** Only imported by `api/routes/idempotency.py` (an admin/debug endpoint). No business service calls it.
- **Classification:** LEGACY

### 3.2 `backend/app/events/risk_detectors.py` (486 lines)

- **Classes:** `RiskReport`, `BaseRiskDetector`, `ConsistencyRiskDetector`, `RaceConditionDetector`, `ReplayVulnerabilityDetector`, `DistributedDedupRiskDetector`, `IdempotencyRiskAnalysis`
- **Singleton:** `risk_analysis`
- **Contains:** Health analysis of the idempotency system.
- **Usage:** Only imported by `api/routes/idempotency.py`. Not part of any active monitoring pipeline.
- **Classification:** LEGACY

### 3.3 `backend/app/events/distributed.py` (365 lines)

- **Classes:** `DistributedDedupEngine`
- **Functions:** `extract_dedup_keys_from_propagation`
- **Singleton:** `distributed_dedup`
- **Usage:** Only imported by `api/routes/idempotency.py`. The `distributed_dedup.dead_letter_count()` is called from the admin route.
- **Classification:** LEGACY

### 3.4 `backend/app/events/integration.py` (393 lines)

- **Classes:** `IdempotentSharedMemory`, `IdempotentConsensusGuard`, `IdempotentUnitOfWork`
- **Functions:** `get_idempotency_key_from_propagation`
- **Usage:** Only reachable via `distributed.py` (lazy imports). The `_memory_key()` function is imported by `distributed.py`. Transitively used through the admin idempotency route.
- **Classification:** LEGACY

---

## 4. Notes on Items That Were Investigated but Are NOT Dead

| File | Reason Not Dead |
|------|----------------|
| `app/core/consensus_timeouts.py` (952 lines) | Imported by `consensus.py` line 904 |
| `app/core/consensus_cancellation.py` (232 lines) | Imported by `consensus.py` line 899 |
| `app/swarm_diagnostics/` (3,952 lines) | `diagnostics_engine` imported by `main.py`, `consensus.py`, `tracing/`, `memory/`, `experiment/`, `circuit_breaker.py`, `services/`, `swarm/` |
| `app/tracing/` (885 lines) | Wired in `main.py` lines 197–199; used across `agents/`, `consensus.py`, `memory/`, `events/` |
| `app/observability/` (1,202 lines) | `metrics_exporter`, `stream`, `swarm_diagnostics`, `consensus_metrics` are all used in production |
| `app/events/types.py` (33 lines) | `emit_event`/`EventType` used by `activation_service.py`, `course_service.py`, `student_service.py`, etc. |
| `app/events/idempotency.py` (385 lines) | Used by middleware, dedup, integration, replay, retry, distributed, and idempotency route |
| `app/events/middleware.py` (178 lines) | Wired in `main.py` line 205 |
| `app/swarm/events.py` (367 lines) | `SwarmEventBus` used by `orchestrator.py` and `detectors.py` |
| `app/swarm/metrics.py` (162 lines) | `SwarmActivationMetrics` used by `orchestrator.py` |
| `app/models/event_outbox.py` (88 lines) | Model used by `db/uow.py` (creates events), `events/types.py` |

---

## 5. Summary

| Category | Files | Total Lines |
|----------|-------|-------------|
| **ORPHAN** | 11 files + 1 directory (8 files) | 3,586 |
| **SUPERSEDED** | 1 file | 145 |
| **LEGACY** | 4 files | 1,571 |
| **TOTAL DEAD** | ~24 files | **~5,302 lines** |

### Quick Cleanup Priority

1. **Delete `app/core/agent_health/`** (1,463 lines) — entirely dead, empty `__init__.py`
2. **Delete `app/events/propagation_ttl.py`** (722 lines) — never imported outside barrel
3. **Delete `app/core/consensus_timeout_middleware.py`** (414 lines) — only used by tests
4. **Delete `app/core/consensus_timeout_metrics.py`** (243 lines) — transitively dead
5. **Delete `app/events/retry.py`, `app/events/dedup.py`, `app/events/outbox.py`** (827 lines combined) — never imported outside barrel
6. **Unwire `app/api/routes/estudiantes.py`** (145 lines) — superseded by `students.py`
7. **Delete `app/swarm_diagnostics/middleware/fastapi.py`** (80 lines) — never wired
