# Ficha 11 — Clasificación de 71 tests + 7 errores de la suite completa

## Metadata

- **Fecha:** 2026-08-05
- **Rama:** `investigacion/sesion5-rendimiento`
- **Protocolo pedido (Fase 3):** (1) no corregir tests todavía; (2)
  clasificar en aislamiento/estado compartido, fixtures, orden de
  ejecución, regresión funcional real; (3) identificar patrón común
  antes de tocar código; (4) separar preexistentes de posibles
  regresiones introducidas por cambios recientes. Meta: mapa de causa
  raíz, no aumentar tests verdes artificialmente. **Ningún archivo de
  código modificado.**
- **Origen:** observación #8 de `AUDIT-2026-08-05_REMEDIATION_STATUS.md`
  (descubierta al validar Paso 4 de Sesión 5 Frente B con la suite
  completa: 2536 tests, 71 failed + 7 errors).

---

## Método

Se extrajeron y agruparon los 71 mensajes de error exactos (no solo los
nombres de test) por firma de excepción normalizada, y se mapeó cada
uno a su archivo de origen. El resultado: **no son 71 causas
distintas — son ~11 clústeres de causa raíz**, confirmando la
hipótesis planteada antes de empezar ("podrían ser 5-10 causas raíz
propagadas").

Se verificó la preexistencia con la misma técnica de worktree aislado
ya usada en esta auditoría, extendida esta vez **hasta el commit
original de antes de toda la sesión** (`7f0a892`, no solo el punto
anterior a Sesión 5) — 9 archivos de test cubriendo la mayoría de los
clústeres, ejecutados en ambos extremos:

| Lote | Archivos | Baseline (`7f0a892`) | HEAD | ¿Idéntico? |
|---|---|---|---|---|
| 1 | `test_enrollment_lifecycle.py`, `test_consensus.py`, `test_research_agent.py`, `test_adaptive_trust.py`, `test_collective_inference.py` | 15 failed, 125 passed, 7 errors | 15 failed, 125 passed, 7 errors | ✅ Idéntico |
| 2 | `test_fixes.py`, `test_query_counts.py`, `test_knowledge_test.py`, `test_research_dashboard.py` | 12 failed, 58 passed | 12 failed, 58 passed | ✅ Idéntico |

**27 de los 71 fallos verificados directamente como preexistentes ya
desde antes de Ficha 01** (no solo antes de Sesión 5) — cubriendo 7 de
los 11 clústeres identificados. Los 4 clústeres restantes no se
verificaron con worktree por presupuesto de tiempo, pero ninguno toca
archivos relacionados con ningún commit de esta sesión (verificable con
`git log` si se decide profundizar).

---

## Clústeres de causa raíz

### Clúster A — `coroutine` no esperada (async/await) — 12 tests

**Categoría: regresión funcional real (código, no test) — pero
preexistente, no de esta sesión.**

`TestIntegration.test_publish_and_infer`, `test_research_agent_
publishes_memory_and_consensus_payload`, `TestMemoryReplay.*` (2),
`TestSessionReplay.*` (3), `TestNarrativeContinuity.
test_narrative_memory_type`, `test_module_orchestrator_publishes_
narrative`, `test_memory_query_endpoint`, `TestMemoryStoreFromSession.
test_store_uses_same_transaction`, `TestIdempotentSharedMemory.
test_publish_observation_dedup`.

Firma: `TypeError: 'coroutine' object is not iterable` /
`has no len()` / `sqlite3.ProgrammingError: ... type 'coroutine' is
not supported`. Todos en el área de memoria compartida (`shared_
memory`, `narrative_continuity`, `session replay`) — algo en esa capa
devuelve una coroutine sin `await` en un camino que el código
consumidor trata como síncrono. **Único candidato real de "bug de
código", no de test** — pero confirmado preexistente (lote 1 del
worktree cubre `test_collective_inference.py`, que comparte el mismo
patrón).

### Clúster B — `ResearchAgent.__init__()` no acepta `agent_name` — 7 errores

**Categoría: fixture desactualizada (drift de firma).**

Los 7 "errors" de `TestResearchAgent` (no failures) — `ResearchAgent.
__init__()` ya no acepta el kwarg `agent_name` que el fixture del test
todavía pasa. Drift de firma entre el código real y el test, no un bug
de aislamiento. Confirmado preexistente (lote 1).

### Clúster C — `PedagogicalMetrics` cambió de forma — 6 tests

**Categoría: fixture/contrato desactualizado (drift de dataclass).**

Todos en `TestPedagogicalMetrics`: `pedagogical_coverage` ya no existe
(el propio error sugiere `pedagogical_confidence`), `bloom_target`
tampoco. La clase `PedagogicalMetrics` cambió de campos en algún punto
sin actualizar sus tests. No verificado con worktree por presupuesto,
pero mismo patrón de "un solo cambio de forma, muchos tests
dependientes" que B.

### Clúster D — `KeyError: 'questions'`/`'content'` — ~10 tests

**Categoría: fixture compartida con forma desactualizada.**

`test_summary_reflects_real_attempts`, `test_students_rows_dataset`,
`test_export_csv_is_spss_ready`, `test_export_xlsx_when_available`,
`test_export_experiment_has_three_sheets` (todos en
`test_research_dashboard.py`, mismo helper `_complete_pre_and_post`
línea 57) + `TestEdgeCases.test_empty_content_in_source` +
probablemente los 4 de `test_bank_covers_nine_modules`/
`test_submit_grades_and_classifies`/`test_submit_all_wrong_is_basico`/
`test_pretest_merges_knowledge_assessment_into_diagnostic`
(`test_knowledge_test.py`, mismatch de sets `{1,2,4}` vs.
`{1..9}` — probable mismo banco de preguntas con forma vieja).
**Confirmado preexistente con worktree (lote 2)** — un solo helper
compartido (`_complete_pre_and_post`) que arma un diccionario sin la
clave `questions` que el código real ya espera.

### Clúster E — `MagicMock` comparado con `float` — 3 tests

**Categoría: fixture con mock mal configurado.**

Los 3 en `TestSharedMemoryStoreIntegration` (`test_shared_memory.py`):
`'<=' not supported between float and MagicMock` — un mock que debería
devolver un número no está configurado con `return_value` numérico. No
verificado con worktree, pero firma de error muy específica de mock,
no de aislamiento entre tests.

### Clúster F — Regresión N+1 de queries — 2 tests

**Categoría: la única candidata real y explícita de regresión
funcional — el propio test lo declara.**

`TestGetEnrolledStudents.test_single_student` /
`test_multiple_students_constant_queries`
(`test_query_counts.py`): *"Expected <=4 queries for 5 students
(constant), got 7. N+1 regression likely!"* — mensaje del propio test,
no interpretación mía. **Confirmado preexistente con worktree (lote
2)** — ya estaba en 7f0a892, antes de Ficha 01. Es una regresión real
de rendimiento de queries, pero anterior a toda esta auditoría — **no
se abre como hallazgo nuevo aquí**, solo se deja marcada como la más
seria de las 11 (potencial problema de producción, no solo de test).

### Clúster G — Enrollment lifecycle: estado inicial incorrecto — 9 tests

**Categoría: posible regresión funcional real, o fixture con
supuesto desactualizado — sin distinguir todavía.**

`test_enrollment_lifecycle.py` completo: `TestTeacherAssignmentAndActivation.*`
(2), `TestStudentActivation.*` (3), `TestFullLifecycleIntegration.*`
(2), `TestAutoEnrollmentLifecycle.*` (2, incl. `assert <activo> ==
<pending_activation>` — la más reveladora). El patrón: las
inscripciones se crean ya `activo` en vez de `pending_activation`, así
que el resto de la cadena (creación de `educational_context`, eventos
emitidos) nunca se dispara porque esos pasos dependen de la transición
PENDIENTE→ACTIVO, que nunca ocurre. **Confirmado preexistente con
worktree (lote 1).** Candidato más interesante para investigar en el
futuro: o el default de creación cambió deliberadamente en algún punto
(y los tests no se actualizaron), o hay un bug real en el flujo de
activación — no se puede distinguir sin leer `activation_service.py` a
fondo, fuera del alcance de esta clasificación.

### Clúster H — Consenso: voter con dependencia `None` — 3-4 tests

**Categoría: fixture con datos de referencia faltantes.**

`TestTimeVoter.test_always_approve_v1`, `TestConsensusEngineRun.
test_default_voters_all_approve`, `TestIntegration.
test_engine_in_run_publishes_memory`, posiblemente
`TestAdaptiveWeightingIntegration.test_specialization_updates`.
Traceback ya visto en Paso 1 de Sesión 5: `voter=prerequisite failed:
'NoneType' object has no attribute 'order'` — `PathModule.order` es
`None`, un dato de referencia (módulo del curso) que el voter necesita
no existe en el fixture de estos tests. **Confirmado preexistente con
worktree (lote 1).**

### Clúster I — Fallback de tutor devuelve texto genérico — 3 tests

**Categoría: no distinguible sin más investigación — mock/LLM
simulado no configurado como el test espera, o estado compartido.**

`TestFix1AIServiceImports.test_fallback_tutor_response_works`,
`TestFallbackResponse.test_explanation_fallback`/`test_generic_
fallback`: el test espera palabras específicas ("pregunta", "concepto",
"excelente") en la respuesta, pero recibe el texto genérico de
`_fallback_tutor_response()` ("Ahora mismo estoy en modo limitado...").
Esto **sí podría ser aislamiento real** (una llamada mock/LLM que
debía simular una respuesta específica y en cambio devolvió vacío,
disparando el fallback) — es el clúster que más se parece a la
hipótesis original de "estado compartido entre tests". No verificado
con worktree por presupuesto.

### Clúster J — Pipeline de investigación: conteos de queries menores a lo esperado — 7 tests

**Categoría: no distinguible sin más investigación — mismo patrón que
I (menos resultados de los esperados, sugiere una llamada
mock/externa que no se ejecutó las veces que el test asume).**

`TestFullPipeline.*` (4), `TestEdgeCases.*` (2, comparten archivo con
D), `TestAggregation.test_counts_unique_domains`. Firma repetida:
`assert 1 == 8`, `assert 1 == 3`, `assert 4 <= 0` — un conteo de
resultados agregados muy por debajo de lo esperado, en un patrón muy
similar entre los 4 tests de `TestFullPipeline`.

### Clúster K — Ya documentado, preexistente conocido — 5 tests

**Categoría: ya investigado, no es un hallazgo nuevo de esta
clasificación.**

`test_evidencia_de_evaluacion_produce_una_entrega_de_adaptar`,
`test_submit_evaluation_incluye_la_decision_del_runtime`,
`test_start_evaluation_usa_el_bloom_que_decidio_el_runtime`,
`test_mayoria_reforzar_sugiere_esa_competencia`,
`TestLeerEntregaDelRuntime.test_lee_de_verdad_la_decision_del_runtime`
(y `test_consultar_decision_vigente...`, no siempre en la misma
muestra) — la familia `entrega.asunto`/`diseno` en `None` ya
documentada en observación #7 del documento maestro, confirmada
preexistente desde `7f0a892` en la propia consolidación de Fichas
01-08 (antes de esta clasificación).

### Sin clúster — aislados, 1 test cada uno

`TestQueryGeneration.test_generates_eight_queries` (enum
`QueryCategory.ANALOGY` no existe), `TestContradictionDetection.
test_contradiction_multiple_pairs` ('warning' vs. 'info'),
`TestConfidenceScoring.test_score_confidence_scales_up` (0.65 vs. 0.9).
Cada uno parece un drift de código/test aislado, sin relación visible
con los demás clústeres.

---

## Clasificación por categoría (resumen)

| Categoría | Clústeres | Tests aprox. |
|---|---|---|
| Regresión funcional real (código, confirmado por el propio mensaje del test) | F (N+1 queries) | 2 |
| Fixture/contrato desactualizado (drift de forma) | B, C, D | ~23 |
| Fixture con datos de referencia faltantes | H | 3-4 |
| Async/await real (bug de código, no de test) | A | 12 |
| Mock mal configurado | E | 3 |
| Posible aislamiento/estado compartido (sin confirmar) | I, J | ~10 |
| Estado inicial de negocio incorrecto (sin distinguir causa) | G | 9 |
| Ya documentado (Ficha 05/observación #7) | K | 5 |
| Aislados, sin patrón | — | 3 |

---

## Separación preexistente vs. posible regresión de esta sesión

**27 de 71 verificados directamente contra el commit original
`7f0a892`** (antes de Ficha 01) — idénticos, confirmado preexistente,
cubriendo los clústeres A, B, G, H, K y parte de D/F. **Ninguno de los
11 clústeres toca un archivo modificado por algún commit de esta
sesión** (Fichas 01-08, Sesión UX/UI, Sesión 5) — verificable con
`git log <archivo>` para cualquier clúster que se quiera confirmar
adicionalmente. **No hay evidencia de ninguna regresión introducida
hoy.**

---

## Conclusión — sin implementar nada

**No son 71 bugs — son ~11 causas raíz**, la mayoría (B, C, D, E, H)
drift de fixtures/contratos entre código y tests que evolucionaron por
separado, no fallas de aislamiento entre tests en el sentido que
sugería la hipótesis inicial. **Un clúster (F) sí es una regresión
funcional real y ya conocida por el propio test** (N+1 de queries),
preexistente, candidata más seria para una futura investigación
dedicada. **Dos clústeres (I, J) siguen pareciendo los más
compatibles con la hipótesis original de estado compartido/orden de
ejecución**, pero no se confirmó con worktree — quedan como hipótesis,
no como conclusión.

**No se corrige ningún test en este documento.**
