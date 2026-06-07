# 📊 Progreso Técnico — UPAO-MAS-EDU

## Sistema Multiagente Educativo con Inteligencia Artificial

**Proyecto:** UPAO-MAS-EDU — Plataforma Educativa Multiagente con IA  
**Equipo:** Ingeniería de Software — Universidad Privada Antenor Orrego  
**Período cubierto:** Semana 4 → Semana 9 (en progreso)  
**Última actualización:** 5 de junio de 2026  
**Stack principal:** FastAPI · LangGraph · React · TypeScript · PostgreSQL · Docker

---

## 1. Evolución de la Arquitectura

### 1.1 Línea de Tiempo Arquitectónica

| Semana | Hito | Descripción |
|--------|------|-------------|
| **S4** | Monolito base | FastAPI + SQLAlchemy + PostgreSQL — estructura CRUD inicial |
| **S5** | Integración multiagente | LangGraph StateGraph + 4 agentes especializados |
| **S6** | Despliegue y estabilización | Render (backend) + Vercel (frontend) + Docker (sandbox) |
| **S7** | Gobernanza de esquemas | Migraciones Alembic consolidadas + documentación técnica |
| **S8** | Swarm intelligence | Consenso, circuit breaker, health monitoring, tracing, events |
| **S9** | Orquestación pedagógica avanzada | Replay, explainability, benchmark, SSE demo |

---

### 1.2 Semana 4 — Monolito Simple

**Objetivo:** Establecer la base funcional del sistema con una arquitectura monolítica limpia.

**Componentes implementados:**

- **FastAPI** como framework HTTP principal con documentación automática (Swagger/OpenAPI).
- **SQLAlchemy 2.0** como ORM con soporte completo para operaciones asíncronas (`AsyncSession`).
- **PostgreSQL 16** como motor de base de datos relacional.
- **Alembic** para gestión de migraciones de esquema.
- Estructura de carpetas basada en el patrón de separación por capas:
  ```
  backend/app/
  ├── models/          # Modelos SQLAlchemy
  ├── schemas/         # Schemas Pydantic (validación)
  ├── services/        # Lógica de negocio
  ├── api/routes/      # Endpoints REST
  ├── core/            # Configuración, seguridad, DB
  └── tests/           # Tests unitarios e integración
  ```
- Autenticación JWT con `python-jose` y hashing con `bcrypt`.
- CRUD completo para las entidades principales: `User`, `Course`, `Resource`, `Enrollment`.
- Configuración de CORS y middleware de logging.

**Decisiones de diseño:**

- Se eligió SQLAlchemy 2.0 sobre versiones anteriores por su soporte nativo de `async/await`, evitando el overhead de wrappers como `databases`.
- Se optó por Pydantic v2 para validación de esquemas por su rendimiento superior (hasta 17x más rápido que v1 en serialización).
- La estructura de carpetas sigue el principio de separación de responsabilidades para facilitar la posterior descomposición en módulos.

---

### 1.3 Semana 5 — Integración Multiagente

**Objetivo:** Integrar un sistema multiagente basado en LangGraph con agentes especializados para asistencia pedagógica.

**Agentes implementados:**

| Agente | Rol | Responsabilidad |
|--------|-----|-----------------|
| 🔍 **Research Agent** | Investigador | Busca y sintetiza información académica relevante |
| 💻 **Programmer Agent** | Programador | Genera código, ejemplos y ejercicios prácticos |
| 📝 **Reviewer Agent** | Revisor | Evalúa calidad, detecta errores y sugiere mejoras |
| 🎨 **Visual Agent** | Visualizador | Crea representaciones visuales y diagramas explicativos |

**Arquitectura del grafo:**

```
                    ┌──────────────┐
                    │   Entrada    │
                    │  (consulta)  │
                    └──────┬───────┘
                           │
                    ┌──────▼───────┐
                    │  Orquestador │
                    │  (LangGraph) │
                    └──────┬───────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
       ┌──────▼──┐  ┌──────▼──┐  ┌──────▼──┐
       │Research │  │Programmer│  │ Visual  │
       │ Agent   │  │  Agent   │  │ Agent   │
       └────┬────┘  └────┬────┘  └────┬────┘
            │            │            │
            └────────────┼────────────┘
                         │
                  ┌──────▼───────┐
                  │   Reviewer   │
                  │    Agent     │
                  └──────┬───────┘
                         │
                  ┌──────▼───────┐
                  │   Respuesta  │
                  │  consolidada │
                  └──────────────┘
```

**Integración técnica:**

- `LangGraph 1.2` como framework de orquestación con `StateGraph`.
- `LangChain Core 1.4` para abstracción de modelos LLM.
- Cada agente implementa una interfaz uniforme con estado compartido.
- Los agentes se comunican a través del estado del grafo (no directamente entre sí).
- Se implementó manejo de errores y fallback en caso de fallo de un agente individual.

---

### 1.4 Semana 6 — Despliegue y Estabilización

**Objetivo:** Llevar el sistema a producción con pipelines de despliegue continuo.

**Infraestructura de despliegue:**

| Componente | Plataforma | URL / Configuración |
|------------|------------|---------------------|
| Backend API | **Render** | Web Service con auto-deploy desde `main` |
| Frontend SPA | **Vercel** | Deploy automático desde repositorio Git |
| Base de datos | **PostgreSQL (Render)** | Instancia managed con backups automáticos |
| Sandbox | **Docker** | Contenedor aislado para ejecución de código |

**Configuraciones realizadas:**

- Variables de entorno seguras en Render y Vercel.
- CORS configurado para dominios de producción.
- Health check endpoint (`/health`) para monitoreo de disponibilidad.
- `docker-compose.yml` para desarrollo local con PostgreSQL + backend + frontend.
- Scripts de migración automatizados en el pipeline de deploy.
- Rate limiting básico en endpoints públicos.

**Estabilización:**

- Corrección de errores de serialización en respuestas anidadas.
- Optimización de queries N+1 con `selectinload` y `joinedload`.
- Configuración de timeouts apropiados para llamadas a LLM.
- Manejo de reconexión a base de datos en caso de drops transitorios.

---

### 1.5 Semana 7 — Gobernanza de Esquemas y Documentación

**Objetivo:** Consolidar el esquema de base de datos con migraciones reproducibles y documentar la arquitectura.

**Migraciones Alembic consolidadas:**

Se realizaron 12 revisiones de Alembic cubriendo la evolución completa del esquema:

| # | Revisión | Descripción |
|---|----------|-------------|
| 1 | `001_initial` | Tablas base: users, courses, resources |
| 2 | `002_enrollment` | Inscripciones y roles |
| 3 | `003_learning_path` | Rutas de aprendizaje personalizadas |
| 4 | `004_diagnostic` | Tests diagnósticos adaptativos |
| 5 | `005_agent_sessions` | Sesiones de agentes multiagente |
| 6 | `006_trust_scores` | Puntuaciones de confianza inter-agente |
| 7 | `007_consensus_logs` | Registros de deliberación y consenso |
| 8 | `008_circuit_breaker` | Estados de circuit breaker por agente |
| 9 | `009_events_outbox` | Outbox de eventos para event sourcing |
| 10 | `010_shared_memory` | Memoria compartida entre agentes |
| 11 | `011_replay_sessions` | Sesiones de replay cognitivo |
| 12 | `012_benchmark_results` | Resultados de benchmark pedagógico |

**Documentación generada:**

- Diagrama ER completo del esquema de base de datos.
- Documentación de API con ejemplos de request/response.
- Guía de configuración local y de producción.
- README actualizado con instrucciones de instalación y uso.

---

### 1.6 Semana 8 — Swarm Intelligence

**Objetivo:** Implementar inteligencia de enjambre con patrones avanzados de coordinación multiagente.

**Componentes de swarm implementados:**

#### a) Motor de Consenso (`consensus.py` — 51KB)

- Votación ponderada entre agentes con pesos dinámicos.
- Estrategias de consenso: mayoría simple, unanimidad, supermayoría.
- Resolución de empates basada en trust score histórico.
- Registro detallado de cada ronda de deliberación.
- Soporte para abstención y voto condicional.

#### b) Timeouts Adaptativos (`consensus_timeouts.py` — 34KB)

- Timeouts dinámicos basados en complejidad de la consulta.
- Escalamiento automático según carga del sistema.
- Mecanismo de deadline con fallback a respuesta parcial.
- Historial de tiempos de respuesta por agente para calibración.

#### c) Circuit Breaker (`circuit_breaker.py` — 29KB)

- Estados: `CLOSED` (normal) → `OPEN` (fallo) → `HALF_OPEN` (prueba).
- Contadores de fallos configurables por agente.
- Recuperación automática con ventana de prueba.
- Logging de transiciones de estado para diagnóstico.
- Fallback a agente de respaldo cuando un agente está en estado `OPEN`.

#### d) Propagación TTL (`propagation_ttl.py` — 28KB)

- Time-to-Live para mensajes inter-agente.
- Propagación en cascada con decremento automático.
- Prevención de loops infinitos en comunicación circular.
- Limpieza de mensajes expirados.

#### e) Health Monitoring

- Heartbeat periódico de cada agente.
- Métricas de latencia, throughput y tasa de error.
- Dashboard de salud del swarm en tiempo real.
- Alertas automáticas cuando un agente supera umbrales.

#### f) Distributed Tracing

- Correlation IDs únicos por solicitud del usuario.
- Propagación de trace context a través del grafo de agentes.
- Registro de spans para cada operación de agente.
- Visualización de traces completos en logs estructurados.

#### g) Event Sourcing (Outbox Pattern)

- Todos los eventos del swarm se persisten en tabla `events_outbox`.
- Claves de idempotencia para evitar procesamiento duplicado.
- Orden garantizado de eventos por sesión.
- Replay de eventos para reconstrucción de estado.

---

### 1.7 Semana 9 — Orquestación Pedagógica Avanzada (En Progreso)

**Objetivo:** Implementar capacidades avanzadas de orquestación pedagógica con explicabilidad y benchmarking.

**Componentes en desarrollo:**

#### a) Replay Cognitivo

- Dashboard de replay (`/replay`) para visualizar sesiones pasadas.
- Reproducción paso a paso de la deliberación multiagente.
- Timeline interactivo con puntos de decisión clave.
- Exportación de sesiones para análisis posterior.

#### b) Explicabilidad (Explainability)

- Cada decisión del sistema incluye una justificación en lenguaje natural.
- Trazabilidad completa: de la consulta del estudiante a la respuesta final.
- Visualización de los factores que influyeron en cada recomendación.
- Mapa de contribución de cada agente a la respuesta consolidada.

#### c) Benchmark Pedagógico

- 5 datasets JSONL con escenarios pedagógicos reales.
- Evaluación automatizada de calidad de respuestas.
- Métricas: relevancia, precisión, cobertura, claridad pedagógica.
- Comparación entre diferentes configuraciones del swarm.

#### d) Demo SSE en Tiempo Real

- Endpoint de Server-Sent Events para streaming de deliberación.
- Visualización en vivo del proceso de consenso multiagente.
- Panel interactivo (`/demo/swarm`) con animaciones de flujo.
- Indicadores de estado por agente en tiempo real.

---

## 2. Métricas del Código

### 2.1 Resumen Cuantitativo

| Categoría | Cantidad | Ubicación |
|-----------|----------|-----------|
| **Archivos Python (backend)** | ~130+ | `backend/app/` |
| **Archivos TypeScript/React (frontend)** | ~80+ | `frontend/src/` |
| **Archivos de tests** | 43 | `backend/tests/`, `frontend/src/__tests__/` |
| **Modelos SQLAlchemy** | 23 | `backend/app/models/` |
| **Servicios de lógica de negocio** | 22 | `backend/app/services/` |
| **Módulos de rutas API** | 17 | `backend/app/api/routes/` |
| **Migraciones Alembic** | 12 | `backend/alembic/versions/` |
| **Hooks personalizados React** | 15 | `frontend/src/hooks/` |
| **Componentes de visualización swarm** | 31 | `frontend/src/components/swarm/` |
| **Detectores de anomalías** | 20 | `backend/app/services/detectors/` |
| **Datasets pedagógicos** | 5 | `backend/data/datasets/` |

### 2.2 Distribución de Código por Capa

```
backend/app/
├── models/              23 modelos    (~2,800 líneas)
├── schemas/             28 schemas    (~3,200 líneas)
├── services/            22 servicios  (~12,500 líneas)
│   ├── agents/          4 agentes     (~3,400 líneas)
│   ├── swarm/           8 módulos     (~18,000 líneas)
│   └── detectors/       20 detectores (~4,600 líneas)
├── api/routes/          17 módulos    (~4,100 líneas)
├── core/                6 módulos     (~1,800 líneas)
├── demo/                3 módulos     (~3,200 líneas)
└── tests/               43 archivos   (~8,500 líneas)

frontend/src/
├── components/          52 componentes (~9,800 líneas)
│   ├── swarm/           31 componentes (~6,200 líneas)
│   ├── ui/              12 componentes (~1,800 líneas)
│   └── layout/          9 componentes  (~1,800 líneas)
├── hooks/               15 hooks       (~2,100 líneas)
├── pages/               11 páginas     (~3,400 líneas)
├── stores/              5 stores       (~900 líneas)
├── services/            8 servicios    (~1,600 líneas)
└── types/               7 definiciones (~800 líneas)
```

### 2.3 Cobertura de Tests

| Módulo | Tests | Cobertura estimada |
|--------|-------|--------------------|
| Modelos | 8 archivos | ~85% |
| Servicios | 12 archivos | ~72% |
| Rutas API | 10 archivos | ~68% |
| Agentes | 5 archivos | ~60% |
| Swarm | 8 archivos | ~55% |
| **Total** | **43 archivos** | **~65%** |

---

## 3. Complejidad Técnica por Módulo

### 3.1 Top 10 Módulos por Tamaño y Complejidad

| # | Módulo | Tamaño | Descripción | Complejidad |
|---|--------|--------|-------------|-------------|
| 1 | `consensus.py` | 51 KB | Motor de consenso multiagente con votación ponderada, estrategias múltiples y resolución de empates | 🔴 Muy Alta |
| 2 | `consensus_timeouts.py` | 34 KB | Timeouts adaptativos con calibración dinámica basada en historial | 🔴 Muy Alta |
| 3 | `circuit_breaker.py` | 29 KB | Circuit breaker con máquina de estados, recuperación automática y fallback | 🟠 Alta |
| 4 | `propagation_ttl.py` | 28 KB | TTL con propagación en cascada y prevención de loops | 🟠 Alta |
| 5 | `pedagogical_orchestration_service.py` | 25 KB | Orquestación pedagógica completa: diagnóstico → ruta → seguimiento | 🟠 Alta |
| 6 | `demo/orchestrator.py` | 24 KB | Orquestador de demo SSE con streaming en tiempo real | 🟡 Media-Alta |
| 7 | `shared_memory.py` | 21 KB | Memoria compartida inter-agente con sincronización y TTL | 🟡 Media-Alta |
| 8 | `student_service.py` | 21 KB | Servicio estudiantil: onboarding, progreso, métricas | 🟡 Media-Alta |
| 9 | `risk_detectors.py` | 17 KB | 20 detectores de riesgo académico con heurísticas | 🟡 Media |
| 10 | `collective_inference.py` | 13 KB | Inferencia colectiva con agregación de resultados multiagente | 🟡 Media |

### 3.2 Análisis de Complejidad Ciclomática

Los módulos del swarm presentan la mayor complejidad ciclomática del sistema debido a:

- **Múltiples caminos de ejecución** en la máquina de estados del circuit breaker (3 estados × N transiciones).
- **Estrategias de consenso configurables** que ramifican la lógica según el tipo de votación.
- **Timeouts anidados** con fallback en cascada (timeout → retry → fallback → respuesta parcial).
- **Propagación condicional** de mensajes basada en TTL, prioridad y estado del agente receptor.

### 3.3 Dependencias Inter-Módulo

```
pedagogical_orchestration_service
    ├── consensus (votación)
    │   ├── consensus_timeouts (deadlines)
    │   └── shared_memory (estado compartido)
    ├── circuit_breaker (resiliencia)
    │   └── health_monitor (métricas)
    ├── collective_inference (agregación)
    │   └── trust_scoring (ponderación)
    ├── propagation_ttl (mensajería)
    └── event_sourcing (persistencia)
        └── idempotency (deduplicación)
```

---

## 4. Stack Tecnológico Completo

### 4.1 Backend

| Tecnología | Versión | Propósito |
|------------|---------|-----------|
| Python | 3.12 | Lenguaje principal del backend |
| FastAPI | 0.115+ | Framework HTTP asíncrono |
| SQLAlchemy | 2.0 | ORM con soporte async nativo |
| Alembic | 1.14+ | Migraciones de esquema de BD |
| LangGraph | 1.2 | Orquestación de agentes (StateGraph) |
| LangChain Core | 1.4 | Abstracción de modelos LLM |
| Pydantic | 2.x | Validación y serialización de datos |
| python-jose | 3.3+ | Generación y validación de tokens JWT |
| bcrypt | 4.x | Hashing seguro de contraseñas |
| uvicorn | 0.34+ | Servidor ASGI de producción |
| httpx | 0.28+ | Cliente HTTP asíncrono |
| pytest | 8.x | Framework de testing |
| pytest-asyncio | 0.25+ | Soporte async para pytest |
| pytest-cov | 6.x | Reporte de cobertura de código |

### 4.2 Frontend

| Tecnología | Versión | Propósito |
|------------|---------|-----------|
| React | 19 | Biblioteca de UI (componentes) |
| Vite | 8 | Bundler y dev server ultrarrápido |
| TypeScript | 6 | Tipado estático para JavaScript |
| Tailwind CSS | 3 | Framework de utilidades CSS |
| shadcn/ui | latest | Componentes UI accesibles y personalizables |
| Zustand | 5.x | Gestión de estado global ligero |
| TanStack React Query | 5.x | Cache y sincronización de datos del servidor |
| React Router | 7.x | Enrutamiento declarativo SPA |
| Lucide React | latest | Iconografía consistente |
| Recharts | 2.x | Gráficos y visualizaciones de datos |

### 4.3 Infraestructura

| Tecnología | Propósito |
|------------|-----------|
| PostgreSQL 16 | Base de datos relacional principal |
| Docker | Contenedorización (sandbox de código) |
| docker-compose | Orquestación de servicios locales |
| Render | Hosting del backend (Web Service) |
| Vercel | Hosting del frontend (SPA estática) |
| Git / GitHub | Control de versiones y CI/CD |

### 4.4 Herramientas de Desarrollo

| Herramienta | Propósito |
|-------------|-----------|
| ESLint | Linting de código TypeScript/React |
| Prettier | Formateo de código frontend |
| Black | Formateo de código Python |
| Ruff | Linting rápido de Python |
| pre-commit | Hooks de pre-commit para calidad |

---

## 5. Patrones de Diseño Implementados

### 5.1 Patrones Arquitectónicos

#### Multi-Agent Orchestration (LangGraph StateGraph)

- **Descripción:** Orquestación de múltiples agentes de IA usando un grafo dirigido acíclico (DAG) donde cada nodo es un agente especializado.
- **Implementación:** `LangGraph.StateGraph` define el flujo de ejecución, con estados compartidos y transiciones condicionales.
- **Beneficio:** Permite composición flexible de agentes, paralelismo controlado y manejo declarativo de flujos complejos.

#### Consensus Voting (Weighted, Specialized)

- **Descripción:** Sistema de votación ponderada donde cada agente emite un voto sobre la mejor respuesta, con pesos basados en su especialización y trust score.
- **Implementación:** `consensus.py` implementa múltiples estrategias (mayoría, unanimidad, supermayoría) con resolución de empates.
- **Beneficio:** Mejora la calidad de las respuestas al agregar perspectivas múltiples con ponderación basada en competencia.

#### Circuit Breaker Pattern

- **Descripción:** Patrón de resiliencia que previene la propagación de fallos cuando un agente está degradado.
- **Implementación:** Máquina de estados (`CLOSED` → `OPEN` → `HALF_OPEN`) con contadores de fallo y ventanas de recuperación configurables.
- **Beneficio:** El sistema mantiene disponibilidad incluso cuando agentes individuales fallan, con degradación graceful.

#### Event Sourcing (Outbox Pattern)

- **Descripción:** Todos los eventos significativos del sistema se persisten en una tabla outbox antes de ser procesados.
- **Implementación:** Tabla `events_outbox` con claves de idempotencia, orden garantizado y replay de eventos.
- **Beneficio:** Trazabilidad completa, capacidad de replay y consistencia eventual sin acoplamiento fuerte.

### 5.2 Patrones de Diseño de Software

#### Repository Pattern

- **Descripción:** Abstracción de la capa de persistencia con interfaces definidas para cada entidad.
- **Implementación:** Cada modelo tiene un repositorio asociado que encapsula las queries de SQLAlchemy.
- **Beneficio:** Desacopla la lógica de negocio de la implementación específica de la base de datos.

#### Unit of Work (UoW)

- **Descripción:** Gestión transaccional de operaciones que involucran múltiples repositorios.
- **Implementación:** Context manager que agrupa operaciones en una transacción atómica con commit/rollback.
- **Beneficio:** Garantiza consistencia de datos en operaciones complejas que afectan múltiples tablas.

#### Idempotency Keys

- **Descripción:** Cada operación de escritura incluye una clave única que previene la ejecución duplicada.
- **Implementación:** Columna `idempotency_key` en tablas críticas con constraint `UNIQUE`.
- **Beneficio:** Seguridad ante reintentos de red, evita efectos secundarios duplicados.

#### Distributed Tracing (Correlation IDs)

- **Descripción:** Cada solicitud del usuario genera un ID de correlación que se propaga a través de todo el pipeline de agentes.
- **Implementación:** Middleware que inyecta `X-Correlation-ID` en headers y lo propaga al estado del grafo.
- **Beneficio:** Permite rastrear el flujo completo de una solicitud a través de múltiples agentes y servicios.

### 5.3 Patrones de Comunicación

#### Shared Memory (Inter-Agent Communication)

- **Descripción:** Espacio de memoria compartido donde los agentes pueden leer y escribir información de forma coordinada.
- **Implementación:** `shared_memory.py` con TTL por entrada, sincronización y limpieza automática.
- **Beneficio:** Permite colaboración asíncrona entre agentes sin acoplamiento directo.

#### Trust Scoring (Behavioral Baseline)

- **Descripción:** Sistema de puntuación de confianza que evalúa el desempeño histórico de cada agente.
- **Implementación:** Métricas de precisión, latencia y consistencia que alimentan los pesos de votación del consenso.
- **Beneficio:** Los agentes más confiables tienen mayor influencia en las decisiones del swarm.

---

## 6. Resumen de Progreso por Sprint

### Vista consolidada

```
Semana 4  ████████░░  Fundamentos      → Monolito funcional
Semana 5  █████████░  Multiagente      → 4 agentes integrados
Semana 6  █████████░  Despliegue       → Producción estable
Semana 7  ████████░░  Gobernanza       → Esquemas consolidados
Semana 8  ██████████  Swarm            → Inteligencia de enjambre
Semana 9  ███████░░░  Orquestación     → En progreso (70%)
```

### Métricas de velocidad del equipo

| Semana | Story Points planificados | Story Points completados | Velocidad |
|--------|--------------------------|--------------------------|-----------|
| S4 | 21 | 21 | 100% |
| S5 | 26 | 24 | 92% |
| S6 | 18 | 18 | 100% |
| S7 | 15 | 15 | 100% |
| S8 | 34 | 31 | 91% |
| S9 | 29 | ~20 (en progreso) | ~69% |

---

## 7. Riesgos Técnicos y Mitigaciones

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|-------------|---------|------------|
| Latencia alta en llamadas LLM | Alta | Medio | Timeouts adaptativos + caché de respuestas |
| Fallo de agente individual | Media | Alto | Circuit breaker + fallback a agente de respaldo |
| Inconsistencia en consenso | Baja | Alto | Event sourcing + idempotency keys |
| Complejidad del swarm dificulta debugging | Alta | Medio | Distributed tracing + correlation IDs |
| Costos de API de LLM en producción | Media | Medio | Rate limiting + caché inteligente |

---

## 8. Próximos Pasos (Semanas 10-11)

- [ ] Completar pruebas de integración end-to-end
- [ ] Optimización de performance (queries, caching, lazy loading)
- [ ] Evaluación completa con datasets de benchmark pedagógico
- [ ] Pulido de UI/UX en componentes de swarm visualization
- [ ] Documentación final del sistema (manual técnico + manual de usuario)
- [ ] Preparación de la presentación final del proyecto

---

> **Nota:** Este documento se actualiza semanalmente como parte de la evidencia de progreso técnico del proyecto UPAO-MAS-EDU. Todas las métricas son aproximaciones basadas en el estado actual del repositorio.
