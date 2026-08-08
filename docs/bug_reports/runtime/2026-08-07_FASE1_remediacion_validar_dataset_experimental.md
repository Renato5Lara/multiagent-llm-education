# Fase 1 — Remediación controlada: Validar y aislamiento del dataset experimental

## Metadata

- **Fecha:** 2026-08-07
- **Rama:** `investigacion/sesion5-rendimiento`
- **Protocolo:** investigación de causa raíz (3 pasadas, artefactos privados
  del tesista) → **remediación controlada** (este documento). Alcance
  autorizado explícitamente: Objetivos A-G de la Fase 1. Multimodalidad,
  nuevos agentes, ConsensusEngine y pesos de confianza quedan **fuera de
  alcance** por instrucción directa.
- **RFC/ADR implementado:** RFC-0010 §1 (Grieta A — el Boundary autora el
  fact, no `Capacidad.EVALUAR`), mismo patrón ya aceptado en
  `4b8c577` (Tutorizar/Diagnosticar). Ningún RFC/ADR nuevo ni modificado.
- **Principios preservados:** P6 (la explicación se recorre), P12
  (`enrutar` función pura de estado+política), P13 (regla/LLM comparten
  contrato), RFC-0004 §4 (la secuencia emerge), INV-12 (dos estados
  terminales exactos).

---

## 1. Causa raíz

`runtime/domain/validar/productor.py::evidencia_de_validacion` filtraba
evidencia por `f.autor is Capacidad.EVALUAR`. Desde RFC-0010 (Grieta A)
la evidencia real la autora el Boundary (`autor="boundary"`) —
`Capacidad.EVALUAR` no está wireada a ningún nodo del grafo
(`runtime/engine/graph/walkthrough.py::_construir`); sus únicos dos
importadores en todo el repositorio, antes de este fix, eran
`tests/runtime/walkthrough/test_P13_evaluar_reglas_vs_llm.py` y
`test_M3_PR5_evaluar_openai_real.py`. El mismo patrón ya se corrigió en
Tutorizar (`4b8c577`, 2026-07-13) — Validar nunca recibió el mismo
arreglo (su último commit tocado, `e374a8a`, es del 2026-07-11).
Confirmado contra Postgres real antes del fix: **0 operaciones
`validar_decision` y 0 claims `Capacidad.VALIDAR` en 19,412 transiciones
reales.**

**Estado: CORREGIDO.**

## 2. Cambio aplicado (Objetivo A)

- `runtime/domain/validar/productor.py` — `evidencia_de_validacion`
  ahora dispara por FORMA del contenido (`competencia` +
  `items_incorrectos`), no por autor. Mismo patrón exacto que
  Tutorizar/Diagnosticar. `producir_llm` (`productor_llm.py`) importa
  esta misma función — el fix la cubre automáticamente, sin tocar ese
  archivo.
- `runtime/engine/graph/walkthrough.py` — `_decision_lista_para_validar`
  ya importaba `evidencia_de_validacion` desde `productor.py` (no
  duplicaba el filtro) — se corrigió únicamente el docstring, que
  mencionaba "fact posterior de Evaluar" de forma desactualizada.

No se tocó el algoritmo de confianza, los pesos, `ConsensusEngine` ni las
condiciones de competencia de decisión — instrucción explícita respetada.

## 3. Archivos modificados

```
backend/runtime/domain/validar/productor.py           (fix, 2 bloques)
backend/runtime/engine/graph/walkthrough.py            (docstring)
backend/tests/runtime/walkthrough/test_FIX_validar_evidencia_boundary.py  (nuevo)
backend/scripts/clasificar_sesiones_experimentales.py  (nuevo, Objetivo D)
backend/scripts/recalibracion_dataset_limpio.py        (nuevo, Objetivo E)
docs/bug_reports/runtime/2026-08-07_FASE1_remediacion_validar_dataset_experimental.md (este documento)
```

Ningún archivo de producción fuera de estos dos fue tocado. Ningún dato
de Postgres fue modificado, borrado ni migrado.

## 4. Tests agregados (Objetivo F)

`test_FIX_validar_evidencia_boundary.py` — 5 tests puros (sin Postgres):

1. `test_evidencia_del_boundary_dispara_validar_regla` — evidencia
   `autor=BOUNDARY` ahora produce un veredicto (antes: `()`).
2. `test_evidencia_del_boundary_dispara_validar_llm` — mismo resultado
   vía `producir_llm`.
3. `test_enrutar_manda_a_validar_con_evidencia_del_boundary` — paridad
   guardia/productor (PR-2): `enrutar` coincide exactamente.
4. `test_evidencia_incompleta_del_boundary_no_autodispara` — evidencia
   parcial (solo "antes", sin "después") sigue sin disparar.
5. `test_validar_decision_actualiza_confianza_de_la_propuesta_origen`
   (Objetivo B) — cadena completa: `producir()` → `validar_decision`
   (reducer real) → `calcular_confianza_efectiva` sube para la PROPUESTA
   que originó la decisión, con una política de prueba de pesos no-cero
   (mismo patrón que `_POLITICA_PRUEBA` en
   `test_A1_A7_confianza_efectiva.py`) — `POLITICAS` de producción no se
   tocó.

Ningún test existente fue eliminado ni modificado en su aserción — todos
los tests preexistentes que construían evidencia con
`autor=Capacidad.EVALUAR` (`test_P13_validar_reglas_vs_llm.py`,
`test_INV_12_reducer_validacion.py`, `test_A1_A7_confianza_efectiva.py`,
`test_R3_reconstruccion_learning_state.py`,
`test_M3_PR7_validar_openai_real.py`) siguen pasando sin cambios: el
filtro por forma es un superconjunto del filtro por autor, no un
reemplazo excluyente.

**Estado: CORREGIDO Y VERIFICADO.**

## 5. Verificación dinámica (Objetivo G)

| Verificación | Resultado |
|---|---|
| `test_FIX_validar_evidencia_boundary.py` | 5/5 passed |
| Suite completa `tests/runtime/` (incluye tests reales contra OpenAI y Postgres) | **435/435 passed**, 348s |
| `pytest --collect-only` (backend completo) | 1929 tests, 3 errores de colección — los 3 preexistentes, ninguno introducido por este cambio (ver §7) |
| `runtime.runtime_sessions` antes vs. después de correr toda la suite | 966 → 966 (sin filas nuevas) |

La verificación de "0 sesiones huérfanas nuevas" confirma empíricamente
que el mecanismo de aislamiento de esquema de las suites `tests/runtime/`
(fixtures `esquema` con nombre `f"runtime_*_{os.getpid()}"` + `DROP
SCHEMA ... CASCADE` en teardown) funciona hoy, no solo en teoría.

**Estado: VERIFICADO.**

## 6. Estado de Validar tras el fix

Verificado mediante prueba dinámica (reconstrucción real + parche en
memoria, informe previo a este documento): sobre 59 sesiones reales con
al menos una competencia evaluada dos veces, el fix pasa de **0/59** a
**24/59** sesiones donde Validar produce veredicto. El resto no dispara
porque la competencia de la decisión pendiente específica no coincide
con la que se re-evaluó dentro de su ventana causal — comportamiento
correcto del contrato, no un defecto adicional.

**Importante — matiz encontrado al recalcular (Objetivo E, ver §8):** el
fix solo afecta ejecuciones **futuras** del walkthrough. La
reconstrucción de historia (`reconstruir`, ADR-0007) nunca reejecuta
productores — solo repite los `TransitionIntent` ya persistidos. Como
Validar nunca disparó en el pasado, no hay ningún `validar_decision`
histórico que "aparezca" al reconstruir con el código corregido. El
efecto del fix solo será observable en sesiones que se ejecuten **de
aquí en adelante**.

## 7. Estado del dataset experimental (Objetivos C y D)

### Objetivo C — investigación de `runtime_bridge.py`, sin modificarlo

Se auditaron **todos** los callers de `app/services/runtime_bridge.py`
(`registrar_evidencia_evaluacion`, `consultar_decision_vigente`,
`avance_por_objetivo`, `_sesion_del_curso`):

- **Producción real:** `app/api/routes/students.py`,
  `app/services/{student_service,knowledge_test_service,
  pedagogy_runtime_bridge,engagement_service,evaluation_service,
  module_orchestration_service}.py`, `evidence_service.py` — todos
  reciben `student_id` desde un usuario ya autenticado en la capa HTTP.
- **Tests de `runtime_bridge` en sí** (`tests/test_runtime_bridge.py` y
  hermanos en `tests/test_*.py`): usan `tests/conftest.py`, que apunta a
  **SQLite en memoria** — cero contacto con Postgres real, cero riesgo.
- **Suites `tests/runtime/*`** (50+ usos de `AlmacenTransiciones`):
  auditadas por muestreo dirigido a los patrones de mayor volumen —
  todas usan fixtures `esquema` con nombre único por proceso
  (`f"runtime_wt_{os.getpid()}"` y variantes) con `DROP SCHEMA CASCADE`
  en teardown, o son explícitamente de **solo lectura** contra el
  esquema real (`test_ADR_0014_reconstruccion_historica_real.py`,
  documentado así en su propio docstring: *"Ninguna entidad real se
  muta"*).

**Hallazgo decisivo:** la causa raíz real de las sesiones huérfanas está
documentada por el propio proyecto en
`app/services/runtime_connection.py` (docstring de `almacenes()`):
*"bug real encontrado en la Épica 2: los tests de `/api/runtime/*`
'aislaban' un esquema temporal que nunca se usaba de verdad, y el
esquema real `runtime` acumulaba sesiones de prueba entre corridas"* —
las variables de entorno de aislamiento se leían a nivel de módulo
(demasiado pronto para que `monkeypatch.setenv(...)` surtiera efecto);
la corrección (lectura perezosa dentro de la función) **ya está en el
código actual**, desde que este archivo se creó en el refactor
`600ebbb`.

**Recomendación — no ejecutada, pendiente de tu confirmación:**
**no modificar `runtime_bridge.py` ni `_sesion_del_curso`.** No son la
causa: no validan `student_id` contra `users` porque esa no es su
responsabilidad (la autenticación ya ocurrió en la capa HTTP para
tráfico real) — el vector de fuga histórico estaba en el aislamiento de
tests, y ese vector ya se cerró en `runtime_connection.py`. Introducir
validación de identidad en `runtime_bridge.py` sería una responsabilidad
nueva que no le corresponde a esa capa (violaría la separación
Boundary/HTTP ya establecida) y no habría prevenido el bug real, que
ocurría enteramente del lado de configuración de tests.

**Estado: INVESTIGADO — SIN CAMBIO DE CÓDIGO (recomendado, no ejecutado sin tu confirmación).**

### Objetivo D — clasificación reproducible

`scripts/clasificar_sesiones_experimentales.py` (100% lectura, sin
`DELETE`/`UPDATE`/`TRUNCATE`) clasifica las 966 filas de
`runtime.runtime_sessions`:

| Categoría | Sesiones | Estudiantes distintos |
|---|---:|---:|
| `CLEAN_REAL` (usuario real + inscripción real) | 73 | 38 |
| `E2E_SEED` (usuario real, sin inscripción o tráfico E2E) | 92 | 3 |
| `ORPHAN` (sin fila en `users`) | 801 | 801 |

Ningún registro fue borrado ni movido — la clasificación es una
consulta, reproducible en cualquier momento.

**Estado: CORREGIDO Y VERIFICADO (clasificación); limpieza física NO
ejecutada — fuera de alcance de esta fase por instrucción explícita.**

## 8. Impacto sobre H10 / Iteración 6.4 (Objetivo E)

`scripts/recalibracion_dataset_limpio.py` recalculó refuerzos/
refutaciones/edad_lógica separando por categoría, sin sobrescribir
`RESEARCH_ITERATIONS.md`:

| Universo | Claims evaluados | refuerzos/refutaciones/edad_lógica |
|---|---:|---|
| Todas (igual que la Iteración 6.4 original) | 6638 | 0 en el 100%, igual que el original |
| Solo `CLEAN_REAL` | 669 | 0 en el 100% |
| `CLEAN_REAL` + `E2E_SEED` | 864 | 0 en el 100% |

**Resultado esperado y confirmado, no una sorpresa:** el resultado es
idéntico entre categorías porque, como se explica en §6, la
reconstrucción histórica nunca reejecuta productores — el fix de Validar
no puede alterar retroactivamente transiciones ya persistidas. La
cifra "902 sesiones reales" de RESEARCH_ITERATIONS.md **se mantiene
como registro histórico exacto de lo que se ejecutó**; el aporte de
este documento es la clasificación (§7) que permite, de aquí en
adelante, filtrar por `CLEAN_REAL` antes de calcular cualquier
estadística nueva.

**Estado: VERIFICADO — sin cambios a resultados históricos, como se pidió explícitamente.**

## 9. Problemas restantes / no resueltos

- **Origen exacto de cada UUID huérfano individual:** se identificó el
  mecanismo (Épica 2, ya corregido) pero no se atribuyó cada una de las
  801 filas a una ejecución de test específica — requeriría instrumentar
  una corrida activa de la suite completa observando escrituras en vivo,
  fuera del alcance de "solo lectura" de esta fase.
- **Validación con datos ecológicos reales del fix de Validar:** el fix
  está corregido y probado dinámicamente contra datos existentes
  (informe previo), pero su efecto en producción solo será observable
  cuando el flujo real de un estudiante vuelva a evaluar la misma
  competencia dos veces — no se generó tráfico nuevo en esta fase.

## 10. Fuera de alcance (por instrucción explícita, no evaluado)

Multimodalidad, nuevos agentes, `ConsensusEngine`, pesos de confianza,
condiciones de competencia de decisión, limpieza física de sesiones
huérfanas, cualquier cambio a `runtime_bridge.py`.

## 11. Riesgos

- Ninguno introducido por el fix de Validar (superconjunto backward-
  compatible del filtro anterior, verificado con la suite completa).
- El dataset huérfano sigue existiendo físicamente — cualquier consulta
  futura sobre `runtime_sessions` que no use la clasificación de §7
  seguirá mezclando datos reales con datos de test, igual que antes de
  esta fase.

## 12. Recomendaciones para la siguiente fase

1. Confirmar (o rechazar) la recomendación de §7: no tocar
   `runtime_bridge.py`.
2. Decidir el destino final de las 801 filas `ORPHAN` (aislar
   permanentemente vs. archivar vs. dejar como están, ahora que están
   clasificadas y no crecen).
3. Generar tráfico real que vuelva a evaluar una misma competencia
   dos veces, para observar el primer `validar_decision` real de
   producción — candidato natural para una futura Iteración H10 (¿6.5?
   o el diseño de H11).
4. Recién entonces: multimodalidad, siguiente fase separada.
