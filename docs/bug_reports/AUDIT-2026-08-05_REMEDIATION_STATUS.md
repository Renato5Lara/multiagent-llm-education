# Estado de remediación — Auditoría UPAO-MAS-EDU 2026-08-05

Consolida el estado de cada hallazgo de `Auditoria-UPAO-MAS-EDU-2026-08-05.docx`
tras la fase de remediación. Cada fila enlaza al commit real y al bug
report detallado cuando existe uno. Ninguna rama está pusheada — todas
viven localmente, apiladas en cadena (`fix/auth-cross-tab-storage-loop`
→ ... → `fix/dropdown-trigger-aschild-slot`, HEAD actual).

## Cierre de fase — resumen final

**Fase cerrada.** Las 7 fichas críticas/importantes con fix implementado
quedan resueltas y validadas en vivo (ver "Tabla de estado" abajo). No se
abre Ficha 05/09 en esta misma fase — quedan como líneas de trabajo
independientes, a decidir por separado.

**Fichas resueltas (7):** 01, 02, 03, 04, 06, 07, 08 — detalle completo
en la tabla de abajo.

**Fichas pendientes (no iniciadas):** 05, 09, más UX/rendimiento y las
Sesiones 3/4/5 del plan original — ver "Pendientes" al final.

**Riesgos aceptados** (trade-offs conscientes tomados durante esta
remediación, no defectos):
- **Ficha 01 (sessionStorage):** una pestaña nueva ya no hereda la
  sesión activa de otra pestaña — debe loguearse. Decisión de
  aislamiento deliberada (commit `66c3f00`), sin evidencia de que la
  herencia automática fuera un requerimiento real del producto.
- **Ficha 04:** la tabla `agent_decision_traces` (0 filas) y
  `app/schemas/decision_trace.py` (huérfano) no se eliminaron —
  mismo criterio que ADR-0011, que tampoco hizo `DROP TABLE` al retirar
  BaseAgent/SwarmOrchestrator (commit `ab3860b`, observaciones #2 y #3).
- **Fichas 07/08:** el fix se acotó estrictamente a los archivos
  pedidos, dejando conscientemente sin tocar `UserForm.tsx` (mismo gap
  de enum que Ficha 07, observación #1) y sin migrar
  `dropdown-menu.tsx` a `@radix-ui/react-dropdown-menu` real, ya
  instalado como dependencia pero no usado (observación #5) — ambos
  habrían ampliado el alcance más allá de lo pedido.

**Hallazgos preexistentes, no introducidos por esta remediación**
(distintos de "riesgos aceptados": son defectos reales, no decisiones
de diseño, pero fuera del alcance de esta auditoría):
- Propagación de logout entre pestañas del mismo usuario no funciona
  (observación #4).
- 5 tests de `runtime_bridge`/evaluación fallan contra OpenAI real,
  confirmado preexistente en el commit base `7f0a892` (observación #6).

**Hipótesis pendiente de investigación** (no confirmada, no convertida
en trabajo activo): los 5 tests fallidos y la Ficha 05 ("Cómo aprenderás
mejor" con fallback genérico) comparten el mismo síntoma exacto —
`entrega.asunto`/`diseno` en `None`. Podrían compartir causa raíz en
`app/services/runtime_bridge.py`, pero esto no está demostrado — ninguna
línea de código de `runtime_bridge.py` se tocó ni se investigó a fondo
en esta fase. Si se abre Ficha 05 como línea de trabajo propia, este es
el punto de partida a verificar primero, no una conclusión ya sentada.

## Tabla de estado

| Ficha | Severidad | Descripción | Commit(s) | Estado | Detalle |
|---|---|---|---|---|---|
| 01 | 🔴 Crítico | Sesión de Admin revertida a otro estudiante tras recarga | `a63597c`, `66c3f00`, `563d396`, `7e93a56` | ✅ RESUELTO | [bug report](auth/2026-08-05_AUDIT-FICHA01-02_cross_tab_storage_revalidation_loop.md) |
| 02 | 🔴 Crítico | Loop sin control de `GET /api/auth/me` entre pestañas | `a63597c`, `563d396` | ✅ RESUELTO | mismo bug report que Ficha 01 (causa raíz compartida) |
| 03 | 🔴 Crítico | Ejercicio Misión 1 rechaza secuencia correcta de 4 pasos | `11320fa`, `d661bcf` | ✅ RESUELTO | `position: null` + `whyWrong` en el item `p1`; copy del prompt actualizado |
| 04 | 🔴 Crítico | Endpoint `/api/trace/*` sin productor (código muerto) | `ab3860b` | ✅ RESUELTO | 3 archivos eliminados físicamente + `alembic/env.py` (referencia no listada en la auditoría, encontrada al verificar) |
| 06 | 🟠 Importante | Runtime Console: 403 para Admin/Investigador | `6eaf14b` | ✅ RESUELTO | dependencia renombrada + segundo gate (`_verificar_pertenencia`) también extendido — sin esto el bug habría persistido desplazado; `tests/test_runtime_boundary_http.py` actualizado (21 passed) |
| 07 | 🟠 Importante | Selector de rol vacío para "Investigador" | `dd2b166` | ✅ RESUELTO | `Roles.tsx` únicamente; `UserForm.tsx` tiene el mismo gap, fuera de alcance (observación registrada en el commit) |
| 08 | 🟠 Importante | `<button>` anidado en menú de acciones de `/admin/users` | `0b0c824` | ✅ RESUELTO | causa raíz real: `DropdownMenuTrigger` (componente compartido) nunca implementaba `asChild` — corregido con `Slot`, no parcheado en `Users.tsx` |

## Validación de regresión ejecutada en esta fase de consolidación

- `grep -rn "aget_current_estudiante_o_docente" backend/` → **0 resultados**
  (encontró y corrigió 9 referencias en `tests/test_runtime_boundary_http.py`
  que habrían roto `pytest` con `ImportError` antes de esta pasada).
- `grep -rn "DropdownMenuTrigger" frontend/src/` → confirma únicamente 2
  call sites reales (`UserDropdown.tsx` sin `asChild`, sin cambio de
  comportamiento; `Users.tsx` con `asChild`, ya validado en vivo).
- `pytest tests/test_runtime_boundary_http.py` → **21 passed** (Postgres real).
- `pytest` dirigido a todos los módulos tocados o relacionados
  (`test_users.py`, `test_auth.py`, `tests/runtime/`,
  `test_pedagogy_runtime_bridge.py`,
  `test_students_evaluation_runtime_wiring.py`,
  `test_runtime_trace_serialization.py`,
  `test_evidence_service_runtime_trace.py`, `test_runtime_bridge.py`,
  `test_runtime_boundary_http.py`,
  `tests/integration/test_it_03_api_runtime_boundary.py`,
  `tests/integration/test_it_04_runtime_postgresql_event_store.py`,
  `tests/integration/test_it_07_runtime_consenso.py`) → **514 passed, 5
  failed** de 519 (Postgres + OpenAI reales, 601s). Los 5 fallos
  (`test_mayoria_reforzar_sugiere_esa_competencia`,
  `test_submit_evaluation_incluye_la_decision_del_runtime`,
  `test_start_evaluation_usa_el_bloom_que_decidio_el_runtime`,
  `test_evidencia_de_evaluacion_produce_una_entrega_de_adaptar`,
  `test_consultar_decision_vigente_refleja_la_ultima_evidencia_registrada`)
  se investigaron y **son preexistentes, no una regresión de esta
  remediación**: (1) ninguno de los 10 commits de esta sesión toca esos
  archivos ni sus dependencias (`app/services/runtime_bridge.py`,
  verificado con `git log`); (2) reproducidos de forma idéntica —mismo
  patrón `asunto`/`diseno` en `None`— en un worktree aislado en el
  commit base `7f0a892` (HEAD antes de que esta sesión tocara cualquier
  archivo). Pendientes de investigación en una sesión propia, fuera del
  alcance de esta auditoría.
- `pytest tests/` (suite completa, sin filtrar) → 3 errores de colección
  preexistentes, **no relacionados a ningún commit de esta remediación**
  (verificado con `git log` sobre esos archivos): `selenium` no instalado
  (`test_it_08_frontend_backend.py`) y dos `ImportError` en
  `test_tavily_cache.py`/`test_tavily_client.py` (integración Tavily, sin
  relación con auth/runtime/admin).
- `npm run build` (frontend, `tsc -b && vite build`) → **build exitoso**,
  incluye `Roles-*.js` y `Users-*.js` sin errores.
- `rtk tsc` / `npx eslint` sobre cada archivo tocado → 0 errores en todas
  las fases.

## Decisión documental tomada en esta fase

Se evaluó crear `ADR-0012-auth-session-isolation-by-tab.md` para la
decisión de `sessionStorage` (Ficha 01) y se descartó: el número
colisionaba con un ADR real ya aceptado (`ADR-0012-politica-consenso-
experimental-v2.md`), y más importante, el namespace `docs/architecture/
ADR/` gobierna exclusivamente `backend/runtime/` (los 16 ADR existentes,
sin excepción, tratan kernel/deliberación/memoria/consenso del runtime
LangGraph). La decisión quedó documentada como sección "Resolución
final" dentro del bug report ya existente de Fichas 01/02 — el
artefacto correcto para cerrar un hallazgo de auditoría, no para definir
arquitectura nueva del runtime.

## Observaciones registradas durante la remediación (no corregidas, fuera de alcance)

Cada una vive documentada en el commit o bug report que la originó — se
listan aquí solo como índice:

1. **`UserForm.tsx`** tiene el mismo enum limitado que motivó la Ficha 07
   — "Investigador" solo aparece como opción si el usuario ya tiene ese
   rol, nunca seleccionable al crear/reasignar (commit `dd2b166`).
2. **`app/schemas/decision_trace.py`** quedó huérfano tras eliminar
   `traces.py` (Ficha 04) — candidato a un futuro retiro (commit `ab3860b`).
3. **Tabla `agent_decision_traces`** (0 filas) sigue en Postgres — mismo
   criterio que ADR-0011, que tampoco incluyó `DROP TABLE` (commit `ab3860b`).
4. **Propagación de logout entre pestañas del mismo usuario** (rama
   `!e.newValue` de `AuthProvider.tsx`) no funciona en la práctica —
   `logout()` nunca llama `localStorage.removeItem`. Preexistente,
   no introducido por esta remediación (bug report Fichas 01/02).
5. **`components/ui/dropdown-menu.tsx`** es una reimplementación propia
   del menú desplegable, mientras `@radix-ui/react-dropdown-menu` ya está
   instalado como dependencia y no se usa — encontrado al investigar la
   Ficha 08, no corregido (migrar a la librería real sería un cambio de
   mayor alcance que el pedido).
6. **5 tests preexistentes fallan contra OpenAI real**
   (`test_pedagogy_runtime_bridge.py`,
   `test_students_evaluation_runtime_wiring.py` ×2,
   `test_runtime_bridge.py` ×2) — `entrega.asunto`/`diseno` llegan en
   `None` donde se esperaba una decisión adaptativa. Confirmado
   preexistente (reproducido idéntico en el commit base `7f0a892`, antes
   de esta remediación) durante la regresión de esta fase de
   consolidación. No investigado a fondo — fuera del alcance de esta
   auditoría, pero registrado porque afecta la confiabilidad de la suite
   de tests del runtime_bridge (posible relación con Ficha 05 de la
   auditoría — "Cómo aprenderás mejor" mostrando fallback genérico
   cuando `entrega.diseno`/`asunto` son `None`, mismo síntoma).

## Pendientes (no iniciados en esta fase)

| Tema | Estado |
|---|---|
| Ficha 05 ("Cómo aprenderás mejor" muestra fallback genérico con perfil mixto, EstudianteC — causa ya diagnosticada por la auditoría como hipótesis: `entrega.diseno`/`asunto` en `None`, nunca confirmada con certeza total; fix nunca implementado) | Pendiente de fix — posible causa raíz compartida con la observación #6 de arriba |
| Ficha 09 (escala Likert de 5 puntos colapsada a binario + redundancia "Base sólida"/"Siguiente reto" con dominio 100%; la auditoría no llegó a re-verificarla en su 2ª pasada) | Pendiente de revisión |
| UX menores (§06 de la auditoría: indicador de "sistema ocupado", vía de escape en ejercicios) | Pendiente |
| Rendimiento (§11: latencia de personalización 6-10s, caché de Pyodide) | Pendiente |
| 🟠 Sesión 3/4 (UX/UI general, editor de código/Pyodide) del plan original | No iniciada |
| 🟡 Sesión 5 (código muerto adicional, deuda técnica, rendimiento) | No iniciada |
