# Estado de remediación — Auditoría UPAO-MAS-EDU 2026-08-05

Consolida el estado de cada hallazgo de `Auditoria-UPAO-MAS-EDU-2026-08-05.docx`
tras la fase de remediación. Cada fila enlaza al commit real y al bug
report detallado cuando existe uno. Ninguna rama está pusheada — todas
viven localmente, apiladas en cadena (`fix/auth-cross-tab-storage-loop`
→ ... → `fix/dropdown-trigger-aschild-slot`, HEAD actual).

## Segunda ronda — líneas de trabajo pendientes de otras sesiones (Fichas 10-16)

Tras la "Cierre de la auditoría completa" original (abajo), se investigó
si otras líneas abiertas en el proyecto (no parte del `.docx` original)
tenían acciones pendientes: `TraceExplorer`, la suite completa de tests,
"Adaptar dormido" (hallazgo de HF-0/Exp-1), la semántica de `Aplazada`
(pregunta que Ficha 05 dejó explícitamente diferida), la clasificación
final de Ficha 09, y Épica C (deuda histórica del 2026-07-25). Cada una
se investigó con el mismo rigor observar→medir→verificar→clasificar
→decidir→implementar, sin implementar hasta tener diagnóstico completo.

| Ficha | Línea | Resultado |
|---|---|---|
| [Ficha 10](frontend/2026-08-05_AUDIT-FICHA10_trace_endpoint_legacy_consumption.md) | `/api/trace/*` eliminado, consumido por `useTrace()` | Contrato frontend obsoleto con fallback silencioso deliberado cuyo disparador (404) cambió de significado; 2 opciones de remediación candidatas, sin decidir |
| [Ficha 11](backend/2026-08-05_AUDIT-FICHA11_suite_completa_clasificacion.md) | 71 tests + 7 errores fallidos | ~11 clústeres de causa raíz clasificados; verificado contra worktree baseline (`7f0a892`) — todos preexistentes, cero regresiones de esta sesión |
| [Ficha 12](runtime/2026-08-05_AUDIT-FICHA12_adaptar_dormido_diagnostico.md) | "Adaptar dormido" (hallazgo HF-0/Exp-1) | `producir_llm` de Adaptar validado por ADR-0007 pero nunca conectado al Boundary — deuda experimental intencional, decisión de cierre ya registrada por el tesista, pendiente de Engineering Gate propio |
| [Ficha 13](runtime/2026-08-05_AUDIT-FICHA13_semantica_aplazada.md) | Semántica de `Aplazada` (pregunta diferida por Ficha 05) | Cierra la pregunta: `Aplazada` es estado válido y diseñado (RFC-0006 §4/CONCEPT-0002 §4), condicionado por `urgente`; los 3 call sites de VARK/pre-test con `urgente=False` quedan como candidato de decisión de producto, no defecto confirmado |
| [Ficha 14](backend/2026-08-05_AUDIT-FICHA14_clasificacion_likert_y_redundancia.md) | Clasificación final de Ficha 09 | Ninguno de los 2 hallazgos (Likert binarizado, redundancia 100%) es defecto funcional ni afecta a Adaptar/Runtime — metodológico y de producto/UX respectivamente |
| [Ficha 15](frontend/2026-08-05_AUDIT-FICHA15_epica_c_estado_vigente.md) | Épica C (Commit 5 pendiente desde 2026-07-25) | Confirmada vigente, sin drift, no superada por la migración a LangGraph Runtime (subsistemas sin punto de contacto) — Commit 5 ejecutado (recorrido E2E real de las 6 etapas de `ciclo3-input.ts`) y Épica C **CERRADA**, Commits 1-5/5 completos |
| [Ficha 16](auth/2026-08-05_AUDIT-FICHA16_admin_credentials_access_state.md) | Hallazgo colateral de Ficha 15: `admin@upao.edu.pe`/`Admin2026!` no coincide con el hash real | Diagnóstico completo: lockout, autenticación y otras cuentas (docente/estudiante) funcionan correctamente; solo el hash de admin cambió hoy (`updated_at` 2026-08-05 21:00:21 UTC), sin pasar por `/recover` (mock, descartado por código), ningún script del repo, ni `seed.py` (idempotente, hardcodea el valor documentado). **Cambio de credencial administrativa detectado fuera del flujo auditado; origen no determinado.** No se intentó adivinar la contraseña real, no se modificó ningún dato |

**Decisión operativa explícita, no técnica, pendiente del tesista sobre
Ficha 16:** ¿la contraseña real actual de `admin@upao.edu.pe` es la que
debe quedar como oficial (actualizar `seed.py`/`CLAUDE.md`/memoria), o
`Admin2026!` debe restaurarse como contraseña oficial (cambio
controlado, documentado, con verificación de login)? Ninguna opción se
ejecuta desde esta auditoría — no se toca `seed.py`, no se resetea
ninguna contraseña, no se modifica `CLAUDE.md` hasta que esa decisión
se tome explícitamente.

**Recomendación registrada, no implementada:** el que un cambio de
credencial de una cuenta ADMIN no genere ningún `audit_logs` es una
observación de gobierno de cambios privilegiados, no un bug confirmado
— depende de si el diseño del sistema pretende trazabilidad completa de
operaciones administrativas (password/rol/estado activo), garantía que
no está declarada en ningún RFC/ADR revisado. Candidata a mejora de
observabilidad futura, no a corrección inmediata.

Con esta ronda, **Iteración 6.3 de la metodología de investigación
queda como el único punto explícitamente diferido** — requiere
población experimental real, no cuentas sintéticas; no se abre hasta
que exista ese dato.

## Cierre de la auditoría completa (2026-08-05)

**La auditoría técnica queda completamente cerrada, sin ningún punto
abierto.** Todos los defectos confirmados (Fichas 01-08, Sesión UX/UI
H1/H2, Sesión 5 Frente A y B, incluido el rol "Investigador") fueron
implementados y validados contra el sistema real — nunca solo "compila"
o "los tests pasan". El rol "Investigador" se trató deliberadamente
como una decisión de arquitectura separada del proceso de remediación
técnica (ver "Rol Investigador — resuelto" más abajo) — nunca mezclado
con los hallazgos técnicos, pero sí resuelto
en la misma sesión tras obtener la decisión del tesista.

Cadena completa de líneas de trabajo, todas cerradas:

| Línea | Estado | Cierre |
|---|---|---|
| Fichas 01, 02, 03, 04, 06, 07, 08 | ✅ Resueltas y validadas en vivo | Ver "Tabla de estado" abajo |
| Ficha 05 | ✅ Diagnóstico forense cerrado — remediación diferida a decisión de arquitectura del consenso (no técnica) | [bug report](runtime/2026-08-05_FICHA05_entrega_diseno_none_investigacion.md) |
| Ficha 09 | ✅ Diagnóstico forense cerrado — remediación diferida a decisión de producto/metodología (no técnica) | [bug report](backend/2026-08-05_FICHA09_likert_binario_y_redundancia_100pct_investigacion.md) |
| Sesión UX/UI (Pasos 1-5) | ✅ Cerrada — H1/H2 implementados y validados E2E, H3 en backlog por decisión, H5/H6 cerrados sin código | [Paso 5](ux/2026-08-05_SESION_UXUI_PASO5_implementacion.md) |
| Sesión 5 — Frente A (Rendimiento) | ✅ Cerrado — sin defecto encontrado, latencia es coste esperado de arquitectura + proveedor LLM | [Paso 3](performance/2026-08-05_SESION5_PASO3_clasificacion_latencia.md) |
| Sesión 5 — Frente B (deuda técnica) | ✅ Cerrado — 5/5 candidatos implementados y validados (incl. comparación contra worktree baseline, cero regresiones) | [Paso 5](tech_debt/2026-08-05_SESION5_FRENTE_B_PASO5_decision_investigador.md) |
| Rol "Investigador" | ✅ **Resuelto — Opción A (mantener vigente), decisión del tesista implementada y validada** | Ver sección dedicada abajo |

## Cierre de fase — resumen final (histórico, Fichas 01-09)

**Fase cerrada.** Las 7 fichas críticas/importantes con fix implementado
quedan resueltas y validadas en vivo (ver "Tabla de estado" abajo). Ficha
05 y Ficha 09 tuvieron cada una su propia investigación forense posterior
(ver "Pendientes" al final) — **ambas con diagnóstico completo y cerrado**,
remediación deliberadamente no iniciada en ninguna de las dos: cada una
requiere una decisión de producto/arquitectura antes de tocar código, no
más investigación.

**Fichas resueltas (7):** 01, 02, 03, 04, 06, 07, 08 — detalle completo
en la tabla de abajo.

**Fichas con diagnóstico cerrado, remediación pendiente de decisión (2):**
05 (decisión de arquitectura del consenso) y 09 (decisión de producto/
metodología del instrumento) — ver "Pendientes" al final.

**Sesión UX/UI — CERRADA** (Pasos 1-5 completos: observar → mapear →
clasificar → decidir → implementar, 9 commits en `investigacion/sesion-
ux-ui`; ver [Paso 5](ux/2026-08-05_SESION_UXUI_PASO5_implementacion.md)
para el cierre completo y el enlace a los 4 documentos previos). 2
remediaciones implementadas y validadas E2E (traducción de vocabulario
técnico interno, microcopy del recurso pedagógico generado), 1 en
backlog por decisión explícita (no por omisión), 2 hallazgos cerrados
sin código.

**Sesión 5 (Rendimiento + deuda técnica) — CERRADA, 5/5, incluido el
rol Investigador.** Ver "Cierre de la auditoría completa" arriba y la
sección "Rol Investigador — resuelto" al final — nada queda "sin
diagnosticar" ni "sin decidir" de esta fase.

**Riesgos aceptados** (trade-offs conscientes tomados durante esta
remediación, no defectos):
- **Ficha 01 (sessionStorage):** una pestaña nueva ya no hereda la
  sesión activa de otra pestaña — debe loguearse. Decisión de
  aislamiento deliberada (commit `66c3f00`), sin evidencia de que la
  herencia automática fuera un requerimiento real del producto.
- **Ficha 04 (superado):** en su momento (commit `ab3860b`), la tabla
  `agent_decision_traces` (0 filas) y `app/schemas/decision_trace.py`
  (huérfano) no se eliminaron, mismo criterio que ADR-0011. Esa
  decisión quedó superada por Sesión 5, Frente B: ambos se retiraron
  físicamente tras una investigación dedicada (commits `5f02876`,
  `ba10d50`) que confirmó, con las 4 salvedades posibles descartadas
  una por una, que no había ninguna razón activa para conservarlos.
- **Fichas 07/08 (superado):** el fix original se acotó estrictamente
  a los archivos pedidos. La migración de `dropdown-menu.tsx` a
  `@radix-ui/react-dropdown-menu` real seguía fuera de alcance — pero
  Sesión 5, Frente B sí retiró la dependencia de Radix nunca usada
  (commit `058f46e`), sin tocar el componente custom (que tiene
  consumidores reales). El gap de `UserForm.tsx` (observación #1)
  dejó de ser un simple "gap" al investigarse a fondo: era una
  contradicción arquitectónica deliberada frente a `Roles.tsx` — el
  tesista decidió Opción A (rol vigente) y quedó implementada y
  validada (commits `bcd651a`, `ef59c91`, ver "Rol Investigador —
  resuelto" para el detalle completo).

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

1. **`UserForm.tsx`/`Roles.tsx` — contradicción sobre "Investigador"**
   (originalmente descrito como "enum limitado", commit `dd2b166`) —
   ✅ **RESUELTO.** Investigado a fondo en Sesión 5, Frente B
   (Pasos 2-3): no era un gap de implementación — `UserForm.tsx` y
   `models/user.py` documentaban que Investigador era un rol legado
   que no debía ofrecerse para asignación nueva, mientras `Roles.tsx`
   (la propia Ficha 07) lo contradecía sin condición. Resuelto por
   decisión del tesista (Paso 5, Opción A — mantener vigente) tras
   confirmar acceso real a Runtime Console, permisos, JWT y un usuario
   real con historial de uso — commits `bcd651a`, `ef59c91`, ver "Rol
   Investigador — resuelto" al final.
2. **`app/schemas/decision_trace.py`** — ✅ **RESUELTO.** Quedó huérfano
   tras eliminar `traces.py` (Ficha 04, commit `ab3860b`); retirado
   físicamente en Sesión 5, Frente B tras confirmar las 4 salvedades
   posibles (API pública, documentación, tests dinámicos, imports
   indirectos) — commit `5f02876`.
3. **Tabla `agent_decision_traces`** — ✅ **RESUELTO.** Retirada
   físicamente vía migración Alembic reversible (`upgrade`/`downgrade`
   verificados contra Postgres real) tras confirmar ausencia de feature
   flag, migración pendiente, o reserva de RFC-0007 — commit `ba10d50`.
4. **Propagación de logout entre pestañas del mismo usuario** (rama
   `!e.newValue` de `AuthProvider.tsx`) no funciona en la práctica —
   `logout()` nunca llama `localStorage.removeItem`. Preexistente,
   no introducido por esta remediación (bug report Fichas 01/02).
   Sigue sin resolver — fuera del alcance de cualquier sesión de esta
   auditoría.
5. **`components/ui/dropdown-menu.tsx` / `@radix-ui/react-dropdown-menu`**
   — ✅ **RESUELTO (parcial, correctamente acotado).** La dependencia de
   Radix nunca usada se retiró de `package.json` en Sesión 5, Frente B
   (commit `058f46e`). El componente custom `dropdown-menu.tsx` **no se
   tocó** — tiene 2 consumidores reales (`UserDropdown.tsx`,
   `Users.tsx`), es código vivo.
6. **`TraceExplorer`/`AgentThoughtStream` en `ModuleLearningView.tsx`**
   (hallazgo nuevo, Sesión 5 Frente B, validación de Paso 4) — llaman a
   `useTrace()` → `GET /api/trace/session/{id}`, endpoint ya eliminado
   por Ficha 04. Se degradan en silencio a una vista de respaldo en vez
   de romperse visiblemente — por eso nunca se detectó durante el
   recorrido visual de la Sesión UX/UI. **No investigado a fondo, no
   tocado** — candidato a su propia investigación futura (mismo
   protocolo que Ficha 05/09), con más impacto potencial que cualquiera
   de los ítems ya resueltos porque es una superficie del estudiante
   real, no infraestructura huérfana sin consumidores.
7. **5 tests preexistentes fallan contra OpenAI real**
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
8. **71 tests + 7 errores preexistentes, descubiertos al validar Paso 4
   de Sesión 5 Frente B con la suite completa** (2536 tests
   recolectados: `test_consensus.py`, `test_enrollment_lifecycle.py`,
   `test_research_agent.py`, `test_adaptive_trust.py`,
   `test_collective_inference.py`, entre otros — ninguno relacionado
   con los cambios de Frente B). Confirmado preexistente con la misma
   técnica de worktree aislado ya usada en esta auditoría: el
   subconjunto más representativo (5 archivos, 15 failed/125 passed/7
   errors) reproduce idéntico en el commit previo a Paso 4 (`5c7d33c`)
   y en HEAD. No investigado a fondo — huele a un problema de
   aislamiento/orden de ejecución al correr la suite completa junta
   (módulos tan dispares fallando a la vez sugiere estado compartido
   entre tests, no un defecto de cada módulo por separado), pero eso no
   está demostrado — fuera del alcance de esta auditoría.

## Pendientes (no iniciados en esta fase)

| Tema | Estado |
|---|---|
| Ficha 05 ("Cómo aprenderás mejor" muestra fallback genérico con perfil mixto, EstudianteC) — **diagnóstico forense CERRADO** ([bug report](runtime/2026-08-05_FICHA05_entrega_diseno_none_investigacion.md), 2 fases): 2 mecanismos confirmados con trazas reales, `runtime_bridge.py` descartado como causa, incidencia real medida en 1/29 sesiones (3.4%, caso puntual). La pregunta arquitectónica que dejó explícitamente diferida (¿`Aplazada` debe producir una decisión provisional en contexto educativo, o es un estado final válido?) **quedó respondida en [Ficha 13](runtime/2026-08-05_AUDIT-FICHA13_semantica_aplazada.md)**: es estado válido, condicionado por `urgente` (RFC-0006 §4/CONCEPT-0002 §4) — no una decisión de arquitectura sin resolver. Queda solo la decisión de producto puntual sobre los 3 call sites con `urgente=False`. | Diagnóstico + semántica arquitectónica cerrados (Ficha 13); remediación pendiente de decisión de producto puntual |
| Ficha 09 (escala Likert de 5 puntos colapsada a binario + redundancia "Base sólida"/"Siguiente reto" con dominio 100%; la auditoría la marcó "NO REPRODUCIDO EN ESTA PASADA") — **diagnóstico forense CERRADO** ([bug report](backend/2026-08-05_FICHA09_likert_binario_y_redundancia_100pct_investigacion.md)): 2 hallazgos distintos confirmados con código real. Hallazgo A (Likert→binario en `compute_prior_knowledge`): dato crudo preservado íntegro en `DiagnosticResult.answers`, solo el campo derivado `known_topics`/`prior_level` pierde resolución — 13/40 registros reales afectados (32.5%). Hallazgo B (redundancia a dominio 100% en `compute_competency_profile`): mecanismo de desempate degenerado, confirmado 10/10 exacto contra los casos de 100% uniforme — 10/28 intentos reales (35.7%). A diferencia de Ficha 05 (3.4%, caso puntual), **ambos hallazgos son frecuentes, no marginales**. **Clasificación final cerrada en [Ficha 14](backend/2026-08-05_AUDIT-FICHA14_clasificacion_likert_y_redundancia.md)**: ninguno de los dos es defecto funcional ni afecta a Adaptar/Runtime — metodológico (A) y producto/UX (B). Remediación sigue sin iniciar, pendiente de decisión de producto/metodología, no de investigación adicional. | Diagnóstico + clasificación cerrados (Ficha 14); remediación pendiente de decisión de producto/metodología |
**El rol "Investigador" ya no está en esta tabla — resuelto.** Ver
"Rol Investigador — resuelto" abajo para el detalle completo de la
decisión e implementación.

**Nada más queda pendiente de esta auditoría.** Rendimiento (§11) y
Sesión 5 completa (código muerto, deuda técnica) están **cerradas** —
ver "Cierre de la auditoría completa" al inicio de este documento.

**Sesión UX/UI (§06 de la auditoría y más allá) — CERRADA.** Ver
[Paso 5](ux/2026-08-05_SESION_UXUI_PASO5_implementacion.md): H1
(vocabulario técnico interno sin traducir) y H2 (panel de recurso
pedagógico sin contexto) implementados y validados E2E; H3 (estados de
espera) queda en backlog por decisión explícita, no por falta de
diagnóstico; H4 documentado como patrón de referencia; H5/H6 cerrados
sin código.

**Sesión 5 — Frente A (Rendimiento) — CERRADO.** Ver
[Paso 3](performance/2026-08-05_SESION5_PASO3_clasificacion_latencia.md):
~98% de la latencia medida es tiempo del proveedor LLM, ~2% overhead
propio del sistema; la secuencia diagnosticar→remediar/orientar es
coste arquitectónico deliberado (RFC-0002 + RFC-0006 §5), no
paralelizable sin violar el contrato de capacidades. Sin defecto
encontrado — declarado explícitamente como resultado válido de
investigación, no como fracaso.

**Sesión 5 — Frente B (deuda técnica) — CERRADO, 5/5.** Ver
[Paso 5](tech_debt/2026-08-05_SESION5_FRENTE_B_PASO5_decision_investigador.md)
para el cierre completo. Commits: `5f02876`, `ba10d50`, `058f46e`,
`ceb2fb6` (los 4 candidatos técnicos: código muerto, infraestructura
huérfana, dependencia sin uso, documentación de tesis desactualizada)
+ `bcd651a`, `ef59c91` (rol Investigador, tras la decisión del
tesista — ver siguiente sección).

## Rol "Investigador" — resuelto (Opción A: mantener vigente)

**No era deuda técnica ni un bug — era una decisión de arquitectura/
producto**, tratada aparte a propósito para no mezclarla con los
hallazgos técnicos de esta auditoría. Investigada con 5 preguntas
concretas antes de decidir, y resuelta en la misma sesión — ver
[Paso 5](tech_debt/2026-08-05_SESION5_FRENTE_B_PASO5_decision_investigador.md)
para el detalle completo (evidencia, las dos opciones consideradas, y
la "Resolución final" con la decisión textual del tesista).

**Resumen:** la evidencia (acceso real a Runtime Console reforzado por
Ficha 06, permisos acotados reales, presencia en JWT, 7 endpoints
protegidos, 1 usuario real con intentos de login recurrentes, routing
frontend dedicado y funcional) confirmó que Investigador **no** es un
rol legado — el problema estaba en 6 comentarios/docstrings
desactualizados, no en el comportamiento real del sistema. El tesista
decidió Opción A (mantener vigente) con alcance explícitamente acotado
a sincronizar documentación y UI, sin ampliar permisos ni rediseñar el
sistema de roles. Implementado en 2 commits (`bcd651a` backend,
`ef59c91` frontend), validado (`tsc`, `npm run build`, import limpio),
cero cambio de autorización real.
