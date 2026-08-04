# ADR-0011 — Retiro físico de BaseAgent / SwarmOrchestrator / AgentFactory y del laboratorio experimental que dependía de ellos

- **Estado:** Aceptado (2026-08-01)
- **Fecha:** 2026-08-01
- **Preserva:** `CLAUDE.md` § "Actualización 2026-07-12 (segunda)" (declaración
  original de retiro del flujo en vivo), `app/agents/__init__.py` (docstring
  de cuarentena: *"la eliminación física... ocurre cuando el laboratorio
  decida su propio destino"* — esta ADR es esa decisión), `docs/SWARM_ACTIVATION_AUDIT.md`
  (evidencia completa de alcanzabilidad, §§0,2,7,8 de ese documento)
- **Criterio de aceptación:** ver §5

## 1. Contexto

`CLAUDE.md` declaró el 2026-07-12 que `app/agents/*` (`BaseAgent` y
sus subclases) estaba retirado del flujo operativo en vivo, pero dejó su
eliminación física pendiente de una condición explícita, escrita en el
propio docstring de cuarentena de `app/agents/__init__.py`: *"Sus únicos
consumidores legítimos son el laboratorio experimental (`app/experiment`,
grupo de control de CONCEPT-0001/D-001)... La eliminación física de este
paquete ocurre cuando el laboratorio decida su propio destino — no
antes, no por partes."*

`docs/SWARM_ACTIVATION_AUDIT.md` (auditoría de pytest de esta misma
fecha, §§0, 2, 7 y 8) verificó exhaustivamente esa condición:

1. Ningún router registrado en `main.py` llega a una subclase de
   `BaseAgent`, a `SwarmOrchestrator` o a `AgentFactory` (§0, §2 — diez
   mecanismos de invocación indirecta descartados explícitamente:
   BackgroundTasks, Celery/RQ, scheduler, event bus externo, WebSocket/SSE,
   webhooks, dynamic dispatch, topología de despliegue, lifespan de
   FastAPI, grep exhaustivo del repositorio).
2. El flujo real del estudiante, trazado endpoint por endpoint (§8), no
   depende del sistema legacy en ninguna de sus cinco etapas con lógica
   adaptativa — tres de ellas (módulo, tutor, evaluación) ya están
   gobernadas por `backend/runtime/` (LangGraph) vía `runtime_bridge`/
   `runtime.boundary`.
3. El único consumidor real restante de `AgentFactory`/`app.agents.*` es
   `app/experiment/benchmark/real/executor.py` (vía
   `app/services/pedagogical_orchestration_service.py`), el laboratorio
   de benchmark "Legacy vs Runtime" que el docstring de cuarentena nombra
   explícitamente como la única condición pendiente.

La decisión de producto — confirmada explícitamente para esta ADR — es
que ese laboratorio ya cumplió su propósito: la arquitectura de tesis es
una única arquitectura multiagente coherente basada en LangGraph
(`backend/runtime/`), sin mantener una comparación activa contra la
arquitectura anterior. Con eso, la condición del docstring de cuarentena
queda satisfecha.

## 2. Decisión

Se elimina físicamente, en un único cambio:

- `app/agents/` completo (15 archivos: `base.py` y sus 11 subclases,
  `trace_builder.py`, `visual_designer_agent.py`, `__init__.py`).
- `app/swarm/orchestrator.py`, `app/swarm/agent_factory.py`, y su
  plumbing exclusivo (`detectors.py`, `events.py`, `lifecycle.py`,
  `metrics.py`, `synchronization.py`, `__init__.py`) — confirmado sin
  consumidores fuera de `app/swarm/` mismo.
- `app/services/pedagogical_orchestration_service.py` — único
  consumidor: el laboratorio que se retira en el mismo cambio.
- `app/experiment/benchmark/real/` completo (`executor.py`, `runner.py`,
  `mapper.py`, `noop_memory.py`, `safety.py`, `real_exports.py`,
  `__init__.py`) y `backend/scripts/run_real_benchmark.py` — el
  laboratorio "Legacy vs Runtime" mencionado en el docstring de
  cuarentena. El resto de `app/experiment/` (condiciones, escenarios,
  estadística, visualización, exportación genérica) no depende de
  `app.agents.*` y permanece intacto.
- Las funciones async huérfanas de `app/services/activation_service.py`
  (`_get_swarm_config_for_course`, `_activate_enrollment`,
  `activate_enrollment_with_swarm`, `activate_enrollments_for_course`,
  `activate_all_pending_for_student`) — sin llamadores reales, dependían
  de `SwarmOrchestrator`. El camino **sync** de ese mismo archivo
  (`activate_enrollments_for_course_sync`, `_activate_enrollment_sync`,
  `activate_enrollment_with_swarm_sync`, `_get_swarm_config_for_course_sync`)
  permanece intacto — es el que de verdad recibe tráfico y su relación
  con `academic_activation_service.py` sigue siendo una decisión de
  producto abierta y distinta (§3 de `SWARM_ACTIVATION_AUDIT.md`), fuera
  del alcance de esta ADR.
- `app/services/session_service.py` completo — confirmado sin
  consumidores reales (solo lo importaban los tests del sistema que se
  retira); su única función con lógica no trivial,
  `start_module_session`, existía únicamente para invocar
  `activate_enrollment_with_swarm`.

Se actualizan en el mismo cambio: los tests que ejercitaban
exclusivamente este código (dejan de tener sentido, no de fallar), y las
referencias documentales activas (`CLAUDE.md`).

## 3. Alternativas rechazadas

- **Eliminar solo `app/agents/*`, dejar el laboratorio intacto para no
  romperlo**: rechazada — es exactamente la coexistencia que el
  docstring de cuarentena prohíbe ("no por partes"), y perpetuaría un
  benchmark que ya no se usa contra un código que ya no existe en
  ningún otro lado.
- **Mantener el laboratorio vivo "por si acaso" para comparaciones
  futuras**: rechazada — la decisión de producto es que la comparación
  Legacy-vs-Runtime ya cumplió su propósito; mantener infraestructura
  sin uso activo contradice la regla de disciplina documental/de código
  de `CLAUDE.md` ("sin deuda técnica, sin código muerto").
- **Tocar también `academic_activation_service.py` / el camino sync de
  `activation_service.py` en este mismo cambio**: rechazada — ese
  conflicto (Ruta A vs Ruta B, `ACTIVO` inmediato vs. `PENDING_ACTIVATION`
  gated por docente) es una decisión de producto independiente,
  documentada por separado en `SWARM_ACTIVATION_AUDIT.md` §3, sin
  relación con la alcanzabilidad de `SwarmOrchestrator`.

## 4. Consecuencias

- `backend/runtime/` (LangGraph) queda como la única arquitectura
  multiagente activa del proyecto — sin una segunda implementación
  paralela que mantener, documentar o explicar en la sustentación.
- Se pierde la capacidad de volver a ejecutar el benchmark ablation
  "Legacy vs Runtime" (`run_real_benchmark.py`) sin revertir esta ADR.
  Cualquier resultado de ese benchmark que ya forme parte de la
  evidencia de tesis debe estar exportado (`real_exports.py` generaba
  CSV/JSON/reportes en `backend/benchmark_real_results/`, que no se
  toca en este cambio) antes de que se pierda la capacidad de
  regenerarlo.
- El conflicto Ruta A vs Ruta B en `academic_activation_service.py` /
  `activation_service.py` (camino sync) sigue abierto y sin resolver —
  esta ADR no lo toca ni lo resuelve.
- Los tests que verificaban específicamente el comportamiento de
  `BaseAgent`/`SwarmOrchestrator` (incluyendo los que la auditoría de
  pytest de esta misma rama corrigió en el commit `429e7a0` sobre
  `cleanup/audit-fixes`) se eliminan junto con el código que probaban —
  no se reescriben contra nada, porque no queda nada que probar.

## 5. Criterios de aceptación

1. `git grep` de `BaseAgent`, `SwarmOrchestrator`, `AgentFactory`,
   `PedagogicalOrchestrationService` (el de `app/services/`, no el de
   `weekly_pedagogy_service.py`) sobre `app/` no devuelve resultados
   fuera de comentarios/documentación histórica.
2. `pytest` completo corre sin `ImportError` ni `ModuleNotFoundError`
   causados por este cambio.
3. `backend/runtime/`, `runtime.boundary`, `runtime_bridge.py`,
   `SharedMemoryStore`, `ResearchAgent` y `ReviewerAgent` quedan
   bit-a-bit intactos.
4. `CLAUDE.md` ya no describe `app/agents/*` como código presente
   en el repositorio a la espera de retiro — refleja que el retiro ya
   ocurrió, con fecha y referencia a esta ADR.
