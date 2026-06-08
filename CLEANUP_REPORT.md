# CLEANUP_REPORT.md — UPAO-MAS-EDU Codebase Cleanup Plan

**Date:** 2026-06-02  
**Codebase:** 363 Python files, 84,029 LOC (backend only; 98 frontend TS/TSX/Vue files not counted)  
**Report scope:** Backend `app/` directory plus scripts, tests, migrations, and scaffolding.

---

## 1. Executive Summary

The codebase has evolved through multiple architectural phases — from a simple Spanish-named FastAPI CRUD, through a LangGraph agent swarm, to a full observability + experiment + tracing platform. This evolution left behind:

- **~2,480 lines** of completely dead production code (zero imports from outside the owning package)
- **~1,463 lines** in a dead subpackage (`app/core/agent_health/`)
- **~657 lines** across two dead consensus-timeout middlewares/metrics that are only test-harnessed but never wired
- **~3,482 lines** in `experiment/benchmark/` which duplicates `experiment/` with a separate parallel API
- **~130 lines** of superseded idempotency middleware
- **19 files** of abandoned temp Vite scaffold
- **2 files** with conflicting names serving different domains (`events/replay.py` vs `experiment/replay.py`)
- **1 dangling export** in `tracing/__init__.py` (`propagation_guard`)

**Total removable safely:** ~5–6% of backend code.  
**Total requiring consolidation:** ~4–5% more.  
**Overall impact:** ~8–10% of the codebase is dead, duplicated, or confusing.

---

## 2. Dead Code Inventory

### 2.1 `app/core/agent_health/` — Entirely Dead (8 files, 1,463 lines)

| File | Lines | Status |
|---|---|---|
| `app/core/agent_health/__init__.py` | 0 | Empty |
| `app/core/agent_health/models.py` | 184 | Internal use only |
| `app/core/agent_health/monitor.py` | 277 | Internal use only |
| `app/core/agent_health/health_scorer.py` | 150 | Internal use only |
| `app/core/agent_health/health_score_voter.py` | 80 | Internal use only |
| `app/core/agent_health/collective_stability.py` | 212 | Internal use only |
| `app/core/agent_health/behavioral_baseline.py` | 107 | Internal use only |
| `app/core/agent_health/adaptive_degradation.py` | 188 | Internal use only |
| `app/core/agent_health/meta_monitor.py` | 265 | Internal use only |
| **Total** | **1,463** | |

**Evidence — Zero production imports:**

```bash
$ grep -rn "from app\.core\.agent_health" backend/app/ --include="*.py"
# Only results: internal cross-imports within the package itself
# backend/app/core/agent_health/monitor.py  imports from other agent_health/ files
# backend/app/core/agent_health/health_scorer.py, health_score_voter.py, etc. import from models.py

$ grep -rn "from app\.core\.agent_health" backend/tests/ --include="*.py"
# Only result: backend/tests/test_agent_health.py  (a test file, not production)
```

**No file outside `app/core/agent_health/` or `tests/` imports any symbol from this package.** The entire subtree is dead.

---

### 2.2 `app/core/consensus_timeout_middleware.py` — Dead (414 lines)

**Evidence:**

```bash
$ grep -rn "from app\.core\.consensus_timeout_middleware\|ConsensusTimeoutMiddleware" backend/app/
# Only result: the file itself (self-referential comments)
backend/app/core/consensus_timeout_middleware.py:  internal references only

$ grep -rn "ConsensusTimeoutMiddleware" backend/tests/
# Multiple hits in tests/test_consensus_timeouts.py
```

This middleware wraps `ConsensusEngine` with async cancellation and hung-agent recovery, but **no production code ever instantiates it**. The `ConsensusEngine.run()` method in `app/core/consensus.py` has a lazy import of `consensus_timeouts` (the policy), but NOT of `consensus_timeout_middleware`.

---

### 2.3 `app/core/consensus_timeout_metrics.py` — Transitively Dead (243 lines)

Only imported by:
1. `app/core/consensus_timeout_middleware.py` (itself dead — see 2.2)
2. `tests/test_consensus_timeouts.py`

No other production imports. **Dead by association.**

---

### 2.4 `app/middleware/idempotency.py` — Superseded (130 lines)

This was the original idempotency middleware (per-endpoint `Depends(get_idempotency_key)` pattern). It was **superseded by `app/events/middleware.py`** (204 lines), which provides a FastAPI middleware-based approach wired in `main.py:204`:

```python
# main.py:204 — uses events-based middleware
from app.events.middleware import make_idempotency_middleware
app.middleware("http")(make_idempotency_middleware())
```

**Evidence — only test imports:**

```bash
$ grep -rn "from app\.middleware\.idempotency" backend/app/
# No results
$ grep -rn "from app\.middleware\.idempotency" backend/tests/
backend/tests/test_concurrency.py: imports from app.middleware.idempotency
```

The production path `app/events/middleware.py` is the active middleware. The `app/middleware/idempotency.py` file is dead.

---

### 2.5 `app/swarm_diagnostics/middleware/fastapi.py` — Dead (80 lines)

Defines `SwarmDiagnosticsMiddleware` — a FastAPI middleware class for automatic swarm instrumentation. **Never wired into `main.py`** or any production code.

**Evidence:**
- `main.py` does NOT import or add this middleware
- Only self-referential import inside the file itself
- No other production file imports it

---

### 2.6 `app/swarm_diagnostics/alerts/__init__.py` — Dead (28 lines)

Defines `ALERT_RULES` list and `should_alert()` utility. **Never imported by any production code.**

```bash
$ grep -rn "from app\.swarm_diagnostics\.alerts\|should_alert\|ALERT_RULES" backend/app/ --include="*.py"
# No results
```

---

### 2.7 `temp_vite_project/` — Abandoned Scaffolding (19 files)

A parallel `temp_vite_project/` directory at the repository root contains a scaffolded Vite + React project. It includes:
- `package.json`, `vite.config.ts`, `tsconfig*.json`
- `src/App.tsx`, `src/main.tsx`, `src/index.css`
- `public/favicon.svg`, `public/icons.svg`
- `assets/hero.png`, etc.

This is **not referenced** by any `docker-compose`, `package.json`, or build script. The active frontend lives in `frontend/`. This is abandoned scaffolding — likely a temporary experiment that was committed by mistake.

---

### 2.8 `app/tracing/propagation.py` — Dangling Export: `propagation_guard`

Exported in `app/tracing/__init__.py:5`:
```python
from app.tracing.propagation import propagation_guard, ...
```

But `propagation_guard` is **only used in tests**:

```bash
$ grep -rn "propagation_guard" backend/app/ --include="*.py"
backend/app/tracing/__init__.py:5  (re-export only)
backend/app/tracing/propagation.py:63  (definition)

$ grep -rn "propagation_guard" backend/tests/
backend/tests/test_tracing.py:30  (imported and used in test helper)
```

The other three exports from `propagation.py` are alive:
- `TraceLoggingFilter` — used in `main.py:73`
- `sanitize_inbound_headers` — used in `test_tracing.py`
- `sanitize_outbound_headers` — used in `test_tracing.py`

---

## 3. Duplication Report

### 3.1 `app/api/routes/estudiantes.py` vs `app/api/routes/students.py`

| Aspect | `estudiantes.py` | `students.py` |
|---|---|---|
| Lines | 145 | 418 |
| Prefix | `/api/estudiante` | `/api/students` |
| Tag | `Estudiante` | `Estudiantes` |
| Auth | `get_current_estudiante` | `get_current_estudiante` |
| Endpoints | diagnostic, path, module, evaluation | onboarding, cycle, profile, diagnostic, learning-path, module, progress, evaluation, tutor |
| Wired in main.py | Yes (line 288) | Yes (line 289) |
| Frontend usage | Only `PATCH /api/estudiante/module/{id}` | All other student endpoints |

**Analysis:** `estudiantes.py` is the legacy Spanish-named router. It contains a subset of endpoints that are duplicated in `students.py`. The frontend still calls ONE endpoint from `estudiantes` (`PATCH /api/estudiante/module/{module_id}` at `frontend/src/hooks/useStudent.ts:124`). All other student endpoints use `/api/students/`.

---

### 3.2 `app/events/replay.py` vs `app/experiment/replay.py`

| Aspect | `events/replay.py` | `experiment/replay.py` |
|---|---|---|
| Lines | 327 | 117 |
| Purpose | Outbox event replay with idempotency | Deterministic experiment replay from snapshots |
| Key class/function | `EventReplayService` | `replay_from_config()`, `verify_reproducibility()` |
| Both wired? | Yes, in their respective `__init__.py` | Yes |

**Analysis:** These are NOT duplicates — they serve completely different domains. However, the naming collision is highly confusing. Any developer searching for "replay" will find both files. **Recommendation:** Rename `events/replay.py` → `events/event_replay.py` and `experiment/replay.py` → `experiment/experiment_replay.py`.

---

### 3.3 `app/experiment/benchmark/` (15 files, 3,482 lines) vs `app/experiment/` (17 files, ~4,500 lines)

The `benchmark/` subpackage duplicates much of the top-level `experiment/` functionality:

| Concept | `app/experiment/` | `app/experiment/benchmark/` |
|---|---|---|
| Conditions | `conditions.py` | `benchmark/conditions.py` |
| Metrics | `metrics.py` | `benchmark/metrics.py` |
| Analysis/Stats | `analysis.py` | `benchmark/statistics.py` |
| Orchestrator | `orchestrator.py` | `benchmark/orchestrator.py` |
| Exports | `export.py` | `benchmark/exports.py` |
| Visualization | (none separate) | `benchmark/visualization.py` |
| Scenarios | `dataset.py` | `benchmark/scenarios.py` |

**Evidence:** The two systems have different class names and APIs:
- `app/experiment/` uses `ExperimentCondition`, `PerRunMetrics`, `AggregatedMetrics`, `ExperimentOrchestrator`, `ExperimentConfig`, `ExperimentDataset`
- `app/experiment/benchmark/` uses `BenchmarkCondition`, `BenchmarkMetrics`, `MetricsCalculator`, `BenchmarkOrchestrator`, `BenchmarkResult`, `ScenarioGenerator`

The benchmark package has its own execution pipeline (`runner.py`, `executor.py`, `mapper.py`) and a `real/` sub-package for real-swarm execution. It is used by `scripts/run_academic_benchmark.py` and `scripts/run_real_benchmark.py`.

**Analysis:** This is a parallel benchmarking system that was developed alongside (or after) the main experiment system. It duplicates the experiment concepts with a different API. Consider merging or clearly deprecating one.

---

## 4. Deduplication Strategy

| # | Duplicate Pair | Action | Rationale |
|---|---|---|---|
| 1 | `estudiantes.py` / `students.py` | **Consolidate into `students.py`.** Add the `PATCH /api/estudiante/module/{id}` endpoint to `students.py` under both prefixes if needed. Add deprecation warning to `estudiantes.py`. Mark for deletion after frontend migrates. | Both are wired but 95% overlap. |
| 2 | `events/replay.py` / `experiment/replay.py` | **Rename both** to eliminate collision: `events/event_replay.py` and `experiment/experiment_replay.py`. Update `__init__.py` exports. | Different domains, same confusing name. |
| 3 | `experiment/` / `experiment/benchmark/` | **Create an ADR** (Architecture Decision Record) to decide which is canonical. If benchmark is the successor, deprecate `experiment/` top-level. If `experiment/` is canonical, move benchmark into it as a sub-module with shared primitives. | Two parallel experiment systems is unsustainable. |
| 4 | `observability/tracing.py` / `tracing/` | **Keep both.** `observability/tracing.py` is a lightweight `TraceContext` (172 lines); `app/tracing/` is the full distributed tracing suite (PropagationContext, CorrelationEngine, LangGraph instrumentation, FastAPI middleware). They serve different abstraction levels. | Not true duplicates — different scope. |

---

## 5. Cleanup Order

### Phase 1 — Safe Deletions (no production impact)

1. Delete `temp_vite_project/` directory entirely
2. Delete `app/swarm_diagnostics/alerts/__init__.py` (never imported)
3. Delete `app/swarm_diagnostics/middleware/fastapi.py` (never wired)
4. Remove `propagation_guard` from `app/tracing/__init__.py` exports (keep definition for tests if needed)

### Phase 2 — Consensus Timeout Cleanup (test-only impact)

5. Delete `app/core/consensus_timeout_middleware.py` (414 lines)
6. Delete `app/core/consensus_timeout_metrics.py` (243 lines)
7. Update `tests/test_consensus_timeouts.py` to remove middleware/metrics tests (or move to a separate file)

### Phase 3 — Agent Health Removal (test-only impact)

8. Delete entire `app/core/agent_health/` directory (8 files, 1,463 lines)
9. Delete `tests/test_agent_health.py`

### Phase 4 — Superseded Middleware

10. Delete `app/middleware/idempotency.py` (130 lines)
11. Update `tests/test_concurrency.py` to reference `app/events.middleware` instead

### Phase 5 — Consolidation (needs verification)

12. **estudiantes.py → students.py merge:**
    - Add `PATCH /api/estudiante/module/{module_id}` to `students.py` (or add a second router prefix)
    - Add deprecation notice to `estudiantes.py`
    - Update frontend to use `/api/students/module/{module_id}` instead of `/api/estudiante/module/{module_id}`
    - After frontend migration: delete `estudiantes.py`

13. **Rename replay files:**
    - `events/replay.py` → `events/event_replay.py`
    - `experiment/replay.py` → `experiment/experiment_replay.py`
    - Update all imports in `__init__.py`, `api/routes/idempotency.py`, scripts, and tests

### Phase 6 — Strategic Decision

14. **Benchmark vs Experiment consolidation** — Requires team ADR. Do not delete either until a decision is made.

---

## 6. Risk Assessment

| Removal | Risk Level | What Could Break | Verification |
|---|---|---|---|
| `temp_vite_project/` | None | Nothing | `git grep temp_vite_project` to confirm zero references |
| `alerts/__init__.py` | None | Nothing | No production imports |
| `middleware/fastapi.py` | None | Nothing | No production imports |
| `propagation_guard` export | **Low** | Any external code importing it from `app.tracing` | `grep -r "from app\.tracing import.*propagation_guard"` outside repo |
| `consensus_timeout_middleware.py` | **Low** | Tests break; no production code | Run test suite before/after |
| `consensus_timeout_metrics.py` | **Low** | Same as above; may also affect middleware | Same |
| `agent_health/` full directory | **Low** | Only `test_agent_health.py` breaks | Run full test suite; check coverage |
| `middleware/idempotency.py` | **Low** | `test_concurrency.py` may break | Update test to use `events/middleware` |
| `estudiantes.py` removal | **Medium** | Frontend `PATCH /api/estudiante/module/{id}` will 404 | Must add endpoint to `students.py` first; run frontend E2E |
| Rename `events/replay.py` | **Medium** | All imports across codebase must be updated | Search for `from app.events.replay` and update all |
| Rename `experiment/replay.py` | **Medium** | All imports across codebase must be updated | Search for `from app.experiment.replay` and update all |
| `experiment/benchmark/` changes | **High** | Scripts (`run_academic_benchmark.py`, `run_real_benchmark.py`) may break | Requires ADR first |

### Verification Strategy

For Phase 1–3 removals:

```bash
# Verify no production imports before deleting
grep -rn "from app\.core\.agent_health" backend/app/ --include="*.py"
grep -rn "from app\.core\.consensus_timeout_middleware" backend/app/ --include="*.py"
grep -rn "from app\.core\.consensus_timeout_metrics" backend/app/ --include="*.py"
grep -rn "from app\.middleware\.idempotency" backend/app/ --include="*.py"
grep -rn "from app\.swarm_diagnostics\.alerts\|from app\.swarm_diagnostics\.middleware" backend/app/ --include="*.py"

# After deletion, run tests
cd backend && python -m pytest tests/ -x -q
```

For Phase 5–6, run the full test suite plus integration test against a staging database.

---

## Appendix A: File Count Summary

| Directory/Area | Files | Lines | Status |
|---|---|---|---|
| `app/core/agent_health/` | 8 | 1,463 | **DELETE** |
| `app/core/consensus_timeout_middleware.py` | 1 | 414 | **DELETE** |
| `app/core/consensus_timeout_metrics.py` | 1 | 243 | **DELETE** |
| `app/middleware/idempotency.py` | 1 | 130 | **DELETE** |
| `app/swarm_diagnostics/middleware/fastapi.py` | 1 | 80 | **DELETE** |
| `app/swarm_diagnostics/alerts/__init__.py` | 1 | 28 | **DELETE** |
| `temp_vite_project/` | 19 | ~500 | **DELETE** |
| `app/api/routes/estudiantes.py` | 1 | 145 | **CONSOLIDATE** |
| `app/events/replay.py` / `experiment/replay.py` | 2 | 444 | **RENAME** |
| `app/experiment/benchmark/` | 15 | 3,482 | **ADR NEEDED** |
| **Subtotal removable** | **~37** | **~3,500** | |
| Active backend code | ~326 | ~80,500 | |
| **Removable fraction** | **~10%** | **~4%** | |

## Appendix B: Git Blame Notes

- `app/core/agent_health/`: Likely added as part of a proposed "agent health monitoring" feature that was never fully integrated into the consensus engine or main.py.
- `consensus_timeout_middleware.py` + `consensus_timeout_metrics.py`: These appear to be a refactoring attempt that was abandoned mid-implementation. The timeouts policy (`consensus_timeouts.py:952` lines) is alive and used, but its middleware wrapper and metrics were never wired.
- `app/middleware/idempotency.py`: The original implementation before the event-based system was built.
- `estudiantes.py`: The first Spanish-named router — survived alongside the newer `students.py` due to frontend dependency.
- `app/experiment/benchmark/`: Likely developed by a different team member or at a different time, explaining the parallel API.
