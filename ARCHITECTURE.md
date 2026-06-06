# Architecture — UPAO-MAS-EDU v1.0.0

## Diagrama de Capas

```
┌─────────────────────────────────────────────────────────────────────┐
│                        FRONTEND (React + Vite)                      │
│  ┌─────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │
│  │   Auth  │ │  Admin   │ │ Docente  │ │Estudiante│ │Investig. │  │
│  │  Pages  │ │  Pages   │ │  Pages   │ │  Pages   │ │  Pages   │  │
│  └────┬────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘  │
│       └───────────┴────────────┴────────────┴────────────┘         │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                  Zustand (Auth) + React Query                 │  │
│  │    Axios (JWT interceptor + auto-refresh)                    │  │
│  └──────────────────────────────────────────────────────────────┘  │
└──────────────────────────────┬──────────────────────────────────────┘
                               │ HTTP / SSE
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    BACKEND (FastAPI + Python 3.12)                  │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                   MIDDLEWARE PIPELINE                         │   │
│  │  CORS → Tracing → Idempotency → RateLimit → QueryTrace → ID  │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────────────┐  │
│  │   Auth   │ │  API     │ │  Agents  │ │   Swarm Orchestrator  │  │
│  │  (JWT)   │ │  Routes  │ │ (LG)     │ │   (9-phase lifecycle) │  │
│  └──────────┘ └────┬─────┘ └────┬─────┘ └──────────┬───────────┘  │
│                    │             │                   │              │
│  ┌─────────────────┴─────────────┴───────────────────┴───────────┐ │
│  │                    SERVICE LAYER                               │ │
│  │  Pedagogical    │  Consensus    │  Memory     │  Orchestration │ │
│  │  Service        │  Engine       │  Service    │  Service       │ │
│  └─────────────────┴───────────────┴─────────────┴───────────────┘ │
│                    │             │                   │              │
│  ┌─────────────────┴─────────────┴───────────────────┴───────────┐ │
│  │                    DOMAIN LAYER                                │ │
│  │  Models/ORM  │  Schemas   │  Events   │  Tracing  │  LLM      │ │
│  └─────────────────┬───────────┬───────────┬───────────┬─────────┘ │
│                    │           │           │           │           │
└────────────────────┼───────────┼───────────┼───────────┼───────────┘
                     │           │           │           │
               ┌─────▼─────┐ ┌──▼───┐ ┌─────▼────┐ ┌───▼────┐
               │PostgreSQL │ │Tavily│ │  OpenAI  │ │Anthropic│
               │    16     │ │ API  │ │   API    │ │   API   │
               └───────────┘ └──────┘ └──────────┘ └─────────┘
```

---

## Flujo de Request

```
Browser                    FastAPI                      PostgreSQL
   │                         │                             │
   │── GET /api/courses ────►│                             │
   │                         │── middleware chain ────────►│
   │                         │  1. CORS check              │
   │                         │  2. Tracing middleware       │
   │                         │  3. Idempotency (mutations)  │
   │                         │  4. Rate limit (auth)       │
   │                         │  5. Request ID               │
   │                         │                             │
   │                         │── decode JWT ──────────────►│
   │                         │── query courses ───────────►│
   │                         │◄─── rows ──────────────────│
   │                         │                             │
   │                         │── serialize → Pydantic ────►│
   │◄─── JSON response ─────│                             │
```

---

## Flujo de Swarm

```
Request → SwarmOrchestrator.start()
  │
  ├── 1. ENTERING → Valida contexto
  ├── 2. CONTEXT_LOADING → Carga módulo/estudiante
  ├── 3. MEMORY_INIT → Carga memoria compartida
  ├── 4. PEDAGOGICAL_ANALYSIS → PedagogicalAgent
  ├── 5. ADAPTIVE_ADJUSTMENT → AdaptiveAgent
  ├── 6. RISK_ASSESSMENT → RiskAgent
  ├── 7. CONSENSUS → ConsensusEngine (4 voters)
  ├── 8. INFERENCE → CollectiveInference
  ├── 9. CONTENT_PRODUCTION → Content production
  │
  └── ACTIVE → SSE stream + observabilidad
```

---

## Flujo de Propagación de Eventos

```
Evento → ttl_event_guard
  │
  ├── ¿TTL existe? → No → lifecycle.start() + forward() → hop=1
  │                                                          
  ├── ¿TTL activo? → No → return None (bloqueado)
  │
  ├── Check feedback loop → ¿agent ya visitado? → FeedbackLoopError
  │
  ├── Check DAG cycle → ¿event ya procesado? → DAGCycleError
  │
  ├── Check stop conditions:
  │     ├── ¿state != ACTIVE? → stop
  │     ├── ¿TTL expired? → stop
  │     ├── ¿max_hops alcanzado? → stop
  │     └── ¿strength depleted? → stop
  │
  └── forward() → hop+1 → nuevo PropagationTTL
```

---

## Flujo de Idempotencia

```
Request con Idempotency-Key
  │
  ├── Hot Cache (LRU, 10k, 5min)
  │     ├── Hit → return cached response
  │     └── Miss → DB lookup
  │
  ├── DB: IdempotencyKey
  │     ├── PENDING → lock + process
  │     ├── IN_PROGRESS → wait
  │     ├── COMPLETED → return cached
  │     └── FAILED → retry
  │
  └── Advisory Lock (pg_advisory_xact_lock)
        └── Serializa concurrencia por key
```

---

## Módulos del Backend

```
backend/app/
├── main.py              # FastAPI entry + middleware + routers
├── core/                # Config, security, consensus engine
├── api/                 # 20 routers FastAPI
├── models/              # 30 SQLAlchemy models
├── schemas/             # Pydantic schemas
├── services/            # Business logic
├── agents/              # LangGraph agents + router
├── swarm/               # Swarm orchestrator + factory
├── swarm_diagnostics/   # 22 anomaly detectors
├── llm/                 # LLM service + voters + prompts
├── memory/              # Shared memory + collective inference
├── events/              # Idempotency, outbox, propagation TTL
├── tracing/             # Distributed tracing (W3C)
├── observability/       # Metrics, SSE, audit
├── experiment/          # Thesis benchmark
├── integrations/        # Tavily search
├── middleware/           # Rate limiting
└── db/                  # Session, UoW, locks
```

---

## Base de Datos (30 modelos)

### Core
- `User` — Auth + roles
- `Course` — Cursos con status lifecycle
- `LearningObjective` — Objetivos con taxonomía Bloom
- `Resource` — Archivos multimedia
- `Enrollment` — Matrícula

### Pedagógicos
- `StudentProfile` — Estilo/ritmo de aprendizaje
- `LearningPath` / `PathModule` — Ruta personalizada
- `StudentProgress` — Progreso por estudiante
- `EvaluationAttempt` — Intentos de evaluación

### Memoria
- `StudentMemory` — Memoria de largo plazo
- `SharedMemoryRecord` — Memoria compartida del swarm
- `KnowledgeNode` / `KnowledgeEdge` — Grafo de conocimiento

### Infraestructura
- `EventOutbox` — Outbox pattern
- `IdempotencyKey` — Idempotencia
- `AuditLog` — Auditoría
- `LoginAttempt` — Intentos de login

### Currículo
- `InstitutionalCourse` — Malla ISIA 2025
- `Competency` — Competencias institucionales/carrera
- `ProgrammingConcept` — Conceptos de programación
