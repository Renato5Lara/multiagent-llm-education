# UPAO-MAS-EDU Architecture Map

> **Project**: Multi-Agent Educational System for Universidad Privada Antenor Orrego (UPAO)
> **Repo root**: `/var/home/rlara/Documentos/Proyecto/multiagent-llm-education`
> **Backend**: FastAPI + SQLAlchemy + LangGraph + Swarm orchestration
> **Frontend**: Vite + React + TypeScript + Tailwind CSS (in `frontend/`)
> **Database**: PostgreSQL (sync via psycopg, async via asyncpg)

---

## 1. High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                            HTTP / HTTPS (Nginx / Render)                        │
└─────────────────────────────────────────────────────────────────────────────────┘
                                       │
                    ┌──────────────────┴──────────────────┐
                    │          FastAPI App (main.py)       │
                    │  Middleware Stack (top→bottom):       │
                    │  1. TracingMiddleware (correlation)   │
                    │  2. IdempotencyMiddleware (dedup)     │
                    │  3. AuthRateLimitMiddleware           │
                    │  4. QueryTracingMiddleware            │
                    │  5. RequestIDMiddleware               │
                    │  6. LogRequestsMiddleware             │
                    │  7. CORSMiddleware                    │
                    ├──────────────────────────────────────┤
                    │  Lifespan: DB health check, upload    │
                    │  dirs, BugDiagnosticsBridge hookup    │
                    └──────────┬───────────────────────────┘
                               │
          ┌────────────────────┼────────────────────┐
          │                    │                    │
          ▼                    ▼                    ▼
  ┌──────────────┐   ┌────────────────┐   ┌─────────────────┐
  │  API Routes   │   │  Agent Routes   │   │ Swarm Endpoints  │
  │  (app/api/    │   │  (app/agents/   │   │ (app/api/swarm,  │
  │   routes/)    │   │   router.py)    │   │  observability)  │
  └──────┬───────┘   └───────┬────────┘   └────────┬────────┘
         │                   │                     │
         ▼                   ▼                     │
  ┌──────────────┐   ┌──────────────┐              │
  │  Services     │   │  Agent Graph  │              │
  │  (app/services)│   │ (LangGraph)  │              │
  └──────┬───────┘   └──────┬───────┘              │
         │                  │                       │
         ▼                  ▼                       │
  ┌──────────────────────────────────────────┐      │
  │           Core / Domain Layer             │      │
  │  Consensus · Trust · Weighting · Voters   │      │
  │  Specialization · Circuit Breaker         │      │
  └─────────────────────┬────────────────────┘      │
                        │                           │
          ┌─────────────┼─────────────┐              │
          ▼             ▼             ▼              │
  ┌────────────┐ ┌────────────┐ ┌──────────┐        │
  │  Models     │ │  Events    │ │  LLM     │        │
  │ (SQLAlchemy)│ │ (Outbox,   │ │ (Service,│        │
  │  + Neo4j KG │ │  Dedup)   │ │  Voters) │        │
  └────────────┘ └────────────┘ └──────────┘        │
          │                                           │
          ▼                                           │
  ┌──────────────────────────────────────────┐        │
  │              Swarm Pipeline               │        │
  │  ┌─────┐ ┌──────┐ ┌──────┐ ┌─────────┐   │        │
  │  │Life-│ │Event │ │Sync  │ │Orches-  │   │        │
  │  │cycle │ │Bus   │ │(Fence│ │trator   │   │        │
  │  └─────┘ └──────┘ │ Gates)│ │          │   │        │
  │                   └──────┘ └─────────┘   │        │
  └──────────────────────────────────────────┘        │
                        │                              │
          ┌─────────────┼───────────────────┐          │
          ▼             ▼                   ▼          │
  ┌────────────┐ ┌────────────┐ ┌────────────────┐    │
  │  Memory     │ │  Sandbox   │ │ Observability  │    │
  │ (Shared,    │ │ (AST,      │ │ (Metrics,SSE,  │    │
  │  Collective)│ │  Docker)   │ │  Diagnostics)  │    │
  └────────────┘ └────────────┘ └────────────────┘    │
                        │                              │
          ┌─────────────┴─────────────┐                 │
          ▼                           ▼                 │
  ┌────────────────┐     ┌──────────────────────┐      │
  │  Experiment/   │     │  Swarm Diagnostics    │      │
  │  Benchmark     │     │  (Dead/Degraded)      │      │
  └────────────────┘     └──────────────────────┘      │
                        │                              │
          ┌─────────────┴─────────────┐                 │
          ▼                           ▼                 │
  ┌──────────────┐          ┌──────────────────┐       │
  │  DB (SQL)    │          │  External         │       │
  │  PostgreSQL  │          │  LLM Providers    │       │
  │  + Neo4j(?)  │          │  (OpenAI,Anthro.) │       │
  │  + Redis(?)  │          │  + Tavily Search  │       │
  └──────────────┘          └──────────────────┘       │
                                                        │
  ┌────────────────────────────────────────────────────┐│
  │           Integrations (Tavily)                    ││
  └────────────────────────────────────────────────────┘│
```

### Pipeline: Agent Swarm Collaboration (Programming Course)

```
ENTERING → CONTEXT_LOADING → MEMORY_INIT → PEDAGOGICAL_ANALYSIS
    │            │               │               │
    ▼            ▼               ▼               ▼
ADAPTIVE_ADJUSTMENT → RISK_ASSESSMENT → CONSENSUS → INFERENCE
    │                    │               │            │
    ▼                    ▼               ▼            ▼
CONTENT_PRODUCTION → ACTIVE
```

### Pipeline: Pedagogical Orchestration (7-Agent Multimodal)

```
ResearchAgent → StructuralPedagogicalAgent → AdaptiveLearningAgent
    │                    │                           │
    ▼                    ▼                           ▼
MultimodalPlanningAgent → PromptEngineeringAgent → ConsistencyAgent
                                                      │
                                                      ▼
                                             ConsensusMediator
```

---

## 2. Module Dependency Map

### `app/api/` — API Layer
- **What**: FastAPI route handlers, Pydantic dependencies, middleware
- **Key files**:
  - `main.py` **← application entry point** — lifespan, middleware stack, router registration
  - `api/routes/*.py` — 17 route modules
  - `api/deps.py` — sync & async DI: DB sessions, UoW, auth guards (`get_current_user`, `aget_current_user`, etc.)
  - `api/middleware/query_tracing.py` — per-request SQL query counter
- **Depends on**: `app.core.security`, `app.db.session`, `app.db.uow`, `app.models`, `app.services.*`, `app.schemas.*`
- **Status**: Production

### `app/agents/` — Multi-Agent Swarm
- **What**: LangGraph agent nodes and standalone agent classes for educational reasoning
- **Key files**:
  - `base.py` — `BaseAgent` abstract class with tracing, diagnostics, shared memory integration
  - `graph.py` / `nodes.py` — LangGraph-based agent graph (legacy v1, 5-node pipeline)
  - `router.py` — FastAPI router (`/api/agents`): `analyze-diagnostic`, `generate-plan`, `generate-evaluation`
  - `pedagogical_agent.py`, `adaptive_agent.py`, `risk_agent.py`, `evaluation_agent.py` — legacy agents (programming pathway)
  - `research_agent.py`, `structural_pedagogical_agent.py`, `adaptive_learning_agent.py`, `multimodal_planning_agent.py`, `prompt_engineering_agent.py`, `consistency_agent.py`, `consensus_mediator.py` — new orchestration agents
  - `programming_graph.py`, `programming_nodes.py` — programming-course-specific LangGraph
  - `schemas.py`, `prompts.py`
- **Depends on**: `app.db.uow`, `app.memory.shared_memory`, `app.observability`, `app.tracing`, `app.swarm_diagnostics`
- **Status**: Production (new agents), Legacy (v1 LangGraph)

### `app/swarm/` — Swarm Lifecycle & Orchestration
- **What**: Core swarm pipeline — lifecycle phases, event bus, synchronization, anomaly detection
- **Key files**:
  - `orchestrator.py` — `SwarmOrchestrator`: 9-phase activation lifecycle (ENTRYING→ACTIVE)
  - `lifecycle.py` — `SwarmLifecycle`, `SwarmPhase`, `PhaseStatus`, phase timing
  - `events.py` — `SwarmEventBus`, `SwarmEventType`, causation chains
  - `synchronization.py` — `PhaseGate`, `SwarmFence`, `ContextLock`
  - `agent_factory.py` — `AgentFactory`: creates all agent instances with shared deps
  - `detectors.py` — Bottleneck, race condition, context inconsistency, propagation failure detectors
  - `metrics.py` — `SwarmActivationMetrics`
- **Depends on**: `app.agents.*`, `app.core.consensus`, `app.core.specialization`, `app.core.weighting`, `app.memory.*`, `app.models`, `app.services.*`, `app.observability`, `app.db.uow`
- **Status**: Production

### `app/core/` — Core Domain Logic
- **What**: Consensus engine, trust scoring, specialization tracking, weighting, circuit breaker
- **Key files**:
  - `config.py` — `Settings` (pydantic-settings): env-driven configuration
  - `consensus.py` — `ConsensusEngine`, `VoteContext`, V1 voters (Mastery, Prereq, Sequence, Time)
  - `programming_voters.py` — `CodeMasteryVoter`, `ProgressionVoter` (programming-specific)
  - `trust.py` — Trust scoring, decay, and aggregation
  - `weighting.py` — Dynamic weight computation
  - `specialization.py` — Specialization tracking per voter
  - `circuit_breaker.py` — Circuit breaker pattern for consensus
  - `consensus_cancellation.py`, `consensus_timeouts.py` — Timeout and cancellation support
  - `consensus_timeout_middleware.py`, `consensus_timeout_metrics.py` — Middleware/metrics
  - `security.py` — JWT token encoding/decoding
- **Depends on**: `app.models`, `app.db.uow`, `app.observability`
- **Status**: Production (core), `agent_health/` is Dead (see §5)

### `app/models/` — SQLAlchemy ORM Models
- **What**: All database entities (PostgreSQL)
- **Key files** (28 model files):
  - `user.py` — `User`, `UserRole`
  - `course.py`, `course_prerequisite.py` — Courses & prerequisites
  - `learning_objective.py`, `resource.py`, `resource_objective.py`
  - `enrollment.py`, `student_profile.py`, `student_progress.py` — Student data
  - `diagnostic_result.py`, `evaluation_attempt.py` — Assessment
  - `competency.py` — Institutional competencies
  - `knowledge_graph.py` — Knowledge nodes & edges
  - `student_memory.py` — `StudentMemory`, `ConversationMessage`
  - `shared_memory_record.py` — Collective memory records
  - `educational_context.py` — Swarm context tracking
  - `programming_domain.py`, `programming_metrics.py`, `programming_prerequisite.py` — Programming-specific
  - `idempotency_key.py` — Idempotency infrastructure
  - `event_outbox.py` — Outbox pattern
  - `retrieval.py`, `audit_log.py`, `login_attempt.py`, `learning_session.py`
  - `institutional_course.py`, `teacher_assignment.py`
- **Depends on**: `app.db.base` (SQLAlchemy `DeclarativeBase`)
- **Status**: Production

### `app/schemas/` — Pydantic Models
- **What**: Request/response schemas for every API endpoint
- **Key files**: `auth.py`, `user.py`, `course.py`, `resource.py`, `objective.py`, `competency.py`, `curriculum.py`, `diagnostic.py`, `progress.py`, `evaluation.py`, `enrollment.py`, `prerequisite.py`, `pedagogical_orchestration.py`
- **Depends on**: Nothing (standalone Pydantic models)
- **Status**: Production

### `app/services/` — Business Logic Layer
- **What**: Service classes implementing all business logic — the thickest layer (~30 files)
- **Key files**:
  - `auth_service.py`, `user_service.py`, `course_service.py` — CRUD services
  - `student_service.py`, `session_service.py` — Student flow
  - `ai_service.py` — AI chat/tutor response generation
  - `analytics_service.py` — IA dashboards
  - `adaptive_service.py` — Adaptive learning unlocks & recommendations
  - `evaluation_service.py`, `exercise_generator_service.py` — Assessment generation
  - `pedagogical_orchestration_service.py` — 7-agent orchestration pipeline
  - `programming_course_service.py`, `programming_pathway_service.py`, `programming_metrics_service.py` — Programming-specific
  - `cognitive_stage_service.py`, `ct_progression_service.py` — CT progression
  - `knowledge_graph_service.py` — Knowledge graph (prerequisite edges)
  - `memory_service.py` — Tutor conversation memory
  - `streaming_service.py` — SSE streaming for tutor
  - `multimodal_service.py`, `multimodal_generation_config.py` — Multimodal content
  - `swarm_activation_service.py`, `activation_service.py` — Activation entry points
  - `resource_service.py`, `competency_service.py`, `curriculum_service.py`, `prerequisite_service.py`
  - `audit_service.py`, `auth_tracing.py`
  - `explanation_service.py` — Algorithm explanation generator
- **Depends on**: `app.models`, `app.schemas`, `app.db.uow`, `app.core.config`, `app.llm.*`
- **Status**: Production

### `app/events/` — Enterprise Event Infrastructure
- **What**: Outbox pattern, idempotency, dedup, replay, TLS propagation, TTL guards
- **Key files**:
  - `outbox.py` — `OutboxService`, transactional outbox
  - `idempotency.py` — `IdempotencyService`, key generation, conflict detection
  - `dedup.py` — `DedupEventBus`, `IdempotentConsumer`, `ReplayGuard`
  - `distributed.py` — `DistributedDedupEngine` (cross-process 3-layer dedup)
  - `integration.py` — Wrappers for shared memory, consensus, unit-of-work
  - `middleware.py` — `make_idempotency_middleware` for FastAPI
  - `propagation_ttl.py` — TTL, depth limits, anti-feedback-loop, DAG cycle detection
  - `replay.py` — `EventReplayService` for safe outbox replay
  - `retry.py` — `RetryHandler`, `CircuitBreaker` with exponential backoff
  - `risk_detectors.py` — Consistency, race, replay, duplicate risk analysis
  - `types.py` — Event type definitions
- **Depends on**: `app.db.*`, `app.models`, `app.core.config`
- **Status**: Production (actively used in middleware)

### `app/llm/` — LLM Integration
- **What**: Unified multi-provider LLM service, prompt management, voters
- **Key files**:
  - `service.py` — `LLMService`: async provider abstraction (OpenAI, Anthropic, OpenAI-compatible)
  - `config.py` — `LLMConfig`, `ProviderKind`
  - `cost_tracker.py` — `TokenBudgetTracker` (per-voter budget control)
  - `confidence.py`, `grounding.py`, `deliberation.py` — Advanced LLM features
  - `metrics.py` — LLM call metrics
  - `response_parser.py` — JSON extraction from LLM responses
  - `prompts/` — Prompt templates: `pedagogical.py`, `evaluation.py`, `adaptive.py`, `deliberation.py`
  - `voters/` — LLM-based voters for consensus: `base.py`, `adaptive.py`, `evaluation.py`, `pedagogical.py`, `mediator.py`
- **Depends on**: `httpx`, `openai`, `anthropic`
- **Status**: Production

### `app/memory/` — Collective Memory
- **What**: Shared memory store, collective inference engine, pattern detection
- **Key files**:
  - `shared_memory.py` — `SharedMemoryStore`: publish/query/lineage on `SharedMemoryRecord`
  - `collective_inference.py` — `CollectiveInferenceEngine` for decentralized reasoning
  - `memory_rules.py` — Confidence computation, TTL, observation merging, conflict resolution
  - `patterns.py` — `PatternDetector`
- **Depends on**: `app.db.uow`, `app.models.shared_memory_record`, `app.observability.tracing`
- **Status**: Production

### `app/sandbox/` — Code Execution Sandbox
- **What**: Hardened Python code execution with 5-layer defense
- **Key files**:
  - `executor.py` — `SandboxExecutor`: unified interface, Docker primary + subprocess fallback
  - `ast_policy.py` — `ASTSafetyPolicy`: static analysis, blocklist of dangerous calls
  - `docker_manager.py` — `DockerManager`: container lifecycle, `ContainerSpec`, `ContainerResult`
  - `security_monitor.py` — `SecurityMonitor`: violation tracking
  - `cleanup.py` — `CleanupManager`: orphan container prevention
  - `metrics.py` — Sandbox metrics collection
  - `exceptions.py` — `SandboxError`, `SandboxTimeout`, `SandboxSecurityViolation`, `classify`
- **Depends on**: `docker` (Python SDK), `asyncio`, `resource`
- **Status**: Production

### `app/observability/` — Metrics & Real-Time Monitoring
- **What**: Prometheus metrics exporter, SSE real-time stream, swarm diagnostics timeline
- **Key files**:
  - `metrics_exporter.py` — `MetricsExporter`: counters, gauges, histograms, Prometheus text format
  - `stream.py` — `MetricsStream`: SSE fan-out to dashboard clients
  - `swarm_diagnostics.py` — `SwarmDiagnostics`: decision timeline + event chain tracking
  - `consensus_metrics.py` — `ConsensusMetrics`: in-process counters
  - `tracing.py` — Trace context helpers
- **Depends on**: `app.core.config`, in-process memory
- **Status**: Production

### `app/tracing/` — Distributed Tracing
- **What**: Correlation engine, span propagation, LangGraph tracing, FastAPI middleware
- **Key files**:
  - `engine.py` — `CorrelationEngine`: span tree, causation chains
  - `models.py` — `PropagationContext`, `SpanContext`, `CorrelationContext`, `Baggage`
  - `fastapi.py` — `make_tracing_middleware`, `instrument_app`
  - `langgraph.py` — `trace_langgraph_node`, `TracingLangGraph`
  - `propagation.py` — Header sanitization, `TraceLoggingFilter`, propagation guard
- **Depends on**: `app.core.config`
- **Status**: Production

### `app/db/` — Database Infrastructure
- **What**: SQLAlchemy session factories, Unit of Work, query counter, locks
- **Key files**:
  - `base.py` — `Base` (SQLAlchemy `DeclarativeBase`)
  - `session.py` — `engine`, `async_engine`, `SessionLocal`, `AsyncSessionLocal`
  - `uow.py` — `UnitOfWork`, `AsyncUnitOfWork`
  - `locks.py` — Advisory locks
  - `query_counter.py` — N+1 query detection
- **Depends on**: `app.core.config`, SQLAlchemy
- **Status**: Production

### `app/experiment/` — Experiment Isolation System
- **What**: Scientific experiment framework for ablation studies, benchmark execution, statistical analysis
- **Key files**:
  - `context.py` — `ExperimentContext`, `ExperimentRegistry`, isolation containers
  - `conditions.py` — 5 experimental conditions (FULL_SWARM, UNIFORM_WEIGHTS, SINGLE_AGENT, NO_TRUST, NO_SPECIALIZATION)
  - `pipelines.py` — `BatchPipeline`, `SingleAgentPipeline`
  - `metrics.py` — Per-run and aggregated metrics extraction
  - `analysis.py` — ANOVA, pairwise Bonferroni/Holm, Cohen's d, power analysis
  - `orchestrator.py` — `ExperimentOrchestrator`: multi-condition runner
  - `dataset.py` — Ground truth dataset, synthetic data generation
  - `evaluation.py` — Fleiss' Kappa, expert agreement protocol
  - `config.py`, `anomaly.py`, `export.py`, `report.py`, `replay.py`, `reset.py`
  - `benchmark/` — Academic benchmark system:
    - `orchestrator.py`, `conditions.py`, `scenarios.py`, `metrics.py`, `statistics.py`, `exports.py`, `visualization.py`
    - `real/` — Real swarm pipeline execution benchmark: `runner.py`, `executor.py`, `mapper.py`, `safety.py`, `noop_memory.py`
- **Depends on**: `app.core.*`, `app.swarm.*`, `app.services.*`, `app.agents.*`, `app.memory.*`
- **Status**: Production (experiment framework), Academic (benchmark suite)

### `app/bug_reports/` — Bug Report Generator
- **What**: Auto-generated bug reports from diagnostics signals
- **Key files**: `generator.py`, `models.py`, `diagnostics_integration.py`, `markdown_writer.py`, `regression.py`
- **Depends on**: `app.swarm_diagnostics`
- **Status**: Production (wired in lifespan via BugDiagnosticsBridge hook)

### `app/integrations/` — External Service Integrations
- **What**: Third-party API clients (currently only Tavily search)
- **Key files**:
  - `tavily/client.py` — HTTP client for Tavily Search API
  - `tavily/retrieval.py` — Search result retrieval
  - `tavily/cache.py`, `tavily/rate_limit.py`, `tavily/observability.py`, `tavily/errors.py`, `tavily/schemas.py`
- **Depends on**: `httpx`, `app.observability`
- **Status**: Production

### `app/swarm_diagnostics/` — Enterprise Swarm Observability (DEAD — see §5)

### `app/middleware/` — FastAPI Middleware
- **What**: Rate limiting, idempotency middleware
- **Key files**: `rate_limit.py`, `idempotency.py`
- **Depends on**: `app.core.config`, `app.events.*`
- **Status**: Production

---

## 3. Data Flow

### API Request → Response Flow

```
HTTP Request
  │
  ▼
TracingMiddleware (correlation_engine → trace_id, span_id)
  │
  ▼
IdempotencyMiddleware (Idempotency-Key extraction + lock)
  │
  ▼
AuthRateLimitMiddleware (IP-based sliding window for /api/auth/login)
  │
  ▼
QueryTracingMiddleware (SQL query count per request)
  │
  ▼
RequestIDMiddleware (X-Request-ID header)
  │
  ▼
LogRequestsMiddleware (method, path, status, duration)
  │
  ▼
CORSMiddleware
  │
  ▼
Route Handler → Depends(get_db/aget_db, get_current_user/aget_current_user)
  │
  ├──→ Sync endpoint: SessionLocal + UnitOfWork.commit()
  └──→ Async endpoint: AsyncSessionLocal + AsyncUnitOfWork.commit()
  │
  ▼
Service Layer → Business logic → Models (SQLAlchemy)
  │
  ▼
PostgreSQL (sync via psycopg, async via asyncpg)
  │
  ▼
JSONResponse ← Serialized via Pydantic schema
```

### Agent Swarm Collaboration Flow

```
Student enters a module
  │
  ▼
POST /api/sessions/module/{module_id}/enter
  │
  ▼
SwarmActivationService
  │
  ▼
SwarmOrchestrator.activate() [acquires ContextLock]
  │
  ▼
  Phase 1: ENTERING          → Verify enrollment
  Phase 2: CONTEXT_LOADING   → Load profile, diagnostic, strengths/weaknesses
  Phase 3: MEMORY_INIT       → Publish baseline to SharedMemoryStore
  Phase 4: PEDAGOGICAL_ANALYSIS → PedagogicalAgent.analyze() (or skip if not programming)
  Phase 5: ADAPTIVE_ADJUSTMENT  → AdaptiveAgent.analyze()
  Phase 6: RISK_ASSESSMENT      → RiskAgent.analyze()
  Phase 7: CONSENSUS            → ConsensusEngine.run() with 4-6 voters
  Phase 8: INFERENCE            → CollectiveInferenceEngine.infer() + PatternDetector
  Phase 9: CONTENT_PRODUCTION   → EvaluationAgent.analyze()
  Phase 10: ACTIVE              → Set context to ACTIVE
  │
  ▼
  Phase Gates (precondition checks between phases)
  │
  ▼
  SwarmEventBus publishes events with causation chains
  │
  ▼
  Anomaly detection runs after each phase (bottleneck, race, inconsistency, propagation)
  │
  ▼
  Result returned: { ok, lifecycle, phase_results, detected_anomalies, metrics }
```

### Pedagogical Orchestration Flow (7-Agent Multimodal Pipeline)

```
Teacher → POST /api/orchestrate/full  { topic, learning_objectives, ... }
  │
  ▼
PedagogicalOrchestrationService.orchestrate()
  │
  ├── 1. ResearchAgent.run()           → { findings, examples, analogies }
  ├── 2. StructuralPedagogicalAgent.run() → { structure, sequence }
  ├── 3. AdaptiveLearningAgent.run()   → { adaptations, personalization }
  ├── 4. MultimodalPlanningAgent.run() → { modalities, config }
  ├── 5. PromptEngineeringAgent.run()  → { prompts, instructions }
  ├── 6. ConsistencyAgent.run()        → { validation, conflicts }
  └── 7. ConsensusMediator.run()       → { final_result, summary }
  │
  ▼
  Each agent publishes observations to SharedMemoryStore
  │
  ▼
  Result: { ok, result: { content, structure, modalities, prompts, ... } }
```

### Benchmark Execution Flow

```
ExperimentOrchestrator.run_all_conditions()
  │
  ├── ExperimentContext is created for each run
  ├── reset_all_global_state() is called between runs
  │
  ├── For each ExperimentCondition (FULL_SWARM, SINGLE_AGENT, etc.):
  │     │
  │     ├── BatchPipeline executes scenarios
  │     ├── Each scenario: injects ground truth, runs swarm, records outputs
  │     ├── extract_metrics() → PerRunMetrics
  │     │
  │     └── Aggregate across runs → AggregatedMetrics
  │
  ├── Statistical analysis:
  │     ├── compute_anova() → F-statistic, p-value
  │     ├── pairwise_bonferroni() / pairwise_holm()
  │     ├── cohens_d() → effect size
  │     └── power_analysis()
  │
  ├── Expert evaluation: fleiss_kappa(), agreement_matrix()
  │
  └── Export: CSV / JSON / LaTeX / Markdown reports
```

### Sandbox Execution Flow

```
Caller → SandboxExecutor.execute(code, stdin)
  │
  ├── Layer 1: ASTSafetyPolicy.validate(code)
  │     ├── Valid? → Continue
  │     └── Invalid? → Return violation result immediately
  │
  ├── Layer 2 (Primary): DockerManager.execute(spec)
  │     ├── Docker available? → Execute in container, return result
  │     └── Docker unavailable? → Fall through
  │
  ├── Layer 3 (Fallback): SubprocessSandbox.execute(code, stdin)
  │     ├── Subprocess with resource limits
  │     ├── Timeout via asyncio.wait_for + SIGKILL
  │     └── Memory limits via setrlimit(RLIMIT_AS)
  │
  ├── Layer 4: SecurityMonitor.record_violation() (if applicable)
  │
  ├── Layer 5: CleanupManager (always destroy containers)
  │
  └── Return: { exec_id, success, stdout, stderr, error, violation, ... }
```

---

## 4. Route Map

### System
| Method | Path | File | Handler |
|--------|------|------|---------|
| GET | `/` | `main.py:303` | `root()` |
| GET | `/health` | `main.py:313` | `health_check()` |

### Auth (`/api/auth`)
| Method | Path | Handler |
|--------|------|---------|
| POST | `/api/auth/login` | `login()` |
| POST | `/api/auth/logout` | `logout()` |
| POST | `/api/auth/refresh` | `refresh_token()` |
| POST | `/api/auth/recover` | `recover_password()` |
| GET | `/api/auth/me` | `get_me()` |

### Users (`/api/users`)
| Method | Path | Handler |
|--------|------|---------|
| GET | `/api/users` | `list_users()` |
| POST | `/api/users` | `create_user()` |
| POST | `/api/users/bulk-import` | `bulk_import()` |
| GET | `/api/users/export-csv` | `export_users_csv()` |
| GET | `/api/users/me` | `get_me()` |
| PUT | `/api/users/me` | `update_me()` |
| GET | `/api/users/{user_id}` | `get_user()` |
| PUT | `/api/users/{user_id}` | `update_user()` |
| DELETE | `/api/users/{user_id}` | `delete_user()` |
| PATCH | `/api/users/{user_id}/role` | `change_role()` |
| POST | `/api/users/{user_id}/deactivate` | `deactivate_user()` |
| POST | `/api/users/{user_id}/activate` | `activate_user()` |

### Courses (`/api/courses`)
| Method | Path | Handler |
|--------|------|---------|
| GET | `/api/courses` | `list_courses()` |
| POST | `/api/courses` | `create_course()` |
| GET | `/api/courses/{course_id}` | `get_course()` |
| PUT | `/api/courses/{course_id}` | `update_course()` |
| DELETE | `/api/courses/{course_id}` | `delete_course()` |
| POST | `/api/courses/{course_id}/publish` | `publish_course()` |
| GET | `/api/courses/{course_id}/enrolled-students` | `list_enrolled_students()` |
| POST | `/api/courses/{course_id}/enroll` | `enroll_student()` |
| DELETE | `/api/courses/{course_id}/enroll/{student_id}` | `remove_student()` |

### Resources
| Method | Path | File | Handler |
|--------|------|------|---------|
| POST | `/api/courses/{course_id}/resources` | `resources.py` | `upload_resource()` |
| GET | `/api/resources/{resource_id}` | `resources.py` | `get_resource()` |
| GET | `/api/resources/{resource_id}/download` | `resources.py` | `download_resource()` |
| DELETE | `/api/resources/{resource_id}` | `resources.py` | `delete_resource()` |
| POST | `/api/resources/{resource_id}/objectives` | `resources.py` | `associate_objectives()` |

### Learning Objectives
| Method | Path | File | Handler |
|--------|------|------|---------|
| GET | `/api/courses/{course_id}/objectives` | `objectives.py` | `list_objectives()` |
| POST | `/api/courses/{course_id}/objectives` | `objectives.py` | `create_objective()` |
| PUT | `/api/objectives/{objective_id}` | `objectives.py` | `update_objective()` |
| DELETE | `/api/objectives/{objective_id}` | `objectives.py` | `delete_objective()` |

### Competencies (`/api/competencies`)
| Method | Path | Handler |
|--------|------|---------|
| GET | `/api/competencies` | `list_competencies()` |
| GET | `/api/competencies/institutional` | `list_institutional_competencies()` |
| POST | `/api/competencies` | `create_competency()` |
| POST | `/api/competencies/course/{course_id}` | `assign_course_competencies()` |
| DELETE | `/api/competencies/{competency_id}` | `delete_competency()` |

### Curriculum (`/api/curriculum`)
| Method | Path | Handler |
|--------|------|---------|
| GET | `/api/curriculum/cycles` | `list_cycles()` |
| GET | `/api/curriculum/cycles/{cycle}` | `get_cycle()` |
| GET | `/api/curriculum/courses` | `list_institutional_courses()` |
| GET | `/api/curriculum/courses/{course_id}` | `get_institutional_course()` |
| POST | `/api/curriculum/teacher-assignments` | `create_teacher_assignment()` |
| GET | `/api/curriculum/teacher-assignments` | `list_teacher_assignments()` |

### Estudiantes (Legacy) (`/api/estudiante`)
| Method | Path | Handler |
|--------|------|---------|
| POST | `/api/estudiante/diagnostic/{course_id}` | `submit_diagnostic()` |
| GET | `/api/estudiante/diagnostic/{course_id}` | `get_diagnostic()` |
| GET | `/api/estudiante/learning-path/{course_id}` | `get_learning_path()` |
| PUT | `/api/estudiante/module/{module_id}` | `update_module()` |
| POST | `/api/estudiante/evaluate/{module_id}` | `submit_evaluation()` |

### Students (`/api/students`)
| Method | Path | Handler |
|--------|------|---------|
| POST | `/api/students/profile` | `create_profile()` |
| GET | `/api/students/profile` | `get_profile()` |
| POST | `/api/students/diagnostic/{course_id}` | `submit_diagnostic()` |
| GET | `/api/students/diagnostic/{course_id}` | `get_diagnostic()` |
| GET | `/api/students/learning-path/{course_id}` | `get_learning_path()` |
| GET | `/api/students/learning-path/{course_id}/detail` | `get_learning_path_detail()` |
| PUT | `/api/students/module/{module_id}` | `update_module()` |
| POST | `/api/students/evaluate/{module_id}` | `submit_evaluation()` |
| GET | `/api/students/progress` | `get_all_progress()` |
| GET | `/api/students/progress/{course_id}` | `get_course_progress()` |
| GET | `/api/students/cycle` | `get_cycle()` |
| PUT | `/api/students/cycle` | `update_cycle()` |
| POST | `/api/students/tutor` | `tutor_chat()` |
| POST | `/api/students/progress` | `initialize_progress()` |
<!-- students.py has several more endpoints -->

### Analytics (`/api/analytics`)
| Method | Path | Handler |
|--------|------|---------|
| GET | `/api/analytics/dashboard` | `ia_dashboard()` |
| GET | `/api/analytics/course-access/{course_id}` | `get_course_access()` |
| GET | `/api/analytics/curriculum-status` | `get_curriculum_status()` |
| GET | `/api/analytics/risk-prediction` | `get_risk_prediction()` |

### Tutor (`/api/tutor`)
| Method | Path | Handler |
|--------|------|---------|
| POST | `/api/tutor/chat` | `tutor_chat()` |
| POST | `/api/tutor/chat/stream` | `tutor_chat_stream()` (SSE) |
| GET | `/api/tutor/memory` | `get_memory()` |
| GET | `/api/tutor/history` | `get_history()` |
| POST | `/api/tutor/explain` | `explain_topic()` |
| GET | `/api/tutor/explain/algorithm/{algorithm}` | `explain_algorithm()` |
| GET | `/api/tutor/replan` | `get_replan()` |
| POST | `/api/tutor/module/{module_id}/complete` | `complete_module()` |
| GET | `/api/tutor/knowledge-graph` | `get_knowledge_graph()` |

### Agents (`/api/agents`)
| Method | Path | Handler |
|--------|------|---------|
| POST | `/api/agents/analyze-diagnostic` | `analyze_diagnostic()` |
| POST | `/api/agents/generate-plan` | `generate_plan()` |
| POST | `/api/agents/generate-evaluation` | `generate_evaluation()` |

### Swarm (`/api/swarm`)
| Method | Path | Handler |
|--------|------|---------|
| GET | `/api/swarm/health` | `swarm_health()` |
| GET | `/api/swarm/spans` | `list_tracing_spans()` |

### Sessions (`/api/sessions`)
| Method | Path | Handler |
|--------|------|---------|
| POST | `/api/sessions/module/{module_id}/enter` | `enter_module()` |
| GET | `/api/sessions/module/{module_id}/entry-data` | `get_entry_data()` |
| POST | `/api/sessions/end` | `end_session()` |
| GET | `/api/sessions/active` | `get_active_session()` |

### Orchestration (`/api/orchestrate`)
| Method | Path | Handler |
|--------|------|---------|
| POST | `/api/orchestrate/full` | `full_orchestration()` |
| POST | `/api/orchestrate/research` | `research_only()` |
| POST | `/api/orchestrate/config` | `update_multimodal_config()` |

### Observability (`/api/observability`)
| Method | Path | Handler |
|--------|------|---------|
| GET | `/api/observability/metrics` | `metrics_prometheus()` (Prometheus text) |
| GET | `/api/observability/metrics.json` | `metrics_json()` |
| GET | `/api/observability/stream` | `metrics_stream()` (SSE) |
| GET | `/api/observability/dashboard` | `dashboard()` (HTML) |
| GET | `/api/observability/swarm` | `swarm_summary()` |
| GET | `/api/observability/anomalies` | `list_anomalies()` |
| GET | `/api/observability/anomalies/{anomaly_id}` | `get_anomaly()` |
| GET | `/api/observability/anomalies/export` | `export_anomalies()` |
| GET | `/api/observability/anomalies/metrics` | `anomaly_metrics()` |
| GET | `/api/observability/timeline` | `timeline()` |
| GET | `/api/observability/lineage` | `lineage()` |
| POST | `/api/observability/reset` | `reset_metrics()` |

### Idempotency (`/api/idempotency`)
| Method | Path | Handler |
|--------|------|---------|
| GET | `/api/idempotency/status` | `idempotency_status()` |
| GET | `/api/idempotency/keys` | `list_keys()` |
| GET | `/api/idempotency/keys/{key}` | `get_key()` |
| POST | `/api/idempotency/cleanup` | `cleanup_expired()` |
| GET | `/api/idempotency/distributed` | `distributed_status()` |
| GET | `/api/idempotency/risk-report` | `risk_report()` |

### Debug (`/api/debug`)
| Method | Path | Handler |
|--------|------|---------|
| GET | `/api/debug/bug-reports` | `list_bug_reports()` |
| GET | `/api/debug/bug-reports/stats` | `bug_report_stats()` |
| GET | `/api/debug/bug-reports/{bug_id}` | `get_bug_report()` |

### Static
| Method | Path | Detail |
|--------|------|--------|
| GET | `/uploads` | StaticFiles mount for uploaded resources |
| GET | `/docs` | Swagger UI |
| GET | `/redoc` | ReDoc UI |
| GET | `/openapi.json` | OpenAPI spec |
| GET | `/api/observability/static/dashboard.html` | Dashboard alias |

---

## 5. Dead Zones

These directories contain code that is **not actively used** in the running application but is preserved for reference:

### `app/swarm_diagnostics/` — DEAD
- **Status**: Degraded / Unwired
- **Evidence**: The `diagnostics_engine` singleton is created at import time in
  `__init__.py` and is still imported in `app/agents/base.py` (for `_record_diagnostics`),
  `app/api/routes/swarm.py`, `app/api/routes/observability.py`, and `main.py` lifespan.
  However, most of its submodules are **not** wired into active code paths:
  - `detectors/` — 17+ specialized anomaly detectors (anomaly, circuit_breaker, conflict,
    consensus_timeout, dag_traversal, deadlock, degraded_agent, divergence, event_storm,
    hallucination, loops, propagation, propagation_storm, recursive_amplification,
    retry_storm, slow_agent, staleness, sync) — No active consumer calls these.
  - `middleware/fastapi.py` — Not installed in the middleware stack.
  - `pipeline/` — Event lineage and metrics pipeline not wired.
  - `alerts/` — Empty `__init__.py`, no rules engine implemented.
- **Replacements**: The in-swarm detectors (`app/swarm/detectors.py`) provide the
  actively-used bottleneck, race condition, context inconsistency, and propagation
  failure detection. Observability is provided by `app/observability/`.

### `app/core/agent_health/` — DEAD
- **Status**: Dead (never integrated)
- **Contents**: `adaptive_degradation.py`, `behavioral_baseline.py`,
  `collective_stability.py`, `health_scorer.py`, `health_score_voter.py`,
  `meta_monitor.py`, `models.py`, `monitor.py`
- **Evidence**: No imports from any other module. No route or service references it.
  The health monitoring role is partially covered by `app/swarm/metrics.py` and
  `app/observability/consensus_metrics.py`.
- **Recommendation**: Archived or removed in next cleanup.

### `app/models/deprecated/` — DOES NOT EXIST YET (but N/A)
- **Note**: No `app/models/deprecated/` directory was found. Model files in
  `app/models/` are all active. No deprecated models identified.

### Other Low-Usage / Zombie Code

| File | Status | Evidence |
|------|--------|----------|
| `app/agents/graph.py` + `nodes.py` | **Legacy** — The 5-node LangGraph (diagnostic_analyzer, path_planner, content_recommender, evaluation_generator, risk_analyzer) is still wired in `router.py` (`POST /api/agents/analyze-diagnostic`, `generate-plan`, `generate-evaluation`) but has been superseded by `SwarmOrchestrator` and the new 7-agent orchestration pipeline. | |
| `app/agents/prompts.py`, `programming_graph.py`, `programming_nodes.py`, `programming_prompts.py` | **Legacy** — Used only by the v1 LangGraph routes. New agents have their own prompt templates in `app/llm/prompts/`. | |
| `app/api/routes/estudiantes.py` | **Legacy** — Superseded by `students.py`. Both routes remain active but `estudiantes.py` endpoints have a Spanish prefix (`/api/estudiante`) while `students.py` uses English (`/api/students`). | |

---

## Architectural Notes

1. **Two Agent Systems coexist**:
   - **V1** (Legacy): LangGraph pipeline in `app/agents/graph.py` — 5 nodes, synchronous,
     exposed via `POST /api/agents/*`. Still functional but frozen.
   - **V2** (Current): `SwarmOrchestrator` in `app/swarm/orchestrator.py` — 9-phase async
     lifecycle with event bus, phase gates, anomaly detection. Used for programming
     course activation and the 7-agent pedagogical orchestration pipeline.

2. **Sync vs Async DB**: Both `SessionLocal` (sync, psycopg) and `AsyncSessionLocal`
   (async, asyncpg) coexist. Legacy routes use sync, new routes use async. Migration
   is in progress.

3. **Three Consensus Systems**:
   - `app/core/consensus.py` — Deterministic V1 engine (no LLM). Used in swarm activation.
   - `app/llm/voters/` — LLM-based voters for pedagogical orchestration.
   - `app/agents/consensus_mediator.py` — Agent-based consensus mediator.

4. **Idempotency is layered**: Event-level (outbox), request-level (FastAPI middleware),
   consumer-level (dedup bus), and distributed (cross-process dedup engine with Redis).

