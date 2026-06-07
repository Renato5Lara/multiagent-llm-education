# 📋 SPRINT 2 — Reporte de Progreso (En Curso)

> **Proyecto:** UPAO-MAS-EDU — Sistema Multiagente Educativo con IA  
> **Equipo:** Equipo de Desarrollo MAS-EDU  
> **Sprint:** Sprint 2  
> **Período:** Semanas 8–11  
> **Estado:** 🔄 En Progreso (Semana 9 de 11)  
> **Progreso temporal:** 50% del Sprint (2 de 4 semanas completadas)  
> **Documento generado:** 05 de junio de 2026

---

## 1. Objetivo del Sprint (Sprint Goal)

> Evolucionar el sistema multiagente educativo hacia una arquitectura distribuida robusta y resiliente, implementando mecanismos avanzados de consenso multi-agente, monitoreo de salud, diagnósticos de enjambre (swarm), trazabilidad distribuida, memoria compartida, sandboxing seguro, benchmarking académico, explicabilidad pedagógica, y un dashboard de visualización del enjambre; sentando las bases para un sistema de IA educativa de nivel productivo con capacidades de auto-supervisión y transparencia algorítmica.

---

## 2. Backlog Planificado del Sprint

| # | Item del Backlog | Prioridad | Story Points | Estado |
|---|-----------------|-----------|:------------:|:------:|
| SP2-01 | Motor de consenso multi-agente | Alta | 21 | ✅ Completado |
| SP2-02 | Circuit breaker pattern | Alta | 13 | ✅ Completado |
| SP2-03 | Agent health monitoring | Alta | 13 | ✅ Completado |
| SP2-04 | Swarm diagnostics (20 detectores) | Alta | 21 | ✅ Completado |
| SP2-05 | Sistema de eventos distribuidos | Alta | 13 | ✅ Completado |
| SP2-06 | Distributed tracing | Media | 8 | ✅ Completado |
| SP2-07 | Shared memory & collective inference | Alta | 13 | ✅ Completado |
| SP2-08 | Replay cognitivo | Media | 13 | ✅ Completado |
| SP2-09 | Sandbox Docker | Alta | 8 | ✅ Completado |
| SP2-10 | Benchmark académico | Media | 8 | ✅ Completado |
| SP2-11 | Explainability pedagógica | Media | 8 | ✅ Completado |
| SP2-12 | Demo SSE orchestrator | Alta | 13 | ✅ Completado |
| SP2-13 | Frontend swarm dashboard | Alta | 13 | ✅ Completado |
| SP2-14 | Weekly learning module | Media | 5 | ✅ Completado |
| SP2-15 | Pedagogical orchestration service | Alta | 13 | ✅ Completado |
| SP2-16 | Integration testing completo | Alta | 8 | 🔲 Pendiente |
| SP2-17 | Optimización de rendimiento | Media | 5 | 🔲 Pendiente |
| SP2-18 | Ejecución completa de benchmarks | Media | 5 | 🔲 Pendiente |
| SP2-19 | Documentación final | Media | 5 | 🔲 Pendiente |
| SP2-20 | UI polish y mejoras responsive | Baja | 5 | 🔲 Pendiente |

**Total Story Points Planificados:** 211  
**Story Points Completados (Semana 9):** 183  
**Story Points Pendientes:** 28  
**Porcentaje de Completitud:** 86.7%

---

## 3. Items Completados (Semanas 8–9)

### SP2-01: Motor de Consenso Multi-Agente ✅

- **Descripción:** Implementación de un sistema de consenso sofisticado que permite a múltiples agentes IA llegar a acuerdos sobre contenido educativo generado.
- **Archivos implementados:**
  - `consensus.py` (51 KB) — Motor principal de consenso con algoritmos de votación, ponderación por expertise y resolución de conflictos
  - `consensus_timeouts.py` (34 KB) — Gestión de timeouts configurables para prevenir bloqueos indefinidos en el proceso de consenso
  - `consensus_cancellation.py` — Mecanismo de cancelación graceful de procesos de consenso en curso
  - `consensus_timeout_middleware.py` — Middleware FastAPI para aplicar timeouts a nivel de request en endpoints de consenso
  - `consensus_timeout_metrics.py` — Recolección de métricas de tiempos de consenso para análisis de rendimiento
- **Complejidad técnica:** Alta — Requirió diseño de algoritmos de votación ponderada, manejo de estados parciales, y recuperación ante fallos de agentes individuales.
- **Story Points:** 21

### SP2-02: Circuit Breaker Pattern ✅

- **Descripción:** Implementación del patrón circuit breaker para proteger el sistema contra fallos en cascada cuando los servicios de LLM o agentes individuales dejan de responder.
- **Archivos implementados:**
  - `circuit_breaker.py` (29 KB) — Implementación completa con estados CLOSED, OPEN, HALF-OPEN, contadores de fallos configurables, ventanas de tiempo, y callbacks de transición de estado
- **Estados del Circuit Breaker:**
  - **CLOSED:** Operación normal, las peticiones se envían al servicio
  - **OPEN:** Servicio detectado como no disponible, las peticiones fallan inmediatamente (fast-fail) con respuesta degradada
  - **HALF-OPEN:** Periodo de prueba donde se permite un número limitado de peticiones para verificar recuperación del servicio
- **Story Points:** 13

### SP2-03: Agent Health Monitoring ✅

- **Descripción:** Sistema completo de monitoreo de salud para cada agente del enjambre, con capacidad de detectar degradación de rendimiento y tomar acciones correctivas automáticas.
- **Archivos implementados (8 archivos):**
  - `monitor.py` — Monitor principal que recolecta métricas de salud de cada agente en tiempo real
  - `meta_monitor.py` — Meta-monitor que supervisa a los monitores individuales (observador del observador)
  - `health_scorer.py` — Algoritmo de scoring que calcula una puntuación de salud compuesta (0-100) basada en latencia, tasa de errores, calidad de respuestas y disponibilidad
  - `adaptive_degradation.py` — Lógica de degradación adaptativa que reduce la carga de un agente cuando su salud baja de umbrales configurados
  - `collective_stability.py` — Evaluación de estabilidad colectiva del enjambre como un todo, detectando correlaciones de degradación entre agentes
  - `behavioral_baseline.py` — Establecimiento de líneas base comportamentales para cada agente, permitiendo detectar anomalías estadísticas
  - `health_score_voter.py` — Sistema de votación para determinar el estado de salud cuando hay discrepancias entre métricas
- **Story Points:** 13

### SP2-04: Swarm Diagnostics ✅

- **Descripción:** Suite completa de 20 detectores de diagnóstico para identificar problemas en el enjambre de agentes en tiempo real.
- **Detectores implementados:**

| # | Detector | Función |
|---|----------|---------|
| 1 | `loop_detector` | Detecta bucles infinitos en cadenas de invocación entre agentes |
| 2 | `deadlock_detector` | Identifica situaciones de deadlock por dependencias circulares de recursos |
| 3 | `hallucination_detector` | Detecta respuestas alucinadas mediante validación cruzada entre agentes |
| 4 | `event_storm_detector` | Identifica tormentas de eventos que saturan el bus de mensajes |
| 5 | `propagation_detector` | Detecta fallos de propagación de información entre agentes |
| 6 | `anomaly_detector` | Identifica comportamientos anómalos mediante análisis estadístico |
| 7 | `conflict_detector` | Detecta conflictos semánticos entre respuestas de diferentes agentes |
| 8 | `resource_leak_detector` | Monitorea fugas de memoria y recursos no liberados |
| 9 | `timeout_detector` | Detecta patrones de timeout recurrentes en agentes específicos |
| 10 | `quality_drift_detector` | Identifica degradación progresiva en la calidad de respuestas |
| 11 | `consensus_failure_detector` | Detecta fallos sistemáticos en el proceso de consenso |
| 12 | `latency_spike_detector` | Identifica picos de latencia y sus causas probables |
| 13 | `cascade_failure_detector` | Detecta patrones de fallo en cascada entre agentes dependientes |
| 14 | `memory_overflow_detector` | Monitorea el uso de memoria compartida y detecta desbordamientos |
| 15 | `stale_state_detector` | Identifica estados obsoletos en agentes que no se actualizan |
| 16 | `bias_detector` | Detecta sesgos sistemáticos en las respuestas de agentes |
| 17 | `rate_limit_detector` | Monitorea y alerta sobre límites de tasa de APIs externas |
| 18 | `dependency_health_detector` | Evalúa la salud de dependencias externas (LLM APIs, BD, etc.) |
| 19 | `communication_breakdown_detector` | Detecta fallos en la comunicación inter-agente |
| 20 | `performance_regression_detector` | Identifica regresiones de rendimiento comparando con baseline |

- **Story Points:** 21

### SP2-05: Sistema de Eventos Distribuidos ✅

- **Descripción:** Infraestructura completa de eventos para comunicación asíncrona entre componentes del sistema.
- **Archivos implementados:**
  - `idempotency.py` — Garantiza que los eventos se procesen exactamente una vez, incluso en caso de reintentos
  - `outbox.py` — Patrón Transactional Outbox para garantizar consistencia entre la base de datos y el bus de eventos
  - `dedup.py` — Deduplicación de eventos basada en hashes de contenido y ventanas temporales
  - `distributed.py` — Bus de eventos distribuido con soporte para múltiples consumidores
  - `propagation_ttl.py` (28 KB) — Control de TTL (Time-To-Live) para propagación de eventos, evitando propagación infinita
  - `risk_detectors.py` (17 KB) — Detectores de riesgo que analizan patrones de eventos para identificar situaciones peligrosas
- **Story Points:** 13

### SP2-06: Distributed Tracing ✅

- **Descripción:** Sistema de trazabilidad distribuida para rastrear el flujo de requests a través del grafo multiagente.
- **Archivos implementados:**
  - `engine.py` (9 KB) — Motor de tracing con soporte para spans, contextos y propagación de trace IDs
  - `fastapi.py` — Middleware de tracing para FastAPI que inyecta trace context en cada request
  - `langgraph.py` — Integración con LangGraph para trazar la ejecución de cada nodo del grafo
  - `propagation.py` — Propagación de trace context entre servicios y entre agentes
- **Capacidades:**
  - Tracing de extremo a extremo: request HTTP → FastAPI → LangGraph → Agentes individuales → Respuesta
  - Correlación de spans padre-hijo para visualizar la jerarquía de ejecución
  - Metadata enriquecida por span: latencia, tokens consumidos, modelo LLM utilizado, resultado del agente
- **Story Points:** 8

### SP2-07: Shared Memory & Collective Inference ✅

- **Descripción:** Sistema de memoria compartida e inferencia colectiva que permite a los agentes acumular y aprovechar conocimiento colectivo.
- **Archivos implementados:**
  - `shared_memory.py` (21 KB) — Almacén de memoria compartida con control de concurrencia, TTL por entrada, y namespaces por sesión/estudiante
  - `collective_inference.py` (13 KB) — Motor de inferencia colectiva que combina las conclusiones de múltiples agentes para producir insights pedagógicos consolidados
  - `patterns.py` — Patrones de acceso a memoria compartida (lectura consistente, escritura atómica, broadcast, suscripción)
  - `memory_rules.py` — Reglas de gestión de memoria: políticas de evicción (LRU, TTL), límites por namespace, reglas de consolidación
- **Story Points:** 13

### SP2-08: Replay Cognitivo ✅

- **Descripción:** Sistema de replay que permite reproducir y analizar el proceso cognitivo de los agentes para fines de debugging, auditoría y mejora pedagógica.
- **Archivos implementados (14 archivos):**
  - `timeline.py` — Línea temporal de eventos cognitivos con resolución de milisegundos
  - `session_replay.py` — Reproductor de sesiones completas de interacción estudiante-agentes
  - `adaptation_replay.py` — Replay de las decisiones de adaptación pedagógica tomadas por los agentes
  - `reasoning_replay.py` — Visualización paso a paso del razonamiento de cada agente
  - `replay_exporter.py` — Exportación de replays a formatos JSON, HTML y Markdown para análisis offline
  - Archivos adicionales de soporte: parsers, formatters, filters, renderers, state snapshots, event correlators, diff analyzers, annotation engine, playback controller
- **Story Points:** 13

### SP2-09: Sandbox Docker ✅

- **Descripción:** Entorno de ejecución aislado basado en Docker para ejecutar código generado por los agentes de forma segura.
- **Archivos implementados:**
  - `runner.py` (10 KB) — Ejecutor de código en contenedores Docker efímeros con límites de CPU, memoria y tiempo
  - `policy.py` — Políticas de seguridad: lista blanca de librerías permitidas, restricciones de red, límites de filesystem, prohibición de operaciones peligrosas
- **Capacidades de seguridad:**
  - Contenedores efímeros que se destruyen después de cada ejecución
  - Límites de recursos: máximo 256 MB RAM, 1 CPU, 30 segundos de ejecución
  - Red deshabilitada por defecto (sin acceso a Internet desde el sandbox)
  - Filesystem de solo lectura excepto directorio temporal designado
  - Lista blanca de imports permitidos (numpy, pandas, matplotlib, etc.)
- **Story Points:** 8

### SP2-10: Benchmark Académico ✅

- **Descripción:** Framework de benchmarking para evaluar la calidad del contenido educativo generado por el sistema multiagente.
- **Archivos implementados:**
  - `runner.py` — Ejecutor de benchmarks con soporte para ejecución paralela y secuencial
  - `metrics.py` — Métricas de evaluación: relevancia pedagógica, dificultad apropiada, cobertura de objetivos, coherencia narrativa, precisión técnica
  - `datasets.py` — Cargador de datasets de referencia
  - `exporters.py` — Exportación de resultados a JSON, CSV y Markdown
- **Datasets JSONL incluidos (5 datasets):**
  1. Dataset de preguntas de programación Python (niveles básico-avanzado)
  2. Dataset de conceptos de bases de datos relacionales
  3. Dataset de algoritmos y estructuras de datos
  4. Dataset de ingeniería de software y patrones de diseño
  5. Dataset de evaluación de explicabilidad pedagógica
- **Story Points:** 8

### SP2-11: Explainability Pedagógica ✅

- **Descripción:** Módulo de explicabilidad que permite al docente y al estudiante entender por qué el sistema tomó determinadas decisiones pedagógicas.
- **Componentes implementados:**
  - `bloom_explainer.py` — Explica las decisiones del sistema en términos de la taxonomía de Bloom (recordar, comprender, aplicar, analizar, evaluar, crear). Muestra cómo el contenido generado se alinea con cada nivel cognitivo.
  - `cognitive_load_analysis.py` — Análisis de la carga cognitiva del contenido presentado al estudiante, basado en la teoría de carga cognitiva de Sweller. Detecta sobrecarga y sugiere simplificaciones.
  - `personalization_trace.py` — Trazabilidad completa de las decisiones de personalización: por qué se eligió un nivel de dificultad específico, por qué se priorizó un tema sobre otro, qué datos del estudiante influyeron en la decisión.
  - `adaptive_reasoning.py` — Explicación del razonamiento adaptativo: cómo el sistema ajusta su comportamiento basándose en el progreso y las interacciones previas del estudiante.
- **Story Points:** 8

### SP2-12: Demo SSE Orchestrator ✅

- **Descripción:** Orquestador de demostración basado en Server-Sent Events (SSE) para streaming en tiempo real de la actividad del enjambre.
- **Archivos implementados:**
  - `orchestrator.py` (24 KB) — Orquestador principal que coordina la ejecución del enjambre y emite eventos SSE en tiempo real
  - `memory.py` — Gestión de memoria de sesión para el orquestador
  - `events.py` — Definición de tipos de eventos SSE: agent_start, agent_thinking, agent_response, consensus_vote, consensus_result, error, health_update
- **Flujo SSE:**
  1. El frontend abre una conexión SSE al endpoint `/api/sse/stream`
  2. El orquestador recibe el request y activa el grafo multiagente
  3. Cada paso del grafo emite eventos SSE en tiempo real
  4. El frontend renderiza los eventos como una visualización interactiva del enjambre
- **Story Points:** 13

### SP2-13: Frontend Swarm Dashboard ✅

- **Descripción:** Dashboard interactivo de visualización del enjambre de agentes con 31 componentes de visualización.
- **Componentes implementados (31 componentes):**

  **Visualización del Grafo:**
  - `AgentNodeVisualization` — Representación visual de cada agente como nodo con indicador de estado
  - `GraphEdgeRenderer` — Renderizado de conexiones entre agentes con dirección y peso
  - `SwarmTopologyView` — Vista topológica completa del enjambre
  - `InteractiveGraphCanvas` — Canvas interactivo con zoom, pan y selección de nodos

  **Métricas en Tiempo Real:**
  - `AgentHealthGauge` — Indicador de salud individual por agente (gauge 0-100)
  - `LatencySparkline` — Gráfico sparkline de latencia por agente
  - `ConsensusProgressBar` — Barra de progreso del proceso de consenso
  - `TokenUsageCounter` — Contador de tokens consumidos por agente
  - `ErrorRateIndicator` — Indicador de tasa de errores

  **Paneles de Monitoreo:**
  - `SwarmOverviewPanel` — Panel resumen del estado general del enjambre
  - `DiagnosticsPanel` — Panel de diagnósticos activos y alertas
  - `CircuitBreakerStatus` — Estado visual de los circuit breakers
  - `MemoryUsagePanel` — Panel de uso de memoria compartida
  - `EventStreamViewer` — Visor de flujo de eventos en tiempo real (tipo terminal)
  - `TraceViewer` — Visualizador de traces distribuidos (tipo waterfall)

  **Replay y Análisis:**
  - `ReplayTimeline` — Línea temporal interactiva para replay cognitivo
  - `ReasoningStepViewer` — Visor paso a paso del razonamiento de agentes
  - `ExplainabilityCard` — Tarjeta de explicabilidad pedagógica
  - `BloomTaxonomyRadar` — Gráfico radar de cobertura de taxonomía de Bloom

  **Componentes de Layout y Soporte:**
  - `DashboardLayout`, `PanelContainer`, `MetricCard`, `StatusBadge`, `AlertBanner`, `LoadingOverlay`, `EmptyState`, `RefreshButton`, `TimeRangeSelector`, `FilterBar`, `ExportButton`, `FullscreenToggle`

- **Story Points:** 13

### SP2-14: Weekly Learning Module ✅

- **Descripción:** Módulo de aprendizaje semanal que estructura el contenido educativo en unidades semanales con objetivos, actividades y evaluaciones.
- **Archivos implementados (8 archivos):**
  - Modelos de datos para módulos semanales
  - Lógica de programación y distribución de contenido por semana
  - Integración con el sistema de progreso del estudiante
  - Generación automática de resúmenes semanales
  - Notificaciones y recordatorios por módulo
  - Métricas de completitud semanal
  - Adaptación dinámica de carga semanal según rendimiento del estudiante
  - Tests unitarios del módulo
- **Story Points:** 5

### SP2-15: Pedagogical Orchestration Service ✅

- **Descripción:** Servicio central de orquestación pedagógica que coordina todas las decisiones educativas del sistema.
- **Archivo principal:** Servicio de 25 KB que integra:
  - Selección dinámica de estrategias pedagógicas basada en el perfil del estudiante
  - Orquestación de la secuencia de contenido según prerequisitos y objetivos
  - Coordinación con el motor de consenso para validar decisiones pedagógicas
  - Integración con el módulo de explicabilidad para documentar cada decisión
  - Gestión de la ruta de aprendizaje adaptativa
  - Control de flujo pedagógico: diagnóstico → contenido → práctica → evaluación → refuerzo
  - Hooks para intervención del docente (override manual de decisiones del sistema)
- **Story Points:** 13

---

## 4. Items en Progreso

> **Nota:** Al cierre de la Semana 9, todos los items de desarrollo principal (SP2-01 a SP2-15) han sido completados. Los items restantes (SP2-16 a SP2-20) corresponden a tareas de aseguramiento de calidad, optimización y documentación planificadas para las Semanas 10–11.

Actualmente no hay items en estado "en progreso" — los items de desarrollo se cerraron al final de la Semana 9 y los items de QA/documentación aún no han iniciado formalmente.

---

## 5. Items Pendientes (Semanas 10–11)

### SP2-16: Integration Testing Completo 🔲

- **Descripción:** Suite completa de tests de integración que validen la interacción entre todos los módulos del sistema.
- **Alcance planificado:**
  - Tests de integración del flujo de consenso multi-agente de extremo a extremo
  - Tests de integración entre circuit breaker y health monitoring
  - Tests del pipeline SSE: orquestador → eventos → frontend
  - Tests de integración del sandbox Docker con el grafo LangGraph
  - Tests del flujo pedagógico completo: diagnóstico → generación → evaluación
  - Tests de integración de la memoria compartida con múltiples agentes concurrentes
- **Story Points:** 8
- **Semana estimada:** Semana 10

### SP2-17: Optimización de Rendimiento 🔲

- **Descripción:** Análisis y optimización del rendimiento del sistema en áreas identificadas como cuellos de botella.
- **Áreas a optimizar:**
  - Tiempo de respuesta del motor de consenso (objetivo: < 10 segundos para 4 agentes)
  - Uso de memoria del sistema de memoria compartida bajo carga concurrente
  - Rendimiento del bus de eventos distribuidos con alto volumen de mensajes
  - Optimización de queries a PostgreSQL (índices, query plans)
  - Caché de respuestas frecuentes de agentes para reducir llamadas a LLM
- **Story Points:** 5
- **Semana estimada:** Semana 10

### SP2-18: Ejecución Completa de Benchmarks 🔲

- **Descripción:** Ejecución completa de los 5 datasets de benchmark sobre el sistema estabilizado para obtener métricas de calidad definitivas.
- **Alcance planificado:**
  - Ejecución de los 5 datasets JSONL contra el sistema en producción
  - Análisis estadístico de resultados: media, mediana, desviación estándar, percentiles
  - Comparación con líneas base (modelos individuales sin consenso vs. con consenso)
  - Generación de reporte de benchmark con gráficos y conclusiones
  - Identificación de áreas donde el sistema multiagente supera al agente individual y viceversa
- **Story Points:** 5
- **Semana estimada:** Semana 10–11

### SP2-19: Documentación Final 🔲

- **Descripción:** Documentación técnica y de usuario completa del sistema.
- **Entregables planificados:**
  - README.md actualizado con instrucciones de instalación, configuración y ejecución
  - Documentación de la arquitectura del sistema multiagente (diagramas, flujos, decisiones de diseño)
  - Guía de uso para docentes y administradores
  - Documentación de API (complementaria a Swagger)
  - Guía de contribución y estándares de código
  - Actualización de ERRORES.md con errores del Sprint 2
- **Story Points:** 5
- **Semana estimada:** Semana 11

### SP2-20: UI Polish y Mejoras Responsive 🔲

- **Descripción:** Refinamiento visual y mejoras de responsividad del frontend.
- **Áreas planificadas:**
  - Mejoras responsive del swarm dashboard para tablets y móviles
  - Animaciones y transiciones suaves en cambios de estado del enjambre
  - Accesibilidad (ARIA labels, navegación por teclado, contraste)
  - Consistencia visual entre las páginas existentes (Sprint 1) y las nuevas (Sprint 2)
  - Loading states y empty states para todos los componentes del dashboard
  - Modo oscuro (si el tiempo lo permite)
- **Story Points:** 5
- **Semana estimada:** Semana 11

---

## 6. Riesgos Identificados

| # | Riesgo | Probabilidad | Impacto | Mitigación | Estado |
|---|--------|:------------:|:-------:|------------|:------:|
| R1 | **Complejidad del integration testing supera el tiempo disponible** | Alta | Alto | Priorizar tests de integración críticos (flujo de consenso, pipeline SSE). Automatizar con fixtures reutilizables. Diferir tests de menor prioridad si es necesario. | 🟡 Activo |
| R2 | **Rendimiento del motor de consenso insuficiente bajo carga real** | Media | Alto | El motor de consenso (51 KB) es complejo y aún no ha sido testeado bajo carga con múltiples usuarios concurrentes. Implementar profiling y load testing en Semana 10. Tener plan B con timeouts agresivos. | 🟡 Activo |
| R3 | **Costos de API de LLM durante ejecución de benchmarks** | Media | Medio | Los 5 datasets de benchmark generarán un volumen significativo de llamadas a APIs de LLM. Estimar costos antes de ejecutar. Considerar uso de modelos más económicos o caché de respuestas para ejecuciones repetidas. | 🟡 Activo |
| R4 | **Docker sandbox requiere Docker instalado en el entorno del evaluador** | Baja | Medio | Documentar claramente los prerrequisitos. Proporcionar un modo "mock" del sandbox que simule la ejecución sin Docker real para demos y evaluaciones donde Docker no esté disponible. | 🟢 Mitigado |
| R5 | **Deuda técnica acumulada por velocidad de desarrollo alta** | Alta | Medio | El ritmo de 183 SP en 2 semanas (~91 SP/semana) ha sido muy alto comparado con Sprint 1 (27 SP/semana). Existe riesgo de código con baja cobertura de tests o edge cases no considerados. Las Semanas 10-11 deben enfocarse en estabilización. | 🟡 Activo |
| R6 | **Fragmentación del dashboard con 31 componentes** | Media | Bajo | El dashboard con 31 componentes de visualización puede resultar confuso para el usuario final. Planificar sesión de UX review en Semana 11 para simplificar si es necesario. | 🟡 Activo |
| R7 | **Dependencia de servicios externos (LLM APIs) para demos** | Media | Alto | Si las APIs de LLM (OpenAI, etc.) experimentan latencia o downtime durante la demo final, el sistema se degradaría visiblemente. Implementar modo offline con respuestas pre-cacheadas para demo de respaldo. | 🟡 Activo |

---

## 7. Métricas Parciales del Sprint

### 7.1 Velocity Parcial

| Métrica | Valor |
|---------|-------|
| Story Points planificados (Sprint completo) | 211 |
| Story Points completados (Semana 9) | 183 |
| Story Points pendientes | 28 |
| Velocidad parcial (2 semanas) | **183 SP** |
| Velocidad promedio semanal (Semanas 8-9) | **91.5 SP/semana** |
| Velocidad Sprint 1 (referencia) | 27 SP/semana |
| Factor de aceleración vs Sprint 1 | **3.39x** |

> **Nota sobre la velocidad:** El incremento significativo de velocidad entre Sprint 1 (27 SP/semana) y Sprint 2 (91.5 SP/semana) se explica por: (a) la base de infraestructura ya establecida en Sprint 1 que aceleró el desarrollo, (b) mayor familiaridad del equipo con el stack tecnológico, (c) la naturaleza más modular de los items del Sprint 2 que permitió desarrollo paralelo, y (d) la complejidad real de algunos items pudo haber sido sobreestimada en story points.

### 7.2 Burndown Parcial (Semanas 8-9)

```
Story Points Restantes
211 |■
    |■
190 |  ■
    |
170 |
    |
150 |
    |
130 |
    |
110 |
    |
 90 |
    |
 70 |
    |
 50 |    
    |      ■ (Semana 9: 28 SP restantes)
 28 |      ■
    |
  0 |_ _ _ _ _ _ _ _ _ _ _
     S8   S9   S10  S11
```

- **Semana 8:** Se completaron los items de infraestructura avanzada: motor de consenso (SP2-01), circuit breaker (SP2-02), health monitoring (SP2-03), parte de swarm diagnostics (SP2-04), sistema de eventos (SP2-05), distributed tracing (SP2-06). ~110 SP quemados.
- **Semana 9:** Se completaron los items restantes de desarrollo: swarm diagnostics completo (SP2-04), shared memory (SP2-07), replay cognitivo (SP2-08), sandbox Docker (SP2-09), benchmark (SP2-10), explainability (SP2-11), SSE orchestrator (SP2-12), swarm dashboard (SP2-13), weekly learning (SP2-14), pedagogical orchestration (SP2-15). ~73 SP quemados.
- **Semanas 10-11 (proyección):** Quedan 28 SP correspondientes a integration testing, optimización, benchmarks, documentación y UI polish.

### 7.3 Distribución de Código por Módulo (Semana 9)

| Módulo | Archivos | Tamaño Aproximado |
|--------|:--------:|:-----------------:|
| Motor de consenso | 5 | ~95 KB |
| Circuit breaker | 1 | ~29 KB |
| Health monitoring | 8 | ~55 KB |
| Swarm diagnostics | 20 | ~80 KB |
| Sistema de eventos | 6 | ~60 KB |
| Distributed tracing | 4 | ~20 KB |
| Shared memory & inference | 4 | ~40 KB |
| Replay cognitivo | 14 | ~50 KB |
| Sandbox Docker | 2 | ~15 KB |
| Benchmark académico | 4 + 5 JSONL | ~30 KB |
| Explainability | 4 | ~25 KB |
| SSE orchestrator | 3 | ~30 KB |
| Frontend dashboard | 31 | ~90 KB |
| Weekly learning | 8 | ~35 KB |
| Pedagogical orchestration | 1 | ~25 KB |
| **Total Sprint 2** | **~115 archivos** | **~679 KB** |

### 7.4 Estado de Tests

| Área | Tests Existentes | Cobertura Estimada |
|------|:----------------:|:------------------:|
| Backend Sprint 1 (auth, courses, etc.) | 51 tests ✅ | ~72% |
| Motor de consenso | Tests unitarios básicos | ~40% |
| Circuit breaker | Tests de estados | ~60% |
| Health monitoring | Tests de scoring | ~35% |
| Swarm diagnostics | Pendiente integración | ~20% |
| Eventos distribuidos | Tests de idempotencia | ~45% |
| Sandbox Docker | Tests de políticas | ~50% |
| Frontend (todos los sprints) | Mínimos | ~10% |

> ⚠️ **Alerta:** La cobertura de tests de los módulos nuevos del Sprint 2 es inferior a la del Sprint 1. El item SP2-16 (Integration Testing) es crítico para cerrar esta brecha.

---

## 8. Plan para Semanas 10–11

### Semana 10 — Estabilización y Testing

| Día | Actividades Planificadas |
|-----|-------------------------|
| Lunes | Inicio de integration testing (SP2-16). Configurar fixtures y mocks para tests de consenso. |
| Martes | Tests de integración del pipeline SSE. Tests de circuito completo con sandbox Docker. |
| Miércoles | Profiling de rendimiento (SP2-17). Identificar cuellos de botella en consenso y eventos. |
| Jueves | Optimizaciones basadas en profiling. Inicio de ejecución de benchmarks (SP2-18). |
| Viernes | Continuar benchmarks. Análisis preliminar de resultados. Revisión de code coverage. |

**Objetivo de la semana:** Completar SP2-16 y SP2-17. Iniciar SP2-18.

### Semana 11 — Documentación, Polish y Cierre

| Día | Actividades Planificadas |
|-----|-------------------------|
| Lunes | Finalizar ejecución de benchmarks (SP2-18). Generar reporte de resultados. |
| Martes | Documentación técnica y de usuario (SP2-19). README, arquitectura, guías. |
| Miércoles | UI polish y mejoras responsive (SP2-20). Sesión de UX review del dashboard. |
| Jueves | Ensayo de la demo del Sprint. Correcciones finales. Buffer para imprevistos. |
| Viernes | **Demo del Sprint 2.** Retrospectiva. Cierre del Sprint. |

**Objetivo de la semana:** Completar SP2-18, SP2-19, SP2-20. Demo exitosa.

---

## 9. Comparativa Sprint 1 vs Sprint 2 (Parcial)

| Métrica | Sprint 1 (Final) | Sprint 2 (Semana 9) |
|---------|:-----------------:|:-------------------:|
| Duración | 4 semanas | 2 de 4 semanas |
| Story Points completados | 108 | 183 |
| Velocidad semanal | 27 SP/semana | 91.5 SP/semana |
| Items del backlog completados | 12/12 (100%) | 15/20 (75%) |
| Archivos nuevos creados | ~60 | ~115 |
| Tests unitarios | 51 | ~80 (estimado) |
| Complejidad técnica | Media-Alta | Muy Alta |
| Riesgos activos | 0 (todos resueltos) | 7 activos |

---

## 10. Conclusión Parcial

Al cierre de la Semana 9 (punto medio del Sprint 2), el equipo ha completado el **86.7% de los Story Points planificados** (183 de 211 SP), incluyendo todos los items de desarrollo de funcionalidad nueva (SP2-01 a SP2-15). El sistema multiagente ha evolucionado significativamente, incorporando:

- **Resiliencia:** Motor de consenso, circuit breaker, health monitoring, swarm diagnostics
- **Observabilidad:** Distributed tracing, replay cognitivo, explainability pedagógica
- **Escalabilidad:** Eventos distribuidos, memoria compartida, inferencia colectiva
- **Seguridad:** Sandbox Docker con políticas de aislamiento
- **Visualización:** Dashboard con 31 componentes para monitoreo del enjambre en tiempo real
- **Pedagogía:** Orquestación pedagógica, módulo semanal, benchmarking académico

Los **28 SP restantes** corresponden a tareas de aseguramiento de calidad (integration testing, benchmarks), optimización de rendimiento, documentación y polish visual, planificadas para las Semanas 10-11. El principal riesgo es la baja cobertura de tests de los módulos nuevos, que debe abordarse como prioridad en la Semana 10.

El equipo se encuentra en buena posición para completar el Sprint exitosamente si mantiene el enfoque en estabilización durante las últimas dos semanas.

---

*Documento elaborado como evidencia Scrum del Sprint 2 (progreso parcial) — Proyecto UPAO-MAS-EDU*  
*Semana 9 del cronograma académico*
