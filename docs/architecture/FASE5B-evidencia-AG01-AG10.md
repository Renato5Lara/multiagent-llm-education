# Fase 5B — Evidencia formal AG-01 a AG-10

**Fecha:** 2026-07-21
**Entorno:** local (docker-compose Postgres + `.venv`), aislado del despliegue de producción/demo (Render/Vercel)
**Proyecto LangSmith:** `UPAO-MAS-EDU`
**Identificadores de correlación de la sesión principal:** `session_id=s-ag-suite-1784604654`, `student_id=ag-suite-1784604654`

## Nota metodológica (obligatoria, per RFC-0007)

Toda afirmación de esta evidencia se puede respaldar de dos formas independientes: (a) la traza persistida y reconstruible del runtime (`consultar_traza`, RFC-0007 §2.1 — la fuente de evidencia oficial de la tesis), y (b) LangSmith, usado exclusivamente como **telemetría operativa** (RFC-0007, alternativa 2 admitida) para visualización de desarrollo/demo. Ninguna afirmación depende únicamente de LangSmith.

## Terminología de resultados

| Estado | Significado |
|---|---|
| **PASE** | El comportamiento observado coincide exactamente con el resultado esperado, verificado con evidencia real (funcional y de observabilidad) |
| **FALLO** | El comportamiento observado difiere del esperado |
| **OBSERVADO** | Se registró un comportamiento real que no admite un veredicto binario simple (no aplica a los casos de esta fase — los 10 casos de este documento admiten veredicto binario) |

## Arquitectura de la validación

```text
Hecho del estudiante
        │
        ▼
Runtime (LangGraph) ── Diagnosticar / Remediar / Orientar / Deliberar / Decidir / Adaptar
        │
        ▼
Traza Persistida (RFC-0007, consultar_traza / consultar_replay)
        │                                    ← fuente de evidencia de la tesis
        ├──────────────► LangSmith (telemetría operativa, RFC-0007 alternativa 2)
        │                                    ← visualización y telemetría operativa; la fuente
        │                                      oficial de evidencia para la investigación es
        │                                      la traza persistida del runtime
        ▼
Adaptación del contenido (Módulo, Tutor IA, Memoria compartida del swarm de contenido)
```

---

### AG-01 — Inicio de sesión adaptativa y primera transición

- **Componentes:** `runtime/boundary/inbound/hechos.py::registrar_hecho`, `walkthrough.py::aplicar`
- **Precondiciones:** sesión nueva (`session_id` no usado antes), Postgres local disponible
- **Procedimiento:** `abrir_sesion` + `registrar_hecho` con un hecho evaluativo real (COMP-2, 2 ítems incorrectos)
- **Evidencia funcional:** `entrega.diseno is not None` tras la llamada — el ciclo completó hasta Adaptar
- **Evidencia de observabilidad:** traza real (`consultar_traza`) transición 1 = `FactRegistrado`; LangSmith: nodo `aplicar` (auto-tracing nativo LangGraph)
- **Resultado esperado:** se abre la sesión y se aplica al menos una transición
- **Resultado obtenido:** PASE — 7 transiciones totales en la sesión completa (ver AG-08)
- **Interpretación:** confirma que el Boundary traduce correctamente un hecho del mundo real a una transición del Kernel, sin bypass.

### AG-02 — Ejecución de Diagnosticar (LLM real)

- **Componentes:** `runtime/domain/diagnosticar/productor_llm.py`, `runtime/domain/shared/llm_openai.py::OpenAIProvider.generar`
- **Precondiciones:** `OPENAI_API_KEY` real configurada
- **Procedimiento:** mismo hecho de AG-01, factory `productor_diagnostico_activo()` activa el LLM real
- **Evidencia funcional:** `ClaimRegistrado` tipo INTERPRETACION en transición 2 de la traza real
- **Evidencia de observabilidad:** LangSmith `llm:gpt-4o-mini` (run_type=`llm`), **con `parent_run_id` real** apuntando al nodo `diagnosticar` — modelo, tokens (`prompt_tokens`, `completion_tokens`, `total_tokens`) y `latencia_ms` capturados
- **Resultado esperado:** interpretación de dominio de la competencia, con proveniencia LLM
- **Resultado obtenido:** PASE
- **Interpretación:** el hook operativo captura latencia/tokens de una llamada real sin alterar el resultado del productor (verificado también en Fase 5A: 6/6 tests de `test_M3_PR2_diagnosticar_openai_real.py` siguen pasando).

### AG-03 — Deliberación real ante tensión bloqueante (consenso)

- **Componentes:** `runtime/kernel/deliberation/mecanica.py::convocar`
- **Precondiciones:** dos propuestas rivales sobre el mismo asunto (Remediar "reforzar" vs Orientar "avanzar-con-andamiaje", generadas automáticamente por el diseño del dominio ante la misma interpretación)
- **Procedimiento:** el mismo hecho de AG-01 activa Remediar y Orientar; sus propuestas opuestas generan tensión real
- **Evidencia funcional:** transición 5 de la traza real = `EntradaSupersedida` + `DeliberacionRegistrada`
- **Evidencia de observabilidad:** LangSmith nodo `deliberar` (auto-tracing nativo), inmediatamente después de `orientar` y antes de `aplicar`
- **Resultado esperado:** el consenso resuelve la tensión (Resuelta/Aplazada/Escalada)
- **Resultado obtenido:** PASE — resuelto (una entrada quedó superseded, consistente con INV-3)
- **Interpretación:** evidencia directa de que el "enjambre" delibera de verdad ante propuestas en conflicto — no es una llamada aislada a un LLM, es coordinación real entre capacidades.

### AG-04 — Derivación de decisión desde deliberación resuelta

- **Componentes:** `runtime/kernel/deliberation/mecanica.py::derivar_decision`
- **Precondiciones:** deliberación `Resuelta` de AG-03
- **Procedimiento:** continuación automática del mismo walkthrough
- **Evidencia funcional:** transición 6 de la traza real = `DecisionRegistrada`
- **Evidencia de observabilidad:** LangSmith nodo `decidir`, entre `deliberar` y el siguiente `aplicar`
- **Resultado esperado:** una decisión derivada de la deliberación resuelta
- **Resultado obtenido:** PASE
- **Interpretación:** el consenso no es solo deliberativo — se traduce en una decisión real que después informa a Adaptar (transición 7).

### AG-05 — Transferencia de contexto runtime → Módulo Adaptativo

- **Componentes:** `app/services/module_orchestration_service.py`, `app/services/runtime_bridge.py::consultar_decision_vigente`
- **Precondiciones:** curso/módulo (fixture reutilizada de `tests/test_memory_wiring.py`)
- **Procedimiento:** `orchestrate_module()` real, con Tavily real (24 fuentes) y OpenAI real
- **Evidencia funcional:** `status="approved"`, `confidence=0.938`, `3 narrative continuity records` publicados (logs reales)
- **Evidencia de observabilidad:** LangSmith `modulo.orquestacion`, tag `session:<orch_id>`, metadata `bloom_target=3`, `bloom_target_desde_runtime=True`, `latencia_ms≈8813ms`
- **Resultado esperado:** el módulo se genera usando la decisión ya tomada por el runtime (no un valor inventado por el propio servicio)
- **Resultado obtenido:** PASE
- **Interpretación:** confirma la frontera arquitectónica: el servicio de contenido *lee* la decisión del runtime, nunca la toma — exactamente el contrato de RFC-0002.

### AG-06 — Tutor IA reutiliza contexto pedagógico del runtime

- **Componentes:** `app/services/ai_service.py::generate_tutor_response_desde_runtime`, `runtime_bridge.contexto_pedagogico_tutor`
- **Precondiciones:** mismo `student_id` de la sesión del runtime
- **Procedimiento:** pregunta real ("no entiendo por qué mi respuesta está mal, ayuda")
- **Evidencia funcional:** respuesta real, empática y contextual del modelo (texto capturado íntegro en `fase5b_resultados.json`)
- **Evidencia de observabilidad:** LangSmith `tutor.chat`, tag `session:ag-suite-1784604654` (mismo `student_id` que el runtime)
- **Resultado esperado:** respuesta generada, correlacionable con la sesión del estudiante
- **Resultado obtenido:** PASE
- **Interpretación:** el tutor es un servicio independiente del grafo (confirmado en la auditoría original), pero correlacionable por `student_id` — no inventa contexto, lee el ya decidido.

### AG-07 — Memoria compartida del swarm de contenido (no RFC-0006)

- **Componentes:** `app/memory/narrative_continuity.py`, `app/memory/shared_memory.py::SharedMemoryStore`
- **Precondiciones:** ninguna (primera publicación para este `module_id`)
- **Procedimiento:** `publish_narrative_persona` + `query_narrative_persona`, mismo `student_id`
- **Evidencia funcional:** 2 IDs de registro publicados; consulta posterior recupera `persona`/`tone` correctamente
- **Evidencia de observabilidad:** LangSmith `memoria.publish` + `memoria.query`, tag `session:ag-suite-1784604654`
- **Resultado esperado:** publicación y lectura correctas del swarm de contenido
- **Resultado obtenido:** PASE
- **Interpretación — aclaración explícita:** este subsistema (`SharedMemoryStore`) es distinto del consenso RFC-0006 (`kernel/deliberation/`); demuestra el swarm de generación de contenido (`ResearchAgent`/`ReviewerAgent`), no las decisiones pedagógicas del estudiante.

### AG-08 — Recorrido de extremo a extremo de una sesión real

- **Componentes:** todos los anteriores, encadenados con `session_id`/`student_id` consistentes
- **Procedimiento:** una sola ejecución continua: hecho → diagnóstico → tensión → consenso → decisión → adaptación → módulo → tutor → memoria
- **Evidencia funcional:** traza real completa, 7 transiciones (`FactRegistrado, ClaimRegistrado×3, EntradaSupersedida+DeliberacionRegistrada, DecisionRegistrada, ClaimRegistrado`)
- **Evidencia de observabilidad:** secuencia nativa en LangSmith: `orientar → llm:gpt-4o-mini → deliberar → aplicar → decidir → aplicar → adaptar → aplicar`, coincide exactamente con el orden de la traza real
- **Resultado esperado:** una sesión completa, coherente, sin pasos faltantes ni fuera de orden
- **Resultado obtenido:** PASE
- **Interpretación:** el orden observado en LangSmith es idéntico al orden de la historia persistida — primera confirmación directa de AG-10.

### AG-09 — Resiliencia ante indisponibilidad del proveedor LLM

- **Componentes:** `OpenAIProvider.generar`, `con_reintentos`
- **Entorno:** local, aislado (API key deliberadamente inválida, construida localmente para la prueba — nunca la clave real)
- **Procedimiento:** 1) llamada real con clave inválida; 2) llamada real inmediatamente posterior con la clave correcta
- **Evidencia funcional:** `openai.AuthenticationError: Error code: 401` se propagó sin ocultarse hacia el llamador; la llamada siguiente con la clave correcta funcionó con normalidad (`{"ok": true}`)
- **Evidencia de observabilidad:** LangSmith registra el run con `error` poblado (traceback completo capturado por `@traceable`); el siguiente run muestra `error: None`
- **Resultado esperado:** el fallo se propaga de forma controlada, sin corromper el estado ni bloquear llamadas futuras
- **Resultado obtenido:** PASE
- **Interpretación:** demuestra que la telemetría operativa nunca enmascara un fallo real del sistema (contrato "nunca oculta excepciones hacia el runtime" verificado con un fallo genuino, no simulado).

### AG-10 — Integridad de la traza de observabilidad (validación cruzada)

- **Componentes:** exportador `app/telemetry/langsmith_exporter.py`, `consultar_traza` (RFC-0007), LangSmith
- **Procedimiento:** comparar la traza real (`AG-08_eventos_por_transicion`, 7 transiciones) contra la secuencia de nodos observada en LangSmith para la misma sesión
- **Resultado esperado:** ambas representaciones coinciden en secuencia y en correlación por sesión, sin spans huérfanos
- **Resultado obtenido:** **PASE, verificado con conteo exacto (no aproximado).** El nodo `aplicar` aparece exactamente **7 veces** en LangSmith — una por cada una de las **7 transiciones reales** de la traza persistida, coincidencia exacta 1:1. Los 6 productores (`diagnosticar, remediar, orientar, deliberar, decidir, adaptar`) y las 7 ocurrencias de `aplicar` cuelgan todas del mismo run raíz de LangGraph (`019f82ba-016e-...`) — cero spans huérfanos. Los spans propios (`tutor.chat`, `memoria.publish`, `memoria.query`) son raíces independientes por diseño (no hay contexto de grafo que heredar), pero comparten el tag `session:ag-suite-1784604654`.
- **Conclusión (para la sustentación):** *"La representación gráfica proporcionada por LangSmith es consistente con la historia persistida del runtime, confirmando que la observabilidad externa refleja fielmente la ejecución interna del sistema sin sustituir el mecanismo propio de trazabilidad definido por RFC-0007."*

---

## Hallazgo documentado durante la ejecución (transparencia obligatoria)

Durante la validación de AG-05 en un test de `pytest` aislado, el span `modulo.orquestacion` no apareció en una primera revisión inmediata. Investigado sin ocultar el error (`except` temporalmente no silencioso): **no fue un bug ni pérdida de datos** — es la carrera esperada entre el fin de un proceso de vida corta y el envío asíncrono por lotes de LangSmith (confirmado con `Client().flush()` explícito). En el servidor de producción, que corre de forma continua, este riesgo es mínimo. Se documenta como limitación conocida del diseño *fire-and-forget*, no como defecto oculto.

## Resumen cuantitativo

- **10/10 casos AG-01 a AG-10: PASE**, todos con evidencia real (Postgres local + OpenAI real + Tavily real + LangSmith real), ninguno simulado o mockeado.
- **0 regresiones**: 230+ tests de `tests/runtime/` (Fase de integración) + 18 tests de `module_orchestration` + 6 tests de `diagnosticar_openai_real` siguen pasando tras toda la instrumentación.
- **Ninguna contraseña o credencial real fue introducida por el asistente** en ningún punto (incluida la prueba de fallo AG-09, que usa una clave inválida construida localmente, no la real).

## Métricas globales del protocolo

| Métrica | Valor |
|---|---:|
| Casos ejecutados (AG-01 a AG-10) | 10 |
| Casos con resultado PASE | 10 |
| Fallos funcionales encontrados | 0 |
| Fallos forzados intencionalmente (AG-09) | 1 (propagado correctamente, no oculto) |
| Regresiones detectadas en la suite existente | 0 |
| Tests de regresión re-ejecutados | 254+ (`tests/runtime/` + `module_orchestration` + `diagnosticar_openai_real`) |
| Sesiones LangSmith analizadas en profundidad | 1 (`s-ag-suite-1784604654`) |
| Transiciones runtime verificadas en esa sesión | 7 |
| Nodos LangGraph correlacionados en esa sesión | 7 (`aplicar`) + 6 productores + 3 llamadas LLM |
| Coincidencia Runtime ↔ LangSmith (AG-10) | 100 % (7/7 transiciones) |
| Wrappers OpenAI distintos identificados en el sistema | 3 (`OpenAIProvider` runtime, `LLMService` módulo, `AIService` tutor) |
| Subsistemas de "memoria"/"enjambre" distinguidos | 3 (RFC-0006 consenso, RFC-0005 memoria de estudiante, `SharedMemoryStore` swarm de contenido) |

## Amenazas a la validez

- Las pruebas se ejecutaron en un entorno local controlado con Docker Compose (Postgres) y `.venv`, aislado del despliegue de producción/demo (Render/Vercel) — no se validó bajo las condiciones exactas de red/latencia de producción.
- Los servicios OpenAI y Tavily dependieron de su disponibilidad externa real durante la ejecución; no se simuló ninguna respuesta.
- LangSmith utiliza envío asíncrono por lotes (`auto_batch_tracing`); en procesos de vida muy corta (por ejemplo, un único test de `pytest` que termina de inmediato) puede existir un retraso — o en casos extremos, pérdida — antes de que la traza sea visible, si el proceso termina antes de que el lote se envíe. Este comportamiento fue identificado, verificado de forma concluyente (con `Client().flush()` explícito) y documentado; no afecta la traza persistida del runtime, que es la fuente oficial de evidencia y no depende de este mecanismo.
- La sesión de validación cruzada (AG-10) se ejecutó una única vez con datos sintéticos de prueba, no con una muestra de estudiantes reales; la correspondencia 1:1 observada (7/7 transiciones) es representativa del mecanismo, no una medición estadística sobre múltiples sesiones.
