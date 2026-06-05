# UPAO-MAS-EDU

Sistema Multiagente Educativo con IA para la personalización adaptativa de rutas de aprendizaje mediante swarm intelligence, memoria compartida y deliberación colectiva.

Desarrollado para el **Taller Integrador 1** de la **Universidad Privada Antenor Orrego (UPAO)**, Trujillo, Perú.

---

## Arquitectura Multiagente

```
                    ┌─────────────────────────────────────┐
                    │           Frontend React             │
                    │    (Vite + TypeScript + Tailwind)     │
                    └──────────────┬──────────────────────┘
                                   │ REST (JWT) + SSE
                    ┌──────────────▼──────────────────────┐
                    │        FastAPI + LangGraph            │
                    │                                      │
                    │  ┌─────────┐  ┌──────────┐          │
                    │  │ Research │  │ Visual   │          │
                    │  │  Agent   │  │ Designer │          │
                    │  └────┬────┘  └────┬─────┘          │
                    │       │             │                 │
                    │  ┌────▼─────────────▼─────┐          │
                    │  │   Swarm Coordinator    │          │
                    │  │  (deliberación/voto)    │          │
                    │  └────┬─────────────┬─────┘          │
                    │       │             │                 │
                    │  ┌────▼────┐  ┌────▼─────┐          │
                    │  │Programmer│  │ Reviewer │          │
                    │  │  Agent  │  │  Agent   │          │
                    │  └─────────┘  └──────────┘          │
                    │                                      │
                    │  ┌──────────────────────────┐       │
                    │  │  Shared Memory /         │       │
                    │  │  Collective Inference    │       │
                    │  └──────────────────────────┘       │
                    │                                      │
                    │  ┌──────────────────────────┐       │
                    │  │  Sandbox Docker (código) │       │
                    │  └──────────────────────────┘       │
                    └──────────────┬──────────────────────┘
                                   │ SQL
                    ┌──────────────▼──────────────────────┐
                    │         PostgreSQL 16                │
                    │   + Alembic Migrations              │
                    └─────────────────────────────────────┘
```

## Stack Tecnológico

| Capa | Tecnología |
|------|-----------|
| Backend | Python 3.12+, FastAPI, SQLAlchemy 2.0, Alembic 1.18 |
| Base de datos | PostgreSQL 16 |
| Frontend | React 19, Vite 8, TypeScript 6, Tailwind CSS 3, shadcn/ui |
| Estado | Zustand + TanStack React Query |
| Auth | JWT (python-jose) + bcrypt |
| Agentes | LangGraph 0.2.x |
| Sandbox | Docker (ejecución aislada de código Python) |
| Despliegue Backend | Render |
| Despliegue Frontend | Vercel |

## Módulos Principales

### Backend (`backend/app/`)

| Módulo | Descripción |
|--------|-------------|
| `agents/` | Sistema multiagente: ResearchAgent, ProgrammerAgent, ReviewerAgent, VisualDesignerAgent |
| `api/routes/` | Endpoints REST: auth, courses, students, resources, swarm, sandbox, replay, pedagogy |
| `swarm_diagnostics/` | Detectores de anomalías: loops, deadlocks, hallucination, event storm, propagation |
| `memory/` | Memoria compartida, inferencia colectiva, narrative continuity |
| `replay/` | Reconstrucción cognitiva adaptativa, session management, timeline export |
| `sandbox/` | Docker sandbox para ejecución aislada de código Python |
| `benchmark/` | Framework reproducible de evaluación: AcademicBenchmarkRunner, metrics |
| `demo/` | Orquestación de demos sintéticas con SSE en tiempo real |
| `explainability/` | Explicabilidad pedagógica: SHAP, LIME, contrafactuales |
| `events/` | Sistema de eventos: outbox, idempotency, propagation TTL, dedup |
| `observability/` | Métricas de consenso, trazabilidad distribuida |

### Frontend (`frontend/src/`)

| Módulo | Descripción |
|--------|-------------|
| `pages/demo/` | Panel Swarm Demo con SSE, timeline de deliberación, trust evolution |
| `pages/replay/` | Dashboard de replay cognitivo longitudinal |
| `components/swarm/` | Componentes de visualización: BloomProgression, ConsensusTimeline, SandboxPanel |
| `components/docente/` | Planificador pedagógico semanal, estructura de cursos |
| `components/estudiante/` | Vista de aprendizaje semanal del estudiante |
| `hooks/` | Custom hooks: useDemoSSE, usePedagogy, useWeeklyLearning |

### Datasets (`datasets/`)

| Dataset | Propósito |
|---------|-----------|
| `bloom_level_tasks.json` | Tareas etiquetadas por nivel Bloom |
| `humaneval_pedagogical.json` | HumanEval adaptado pedagógicamente |
| `mbpp_pedagogical.json` | MBPP con metadatos pedagógicos |
| `misconception_dataset.json` | Dataset de misconceptions |
| `multimodal_pedagogical.json` | Ejercicios multimodales |

---

## Instalación

### Requisitos

- Python 3.12+
- Node.js 20+
- PostgreSQL 16 (o Docker)
- Docker (para sandbox de agentes)
- npm 10+

### 1. Clonar

```bash
git clone <repo-url>
cd upao-mas-edu
```

### 2. Base de datos (PostgreSQL con Docker)

```bash
docker compose up -d
```

O usando PostgreSQL local:

```bash
createdb upao_mas_edu
```

### 3. Backend

```bash
cd backend
python -m venv venv
# Windows: venv\Scripts\activate
# Linux/Mac: source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Editar .env si es necesario
alembic upgrade head
python seed.py
```

### 4. Frontend

```bash
cd frontend
npm install
cp .env.example .env
```

### 5. Ejecutar

```bash
# Terminal 1 — Backend
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2 — Frontend
cd frontend
npm run dev
```

| Servicio | URL |
|----------|-----|
| Frontend | http://localhost:5173 |
| Backend API | http://localhost:8000 |
| Swagger UI | http://localhost:8000/docs |
| ReDoc | http://localhost:8000/redoc |

---

## Docker Sandbox

El sandbox permite ejecución aislada de código Python generado por los agentes:

```bash
# Build de la imagen sandbox
docker build -t upao-sandbox -f backend/app/sandbox/docker/Dockerfile.backend backend/

# O usar docker-compose (incluye PostgreSQL + backend)
docker compose up -d
```

## Ollama Setup (opcional)

Para usar modelos locales en lugar de OpenAI:

```bash
# Instalar Ollama
# https://ollama.com

# Descargar modelo
ollama pull llama3.2

# Configurar .env
# OPENAI_API_KEY=ollama
# OPENAI_BASE_URL=http://localhost:11434/v1
```

## API Keys

| Key | Proveedor | ¿Requerida? | ¿Dónde obtener? |
|-----|-----------|-------------|-----------------|
| `OPENAI_API_KEY` | OpenAI | No (fallback a templates) | https://platform.openai.com/api-keys |
| `TAVILY_API_KEY` | Tavily | No (búsqueda degradada) | https://app.tavily.com |

Las API keys se configuran en `backend/.env` (copiar desde `.env.example`).

---

## Demo Swarm

### Ruta de demo

```bash
# Backend debe estar corriendo
# Endpoints SSE en tiempo real:
GET  /api/swarm-demo/stream
POST /api/swarm-demo/start
POST /api/swarm-demo/stop
GET  /api/swarm-demo/status

# Abrir en el navegador:
# http://localhost:5173/demo/swarm
```

La demo muestra:
- Orquestación multiagente en tiempo real vía SSE
- Timeline de deliberación con consenso ponderado
- Evolución de trust entre agentes
- Paneles de sandbox, memoria compartida, consistencia narrativa
- Replay cognitivo de sesiones

## Benchmark

```bash
cd backend
python -m pytest tests/test_benchmark.py -v
python -m app.benchmark.cli --output outputs/benchmark
```

El benchmark evalúa:
- Precisión pedagógica (Bloom taxonomy alignment)
- Diversidad de fuentes (research agent)
- Calidad de código (programmer agent)
- Tasa de revisión (reviewer agent)
- Coherencia visual (visual designer agent)

Resultados en `outputs/benchmark/`.

## Replay Cognitivo

```bash
# API
GET  /api/replay/sessions
GET  /api/replay/sessions/{id}
GET  /api/replay/sessions/{id}/timeline
POST /api/replay/sessions/{id}/export

# Frontend
# http://localhost:5173/replay
```

El replay reconstructivo permite:
- Navegar la línea de tiempo de decisiones del swarm
- Ver adaptaciones por sesión de estudiante
- Exportar sesiones a JSON, CSV o HTML
- Analizar métricas longitudinales

## Explainability

```bash
# API
POST /api/explain/decision
POST /api/explain/session/{id}
```

Paneles de explicabilidad:
- SHAP values para decisiones de ruta adaptativa
- Análisis contrafactual ("qué cambiaría la recomendación")
- Atribución de influencia por agente

---

## Estructura del Repositorio

```
upao-mas-edu/
├── backend/
│   ├── app/
│   │   ├── agents/              # Sistema multiagente (LangGraph)
│   │   ├── api/routes/          # Endpoints REST
│   │   ├── benchmark/           # Benchmark académico
│   │   ├── core/                # Config, health, consensus, trust
│   │   ├── db/                  # SQLAlchemy, Unit of Work
│   │   ├── demo/                # Demo sintética SSE
│   │   ├── events/              # Sistema de eventos
│   │   ├── explainability/      # SHAP, LIME, contrafactuales
│   │   ├── memory/              # Shared memory, collective inference
│   │   ├── models/              # SQLAlchemy models
│   │   ├── observability/       # Métricas y tracing
│   │   ├── replay/              # Replay cognitivo
│   │   ├── sandbox/             # Docker sandbox
│   │   ├── schemas/             # Pydantic schemas
│   │   ├── services/            # Lógica de negocio
│   │   └── weekly_learning/     # Planificación semanal
│   ├── alembic/                 # Migraciones (12 revisiones)
│   ├── tests/                   # Tests (pytest)
│   ├── scripts/                 # Scripts auxiliares
│   ├── requirements.txt
│   ├── Dockerfile
│   └── setup.sh
├── frontend/
│   ├── src/
│   │   ├── components/          # Componentes React
│   │   ├── hooks/               # Custom hooks
│   │   ├── pages/               # Páginas
│   │   ├── providers/           # AuthProvider, etc.
│   │   ├── stores/              # Zustand stores
│   │   └── types/               # TypeScript types
│   ├── package.json
│   └── vite.config.ts
├── datasets/                    # Datasets pedagógicos
├── docs/                        # Documentación técnica
├── outputs/                     # Benchmark results
├── docker-compose.yml
├── render.yaml
└── run_demo.py
```

---

## Troubleshooting

| Problema | Solución |
|----------|----------|
| `psycopg2` connection error | Verificar PostgreSQL en ejecución y `DATABASE_URL` en `.env` |
| Alembic `Target database is not up to date` | Ejecutar `alembic upgrade head` |
| Frontend no carga | Verificar `npm install` y `npm run dev` |
| Agente no responde | Verificar `OPENAI_API_KEY` o configurar Ollama |
| Sandbox falla | Verificar Docker en ejecución e imagen `upao-sandbox` |
| Seed duplica datos | Es idempotente — ejecutar sin riesgo |
| `Port 8000 in use` | Cambiar puerto o matar proceso: `npx kill-port 8000` |
| CORS errors | Verificar `FRONTEND_URL` en backend `.env` |

## Comandos Importantes

```bash
# Backend
pytest -v                           # Ejecutar tests (38+ tests)
alembic upgrade head                # Aplicar migraciones
alembic downgrade -1                # Revertir última migración
python seed.py                      # Seed idempotente
uvicorn app.main:app --reload       # Servidor dev

# Frontend
npm run dev                         # Servidor dev
npm run build                       # Build producción
npm run lint                        # ESLint

# Docker
docker compose up -d                # Iniciar PostgreSQL + backend
docker compose down                 # Detener servicios

# Benchmark
python -m pytest tests/test_benchmark.py -v

# Demo
python run_demo.py                  # Demo rápida desde CLI
```

---

## Licencia

Proyecto académico — UPAO Taller Integrador 1
