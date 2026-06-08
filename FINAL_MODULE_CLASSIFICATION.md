# UPAO-MAS-EDU — Final Module Classification

Generated: 2026-06-02

## Summary Table

| Classification   | Count | Lines of Code |
|------------------|-------|---------------|
| PRODUCTION       | 133   | 27,406        |
| EXPERIMENTAL     | 55    | 10,848        |
| DEMO             | 26    | 7,215         |
| DEPRECATED       | 6     | 1,249         |
| REMOVABLE        | 3     | 477           |
| **Total**        | **223** | **47,195**   |

*Note: Total LOC counts exclude blank/comment-only `__init__.py` files and the `main.py` (330 LOC, PRODUCTION).*

---

## Classification Criteria

| Classification   | Definition |
|------------------|------------|
| **PRODUCTION**   | Wired in `main.py`, actively called at runtime, has test coverage |
| **EXPERIMENTAL** | New feature, partially integrated, may have tests but not yet in critical path |
| **DEMO**         | Used only by demo scripts (`scripts/`), not reachable from production HTTP |
| **DEPRECATED**   | Superseded by newer code, still present for backward compatibility |
| **REMOVABLE**    | Dead code — not imported by any production module, safe to delete |

---

## PRODUCTION (133 files, 27,406 LOC)

### `app/api/routes/` — API Route Handlers

| File | LOC | Justification | Dependencies (app modules) |
|------|-----|---------------|----------------------------|
| `api/routes/auth.py` | 162 | Login/logout/refresh endpoints wired in main.py | `deps`, `models.user`, `core.security`, `schemas.auth`, `services.auth_service`, `services.user_service` |
| `api/routes/users.py` | 213 | User CRUD wired in main.py | `deps`, `models.user`, `schemas.user`, `services.user_service`, `services.audit_service` |
| `api/routes/courses.py` | 221 | Course CRUD wired in main.py | `deps`, `models.user`, `schemas.course`, `services.course_service`, `services.audit_service` |
| `api/routes/resources.py` | 105 | Resource management wired in main.py | `deps`, `models.user`, `schemas.resource`, `services.course_service`, `services.resource_service`, `services.audit_service` |
| `api/routes/objectives.py` | 104 | Learning objectives CRUD wired in main.py | `deps`, `models.learning_objective`, `models.user`, `schemas.objective`, `services.course_service`, `services.audit_service` |
| `api/routes/students.py` | 418 | Full student flow wired in main.py | `deps`, `models.user`, `schemas.*`, `services.*` |
| `api/routes/competencies.py` | 77 | Competency management wired in main.py | `deps`, `models.user`, `schemas.competency`, `services.competency_service` |
| `api/routes/curriculum.py` | 115 | Institutional curriculum wired in main.py | `deps`, `models.user`, `schemas.curriculum`, `services.curriculum_service`, `services.audit_service` |
| `api/routes/analytics.py` | 60 | Student/teacher analytics wired in main.py | `deps`, `models.user`, `schemas.prerequisite`, `services.analytics_service`, `services.prerequisite_service`, `services.course_service` |
| `api/routes/tutor.py` | 221 | AI tutor streaming wired in main.py | `agents.prompts`, `deps`, `db.uow`, `models.user`, `services.ai_service`, `services.adaptive_service`, `services.*` |
| `api/routes/swarm.py` | 39 | Swarm diagnostics health endpoint wired in main.py | `swarm_diagnostics` |
| `api/routes/sessions.py` | 93 | Learning session management wired in main.py | `deps`, `models.user`, `services.session_service`, `services.audit_service` |
| `api/routes/idempotency.py` | 139 | Idempotency admin API wired in main.py | `db.session`, `events.idempotency`, `models.*` |
| `api/routes/debug_bug_reports.py` | 89 | Bug report inspection API wired in main.py | `bug_reports` |
| `api/routes/observability.py` | 780 | Metrics/streaming/dashboard API wired in main.py | `observability`, `swarm_diagnostics` |
| `api/routes/orchestration.py` | 172 | Pedagogical orchestration API wired in main.py | `deps`, `db.uow`, `models.user`, `schemas.pedagogical_orchestration`, `services.pedagogical_orchestration_service` |

### `app/api/` — API Infrastructure

| File | LOC | Justification | Dependencies (app modules) |
|------|-----|---------------|----------------------------|
| `api/__init__.py` | 1 | Package marker | (none) |
| `api/deps.py` | 228 | FastAPI DI deps (DB, UoW, auth) used by every route | `core.security`, `db.session`, `db.uow`, `models.user` |
| `api/routes/__init__.py` | 1 | Package marker | (none) |
| `api/middleware/__init__.py` | 0 | Package marker | (none) |
| `api/middleware/query_tracing.py` | 68 | N+1 query detection middleware wired in main.py | `db.query_counter` |

### `app/core/` — Core Infrastructure

| File | LOC | Justification | Dependencies (app modules) |
|------|-----|---------------|----------------------------|
| `core/__init__.py` | 1 | Package marker | (none) |
| `core/config.py` | 74 | Settings singleton used by main.py and every module | (none) |
| `core/security.py` | 124 | JWT/password hashing used by deps and auth service | `core.config` |
| `core/consensus.py` | 1,472 | Core consensus engine used by services, swarm, voters | `core.trust`, `core.weighting`, `core.specialization`, `core.circuit_breaker`, `core.consensus_cancellation`, `core.agent_health.*`, `observability.consensus_metrics`, `events.propagation_ttl`, `memory.memory_rules`, `models.programming_prerequisite` |
| `core/circuit_breaker.py` | 777 | Circuit breaker used by consensus and events | `core.config`, `swarm_diagnostics` |
| `core/trust.py` | 266 | Trust scoring used by consensus engine | `observability` |
| `core/weighting.py` | 109 | Weight strategies used by consensus | (none) |
| `core/specialization.py` | 201 | Agent specialization used by consensus | (none) |
| `core/consensus_cancellation.py` | 232 | Cancellation protocol used by consensus | `events.types` |
| `core/consensus_timeouts.py` | 952 | Timeout handling used by consensus | (none) |
| `core/consensus_timeout_metrics.py` | 243 | Timeout metrics used by consensus | (none) |
| `core/consensus_timeout_middleware.py` | 414 | Timeout middleware for consensus | `core.agent_health.*`, `core.consensus` |
| `core/programming_voters.py` | 209 | Programming-specific voters used by swarm activation | (none) |
| `core/agent_health/__init__.py` | 0 | Package marker | (none) |
| `core/agent_health/models.py` | 184 | Agent health data models | (none) |
| `core/agent_health/monitor.py` | 277 | Agent health monitor | `swarm_diagnostics`, `observability` |
| `core/agent_health/meta_monitor.py` | 265 | Meta-monitoring for agent health | (none) |
| `core/agent_health/adaptive_degradation.py` | 188 | Adaptive degradation for health | (none) |
| `core/agent_health/behavioral_baseline.py` | 107 | Behavioral baseline for agents | (none) |
| `core/agent_health/collective_stability.py` | 212 | Collective stability monitoring | `swarm_diagnostics` |
| `core/agent_health/health_scorer.py` | 150 | Health score calculation | (none) |
| `core/agent_health/health_score_voter.py` | 80 | Health score voting | `core.consensus` |

### `app/db/` — Database Layer

| File | LOC | Justification | Dependencies (app modules) |
|------|-----|---------------|----------------------------|
| `db/__init__.py` | 21 | Public exports | `db.session`, `db.uow`, `db.base`, `db.query_counter` |
| `db/session.py` | 73 | SQLAlchemy engine/session used by main.py | `core.config` |
| `db/base.py` | 10 | Declarative Base for all models | (none) |
| `db/uow.py` | 559 | Unit of Work pattern used by deps | `db.session` |
| `db/query_counter.py` | 135 | SQL query counter used by query_tracing middleware | (none) |
| `db/locks.py` | 200 | Distributed locks used by consensus | `swarm_diagnostics` |

### `app/models/` — SQLAlchemy ORM Models

| File | LOC | Justification | Dependencies (app modules) |
|------|-----|---------------|----------------------------|
| `models/__init__.py` | 57 | Exports all models | (all model modules) |
| `models/user.py` | 55 | User model used by every auth-dependent module | (none) |
| `models/course.py` | 66 | Course model | (none) |
| `models/learning_objective.py` | 31 | Learning objective model | (none) |
| `models/resource.py` | 51 | Resource model | (none) |
| `models/resource_objective.py` | 27 | Resource-objective association | (none) |
| `models/enrollment.py` | 47 | Enrollment model | (none) |
| `models/audit_log.py` | 31 | Audit log model | (none) |
| `models/login_attempt.py` | 30 | Login attempt model | (none) |
| `models/diagnostic_result.py` | 36 | Diagnostic result model | (none) |
| `models/student_progress.py` | 88 | Student progress model | (none) |
| `models/evaluation_attempt.py` | 36 | Evaluation attempt model | (none) |
| `models/competency.py` | 57 | Competency model | (none) |
| `models/student_profile.py` | 32 | Student profile model | (none) |
| `models/institutional_course.py` | 42 | Institutional course model | (none) |
| `models/teacher_assignment.py` | 24 | Teacher assignment model | (none) |
| `models/course_prerequisite.py` | 24 | Course prerequisite model | (none) |
| `models/student_memory.py` | 71 | Student memory model | (none) |
| `models/knowledge_graph.py` | 37 | Knowledge graph model | (none) |
| `models/idempotency_key.py` | 74 | Idempotency key model | (none) |
| `models/shared_memory_record.py` | 154 | Shared memory record model | (none) |
| `models/educational_context.py` | 66 | Educational context model | (none) |
| `models/programming_domain.py` | 127 | Programming domain model | (none) |
| `models/programming_prerequisite.py` | 71 | Programming prerequisite model | (none) |
| `models/programming_metrics.py` | 44 | Programming metrics model | (none) |
| `models/resource_programming_tag.py` | 32 | Resource programming tag model | (none) |
| `models/learning_session.py` | 42 | Learning session model | (none) |
| `models/retrieval.py` | 184 | Retrieval cache model | (none) |
| `models/event_outbox.py` | 88 | Event outbox model | (none) |

### `app/schemas/` — Pydantic Schemas

| File | LOC | Justification | Dependencies (app modules) |
|------|-----|---------------|----------------------------|
| `schemas/__init__.py` | 1 | Package marker | (none) |
| `schemas/auth.py` | 44 | Auth schemas used by auth route | (none) |
| `schemas/user.py` | 69 | User schemas used by users route | (none) |
| `schemas/course.py` | 80 | Course schemas used by courses route | (none) |
| `schemas/resource.py` | 32 | Resource schemas used by resources route | (none) |
| `schemas/objective.py` | 36 | Objective schemas used by objectives route | (none) |
| `schemas/diagnostic.py` | 44 | Diagnostic schemas used by estudiantes/students routes | (none) |
| `schemas/progress.py` | 86 | Progress schemas used by students route | (none) |
| `schemas/evaluation.py` | 22 | Evaluation schemas used by students route | (none) |
| `schemas/competency.py` | 58 | Competency schemas used by competencies route | (none) |
| `schemas/curriculum.py` | 40 | Curriculum schemas used by curriculum route | (none) |
| `schemas/prerequisite.py` | 58 | Prerequisite schemas used by analytics route | (none) |
| `schemas/enrollment.py` | 20 | Enrollment schemas used by courses route | (none) |
| `schemas/pedagogical_orchestration.py` | 166 | Orchestration schemas used by orchestration route | (none) |

### `app/services/` — Business Logic Services

| File | LOC | Justification | Dependencies (app modules) |
|------|-----|---------------|----------------------------|
| `services/__init__.py` | 1 | Package marker | (none) |
| `services/auth_service.py` | 158 | Auth logic used by auth route | `core.security`, `models.user`, `services.auth_tracing` |
| `services/user_service.py` | 242 | User CRUD used by users route | `models.user`, `schemas.user`, `services.audit_service` |
| `services/course_service.py` | 285 | Course CRUD used by multiple routes | `models.*`, `events.outbox` |
| `services/resource_service.py` | 195 | Resource management used by resources route | `models.*`, `core.config` |
| `services/student_service.py` | 792 | Student flow used by estudiantes/students routes | `models.*`, `schemas.*`, `services.*` |
| `services/evaluation_service.py` | 164 | Evaluation logic used by estudiantes route | `models.*`, `services.ai_service` |
| `services/audit_service.py` | 31 | Audit logging used by most routes | `models.audit_log` |
| `services/curriculum_service.py` | 146 | Curriculum logic used by curriculum route | `models.*`, `services.knowledge_graph_service` |
| `services/competency_service.py` | 81 | Competency logic used by competencies route | `models.*` |
| `services/analytics_service.py` | 79 | Analytics used by analytics route | `models.*` |
| `services/ai_service.py` | 154 | AI/LLM service used by tutor and evaluation routes | `core.config` |
| `services/adaptive_service.py` | 425 | Adaptive learning used by tutor route | `models.*`, `core.consensus`, `observability` |
| `services/session_service.py` | 176 | Session management used by sessions route | `models.*`, `services.*` |
| `services/activation_service.py` | 356 | Activation service used by student_service | `models.*`, `services.*`, `events.outbox` |
| `services/memory_service.py` | 317 | Memory service used by student_service | `models.*`, `memory.*` |
| `services/cognitive_stage_service.py` | 267 | Cognitive stage used by student_service | `models.*` |
| `services/ct_progression_service.py` | 244 | CT progression used by student_service | `models.*` |
| `services/programming_course_service.py` | 289 | Programming courses used by activation_service | `models.*` |
| `services/programming_metrics_service.py` | 201 | Programming metrics used by activation_service | `models.*` |
| `services/programming_pathway_service.py` | 240 | Programming pathway used by activation_service | `models.*`, `services.cognitive_stage_service` |
| `services/exercise_generator_service.py` | 250 | Exercise generation used by student_service | `models.*` |
| `services/explanation_service.py` | 202 | Explanation service used by tutor route | `models.*`, `services.ai_service` |
| `services/knowledge_graph_service.py` | 241 | Knowledge graph used by curriculum/student services | `models.*` |
| `services/prerequisite_service.py` | 623 | Prerequisite checking used by analytics route | `models.*` |
| `services/streaming_service.py` | 89 | SSE streaming used by tutor route | (none) |
| `services/swarm_activation_service.py` | 79 | Swarm activation used by student_service | `models.*`, `services.ai_service`, `memory.*`, `events.outbox` |
| `services/pedagogical_orchestration_service.py` | 203 | Pedagogical orchestration used by orchestration route | `agents.*`, `services.*`, `memory.*`, `events.*` |
| `services/multimodal_service.py` | 181 | Multimodal generation used by orchestration_service | `services.multimodal_generation_config` |
| `services/multimodal_generation_config.py` | 74 | Multimodal config used by multimodal_service | (none) |
| `services/auth_tracing.py` | 163 | Auth tracing used by auth_service | `swarm_diagnostics`, `tracing.*` |

### `app/agents/` — Multi-Agent System

| File | LOC | Justification | Dependencies (app modules) |
|------|-----|---------------|----------------------------|
| `agents/__init__.py` | 35 | Exports all agents, wired via router | `agents.base`, `agents.pedagogical_agent`, `agents.adaptive_agent`, `agents.risk_agent`, `agents.evaluation_agent`, `agents.structural_pedagogical_agent`, `agents.research_agent`, `agents.adaptive_learning_agent`, `agents.multimodal_planning_agent`, `agents.prompt_engineering_agent`, `agents.consistency_agent`, `agents.consensus_mediator` |
| `agents/router.py` | 126 | Agent endpoints wired in main.py | `deps`, `models.*`, `agents.graph`, `agents.schemas`, `schemas.diagnostic`, `services.*` |
| `agents/graph.py` | 121 | LangGraph definition used by router | `agents.nodes`, `agents.base`, `agents.pedagogical_agent`, `agents.adaptive_agent`, `agents.evaluation_agent`, `agents.risk_agent` |
| `agents/nodes.py` | 376 | LangGraph nodes used by graph | `agents.*`, `services.*`, `models.*` |
| `agents/schemas.py` | 46 | Agent data schemas used by router | (none) |
| `agents/base.py` | 255 | BaseAgent class used by all agents | `memory.*`, `swarm_diagnostics` |
| `agents/prompts.py` | 117 | Prompt templates used by tutor route | (none) |
| `agents/pedagogical_agent.py` | 135 | Legacy pedagogical agent used by graph | `agents.base`, `memory.*`, `services.*` |
| `agents/adaptive_agent.py` | 151 | Legacy adaptive agent used by graph | `agents.base`, `memory.*`, `services.*` |
| `agents/risk_agent.py` | 220 | Risk agent used by graph | `agents.base`, `services.*` |
| `agents/evaluation_agent.py` | 144 | Evaluation agent used by graph | `agents.base`, `services.*` |
| `agents/structural_pedagogical_agent.py` | 173 | New pedagogical agent used by orchestration | `agents.base`, `memory.*`, `schemas.pedagogical_orchestration` |
| `agents/research_agent.py` | 274 | Research agent used by orchestration | `agents.base`, `integrations.tavily.*`, `llm.service`, `llm.config` |
| `agents/adaptive_learning_agent.py` | 118 | New adaptive agent used by orchestration | `agents.base` |
| `agents/multimodal_planning_agent.py` | 170 | Multimodal planning agent used by orchestration | `agents.base`, `services.*` |
| `agents/prompt_engineering_agent.py` | 389 | Prompt engineering agent used by orchestration | `agents.base` |
| `agents/consistency_agent.py` | 366 | Consistency agent used by orchestration | `agents.base`, `memory.*` |
| `agents/consensus_mediator.py` | 171 | Consensus mediator used by orchestration | `agents.base` |

### `app/tracing/` — Distributed Tracing

| File | LOC | Justification | Dependencies (app modules) |
|------|-----|---------------|----------------------------|
| `tracing/__init__.py` | 23 | Exports correlation_engine singleton, wired in main.py | `tracing.engine`, `tracing.models`, `tracing.langgraph`, `tracing.fastapi`, `tracing.propagation` |
| `tracing/engine.py` | 275 | CorrelationEngine used by main.py | `swarm_diagnostics` |
| `tracing/models.py` | 212 | Tracing data models | `observability` |
| `tracing/fastapi.py` | 125 | FastAPI tracing middleware wired in main.py | `tracing.engine`, `tracing.propagation`, `swarm_diagnostics` |
| `tracing/propagation.py` | 153 | Header propagation used by main.py | (none) |
| `tracing/langgraph.py` | 97 | LangGraph tracing wrapper | `tracing.engine` |

### `app/events/` — Event System & Idempotency

| File | LOC | Justification | Dependencies (app modules) |
|------|-----|---------------|----------------------------|
| `events/__init__.py` | 126 | Exports all event modules | `events.outbox`, `events.idempotency`, `events.dedup`, `events.integration`, `events.distributed`, `events.retry`, `events.replay`, `events.risk_detectors`, `events.middleware`, `events.propagation_ttl` |
| `events/idempotency.py` | 385 | IdempotencyService used by routes | `models.*`, `events.outbox`, `events.dedup`, `events.types` |
| `events/middleware.py` | 178 | Idempotency middleware wired in main.py | `events.idempotency` |
| `events/outbox.py` | 163 | OutboxService used by services | `models.event_outbox`, `db.session` |
| `events/dedup.py` | 320 | DedupEventBus used by idempotency | `events.types` |
| `events/integration.py` | 393 | Idempotent wrappers for memory/consensus | `events.idempotency`, `events.dedup`, `memory.*` |
| `events/distributed.py` | 365 | Cross-process dedup | `models.*`, `events.dedup` |
| `events/retry.py` | 344 | RetryHandler with circuit breaker | `events.types` |
| `events/replay.py` | 327 | EventReplayService | `events.outbox`, `events.idempotency` |
| `events/risk_detectors.py` | 486 | Idempotency risk analysis | `events.types` |
| `events/propagation_ttl.py` | 722 | Propagation TTL with feedback-loop protection | `events.types` |
| `events/types.py` | 33 | Event type definitions | (none) |

### `app/middleware/` — HTTP Middleware

| File | LOC | Justification | Dependencies (app modules) |
|------|-----|---------------|----------------------------|
| `middleware/__init__.py` | 0 | Package marker | (none) |
| `middleware/rate_limit.py` | 87 | Auth rate-limiting middleware wired in main.py | `core.config` |
| `middleware/idempotency.py` | 130 | Idempotency key propagation middleware | (none) |

### `app/observability/` — Observability System

| File | LOC | Justification | Dependencies (app modules) |
|------|-----|---------------|----------------------------|
| `observability/__init__.py` | 27 | Exports singletons, wired in main.py | `observability.metrics_exporter`, `observability.stream`, `observability.swarm_diagnostics`, `observability.consensus_metrics` |
| `observability/metrics_exporter.py` | 454 | Prometheus/JSON metrics exporter | (none) |
| `observability/stream.py` | 131 | SSE metrics stream | (none) |
| `observability/swarm_diagnostics.py` | 248 | Swarm diagnostics timeline/chain | (none) |
| `observability/consensus_metrics.py` | 170 | In-process consensus counters | (none) |
| `observability/tracing.py` | 172 | Trace context management | (none) |

### `app/bug_reports/` — Bug Report Automation

| File | LOC | Justification | Dependencies (app modules) |
|------|-----|---------------|----------------------------|
| `bug_reports/__init__.py` | 35 | Exports all modules, wired in main.py lifecycle | `bug_reports.models`, `bug_reports.generator`, `bug_reports.markdown_writer`, `bug_reports.regression`, `bug_reports.diagnostics_integration` |
| `bug_reports/models.py` | 233 | Bug report data models | (none) |
| `bug_reports/generator.py` | 297 | Bug report generator | `bug_reports.models`, `bug_reports.markdown_writer` |
| `bug_reports/markdown_writer.py` | 178 | Markdown report writer | `bug_reports.models` |
| `bug_reports/regression.py` | 187 | Regression tracker | `bug_reports.models` |
| `bug_reports/diagnostics_integration.py` | 291 | Bridge to swarm diagnostics, wired in main.py | `bug_reports.*`, `swarm_diagnostics` |

### `app/swarm/` — Swarm Orchestration Layer

| File | LOC | Justification | Dependencies (app modules) |
|------|-----|---------------|----------------------------|
| `swarm/__init__.py` | 28 | Exports all swarm modules | `swarm.lifecycle`, `swarm.orchestrator`, `swarm.events`, `swarm.synchronization`, `swarm.detectors`, `swarm.metrics`, `swarm.agent_factory` |
| `swarm/orchestrator.py` | 1,039 | SwarmOrchestrator used by services | `swarm.*`, `core.consensus`, `memory.*`, `events.*`, `observability` |
| `swarm/events.py` | 367 | SwarmEventBus used by orchestrator | `events.types` |
| `swarm/lifecycle.py` | 286 | Swarm lifecycle management | (none) |
| `swarm/synchronization.py` | 347 | Phase gates, fences, context locks | `swarm_diagnostics`, `observability` |
| `swarm/detectors.py` | 444 | Bottleneck/race/consistency detectors | (none) |
| `swarm/metrics.py` | 162 | Swarm activation metrics | (none) |
| `swarm/agent_factory.py` | 179 | AgentFactory used by swarm activation | `agents.*`, `memory.*` |

### `app/swarm_diagnostics/` — Enterprise Swarm Diagnostics

| File | LOC | Justification | Dependencies (app modules) |
|------|-----|---------------|----------------------------|
| `swarm_diagnostics/__init__.py` | 26 | diagnostics_engine singleton, wired in main.py | `swarm_diagnostics.core` |
| `swarm_diagnostics/core.py` | 419 | SwarmDiagnosticsEngine used by routes and services | `swarm_diagnostics.models.*`, `swarm_diagnostics.detectors.*`, `swarm_diagnostics.pipeline.*`, `swarm_diagnostics.alerts` |
| `swarm_diagnostics/models/__init__.py` | 3 | Exports diagnostic models | `swarm_diagnostics.models.diagnostic_event`, `swarm_diagnostics.models.anomaly_signal`, `swarm_diagnostics.models.health_snapshot` |
| `swarm_diagnostics/models/anomaly_signal.py` | 96 | Anomaly signal model | (none) |
| `swarm_diagnostics/models/diagnostic_event.py` | 43 | Diagnostic event model | (none) |
| `swarm_diagnostics/models/health_snapshot.py` | 43 | Health snapshot model | (none) |
| `swarm_diagnostics/detectors/__init__.py` | 27 | Detector exports | (all detector modules) |
| `swarm_diagnostics/detectors/base.py` | 36 | Base detector class | (none) |
| `swarm_diagnostics/detectors/propagation.py` | 95 | Propagation failure detector | (none) |
| `swarm_diagnostics/detectors/conflict.py` | 116 | Consensus conflict analyzer | (none) |
| `swarm_diagnostics/detectors/anomaly.py` | 105 | Behavior anomaly detector | (none) |
| `swarm_diagnostics/detectors/loops.py` | 109 | Delegation loop detector | (none) |
| `swarm_diagnostics/detectors/retry_storm.py` | 90 | Retry storm detector | (none) |
| `swarm_diagnostics/detectors/deadlock.py` | 99 | Deadlock detector | (none) |
| `swarm_diagnostics/detectors/staleness.py` | 85 | Stale memory monitor | (none) |
| `swarm_diagnostics/detectors/divergence.py` | 96 | Agent divergence detector | (none) |
| `swarm_diagnostics/detectors/event_storm.py` | 98 | Event storm detector | (none) |
| `swarm_diagnostics/detectors/sync.py` | 112 | Sync delay monitor | (none) |
| `swarm_diagnostics/detectors/propagation_storm.py` | 118 | Propagation storm detector | (none) |
| `swarm_diagnostics/detectors/recursive_amplification.py` | 145 | Recursive amplification detector | (none) |
| `swarm_diagnostics/detectors/dag_traversal.py` | 280 | DAG traversal pitfall detector | (none) |
| `swarm_diagnostics/detectors/consensus_timeout.py` | 443 | Hung consensus / cascading delay detectors | (none) |
| `swarm_diagnostics/detectors/circuit_breaker.py` | 453 | Circuit breaker anomaly detectors | (none) |
| `swarm_diagnostics/detectors/degraded_agent.py` | 114 | Degraded agent detector | (none) |
| `swarm_diagnostics/detectors/hallucination.py` | 182 | Hallucination detector | (none) |
| `swarm_diagnostics/detectors/slow_agent.py` | 161 | Slow agent detector | (none) |
| `swarm_diagnostics/pipeline/__init__.py` | 2 | Pipeline exports | `swarm_diagnostics.pipeline.metrics`, `swarm_diagnostics.pipeline.lineage` |
| `swarm_diagnostics/pipeline/metrics.py` | 151 | Swarm metrics collector | (none) |
| `swarm_diagnostics/pipeline/lineage.py` | 97 | Event lineage tracker | (none) |
| `swarm_diagnostics/middleware/fastapi.py` | 80 | FastAPI auto-instrumentation (not wired, available) | `swarm_diagnostics`, `observability.tracing` |
| `swarm_diagnostics/alerts/__init__.py` | 28 | Alert rules configuration | `swarm_diagnostics.models.anomaly_signal` |

### `app/memory/` — Shared Collective Memory

| File | LOC | Justification | Dependencies (app modules) |
|------|-----|---------------|----------------------------|
| `memory/__init__.py` | 40 | Exports memory modules | `memory.memory_rules`, `memory.shared_memory`, `memory.patterns`, `memory.collective_inference` |
| `memory/shared_memory.py` | 502 | SharedMemoryStore used by services and agents | `memory.memory_rules`, `models.shared_memory_record`, `events.*`, `observability` |
| `memory/memory_rules.py` | 248 | TTL/confidence/conflict rules used by shared_memory | (none) |
| `memory/patterns.py` | 396 | Pattern detection used by collective_inference | `memory.memory_rules` |
| `memory/collective_inference.py` | 379 | Collective inference used by services | `memory.patterns`, `memory.memory_rules` |

### `app/integrations/tavily/` — Tavily Search API

| File | LOC | Justification | Dependencies (app modules) |
|------|-----|---------------|----------------------------|
| `integrations/__init__.py` | 1 | Package marker | (none) |
| `integrations/tavily/__init__.py` | 38 | Exports Tavily modules | `integrations.tavily.client`, `integrations.tavily.cache`, `integrations.tavily.rate_limit`, `integrations.tavily.retrieval`, `integrations.tavily.schemas`, `integrations.tavily.errors` |
| `integrations/tavily/client.py` | 307 | Tavily HTTP client used by research_agent | `integrations.tavily.schemas`, `integrations.tavily.rate_limit`, `integrations.tavily.observability` |
| `integrations/tavily/cache.py` | 353 | Response cache used by research_agent | `integrations.tavily.schemas`, `observability` |
| `integrations/tavily/rate_limit.py` | 251 | Rate limiter used by client | `observability` |
| `integrations/tavily/retrieval.py` | 398 | Pedagogical retrieval strategy used by research_agent | `integrations.tavily.*`, `observability` |
| `integrations/tavily/schemas.py` | 221 | Data schemas for Tavily | (none) |
| `integrations/tavily/errors.py` | 51 | Tavily error types | (none) |
| `integrations/tavily/observability.py` | 191 | Tavily diagnostics used by client/retrieval | `observability` |

### `app/llm/` — LLM Infrastructure (core submodules)

| File | LOC | Justification | Dependencies (app modules) |
|------|-----|---------------|----------------------------|
| `llm/__init__.py` | 43 | Exports all LLM modules | (all llm submodules) |
| `llm/config.py` | 119 | LLM provider config used by research_agent | (none) |
| `llm/service.py` | 313 | LLMService used by research_agent and voter base | `llm.config`, `llm.cost_tracker` |
| `llm/cost_tracker.py` | 140 | Token budget tracking used by service | (none) |
| `llm/response_parser.py` | 130 | Response parsing used by voter base | (none) |

### `app/__init__.py`

| File | LOC | Justification | Dependencies (app modules) |
|------|-----|---------------|----------------------------|
| `__init__.py` | 1 | Package marker for `app` namespace | (none) |

### `app/main.py`

| File | LOC | Justification | Dependencies (app modules) |
|------|-----|---------------|----------------------------|
| `main.py` | 330 | FastAPI application entry point | `api.routes.*`, `agents.router`, `core.config`, `db.session`, `tracing.propagation`, `tracing.fastapi`, `tracing`, `events.middleware`, `middleware.rate_limit`, `api.middleware.query_tracing`, `swarm_diagnostics`, `bug_reports` |

---

## EXPERIMENTAL (55 files, 10,848 LOC)

### `app/llm/` — Advanced LLM Features (new hybrid cognition system)

| File | LOC | Justification | Dependencies (app modules) |
|------|-----|---------------|----------------------------|
| `llm/confidence.py` | 171 | Confidence calibration — not directly imported by production code | (none) |
| `llm/grounding.py` | 257 | Hallucination guard — used by voter base, but voters not yet in critical path | (none) |
| `llm/deliberation.py` | 480 | Multi-round deliberation — only used by experiment orchestrator | `llm.voters.*`, `llm.prompts.deliberation` |
| `llm/metrics.py` | 307 | Swarm metrics — only used by experiment orchestrator | `llm.deliberation` |
| `llm/voters/__init__.py` | 15 | Voter exports | `llm.voters.base`, `llm.voters.pedagogical`, `llm.voters.adaptive`, `llm.voters.evaluation`, `llm.voters.mediator` |
| `llm/voters/base.py` | 158 | HybridVoter base — not directly used in production path | `llm.service`, `llm.cost_tracker`, `llm.confidence`, `llm.grounding`, `llm.response_parser` |
| `llm/voters/pedagogical.py` | 74 | Pedagogical voter | `llm.prompts.pedagogical`, `llm.voters.base` |
| `llm/voters/adaptive.py` | 57 | Adaptive voter | `llm.prompts.adaptive`, `llm.voters.base` |
| `llm/voters/evaluation.py` | 78 | Evaluation voter | `llm.prompts.evaluation`, `llm.voters.base` |
| `llm/voters/mediator.py` | 57 | Mediator voter | `llm.prompts.deliberation`, `llm.voters.base` |
| `llm/prompts/__init__.py` | 24 | Prompt template exports | `llm.prompts.pedagogical`, `llm.prompts.adaptive`, `llm.prompts.evaluation`, `llm.prompts.deliberation` |
| `llm/prompts/pedagogical.py` | 50 | Pedagogical prompt templates | (none) |
| `llm/prompts/adaptive.py` | 53 | Adaptive prompt templates | (none) |
| `llm/prompts/evaluation.py` | 51 | Evaluation prompt templates | (none) |
| `llm/prompts/deliberation.py` | 77 | Deliberation prompt templates | (none) |

### `app/agents/` — Programming Pathway Agents (new feature, no production consumers)

| File | LOC | Justification | Dependencies (app modules) |
|------|-----|---------------|----------------------------|
| `agents/programming_graph.py` | 109 | Programming LangGraph — not imported by any production module | `agents.programming_nodes`, `agents.programming_prompts` |
| `agents/programming_nodes.py` | 253 | Programming LangGraph nodes — not imported outside programming_graph | (none) |
| `agents/programming_prompts.py` | 115 | Programming prompt templates — not imported outside programming_graph | (none) |

### `app/sandbox/` — Python REPL Sandbox (isolated, not wired into production)

| File | LOC | Justification | Dependencies (app modules) |
|------|-----|---------------|----------------------------|
| `sandbox/__init__.py` | 45 | Exports sandbox modules | `sandbox.ast_policy`, `sandbox.docker_manager`, `sandbox.executor`, `sandbox.security_monitor`, `sandbox.cleanup`, `sandbox.metrics`, `sandbox.exceptions` |
| `sandbox/ast_policy.py` | 345 | AST safety analysis — no production imports | (none) |
| `sandbox/docker_manager.py` | 384 | Docker container management — no production imports | `sandbox.exceptions` |
| `sandbox/executor.py` | 291 | SandboxExecutor — no production imports | `sandbox.ast_policy`, `sandbox.docker_manager`, `sandbox.security_monitor`, `sandbox.metrics` |
| `sandbox/security_monitor.py` | 85 | Security monitoring — no production imports | (none) |
| `sandbox/cleanup.py` | 109 | Orphan cleanup — no production imports | `sandbox.docker_manager` |
| `sandbox/metrics.py` | 57 | Sandbox metrics — no production imports | (none) |
| `sandbox/exceptions.py` | 94 | Sandbox exception types | (none) |

---

## DEMO (26 files, 7,215 LOC)

### `app/experiment/` — Experiment Isolation System (script-only)

| File | LOC | Justification | Dependencies (app modules) |
|------|-----|---------------|----------------------------|
| `experiment/__init__.py` | 204 | Exports all experiment modules, only imported by scripts | (all experiment submodules) |
| `experiment/context.py` | 392 | ExperimentContext — used by run_experiment.py | `experiment.conditions`, `experiment.reset`, `swarm_diagnostics`, `observability`, `core.consensus` |
| `experiment/reset.py` | 84 | Global state reset — used by context | `memory.*`, `observability`, `core.consensus` |
| `experiment/conditions.py` | 185 | Experiment conditions — used by scripts | `core.consensus` |
| `experiment/pipelines.py` | 351 | Execution pipelines — used by run_baseline_experiment.py | `experiment.*`, `core.consensus` |
| `experiment/metrics.py` | 377 | Per-run and aggregated metrics | (none) |
| `experiment/analysis.py` | 515 | Statistical analysis (ANOVA, Cohen's d, etc.) | (none) |
| `experiment/dataset.py` | 501 | Ground truth dataset generation | (none) |
| `experiment/evaluation.py` | 343 | Fleiss' Kappa, expert evaluation | (none) |
| `experiment/config.py` | 213 | Experiment configuration | (none) |
| `experiment/orchestrator.py` | 468 | Multi-condition experiment runner | `experiment.*`, `llm.deliberation`, `llm.metrics` |
| `experiment/anomaly.py` | 164 | Anomaly detection for experiment runs | (none) |
| `experiment/export.py` | 285 | CSV/JSON/LaTeX export | (none) |
| `experiment/report.py` | 274 | LaTeX/Markdown report generation | (none) |
| `experiment/replay.py` | 117 | Deterministic replay from snapshots | `experiment.config` |

### `app/experiment/benchmark/` — Academic Benchmark (script-only)

| File | LOC | Justification | Dependencies (app modules) |
|------|-----|---------------|----------------------------|
| `experiment/benchmark/__init__.py` | 70 | Exports benchmark modules | (all benchmark submodules) |
| `experiment/benchmark/conditions.py` | 183 | 6 benchmark conditions | (none) |
| `experiment/benchmark/scenarios.py` | 233 | Scenario generation | (none) |
| `experiment/benchmark/metrics.py` | 288 | 13 benchmark metrics | (none) |
| `experiment/benchmark/statistics.py` | 433 | Mann-Whitney U, McNemar, Cohen's d | (none) |
| `experiment/benchmark/orchestrator.py` | 255 | Benchmark orchestrator | `experiment.benchmark.*` |
| `experiment/benchmark/exports.py` | 549 | Report/CSV/LaTeX/JSON export | (none) |
| `experiment/benchmark/visualization.py` | 388 | Chart generation (matplotlib) | (none) |

### `app/experiment/benchmark/real/` — Real Swarm Benchmark (script-only)

| File | LOC | Justification | Dependencies (app modules) |
|------|-----|---------------|----------------------------|
| `experiment/benchmark/real/__init__.py` | 25 | Exports real benchmark modules | `experiment.benchmark.real.runner`, `experiment.benchmark.real.real_exports` |
| `experiment/benchmark/real/runner.py` | 193 | Real swarm execution runner | `experiment.benchmark.real.*`, `services.*`, `memory.*` |
| `experiment/benchmark/real/executor.py` | 240 | Per-condition executor | `experiment.benchmark.real.*`, `services.*`, `memory.*`, `agents.*` |
| `experiment/benchmark/real/mapper.py` | 167 | Condition-to-agent mapping | (none) |
| `experiment/benchmark/real/noop_memory.py` | 105 | No-op memory for ablation | `memory.*` |
| `experiment/benchmark/real/real_exports.py` | 204 | Real benchmark export formats | (none) |
| `experiment/benchmark/real/safety.py` | 149 | Safety wrappers for real execution | (none) |

---

## DEPRECATED (6 files, 1,249 LOC)

| File | LOC | Justification | Dependencies (app modules) |
|------|-----|---------------|----------------------------|
| `api/routes/estudiantes.py` | 145 | Superseded by `students.py`; marked "legacy" in tags, still wired for backward compat | `deps`, `models.user`, `schemas.*`, `services.*` |
| `agents/pedagogical_agent.py` | 135 | Superseded by `structural_pedagogical_agent.py`; marked "legacy" in `agents/__init__.py` | `agents.base`, `memory.*`, `services.*` |
| `agents/adaptive_agent.py` | 151 | Superseded by `adaptive_learning_agent.py`; marked "legacy" in `agents/__init__.py` | `agents.base`, `memory.*`, `services.*` |
| `agents/risk_agent.py` | 220 | Marked "legacy" in `agents/__init__.py`; kept for backward compatibility | `agents.base`, `services.*` |
| `agents/evaluation_agent.py` | 144 | Marked "legacy" in `agents/__init__.py`; kept for backward compatibility | `agents.base`, `services.*` |
| `agents/graph.py` | 121 | Legacy LangGraph definition using deprecated agents; superseded by programming/orchestration graphs | `agents.nodes`, `agents.base`, deprecated agents |

*Note: All DEPRECATED modules are still wired in production for backward compatibility. They should be migrated to their replacements and removed.*

---

## REMOVABLE (3 files, 477 LOC)

| File | LOC | Justification | Dependencies (app modules) |
|------|-----|---------------|----------------------------|
| `agents/programming_graph.py` | 109 | Not imported by any production module, script, or test. Self-contained dead code cluster. | `agents.programming_nodes`, `agents.programming_prompts` |
| `agents/programming_nodes.py` | 253 | Only imported by `programming_graph.py`. No production reachability. | (none) |
| `agents/programming_prompts.py` | 115 | Only imported by `programming_graph.py`. No production reachability. | (none) |

*Note: The `experiment/` package is DEMO (script-only), not REMOVABLE. The `sandbox/` package is EXPERIMENTAL — it has tests, a clean API, and is likely designed for future integration into the code execution pipeline.*

---

## Dependency Graph Summary

```
main.py
  ├── api/routes/* ──────────────────── deps, services, schemas
  ├── agents/router ─────────────────── agents/graph, agents/nodes, services
  ├── tracing/* ─────────────────────── (distributed tracing infrastructure)
  ├── events/middleware ─────────────── events/idempotency, events/outbox
  ├── middleware/rate_limit ─────────── (rate limiting)
  ├── api/middleware/query_tracing ──── db/query_counter
  ├── swarm_diagnostics ────────────── (diagnostics engine)
  ├── bug_reports ──────────────────── (bug report automation)
  └── core/config, db/session ──────── (foundation)

Production service tree:
  routes → services → models, core, memory, events
  agents → agents/* (base, nodes, legacy agents)
  orchestration route → services/pedagogical_orchestration_service → agents/* (new agents)

DEMO (scripts, unreachable from HTTP):
  scripts/* → experiment/* → core/consensus, llm/deliberation, llm/voters

EXPERIMENTAL (available but not in critical path):
  sandbox/* ─── isolated, self-contained
  llm/advanced ─── confidence, grounding, voters, prompts, deliberation
  agents/programming_* ─── dead code cluster (REMOVABLE)
```

---

## Recommendations

1. **Remove** `agents/programming_graph.py`, `programming_nodes.py`, `programming_prompts.py` (dead code, 477 LOC).
2. **Migrate** DEPRECATED legacy agents → new orchestration agents; remove legacy `agents/graph.py` and `agents/nodes.py` after migration.
3. **Integrate** `sandbox/` into the student code execution pipeline if needed; otherwise consider removal.
4. **Promote** `llm/voters/` and `llm/deliberation.py` to full PRODUCTION once the hybrid cognition system is wired into a production route.
5. **Archive** `experiment/` to a separate repository or remove from the production app container (it is only used by standalone scripts).
