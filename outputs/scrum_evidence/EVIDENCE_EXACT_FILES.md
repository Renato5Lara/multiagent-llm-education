# EVIDENCIA EXACTA — Mapeo de Archivos Reales a Apartados Semanales

Estructura exacta de carpetas y archivos del proyecto real para cada apartado de las Semanas 8 y 9.

---

## ═══════════════════════════════
## SEMANA 8 — Sprint 2
## ═══════════════════════════════

### 📁 1. Integración Tavily Retrieval

```
backend/app/integrations/tavily/
├── __init__.py
├── cache.py              ← Cache de consultas Tavily
├── client.py             ← Cliente HTTP para Tavily API
├── retrieval.py          ← PedagogicalRetrievalStrategy + _build_multimodal_prompts
└── schemas.py            ← QueryCategory, RetrievalResult, diversity_score, grounding_score

backend/app/integrations/__init__.py

backend/app/agents/research_agent.py    ← ResearchAgent (usa TavilyClient)
backend/app/core/config.py              ← TAVIL_API_KEY, has_tavily

backend/app/api/routes/
├── swarm.py              ← /api/swarm/memory (usa shared memory)
├── swarm_demo.py         ← /api/swarm/demo/run (usa research agent)
└── replay.py             ← /api/replay (usa retrieval events)

backend/tests/test_pedagogical_research_pipeline.py
backend/tests/test_fixes.py
backend/tests/test_config.py
```

**CAPTURAS SUGERIDAS:** retrieval.py (PedagogicalRetrievalStrategy), client.py (TavilyClient), schemas.py (QueryCategory), research_agent.py (ResearchAgent.research), config.py (TAVIL_API_KEY)

---

### 📁 2. Pedagogical Research Pipeline

```
backend/app/agents/research_agent.py       ← ResearchAgent con estrategias de retrieval
backend/app/integrations/tavily/retrieval.py ← PedagogicalRetrievalStrategy

backend/app/services/
├── pedagogical_orchestration_service.py   ← Orquestación pedagógica multiagente
└── module_orchestration_service.py        ← _build_multimodal_prompts

backend/app/weekly_learning/
├── __init__.py
├── orchestration.py       ← OrchestratorAgent, orchestrate_week
├── planner.py             ← WeeklyPlanner, _generate_prompts
├── models.py              ← WeeklyPlan (multimodal_prompts)
├── schemas.py             ← WeeklyPlan schemas
├── routes.py              ← API endpoints
├── validation.py          ← Validación de planes semanales
├── weekly_structure.py    ← Estructura semanal
└── progression.py         ← Progresión pedagógica

backend/tests/
├── test_pedagogical_research_pipeline.py
├── test_memory_wiring.py
├── test_adaptation.py
└── test_pedagogical_orchestration.py
```

**CAPTURAS SUGERIDAS:** research_agent.py (ResearchAgent), retrieval.py (build_pedagogical_queries), orchestration.py (orchestrate_week), planner.py (WeeklyPlanner)

---

### 📁 3. Shared Memory Narrativa

```
backend/app/memory/
├── __init__.py
├── shared_memory.py         ← SharedMemoryStore, SharedMemoryService
├── narrative_continuity.py  ← NarrativeContinuityEngine
├── pedagogical_memory.py    ← PedagogicalMemoryService, adaptation_metrics
├── collective_inference.py  ← CollectiveInferenceEngine
├── memory_rules.py          ← MemoryConsolidationRules
└── patterns.py              ← MemoryPatternDetector

backend/app/models/
├── shared_memory_record.py  ← SharedMemoryRecord ORM
└── student_memory.py        ← StudentMemory ORM

backend/app/api/routes/
├── swarm.py                 ← GET /api/swarm/memory
├── replay.py                ← GET /api/replay/student/{id}/memory
├── pedagogy.py              ← usa memory_store_from_session
└── students.py              ← usa memory_store_from_session

backend/app/replay/
├── session_replay.py        ← reconstrucción con memoria
└── memory_replay.py         ← MemoryReplay snapshots

backend/alembic/versions/
├── 0a1b2c3d4e5f_add_shared_memory.py
├── 3ba21248a301_merge_shared_memory_and_idempotency_.py
└── 8b9c0d1e2f3a_add_memory_and_knowledge_graph.py

frontend/src/components/swarm/
├── SharedMemoryReplay.tsx
├── MemoryInfluencePanel.tsx
├── NarrativeConsistencyPanel.tsx
└── CognitiveContinuityView.tsx

backend/tests/
├── test_shared_memory.py
├── test_memory_wiring.py
├── test_memory.py
└── test_adaptation.py
```

**CAPTURAS SUGERIDAS:** shared_memory.py (SharedMemoryStore), narrative_continuity.py, pedagogical_memory.py, SharedMemoryReplay.tsx, MemoryInfluencePanel.tsx

---

### 📁 4. SSE Observability

```
backend/app/observability/
├── __init__.py
├── tracing.py               ← TraceContext, TracingSpan
├── swarm_diagnostics.py     ← DecisionRecord, EventChainTracker, SwarmDiagnostics
└── consensus_metrics.py     ← ConsensusMetrics (approvals, rejections, latencies)

backend/app/api/routes/
├── swarm.py                 ← SSE streams for live events
├── replay.py                ← SSE event generator for replay
├── swarm_demo.py            ← SSE replay/stream endpoints
├── tutor.py                 ← SSE streaming tutor
└── sandbox.py               ← SSE observable execution

backend/app/demo/events.py   ← SSE event types, EventBus, fan-out

backend/app/benchmark/mermaid.py ← SSE observability diagram

frontend/src/
├── hooks/useDemoSSE.ts      ← Hook SSE para el demo
├── pages/demo/SwarmDemo.tsx ← EventSource SSE connection
└── pages/replay/ReplayDashboard.tsx ← SSE log viewer

backend/tests/
├── test_streaming.py
└── test_observability.py
```

**CAPTURAS SUGERIDAS:** swarm_diagnostics.py (DecisionRecord), consensus_metrics.py, useDemoSSE.ts, SwarmDemo.tsx (SSE connection), replay.py (SSE generator)

---

### 📁 5. Swarm Diagnostics

```
backend/app/swarm_diagnostics/
├── __init__.py
├── core.py                  ← SwarmDiagnosticsCore
├── alerts/__init__.py
├── detectors/
│   ├── __init__.py
│   ├── base.py              ← BaseDetector
│   ├── anomaly.py           ← AnomalyDetector
│   ├── circuit_breaker.py   ← CircuitBreakerDetector
│   ├── conflict.py          ← ContradictionAnalyzer
│   ├── consensus_timeout.py ← ConsensusTimeoutDetector
│   ├── dag_traversal.py     ← DAGTraversalDetector
│   ├── deadlock.py          ← DeadlockDetector
│   ├── degraded_agent.py    ← DegradedAgentDetector
│   ├── divergence.py        ← DivergenceDetector
│   ├── event_storm.py       ← EventStormDetector
│   ├── hallucination.py     ← HallucinationDetector
│   ├── loops.py             ← LoopDetector
│   ├── propagation.py       ← PropagationDetector
│   ├── propagation_storm.py ← PropagationStormDetector
│   ├── recursive_amplification.py ← RecursiveAmplificationDetector
│   ├── retry_storm.py       ← RetryStormDetector
│   ├── slow_agent.py        ← SlowAgentDetector
│   ├── staleness.py         ← StalenessDetector
│   └── sync.py              ← SyncDetector
├── middleware/fastapi.py    ← SwarmDiagnosticsMiddleware
├── models/
│   ├── __init__.py
│   ├── anomaly_signal.py    ← AnomalySignal
│   ├── diagnostic_event.py  ← DiagnosticEvent
│   └── health_snapshot.py   ← HealthSnapshot
└── pipeline/
    ├── __init__.py
    ├── lineage.py           ← PipelineLineage
    └── metrics.py           ← PipelineMetrics

docs/SWARM_INTELLIGENCE_ARCHITECTURE.md

backend/tests/
├── test_swarm_diagnostics.py
└── test_health_detectors.py
```

**CAPTURAS SUGERIDAS:** core.py (SwarmDiagnosticsCore), detectors/ (lista completa 20 archivos), base.py (BaseDetector), slow_agent.py (SlowAgentDetector.analyze)

---

### 📁 6. Contradictions y Misconceptions

```
backend/app/swarm_diagnostics/detectors/conflict.py  ← ContradictionAnalyzer

backend/app/api/routes/replay.py  ← misconception SSE events

frontend/src/
├── components/swarm/ContradictionViewer.tsx
├── hooks/useDemoSSE.ts           ← contradiction:detected, misconception:detected events
├── types/weeklyLearning.ts       ← misconception field
└── types/pedagogy.ts             ← misconception field

datasets/misconception_dataset.jsonl  ← Dataset de misconceptions

backend/tests/test_cognitive_replay.py  ← contradiction/misconception events tests
```

**CAPTURAS SUGERIDAS:** conflict.py (ContradictionAnalyzer), ContradictionViewer.tsx, misconception_dataset.jsonl (primeras líneas)

---

### 📁 7. Multimodal Prompt Generation

```
backend/app/services/
├── multimodal_service.py        ← MultimodalService (image/video/audio prompts)
├── pedagogical_orchestration_service.py  ← multimodal_planning
├── module_orchestration_service.py       ← _build_multimodal_prompts
└── explanation_service.py       ← multimodal explanations

backend/app/integrations/tavily/
├── retrieval.py                 ← _build_multimodal_prompts
└── schemas.py                   ← QueryCategory.MULTIMODAL

backend/app/agents/
├── visual_designer_agent.py     ← VisualDesignerAgent
└── research_agent.py            ← multimodal research

backend/app/weekly_learning/
├── orchestration.py             ← multimodal_prompts generation
├── planner.py                   ← _generate_prompts
├── models.py                    ← multimodal_prompts column
└── validation.py                ← missing_multimodal validator

backend/app/replay/timeline.py   ← prompt:generated timeline events
backend/app/demo/orchestrator.py ← multimodal prompts in demo

datasets/multimodal_pedagogical_tasks.jsonl
```

**CAPTURAS SUGERIDAS:** multimodal_service.py (MultimodalService), visual_designer_agent.py, schemas.py (QueryCategory.MULTIMODAL), multimodal_pedagogical_tasks.jsonl

---

### 📁 8. Dashboard Pedagógico

```
frontend/src/pages/investigador/Dashboard.tsx   ← Panel del Investigador

frontend/src/components/swarm/
├── PedagogicalStructurePanel.tsx  ← Estructura pedagógica
├── BloomProgressionView.tsx       ← Progresión Bloom
├── BloomDecisionView.tsx          ← Decisiones Bloom
├── LiveSessionFeed.tsx            ← Feed de sesión en vivo
├── ConsensusTimeline.tsx          ← Timeline de consenso
├── StudentEvolutionView.tsx       ← Evolución del estudiante
├── CognitiveLoadPanel.tsx         ← Carga cognitiva
├── CognitiveReplayView.tsx        ← Replay cognitivo
├── AdaptationEvolution.tsx        ← Evolución adaptativa
├── AdaptationReasoningPanel.tsx   ← Razonamiento adaptativo
└── ReplaySessionViewer.tsx        ← Visor de sesiones

frontend/src/hooks/usePedagogy.ts
frontend/src/types/pedagogy.ts

backend/app/explainability/bloom_explainer.py  ← BloomExplainer
backend/app/benchmark/mermaid.py               ← Diagramas Mermaid
backend/app/api/routes/swarm.py                ← SSE adaptation streams
```

**CAPTURAS SUGERIDAS:** InvestigadorDashboard.tsx, PedagogicalStructurePanel.tsx, BloomProgressionView.tsx, LiveSessionFeed.tsx, ConsensusTimeline.tsx

---

### 📁 9. Async Orchestration

```
backend/app/services/
├── module_orchestration_service.py     ← ModuleOrchestrationService
└── pedagogical_orchestration_service.py ← PedagogicalOrchestrationService

backend/app/weekly_learning/
├── orchestration.py                    ← OrchestratorAgent.plan_week
├── routes.py                           ← POST /api/weekly-learning/courses/{id}/plan
└── planner.py                          ← WeeklyPlanner

backend/app/api/routes/
├── students.py                         ← POST /api/students/module/{id}/orchestrate
├── pedagogy.py                         ← POST /api/pedagogy/weekly-plans/{id}/validate
└── estudiantes.py                      ← endpoints legacy

backend/tests/
├── test_memory_wiring.py               ← tests orquestación
└── test_pedagogical_orchestration.py   ← tests pedagógicos
```

**CAPTURAS SUGERIDAS:** module_orchestration_service.py (orchestrate_module), orchestration.py (orchestrate_week), students.py (orchestrate_module endpoint)

---

### 📁 10. Retrieval + Consenso

```
backend/app/integrations/tavily/
├── schemas.py              ← diversity_score, grounding_score, retrieval_confidence
└── retrieval.py            ← PedagogicalRetrievalStrategy con métricas

backend/app/agents/research_agent.py   ← diversity validations, consensus_payload

backend/app/core/
├── consensus.py            ← ConsensusEngine, shared memory integration
├── consensus_timeout_metrics.py       ← timeout metrics
├── consensus_timeouts.py             ← timeout handling
├── consensus_cancellation.py         ← consensus cancellation
├── consensus_timeout_middleware.py   ← timeout middleware
├── specialization.py                 ← agent specialization
├── trust.py                          ← trust scoring
└── weighting.py                      ← weighted voting

backend/app/benchmark/
├── metrics.py              ← grounding_score metric
└── runner.py               ← retrieval_grounding trace

backend/app/observability/consensus_metrics.py

frontend/src/components/swarm/
├── SourceDiversityPanel.tsx
├── PromptGroundingPanel.tsx
├── RetrievalTimeline.tsx
├── ConsensusTimeline.tsx
└── ReplayConsensusView.tsx

backend/tests/
├── test_consensus.py
└── test_consensus_timeouts.py
```

**CAPTURAS SUGERIDAS:** schemas.py (diversity_score, grounding_score), consensus.py (ConsensusEngine), trust.py (TrustStore), Specialization, SourceDiversityPanel.tsx, RetrievalTimeline.tsx

---

## ═══════════════════════════════
## SEMANA 9 — Hardening y Validación
## ═══════════════════════════════

### 📁 1. Sandbox Docker Aislado

```
backend/app/sandbox/
├── __init__.py
├── policy.py              ← SandboxPolicy, _PolicyVisitor, DENIED_IMPORT_ROOTS, DENIED_CALLS, DENIED_ATTRIBUTES
├── runner.py              ← SandboxRunner (docker-py, timeout, memory limit, --network none)
└── schemas.py             ← SandboxRequest, SandboxResult, SandboxLimits, SecurityViolation

backend/app/sandbox/docker/
├── Dockerfile             ← python:3.11-slim, sandbox user, read-only filesystem
└── runner_payload.py      ← In-container runner: restricted_import, blocked_call, validate(), AST check

backend/app/api/routes/sandbox.py  ← POST /api/sandbox/execute, POST /api/sandbox/execute/stream

frontend/src/components/swarm/SandboxValidationPanel.tsx

backend/tests/test_sandbox.py  ← 28 tests (policy, runner, security violations, hardening)
```

**CAPTURAS SUGERIDAS:** policy.py (DENIED_IMPORT_ROOTS, DENIED_ATTRIBUTES), Dockerfile, runner_payload.py (restricted_import, blocked_call), runner.py (SandboxRunner), SandboxValidationPanel.tsx

---

### 📁 2. ReviewerAgent

```
backend/app/agents/
├── __init__.py             ← exports ReviewerAgent
├── reviewer_agent.py       ← ReviewerAgent, review_code, review_feedback
├── graph.py                ← integration in LangGraph (reviewer node)
├── programmer_agent.py     ← ProgrammerAgent (genera código, usa reviewer)
└── prompts.py              ← reviewer prompt templates

backend/app/services/pedagogical_orchestration_service.py  ← usa ReviewerAgent

backend/tests/test_fixes.py     ← referencia a reviewer
backend/tests/test_sandbox.py   ← TestProgrammerReviewerLoop (4 tests)
```

**CAPTURAS SUGERIDAS:** reviewer_agent.py (ReviewerAgent), graph.py (reviewer node en LangGraph), test_sandbox.py (TestProgrammerReviewerLoop)

---

### 📁 3. Replay Longitudinal

```
backend/app/replay/
├── __init__.py
├── models.py               ← ReplayEvent, ReplaySession, ReplaySummary, ReplayMode
├── session_replay.py       ← SessionReplay (reconstrucción week-by-week)
├── session_store.py        ← SessionStore
├── replayer.py             ← CognitiveReplayer (streaming con speed control)
├── recorder.py             ← ReplayRecorder (persiste eventos SSE)
├── serializer.py           ← ReplaySerializer (JSON/Markdown/HTML)
├── export.py               ← ReplayExporter (dispatch format)
├── replay_exporter.py      ← Full exporter (JSON, Markdown, LaTeX, CSV)
├── timeline.py             ← TimelineBuilder, timeline data structures
├── timeline_builder.py     ← TimelineBuilder.build
├── adaptation_replay.py    ← AdaptationReplay (decisiones por semana)
├── memory_replay.py        ← MemoryReplay (snapshots con deltas)
└── reasoning_replay.py     ← ReasoningReplay (explicaciones por semana)

backend/app/api/routes/replay.py  ← 10 endpoints REST + SSE

frontend/src/pages/replay/
└── ReplayDashboard.tsx     ← Dashboard principal de replay

frontend/src/components/swarm/
├── ReplayTimeline.tsx
├── ReplayControls.tsx
├── ReplayExportPanel.tsx
├── ReplaySessionViewer.tsx
├── ReplayMemoryView.tsx
├── ReplayReasoningPanel.tsx
├── ReplayConsensusView.tsx
├── DeliberationReplay.tsx
└── CognitiveReplayView.tsx

frontend/src/types/replay.ts

backend/tests/
├── test_replay.py
└── test_cognitive_replay.py
```

**CAPTURAS SUGERIDAS:** session_replay.py (SessionReplay.reconstruct), replayer.py (CognitiveReplayer), replay.py (10 endpoints), ReplayDashboard.tsx, ReplayTimeline.tsx, ReplayExportPanel.tsx

---

### 📁 4. Explainability Pedagógica

```
backend/app/explainability/
├── __init__.py
├── __init__.py             ← "Explainable Adaptive Pedagogy"
├── models.py               ← Reason, Explanation, AdaptationExplanation
├── adaptive_reasoning.py   ← AdaptiveReasoning (orquestador central)
├── bloom_explainer.py      ← BloomExplainer (explica cambios de nivel Bloom)
├── cognitive_load_analysis.py ← CognitiveLoadAnalyzer (tendencias de carga)
├── personalization_trace.py   ← PersonalizationTracer (prompt, modality, pacing, scaffolding)
└── adaptation_decision_graph.py ← DecisionGraphBuilder

backend/app/services/explanation_service.py

frontend/src/components/swarm/
├── CognitiveLoadPanel.tsx
├── PersonalizationReasoning.tsx
├── PersonalizationTimeline.tsx
├── AdaptationReasoningPanel.tsx
├── AdaptiveTraceTimeline.tsx
└── BloomDecisionView.tsx

backend/tests/
├── test_explainability.py
└── test_explanations.py
```

**CAPTURAS SUGERIDAS:** adaptive_reasoning.py (AdaptiveReasoning), bloom_explainer.py (BloomExplainer.explain_change), cognitive_load_analysis.py, personalization_trace.py, CognitiveLoadPanel.tsx, PersonalizationReasoning.tsx

---

### 📁 5. Benchmark Reproducible

```
backend/app/benchmark/
├── __init__.py
├── __init__.py
├── runner.py               ← BenchmarkRunner (ejecuta experimentos)
├── cli.py                  ← CLI interface (modo swarm, single-agent)
├── datasets.py             ← DatasetLoader (carga datasets)
├── metrics.py              ← BenchmarkMetrics (cómputo de métricas)
├── statistics.py           ← StatisticalAnalyzer (análisis estadístico)
├── exporters.py            ← BenchmarkExporter (CSV, JSON, LaTeX)
├── schemas.py              ← BenchmarkTask, BenchmarkResult
├── mermaid.py              ← MermaidValidator (diagramas)

datasets/
├── bloom_level_tasks.jsonl
├── humaneval_pedagogical.jsonl
├── mbpp_pedagogical.jsonl
├── misconception_dataset.jsonl
└── multimodal_pedagogical_tasks.jsonl

outputs/benchmark/
├── academic-hardening-42-14c3ac49/
│   ├── experiment_replay.json
│   ├── records.jsonl
│   ├── report.md
│   ├── results.csv
│   ├── summary.json
│   └── tables.tex
└── academic-hardening-42-f446121e/
    ├── experiment_replay.json
    ├── records.jsonl
    ├── report.md
    ├── results.csv
    ├── summary.json
    └── tables.tex

backend/tests/test_benchmark.py
```

**CAPTURAS SUGERIDAS:** runner.py (BenchmarkRunner), datasets.py, datasets/*.jsonl (primeras líneas), outputs/benchmark/*/report.md, tables.tex, results.csv, summary.json

---

### 📁 6. Degraded Mode

```
backend/app/core/agent_health/
├── __init__.py
├── adaptive_degradation.py  ← AdaptiveDegradationManager
├── monitor.py               ← HealthMonitor
├── models.py                ← AgentHealth, HealthScore
├── health_scorer.py         ← HealthScorer
├── health_score_voter.py    ← HealthScoreVoter
├── behavioral_baseline.py   ← BehavioralBaseline
├── collective_stability.py  ← CollectiveStabilityAnalyzer
├── meta_monitor.py          ← MetaMonitor
└── __init__.py

backend/app/core/
├── consensus_timeouts.py    ← degraded mode logic
└── consensus_cancellation.py ← DEGRADED_MODE constant

backend/app/integrations/tavily/client.py ← degraded-mode (fallback sin API key)
backend/app/main.py                       ← GET /health (status: degraded)

outputs/sustentation/
├── health.json              ← Health check evidence
├── metrics.txt              ← Métricas del sistema
├── swarm_evidence.json      ← Swarm evidence
├── api_summary.json         ← API summary
├── READINESS_REPORT.md      ← Readiness report
└── DEMO_SCRIPT.md           ← Demo script

outputs/final_readiness/
├── DEGRADED_MODE_REPORT.md  ← Reporte de degraded mode
├── FINAL_READINESS.md       ← Readiness final
├── E2E_VALIDATION.md        ← Validación E2E
├── LIVE_DEMO_VALIDATION.md  ← Validación demo
└── FINAL_BUGS.md            ← Bugs conocidos

docs/agent_health_monitoring.md

backend/tests/
├── test_agent_health.py
└── test_consensus_timeouts.py
```

**CAPTURAS SUGERIDAS:** health.json (curl response), main.py (health endpoint), adaptive_degradation.py, client.py (TavilyClient degraded), consensus_cancellation.py (DEGRADED_MODE)

---

### 📁 7. SSE Replay Avanzado

```
backend/app/api/routes/
├── replay.py               ← GET /api/replay/stream/{student_id} (SSE)
└── swarm_demo.py           ← GET /api/swarm/demo/replay/{session_id}/stream (SSE)

backend/app/replay/
├── recorder.py             ← ReplayRecorder (persiste eventos SSE)
├── models.py               ← ReplayEvent, ReplayMode
├── replayer.py             ← CognitiveReplayer (streaming)
└── timeline.py             ← TimelineBuilder (eventos SSE)

frontend/src/
├── pages/replay/ReplayDashboard.tsx ← EventSource SSE, sseLog viewer
├── components/swarm/
│   ├── ReplayTimeline.tsx
│   └── ReplayControls.tsx
└── hooks/useDemoSSE.ts    ← SSE event parsing

outputs/frontend_stabilization/SSE_VALIDATION.md

backend/tests/
├── test_replay.py
├── test_cognitive_replay.py
└── test_streaming.py
```

**CAPTURAS SUGERIDAS:** replay.py (stream endpoint, event generator), recorder.py (ReplayRecorder.record), ReplayDashboard.tsx (EventSource), SSE_VALIDATION.md

---

### 📁 8. Shared Memory Adaptativa

```
backend/app/memory/
├── pedagogical_memory.py    ← adaptation_metrics, personalization
├── shared_memory.py
├── memory_rules.py
└── patterns.py

backend/app/services/adaptive_service.py    ← AdaptiveService

backend/app/explainability/
├── personalization_trace.py ← PersonalizationTracer (4 dimensiones)
└── cognitive_load_analysis.py ← CognitiveLoadAnalyzer

frontend/src/components/swarm/
├── MemoryInfluencePanel.tsx
├── PersonalizationTimeline.tsx
├── AdaptiveTraceTimeline.tsx
└── AdaptationEvolution.tsx

backend/tests/
├── test_adaptive.py
├── test_adaptation.py
├── test_adaptive_trust.py
├── test_shared_memory.py
└── test_memory_wiring.py
```

**CAPTURAS SUGERIDAS:** pedagogical_memory.py (adaptation_metrics), adaptive_service.py, personalization_trace.py, MemoryInfluencePanel.tsx, PersonalizationTimeline.tsx

---

### 📁 9. Academic Hardening

```
backend/app/services/academic_activation_service.py

outputs/sustentation/
├── READINESS_REPORT.md
├── metrics.txt
├── api_summary.json
├── swarm_evidence.json
├── health.json
└── DEMO_SCRIPT.md

outputs/final_readiness/
├── FINAL_READINESS.md
├── DEGRADED_MODE_REPORT.md
├── DEMO_CHECKLIST.md
├── E2E_VALIDATION.md
├── FINAL_BUGS.md
├── LIVE_DEMO_VALIDATION.md
├── SUSTENTATION_FLOW.md
└── UX_AUDIT.md

outputs/scrum_evidence/
├── WEEKLY_TIMELINE.md
├── SPRINT1_REPORT.md
├── SPRINT2_PROGRESS.md
├── WEEKLY_HOURS.md
├── CODE_EVIDENCE_GUIDE.md
├── SCREENSHOT_GUIDE.md
├── WEEKLY_COMMITS.md
├── TECHNICAL_PROGRESS.md
├── DEMO_PROGRESS_WEEK9.md
└── EVIDENCE_EXACT_FILES.md  ← (este archivo)

backend/tests/test_academic_activation.py
```

**CAPTURAS SUGERIDAS:** FINAL_READINESS.md, DEGRADED_MODE_REPORT.md, metrics.txt, health.json, DEMO_SCRIPT.md

---

### 📁 10. Tests y Estabilización

```
backend/tests/
├── __init__.py
├── conftest.py                  ← Fixtures compartidos
├── test_academic_activation.py
├── test_adaptation.py
├── test_adaptive.py
├── test_adaptive_trust.py
├── test_agent_health.py
├── test_auth.py                 ← Auth tests
├── test_benchmark.py            ← Benchmark tests
├── test_circuit_breaker.py
├── test_cognitive_replay.py     ← Cognitive replay tests
├── test_collective_inference.py
├── test_concurrency.py
├── test_config.py
├── test_consensus.py
├── test_consensus_timeouts.py
├── test_courses.py              ← Courses CRUD tests
├── test_event_outbox.py
├── test_explainability.py       ← Explainability tests
├── test_explanations.py
├── test_fixes.py
├── test_health_detectors.py
├── test_idempotency.py
├── test_idempotency_distributed.py
├── test_knowledge_graph.py
├── test_memory.py
├── test_memory_wiring.py
├── test_observability.py
├── test_patterns.py
├── test_pedagogical_orchestration.py
├── test_pedagogical_research_pipeline.py
├── test_prerequisite.py
├── test_propagation_ttl.py
├── test_replay.py               ← Replay tests
├── test_resources.py
├── test_sandbox.py              ← Sandbox tests (28)
├── test_shared_memory.py
├── test_streaming.py
├── test_students.py
├── test_swarm_diagnostics.py
├── test_tracing.py
├── test_tutor_endpoints.py
└── test_users.py

frontend:
├── npm run build → 0 errores, 812ms
├── npm run lint  → 0 errores, 1 warning
└── npx tsc --noEmit → 0 errores
```

**CAPTURAS SUGERIDAS:** pytest output (1338 passed), npm run build output, npm run lint output, tsc output, test_sandbox.py (28 tests)
