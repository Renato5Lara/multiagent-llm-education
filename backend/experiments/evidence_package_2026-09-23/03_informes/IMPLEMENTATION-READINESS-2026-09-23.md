# Implementation Readiness

| Campo | Valor |
|---|---|
| Documento | `IMPLEMENTATION-READINESS-2026-09-23.md` |
| Fase | NITRO 0.1 — auditoría técnica + diseño + plan (sin cambios al repositorio) |
| Contrato de referencia | `Docuemento de tesis/MASTER-SPEC-2026-09-23.md` (leído completo, §1–§27 y anexo de contradicciones) |
| Regla de precedencia | MASTER SPEC > arquitectura actual > código histórico |
| Rama / commit auditado | `feat/pretest-m1-v4` @ `d31d29c819151239e932c1d3c28e56dd364507d0` |

**Convención de etiquetas usada en todo el documento** (para no presentar decisiones nuestras como aprobadas por el asesor):

- **[ASESORÍA DEFINE]** — está en la asesoría o en el Master Spec como requisito.
- **[ASESORÍA NO DEFINE → PROPUESTA]** — el Master Spec lo marca como pendiente o no lo menciona; lo que sigue es un diseño nuestro, sujeto a aprobación.
- **[DECISIÓN HUMANA: DEC-xx]** — requiere cierre humano antes de tocar código; el catálogo completo está en §25.

**Estados de evidencia en el repo:** `LIVE-TRACKED` (en git), `LIVE-UNTRACKED` (existe en disco, no versionado), `DELETED`, `HISTORICAL`, `DOC-ONLY`. No se usó `__pycache__` como evidencia.

---

## 1. Estado del repositorio

### 1.1 Git y árbol de trabajo

| Ítem | Valor verificado |
|---|---|
| Rama | `feat/pretest-m1-v4` |
| Commit | `d31d29c819151239e932c1d3c28e56dd364507d0` ("docs(architecture): registro de validación del banco de diagnóstico de M1 (v4)") |
| Árbol de trabajo | **SUCIO**: 71 entradas en `git status --short` (13 tracked modificados + resto untracked). Al iniciar la sesión eran 70; la entrada adicional es `docs/architecture/ADR/.impeccable/` (untracked), que no fue creada por ningún comando de esta auditoría (no se ejecutó ninguna escritura en el repo) |
| Tracked modificados | `.claude/settings.local.json`, `.codegraph/daemon.pid`, `CLAUDE.md`, `backend/app/api/routes/auth.py`, `backend/app/main.py`, `backend/app/models/__init__.py`, `backend/app/sandbox/docker/runner_payload.py`, `backend/app/sandbox/runner.py`, `backend/runtime/domain/{adaptar,diagnosticar,orientar,remediar}/productor.py`, `backend/runtime/kernel/deliberation/politica.py` |
| Archivos `.py` tracked en `backend/` | 603 (coincide con el Master Spec §8) |

### 1.2 Hallazgo de higiene que afecta al plan (no está en el Master Spec)

**Todo el stack CMG está `LIVE-UNTRACKED`** (0 archivos `cmg_*` en `git ls-files`): `app/services/cmg_{concept_catalog,evaluation_service,experiment_repository,generation_service,multiagent_configuration_service}.py`, `app/models/experiment_cmg_result.py`, `scripts/experimento_cmg_runner.py`, y 7 archivos `tests/test_cmg_*`/`test_experimento_cmg_runner.py`.
**El head de Alembic es una migración untracked**: `928a10b002db` (`add_run_label_to_experiment_cmg_results`), hija de `f101101bc75d` (también untracked). Consecuencia: cualquier migración nueva del PoC (F2-1) tendría como padre una revisión no versionada. → **DEC-14**.
El Master Spec dice basarse solo en archivos tracked (§1, "Corrección respecto al documento previo") pero cita `cmg_evaluation_service.py`, que es untracked; su método de evidencia (`git ls-files`) no ve la mayor parte del generador y evaluador actuales.

### 1.3 Entorno efectivo

| Ítem | Valor | Observación |
|---|---|---|
| Python efectivo | venv `backend/.venv` = **3.14.7**; `Dockerfile` = `python:3.12-slim`; `CLAUDE.md` = 3.11; asesoría = 3.12 | Tres versiones distintas. El Master Spec §17 marca "CUMPLE" solo por el `Dockerfile`. → DEC-15 |
| LangGraph | 1.2.0 (instalado y pineado en `requirements.txt`) | `LIVE` |
| FastAgent | no instalado, 0 referencias | — |
| Redis | 0 referencias en `app/`, `runtime/`, `requirements.txt`, `docker-compose*.yml`; sin cliente `redis` ni binario | `AUSENTE` |
| Docker CLI | **no existe en esta máquina** (`command -v docker` vacío) | `SandboxRunner` usa `docker_bin="docker"` y devuelve `INFRASTRUCTURE_ERROR` (`sandbox: docker_unavailable`) si falta (`app/sandbox/runner.py`) |
| Podman | instalado; contenedor `upao_postgres` (postgres:16-alpine) **activo y saludable** | Dev local corre sobre podman, no docker |
| PostgreSQL | 16, conteos read-only: `concepts`=32, `learning_objectives`=221, `experiment_cmg_results`=128 | Alembic: 32 archivos de migración |
| Java | `/usr/bin/java` presente | JMeter (JVM) no exige instalar Java; JMeter mismo NO instalado |
| JMeter / Locust | no instalados, 0 referencias en el repo | Existe un harness propio de carga (ver 1.5) |
| Hardware | 8 CPU lógicos, 7 GB RAM (≈1 GB disponible al medir) | Limita la validez de pruebas de 100 usuarios con generador y SUT co-ubicados |
| Async/DB | `app/db/session.py`: engine síncrono con `pool_size=10, max_overflow=20` (rama Postgres) y `create_async_engine` aparte | Cuello de botella conocido de QueuePool en los benchmarks E1/E2 |
| Tests de app | `tests/conftest.py` usa **SQLite en memoria** (StaticPool) y TestClient; los de `tests/runtime` usan Postgres | Relevante para tests de modelos nuevos (tipos portables) |

### 1.4 Estructura relevante

- `backend/runtime/` (8.401 líneas): kernel (`state`, `reducers`, `deliberation`, `events`, `memory`, `transitions`), `domain/` con 8 capacidades por verbo (`adaptar, diagnosticar, evaluar, modelar, orientar, remediar, tutorizar, validar`), `engine/graph/walkthrough.py` (LangGraph `StateGraph`, nodos `aplicar, diagnosticar, remediar, orientar, deliberar, decidir, validar, modelar, tutorizar, adaptar`) y `engine/checkpoint/`. **No hay `random` en `runtime/`** (P12: sin azar).
- `backend/app/`: 20 routers (`runtime.py` = Boundary HTTP `/api/runtime/*`); `app/agents/` y `app/swarm/` **DELETED** (solo `__pycache__`, commit `5d93bec`, ADR-0011).
- `frontend/`: React/TS con rutas admin/docente/estudiante/evidencia; sin renderer Mermaid (0 coincidencias en `frontend/src` ni `package.json`); audio solo con `speechSynthesis` y `<audio>` para recursos externos.
- Observabilidad `LIVE`: `app/tracing/` (`CorrelationEngine`, `trace_langgraph_node`, propagación), `app/telemetry/spans_operativos.py` (LangSmith, latencia/tokens como telemetría operativa, RFC-0007), `app/observability/` (exporter, stream), `app/swarm_diagnostics/` (detectores).

### 1.5 Benchmarks y experimentos existentes

- `app/benchmark/` (`LIVE-TRACKED`: `mermaid.py`, `metrics.py`, `runner.py`, `statistics.py`, `exporters.py`, `datasets.py`) y `app/experiment/benchmark/` (`LIVE-TRACKED`, sin `real/`, eliminado en ADR-0011). **`PedagogicalMetricEvaluator.score()` es un evaluador proxy sembrado con ruido acotado; no mide contenido real** (confirmado leyendo el código) → no es F1_adapt.
- `scripts/benchmark_capacidad_http.py` (`LIVE-UNTRACKED`) + `scripts/instrumentacion_e1.py` + `scripts/benchmark_results/*.json`: harness HTTP de usuarios concurrentes con p50/p95/p99, throughput, errores por tipo, QueuePool y `pg_stat`. Mide **login + 2 GET** por usuario, no adaptaciones; corridas E2 mostraron saturación del pool alrededor de N=80. `HISTORICAL/REUTILIZABLE como diseño`, no como evidencia de RNF01/RNF04.
- Experimentos CMG: `pilot_1` y `corrida_2` = 64 filas cada una en `experiment_cmg_results` (32 conceptos × 2 condiciones). **Corrección al Master Spec §20/§23:** el spec dice que Corrida 2 "usa datos reales"; el código muestra que la evidencia diagnóstica es **sintética** (`traza["evidence_source"] = "synthetic_experimental_instrument"` en `cmg_multiagent_configuration_service.py`); los Concepts sí son reales.

---

## 2. Estado respecto al Master Spec

### 2.1 Trazabilidad requisito → código

Estados: CUMPLE / PARCIAL / AUSENTE / CONFLICTO / HISTÓRICO. **No se declara equivalencia** salvo demostrada operacionalmente.

| Req. | Módulo/función actual más cercano (LIVE) | Test | Evidencia | Estado | Nota |
|---|---|---|---|---|---|
| **RF01** perfil JSON (nivel, estilo, tasa de error) | `app/models/diagnostic_result.py` (`profile`, `modality_scores`, `dominant_modality`), `app/models/student_profile.py`, `app/schemas/diagnostic.py`; "tasa de error" solo existe como `errores/items_totales` del instrumento **sintético** CMG | `tests/test_students.py` (diagnóstico); ninguno del contrato RF01 | Sin esquema JSON versionado ni endpoint que acepte el payload de RF01 | **AUSENTE** | Los datos de VARK existen (`student_service.compute_modality_scores`), el **contrato** no |
| **RF02** `W=[w_v,w_a,w_t,w_c]` | `student_service.compute_modality_scores` → 4 dims `visual/reading/audio/kinesthetic` (promedio de 2–3 preguntas de la Sección B) | — | Sin vector normalizado; "código" no tiene dimensión VARK propia (`kinesthetic`≠código) | **AUSENTE** | `adaptar/productor.py` decide por reglas categóricas (modalidad×profundidad); mecanismo distinto, no sustituto |
| **RF03** enjambre en paralelo | Único `asyncio.gather` real: recuperación Tavily en `ResearchAgent` | — | Ninguna generación concurrente de código/diagrama/texto/audio | **AUSENTE** | |
| **RF04** ciclo iterativo con 𝓕 | `runtime/kernel/deliberation/{mecanica,confianza,politica}.py` = consenso por confianza efectiva | `tests/runtime/*` | Es **otro** mecanismo (estigmergia, sin iteraciones, sin azar). Sin 𝓕, sin bucle | **AUSENTE** (+ **CONFLICTO** de diseño, ver 24) | |
| **RF05** paquete con 4 modalidades | `CMG` (`cmg_generation_service.py`, UNTRACKED): explicación, código+tests+ejercicio, Mermaid textual, prompts de audio como texto | `tests/test_cmg_generation_service.py` (UNTRACKED) | 3 de 4 piezas; **sin audio real**; sin selección por 𝓕 | **PARCIAL** | No es equivalente: no hay coherencia garantizada ni empaquetado |
| **RF06** métricas por ciclo | `experiment_cmg_results` (propósito distinto) | `test_cmg_experiment_persistence.py` | Sin tablas de ciclo/iteración/convergencia | **AUSENTE** (tabla existente = **HISTÓRICO**) | |
| **RF07** gold standard | — | — | `cmg_evaluation_service.evaluar_d1_graduado` mide cobertura léxica; no es etiquetado por perfil | **AUSENTE** | |
| **RF08** discretización PSO | — | — | 0 coincidencias de `p_best/g_best/particle/velocity` en código | **AUSENTE** | |
| **RNF01** `L_resp<2.0s` | `benchmark_capacidad_http.py` (UNTRACKED) mide latencia HTTP de un flujo distinto | — | Sin endpoint de adaptación que medir | **PARCIAL** (herramienta) / artefacto **AUSENTE** | |
| **RNF02** `T_conv≤15` | — | — | Sin contador de iteración | **AUSENTE** | |
| **RNF03** `F1_adapt≥0.85` | `app/benchmark/metrics.py` (proxy sintético) | `tests/test_benchmark.py` | No mide contenido real | **AUSENTE** (proxy = **HISTÓRICO**) | |
| **RNF04** `Throughput≥20 req/s` | Mismo harness HTTP; e2/e3 con N=70–90 | — | Saturación de pool observada sobre otro flujo | **AUSENTE** para el artefacto | |
| **RNF05** `SUS>75` | — | — | 0 coincidencias reales | **AUSENTE** | |

### 2.2 Estado por componente de infraestructura (Master Spec §17, con correcciones)

| Componente | Master Spec | Verificación de esta fase |
|---|---|---|
| Python 3.12 | CUMPLE | **PARCIAL**: solo el `Dockerfile`; venv local 3.14.7 |
| Docker | CUMPLE | **PARCIAL**: `docker-compose.yml` y `Dockerfile` existen; el CLI `docker` no está en esta máquina (solo podman) y el sandbox lo exige |
| Redis | AUSENTE | Confirmado |
| LangGraph / FastAgent | PARCIAL | Confirmado (solo LangGraph) |
| JMeter/Locust | NO COMPROBADO | **Confirmado AUSENTE** (sin binarios ni scripts); existe harness propio en Python |
| Sandbox de código | "no verificado" | **Verificado**: `app/sandbox/{runner,policy,schemas,docker_manager}.py` (TRACKED; `runner.py` y `runner_payload.py` con cambios sin commitear). AST policy con imports/calls denegados; límites `timeout_seconds≤10`, `memory_mb≤512`, `pids≤128`; requiere CLI docker |

### 2.3 Tensiones internas del Master Spec detectadas en esta fase (no listadas en su §25)

1. **RF05 vs §12 vs §13:** RF05 exige que el paquete contenga **siempre las 4 modalidades**, pero el gold standard etiqueta "inclusión/exclusión" y la matriz es **4×4 (multiclase)**. Si las 4 siempre están, la inclusión no discrimina y F1 sobre inclusión es trivial. La semántica de la etiqueta (¿modalidad dominante? ¿nivel de énfasis? ¿conjunto priorizado?) es indefinida. → **DEC-03**.
2. **`CR` no está definida.** Aparece como umbral (`CR≥98%`, §3) y como métrica de AG0 (§7), pero §14 no la define. → **DEC-10**.
3. **`T_conv≤15` es tautológico** si `k_max=15` y T_conv se mide en iteraciones: el ciclo nunca puede superar 15. Solo tiene contenido como `CR` (proporción que converge por ε antes de `k_max`) o en tiempo. → **DEC-10**.
4. **Criterio `|ΔF|<ε` sobre espacio discreto:** 𝓕 es constante a tramos; un solo paso sin mejora dispara la parada en k=1. → **DEC-10**.
5. **Tamaño del enjambre (N partículas) no definido**, ni `Vmax`, ni la semántica de `i`,`j` en `x_ij`. → **DEC-02/DEC-08**.
6. **Coher vs Redund** pueden penalizar la misma señal (términos compartidos) si no se separan operacionalmente. → **DEC-04**.
7. **Little:** con `Throughput=20 req/s` y `L_resp=2 s`, deben estar en vuelo ≈40 ciclos completos simultáneamente (20×2), en un host de 8 CPU / 7 GB. → **DEC-09**.

---

## 3. Arquitectura target

**Principio de ubicación [PROPUESTA]:** los cinco agentes y el PSO viven en un **paquete nuevo** `backend/adaptation_swarm/`, hermano de `backend/runtime/`, **sin modificar** el kernel ni `runtime/domain/*`. Motivos: (1) el kernel es física/estigmergia sin azar (P12, CONCEPT-0001, RFC-0006) y el PSO exige azar sembrado y un orquestador central; (2) `runtime/` nunca importa `app/` y debe seguir así; (3) el stack legacy fue retirado por ADR-0011, así que no se reintroduce `BaseAgent`. La contradicción con esas normas queda registrada en §24 y en DEC-01: se requiere un ADR nuevo que declare el alcance del subsistema PoC (no modifica RFC-0006 para el runtime de estudiantes).

```
POST /api/adaptation  (nombre propuesto; la asesoría no fija endpoint)
   │  perfil JSON (RF01, schema versionado)
   ▼
┌───────────────────────────── AG0 Swarm-Orchestrator ─────────────────────────────┐
│ LangGraph StateGraph (control del ciclo)                                         │
│ recibir → perfilar → sembrar_enjambre → despachar → recolectar → evaluar(𝓕)      │
│   → actualizar_PSO(p_best,g_best,v,x,decodificar φ) → ¿converge?                 │
│        no ↺ despachar        sí → seleccionar S* → ensamblar → persistir → responder│
└───────────────┬──────────────────────────────────────────────────────────────────┘
                │  Redis Streams (bus real: mensajes AG0↔AG1..AG4 + memoria compartida)
   ┌────────────┼──────────────┬────────────────┬─────────────────┐
   ▼            ▼              ▼                ▼                 ▼
 AG1 Profil   AG2 Code       AG3 Diagram      AG4 Text          AG4 TTS
 (W)          (código)       (Mermaid/UML)    (explicación)     (audio)
                │  ▲ sandbox      │ deriva del AST del código
                ▼  │              ▼
        biblioteca de candidatos versionada (ver DEC-09) + PostgreSQL (registro permanente)
```

**Respuestas a las preguntas de diseño del encargo:**

| Pregunta | Respuesta [PROPUESTA] | Justificación |
|---|---|---|
| ¿Agentes = objetos/clases independientes? | **Sí.** Cada AG es una clase que implementa un `Protocol` común (`SwarmAgent`) con bucle consumidor sobre Redis | La asesoría exige 5 componentes reales; deben poder ejecutarse, fallar y medirse por separado |
| ¿Son nodos de LangGraph? | **Solo AG0** es un grafo LangGraph (control del ciclo). AG1–AG4 **no** son nodos internos del bucle | Si AG1–AG4 fueran nodos, Redis sería decorativo (el encargo lo prohíbe). Con AG0 como grafo y AG1–AG4 como consumidores del bus, la comunicación inter-agente es real y medible |
| ¿Dónde vive el estado? | El estado autoritativo del ciclo (k, partículas, p_best, g_best) está en el **estado del grafo de AG0**, espejado en Redis (`hash`) para observabilidad/recuperación; AG1–AG4 son **sin estado** (handlers idempotentes) salvo cachés. El registro permanente es PostgreSQL | Separa control (AG0) de trabajo (AG1–4) y permite reintentos |
| ¿Dónde vive la comunicación? | **Redis Streams** con grupos de consumidores | Ver §5 |
| ¿Dónde vive PSO? | Librería **pura** `adaptation_swarm/pso/` (sin Redis, sin LLM, RNG con semilla), invocada por AG0 | Testeable de forma unitaria y reproducible |
| ¿Quién controla el ciclo? | **AG0** (decide continuar/parar por ε/k_max) | [ASESORÍA DEFINE] §7 AG0 |

**Modo de realización de candidatos (bloqueante de latencia):** un candidato es una configuración `S_i` (partícula) cuya realización requiere código, diagrama, texto y audio. Realizarla por LLM/TTS/sandbox **en cada partícula e iteración** excede `L_resp<2 s` por órdenes de magnitud (un contenedor de sandbox por ejecución; una llamada LLM/TTS = segundos). Se presentan tres modos y se recomienda uno, **sin adoptarlo**:

| Modo | Descripción | Cumple RNF01/04 | Reproducible | Riesgo |
|---|---|---|---|---|
| **M1 Biblioteca versionada** | AG2/AG3/AG4 *generan y validan offline* una biblioteca de variantes por concepto (código validado en sandbox, diagramas derivados del AST, textos por nivel, audio TTS sintetizado y almacenado con hash). En línea, cada AG *selecciona/compone* desde la biblioteca; el PSO busca sobre índices discretos | **Sí** (fitness sub-ms; bus ~ms) | **Alta** (mismo input+semilla+versión de biblioteca → mismo resultado) | Se debe justificar ante el asesor que "generar" ocurre en la fase de construcción de la biblioteca y en fallo de caché |
| M2 Generación en línea | Cada partícula genera con LLM/TTS/sandbox | **No** en ningún escenario realista | Baja (variabilidad LLM) | Latencia de decenas de segundos por ciclo |
| M3 Híbrido | M1 para la búsqueda + una generación en línea de S* (texto personalizado) | Dudoso (≥1 llamada LLM ≈ 1–3 s solo esa llamada) | Media | Consume todo el presupuesto de L_resp |

**Más coherente con el Master Spec [PROPUESTA, pendiente]:** M1 para las mediciones de RNF01/RNF04 y para los 100 casos, con M2 disponible como **modo de evaluación de calidad separado y etiquetado** (no compite por latencia). → **DEC-09**.

---

## 4. Diseño AG0–AG4

Interfaz común [PROPUESTA]:

```python
class SwarmAgent(Protocol):
    agent_id: str                                  # "AG0".."AG4"
    async def handle(self, msg: BusMessage) -> AsyncIterator[BusMessage]: ...
    async def run(self, bus: Bus, stop: asyncio.Event) -> None: ...   # bucle XREADGROUP
```

| Campo | AG0 Swarm-Orchestrator | AG1 Profil-Agent | AG2 Code-Agent | AG3 Diagram-Agent | AG4 Text-Agent |
|---|---|---|---|---|---|
| Módulo propuesto | `adaptation_swarm/agents/ag0_orchestrator.py` + `graph/cycle_graph.py` | `agents/ag1_profil.py` | `agents/ag2_code.py` | `agents/ag3_diagram.py` | `agents/ag4_text.py` (+ `tts/`) |
| Responsabilidad [ASESORÍA DEFINE] | Dirige ciclos, calcula 𝓕 global, decreta convergencia | Parsea perfil, produce W | Extrae/valida/formatea código ejecutable (Python/C++) | Diagramas Mermaid/UML/SVG asociados a la lógica del código | Explicación conceptual adaptada y coordina TTS |
| Input | `ProfileRequest` (RF01) | `ProfileRequest` | `CandidateRequest` (concepto, nivel, config de código de la partícula) | `CandidateRequest` + referencia al código realizado | `CandidateRequest` + W + referencias de código/diagrama |
| Output | `g_best`, decisión de convergencia, `PackageReady` | `WeightsReady{W, profile_id, schema_v}` | `CodeCandidateReady{code_ref, sha256, sandbox_status}` | `DiagramCandidateReady{mermaid_ref, sha256, valid}` | `TextCandidateReady{text_ref}`, `AudioCandidateReady{audio_ref, sha256, mime, dur}` |
| Estado | `k`, partículas `(x,v,p_best)`, `g_best`, semilla RNG | ninguno (función pura + esquema) | ninguno (caché por hash) | ninguno | ninguno (caché de audio por hash) |
| Mensajes que emite/consume | ver tabla de mensajes §5.3 | consume `PROFILE_REQUEST`; emite `W_READY` | consume `CANDIDATE_REQUEST` (dim código); emite `CODE_READY` | consume `CANDIDATE_REQUEST` (dim diagrama), depende de `CODE_READY` | consume `CANDIDATE_REQUEST` (texto/audio) |
| Dependencias | `pso/`, `fitness/`, LangGraph, Redis, Postgres | `profiles/w_mapping.py` | `SandboxRunner` (adaptado), catálogo (`cmg_concept_catalog`), `MermaidValidator` no | `app/benchmark/mermaid.py` (`MermaidValidator`), analizador AST | `LLMService`/`OpenAIProvider`, proveedor TTS (DEC-06), `MultimodalService` |
| Persistencia | `CicloAdaptacion`, `IteracionPSO`, `ParticulaPSO`, `PaqueteMultimodal`, `MetricaCiclo` | `PesosModalidad` | `CandidatoModal` (modalidad=código) | `CandidatoModal` (=diagrama) | `CandidatoModal` (=texto, =audio) |
| Tests | unit (bucle, parada), integración Redis, E2E | unit (mapeo→W, suma=1) | unit (validación, hash), integración sandbox | unit (Mermaid válido, coherencia con AST) | unit (plantillas, TTS con proveedor real en integración) |
| Redis | XADD/XREADGROUP, hashes de estado, TTL | consumidor | consumidor | consumidor | consumidor |
| LangGraph | **Es** el grafo (nodos: recibir, perfilar, sembrar, despachar, recolectar, evaluar, actualizar_pso, decidir_parada, seleccionar, ensamblar, persistir, responder) | no | no | no | no |
| Participación en PSO | Ejecuta el ciclo; guarda g_best | Fija el objetivo `W` de `Simil` | Realiza la dimensión "código" de cada partícula | Realiza la dimensión "diagrama" | Realiza "texto" y "audio" |

**Paralelismo real (RF03):** tras `sembrar` y en cada iteración, AG0 publica `CANDIDATE_REQUEST` para AG2/AG4 simultáneamente; AG3 arranca cuando llega `CODE_READY` (el diagrama se deriva del código, [ASESORÍA DEFINE] "entradas: código o lógica"). La evidencia de paralelismo son los timestamps solapados en los mensajes persistidos (`t_recv`, `t_done` por agente).

**Cómo cumplir "cinco componentes reales y trazables":** cada agente es un proceso/tarea asyncio con `agent_id` propio, cola propia (grupo de consumidores por agente), métricas propias (latencia de handler, errores) y su fila de trazabilidad por mensaje. Ninguno es una función anónima dentro de AG0.

---

## 5. Diseño Redis

**[ASESORÍA DEFINE]:** Redis como *bus de mensajes e intercambio de memoria compartida*. **No** se sustituye por PostgreSQL, por memoria de Python ni por una abstracción sin transporte real. `redis` (cliente `redis-py` asyncio) y un servicio `redis:7` en `docker-compose.yml` serán dependencias nuevas de F1-1 (no se instalan en esta fase).

### 5.1 Reparto de datos Redis vs PostgreSQL [PROPUESTA]

| Dato | Dónde | Motivo |
|---|---|---|
| Mensajes inter-agente en vuelo (requests/replies) | Redis Streams | Transporte; ordenación; consumer groups; reintento |
| Estado de trabajo del ciclo (k, g_best, p_best actuales, status) | Redis hashes `swarm:{cycle_id}:state` / `:pbest` | "Memoria compartida" que AG1–AG4 pueden leer |
| Blobs pequeños de payload (referencias, no contenido) | Redis | Las piezas pesadas (código, texto, mp3) van por **referencia** (`ref`+`sha256`), no por el bus |
| Registro permanente por ciclo/iteración/partícula/candidato/paquete/métrica | PostgreSQL | RF06, reproducibilidad, análisis estadístico |
| Copia permanente del log de mensajes (M2 overhead de comunicación) | PostgreSQL (volcado asíncrono desde el stream) | El stream expira; la evidencia no |
| Biblioteca de candidatos (código/diagrama/texto/audio + hashes) | Postgres (metadatos) + `uploads/multimodal/` (binarios; ya existe `MultimodalService`) | Persistente, versionada |
| Cachés (audio por hash, código validado por hash) | Redis con TTL + respaldo en disco | Velocidad |

### 5.2 Espacio de claves y canales [PROPUESTA]

```
swarm:req                              # stream de entrada de AG0 (solicitudes)
swarm:{cycle_id}:to:AG1|AG2|AG3|AG4    # un stream por agente destino (grupo de consumidores = el agente)
swarm:{cycle_id}:to:AG0                # respuestas hacia AG0
swarm:{cycle_id}:state                 # hash: k, status, g_best_F, g_best_x, seed, config_hash
swarm:{cycle_id}:pbest                 # hash: particle_idx -> {x, F, iteration}
swarm:{cycle_id}:log                   # stream cronológico de TODOS los mensajes (auditoría)
swarm:cache:audio:{sha256}             # cachés con TTL
```

**TTL:** claves de ciclo expiran (p. ej. 24 h) *después* de confirmar el volcado a PostgreSQL; el ciclo nunca depende de Redis para su registro permanente. Valor exacto = parámetro de configuración, no decisión metodológica.

### 5.3 Formato de mensaje (envelope) [PROPUESTA]

| Campo | Tipo | Nota |
|---|---|---|
| `message_id` | UUID | idempotencia |
| `schema_version` | str | versionado del contrato |
| `correlation_id` | UUID | 1 por solicitud HTTP; viaja a logs/spans |
| `cycle_id` | UUID | 1 por adaptación |
| `profile_id` | str | perfil sintético o real |
| `iteration` | int (0..15) | 0 = siembra |
| `particle_idx` | int \| null | |
| `agent_id` | enum `AG0..AG4` | emisor |
| `recipient` | enum | destino |
| `type` | enum | `PROFILE_REQUEST, W_READY, CANDIDATE_REQUEST, CODE_READY, DIAGRAM_READY, TEXT_READY, AUDIO_READY, EVALUATE, GBEST_BROADCAST, CONVERGED, ERROR` |
| `timestamp_utc` | ISO-8601 | reloj de pared |
| `t_mono_ns` | int | reloj monotónico (para latencias; A4 del kernel evita reloj de pared solo *dentro del kernel*) |
| `payload` | JSON | referencias + parámetros, nunca binarios |
| `status` | `ok|error|retry` | |
| `error` | `{code,message}` \| null | |

Respuestas con error nunca se silencian (mismo estándar que ADR-0004 E-2 del runtime): AG0 registra `ERROR`, y el ciclo termina con `status=failed` explícito, no con un g_best inventado.

---

## 6. Diseño PSO

### 6.1 Lo que define la asesoría [ASESORÍA DEFINE]

`v_ij(k+1) = w·v_ij(k) + c1·r1·(p_ij − x_ij(k)) + c2·r2·(g_j − x_ij(k))`; `x_ij(k+1) = x_ij(k) + v_ij(k+1)`; parada `|𝓕(g_best^k) − 𝓕(g_best^{k−1})| < ε` con `ε=0.001` **o** `k=k_max=15`; espacio "discreto".

### 6.2 Inconsistencia documentada (no corregida silenciosamente)

Las ecuaciones son las del PSO **continuo** de Kennedy & Eberhart (1995); la asesoría declara espacio discreto pero no entrega operador de discretización (Master Spec §8, RF08). Sin él, `x_ij ∈ ℝ` no denota una configuración modal válida.

### 6.3 Alternativas matemáticas válidas [ASESORÍA NO DEFINE → PROPUESTA]

| Alt. | Idea | Mantiene las ecuaciones literales | Encaja con el espacio | Pros | Contras |
|---|---|---|---|---|---|
| **A. PSO continuo latente + decodificador φ** | Se aplican **exactamente** las dos ecuaciones sobre `x ∈ ℝ^d`; se define `φ: ℝ^d → S` (redondeo + saturación a rango, por dimensión) para evaluar 𝓕 y reportar `S_i=φ(x_i)` | **Sí, literalmente** | Bueno para dimensiones **ordinales** (nivel de profundidad, longitud, énfasis) | Cambia solo lo estrictamente necesario (añade RF08); trivial de probar; determinista | Imponer orden a variantes categóricas es artificial; 𝓕 constante a tramos (plateaus) |
| B. PSO binario (Kennedy & Eberhart 1997) | `x∈{0,1}^d`, `P(x=1)=sigmoid(v)` | No (cambia la actualización de posición) | Bueno para presencia/ausencia | Estándar para discreto | Contradice la ecuación de `x_ij(k+1)` de la asesoría; RF05 exige las 4 modalidades siempre (inclusión trivial) |
| C. PSO por conjuntos (S-PSO, Clerc) | Velocidad = conjunto de operaciones de reemplazo; posición = selección discreta | No | Bueno para variantes categóricas | Natural para "índice de variante" | Ecuaciones distintas |
| D. Categorical/softmax | `x` = logits por dimensión; `S_i` = argmax o muestreo | Parcial (misma forma de la ecuación sobre logits) | Bueno para categóricas | Mantiene la actualización | Introduce azar extra en el decodificador si se muestrea |

**Más integrable técnicamente con el Master Spec [PROPUESTA, no aprobada]:** **A**, porque (i) conserva las ecuaciones de la asesoría *tal cual*, (ii) el operador φ es una función pura testeable (RF08 lo pide explícitamente como función documentada "que mapee `x_ij ∈ ℝ` a una combinación discreta"), (iii) las dimensiones categóricas se modelan como **índices ordenados de un catálogo versionado** con orden declarado (por costo o profundidad), evitando orden arbitrario. Se deja **explícito** que φ es una decisión nuestra. **DEC-02** requiere aprobación (idealmente del asesor, porque toca la formulación matemática entregada).

### 6.4 Definiciones que hacen falta [ASESORÍA NO DEFINE → PROPUESTA]

| Elemento | Propuesta | Estado |
|---|---|---|
| Partícula `i` | **Un candidato de paquete completo `S_i`** (no un agente). AG2/AG3/AG4 *realizan* las dimensiones de cada `S_i`. Coherente con `𝓕(S_i)` y con "p_best del agente" reinterpretado como p_best de la partícula | DEC-02 |
| Dimensión `j` | d dimensiones ordinales por modalidad (ver §7.2) | DEC-02 |
| Tamaño del enjambre N | Parámetro de configuración; propuesta inicial N=20 (barrido {10,20,30} como análisis de sensibilidad **pre-registrado**) | DEC-08 |
| `w, c1, c2` | No fijados por la asesoría. Propuesta: valores de constricción de Clerc–Kennedy (`w≈0.729`, `c1=c2≈1.494`) como *default documentado*, con barrido de sensibilidad | DEC-08 |
| `r1, r2` | `U(0,1)` independientes por partícula y dimensión, con `numpy.random.Generator(PCG64(seed))` o `random.Random(seed)` propio del ciclo | DEC-08 |
| `Vmax` | Saturación de velocidad a ±(rango de la dimensión)/2 (propuesta; evita divergencia) | DEC-08 |
| Semilla | `seed` = f(`batch_seed`, `profile_id`, `replicate`) determinista y persistido | técnica |
| Inicialización | Muestreo uniforme sobre el dominio de cada dimensión con el RNG sembrado; **una partícula sembrada por W** (heurística opcional, etiquetada) | DEC-08 |
| Parada | Literal de la asesoría (ver 6.5) | DEC-10 |

### 6.5 Convergencia: problemas a decidir (no se cambia la regla sin aprobación)

1. **Plateaus:** con 𝓕 constante a tramos y φ discreto, `|ΔF|<ε` puede cumplirse en `k=1` sin haber explorado. Alternativa: exigir `ε` durante `m` iteraciones consecutivas (paciencia). **Es una modificación** de la regla de la asesoría → DEC-10.
2. `T_conv≤15` tautológico: reportar además `CR` = proporción de ciclos que paran por ε (no por `k_max`) y la distribución de `k_stop`.
3. Registrar siempre `stop_reason ∈ {epsilon, k_max, error}`.

---

## 7. Diseño de discretización

### 7.1 Decodificador φ [PROPUESTA sobre la alternativa A]

Para cada dimensión `j` con dominio ordenado `D_j = {0,…,K_j−1}`: `φ_j(x) = min(K_j−1, max(0, round(x)))`; `S_i = (φ_1(x_i1),…,φ_d(x_id))`. Propiedades a probar: total (definida ∀ x), idempotente en el dominio, determinista, monótona por dimensión. **Empates de `round`** (x.5): redondeo half-to-even de Python; se fija por test.

### 7.2 Espacio de configuración [PROPUESTA — DEC-02]

Por modalidad `m ∈ {código, diagrama, texto, audio}` dos dimensiones ordinales (8 dimensiones en total, valores pequeños para que el espacio sea realizable con una biblioteca finita):

| Dim | Significado | Dominio (ejemplo, se fija en DEC-02) |
|---|---|---|
| `e_m` énfasis/rol de la modalidad en el paquete | {0 apoyo, 1 estándar, 2 principal} (**las 4 modalidades siempre están presentes, RF05**) | K=3 |
| `v_m` variante de realización | índice en el catálogo de variantes de `m` **ordenado por costo/profundidad** | K=3 por modalidad (p. ej. código: mínimo / comentado / con reto; diagrama: flujo / secuencia-simple / anotado; texto: breve / estándar / extendido; audio: voz base a 3 duraciones) |

Tamaño del espacio: `(3·3)^4 = 6.561` configuraciones por concepto; enumerable por fuerza bruta, lo que permite **verificar el óptimo global** de cada caso y medir cuánto se acerca el PSO (evidencia útil para PE3, sin ser un requisito de la asesoría).

**Restricción con RF05:** como las 4 modalidades siempre están presentes, la etiqueta que F1 compara **no puede ser presencia/ausencia**; es el énfasis `e_m`. Ver DEC-03.

---

## 8. Diseño de Fitness

`𝓕(S_i) = α·Simil(S_i,W) + β·Coher(S_i) − γ·Redund(S_i) − δ·CostT(S_i)`, `α+β+γ+δ=1`.

**[ASESORÍA DEFINE]:** la forma de 𝓕 y la restricción de suma. **[ASESORÍA NO DEFINE]:** método de cálculo de los 4 términos, su rango, y los valores de α,β,γ,δ. Todo lo siguiente es propuesta nuestra (Master Spec §9, GAP #2).

Rango de 𝓕 con términos en [0,1]: `[−(γ+δ), α+β]`.

| Término | Entrada | Salida / rango | Fórmula propuesta | Normalización | Fuente | Costo | Determinismo | Dep. LLM | Test unitario |
|---|---|---|---|---|---|---|---|---|---|
| **Simil(S,W)** | vector de énfasis `s_m = e_m/Σe` (o dist. equivalente) y `W` | [0,1] | `1 − ½·‖s − W‖₁` (similitud por variación total; ambos suman 1) | `W` con Σ=1 (AG1) | AG1 + config de S | O(1) | **Sí** | No | Sí: casos límite (s=W→1; soportes disjuntos→0) |
| *Alt. Simil* | idem | [0,1] | coseno(s,W) | ninguna | idem | O(1) | Sí | No | Sí; contra: insensible a magnitud, peor interpretabilidad como "proporción" |
| **Coher(S)** | código, diagrama, texto (audio = TTS(texto), su coherencia es por construcción vía hash) | [0,1] | media ponderada de 3 subpuntajes continuos: (a) *anclaje léxico*: fracción de **términos-ancla del concepto** (`ConceptAnchor`) presentes en cada pieza; (b) *diagrama↔código*: fracción de etiquetas del diagrama que aparecen como identificadores/AST del código; (c) *texto↔código*: fracción de identificadores clave del código mencionados en el texto | fracciones ∈[0,1] | piezas realizadas | O(|piezas|) | **Sí** (sin modelos) | No | Sí. Extiende el criterio de D3 (4 flags booleanos) a un escalar continuo; D3 permanece como *pass/fail auxiliar* |
| *Alt. Coher* | idem | [0,1] | similitud coseno de embeddings entre piezas | — | proveedor de embeddings | costo API | No estrictamente (versión del modelo) | **Sí** | Requiere ampliar el contrato `LLMProvider` (`embed()`), lo que el proyecto trata como **modificación de interfaz compartida con RFC previo** |
| *Alt. Coher* | idem | [0,1] | LLM-as-judge | — | LLM | alto | No | **Sí** | El repo documenta 0 evaluadores tipo judge; riesgo de validez |
| **Redund(S)** | texto, código (comentarios), diagrama (etiquetas) | [0,1] | solapamiento de **n-gramas de contenido excluyendo `ConceptAnchor`**: media de Jaccard de n-gramas (n=3) entre pares de piezas | [0,1] | piezas | O(|piezas|) | **Sí** | No | Sí |
| **CostT(S)** | variantes elegidas `v_m` | [0,1] | `Σ_m t̂_m(v_m) / T_ref`, saturado a 1; `t̂_m` = mediana de tiempo de realización **medida y congelada** en la biblioteca (tabla versionada) | dividir por `T_ref` fijo | telemetría de calibración | O(1) | **Sí** (la tabla es dato, no reloj) | No (la calibración sí mide LLM/TTS) | Sí. El tiempo real de cada ciclo se mide aparte como métrica, no dentro de 𝓕 (evita no-determinismo) |

**Separación Coher/Redund [DEC-04]:** Coher premia compartir términos **ancla del concepto**; Redund penaliza repetir contenido **no ancla**. Sin esa separación, ambos términos se contradicen.

**Pesos α,β,γ,δ:** la asesoría no da valores. Propuesta: fijar un vector de referencia **antes** de ejecutar los 100 casos y registrarlo en el manifiesto (p. ej. α=0.4, β=0.3, γ=0.15, δ=0.15) y ejecutar un **análisis de sensibilidad** sobre una rejilla pre-registrada. Estos números son ilustrativos, **no aprobados**. → DEC-04.

**Riesgo de circularidad con el gold standard:** si `Simil` usa `W` y el gold se deriva de la misma `W`, el PSO puede "acertar" el gold solo maximizando `Simil` (F1 inflado). El gold debe depender de una fuente **independiente** (p. ej. de la dificultad del concepto y del arquetipo, no de `W`). Ver §9.

---

## 9. Diseño Gold Standard

**[ASESORÍA DEFINE]:** existe una "regla de oro teórica (Gold Standard) definida para el perfil j" y una matriz de confusión 4×4. **[ASESORÍA NO DEFINE]:** quién lo define, con qué método, ni la semántica de la etiqueta (Master Spec §12, GAP). Se evalúan las 4 opciones pedidas.

| | **A. Reglas determinísticas** | **B. Expertos** | **C. LLM-as-judge** | **D. Combinación** |
|---|---|---|---|---|
| Descripción | Tabla versionada `(arquetipo × dificultad) → etiqueta ideal` definida y **pre-registrada** antes de ejecutar el PSO | ≥10 expertos etiquetan la combinación ideal por perfil/concepto | Un LLM decide la combinación ideal | Reglas (A) como etiqueta operativa **validadas** por expertos (B) con acuerdo inter-juez |
| Reproducibilidad | Total | Media (la muestra de expertos) | Baja (varía con el modelo/versión) | Alta (la regla es la etiqueta; los expertos validan) |
| Costo / tiempo | Bajo / días | Alto / semanas de campo (100 casos × ≥10 jueces = ≥1.000 juicios) | Medio (API) / horas | Medio-alto |
| Validez | Depende de la justificación de las reglas (validez de contenido débil si no se contrastan) | Alta (juicio experto) pero costosa | **Riesgo de circularidad**: evaluar un sistema con LLM usando otro LLM; sin evidencia de validez en el repo (0 judges) | Alta y auditable |
| Sesgo | Sesgo del diseñador de reglas | Sesgo/fatiga de expertos | Sesgo del modelo | Se mitiga con acuerdo (κ) |
| Dificultad | Baja | Alta (logística, ética) | Media | Media-alta |
| Trazabilidad | Excelente (versionada) | Buena (hojas de anotación) | Regular | Excelente |
| n≥100 | Sí | Difícil sin muestreo | Sí | Sí (expertos sobre subconjunto) |
| Compatible con F1 | Sí | Sí | Sí | Sí |
| DSRM | Buena para "Demostración", evaluación por reglas explícitas | Buena para "Evaluación" | Débil sin validación adicional | La mejor alineación con Demostración+Evaluación |
| Riesgos | Circularidad con 𝓕; reglas arbitrarias | Reclutamiento, tiempo (cronograma de 16 semanas) | Validez, costo, deriva de versión | Coordinación |
| Dependencias | Diseño de reglas (DEC-03), esquema de perfil (DEC-13) | Reclutamiento y consentimiento (comparte n≥10 con SUS) | API LLM | A + B |
| Evidencia en el repo | D1 graduado (R23–R26) = precedente de rúbrica determinista para **otra** dimensión | Ninguna | 0 judges/rubric en `app/` (`cmg_evaluation_service.py`) | — |

**Técnicamente más coherente con el Master Spec [PROPUESTA, no adoptada]: D** — regla determinística versionada como gold operativo (reproducible, n≥100, auditable), con validación del **mismo panel de ≥10 expertos** que responderá SUS sobre un subconjunto (acuerdo inter-juez y κ contra la regla); LLM-as-judge solo como control auxiliar declarado, nunca como verdad de referencia. Requiere resolver antes la **semántica de la etiqueta** (DEC-03):

| Semántica de etiqueta | Matriz | Compatible con RF05 (4 siempre) | Problema |
|---|---|---|---|
| (i) Modalidad **dominante** ∈ {código, diagrama, texto, audio} | **4×4 multiclase**, F1 macro | Sí | "Balanced-Multimodal" no tiene dominante: hace falta una regla de desempate o una quinta clase (rompe el 4×4) |
| (ii) Conjunto de modalidades **priorizadas** (`e_m=2`) | 4 matrices 2×2 (multilabel), F1 micro/macro | Sí | La asesoría habla de 4×4, no de multilabel |
| (iii) Vector completo de énfasis `e` | Concordancia por dimensión (κ ponderado) | Sí | No produce P/R/F1 estándar sin binarizar |

---

## 10. Diseño F1_adapt

[ASESORÍA DEFINE]: `Precision=TP/(TP+FP)`, `Recall=TP/(TP+FN)`, `F1=2PR/(P+R)`, umbral ≥0.85. [ASESORÍA NO DEFINE]: unidad de análisis y mecanismo de evaluación.

Propuesta operacional (sujeta a DEC-03):

- **Unidad de análisis:** el **caso** = un par `(perfil, concepto)` (ver DEC-07). F1 se calcula sobre el conjunto de los n≥100 casos (macro sobre las 4 clases si semántica (i)).
- `g_best` → etiqueta predicha: `argmax_m e_m(g_best)` con desempate determinista declarado (orden fijo de modalidades), o el conjunto `{m: e_m=2}` según semántica.
- Matriz de confusión 4×4 acumulada; `Precision/Recall/F1` por clase y macro; F1_adapt = macro-F1.
- Módulo puro `adaptation_swarm/gold/f1.py`, con pruebas contra matrices de valores conocidos (calculadas a mano) y propiedades (F1∈[0,1]; matriz diagonal → 1).
- **No** reutilizar `app/benchmark/metrics.py` (proxy sembrado con ruido).
- Reportar además IC95% (bootstrap sobre casos) y la matriz completa, no solo el escalar.

---

## 11. Diseño perfiles sintéticos

### 11.1 Perfil JSON → AG1 → W [RF01, RF02 — ASESORÍA DEFINE la existencia; el resto PROPUESTA]

**Esquema JSON v0 (RF01 fija 3 campos; el resto es propuesta):**

```json
{ "schema_version": "profile-v0",
  "profile_id": "syn-0001",
  "nivel": 0.0-1.0,                       // RF01
  "estilo": {"visual":..,"auditivo":..,"textual":..,"codigo":..},  // RF01 "estilo"; PROPUESTA: 4 dims que suman 1
  "tasa_error_previa": 0.0-1.0,           // RF01
  "arquetipo": "visual_dominante|logico_sintactico|explicativo_conceptual|balanced_multimodal",   // sintético
  "dificultad": "secuencial|condicional|repetitivo|arreglos|funciones",                            // sintético
  "concept_id": "..." }
```

**`W=[w_v,w_a,w_t,w_c]` [PROPUESTA]:** cada `w` ∈ [0,1], Σ=1 (normalización `w_i = s_i/Σ s`, con suavizado ε para evitar Σ=0). Semántica: peso relativo de la modalidad visual (diagrama), auditiva (audio/TTS), textual (explicación) y de código en el paquete ideal del perfil. `nivel` y `tasa_error_previa` **modulan** W (p. ej., tasa de error alta desplaza peso hacia el par código/diagrama guiados); la regla exacta **no está en la asesoría** → DEC-13. **Relación con `Simil(S,W)`:** `W` es el objetivo contra el que se mide la distribución de énfasis de `S`.

**Conexión con el VARK real del repo:** `compute_modality_scores` produce 4 dimensiones `visual/reading/audio/kinesthetic`. Mapeo natural a `[w_v,w_t,w_a,·]`; **no existe dimensión "código"** (kinesthetic ≠ código) → no hay equivalencia demostrable; los perfiles reales quedan **fuera** de esta PoC (la asesoría pide perfiles sintéticos).

### 11.2 Generación de los 100 perfiles [ASESORÍA DEFINE: distribución; PROPUESTA: método]

Requisito: 25/25/25/25 por arquetipo **y** 20×5 por dificultad. Diseño **factorial balanceado**: 4 arquetipos × 5 dificultades = 20 celdas × **5 réplicas** = **100**; ambas marginales cumplen exactamente por construcción (25 y 20). Verificación por conteo en el script generador y en un test.

- **Centroides de W por arquetipo [PROPUESTA — no aprobados; DEC-13]:** p. ej. Visual-Dominante concentra peso en `w_v`; Lógico-Sintáctico en `w_c`; Explicativo-Conceptual en `w_t`; Balanced ≈ uniforme. Muestreo `W ~ Dirichlet(κ·centroide)` con κ y semilla registrados (garantiza Σ=1). Los valores numéricos de centroides y κ **no existen en la asesoría**.
- **Dificultad → concepto real:** los 8 módulos del currículo (verificado en Postgres) se mapean a las 5 categorías: secuencial ← {Introducción, Variables y Tipos, Operadores}; condicional ← Condicionales; repetitivo ← Bucles; arreglos ← Arreglos; funciones ← Funciones (Recursividad queda fuera; requiere confirmación, DEC-07). Los 32 conceptos existentes proveen los `ConceptAnchor` y el código/ejercicios de catálogo.
- **Unidad de generación (DEC-07):** dos lecturas — 100 perfiles únicos (cada uno con 1 concepto asignado) o 100 combinaciones perfil×concepto. El diseño 4×5×5 sirve para ambas.
- **Dataset versionado:** `datasets/synthetic_profiles/profiles-v1.jsonl` + `manifest.json` (semilla, hashes, conteos, versión del generador).

---

## 12. Diseño multimodal

Pipeline [ASESORÍA DEFINE]: AG2→código, AG3→diagrama, AG4→texto, AG4→TTS; AG0 evalúa candidatos con 𝓕; el paquete final contiene las 4 piezas.

**Coherencia código ↔ diagrama ↔ texto ↔ audio [PROPUESTA, por construcción]:**

1. **`ConceptAnchor`** (fuente única): `{concept_id, concept_version, learning_objective_id, terms[], code_identifiers[]}` generado una vez y pasado a los tres agentes. Deriva del `Concept`/`LearningObjective` reales y de la plantilla de catálogo (`cmg_concept_catalog`).
2. **AG2** produce el código y lo valida en el sandbox (offline, biblioteca M1); emite `code_ref, sha256, sandbox_status`.
3. **AG3** construye el diagrama **a partir del AST del código** (nodos = funciones/ramas/bucles; etiquetas = identificadores), no de un texto libre. Se valida con `MermaidValidator`. Coherencia código↔diagrama es estructural.
4. **AG4-texto** redacta usando `code_identifiers` y `terms` como vocabulario obligatorio.
5. **AG4-TTS** sintetiza **exactamente** el texto (mismo `sha256_text`); el audio guarda `text_sha256` como clave de vinculación.
6. **AG0** rechaza (o penaliza vía `Coher`) paquetes cuyos hashes no encadenan.

**Identificadores y versiones:**

| ID | Formato | Uso |
|---|---|---|
| `content_id` | `sha256(concept_id ‖ anchor_version ‖ modalidad ‖ variante ‖ generator_version)` | pieza de biblioteca (código/diagrama/texto/audio) |
| `candidate_id` | UUID | realización de una partícula en una iteración |
| `particle_id` | `(cycle_id, idx)` | |
| `iteration_id` | `(cycle_id, k)` | |
| `cycle_id` | UUID | una adaptación completa |
| `package_id` | `sha256(content_id_code ‖ content_id_diagram ‖ content_id_text ‖ content_id_audio ‖ cycle_id)` | paquete entregado |
| `library_version` | semver + hash del manifiesto | biblioteca de candidatos |

**Paquete de salida [ASESORÍA DEFINE RF05]:** `{code, diagram_mermaid, text, audio_ref}` + `package_id`, `W`, `g_best`, `F`, `k_stop`, `stop_reason`. El audio se referencia por URL/`content_id`; el archivo debe **existir** al responder (RF05: "audio real, no bandera").

---

## 13. Diseño TTS

[ASESORÍA DEFINE]: AG4 produce audio (TTS). [Master Spec §10]: no se acepta "existe generación de audio" sin un **archivo real** producido por un proveedor. Estado actual: `multimodal_generation_config.py` solo declara `generate_audio_directly=False` y `preferred_audio_model="elevenlabs"` como texto; sin SDK ni llamada.

| Opción | Proveedor | Costo | Reproducibilidad | Integración con el repo | Riesgo |
|---|---|---|---|---|---|
| Nube A | OpenAI TTS | por carácter | Media (versión de modelo) | **SDK `openai` ya instalado** (2.44.0) y `OPENAI_API_KEY` en `Settings` | Costo API no presupuestado explícitamente (Master Spec §25 #6) |
| Nube B | ElevenLabs | por carácter/plan | Media | Requiere SDK nuevo; el string ya está en config | Presupuesto, latencia |
| Local | motor open-source local (p. ej. Piper) | 0 | **Alta** (binario + modelo fijados) | Requiere dependencia/modelo nuevo y CPU | Calidad de voz en español, peso de imagen |

Diseño independiente del proveedor: interfaz `TTSProvider(Protocol){ name, version, synthesize(text, voice, lang) -> AudioResult{bytes, mime, duration_s, sha256} }`, caché por `sha256(text ‖ voice ‖ model ‖ version)`, almacenamiento con `MultimodalService.store_content` (categoría `audio`, ya soporta `.mp3/.wav/.ogg`), registro de la llamada (proveedor, modelo, versión, latencia, tamaño, hash) en `CandidatoModal`/biblioteca. **Evidencia mínima:** archivo real + log de llamada + hash. Formato propuesto: MP3 (compat. con `<audio>` de `ExternalResourceCard`/`ContentViewer` ya en el frontend). → **DEC-06** (proveedor/presupuesto).

---

## 14. Diseño métricas

| ID | Métrica | Fuente de medición | Cálculo | Estado del diseño |
|---|---|---|---|---|
| M1 | `T_conv` | `IteracionPSO.k` y `CicloAdaptacion.stop_reason` | `k_stop` (iteraciones) y `t_conv_ms = t_stop − t_ini` (monotónico) | definido; ver tautología (DEC-10) |
| CR | Tasa de convergencia | `stop_reason` | `#ciclos con stop_reason=epsilon / #ciclos` — **definición nuestra**, la asesoría no la define | DEC-10 |
| M2 | Overhead de comunicación inter-agente | log de mensajes | `Σ(t_recv−t_sent)` por ciclo; nº de mensajes; bytes | asesoría sin fórmula → propuesta |
| M3 | `F1_adapt`, Precision, Recall | `EvaluacionGoldStandard` vs `g_best` | §10 | DEC-03 |
| M4 | Coherencia | `Coher(S*)` | §8 | DEC-04 |
| M5 | `L_resp` | cliente de carga (t0 envío → último byte) + `t_mono` del servidor | percentiles p50/p90/p95/p99 | §15 |
| M6 | Throughput | cliente de carga | `N_ok/Δt` en ventana estacionaria; error <1% | §15 |
| Recursos | CPU, RAM | muestreador durante las corridas | proceso backend + Redis + Postgres; `psutil` **no instalado** (a decidir en F7-3) o `/proc`/`podman stats` | sin fórmula en la asesoría |
| M7 | SUS | `RespuestaSUS` | §16 | definido |

Toda cifra se etiqueta con `run_id`, `library_version`, `seed`, `commit`. No se reporta ningún umbral como logrado sin ejecución real (Master Spec §27, criterios 1–2).

---

## 15. Diseño benchmark (L_resp y throughput)

**[ASESORÍA DEFINE]:** escenarios 1, 10, 25, 50, 100 peticiones simultáneas; JMeter v5.6 y Locust; `L_resp<2.0 s`; `Throughput≥20 req/s`; error `<1%`. **El resto es propuesta.**

| Aspecto | Definición propuesta |
|---|---|
| Endpoint | `POST /api/adaptation` (nombre propuesto) |
| Payload | un perfil JSON del dataset de 100 perfiles (§11), seleccionado con semilla fija; sin autenticación de estudiante (la PoC no usa estudiantes reales) o con un token de servicio fijo |
| Inicio de la medición | envío del primer byte de la request (cliente) |
| Fin | recepción del **último byte** del cuerpo JSON que contiene el paquete completo (4 piezas; el audio debe existir y estar referenciado) |
| Se incluye | validación de perfil, AG1, ciclo PSO completo (≤15 iteraciones), Redis, ensamblado, persistencia síncrona mínima |
| Se excluye | la descarga posterior del archivo de audio (`GET` del `audio_ref`), y la persistencia asíncrona de trazas detalladas (declarada) |
| Modo | corridas separadas y **etiquetadas** para M1 (biblioteca) y, si se quiere, M2 (en línea) |
| Warm-up | 10 requests descartados por escenario; **cold start** (primer request tras arranque) se reporta aparte |
| Concurrencia | 1, 10, 25, 50, 100 usuarios virtuales (VU) con *ramp-up* corto y meseta de ≥60 s; sin *think time* |
| Percentiles | p50, p90, p95, p99 y máximo |
| Errores | tasa de error por tipo (timeout cliente, 5xx, 4xx); un ciclo con `status=failed` cuenta como error |
| Throughput | `N_ok / duración de la meseta` |
| Criterio RNF01 | p95 `<2.0 s` con ≤25 VU (Master Spec §5) |
| Criterio RNF04 | throughput `≥20 req/s` con error `<1%` en estrés progresivo (1→50 hilos) |
| Aritmética | Little: 20 req/s × 2 s ⇒ ~40 ciclos en vuelo; el diseño debe soportarlo (event loop, pool de Postgres, Redis) |

**Herramientas:** Locust (Python; `locustfile.py`) y JMeter 5.6 (`plan.jmx`); **ambos exigidos por la asesoría**. Java está presente; ninguno está instalado (F1-2). Riesgo declarado: Locust con Python 3.14 (compatibilidad de `gevent`) no verificado. **Validez del entorno:** generador de carga y SUT en el mismo host de 8 CPU/7 GB (≈1 GB libre al medir) sesga los resultados; se debe declarar y, si es posible, separar. Los benchmarks históricos del repo (saturación de QueuePool cerca de N≈80 en login) son una advertencia: el endpoint nuevo debe evitar trabajo síncrono de DB en el camino caliente (persistir en segundo plano o con pool asíncrono).

---

## 16. Diseño SUS

- **Instrumento:** SUS de Brooke (10 ítems, escala Likert 1–5). Versión en español a **seleccionar y citar** (DEC-16); la asesoría cita el procedimiento en su §4.4 pero el Master Spec no lo transcribe.
- **Participantes:** n≥10 docentes/expertos [ASESORÍA DEFINE].
- **Procedimiento [PROPUESTA]:** guion de tareas fijo y versionado (p. ej. cargar un perfil, obtener un paquete, revisar las 4 modalidades, leer la traza del enjambre), consentimiento informado, identificación **seudonimizada**, aplicación tras la demostración.
- **Cálculo [estándar SUS]:** ítems impares `(respuesta−1)`, ítems pares `(5−respuesta)`; suma × 2,5 → 0–100 por evaluador; media del grupo.
- **Criterio:** media `>75.0` [ASESORÍA DEFINE]; análisis con Shapiro-Wilk → t de una muestra o Wilcoxon (α=0,05, IC95%) [ASESORÍA DEFINE]; el Master Spec §22 recomienda revisar ese plan.
- **Almacenamiento:** tabla `respuesta_sus` (§17); respuestas crudas + puntaje calculado + versión del instrumento/guion.
- **Evidencia:** exportación CSV de respuestas crudas y notebook/script de cálculo reproducible.
- **En esta fase no se recolecta ninguna respuesta.** Depende de que exista el artefacto funcional (RF05) y de aprobación ética/logística (DEC-16).

---

## 17. Modelo de datos

**Convenciones del repo (verificadas):** SQLAlchemy 2.0 `Base` declarativa; PK `String(36)` con `uuid4`; `DateTime(timezone=True)`; `JSON`; Alembic con head lineal; patrón `run_label` de `experiment_cmg_results`; modelo `IdempotencyKey` existente. Los tests de modelos de `app/` corren en SQLite, así que se prefieren tipos portables (`JSON`, no `JSONB`, salvo decisión).

**Entidades del Master Spec §18 + ampliaciones necesarias.** Las marcadas ➕ **no** están en el Master Spec (se listan aparte para que no se confundan con lo aprobado).

| Entidad | Campos clave | PK | FK | Índices / constraints | Timestamps | Versionado | Idempotencia |
|---|---|---|---|---|---|---|---|
| **PerfilSintetico** | `id`, `profile_ref` (ej. syn-0001), `arquetipo`, `dificultad`, `concept_id`, `nivel`, `tasa_error_previa`, `estilo` JSON, `payload_json`, `dataset_version` | `id` | `concept_id→concepts.id` | `UNIQUE(dataset_version, profile_ref)`; `CHECK arquetipo IN (…)`; `CHECK dificultad IN (…)` | `created_at` | `dataset_version`, `schema_version` | unique por (dataset, ref) |
| **PesosModalidad** | `id`, `profile_id`, `cycle_id`, `w_v,w_a,w_t,w_c`, `rule_version` | `id` | `profile_id`, `cycle_id` | `CHECK 0≤w≤1`; `CHECK abs(w_v+w_a+w_t+w_c−1)<1e-9`; `UNIQUE(cycle_id)` | `created_at` | `rule_version` | `UNIQUE(cycle_id)` |
| ➕ **ExperimentoRun** | `id`, `run_label`, `spec_version`, `git_commit`, `library_version`, `batch_seed`, `config_json`, `config_hash`, `env_json` | `id` | — | `UNIQUE(run_label)` | `started_at, finished_at` | los tres versionados | `UNIQUE(run_label)` |
| **CicloConvergencia** (Master Spec: 1 fila por iteración) → se propone **separar** en ➕ **CicloAdaptacion** (1 por perfil/ejecución) y **IteracionPSO** (k filas) | Ciclo: `id`, `run_id`, `profile_id`, `seed`, `status`, `stop_reason`, `k_stop`, `t_ini,t_fin`, `t_conv_ms`, `g_best_F`, `g_best_x` JSON. Iteración: `cycle_id`, `k`, `g_best_F`, `delta_F`, `t_iter_ms` | `id` / `(cycle_id,k)` | `run_id`, `profile_id`; `cycle_id` | `UNIQUE(run_id,profile_id,replicate)`; `UNIQUE(cycle_id,k)`; `CHECK 0≤k≤15`; `CHECK stop_reason IN (epsilon,k_max,error)` | `created_at` | `seed`, `config_hash` | `UNIQUE(run_id,profile_id,replicate)` |
| ➕ **ParticulaPSO** | `cycle_id`, `k`, `idx`, `x` JSON, `v` JSON, `S` JSON (φ(x)), `F`, `F_simil,F_coher,F_redund,F_costt`, `p_best_F`, `p_best_x` | `(cycle_id,k,idx)` | `cycle_id` | índice `(cycle_id,k)` | — | — | PK compuesta |
| **CandidatoModal** | `id`, `cycle_id`, `k`, `particle_idx`, `modalidad`, `variante`, `content_id`, `content_ref`, `sha256`, `generator_version`, `sandbox_status`, `mime`, `duration_ms`, `is_p_best` | `id` | `cycle_id`; `content_id→biblioteca` | `CHECK modalidad IN (codigo,diagrama,texto,audio)`; `UNIQUE(cycle_id,k,particle_idx,modalidad)` | `created_at` | `generator_version` | unique compuesta |
| ➕ **BibliotecaCandidato** (M1) | `content_id`, `concept_id`, `anchor_version`, `modalidad`, `variante`, `blob_ref`, `sha256`, `library_version`, `validated` | `content_id` | `concept_id` | `UNIQUE(concept_id,anchor_version,modalidad,variante,library_version)` | `created_at` | `library_version` | por `content_id` |
| **PaqueteMultimodal** | `package_id`, `cycle_id`, `code_content_id`, `diagram_content_id`, `text_content_id`, `audio_content_id`, `S_star` JSON, `F_star` | `package_id` | `cycle_id` + 4 refs | `UNIQUE(cycle_id)`; `NOT NULL` en las 4 refs (RF05) | `created_at` | — | `UNIQUE(cycle_id)` |
| **EvaluacionGoldStandard** | `profile_id`, `concept_id`, `gold_label`, `method` (regla/experto/llm), `rule_version`, `annotator_id?`, `agreement?` | `id` | `profile_id`, `concept_id` | `UNIQUE(profile_id,concept_id,method,rule_version)` | `created_at` | `rule_version` | unique compuesta |
| **MetricaCiclo** | `cycle_id`, `t_conv_ms`, `k_stop`, `converged`, `f1_pred_label`, `l_resp_ms`, `n_msgs`, `comm_overhead_ms`, `cpu_pct`, `ram_mb` | `cycle_id` | `cycle_id` | — | `created_at` | — | 1:1 |
| ➕ **MensajeAgente** | copia de `swarm:{cycle}:log`: `message_id`, `correlation_id`, `cycle_id`, `k`, `agent_id`, `recipient`, `type`, `t_sent`, `t_recv`, `payload_ref`, `status`, `error` | `message_id` | `cycle_id` | índice `(cycle_id,t_sent)` | — | `schema_version` | `message_id` |
| **RespuestaSUS** | `id`, `evaluador_id` (seudónimo), `item_1..item_10`, `puntaje`, `instrumento_version`, `guion_version` | `id` | — | `CHECK 1≤item≤5`; `UNIQUE(evaluador_id,instrumento_version)` | `created_at` | `instrumento_version` | unique |

**Restricciones globales:** timestamps con zona; JSON con `schema_version`; ninguna tabla nueva modifica `experiment_cmg_results` ni el estado del kernel. **Migraciones:** no se hacen en esta fase; cadena a partir de `928a10b002db` (untracked) → DEC-14.

---

## 18. Observabilidad

Cadena exigida: `profile_id → cycle_id → iteration → particle → candidate → agent → fitness → final package`.

**Diseño [PROPUESTA]:**

1. **Correlación única:** `correlation_id` en cada mensaje y span. Reutilizar `app/tracing/CorrelationEngine` y `trace_langgraph_node` (LIVE) para nodos de AG0, y `app/telemetry/spans_operativos.py` para llamadas LLM/TTS (telemetría operativa con LangSmith, no registro científico).
2. **Registro científico** (para la tesis) ≠ telemetría operativa: el registro es la base de datos (tablas del §17: ciclo, iteración, partícula, candidato, mensaje, paquete, métrica). La telemetría operativa (LangSmith) puede faltar sin invalidar la evidencia (mismo criterio que RFC-0007 del runtime).
3. **Eventos mínimos por iteración:** `k`, `F` de cada partícula, `p_best` actualizados, `g_best`, `ΔF`, `stop_check`.
4. **Comunicación inter-agente:** cada mensaje con `t_sent/t_recv`, agente emisor/receptor, tipo y tamaño; volcado del stream a `MensajeAgente`.
5. **Recursos:** muestreo de CPU/RAM del proceso y contenedores durante las corridas de carga.
6. **Consulta de trazabilidad:** una función/consulta SQL que, dado `profile_id`, reconstruye el árbol completo y devuelve el paquete final (criterio de aceptación).
7. **Reconstruibilidad:** `run_manifest.json` (semilla, commit, versiones, hashes) para repetir un ciclo bit a bit en modo M1.

---

## 19. Testing

Principios: sin mocks de dominio para Redis/Postgres en integración (el proyecto exige validar contra servicios reales); los unitarios de PSO/fitness/W/F1 son puros.

| Nivel | Qué se prueba | Herramienta / notas |
|---|---|---|
| **Unit — PSO** | ecuaciones literales (valores calculados a mano para 1 partícula/1 dimensión); `p_best/g_best` monótonos; `Vmax`; semilla ⇒ trayectoria idéntica; parada por ε y por `k_max=15` | pytest, sin Redis |
| **Unit — discretización** | φ total, idempotente en el dominio, monótona, saturación, empates de `round` | pytest |
| **Unit — fitness** | cada término en casos límite; `α+β+γ+δ=1` validado; rango de 𝓕; separación Coher/Redund | pytest |
| **Unit — W** | Σ=1, rango [0,1], reglas de arquetipo/nivel/error, Σ=0 → suavizado | pytest |
| **Unit — gold/F1** | matrices conocidas; F1∈[0,1]; diagonal → 1; desempate determinista | pytest |
| **Unit — cada agente** | `handle()` con mensajes válidos e inválidos; idempotencia por `message_id`; errores explícitos | pytest |
| **Unit — perfiles sintéticos** | 100 filas, marginales 25/25/25/25 y 20×5 exactas, semilla reproducible | pytest |
| **Integración — Redis** | streams, consumer groups, reintento, TTL, orden; **Redis real en contenedor podman** | pytest-asyncio |
| **Integración — AG0–AG4** | ciclo completo con los cinco agentes por el bus; timestamps solapados (RF03) | pytest-asyncio |
| **Integración — multimodal** | 4 piezas presentes; hashes encadenados; código pasa sandbox; Mermaid válido; audio real con proveedor | pytest (marca `integration`) |
| **Integración — persistencia** | escritura/consulta de trazabilidad; constraints (CHECK/UNIQUE) | pytest sobre Postgres (los tests de `app/` usan SQLite: declarar cuáles corren dónde) |
| **E2E** | perfil → PSO → convergencia → paquete → métricas persistidas | script + pytest |
| **Performance** | 1/10/25/50/100 VU con Locust y JMeter; p50/p90/p95/p99; error<1% | reportes versionados |
| **Reproducibilidad** | mismo `seed`+config+`library_version` ⇒ mismo `g_best`; manifiesto completo; sin dependencia de reloj en 𝓕 | pytest + comparación de manifiestos |
| **Propiedades** | (con muestreo sembrado; `hypothesis` no instalado) 𝓕 acotada; `g_best` nunca empeora; φ(x) ∈ dominio | pytest parametrizado |

Cada test cita el requisito que cubre (RFxx/RNFxx) en su docstring, para mantener trazabilidad con el Master Spec.

---

## 20. Dependencias

```
F0 ──► F1 ──► F2 ──► F3 ──► F4 ──► F5 ──► F6 ──► F7 ──► F8 ──► F9 ──► F10 ──► F11
```

| Fase | Depende (fuerte) | Depende (débil) | Bloqueantes | Paralelizable con |
|---|---|---|---|---|
| **F0** Decisiones/ADR/perfil JSON | — | — | DEC-01,02,03,04,09,14 | F1-2 (Locust/JMeter) |
| **F1** Infra (Redis, carga) | DEC-05 (confirmación), DEC-15 | F0 | podman/compose para Redis | F0, F6 (esquemas) |
| **F2** Modelo de datos | F0-3 (esquema perfil), **DEC-14 (head untracked)** | F1 | commit de la cadena CMG | F3 (interfaces) |
| **F3** Agentes | **DEC-01**, F1-1, F2 | F0 | ADR de arquitectura | F4 (PSO puro) |
| **F4** PSO + 𝓕 | **DEC-02, DEC-04, DEC-08, DEC-10** | F3 | operador φ aprobado | F5 (biblioteca), F6 |
| **F5** Multimodal (+TTS) | F3, **DEC-06, DEC-09** | F4 | proveedor TTS | F6 |
| **F6** Perfiles sintéticos | F0-3, DEC-07, DEC-13 | — | centroides/reglas | F4, F5 |
| **F7** Métricas + gold | **DEC-03**, F4 | F6 | semántica de la etiqueta | F8 (scripts de carga) |
| **F8** Benchmark | F1-2, F3 (endpoint), F5 | F7 | endpoint de adaptación | F7 |
| **F9** Validación (100 casos + SUS) | F4, F6, F7, F5; SUS: **DEC-16** | F8 | gold aprobado | — |
| **F10** Documentación | F9 | — | — | — |
| **F11** Auditoría final | F10 | — | — | — |

**Camino crítico:** DEC-01 → F3 → F4 (con DEC-02/04) → F5 → F9. **Riesgo de calendario:** las decisiones DEC-01/02/03 son de aprobación externa (asesor) y están en el camino crítico.

---

## 21. Conservación (A)

| Qué | Ruta | Uso en el nuevo sistema |
|---|---|---|
| Kernel y capacidades del runtime | `backend/runtime/**` | **Intactos.** Siguen sirviendo al flujo de estudiantes; el PoC no los importa ni modifica |
| Sandbox de ejecución | `backend/app/sandbox/{runner,policy,schemas,docker_manager}.py` | Validación de código de AG2 (fase de construcción de biblioteca); configurar `docker_bin` a podman (sin código nuevo si el parámetro basta; **no verificado**) |
| Generación/evaluación CMG y catálogo | `backend/app/services/cmg_*.py` | Fuente de plantillas de código/ejercicios (32 conceptos) y de D1/D2/D3 como validadores auxiliares; **no modificados** |
| Mermaid | `backend/app/benchmark/mermaid.py` | `MermaidValidator` para AG3 |
| Almacenamiento multimodal | `backend/app/services/multimodal_service.py` | Persistencia de audio/binarios |
| LLM | `backend/app/llm/{service,cost_tracker,config}.py`, `runtime/domain/shared/llm_openai.py` | Texto (AG4) y control de presupuesto de tokens |
| Trazas/telemetría | `backend/app/tracing/**`, `app/telemetry/**` | Correlación y spans operativos |
| Postgres + Alembic + Docker | `docker-compose.yml`, `backend/alembic/**`, `Dockerfile` | Base de persistencia |
| Histórico experimental | `experiment_cmg_results`, `experiments/results/**`, R22–R32, D1/D2/D3 | Conservados sin cambios (Master Spec §23, criterio 6) |
| Harness de carga propio | `backend/scripts/benchmark_capacidad_http.py`, `instrumentacion_e1.py` | Referencia de diseño de medición |

## 22. Reemplazos (B adaptar / C reemplazar / D eliminar)

**B. Adaptar (cambios acotados, tras las decisiones):**
- `backend/app/services/multimodal_generation_config.py` — las banderas de audio pasan de configuración inerte a controlar una llamada real.
- `docker-compose.yml` (+servicio `redis`), `backend/requirements.txt` (+cliente `redis`; herramientas de carga y medición de recursos si se aprueban) — **no en esta fase**.
- `backend/app/main.py` (registro del router nuevo), `backend/app/models/__init__.py` (registro de modelos) — ya tienen cambios sin commitear: coordinar con DEC-14.
- `SandboxRunner.docker_bin` — apuntar a podman en el entorno de desarrollo (verificar compatibilidad de los comandos `create/start/exec/cp`).

**C. Reemplazar:**
- Nada del código vivo se reemplaza. Se reemplaza **documentación**: `docs/SWARM_INTELLIGENCE_ARCHITECTURE.md` describe archivos inexistentes (`app/agents/graph.py`, `app/swarm/coordinator.py`) y debe sustituirse por el ADR nuevo cuando exista.
- `CLAUDE.md` / `THESIS_SCOPE_FREEZE.md` (título y régimen) requieren enmienda **humana** para reflejar el nuevo alcance DSR.

**D. Eliminar:** **nada.** No se propone eliminar ningún archivo ahora.

## 23. Nuevos componentes (E)

```
backend/adaptation_swarm/
  agents/{base.py, ag0_orchestrator.py, ag1_profil.py, ag2_code.py, ag3_diagram.py, ag4_text.py}
  bus/{envelope.py, redis_bus.py, streams.py}
  graph/cycle_graph.py                 # LangGraph de AG0
  pso/{space.py, decode.py, engine.py, params.py, rng.py}
  fitness/{simil.py, coher.py, redund.py, costt.py, fitness.py}
  profiles/{schema.py, w_mapping.py, generator.py}
  gold/{rubric.py, f1.py, agreement.py}
  library/{anchor.py, builder.py, manifest.py}      # biblioteca M1
  tts/{provider.py, openai_tts.py|local_tts.py}
  metrics/{cycle.py, recursos.py, sus.py}
  persistence/{repository.py}
  api/router.py                        # POST /api/adaptation
backend/app/models/{perfil_sintetico.py, pesos_modalidad.py, ciclo_adaptacion.py, iteracion_pso.py,
                    particula_pso.py, candidato_modal.py, biblioteca_candidato.py,
                    paquete_multimodal.py, evaluacion_gold.py, metrica_ciclo.py,
                    mensaje_agente.py, respuesta_sus.py, experimento_run.py}
backend/alembic/versions/<nuevas>.py
backend/tests/adaptation_swarm/**
backend/loadtest/{locustfile.py, plan.jmx, README.md}
datasets/synthetic_profiles/{profiles-v1.jsonl, manifest.json}
docs/architecture/ADR/ADR-00xx-poc-enjambre-pso.md
```

---

## 24. Riesgos

| # | Riesgo | Nivel | Mitigación propuesta (sin reducir alcance) |
|---|---|---|---|
| 1 | **Contradicción con decisiones vigentes**: CONCEPT-0001 ("sin cognición central", agentes que no se hablan), RFC-0006, P12 (sin azar en el kernel) y ADR-0011 (stack de agentes retirado) vs AG0 central, mensajería y PSO con azar | **Crítico** | ADR nuevo con alcance acotado al subsistema PoC; el kernel no se toca. La contradicción se registra, no se oculta (DEC-01) |
| 2 | Latencia: generar por partícula (LLM/TTS/sandbox) rompe `L_resp<2 s`; `Throughput≥20` exige ~40 ciclos en vuelo | **Crítico** | Modo M1 (biblioteca) + modo M2 separado; medir cada uno etiquetado (DEC-09) |
| 3 | Gold standard indefinido y semántica de etiqueta incompatible con RF05/4×4; riesgo de circularidad con `Simil` | **Crítico** | Gold D independiente de `W`; validación con expertos (DEC-03) |
| 4 | Discretización: ecuaciones continuas sobre espacio discreto; plateaus de 𝓕 y parada prematura | **Alto** | φ documentado + pruebas + paciencia opcional pre-registrada (DEC-02, DEC-10) |
| 5 | Términos de 𝓕 sin definición; Coher/Redund pueden solaparse | **Alto** | Definiciones deterministas (§8), separación por `ConceptAnchor` (DEC-04) |
| 6 | Repo sucio: stack CMG y **head de Alembic sin versionar**; cambios sin commitear en `runtime/` | **Alto** | Commit ordenado por el propietario antes de F2 (DEC-14) |
| 7 | Audio real: proveedor/presupuesto no definidos; el repo solo tiene un flag inerte | **Alto** | Interfaz `TTSProvider` + caché + evidencia de archivo (DEC-06) |
| 8 | Entorno: Python 3.14.7 local vs 3.12 objetivo; sin `docker` (solo podman); 8 CPU/7 GB; Locust en 3.14 sin verificar | **Alto** | Fijar versión objetivo y entorno de medición (DEC-15); declarar host de carga |
| 9 | Alcance total (5 agentes + Redis + PSO + TTS + gold + SUS + carga) en el cronograma de 16 semanas | **Alto** | Camino crítico explícito (§20); slice vertical primero (§27) |
| 10 | Reproducibilidad con LLM/TTS | **Medio** | Biblioteca versionada + caché por hash + `temperature=0` + manifiesto |
| 11 | Concurrencia: pool síncrono de DB (E1/E2 saturaron cerca de N=80) | **Medio** | Persistencia fuera del camino caliente; pool y workers dimensionados; medir |
| 12 | Redis mal usado como decoración | **Medio** | AG1–AG4 sin estado, sin llamada directa desde AG0; pruebas que verifican que el flujo falla si Redis se apaga |
| 13 | Costos API (LLM/TTS) | **Medio** | Biblioteca offline una vez; `cost_tracker` existente |
| 14 | Validez de perfiles sintéticos (centroides arbitrarios) | **Medio** | Documentar y pre-registrar; sensibilidad |
| 15 | Seguridad del sandbox (código generado) | **Bajo-Medio** | Política AST + límites ya existentes; el código proviene de catálogo/biblioteca validada |
| 16 | Discrepancias del Master Spec (p. ej. "Corrida 2 = datos reales", "L_resp no comprobado") | **Bajo** | Corregidas aquí; sugerir enmienda del Master Spec (no modificado por esta fase) |

---

## 25. Decisiones pendientes

| ID | Decisión | Qué se decide | Bloquea | Quién |
|---|---|---|---|---|
| **DEC-01** | Modelo de agentes y ADR | Aprobar 5 agentes reales con mensajería en un **subsistema nuevo** (`adaptation_swarm/`) y redactar el ADR que declare el alcance frente a CONCEPT-0001/RFC-0006/ADR-0011, o reinterpretar "multiagente" con el kernel | F3, F4 | Humano (tesista + asesor) |
| **DEC-02** | PSO discreto | Aprobar el operador φ (alternativa A u otra), la definición de partícula (candidato de paquete) y el espacio de configuración (§7.2) | F4 | Asesor |
| **DEC-03** | Gold standard y etiqueta | Método (A/B/C/D) y semántica de etiqueta (dominante / conjunto / vector) compatible con RF05 y la matriz 4×4 | F7, F9 | Asesor |
| **DEC-04** | Fitness | Definiciones de Simil/Coher/Redund/CostT y valores (o rejilla) de α,β,γ,δ | F4 | Asesor |
| **DEC-05** | Redis | Confirmar adopción literal (el encargo la exige; la asesoría la exige) y el modo de despliegue (compose con podman) | F1-1 | Humano |
| **DEC-06** | TTS | Proveedor, presupuesto y formato | F5 | Humano |
| **DEC-07** | Unidad n=100 y conceptos | 100 perfiles únicos vs 100 perfil×concepto; mapeo dificultad→módulo/concepto; Recursividad fuera | F6 | Asesor |
| **DEC-08** | Parámetros PSO | N, `w`, `c1`, `c2`, `Vmax`, inicialización, política de semilla; pre-registro de sensibilidad | F4 | Tesista (con visto bueno) |
| **DEC-09** | Modo de realización y definición de `L_resp` | M1 (biblioteca) / M2 (en línea) / M3; qué entra y qué se excluye de la latencia (audio, persistencia) | F5, F8 | Asesor |
| **DEC-10** | Convergencia | Regla literal vs paciencia; definición de `CR`; interpretación de `T_conv≤15` | F4, F7 | Asesor |
| **DEC-11** | Framework | LangGraph solo, o LangGraph+FastAgent en roles distintos | F3 | Humano |
| **DEC-12** | Curso | "Programación" vs "Fundamentos de la Programación" | F10 | Asesor |
| **DEC-13** | Perfil y W | Esquema JSON v0; regla perfil→W; centroides y κ de los arquetipos | F0-3, F6 | Asesor |
| **DEC-14** | Higiene del repo | Commitear (o descartar explícitamente) el stack CMG, sus migraciones y los cambios de `runtime/` antes de nuevas migraciones | F2 | **Propietario del repo** (esta fase no crea commits) |
| **DEC-15** | Entorno | Versión de Python objetivo (3.12), sustituto de docker (podman), host de pruebas de carga | F1, F8 | Humano |
| **DEC-16** | SUS | Versión en español, guion de tareas, reclutamiento, consentimiento y ética | F7-4, F9 | Humano |
| **DEC-17** | Plan estadístico | Confirmar Shapiro-Wilk → t/Wilcoxon de una muestra, o adoptar el rigor previo (Wilcoxon pareado + bootstrap) | F9-2 | Asesor |

---

## 26. Backlog de implementación

Formato por tarea: **ID · Tarea · Dep. · Archivos objetivo · Resultado · Tests · Criterio de aceptación · Evidencia · Riesgo.** Las tareas empiezan **después** de cerrar sus DEC; las marcadas 🟢 pueden iniciar sin decisión metodológica.

### F0 — Especificación y decisiones

| ID | Tarea | Dep. | Archivos | Resultado | Tests | Aceptación | Evidencia | Riesgo |
|---|---|---|---|---|---|---|---|---|
| T0-01 | Cerrar DEC-01…DEC-17 | — | acta / ADR | decisiones escritas | — | cada DEC con fecha y responsable | acta | asesor no disponible |
| T0-02 | Redactar ADR del PoC (alcance frente a CONCEPT-0001/RFC-0006/ADR-0011) | DEC-01 | `docs/architecture/ADR/ADR-00xx-…md` | ADR aceptado | — | revisión aprobada | ADR | contradicción normativa |
| T0-03 🟢 | Esquema JSON del perfil `profile-v0` | — | `adaptation_swarm/profiles/schema.py` (cuando se autorice código) / `docs` | esquema versionado + 3 ejemplos | validación de 3 ejemplos y de casos inválidos | schema válido | archivo + tests | campos ambiguos (DEC-13) |
| T0-04 | Especificación matemática de φ, espacio §7.2 y parada | DEC-02, DEC-10 | ADR o `docs/architecture/pso-spec.md` | documento matemático | — | aprobado por el asesor | documento | rechazo de A |
| T0-05 | Rúbrica del gold standard (tabla versionada) | DEC-03, DEC-13 | `adaptation_swarm/gold/rubric.py` + `docs` | rúbrica pre-registrada | tests de cobertura de las 20 celdas | 20 celdas con etiqueta y justificación | rúbrica hash | circularidad |

### F1 — Infraestructura

| ID | Tarea | Dep. | Archivos | Resultado | Tests | Aceptación | Evidencia | Riesgo |
|---|---|---|---|---|---|---|---|---|
| T1-01 | Servicio Redis en compose y cliente asyncio | DEC-05, DEC-15 | `docker-compose.yml`, `backend/requirements.txt`, `bus/redis_bus.py` | Redis activo y alcanzable | integración: PING, XADD/XREADGROUP, TTL | round-trip real medido | log + test | podman vs compose |
| T1-02 🟢 | Esqueleto de carga (Locust y JMeter) con los 5 escenarios | contrato de endpoint (T3-06) | `backend/loadtest/*` | scripts versionados | ejecución de 1 VU contra un endpoint de prueba | 1 escenario corre y produce percentiles | reporte | Locust/3.14 |
| T1-03 | Fijar versión Python/entorno reproducible | DEC-15 | `Dockerfile`, doc | entorno documentado | `python --version` en contenedor | =3.12.x | log | divergencia local |

### F2 — Modelo de datos

| ID | Tarea | Dep. | Archivos | Resultado | Tests | Aceptación | Evidencia | Riesgo |
|---|---|---|---|---|---|---|---|---|
| T2-01 | Commitear/estabilizar la cadena CMG | DEC-14 | (acción del propietario) | head trackeado | `alembic heads` = 1 head trackeado | 1 head versionado | `git ls-files` | pérdida de trabajo |
| T2-02 | Modelos SQLAlchemy §17 | T0-03, T2-01 | `app/models/*.py`, `app/models/__init__.py` | 13 modelos | constraints (CHECK/UNIQUE) en SQLite y Postgres | tests verdes | esquema | tipos no portables |
| T2-03 | Migración Alembic | T2-02 | `alembic/versions/*` | `upgrade head` limpio | `upgrade`/`downgrade` en BD de prueba | sin error | `\d` de tablas | migración sobre datos existentes |

### F3 — Arquitectura multiagente

| ID | Tarea | Dep. | Archivos | Resultado | Tests | Aceptación | Evidencia | Riesgo |
|---|---|---|---|---|---|---|---|---|
| T3-01 | `Envelope` y catálogo de mensajes | T1-01 | `bus/envelope.py` | modelo pydantic versionado | serialización ida/vuelta; campos obligatorios | 100% de campos §5.3 | tests | cambios de esquema |
| T3-02 | `SwarmAgent` + bucle consumidor | T3-01 | `agents/base.py` | clase base con XREADGROUP, idempotencia y errores explícitos | tests de reintento y duplicados | duplicados no reprocesan | tests | bloqueo de consumidores |
| T3-03 | AG1 Profil-Agent | T0-03, T3-02 | `agents/ag1_profil.py`, `profiles/w_mapping.py` | `W` sumando 1 | unit W (Σ=1, límites) | RF02 verificable en log | log de W | regla DEC-13 |
| T3-04 | AG2 Code-Agent | T3-02, T5-01 | `agents/ag2_code.py` | código validado por sandbox | unit + integración con sandbox | `sandbox_status=success` | log | docker/podman |
| T3-05 | AG3 Diagram-Agent (AST→Mermaid) | T3-04 | `agents/ag3_diagram.py` | Mermaid coherente con el código | unit: etiquetas ⊂ identificadores; `MermaidValidator` | válido y coherente | tests | AST de casos raros |
| T3-06 | AG4 Text-Agent (+ TTS) | T3-02, T5-03 | `agents/ag4_text.py` | texto y audio | integración con proveedor real | archivo de audio real | archivo + log | proveedor |
| T3-07 | AG0 + grafo LangGraph (sin PSO) | T3-03…T3-06 | `agents/ag0_orchestrator.py`, `graph/cycle_graph.py` | ciclo que despacha/recolecta por el bus | integración: paralelismo (timestamps solapados) | RF03 demostrado | trazas | estado en grafo vs Redis |
| T3-08 | Endpoint `POST /api/adaptation` | T3-07 | `api/router.py`, `app/main.py` | endpoint operativo | HTTP real | respuesta con 4 piezas | curl + test | contrato |

### F4 — PSO y fitness

| ID | Tarea | Dep. | Archivos | Resultado | Tests | Aceptación | Evidencia | Riesgo |
|---|---|---|---|---|---|---|---|---|
| T4-01 🟢 | Motor PSO continuo con las ecuaciones literales y RNG sembrado | — | `pso/engine.py`, `pso/params.py`, `pso/rng.py` | actualización de v y x, p_best, g_best, parada | ecuaciones a mano; determinismo por semilla; parada ε/k_max | pasa | tests | `Vmax` |
| T4-02 | Decodificador φ y espacio | DEC-02, T0-04 | `pso/decode.py`, `pso/space.py` | φ documentado | propiedades §7.1 | pasa | tests | orden artificial |
| T4-03 | Simil, Redund, CostT | DEC-04 | `fitness/*.py` | términos deterministas | unit por término | rangos [0,1] | tests | calibración de `T_ref` |
| T4-04 | Coher continuo | DEC-04, T3-05 | `fitness/coher.py` | Coher escalar | unit + casos con anclas | ∈[0,1], monótono con solapamiento | tests | ruido léxico |
| T4-05 | 𝓕 completa con validación α+β+γ+δ=1 | T4-03, T4-04 | `fitness/fitness.py` | 𝓕 reproducible | unit + propiedades | escalar reproducible | log de 𝓕 | pesos |
| T4-06 | Integración PSO↔AG0 (bucle con evaluación por el bus) | T3-07, T4-01…05 | `graph/cycle_graph.py` | ciclo completo ≤15 it. | integración + E2E | converge o llega a `k_max` | logs de iteración | plateaus |
| T4-07 | Fuerza bruta de referencia (6.561 configs) | T4-05 | `pso/brute_force.py` | óptimo global por caso | test de coincidencia en casos pequeños | reporte de brecha PSO vs óptimo | reporte | tiempo |

### F5 — Multimodalidad

| ID | Tarea | Dep. | Archivos | Resultado | Tests | Aceptación | Evidencia | Riesgo |
|---|---|---|---|---|---|---|---|---|
| T5-01 | `ConceptAnchor` y constructor de biblioteca (código) | DEC-09, T2-03 | `library/anchor.py`, `library/builder.py` | variantes de código validadas | unit + sandbox | 100% validadas | manifiesto | cobertura de conceptos |
| T5-02 | Variantes de diagrama y texto en biblioteca | T5-01 | `library/builder.py` | piezas + hashes | unit | hashes encadenados | manifiesto | calidad del texto |
| T5-03 | `TTSProvider` + caché + almacenamiento | DEC-06 | `tts/*` | audio real | integración con proveedor | mp3 real + hash | archivo + log | costo |
| T5-04 | Calibración de `t̂_m` y `T_ref` | T5-01…03 | `library/manifest.py` | tabla de tiempos | — | valores congelados | tabla | variabilidad |
| T5-05 | Empaquetado y verificación de coherencia | T5-02, T5-03 | `agents/ag0_orchestrator.py` | `PaqueteMultimodal` con 4 piezas | integración | RF05 verificado por prueba | test E2E | hashes |

### F6 — Perfiles sintéticos

| ID | Tarea | Dep. | Archivos | Resultado | Tests | Aceptación | Evidencia | Riesgo |
|---|---|---|---|---|---|---|---|---|
| T6-01 | Generador factorial 4×5×5 + Dirichlet | DEC-07, DEC-13 | `profiles/generator.py` | `profiles-v1.jsonl` | marginales exactas; semilla | 100 filas 25/25/25/25 y 20×5 | conteo + manifiesto | centroides |
| T6-02 🟢 | Script de verificación de distribución | T6-01 | `profiles/generator.py` | verificación automática | test | pasa | log | — |

### F7 — Métricas

| ID | Tarea | Dep. | Archivos | Resultado | Tests | Aceptación | Evidencia | Riesgo |
|---|---|---|---|---|---|---|---|---|
| T7-01 🟢 | Módulo F1/Precision/Recall desde matriz de confusión | — | `gold/f1.py` | funciones puras | matrices conocidas | valores exactos | tests | semántica (DEC-03) |
| T7-02 | Cálculo de gold por rúbrica y acuerdo con expertos | DEC-03, T0-05 | `gold/rubric.py`, `gold/agreement.py` | etiquetas de 100 casos | unit | 100 casos etiquetados | dataset | circularidad |
| T7-03 | Persistir métricas por ciclo y `MensajeAgente` | T2-03, T3-07 | `persistence/repository.py`, `metrics/cycle.py` | filas por ciclo/iteración | integración | consulta de trazabilidad completa | SQL | costo de escritura |
| T7-04 🟢 | Función SUS (puntaje y agregación) | — | `metrics/sus.py` | cálculo estándar | vectores de ejemplo | reproduce puntajes conocidos | tests | — |
| T7-05 | Muestreo de CPU/RAM | DEC-15 | `metrics/recursos.py` | serie temporal por corrida | test de humo | valores presentes | archivos | `psutil` no instalado |

### F8 — Benchmark

| ID | Tarea | Dep. | Archivos | Resultado | Tests | Aceptación | Evidencia | Riesgo |
|---|---|---|---|---|---|---|---|---|
| T8-01 | Locust con los 5 escenarios | T3-08, T1-02 | `loadtest/locustfile.py` | reporte | corrida real | p50/p90/p95/p99 por escenario | CSV/HTML | host compartido |
| T8-02 | JMeter con los 5 escenarios | T3-08 | `loadtest/plan.jmx` | reporte | corrida real | mismos escenarios | JTL/HTML | instalación |
| T8-03 | Informe de latencia/throughput (M1 y, si aplica, M2) | T8-01, T8-02 | `docs`/reporte | tabla versionada | — | RNF01/RNF04 evaluados sin maquillaje | reporte | umbral no alcanzado |

### F9 — Validación

| ID | Tarea | Dep. | Archivos | Resultado | Tests | Aceptación | Evidencia | Riesgo |
|---|---|---|---|---|---|---|---|---|
| T9-01 | Ejecutar 100 casos con `--dry-run` previo | T4-06, T6-01, T7-01…03 | script de corrida | 100/100 ciclos registrados | dry-run + real | 100/100 con `stop_reason` | tablas | fallos de ciclo |
| T9-02 | Cálculo de F1, T_conv, CR, Coher | T9-01 | `metrics/` | reporte por caso y agregado | unit sobre datos | reproducible | reporte | F1<0.85 |
| T9-03 | Análisis estadístico | DEC-17, T9-02 | script | Shapiro-Wilk y prueba elegida, IC95% | — | reproducible | reporte | normalidad |
| T9-04 | SUS con ≥10 expertos | DEC-16, T3-08 | formulario + `respuesta_sus` | 10 respuestas | cálculo | media y prueba | CSV | reclutamiento |

### F10–F11

| ID | Tarea | Dep. | Archivos | Resultado | Aceptación | Riesgo |
|---|---|---|---|---|---|---|
| T10-01 | Documentación de evidencia y enmienda de CLAUDE.md/Scope Freeze (humano) | F9 | docs | documentos actualizados | revisión del asesor | deriva documental |
| T11-01 | Re-auditoría RF/RNF contra el código final | F10 | informe | todas las filas en CUMPLE o con excepción firmada | sin sustituciones silenciosas | — |

---

## 27. Checklist de aceptación

Estado actual de cada casilla: **todas sin marcar** (nada implementado). Cada una lista su evidencia verificable.

- [ ] Redis operativo (servicio en compose + PING + XADD/XREADGROUP real)
- [ ] Redis messaging (mensajes AG0↔AG1–4 con `correlation_id`; el ciclo falla si Redis se detiene)
- [ ] AG0 implementado (LangGraph, decide parada)
- [ ] AG1 implementado (W con Σ=1, log inspeccionable)
- [ ] AG2 implementado (código validado en sandbox)
- [ ] AG3 implementado (Mermaid derivado del AST, válido)
- [ ] AG4 implementado (texto + TTS)
- [ ] PSO implementado (ecuaciones literales, RNG sembrado)
- [ ] p_best implementado
- [ ] g_best implementado
- [ ] discretización implementada (φ aprobado + pruebas)
- [ ] fitness implementado (4 términos, α+β+γ+δ=1)
- [ ] convergencia ≤15 (`k_stop≤15`, `stop_reason` registrado)
- [ ] epsilon=0.001 (parametrizado y probado)
- [ ] audio real (archivo mp3/wav generado por proveedor + hash + log)
- [ ] paquete con 4 modalidades (`NOT NULL` y prueba E2E)
- [ ] 100 perfiles (25/25/25/25 y 20×5 verificados por conteo)
- [ ] gold standard (artefacto versionado antes de calcular F1)
- [ ] F1 real (Precision/Recall/F1 desde matriz sobre 100 casos)
- [ ] L_resp medible (p50/p90/p95/p99 por escenario)
- [ ] throughput medible (req/s con error <1%)
- [ ] JMeter y Locust con los escenarios 1/10/25/50/100
- [ ] SUS (≥10 respuestas, puntaje calculado)
- [ ] trazabilidad (`profile_id→cycle→iteración→partícula→candidato→agente→fitness→paquete` consultable)
- [ ] modelo de datos migrado
- [ ] tests (unit, integración, E2E, performance, reproducibilidad)
- [ ] benchmark ejecutado y reportado sin maquillaje
- [ ] reproducibilidad (mismo seed+config+versión ⇒ mismo g_best; manifiesto completo)
- [ ] ADR del PoC aceptado y contradicciones documentadas

---

### BLOCKERS

Cosas que **realmente impiden** comenzar la implementación del núcleo (no las tareas 🟢 de abajo):

1. **DEC-01** — sin decidir el modelo de agentes y su ADR (contradice CONCEPT-0001/RFC-0006/ADR-0011) no debe escribirse AG0–AG4.
2. **DEC-02** — sin operador de discretización aprobado no se puede cerrar el PSO (RF08 bloquea RF04).
3. **DEC-03** — sin gold standard y semántica de etiqueta (compatible con RF05 y 4×4) F1_adapt es incalculable (RF07 bloquea RNF03).
4. **DEC-04** — sin definición de los 4 términos de 𝓕 y sus pesos, 𝓕 no es implementable.
5. **DEC-09** — sin decidir el modo de realización de candidatos (biblioteca vs en línea) no se puede diseñar el endpoint ni cumplir `L_resp`.
6. **DEC-14** — el head de Alembic (`928a10b002db`) y todo el stack CMG **no están versionados**; crear migraciones nuevas sobre eso es inseguro.

### CAN START WITHOUT HUMAN DECISION

Tareas que no fijan ninguna decisión metodológica y pueden empezar cuando se autorice escribir código:

- T0-03 esquema JSON del perfil (solo los 3 campos de RF01 son obligatorios; los demás como opcionales versionados).
- T4-01 motor PSO con las ecuaciones **literales** de la asesoría y RNG sembrado (el decodificador φ es un parámetro inyectable; no se aprueba aquí).
- T7-01 funciones puras de Precision/Recall/F1 desde matriz de confusión.
- T7-04 cálculo SUS (fórmula estándar de Brooke).
- T6-02 verificador de marginales (25/25/25/25 y 20×5).
- T1-02 esqueleto de Locust/JMeter (escenarios 1/10/25/50/100 fijados por la asesoría).
- T3-01 modelo de `Envelope` y catálogo de mensajes.
- T1-01 servicio Redis y cliente (Redis es exigido por la asesoría; DEC-05 solo confirma el modo de despliegue).
- T7-05 medición de CPU/RAM (sin definición metodológica pendiente).

### REQUIRES HUMAN DECISION

DEC-01, DEC-02, DEC-03, DEC-04, DEC-06, DEC-07, DEC-08, DEC-09, DEC-10, DEC-11, DEC-12, DEC-13, DEC-14, DEC-15, DEC-16, DEC-17 (detalle en §25). **Antes de tocar código:** DEC-01, DEC-02, DEC-03, DEC-04, DEC-09, DEC-14 (bloqueantes); el resto antes de sus fases respectivas.

### FIRST IMPLEMENTATION SLICE

**Slice vertical "esqueleto caminante" — un perfil, un concepto, de punta a punta, con los cinco agentes reales sobre Redis real.** Se ejecuta una vez cerrados DEC-01, DEC-02, DEC-04 (versión de trabajo), DEC-05, DEC-09 y DEC-14.

Alcance del slice:

1. Un `profile-v0` sintético de la celda (Visual-Dominante × Bucles) → **AG1** produce `W` con Σ=1.
2. **AG0** (grafo LangGraph) siembra N partículas con RNG sembrado y despacha `CANDIDATE_REQUEST` por **Redis Streams** a AG2/AG4 en paralelo; AG3 deriva el diagrama del código.
3. Biblioteca M1 **mínima pero real** para un concepto ("Bucle for"): 3 variantes de código validadas en sandbox, 3 diagramas derivados del AST, 3 textos, **y audio real por TTS** (proveedor decidido en DEC-06; no se acepta placeholder).
4. `𝓕` con los 4 términos según §8 y φ según DEC-02; PSO de ≤15 iteraciones con parada por ε/`k_max`.
5. Paquete final con las **4 modalidades** y `package_id`.
6. Persistencia de `CicloAdaptacion`, `IteracionPSO`, `ParticulaPSO`, `CandidatoModal`, `PaqueteMultimodal`, `MensajeAgente` y `MetricaCiclo` en Postgres.
7. Un `POST /api/adaptation` que devuelve el paquete y un script que mide L_resp de 20 repeticiones (sin afirmar cumplimiento).

**Criterios de aceptación del slice:** Redis real (el ciclo falla si se detiene); timestamps solapados de AG2/AG4 (RF03); `k_stop≤15` con `stop_reason`; consulta que reconstruye la cadena `profile→cycle→iteración→partícula→candidato→paquete`; mismo `seed`+`library_version` reproduce el mismo `g_best`; archivo de audio real con hash. **Fuera del slice** (se conservan como fases posteriores, no eliminadas): gold standard/F1, 100 perfiles, JMeter/Locust completos, SUS.

---

## Anexo A — Correcciones propuestas al Master Spec (no aplicadas; el spec no se modificó)

1. §20/§23: Corrida 2 usa **evidencia sintética** (no "datos reales"); los Concepts son reales.
2. §20: existe herramienta propia de medición de latencia/throughput (`benchmark_capacidad_http.py`, untracked); RNF01/RNF04 no están "sin herramienta", están "sin JMeter/Locust y sin endpoint".
3. §21: el sandbox **sí fue verificado** (tracked; requiere CLI `docker`, no disponible localmente; política AST y límites confirmados).
4. §17: "Docker CUMPLE" y "Python 3.12 CUMPLE" son ciertos solo para los archivos de despliegue; el entorno local difiere.
5. §1: el método "solo `git ls-files`" omite el stack CMG completo (untracked) que el propio spec cita.
6. Añadir a §25: tensión RF05↔§12 (4 siempre vs inclusión/exclusión), definición de `CR`, tautología de `T_conv≤15`, plateaus de 𝓕, tamaño del enjambre.

## Anexo B — Verificaciones realizadas en esta fase (solo lectura)

Lecturas de código y de documentos; `git status/rev-parse/ls-files/log`; `alembic heads` (no abre conexión a BD ni modifica nada); `SELECT count(*)` y `SELECT title …` sobre `concepts`, `learning_objectives`, `experiment_cmg_results` vía `podman exec … psql`; `command -v`, `nproc`, `free`. **No** se ejecutaron migraciones, instalaciones, commits, ni pruebas.
