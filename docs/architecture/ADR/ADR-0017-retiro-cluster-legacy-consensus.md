# ADR-0017 — Retiro del clúster Legacy Consensus y preservación de `app/experiment/analysis.py`

- **Estado:** Propuesto (2026-08-06) — pendiente de aprobación explícita del
  tesista antes de ejecutar cualquier fase de §7.
- **Fecha:** 2026-08-06
- **Preserva:** `runtime/kernel/deliberation/*` (el motor de consenso vigente
  de la tesis, sin ninguna relación de código con este ADR), ADR-0011 (esta
  ADR extiende su mismo razonamiento a un hermano que quedó fuera de su
  alcance, no lo modifica), ADR-0012 (política del kernel — nombre similar,
  código distinto, sin relación), `app/api/routes/{swarm,replay}.py` +
  `app.memory.*` + `app.explainability.*` + el paquete `app.swarm_diagnostics`
  + `app.tracing` (directorio `app/tracing/`, distinto de
  `app/observability/tracing.py` — confirmado sin relación con el clúster
  que se retira, ver §2), `app/observability/{metrics_exporter,stream,
  tracing}.py` (consumidores reales; `metrics_exporter.py` pierde solo la
  sección "consensus" de su exportación — ver §4.3),
  `app/core/{__init__,config,security}.py` + `app/llm/{config,service,
  cost_tracker}.py` (infraestructura de toda la app, sin relación),
  `app/services/module_orchestration_service.py` (su lógica no cambia;
  solo deja de arrastrar una carga transitiva no deseada — ver §4), los 7
  archivos vivos de `app/replay/` (`__init__,session_replay,
  adaptation_replay,reasoning_replay,memory_replay,timeline_builder,
  replay_exporter.py` — motor real de Replay Cognitivo, RFC-0008 §3,
  importado por `app/api/routes/replay.py`; 9 de los 16 archivos del
  mismo directorio SÍ se retiran, ver §9.7 — lista completa en
  `PRESERVED_BACKEND_FILES` de `backend/scripts/
  audit_consensus_cluster.py`), `frontend/src/components/swarm/
  AgentActivityPanel.tsx` (único archivo vivo dentro de un directorio
  donde los otros 25 se retiran — usado por 4 páginas reales del
  estudiante, ver §4.1)
- **Criterio de aceptación:** ver §8

## 1. Contexto

La Auditoría Externa 2026-08-06 (hallazgo C1) reportó que
`app/core/consensus.py` (1,661 líneas) seguía vivo, registrado en `main.py`
y alcanzable por `/api/swarm/demo`, contradiciendo la afirmación de
`CLAUDE.md` (actualización 2026-08-01, ADR-0011) de que
`backend/runtime/` (LangGraph) es "la única arquitectura multiagente activa
del proyecto".

En vez de decidir sobre esa sola afirmación, se abrió una investigación
dedicada (Ficha C1) que rastreó imports exactos — no coincidencia de texto
— desde `app/core/consensus.py` hacia afuera, seguida de tres rondas de
revisión propia pedidas explícitamente por el tesista, cada una ampliando
el método: imports estáticos → `__init__.py` de paquete y tests uno por
uno → imports dinámicos (`importlib`, `React.lazy`, barrel files) → un
script versionado y determinista
(`backend/scripts/audit_consensus_cluster.py`) → un chequeo de
completitud que lista cada archivo que existe de verdad en los
directorios auditados, en vez de solo verificar una lista escrita a
mano. Esa última capa encontró 15 archivos más
(`app/core/consensus_cancellation.py` y `consensus_timeout_metrics.py`,
4 de `app/demo/`, 9 de `app/replay/`) que las tres rondas anteriores
nunca habían examinado. El hallazgo central: **no es un archivo aislado,
es un clúster de 88 archivos de producción** (59 backend + 29 frontend —
suma verificada archivo por archivo, reproducible con el script de §9)
que se retiran, 3 archivos que se editan sin borrarse
(`app/llm/__init__.py`, `app/observability/__init__.py`,
`app/observability/metrics_exporter.py` — ver §2), y 17 archivos de test
de los cuales 10 se retiran completos y 7 requieren edición quirúrgica
porque mezclan cobertura de código vivo con el clúster que se retira
(ver §4).

Esta ADR extiende — no reabre — el razonamiento que ADR-0011 ya aplicó el
2026-08-01 a `app/agents/`, `app/swarm/` y `app/experiment/benchmark/real/`:
que un laboratorio de comparación Legacy-vs-Runtime, una vez que "cumplió
su propósito" (decisión de producto ya tomada en ADR-0011 §1), se retira
físicamente en vez de mantenerse como deuda técnica. `docs/
SWARM_ACTIVATION_AUDIT.md` §8 (2026-08-01 — la evidencia que sostiene a
ADR-0011) ya había clasificado explícitamente `app/experiment/
orchestrator.py` y `app/demo/orchestrator.py` en esa misma categoría; ADR-
0011 simplemente no llegó a ejecutar el retiro sobre ellos.

## 2. Evidencia (hechos verificados, sin extrapolar)

**Método y su límite explícito.** Todo lo que sigue se verificó en dos
capas: (a) imports estáticos (`from X import Y` / `import X`, cabecera y
dentro de funciones) sobre el código fuente actual del repositorio, y (b)
una búsqueda dedicada de mecanismos que un grep de imports no vería —
`importlib`, `__import__`, `pkgutil`, `entry_points`, registro dinámico
por `getattr`/reflexión en el backend; `React.lazy`, `import()` dinámico,
archivos barrel (`index.ts`), Storybook y snapshots de test en el
frontend. Resultado de (b): el único uso de `importlib`/`__import__` en
todo `app/` vivo está en `app/sandbox/*`, y es código que **bloquea**
imports dinámicos (política de sandbox para código de estudiante), no que
los habilita; cero barrel files, cero `React.lazy`/`import()` dinámico,
cero Storybook (no configurado en el proyecto) tocando el clúster. Esto
no prueba matemáticamente la ausencia de cualquier dependencia posible
(p. ej. una ruta de importación construida por concatenación de strings
en tiempo de ejecución, en un lenguaje sin ese patrón detectable
estáticamente sería indetectable por definición) — prueba la ausencia de
los mecanismos de indirección que el propio código base usa en cualquier
otro lugar. El resto de esta sección usa "sin importador estático ni
dinámico encontrado" como la afirmación exacta; donde el texto dice
"confirmado" o "verificado", se refiere a este método de dos capas, no a
una garantía absoluta — el §9 (Inventario) trae esta misma verificación
desglosada archivo por archivo, generada por
`backend/scripts/audit_consensus_cluster.py` (versionado en el
repositorio, sin dependencias externas, determinista — dos corridas
consecutivas sobre el mismo commit producen el mismo texto byte a byte,
verificado), no transcrita a mano.

**Alcanzabilidad HTTP/frontend.**
`app/api/routes/swarm_demo.py` registra 8 endpoints reales bajo
`/api/swarm/demo` (`main.py:339`): `POST /run`, `GET /latest`,
`replay/{id}`, `replay/{id}/cognitive`, `replay/{id}/step/{i}`,
`replay/{id}/export`, `replay/{id}/stream`, `events/{id}`. Ninguno tiene
`Depends(get_current_*)`. `App.tsx:57` redirige `/swarm-demo → /evidencia`
sin montar `pages/demo/SwarmDemo.tsx`.

`SwarmDemo.tsx` importa 18 componentes propios de
`frontend/src/components/swarm/` (25.1K–1.6K cada uno) + `types/
swarmDemo.ts` + `hooks/useDemoSSE.ts`. La revisión de este ADR encontró
que ese directorio tiene **26 archivos, no una lista corta**: 25
dependen de `types/swarmDemo.ts` o de `types/replay.ts` (que a su vez
importa de `swarmDemo.ts`) y ninguno de los 25 tiene un importador
estático o dinámico (§método arriba) fuera de `components/swarm/` o de
`SwarmDemo.tsx` — verificado archivo por archivo con script, no por
muestreo (§9). El archivo 26, `AgentActivityPanel.tsx`, es la
excepción real: lo importan 4 páginas en vivo del estudiante
(`DiagnosticTest.tsx`, `Evaluation.tsx`, `KnowledgeTest.tsx`,
`ModuleLearningView.tsx`), y su propia fuente de datos
(`useLiveDeliberation`) no tiene relación con `types/swarmDemo.ts` ni con
el clúster de consenso. Mismo patrón de nombres confusamente similares ya
visto en el backend (`app.swarm_diagnostics` vivo vs
`app/observability/swarm_diagnostics.py` retirable): un directorio mixto,
no una unidad homogénea.

**Acoplamiento de arranque, no de invocación — mayor de lo que la primera
lectura de `app/llm/__init__.py` registró.**
El archivo completo (releído íntegro en la revisión de este ADR) importa
incondicionalmente, además de lo vivo (`LLMConfig`, `LLMService`,
`TokenBudgetTracker`), **seis piezas del clúster retirable**:
`ConfidenceCalibrator` (`app.llm.confidence` — no listado en el borrador
original de este ADR; su único otro consumidor es `app/llm/voters/
base.py`, también retirable), `LLMResponseParser`, `HallucinationGuard`,
`SwarmDeliberationOrchestrator`, `SwarmMetrics`, y los 5 `Voter`. Como
Python ejecuta el `__init__.py` de un paquete antes que cualquier
submódulo, `app/services/module_orchestration_service.py` (vivo, atiende
`POST /students/module/{id}/orchestrate`) arrastra la carga completa de
`app/core/consensus.py` en cada arranque a través de sus imports
—limpios y sin relación directa— de `app.llm.config.LLMConfig` y
`app.llm.service.LLMService`. Cero instanciación a nivel de módulo
(`TrustSystem()`, `ConsensusEngine()`) verificada en todo el clúster; cero
wiring en `lifespan()` de `main.py`.

**Segundo acoplamiento de arranque, encontrado en la revisión de este ADR.**
`app/observability/__init__.py` tiene el mismo patrón que `app/llm/
__init__.py`: importa incondicionalmente `swarm_diagnostics` y
`consensus_metrics` (ambos retirables) junto a `metrics_exporter`/`stream`
(ambos vivos). Peor aún, `app/observability/metrics_exporter.py` —vivo,
importado por el paquete `app.swarm_diagnostics` (vivo) y por
`app/integrations/tavily/{rate_limit,observability}.py` (vivo)— tiene una
dependencia real, no solo de carga, de `consensus_metrics.py`:
`consensus_metrics.metrics.get_snapshot()` alimenta directamente su
exportación estilo Prometheus (`swarm_consensus_total`,
`swarm_consensus_avg_latency_ms`, etc., `metrics_exporter.py:271,300,
361-373,445`). Retirar `consensus_metrics.py` sin antes editar
`metrics_exporter.py` rompería con `ImportError` un módulo que sí atiende
tráfico real. Sección "consensus" siempre reporta ceros en producción
(`ConsensusEngine` nunca corre), así que quitarla no pierde ninguna señal
real — pero es una edición quirúrgica de código vivo, no una eliminación
de archivo.

**Test files que mezclan código vivo con el clúster que se retira.**
7 de los 17 archivos de test bajo `tests/` no pueden borrarse enteros:
importan simultáneamente algo del clúster retirable y algo del paquete
vivo `app.swarm_diagnostics` (o de `app.observability.metrics_exporter`).
El caso más claro: `test_swarm_diagnostics.py` (780 líneas) tiene una sola
clase, `TestConsensusIntegration` (última del archivo, ~60 líneas), que
depende de `ConsensusEngine`; el resto —16 clases, ~720 líneas— prueba
exclusivamente el paquete vivo. Los otros 6 casos mixtos:
`test_diagnostics_integration.py`, `test_circuit_breaker.py`,
`test_consensus_timeouts.py`, `test_observability.py`,
`test_experiment_isolation.py`, `test_experiment_pipeline.py`.

**Propósito original superado, no simplemente antiguo.**
`docs/experimental_design.md` (último commit 2026-06-06, cero referencias
desde `RESEARCH_ITERATIONS.md`, `THESIS_SCOPE_FREEZE.md`,
`ROADMAP_THESIS_FOCUS.md` o `CLAUDE.md`) define el Experimento D / SH4:
medir si `ConsensusEngine` supera en precisión al voto individual — la
razón de ser original del clúster. La hipótesis vigente de
`RESEARCH_ITERATIONS.md` también invoca "consenso determinista", pero ese
consenso hoy se implementa en `runtime/kernel/deliberation/`
(`POLITICAS["v2"]`, D1/D2/D3 — cadena de iteraciones H10, ADR-0012 a
ADR-0016), un motor distinto construido después. `docs/
SWARM_ACTIVATION_AUDIT.md:296-302` ya deja escrito: *"`ConsensusEngine(` en
todo `app/`: solo aparece en `app/swarm/orchestrator.py` (muerto),
`app/experiment/orchestrator.py` (el grupo de control experimental
Legacy-vs-Runtime que CONCEPT-0001/D-001 reserva a propósito para
comparación, no tráfico real) y `app/demo/orchestrator.py` (el simulador
de /evidencia, tampoco tráfico real)."*

**Un archivo, y solo uno, está fuera de esta clasificación.**
`app/experiment/analysis.py` (ANOVA, Cohen's d, potencia estadística —
stdlib-only, cero import de `app.core.*`) fue registrado el 2026-07-08
(`RESEARCH_LAYER_TECHNICAL_REPORT.md` §9.2) como mejora futura para el
dashboard de investigación, y ejecutado por primera vez contra datos
reales de Postgres el 2026-08-05 (Iteración de Investigación 6.2:
`compute_anova`, `cohens_d=-0.492`, N=3). Es el único componente del
directorio `app/experiment/` con uso demostrado esta semana.

## 3. Decisión

Esta no es una decisión, son dos, ejecutadas en el mismo cambio pero
lógicamente independientes:

> **3.1 — Se retira de la superficie de producción el clúster Legacy
> Consensus completo** (motor de consenso heredado, sus 8 endpoints HTTP,
> el frontend asociado, y los tests/scripts que lo ejercitan).
>
> **3.2 — Se extrae `app/experiment/analysis.py`** a un módulo propio,
> fuera de `app/experiment/` (que de otro modo se retira entero), y
> permanece como infraestructura de investigación activa — sin mezclarse
> con el código de producción que se retira ni con el runtime.

No se decide en esta ADR *dónde* vive `analysis.py` tras la extracción
(candidato: `app/services/research_statistics.py`, para quedar junto a
`research_dashboard_service.py`, su consumidor planeado) — eso se resuelve
en la Fase 1 de §7, con el único criterio de que el destino no reintroduzca
ninguna dependencia hacia el clúster que se retira.

## 4. Alcance exacto del retiro (3.1)

**4.1 Archivos que se eliminan (88: 59 backend + 29 frontend)**

- `app/core/{consensus,circuit_breaker,specialization,trust,weighting,
  programming_voters,consensus_timeouts,consensus_timeout_middleware,
  consensus_cancellation,consensus_timeout_metrics}.py` (10 archivos —
  los últimos dos añadidos en la cuarta ronda de revisión: usan el único
  import relativo de todo `app/`, por eso el rastreo de imports
  absolutos de las rondas anteriores nunca los alcanzó — ver §9.1). **No**
  se retira `app/core/{__init__,config,security}.py` (config/auth de
  toda la app, sin relación).
- `app/llm/voters/{__init__,base,pedagogical,adaptive,evaluation,
  mediator}.py` (6) + `app/llm/prompts/{__init__,adaptive,deliberation,
  evaluation,pedagogical}.py` (5 — su único consumidor confirmado son los
  propios voters que se retiran) + `app/llm/{deliberation,grounding,
  metrics,response_parser,confidence}.py` (5 — `confidence.py` añadido en
  la revisión de este ADR, único otro consumidor: `app/llm/voters/
  base.py`) = 16 archivos. **No** se retira `app/llm/config.py`,
  `app/llm/service.py` ni `app/llm/cost_tracker.py` (usados por
  `module_orchestration_service.py` real).
- `app/observability/{consensus_metrics,swarm_diagnostics}.py` (2
  archivos — nombre confuso con el paquete vivo `app.swarm_diagnostics`,
  sin relación de código entre ambos, ver §1 "Preserva"; `consensus_metrics.py`
  requiere primero la edición de §4.3, no un borrado directo). **No** se
  retira `app/observability/{stream,tracing}.py` (consumidores reales:
  `app/replay/engine.py` — que a su vez no tiene consumidor propio, ver
  más abajo — y varios módulos vivos respectivamente).
- `app/demo/{orchestrator,__init__,events,memory,synthetic}.py` (5 — los
  4 últimos añadidos en la cuarta ronda; el borrador original solo tenía
  `orchestrator.py`) + `app/api/routes/swarm_demo.py` (1) = 6 archivos
- `app/replay/{export,session_store,models,replayer,serializer,
  timeline,engine,recorder,tracks}.py` (9 de los 16 archivos de
  `app/replay/` — añadidos en la cuarta ronda. Los otros 7 —
  `session_replay.py`, `adaptation_replay.py`, `reasoning_replay.py`,
  `memory_replay.py`, `timeline_builder.py`, `replay_exporter.py`,
  `__init__.py` — son el motor real de Replay Cognitivo, importados por
  `app/api/routes/replay.py` (router vivo, RFC-0008 §3) y **no** se
  tocan. `engine.py`, `recorder.py` y `tracks.py` están huérfanos
  incluso dentro del propio clúster muerto: ni siquiera `swarm_demo.py`
  los alcanza — ver §9.7)
- `app/experiment/{__init__,orchestrator,conditions,dataset,evaluation,
  pipelines,metrics,context,reset,export,report,anomaly,config,
  replay}.py` (14 de los 15 archivos de `app/experiment/` a nivel raíz —
  queda fuera únicamente `analysis.py`, §3.2). `anomaly.py`, `config.py`
  y `replay.py` no importan nada de `app.core.*`/`app.llm.*`/
  `app.demo.*` directamente, pero su único consumidor confirmado es la
  propia cadena que se retira (`report.py`, `orchestrator.py`,
  `scripts/run_experiment.py`) — sin extractor externo que los mantenga
  vivos, van con el resto.
- `scripts/run_experiment.py` + `scripts/run_baseline_experiment.py` (2)
- **Frontend (29 archivos, no 3 — corregido en la revisión de este ADR):**
  `frontend/src/pages/demo/SwarmDemo.tsx` + `frontend/src/hooks/
  useDemoSSE.ts` + `frontend/src/types/swarmDemo.ts` +
  `frontend/src/types/replay.ts` (importa de `swarmDemo.ts`, sin otro
  consumidor) + los 25 archivos de `frontend/src/components/swarm/`
  **excepto** `AgentActivityPanel.tsx` (`AdaptationEvolution`,
  `AdaptationReasoningPanel`, `AdaptiveTraceTimeline`,
  `BloomDecisionView`, `BloomProgressionView`, `CognitiveContinuityView`,
  `CognitiveLoadPanel`, `CognitiveReplayView`, `ConsensusTimeline`,
  `ContradictionViewer`, `DeliberationReplay`, `LiveSessionFeed`,
  `NarrativeConsistencyPanel`, `PedagogicalStructurePanel`,
  `PersonalizationReasoning`, `PersonalizationTimeline`,
  `PromptGroundingPanel`, `ReplayControls`, `ReplaySessionViewer`,
  `ReplayTimeline`, `RetrievalTimeline`, `SandboxValidationPanel`,
  `SharedMemoryReplay`, `SourceDiversityPanel`, `TrustEvolution.tsx`).
  Verificado archivo por archivo (no por muestreo): ninguno tiene
  importador fuera de `components/swarm/` o de `SwarmDemo.tsx` — ver §2.
  La entrada de ruta `/swarm-demo` en `App.tsx` es una edición, no un
  archivo que se borre.

**4.2 Tests — 10 se eliminan completos, 7 requieren edición quirúrgica**

Eliminación completa (prueban exclusivamente el clúster que se retira):
`test_adaptive_trust.py`, `test_async_safety.py`,
`test_collective_inference.py`, `test_consensus.py`,
`test_experimental_baseline.py`, `test_llm_deliberation.py`,
`test_llm_integration.py`, `test_llm_phase3.py`, `test_llm_voters.py`,
`test_cognitive_replay.py` (nuevo en la cuarta ronda — sus tres imports,
`app.demo.memory`, `app.replay.export`, `app.replay.session_store`, son
los tres huérfanos vía demo de §9.6/§9.7, ninguno del motor vivo de
Replay Cognitivo).

Edición quirúrgica (mezclan cobertura del clúster que se retira con
cobertura de código vivo — se elimina solo la clase/función que depende
del clúster, el resto del archivo permanece): `test_swarm_diagnostics.py`
(retirar únicamente `TestConsensusIntegration`, ~60 de 780 líneas),
`test_diagnostics_integration.py`, `test_circuit_breaker.py`,
`test_consensus_timeouts.py`, `test_observability.py`,
`test_experiment_isolation.py`, `test_experiment_pipeline.py` — ver
evidencia en §2.

**4.3 Archivos que se editan, no se borran**

- `app/llm/__init__.py`: deja de importar `ConfidenceCalibrator`,
  `LLMResponseParser`, `HallucinationGuard`, `SwarmDeliberationOrchestrator`,
  `SwarmMetrics` y los 5 `Voter` — conserva `LLMConfig`, `LLMService`,
  `TokenBudgetTracker` (§2).
- `app/observability/__init__.py`: deja de importar `swarm_diagnostics` y
  `consensus_metrics`; conserva `metrics_exporter`/`stream`.
- `app/observability/metrics_exporter.py`: se retira la sección
  `"consensus"` de su snapshot y de su exportación Prometheus
  (`metrics_exporter.py:271,300,361-373,445`) — siempre reportaba ceros en
  producción, no se pierde ninguna señal real.
- `app/main.py`: se retira la entrada `swarm_demo` del import de routers
  (línea 32) y el `include_router(swarm_demo.router)` (línea 339).
- `frontend/src/App.tsx`: se retira la entrada de ruta `/swarm-demo`.

## 5. Alternativas rechazadas

- **Retirar todo `app/experiment/` sin extraer `analysis.py` primero**:
  rechazada — perdería el único componente con uso de investigación
  demostrado esta semana (Iteración 6.2), y contradice la propia mejora
  futura ya registrada en `RESEARCH_LAYER_TECHNICAL_REPORT.md` §9.2.
- **Mantener el clúster completo "por si acaso" para una futura
  comparación de consenso**: rechazada — mismo razonamiento que ADR-0011
  §3 ya rechazó para su hermano: la comparación Legacy-vs-Runtime ya
  cumplió su propósito según la decisión de producto vigente, y
  `docs/SWARM_ACTIVATION_AUDIT.md` ya lo documenta así desde el
  2026-08-01.
- **Corregir en vez de retirar** (añadir auth a los 8 endpoints de
  `/api/swarm/demo`, mantener el clúster vivo): rechazada como decisión
  principal — el problema no es la falta de autorización, es que el
  motor no tiene ningún consumidor real; arreglar el síntoma (auth)
  dejaría intacta la causa (arquitectura duplicada que contradice
  ADR-0011). El hallazgo de autorización se documenta en §6 como
  beneficio secundario del retiro, no como justificación principal.
- **Ejecutar todo en un solo commit**: rechazada — viola la regla de
  "cambios pequeños" de `CLAUDE.md` (una responsabilidad arquitectónica
  por commit); se divide en las 6 fases de §7.

## 6. Consecuencias

**Positivas**

- `backend/runtime/` (LangGraph) queda, ahora sí sin excepciones, como la
  única arquitectura multiagente activa — cierra la contradicción textual
  con `CLAUDE.md`/ADR-0011 que motivó C1.
- Desaparece la carga transitiva de `app/core/consensus.py` en cada
  arranque del backend.
- Beneficio secundario de seguridad, no la razón principal de esta ADR:
  el retiro elimina además una superficie HTTP heredada de 8 endpoints
  sin autenticación (`/api/swarm/demo/*`), usada únicamente por
  componentes legacy y sin ninguna ruta de UI que la exponga hoy.
- `app/experiment/analysis.py` deja de estar mezclado con código de
  producción retirable y queda en una ubicación que refleja su rol real:
  infraestructura de investigación.

**Negativas**

- Se pierde la capacidad de volver a ejecutar `scripts/run_experiment.py`
  / `run_baseline_experiment.py` sin revertir esta ADR — ningún resultado
  de esos scripts forma parte hoy de la evidencia de tesis ya exportada
  (verificado: cero referencia desde `RESEARCH_ITERATIONS.md`).
- De los 17 archivos de test (10,171+ líneas) y los 149 tests de la suite
  de `app/experiment/`, 10 archivos se eliminan enteros junto con el
  código que probaban — no se reescriben, porque no queda nada que
  probar (mismo criterio que ADR-0011 §4). Los otros 7, incluidos
  `test_experiment_isolation.py` y `test_experiment_pipeline.py` (parte
  de esos 149), se editan quirúrgicamente (§4.2): pierden solo las
  clases/funciones que dependían del clúster, conservando su cobertura
  de código vivo.
- `docs/experimental_design.md` (Experimento D / SH4) queda documentando
  un diseño ya no perseguido — se anota como históricamente superseded en
  la Fase 6, no se borra (es evidencia de la evolución de la tesis).
- Requiere editar tres archivos que siguen siendo parte del camino en
  vivo (§4.3): `app/llm/__init__.py`, `app/observability/__init__.py` y
  `app/observability/metrics_exporter.py` — este último pierde
  permanentemente la sección `"consensus"` de su exportación Prometheus
  (siempre en cero hoy, pero deja de existir como posibilidad si el
  motor de consenso volviera a activarse sin revertir esta ADR).
- 7 de los 17 archivos de test (§4.2) requieren edición quirúrgica en vez
  de borrado directo — más trabajo de revisión que un retiro limpio, pero
  necesario para no perder cobertura de `app.swarm_diagnostics` (vivo).
- `app/experiment/benchmark/*` (M2, tercer subsistema de benchmark, fuera
  de alcance de este ADR) deja de ser importable ni siquiera de forma
  aislada, porque depende de `app/experiment/__init__.py` por semántica
  de paquete de Python (§9.8, nota). Sin consecuencia práctica hoy — no
  tiene consumidores propios — pero cierra la puerta a revivirlo sin
  antes revertir parte de esta ADR.

## 7. Plan de ejecución

Seis fases, cada una su propio commit. A diferencia del borrador
original de este ADR, **el código y los tests que lo cubren se retiran
en la misma fase** (mismo criterio que ADR-0011 §2) — así ninguna fase
deja `pytest` en rojo entre commits; solo la Fase 1 debe ir
obligatoriamente primero (nada se retira antes de confirmar qué se
preserva).

1. **Extraer `app/experiment/analysis.py`** a su ubicación final;
   verificar con `grep` que ningún import restante del clúster lo
   referencia; correr sus tests propios en el nuevo lugar.
2. **Cortar los dos acoplamientos de arranque**: editar
   `app/llm/__init__.py` (deja de importar `ConfidenceCalibrator`,
   `LLMResponseParser`, `HallucinationGuard`,
   `SwarmDeliberationOrchestrator`, `SwarmMetrics` y los 5 `Voter`),
   `app/observability/__init__.py` (deja de importar `swarm_diagnostics`/
   `consensus_metrics`) y `app/observability/metrics_exporter.py`
   (retira la sección `"consensus"` de su snapshot/exportación); confirmar
   que `module_orchestration_service.py`, `app.swarm_diagnostics` y la
   integración Tavily siguen en verde sin cambio de comportamiento.
3. **Retirar `/api/swarm/demo` completo, incluyendo su almacenamiento de
   replay muerto**: `app/api/routes/swarm_demo.py`, `app/demo/*` (5
   archivos), `app/replay/{export,session_store,models,replayer,
   serializer,timeline,engine,recorder,tracks}.py` (9 archivos — ninguno
   toca el motor vivo de `app/api/routes/replay.py`, ver §9.7), la línea
   de registro en `main.py`, `test_cognitive_replay.py` (eliminación
   completa, §4.2), y los 29 archivos frontend de §4.1
   (`pages/demo/SwarmDemo.tsx`, `hooks/useDemoSSE.ts`,
   `types/{swarmDemo,replay}.ts`, los 25 de `components/swarm/` salvo
   `AgentActivityPanel.tsx`, la entrada `/swarm-demo` de `App.tsx`) — una
   sola feature, un solo commit; confirmar que `frontend` compila, que
   `app/api/routes/replay.py` sigue funcionando (7 archivos de
   `app/replay/` intactos), y que las 4 páginas que usan
   `AgentActivityPanel.tsx` siguen renderizando.
4. **Retirar `app/core/*` (10 archivos, incl. `consensus_cancellation.py`
   y `consensus_timeout_metrics.py`), `app/llm/{voters,prompts,
   deliberation,grounding,metrics,response_parser,confidence}` y
   `app/observability/*`** (§4.1) junto con los tests que les
   corresponden: los 9 archivos de eliminación completa de §4.2
   (excluyendo `test_cognitive_replay.py`, ya retirado en la Fase 3), y
   la edición quirúrgica de `test_swarm_diagnostics.py`,
   `test_diagnostics_integration.py`, `test_circuit_breaker.py`,
   `test_observability.py` (retirar solo las clases/funciones que
   dependen del clúster).
5. **Retirar `app/experiment/*` (14 archivos) y `scripts/run_experiment.py`
   + `run_baseline_experiment.py`**, junto con la edición quirúrgica de
   `test_consensus_timeouts.py`, `test_experiment_isolation.py` y
   `test_experiment_pipeline.py`.
6. **Documentación y validación final**: anotar `docs/
   experimental_design.md` (Experimento D/SH4 → superseded, con cita a
   esta ADR) y `RESEARCH_LAYER_TECHNICAL_REPORT.md` §9.2 (actualizar
   destino de `analysis.py`); actualizar `CLAUDE.md` si describe el
   clúster como presente; correr `pytest` completo (sin `ImportError`/
   `ModuleNotFoundError` causados por este cambio, sin pérdida de tests
   fuera de los retirados deliberadamente); `git grep` de los patrones de
   §8.1 sobre `app/` sin resultados fuera de comentarios/documentación
   histórica; confirmar `backend/runtime/`, `runtime.boundary`,
   `runtime_bridge.py`, `module_orchestration_service.py`,
   `app/api/routes/{swarm,replay}.py` y sus dependencias (`app.memory.*`,
   `app.explainability.*`, `app.swarm_diagnostics`, `app.tracing`, los 7
   archivos vivos de `app/replay/`, `app/core/{config,security}.py`)
   bit-a-bit intactos.

## 8. Criterios de aceptación

1. Tras ejecutar las 6 fases, `python backend/scripts/audit_consensus_cluster.py`
   ya no encuentra los 88 archivos de §9 (fallan al no existir) y
   `completeness_check()` sigue pasando sobre lo que queda. Además,
   `reachability_check(simulate_edits=False)` (ya sin necesidad de
   simular nada, porque las ediciones ya están aplicadas de verdad)
   confirma 0 archivos del antiguo `CLUSTER_BACKEND` alcanzables desde
   `app.main` — es el criterio autoritativo, reemplaza cualquier
   `git grep` mantenido a mano. Alternativa manual equivalente si el
   script no puede correr:
   `git grep -nE "ConsensusEngine|TrustSystem|SpecializationTracker|from app\.core\.(consensus|consensus_cancellation|consensus_timeout_metrics)|from app\.demo\.|from app\.replay\.(export|session_store|models|replayer|serializer|timeline|engine|recorder|tracks)\b|from app\.llm\.voters|from app\.llm\.prompts|from app\.experiment\.(orchestrator|conditions|dataset|evaluation|pipelines|metrics|context|reset|export|report|anomaly|config|replay)|swarm_demo"`
   sobre `app/`, `scripts/` y `frontend/src/` sin resultados fuera de
   comentarios/documentación histórica.
2. `pytest` completo corre sin `ImportError` ni `ModuleNotFoundError`
   causados por este cambio; la suite completa no pierde tests además de
   los retirados deliberadamente en §4.2, y ningún test de
   `app.swarm_diagnostics` (el paquete vivo) desaparece.
3. `app/experiment/analysis.py` (en su nueva ubicación) sigue siendo
   stdlib-only y sus funciones (`compute_anova`, `cohens_d`,
   `generate_statistical_report`) se pueden invocar de forma aislada, sin
   importar nada del clúster retirado.
4. `metrics_exporter.export()` (Prometheus) ya no emite ninguna línea
   `swarm_consensus_*`, y su snapshot JSON ya no tiene la clave
   `"consensus"` — sin romper a sus consumidores reales (`app.
   swarm_diagnostics`, `app/integrations/tavily/*`).
5. `runtime/kernel/deliberation/*`, `app/api/routes/{swarm,replay}.py`,
   `app.memory.*`, `app.explainability.*`, `app.swarm_diagnostics`,
   `app.tracing`, `module_orchestration_service.py`,
   `app/core/{config,security}.py`, `app/llm/{config,service,
   cost_tracker}.py`, `app/observability/{stream,tracing}.py`, y los 7
   archivos vivos de `app/replay/` (§9.7) quedan bit-a-bit intactos salvo
   los tres archivos editados en §4.3.
6. `frontend/src/components/swarm/AgentActivityPanel.tsx` queda
   bit-a-bit intacto y `DiagnosticTest.tsx`, `Evaluation.tsx`,
   `KnowledgeTest.tsx`, `ModuleLearningView.tsx` lo siguen importando sin
   error; `pnpm build` (o `rtk pnpm build`) del frontend termina sin
   errores de módulo no encontrado.
7. `CLAUDE.md` ya no describe el clúster Legacy Consensus como presente
   en el repositorio a la espera de retiro — refleja que el retiro ya
   ocurrió, con fecha y referencia a esta ADR.

## 9. Inventario verificado (una fila por archivo)

Generado por `backend/scripts/audit_consensus_cluster.py` (no transcrito
a mano), pedido explícitamente por el tesista en la tercera ronda de
revisión de este ADR: "cuando esa tabla ya no cambie entre revisiones,
recién el ADR está maduro". Para regenerar esta sección tras cualquier
cambio en el código o en el alcance:

```
cd backend && python scripts/audit_consensus_cluster.py
```

**Cuarta ronda — el script deja de solo verificar, empieza a exigir
completitud.** La versión anterior verificaba una lista escrita a mano
(`CLUSTER_BACKEND`); no podía detectar un archivo que esa lista hubiera
olvidado — limitación que el propio tesista señaló explícitamente antes
de que se materializara. `completeness_check()` la cierra: lista TODO lo
que existe de verdad en cada directorio de `AUDITED_DIRECTORIES` y
detiene el script (`exit 1`) si algo no está en `CLUSTER_BACKEND`,
`EDITED_BACKEND_FILES`, `EXTRACTED_FILE` o `PRESERVED_BACKEND_FILES` (con
su razón). Corriéndolo por primera vez encontró 15 archivos que las tres
rondas anteriores nunca habían examinado — el total pasó de 73 a 88 (ver
§1). La lista sigue sin "descubrir" el clúster desde cero (sigue siendo
una lista con intención humana detrás), pero ahora es imposible que un
archivo quede fuera de vista sin que el script lo señale.

**Verificaciones de esta ronda, pedidas explícitamente:**
- Dos corridas consecutivas sobre el mismo commit producen exactamente
  la misma salida (`diff` vacío) — repetido después de cada cambio al
  script.
- Dos versiones del patrón de detección de imports frontend produjeron
  falsos positivos reales antes de esta versión (coincidencia de
  substring con nombres comunes como "replay", y coincidencia con
  literales de ruta de React Router como `"/replay"`) — ambos corregidos
  y verificados de nuevo antes de aceptar la salida.
- **Prueba de mutación** (inyectar un import real, confirmar detección,
  revertir): se añadió temporalmente `from app.core.consensus import
  ConsensusEngine` a `app/api/deps.py` (archivo vivo) — el script lo
  detectó correctamente como consumidor externo
  (`app/api/deps.py:248`); revertido, volvió a `ninguno`. Repetido con
  una variante multilínea (`from app.core.consensus import (\n
  ConsensusEngine,\n)`) y una con alias (`import app.core.trust as
  trust_alias`) — ambas detectadas correctamente. `deps.py` verificado
  byte a byte idéntico al original después de revertir (`diff` vacío) en
  los tres casos.
- **"Único import relativo de todo `app/`" — con la evidencia cruda, no
  solo la conclusión** (pedido explícito): `grep -rnE "^\s*from\s+\.+\w*\s+import" app --include="*.py"`
  devuelve exactamente una línea:
  `app/core/consensus_timeout_metrics.py:21:from .consensus_cancellation import CancellationReason`.

**Quinta ronda — `directory_sanity_check()`: ¿está completo
`AUDITED_DIRECTORIES` mismo?** Objeción del tesista, válida: `completeness_check()`
garantiza que todo archivo *dentro* de los directorios auditados esté
clasificado, pero esa lista de directorios sigue siendo manual — no
detectaría un directorio hermano completo si nadie lo agrega. Se añadió
`directory_sanity_check()`: lista los 26 directorios de primer nivel de
`app/`, y para cada uno de los 20 fuera de `AUDITED_DIRECTORIES`
comprueba (a) si algún archivo del clúster lo importa, y (b) si su
nombre sugiere relación (`consensus`, `swarm`, `legacy`, `voter`, `demo`,
`replay`). Correrlo por primera vez encontró **dos directorios reales
nunca examinados en ninguna ronda anterior**: `app/benchmark` (8
archivos — un tercer subsistema de benchmark completamente aislado, cero
imports de/hacia el clúster, único consumidor `tests/test_benchmark.py`;
análogo a `app/experiment/benchmark/`, M2 — fuera de alcance de este ADR
igual que M2, no se añade) y `app/events` (11 archivos — infraestructura
de outbox/idempotencia usada por `main.py`, `curriculum_service.py`,
`course_service.py` y más; sin ninguna relación con consenso). También
confirmó que `app/agents/` y `app/swarm/` (los directorios que ADR-0011
declaró retirados el 2026-08-01) solo contienen `.pyc` de `__pycache__`
— cero archivos `.py` reales, la aserción de ADR-0011 se sostiene. El
resultado no amplía el alcance de este ADR: ningún directorio nuevo se
suma a `CLUSTER_BACKEND`. **Es la primera ronda de las cinco donde el
total no cambió — se mantuvo en 88** (verificado con `diff` entre dos
corridas consecutivas sobre el mismo commit, igual que las rondas
anteriores).

**Sexta ronda — `reachability_check()`: alcanzabilidad real, no
aproximada por grep.** Pedido explícito del tesista: un análisis de
alcanzabilidad desde los puntos de entrada reales (`main.py`), no solo
"¿alguien importa este archivo?" por texto. En vez de aproximarlo con
otra expresión regular, el script importa `app.main` de verdad, en un
subproceso aislado, y lee `sys.modules` después — es la resolución de
imports real de Python, no una heurística. Primer resultado (estado
actual del repositorio, sin ediciones): **250 módulos `app.*` alcanzables
desde `app.main`, de los cuales 32 pertenecen a `CLUSTER_BACKEND`**. Esto
no contradice la clasificación "eliminar" — es la confirmación exacta,
con evidencia de más peso, de los dos acoplamientos de arranque que §2 ya
documentaba: los 15 archivos de `app/llm/*` alcanzables vía el import
incondicional de `app/llm/__init__.py`, los 2 de
`app/observability/{consensus_metrics,swarm_diagnostics}.py` vía
`app/observability/__init__.py`, y los 15 de `app/demo/*` +
`app/replay/{export,session_store,models,replayer,serializer,timeline}.py`
+ `app/api/routes/swarm_demo.py` vía el registro de `swarm_demo.router`
en `main.py`.

La pregunta que de verdad importa no es "¿qué es alcanzable hoy?" (ya
se sabía) sino **"¿qué queda alcanzable después de ejecutar el plan?"**
— `reachability_check(simulate_edits=True)` aplica, dentro del mismo
subproceso y con reversión garantizada por `try/finally` (el árbol de
trabajo real nunca se toca — verificado con `git diff --stat` después de
cada corrida, sin diferencias), los 4 recortes de import exactos de las
Fases 2 y 3 (§7: `app/llm/__init__.py`, `app/observability/__init__.py`,
`app/observability/metrics_exporter.py`, quitar el registro de
`swarm_demo` en `main.py`), y vuelve a importar `app.main`. Resultado:
**218 módulos `app.*`, cero de `CLUSTER_BACKEND` alcanzables** — los 32
archivos que dependían del acoplamiento de arranque quedan, todos,
inalcanzables tras el plan. `app.main` sigue importando sin error después
de las 4 ediciones simuladas — el plan no rompe el arranque del backend.
El script hace fallar la corrida (`exit 1`) si algún archivo de
`CLUSTER_BACKEND` sigue alcanzable tras la simulación, para que un futuro
cambio al plan que deje un cabo suelto se note de inmediato, no se
descubra en producción.

**Lo que esta ronda NO hace, a propósito.** El tesista pidió además una
"ejecución completa de backend, frontend y pruebas E2E" tras borrar los
88 archivos de verdad. Eso es un paso legítimo, pero pertenece a la
*ejecución* del ADR (Fase 6, §7: `pytest` completo tras cada fase; el
build de frontend en la Fase 3), no a su *aprobación* — ejecutarlo ahora
significaría borrar código de producción antes de que el ADR pase de
Propuesto a Aceptado, exactamente lo que este documento existe para
evitar. `reachability_check()` es la validación más fuerte posible sin
cruzar esa línea: usa la resolución de imports real de Python (no una
aproximación), simula el efecto neto de las 4 ediciones sin tocar el
árbol de trabajo, y dejaría cualquier archivo mal clasificado en
evidencia con `exit 1` — pero no reemplaza correr la suite completa
después de que las fases se ejecuten de verdad.

Columna "Consumidor externo" = resultado del método de dos capas de §2
(estático + dinámico); "ninguno" significa que ninguna de las dos capas
encontró uno, no que sea matemáticamente imposible que exista. Esta
tabla es el artefacto que debe permanecer estable entre futuras
revisiones — un
`git diff` de esta sección entre dos rondas de auditoría es la prueba de
madurez que el tesista pidió.

**9.1 Backend — `app/core/*` (categoría: motor de consenso heredado)**

| Archivo | Consumidor externo | Tests que lo cubren | Acción |
|---|---|---|---|
| `consensus.py` | ninguno | 15 archivos (todos los `test_*` de §4.2, incl. `test_swarm_diagnostics.py` solo en `TestConsensusIntegration`) | eliminar |
| `circuit_breaker.py` | ninguno | `test_circuit_breaker.py`*, `test_diagnostics_integration.py`* (*edición quirúrgica) | eliminar |
| `specialization.py` | ninguno | `test_adaptive_trust.py`, `test_experimental_baseline.py`, `test_consensus_timeouts.py`* | eliminar |
| `trust.py` | ninguno | `test_adaptive_trust.py`, `test_consensus_timeouts.py`*, `test_experiment_isolation.py`*, `test_experimental_baseline.py` | eliminar |
| `weighting.py` | ninguno | `test_adaptive_trust.py` | eliminar |
| `programming_voters.py` | ninguno | ninguno | eliminar |
| `consensus_timeouts.py` | ninguno | `test_consensus_timeouts.py`* | eliminar |
| `consensus_timeout_middleware.py` | ninguno | `test_consensus_timeouts.py`* | eliminar |
| `consensus_cancellation.py` | ninguno | `test_consensus_timeouts.py`* | eliminar |
| `consensus_timeout_metrics.py` | ninguno | `test_consensus_timeouts.py`* | eliminar |

Los últimos dos, **`consensus_cancellation.py` y `consensus_timeout_metrics.py`,
no estaban en ninguna versión anterior de este inventario** — se
encontraron en la cuarta ronda de revisión al añadir `completeness_check()`
al script (ver §9, intro): ambos usan un import relativo
(`from .consensus_cancellation import ...`), el único caso de import
relativo en todo `app/`, y por eso el rastreo de imports absolutos de las
tres rondas anteriores nunca los alcanzó por accidente — solo aparecieron
al listar directamente qué archivos existen de verdad en `app/core/`.

**9.2 Backend — `app/llm/voters/*` (categoría: voters LLM)**

| Archivo | Consumidor externo | Tests que lo cubren | Acción |
|---|---|---|---|
| `voters/__init__.py` | `app/llm/__init__.py` (se edita, §4.3) | `test_llm_deliberation.py`, `test_llm_voters.py` | eliminar |
| `voters/base.py` | `voters/__init__.py` (retirable) | ninguno directo | eliminar |
| `voters/pedagogical.py` | `voters/__init__.py` (retirable) | ninguno directo | eliminar |
| `voters/adaptive.py` | `voters/__init__.py` (retirable) | ninguno directo | eliminar |
| `voters/evaluation.py` | `voters/__init__.py` (retirable) | ninguno directo | eliminar |
| `voters/mediator.py` | `voters/__init__.py` (retirable) | ninguno directo | eliminar |

**9.3 Backend — `app/llm/prompts/*` (categoría: prompts LLM)**

| Archivo | Consumidor externo | Tests que lo cubren | Acción |
|---|---|---|---|
| `prompts/__init__.py` | `voters/{pedagogical,adaptive,evaluation,mediator}.py` (retirables) | `test_llm_integration.py` | eliminar |
| `prompts/adaptive.py` | igual | `test_llm_integration.py` | eliminar |
| `prompts/deliberation.py` | igual | `test_llm_integration.py` | eliminar |
| `prompts/evaluation.py` | igual | `test_llm_integration.py` | eliminar |
| `prompts/pedagogical.py` | igual | `test_llm_integration.py` | eliminar |

**9.4 Backend — `app/llm/{deliberation,grounding,metrics,response_parser,confidence}.py` (categoría: soporte LLM)**

| Archivo | Consumidor externo | Tests que lo cubren | Acción |
|---|---|---|---|
| `deliberation.py` | `app/llm/__init__.py` (se edita) | `test_llm_phase3.py`, `test_llm_deliberation.py` | eliminar |
| `grounding.py` | `app/llm/__init__.py` (se edita) | `test_llm_integration.py` | eliminar |
| `metrics.py` | `app/llm/__init__.py` (se edita) | `test_llm_phase3.py` | eliminar |
| `response_parser.py` | `app/llm/__init__.py` (se edita) | `test_llm_integration.py` | eliminar |
| `confidence.py` | `app/llm/__init__.py` (se edita) + `voters/base.py` (retirable) | ninguno directo | eliminar |

**9.5 Backend — `app/observability/*` (categoría: observabilidad)**

| Archivo | Consumidor externo | Tests que lo cubren | Acción |
|---|---|---|---|
| `consensus_metrics.py` | `metrics_exporter.py` (**vivo** — editar primero, §4.3) + `__init__.py` (se edita) | `test_experiment_isolation.py`*, `test_observability.py`* | eliminar (tras Fase 2) |
| `swarm_diagnostics.py` | `app/observability/__init__.py` (se edita) | `test_observability.py`* | eliminar |

**9.6 Backend — `app/demo/*` y la ruta `/api/swarm/demo` (categoría: demo HTTP)**

Ampliado en la cuarta ronda de revisión: el borrador anterior solo tenía
`orchestrator.py`. `completeness_check()` (script) encontró los otros 4
archivos del directorio.

| Archivo | Consumidor externo | Tests que lo cubren | Acción |
|---|---|---|---|
| `demo/orchestrator.py` | ninguno | ninguno | eliminar |
| `demo/__init__.py` | ninguno | `test_cognitive_replay.py`* | eliminar |
| `demo/events.py` | ninguno | ninguno | eliminar |
| `demo/memory.py` | ninguno | `test_cognitive_replay.py`* | eliminar |
| `demo/synthetic.py` | ninguno | ninguno | eliminar |
| `api/routes/swarm_demo.py` | `main.py` (se edita, línea de registro) | ninguno | eliminar |

**9.7 Backend — `app/replay/*` (categoría: réplica cognitiva — 9 de 16 archivos huérfanos, 7 son el motor real y se conservan)**

`app/api/routes/replay.py` (router **vivo**, RFC-0008 §3, mismo prefijo
que la Épica 4: Replay Cognitivo) importa 6 de los 16 archivos de este
directorio + `__init__.py` como paquete — esos 7 se conservan
(`PRESERVED_BACKEND_FILES` en el script: `session_replay.py`,
`adaptation_replay.py`, `reasoning_replay.py`, `memory_replay.py`,
`timeline_builder.py`, `replay_exporter.py`, `__init__.py`, este último
solo un docstring, sin imports que cortar). Los otros 9 se dividen en dos
grupos: 6 alcanzables solo desde `app/api/routes/swarm_demo.py`
(directa o indirectamente, vía `serializer.py`/`timeline.py`), y 3
(`engine.py`, `recorder.py`, `tracks.py`) huérfanos incluso dentro del
propio clúster muerto — ni el demo los alcanza.

| Archivo | Consumidor externo | Tests que lo cubren | Acción |
|---|---|---|---|
| `export.py` | ninguno | `test_cognitive_replay.py`* | eliminar |
| `session_store.py` | ninguno | `test_cognitive_replay.py`* | eliminar |
| `models.py` | ninguno | ninguno | eliminar |
| `replayer.py` | ninguno | ninguno | eliminar |
| `serializer.py` | `export.py` (retirable) | ninguno | eliminar |
| `timeline.py` | `session_store.py` (retirable) | ninguno | eliminar |
| `engine.py` | ninguno (huérfano incluso dentro del clúster) | ninguno | eliminar |
| `recorder.py` | ninguno (huérfano incluso dentro del clúster) | ninguno | eliminar |
| `tracks.py` | `engine.py` (retirable) | ninguno | eliminar |

**9.8 Backend — `app/experiment/*` (categoría: benchmark de experimento — distinto de `app/experiment/benchmark/`, M2, fuera de alcance)**

| Archivo | Consumidor externo | Tests que lo cubren | Acción |
|---|---|---|---|
| `__init__.py` | `app/experiment/benchmark/{__init__,orchestrator,metrics,exports,visualization}.py` — dependencia real, no falso positivo (ver nota abajo) | `test_experiment_isolation.py`*, `test_experimental_baseline.py`, `test_experiment_pipeline.py`* | eliminar |
| `orchestrator.py` | ninguno | `test_experiment_pipeline.py`* | eliminar |
| `conditions.py` | ninguno | `test_experimental_baseline.py` | eliminar |
| `dataset.py` | ninguno | `test_experiment_pipeline.py`* | eliminar |
| `evaluation.py` | ninguno | `test_experiment_pipeline.py`* | eliminar |
| `pipelines.py` | ninguno | `test_experimental_baseline.py` | eliminar |
| `metrics.py` | ninguno | `test_experimental_baseline.py`, `test_experiment_pipeline.py`* | eliminar |
| `context.py` | ninguno | `test_experiment_isolation.py`* | eliminar |
| `reset.py` | ninguno | ninguno | eliminar |
| `export.py` | ninguno | `test_experiment_pipeline.py`* | eliminar |
| `report.py` | ninguno | ninguno | eliminar |
| `anomaly.py` | `report.py` (retirable) | `test_experiment_pipeline.py`* | eliminar |
| `config.py` | `report.py`, `replay.py`, `orchestrator.py` (todos retirables) | `test_experiment_pipeline.py`* | eliminar |
| `replay.py` | `report.py` (retirable) | `test_experiment_pipeline.py`* | eliminar |
| `analysis.py` | — no aplica, se extrae (§3.2), no se elimina | tests propios, migran con el archivo | **extraer** |

**Nota sobre `app/experiment/__init__.py` — corrección encontrada corriendo
`scripts/audit_consensus_cluster.py`.** Una ronda anterior de este ADR
había descrito la dependencia de `app/experiment/benchmark/*.py` sobre
este archivo como "falso positivo" (razonando que solo importaban su
propio subpaquete `app.experiment.benchmark.*`, no `app.experiment`
directamente). Esa explicación era incorrecta: Python ejecuta el
`__init__.py` de CADA paquete ancestro antes de importar un submódulo —
la misma regla ya citada en §2 para `app/llm/__init__.py` y
`app/observability/__init__.py` — así que `from app.experiment.benchmark.
conditions import X` sí requiere que `app/experiment/__init__.py` se
ejecute primero. La dependencia es real. Lo que sí se mantiene es la
conclusión práctica: `app/experiment/benchmark/*` (M2, un tercer
subsistema de benchmark no documentado, fuera del alcance de este ADR)
no tiene NINGÚN consumidor propio fuera de sí mismo — verificado de
nuevo en esta corrección (`grep` sobre `app/`, `scripts/`, `tests/`
excluyendo el propio directorio, cero resultados). Retirar `app/
experiment/__init__.py` no rompe ningún flujo real porque `benchmark/`
tampoco lo tiene; sí lo deja permanentemente no-importable incluso de
forma aislada, una consecuencia menor que se documenta aquí en vez de
descartarse con una explicación incorrecta.

**9.9 Backend — scripts**

| Archivo | Consumidor externo | Tests que lo cubren | Acción |
|---|---|---|---|
| `scripts/run_experiment.py` | ninguno | n/a (script, no importado) | eliminar |
| `scripts/run_baseline_experiment.py` | ninguno | n/a (script, no importado) | eliminar |

**9.10 Backend — archivos editados, no eliminados**

| Archivo | Por qué sigue vivo | Qué pierde | Acción |
|---|---|---|---|
| `app/llm/__init__.py` | Importado transitivamente por `module_orchestration_service.py` (vivo) vía `app.llm.config`/`app.llm.service` | Imports de `ConfidenceCalibrator`, `LLMResponseParser`, `HallucinationGuard`, `SwarmDeliberationOrchestrator`, `SwarmMetrics`, 5 `Voter` | editar |
| `app/observability/__init__.py` | Importado por `app/replay/engine.py` (vivo, RFC-0008) vía `stream` | Imports de `swarm_diagnostics`, `consensus_metrics` | editar |
| `app/observability/metrics_exporter.py` | Consumido por `app.swarm_diagnostics` (vivo) y `app/integrations/tavily/*` (vivo) | Sección `"consensus"` de su snapshot/exportación Prometheus | editar |

**9.11 Frontend — `types/*` y archivos raíz del demo**

| Archivo | Consumidor externo | Acción |
|---|---|---|
| `pages/demo/SwarmDemo.tsx` | ninguno (`App.tsx` redirige sin montar) | eliminar |
| `hooks/useDemoSSE.ts` | `SwarmDemo.tsx` (retirable) | eliminar |
| `types/swarmDemo.ts` | los 24 componentes de 9.10 que lo importan directamente + `useDemoSSE.ts` + `SwarmDemo.tsx` + `types/replay.ts` (todos retirables) | eliminar |
| `types/replay.ts` | `ReplaySessionViewer.tsx` (retirable) | eliminar |

**9.12 Frontend — `src/components/swarm/*` (26 archivos: 25 se retiran, 1 se conserva)**

| Archivo | Consumidor externo | Acción |
|---|---|---|
| `AgentActivityPanel.tsx` | `DiagnosticTest.tsx`, `Evaluation.tsx`, `KnowledgeTest.tsx`, `ModuleLearningView.tsx` (4 páginas **vivas**) | **conservar** |
| `AdaptationEvolution.tsx` | ninguno | eliminar |
| `AdaptationReasoningPanel.tsx` | ninguno | eliminar |
| `AdaptiveTraceTimeline.tsx` | ninguno | eliminar |
| `BloomDecisionView.tsx` | ninguno | eliminar |
| `BloomProgressionView.tsx` | `SwarmDemo.tsx` (retirable) | eliminar |
| `CognitiveContinuityView.tsx` | ninguno | eliminar |
| `CognitiveLoadPanel.tsx` | ninguno | eliminar |
| `CognitiveReplayView.tsx` | `SwarmDemo.tsx` (retirable) | eliminar |
| `ConsensusTimeline.tsx` | `SwarmDemo.tsx` (retirable) | eliminar |
| `ContradictionViewer.tsx` | `SwarmDemo.tsx` (retirable) | eliminar |
| `DeliberationReplay.tsx` | `SwarmDemo.tsx` (retirable) | eliminar |
| `LiveSessionFeed.tsx` | `SwarmDemo.tsx` (retirable) | eliminar |
| `NarrativeConsistencyPanel.tsx` | `SwarmDemo.tsx` (retirable) | eliminar |
| `PedagogicalStructurePanel.tsx` | `SwarmDemo.tsx` (retirable) | eliminar |
| `PersonalizationReasoning.tsx` | ninguno | eliminar |
| `PersonalizationTimeline.tsx` | ninguno | eliminar |
| `PromptGroundingPanel.tsx` | `SwarmDemo.tsx` (retirable) | eliminar |
| `ReplayControls.tsx` | `SwarmDemo.tsx` (retirable) | eliminar |
| `ReplaySessionViewer.tsx` | ninguno | eliminar |
| `ReplayTimeline.tsx` | `SwarmDemo.tsx` (retirable); coincidencia de nombre benigna con la interfaz `ReplayTimeline` definida en `types/replay.ts` (no es un import del componente — verificado, §2) | eliminar |
| `RetrievalTimeline.tsx` | `SwarmDemo.tsx` (retirable) | eliminar |
| `SandboxValidationPanel.tsx` | `SwarmDemo.tsx` (retirable) | eliminar |
| `SharedMemoryReplay.tsx` | `SwarmDemo.tsx` (retirable) | eliminar |
| `SourceDiversityPanel.tsx` | `SwarmDemo.tsx` (retirable) | eliminar |
| `TrustEvolution.tsx` | `SwarmDemo.tsx` (retirable) | eliminar |

**Totales de esta sección** (deben cuadrar con §4.1/§4.2, y con la salida
real de `python scripts/audit_consensus_cluster.py` — "Total 'eliminar'
en esta corrida"): 59 archivos backend a eliminar (9.1–9.8, sin contar
`analysis.py` que se extrae) + 3 editados (9.10) + 29 frontend a eliminar
(9.11+9.12, sin contar `AgentActivityPanel.tsx` que se conserva) = **88
eliminados**, 3 editados, 2 conservados en su lugar (`analysis.py` se
muda, `AgentActivityPanel.tsx` se queda), y 15 archivos backend más
conservados explícitamente donde están (`PRESERVED_BACKEND_FILES` del
script: `app/core/{__init__,config,security}.py`,
`app/llm/{config,service,cost_tracker}.py`,
`app/observability/{stream,tracing}.py`, y los 7 de `app/replay/` de
§9.7 — `session_replay.py`, `adaptation_replay.py`, `reasoning_replay.py`,
`memory_replay.py`, `timeline_builder.py`, `replay_exporter.py`,
`__init__.py`). 17 archivos de test (16 + `test_cognitive_replay.py`,
nuevo en esta ronda) según el desglose de §4.2, marcados con `*` en
9.1–9.8 donde requieren edición quirúrgica en vez de eliminación
completa.
