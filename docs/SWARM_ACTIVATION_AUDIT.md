# Auditoría: Rutas de Activación de Enrollment y Alcanzabilidad del Swarm

- **Fecha:** 2026-08-01
- **Origen:** auditoría de la suite de pytest en la rama `cleanup/audit-fixes`
  (129 fallos/errores pre-existentes, desenmascarados al arreglar la
  colección de `test_tavily_*.py`). Este documento cubre únicamente el
  subconjunto que resultó ser una decisión de arquitectura, no un bug
  mecánico de tests.
- **Estado:** Resuelto para la parte de alcanzabilidad (2026-08-01) — ver
  `ADR-0011-retiro-fisico-baseagent-swarm-legacy.md`: `BaseAgent`,
  `SwarmOrchestrator`, `AgentFactory` y el laboratorio de benchmark
  "Legacy vs Runtime" fueron eliminados físicamente en la rama
  `architecture/remove-legacy-baseagent-swarm`. El conflicto Ruta A vs
  Ruta B (§3) sigue abierto — la ADR no lo toca. Lo que sigue, hasta la
  §9, describe el estado *previo* a esa decisión y es la evidencia sobre
  la que se tomó.
- **Estado (histórico, previo a ADR-0011):** Informativo — sin cambios de código todavía. Requiere
  decisión antes de tocar `activation_service.py`,
  `academic_activation_service.py` o los tests de
  `test_enrollment_lifecycle.py`.

## 0. Relación con `docs/CLAUDE.md` — esto NO es un hallazgo nuevo

Antes de nada: `docs/CLAUDE.md` § "Actualización 2026-07-12 (segunda)" ya
declara formalmente que `backend/app/agents/*` (`BaseAgent` y sus
subclases — `PedagogicalAgent`, `AdaptiveAgent`, `RiskAgent`,
`EvaluationAgent`, etc.) está **retirado del flujo operativo en vivo**,
verificado por una auditoría exhaustiva de esa fecha: *"ninguno [de los
routers registrados en `main.py`] alcanza una subclase real de
BaseAgent"*, con la única excepción del grupo de control experimental en
`app/experiment/benchmark/real/executor.py`.

Esta auditoría rastreó una cadena distinta (`activation_service.py` →
`SwarmOrchestrator` → `AgentFactory`) y confirma que llega exactamente a
esa misma familia de código ya declarada legacy:

```
app/swarm/orchestrator.py :: SwarmOrchestrator
  → app/swarm/agent_factory.py :: AgentFactory
    → app/agents/pedagogical_agent.py :: PedagogicalAgent
    → app/agents/adaptive_agent.py :: AdaptiveAgent
    → app/agents/risk_agent.py :: RiskAgent
    → app/agents/evaluation_agent.py :: EvaluationAgent
    → ... (resto de subclases de BaseAgent)
```

**Conclusión de esta sección:** lo que sigue no es una crisis nueva ni una
contradicción con `docs/CLAUDE.md` — es evidencia independiente, obtenida
por una ruta de auditoría distinta, que corrobora y extiende la decisión
de 2026-07-12 al *orquestador* que consume `BaseAgent` (que no había sido
nombrado explícitamente en esa auditoría), y documenta un bug concreto
dentro de esa misma maquinaria legacy. El tono de las secciones
siguientes debe leerse como "confirmación adicional", no como
descubrimiento.

## 1. Las tres rutas de activación de enrollment que existen hoy

| # | Módulo | Entrada real | Efecto en `Enrollment.status` | Crea `EducationalContext` | Invoca `SwarmOrchestrator` |
|---|---|---|---|---|---|
| A | `academic_activation_service.py::_ensure_enrollment` | `POST` que dispara `auto_enroll_from_curriculum` (auto-matrícula del estudiante) | `ACTIVO` inmediato, incluso reactiva enrollments existentes a `ACTIVO` | No | No |
| B | `activation_service.py` — camino **sync** (`_activate_enrollment_sync` / `activate_enrollment_with_swarm_sync`) | `POST /teacher-assignments` (`curriculum.py::create_teacher_assignment`, `def` sync) | `PENDING_ACTIVATION` → `ACTIVO` (solo tras asignar docente) | Sí — pero el log de la propia función dice literalmente *"legacy — setting ACTIVE directly, no swarm"* | **No, nunca** — la función no referencia `SwarmOrchestrator` en absoluto |
| C | `activation_service.py` — camino **async** (`_activate_enrollment` / `activate_enrollment_with_swarm`) | Ninguna — `activate_enrollments_for_course`, `activate_all_pending_for_student` y `session_service.start_module_session` tienen **cero** llamadores en `app/` fuera de sí mismos | `PENDING_ACTIVATION` → `INITIALIZING` → `ACTIVE`/`FAILED` con savepoint real | Sí | **Sí** — es la única de las tres que realmente lo hace |

La ruta C es la más completa (créditos por diseño: usa `AsyncSession`,
`AsyncUnitOfWork`, savepoints, y de verdad orquesta el swarm) pero está
completamente huérfana. Las rutas A y B sí reciben tráfico real, y
ninguna de las dos ejecuta el swarm.

## 2. Verificación exhaustiva de alcanzabilidad de `SwarmOrchestrator`

Antes de afirmar "inaccesible desde cualquier ruta FastAPI en
producción", se descartaron explícitamente los siguientes mecanismos de
invocación indirecta:

| Mecanismo | Resultado |
|---|---|
| `BackgroundTasks` de FastAPI | 0 usos en `app/` |
| Celery / RQ | no está en `requirements.txt`, 0 imports |
| Scheduler (APScheduler, cron, `@repeat_every`) | 0 usos |
| Event bus / señales | `SwarmEventBus`/`EventBus` existen, pero son plumbing **interno** del propio swarm (`app/swarm/events.py`, `app/swarm/detectors.py`) — no hay ningún consumidor externo que dispare `SwarmOrchestrator` desde fuera |
| WebSocket / SSE | Existen en `sandbox.py` y `swarm_demo.py`, pero `swarm_demo.py` usa `app.demo.orchestrator::SwarmDemoOrchestrator` — una clase completamente separada, sin relación de herencia ni de import con `app.swarm.orchestrator.SwarmOrchestrator` |
| Webhooks / n8n | 0 referencias en el repo |
| `importlib`, `getattr`/`globals()` dinámico, registro de plugins | 0 usos en las rutas ni en `activation_service.py` |
| Topología de despliegue (`docker-compose.yml`, `docker-compose.prod.yml`, `Procfile`) | Un único proceso de aplicación (`web: uvicorn app.main:app`) + Postgres. Sin worker separado, sin cola. |
| `app/main.py::lifespan` | Solo logging de arranque, verificación de conexión a DB y validación de API keys — ninguna referencia a activación o swarm |
| Grep exhaustivo del repo completo (excluyendo `tests/` y `__pycache__`) | Las únicas apariciones de `activate_enrollment_with_swarm(` y `SwarmOrchestrator(` fuera de su propia definición son los dos llamadores ya identificados (`activation_service.py:266` interno, `session_service.py:71`), ambos sin llamador propio |

Con estas diez verificaciones, la afirmación se sostiene como conclusión
respaldada por evidencia: **`SwarmOrchestrator` no se ejecuta desde
ningún proceso que corra en este despliegue**, hoy.

## 3. El conflicto Ruta A vs. Ruta B (`academic_activation_service` vs. `activation_service`)

Esto **no es un bug de tests** — son dos modelos de negocio distintos
coexistiendo:

- Ruta A (`_ensure_enrollment`, 2026-06-04): matrícula = activación
  inmediata, sin distinción de si hay un docente asignado.
- Ruta B (`_activate_enrollment_sync`, 2026-06-06, dos días después):
  matrícula queda `PENDING_ACTIVATION` hasta que un docente se asigna al
  curso — invariante que `test_activation_only_when_teacher_assigned`
  verifica explícitamente y que Ruta A viola en cuanto se ejecuta
  primero (que es siempre, porque `auto_enroll_from_curriculum` es lo
  que crea el enrollment).

`test_enrollment_lifecycle.py` (9 fallos) asume el invariante de la Ruta
B pero ejercita un flujo (`auto_enroll_from_curriculum` → luego
`create_course_from_institutional`) que pasa primero por la Ruta A, que
ya dejó el enrollment en `ACTIVO`. Cualquier corrección debe decidir cuál
invariante es el vigente — no se resuelve tocando únicamente los tests.

## 4. El bug de `_get_swarm_config_for_course_sync` — impacto acotado

`activation_service.py:58-70`:

```python
def _get_swarm_config_for_course_sync(db: Session, course: Course) -> dict:
    try:
        from app.services.programming_course_service import detect_programming_course as _detect_sync
        profile = _detect_sync(db, course)          # async def sin await
        if profile.is_programming_course:            # AttributeError: coroutine
            return get_programming_swarm_config()
    except Exception:
        logger.warning(...)                           # agregado en 9129c53, 2026-07-23
    return {...config por defecto de 4 agentes...}
```

- Introducido en el mismo commit que creó la función async
  (`5a1fb44`, 2026-06-06). Corrió en silencio (sin log) hasta
  `9129c53` (2026-07-23).
- **Impacto real, dado el hallazgo de la §2: ninguno funcional.** La
  Ruta B (la única que llega a esta función) nunca invoca
  `SwarmOrchestrator` de todas formas — el `swarm_config` que esta
  función calcula se guarda en `EducationalContext.swarm_config` pero
  no gobierna ninguna ejecución real de agentes. El único efecto
  observable es cuál de los dos diccionarios estáticos (4 agentes vs. 7)
  queda persistido en esa columna — cosmético mientras la Ruta B siga
  siendo "legacy, no swarm" por diseño.

## 5. Alternativas consideradas

| Opción | Descripción | A favor | En contra |
|---|---|---|---|
| **(a) Duplicar** `detect_programming_course_sync` (~40 líneas, misma lógica de scoring contra `Session` síncrona) | Arregla solo `_get_swarm_config_for_course_sync` | Cambio pequeño y contenido | No arregla nada funcional (§4) — la Ruta B sigue sin ejecutar el swarm. Introduce una segunda copia de la lógica de scoring que hay que mantener sincronizada. Va en contra de la dirección ya declarada del proyecto (BaseAgent retirado). |
| **(b) Migrar** `curriculum.py::create_teacher_assignment` + las 3 funciones de `curriculum_service.py` a async, apuntando a la Ruta C ya existente | Conecta por primera vez la maquinaria async/`SwarmOrchestrator` a una petición real | Reutiliza código ya escrito y probado (Ruta C); la infraestructura async (`aget_db`, `aget_uow`, `AsyncUnitOfWork`) ya existe | Sería reactivar deliberadamente la familia `BaseAgent`/`SwarmOrchestrator` que `docs/CLAUDE.md` ya declaró legacy y en camino a eliminación física — remar contra la dirección arquitectónica vigente del proyecto (migración a `backend/runtime/` LangGraph) |
| **(c) No tocar la detección; simplificar la Ruta B** — eliminar el intento de detección de curso de programación en `_get_swarm_config_for_course_sync` y devolver siempre el config por defecto (o eliminar la función y hardcodear un único dict) | Elimina el bug sin duplicar lógica ni reactivar BaseAgent | Mínimo, coherente con "Ruta B es legacy y no ejecuta swarm de todas formas" | El campo `swarm_config` deja de reflejar ninguna detección real — honesto sobre lo que la Ruta B realmente hace hoy, pero renuncia a la distinción 4 vs. 7 agentes por completo |
| **(d) No hacer nada por ahora** | Dejar el bug como está, documentado | Cero riesgo, cero esfuerzo | El log de warning sigue ensuciando logs de producción en cada activación de docente; el campo `swarm_config` sigue siendo engañoso (sugiere detección real que nunca ocurre) |

## 6. Recomendación

Dado que la Ruta C (`SwarmOrchestrator` real) depende de la familia
`BaseAgent` ya declarada legacy en `docs/CLAUDE.md`, la opción **(b)
migrar** no parece la dirección correcta — sería invertir esfuerzo en
reconectar una arquitectura que el propio proyecto ya decidió
descontinuar, en lugar de avanzar hacia `backend/runtime/` (LangGraph),
que es donde `docs/CLAUDE.md` dirige explícitamente todo desarrollo
nuevo de agentes/orquestación.

Entre (a), (c) y (d): (a) no resuelve nada funcional y añade deuda; (c)
es honesto y mínimo pero renuncia a la distinción de configs; (d) no
cuesta nada pero deja logs sucios y un campo engañoso. Sin más contexto
sobre si `EducationalContext.swarm_config` se lee en algún otro lugar
(frontend, reporting, investigación) de un modo que dependa de la
distinción 4 vs. 7 agentes, no hay evidencia suficiente para preferir
(c) sobre (d) o viceversa — es la pregunta que falta responder antes de
decidir.

No se ha modificado ningún archivo de código para esta auditoría. El
conflicto de la §3 (Ruta A vs. Ruta B) y la elección entre (a)/(c)/(d)
de la §5 quedan pendientes de decisión explícita antes de abrir una
rama de trabajo.

## 7. Adenda 2026-08-01 — ¿reemplazó LangGraph a `BaseAgent`, o solo coexisten?

Pregunta de seguimiento tras la §0: ¿el reemplazo de `BaseAgent` por
`backend/runtime/` (LangGraph) está completo, o es una migración a
medias con dos arquitecturas activas simultáneamente? Se auditó router
por router de `main.py` (22 routers registrados) y se rastreó cada
import por su ruta exacta, replicando el método que `docs/CLAUDE.md`
ya usó el 2026-07-12.

**Hallazgo: no son dos, son tres cosas coexistiendo, y las tres siguen
vigentes salvo la primera:**

1. **`app.agents.*` / `SwarmOrchestrator` / `AgentFactory`** — confirmado
   inalcanzable (§0, §2). Candidato real a eliminación física, pero solo
   cuando se cumpla el criterio que `docs/CLAUDE.md` ya fijó
   explícitamente: *"cuando `backend/runtime/` alcance paridad funcional
   end-to-end"*. Esa es una pregunta de producto (¿qué le falta al
   runtime para cubrir lo que hacía la ruta legacy?), no algo que un
   grep pueda decidir por sí solo.

2. **Clases de agente independientes, sin herencia de `BaseAgent`**
   (`ResearchAgent`, `ReviewerAgent` en `app/services/research_agent.py`
   / `reviewer_agent.py`) — **vivas y en uso real**, instanciadas en
   `WeeklyPedagogyOrchestrationService`
   (`app/services/weekly_pedagogy_service.py:434,441`), alcanzada desde
   `POST` en `app/api/routes/pedagogy.py` (router registrado). Esto
   corrobora, con una ruta de auditoría distinta, la nota de
   `docs/CLAUDE.md`: *"ResearchAgent y ReviewerAgent... no heredan de
   BaseAgent"*. Confirma además algo relevante para el ítem pendiente de
   la auditoría anterior de pytest: el `ResearchAgent` real que
   `test_research_agent.py` prueba con una firma obsoleta
   (`agent_name=`, `uow=`) es exactamente esta clase viva — el
   diseño simple actual (`ResearchAgent()`, sin argumentos, tal como se
   instancia aquí) es el vigente; los tests son los que están
   desactualizados, no el código.

3. **`backend/runtime/` (LangGraph) vía el Platform Boundary** — confirmado
   vivo y cableado: `app/api/routes/runtime.py` (450 líneas, router
   `runtime_boundary_routes` registrado en `main.py:348`) expone
   `POST /sessions`, `POST /hechos`, `GET .../traza`, `GET .../estado`,
   `GET .../memoria`, `GET .../replay`, `POST .../hechos-docente`,
   `POST .../escaladas/resolver` — con dependencias de auth reales
   (`aget_current_estudiante`, `aget_current_docente`). El frontend lo
   consume mediante hooks dedicados (`useRuntimeTrace`,
   `useRuntimeEstado`, `useRuntimeMemoria`, `useRuntimeReplay`,
   `useRuntimeEscaladas`, `useRuntimeHitl`), pero **todos esos usos
   confirmados están en `pages/evidencia/RuntimeConsole.tsx` y
   `components/observability/*`** — es decir, en el "Modo Evidencia" de
   observación/replay que describe `docs/CLAUDE.md`, no en componentes
   del flujo de estudiante (`DiagnosticTest.tsx`,
   `ModuleExperienceView.tsx`, etc.).

**Lo que queda sin verificar, explícitamente:** no encontré, en el
frontend, ninguna llamada directa a `POST /runtime/sessions` o
`POST /runtime/hechos` fuera de esos hooks de observabilidad — lo cual
sugiere que la apertura de sesión/registro de hechos ocurre del lado del
servidor (candidato: `app/services/pedagogy_runtime_bridge.py`, que
`ADR-0009 §6` ya documenta como *"segundo consumidor legítimo... invoca
al Boundary desde el flujo de evaluación (no HTTP directo, sino
orquestación de servicio)"*), pero no rastreé esa cadena completa hasta
el flujo real de diagnóstico/módulo/tutor del estudiante. **No afirmo
que el flujo adaptativo completo del estudiante ya corra 100% sobre
LangGraph** — solo que el Boundary está vivo, cableado, y consumido por
al menos el Modo Evidencia y (indirectamente, vía `pedagogy_runtime_bridge`)
el flujo de evaluación semanal. Confirmar el resto requeriría trazar
`pedagogy_runtime_bridge.py` y los servicios de diagnóstico/módulo/tutor
uno por uno — no lo hice todavía porque excede el alcance de "verificar
antes del ADR" y entra en el terreno de "Fase 3+" que se pidió no
ejecutar aún.

**Conclusión de la adenda:** no hay una migración "a medias" en el
sentido de confusión accidental — `docs/CLAUDE.md` ya documenta esta
coexistencia como una estrategia deliberada con un criterio de cierre
explícito. Lo que sí falta, y no se puede responder desde el código
solo, es si ese criterio ("paridad funcional end-to-end") ya se cumplió.
Esa es la pregunta que decide si la Fase 3 (eliminación) tiene sentido
ahora o todavía no.

## 8. Adenda 2026-08-01 (segunda) — trazado end-to-end del flujo del estudiante

Se rastreó cada endpoint real que el frontend del estudiante invoca
(`frontend/src/hooks/useStudent.ts` → `backend/app/api/routes/students.py`
→ servicio → lo que ese servicio toca), con cita de archivo y línea.
Login se omite por no ser relevante a la lógica adaptativa (JWT estándar).

| Etapa | Endpoint | Servicio | ¿Usa `runtime.boundary`/LangGraph? | ¿Usa legacy (`SwarmOrchestrator`/`ConsensusEngine`/`BaseAgent`)? | Estado |
|---|---|---|---|---|---|
| Diagnóstico inicial | `POST /students/diagnostic/{course_id}` (`students.py:257`) | `student_service.save_diagnostic` (scoring determinista) + `ai_service.analyze_diagnostic_ai` (**una** llamada a OpenAI, con fallback heurístico) | No | No — el `"consensus_summary"` en `save_diagnostic` (`student_service.py:199`) es una clave de diccionario literal, no una invocación de `ConsensusEngine` | Ni LangGraph ni legacy: lógica de plataforma directa. El comentario del hook (`useStudent.ts:32-34`, *"la deliberación real encadena 5 agentes LLM... Consenso"*) no corresponde a esta implementación — es información desactualizada en el propio código. |
| Selección/recomendación de contenido | `POST /students/learning-path/{course_id}` (`students.py:390`) | `student_service.generate_learning_path_adaptive` | No | No | Puramente determinista — cero LLM, cero runtime, cero agentes. |
| Experiencia del módulo | `POST /students/module/{module_id}/orchestrate` (`students.py:753`, `async def`) | `module_orchestration_service.orchestrate_module` | **Sí** — `from runtime.boundary import Entrega, normalizar_asunto` (`module_orchestration_service.py:49`); `bloom_target_desde_entrega`/`asunto_de_modalidad` delegan la decisión al runtime con el comentario explícito *"Épica 2: el runtime decide, este servicio ejecuta"* (líneas 71-77) | Usa `ResearchAgent` (vivo, sin herencia de `BaseAgent` — confirma §7.2) y `SharedMemoryStore`; no usa `SwarmOrchestrator` ni `ConsensusEngine` | **Runtime en el lazo de decisión real**, con fallback a `Entrega(asunto=None, diseno=None)` si el runtime falla (línea 135) — best-effort, nunca bloquea. |
| Tutor IA | `POST /students/tutor/chat` (`students.py:1046`) | `runtime_bridge.contexto_pedagogico_tutor` + `registrar_pregunta_tutor` + `ai_service.generate_tutor_response_desde_runtime` | **Sí**, explícitamente documentado en el docstring de la propia función (líneas 1052-1059): *"el contexto pedagógico... lo decide el runtime — esta capa solo lo lee por el Boundary y redacta (RFC-0002 R4)"* | No | Mismo patrón best-effort: si el runtime no tiene sesión todavía, el chat sigue funcionando sin ese contexto. |
| Evaluación | `POST /students/evaluation/{course_id}/start`, `POST /students/evaluation/{attempt_id}/submit` (`students.py:963,988`) | `evaluation_service.start_evaluation`/`submit_evaluation` (persistencia) + `runtime_bridge.registrar_evidencia_evaluacion` en la capa de ruta | **Sí** — comentario cita `ADR-0010` explícitamente (línea 1006); el resultado (`entrega.asunto`, `entrega.diseno`) se devuelve al frontend como `runtime_decision` (línea 1042) | No | La evidencia de la evaluación entra al runtime como hecho; la decisión vuelve y se expone en la respuesta HTTP — no solo se registra, también se consume. |
| Feedback y memoria | (no hay endpoint dedicado — la "memoria" vive en dos sistemas distintos) | — | Parcial — `runtime.boundary` tiene su propio `AlmacenMemoria` (Postgres, esquema `runtime`, expuesto en `GET /runtime/sessions/{id}/memoria`) | La plataforma usa por separado `app/memory/shared_memory.py::SharedMemoryStore` (mismo Postgres de `app/`, tablas de plataforma) | Dos almacenes de memoria coexisten y no están unificados: el de la plataforma (usado por `module_orchestration_service`/tutor) y el del runtime (propio del Boundary, ver ADR-0009 §2.4). No es un bug — es la separación física que ADR-0002 §5 exige a propósito — pero vale la pena que quede explícito: "memoria" no es una sola cosa en este sistema. |

**Chequeo adicional pedido explícitamente — ¿participa `ConsensusEngine` en algún punto vivo?** Grep de
`ConsensusEngine(` en todo `app/`: solo aparece en `app/swarm/orchestrator.py`
(muerto, §0/§2), `app/experiment/orchestrator.py` (el grupo de control
experimental Legacy-vs-Runtime que `CONCEPT-0001/D-001` reserva a
propósito para comparación, no tráfico real) y `app/demo/orchestrator.py`
(el simulador de `/evidencia`, tampoco tráfico real). **`ConsensusEngine`
no participa en ningún endpoint que un estudiante real dispare.**

### Respuesta a la pregunta central

> "¿Todo el flujo principal del estudiante pasa por LangGraph?"

No completamente, pero tampoco es "runtime como plataforma paralela de
observabilidad" — es más específico que ambos extremos: **tres de las
cinco etapas con lógica adaptativa (módulo, tutor, evaluación) sí
consultan o alimentan al runtime LangGraph vía `runtime_bridge`/
`runtime.boundary`, con el runtime tomando la decisión real (bloom
target, asunto/modalidad, diseño) y la plataforma solo ejecutando o
redactando — exactamente el patrón que RFC-0002 R4 exige.** Las otras
dos (diagnóstico inicial, generación de ruta) son lógica de plataforma
determinista/un-solo-LLM-call, sin runtime ni agentes de ningún tipo —
ninguna pasa por el sistema legacy tampoco. En ninguna etapa del flujo
real de estudiante aparece `SwarmOrchestrator`, `AgentFactory`,
`ConsensusEngine` o una subclase de `BaseAgent`.

**Consecuencia para la pregunta de eliminación:** dado que ninguna etapa
del flujo real de estudiante usa el sistema legacy, la "paridad
funcional end-to-end" de `docs/CLAUDE.md` — en el sentido de "nada vivo
depende ya de `BaseAgent`/`SwarmOrchestrator`" — **parece cumplida** por
esta auditoría. Lo que sigue sin resolver (y no es una pregunta de
código) es si diagnóstico y generación de ruta *deberían* pasar también
por el runtime en el futuro, o si su naturaleza determinista los deja
fuera del alcance de RFC-0002 a propósito — esa es una decisión de
diseño para la tesis, no un hallazgo de esta auditoría.
