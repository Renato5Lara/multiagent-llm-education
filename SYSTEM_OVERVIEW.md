# System Overview — UPAO-MAS-EDU v1.0.0

**Sistema Multi-Agente con Inteligencia de Enjambre para Educación
Personalizada en Programación**

---

## 1. Propósito

Plataforma educativa universitaria que utiliza un enjambre de agentes
de inteligencia artificial para generar rutas de aprendizaje
personalizadas, adaptadas al perfil cognitivo, ritmo y estilo de
aprendizaje de cada estudiante.

---

## 2. Stack Tecnológico

```
Frontend (React 19 + Vite 8 + TypeScript 6)
      │
      │ HTTP/SSE
      ▼
Backend (FastAPI 0.136 + Python 3.12)
      │
      ├── Swarm LangGraph (10+ agentes pedagógicos)
      ├── Consenso Determinista (4 voters)
      ├── Memoria Compartida (PostgreSQL)
      ├── Tracing Distribuido (W3C Trace Context)
      ├── Diagnóstico (22 detectores de anomalías)
      └── Eventos Idempotentes
      │
      ▼
PostgreSQL 16 (Alembic migrations)
```

---

## 3. Usuarios del Sistema

| Rol | Descripción |
|-----|-------------|
| **Admin** | CRUD usuarios, roles, configuración global |
| **Docente** | Gestión de cursos, recursos, evaluación |
| **Estudiante** | Test diagnóstico, rutas de aprendizaje, ejercicios |
| **Investigador** | Acceso a métricas, experimentos, reportes |

---

## 4. Ciclo de Aprendizaje

```
1. Onboarding → Test Diagnóstico (12 preguntas Likert)
2. Perfilamiento → Estilo, ritmo, preferencias
3. Ruta de Aprendizaje → Malla ISIA 2025 personalizada
4. Contenido Adaptativo → Videos, PDFs, interactivos
5. Evaluación → Ejercicios generados por IA
6. Retroalimentación → Agente tutor con memoria contextual
7. Replanificación → Ajuste continuo de la ruta
```

---

## 5. Swarm Pedagógico

9 fases de orquestación:

```
ENTERING → CONTEXT_LOADING → MEMORY_INIT
  → PEDAGOGICAL_ANALYSIS → ADAPTIVE_ADJUSTMENT
    → RISK_ASSESSMENT → CONSENSUS
      → INFERENCE → CONTENT_PRODUCTION → ACTIVE
```

### Agentes del Swarm

| Agente | Función |
|--------|---------|
| PedagogicalAgent | Detección de etapa cognitiva |
| StructuralPedagogicalAgent | Análisis estructural |
| AdaptiveAgent | Selección de pathway |
| AdaptiveLearningAgent | Adaptación continua |
| RiskAgent | Detección de riesgo académico |
| EvaluationAgent | Generación de ejercicios |
| ResearchAgent | Investigación de contenido |
| MultimodalPlanningAgent | Planeación de modalidades |
| PromptEngineeringAgent | Generación de prompts |
| ConsistencyAgent | Validación de coherencia |
| ConsensusMediatorAgent | Mediación de consenso |

### Pipeline Clásico (5 nodos)

```
diagnostic_analyzer → path_planner → content_recommender
  → evaluation_generator → risk_analyzer
```

### Pipeline Programación (3 nodos)

```
pseudocode_analyzer → debug_analyzer → ct_assessor
```

---

## 6. Consenso

4 voters deterministas:

| Voter | Base | Función |
|-------|------|---------|
| MasteryVoter | DB mastery scores | ¿Domina el prerrequisito? |
| PrereqVoter | DB course graph | ¿Completó prerrequisitos? |
| SequenceVoter | DB sequence order | ¿Orden pedagógico correcto? |
| TimeVoter | DB time windows | ¿Ventana de tiempo válida? |

Decisiones: `APPROVE`, `REJECT`, `ABSTAIN`

---

## 7. Memoria Compartida

- `SharedMemoryRecord` en PostgreSQL
- `publish_observation()` con dedup por content-hash
- `query()` por estudiante/módulo/tipo
- Conflict resolution por majority + confidence
- TTL por tipo: 30d (observación), 14d (inferencia), 7d (patrón), 3d (señal)

---

## 8. Eventos y Tracing

### Eventos
- Idempotencia con hot cache LRU + DB + advisory locks
- Outbox pattern para publicación confiable
- Replay de eventos con validación
- Propagación TTL (hop counting + decay + anti-feedback-loop)

### Tracing
- W3C Trace Context (`traceparent`, `tracestate`, `baggage`)
- Causation chain con depth tracking
- Correlation ID por request
- Logging estructurado con trace_id/span_id

---

## 9. Diagnóstico Automático

22 detectores de anomalías que monitorean:

| Categoría | Detectores |
|-----------|------------|
| Propagación | propagation_failure, propagation_storm, recursive_amplification, dag_traversal |
| Consenso | consensus_conflict, consensus_timeout, hung_consensus |
| Agentes | degraded_agent, slow_agent, agent_divergence, hallucination |
| Eventos | event_storm, retry_storm, deadlock |
| Memoria | staleness, sync_delay |
| Infra | circuit_breaker_storm, cascading_failure |

---

## 10. Experimentos (Benchmark)

5 condiciones para tesis:

| Condición | Descripción |
|-----------|-------------|
| full_swarm | Sistema completo (control) |
| uniform_weights | Pesos uniformes en consenso |
| single_agent | Agente único sin enjambre |
| no_trust | Sin scoring de confianza |
| no_specialization | Sin especialización |

Métricas: precision, recall, f1_score, adaptation_rate, consensus_time,
agent_agreement, memory_utilization
