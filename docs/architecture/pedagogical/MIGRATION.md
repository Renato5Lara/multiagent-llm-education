# Bitácora de Migración — Arquitectura Pedagógica v1.0 → Implementación

No es arquitectura. Es registro de avance: qué se implementó, en qué commit, y qué
falta. Una o dos líneas por entrada — el detalle vive en el propio commit y en
[ESTADO.md](ESTADO.md)/[ANEXO-A](ANEXO-A-MATRIZ-TRAZABILIDAD.md) para trazabilidad
de principios.

## Commit 1 — Boundary: Política de Selección de Forma (Adenda A)
✔ `backend/app/services/adaptive_form_selection.py` — `1ba66ed`
✔ Corrección funcional (insumo de Memoria, `formas_ya_mostradas`) — `7c9f8d3`
✔ 13/13 tests, backend importa limpio, cero wiring todavía (módulo inerte)

## Commit 2 — Higiene del repositorio (~8 días integrados en 7 commits)
✔ `d4ccf65` fix(replay): fix de evidencia abandonada (STAB-01)
✔ `9129c53` chore: except silenciosos → logging
✔ `9ebd873` style: tokens de tema oscuro
✔ `503b160` fix(auth): redirect de rol investigador
✔ `b322da0` feat(learning): bloqueo del Post-Test sin ruta completa (IMPL-01)
✔ `c990e74` refactor(docente): retiro de Comparación Swarm (IMPL-02/03)
✔ `a694f3b` fix(users): desacople de Ciclo del pipeline legado
✔ `429f543` refactor(dashboard): recomposición en 4 componentes
✔ `9f2b94e` feat(experience): sub-pasos + botón Ayuda en ModuleExperienceView
✔ Backend importa limpio, frontend build de producción limpio tras cada grupo
□ Pendiente de decisión del usuario, fuera de esta bitácora:
  `backend/scripts/seed_demo_swarm.py` (¿sigue en uso?), `PENDING_FIXES_M1.md`
  y `frontend/--full-page` (descartables, no son trabajo real)

## Commit 3 — Wiring + migración del frontend
✔ `91e7ea4` (3a) — `/cycle-evidence` llama a `seleccionar_forma()`, aditivo
  puro; `CycleEvidenceSubmit.formas_ya_mostradas` nuevo, aún vacío desde el
  frontend en este punto. El módulo del Commit 1 deja de estar inerte.
✔ `b45c9ae` (3b) — `experienceOrchestrator.ts` consume
  `runtime_decision.forma.tipo` como fuente primaria;
  `REINFORCEMENT_BY_MODALITY`/`resolveReinforcementPriority` quedan solo de
  fallback (Boundary sin recomendación reconocible, o sin contenido
  autorado para la forma recomendada). `visitedReinforcements` ahora viaja
  como `formas_ya_mostradas` en cada request — cierra el círculo con la
  corrección funcional del commit `7c9f8d3`.
✔ Orden invertido respecto al plan original (wiring antes que frontend) por
  seguridad: evita un adaptador frontend apuntando a un campo que el
  backend todavía no envía.
✔ 17/17 tests backend, tsc limpio, eslint sin errores nuevos, build de
  producción exitoso. Sin cambio de comportamiento observable: misma
  prioridad, ahora en el Boundary en vez de en el cliente.

## Deuda técnica registrada (no se resuelve ahora)
□ `REINFORCEMENT_BY_MODALITY`/`resolveReinforcementPriority`
  (`experienceOrchestrator.ts`) quedan como fallback local desde el Commit 3.
  Cuando el Boundary pueda recomendar todas las formas del catálogo de PP4 y
  todos los ciclos estén completamente adaptados con contenido autorado para
  cada una, evaluar eliminar definitivamente el fallback — no antes.

## Commit 4 — Infraestructura de la Adenda B (no "Adenda B completa")
✔ `e6c86a3` — `POST /api/students/consent-response` (contrato +
  registro en `research_metrics`, `CONSENT_RESPONSE`) + `useSubmitConsentResponse`
  en el frontend, sin wiring a ningún componente.
✔ Checklist de aceptación (5/5): sin cambio de comportamiento observable
  (endpoint y hook nuevos, sin consumidor); ninguna decisión pedagógica
  nueva (nunca llama a `runtime_bridge`, verificado con test); permanece
  inactiva (ninguna prioridad selecciona una forma "consentimiento" hoy);
  4/4 tests (contrato, persistencia, verificación negativa de no-toca-
  runtime); oferta proactiva y solicitud voluntaria no comparten código.
✔ `ModuleExperienceView.tsx` no se tocó — cero riesgo por construcción,
  no solo por intención. Backend importa limpio, tsc/eslint/build
  limpios.
□ Activación futura (fuera de este commit): ampliar
  `_PRIORIDAD_POR_MODALIDAD` o un productor nuevo del runtime (RFC) para
  que `codigo_guiado`/`narracion_tutor` empiecen a seleccionarse; recién
  ahí construir la UI que ofrezca consentimiento visible.

## Verificación de aislamiento (Commit 4, post-cierre)

Los 4 puntos que propuso el usuario, verificados independientemente del
commit (no solo confiando en lo ya probado):

1. **El endpoint existe** — `POST /api/students/consent-response`, confirmado.
2. **Ningún flujo actual lo consume** — cero referencias a
   `useSubmitConsentResponse`/`consent-response` fuera de su propia
   definición, en frontend y backend.
3. **Su presencia no modifica el comportamiento observable** — **verificado
   con diff exacto, no solo re-corrida.** Suite completa (2411 tests, excluidos
   los 2 archivos de colección rota de Tavily) corrida en el estado actual
   (79 failed, 7 errors) y comparada contra un worktree del commit
   `076f9f6` (el estado exacto previo a toda esta sesión — Boundary,
   Adendas, higiene del repo, todo). Diff de nombres de test fallidos:
   - **6 "nuevos" resultaron ser un artefacto del método de comparación**,
     no una regresión: `tests/test_config.py` (6 tests sobre API keys por
     defecto) leen el `.env` real del directorio de trabajo — el worktree
     temporal no tenía `.env` (no versionado), así que ahí pasaban con
     valores vacíos por accidente. Confirmado corriendo el mismo archivo
     en ambos directorios: mismatch de `.env`, no de código.
   - **1 test que fallaba en el baseline ahora pasa**:
     `test_evidence_service_runtime_trace.py::test_narrativa_por_
     concepto_usa_razonamiento_real_del_claim` — mismo módulo que toca el
     fix STAB-01 (`evidence_service.py`, commit `d4ccf65`), mejora
     incidental ya documentada en ese commit, no una sorpresa.
   - **Los 74 fallos restantes son idénticos en baseline y estado
     actual** — legacy (`test_swarm_activation.py`/`test_swarm_
     transactions.py`, BaseAgent confirmado muerto desde la Auditoría),
     dependientes de red externa (`test_retrieval_strategy.py`,
     `test_research_agent.py`), u otra deuda preexistente sin relación
     con `backend/runtime/`, el Boundary o esta migración.
   - **Conclusión, formulada con la precisión que el método permite:** no
     se identificaron regresiones nuevas atribuibles a los Commits 1–4 en
     las suites ejecutadas y comparadas contra el baseline (2411 tests,
     por diff exacto de nombres fallidos, no por inspección de una
     muestra). Esto no es una prueba de ausencia total de regresión —
     quedan fuera del alcance de esta verificación cualquier camino sin
     cobertura de test y `tests/test_knowledge_test.py`/los 2 archivos de
     Tavily con error de colección, excluidos de ambas corridas por
     separado (ver más abajo).
4. **Los datos registrados alcanzan para una futura activación** —
   matizado, no un "sí" plano: ver tabla de niveles.

**Hallazgo colateral, sin relación con este trabajo:** la corrida completa
encontró 2 errores de colección preexistentes —
`tests/test_tavily_cache.py` y `tests/test_tavily_client.py` importan
`get_tavily_cache`/`get_tavily_client`, funciones que ya no existen en
`app/integrations/tavily/`. Cero cambios sin commitear en esos archivos
(`git status` limpio, último commit real de hace varias sesiones) — no es
una regresión de esta migración, es deuda preexistente fuera de alcance.

### Niveles de evolución del endpoint de consentimiento

| Nivel | Uso | ¿El payload actual alcanza? |
|---|---|---|
| 1 (actual) | Registro analítico (`research_metrics`) | Sí — es literalmente lo que hace hoy |
| 2 | Memoria del ciclo (evitar repetir ofertas en el mismo ciclo) | **No aplica a este endpoint** — esa responsabilidad ya la resuelve `formas_ya_mostradas` (Commit 3), client-side, por ciclo. Este endpoint no necesita evolucionar hacia esto porque el mecanismo ya existe en otro lugar. |
| 3 | Evento de dominio (afectar decisiones futuras del runtime) | **No, tal como está.** Falta una referencia causal a la decisión de Adaptar que originó la oferta (un `EntryId`/asunto) — sin eso, un fact/claim nuevo violaría INV-5 (todo claim exige respaldo) y P6 (la explicación se recorre). Si algún día se decide activar este nivel, el esquema necesita ese campo antes, no después. |

## Merge con origin/runtime/architecture (2026-07-24)
✔ `f298372` — 44 commits desarrollados en paralelo (Runtime, PythonBridge,
  ConceptPrimerCard) fusionados con los Commits 1-4 de esta bitácora.
  Backup: `backup/runtime-before-merge`. 363/363 tests, tsc y build
  limpios tras resolver.

**Pendiente de Engineering Review — colisión arquitectónica real,
no resuelta aquí, solo contenida:** el merge introdujo `andamiaje`
(4a dimensión de Adaptar, RFC-0002 §3/R3 — `runtime/domain/adaptar/
productor.py`, valores `ejemplo`/`alternar-modalidad`/`reto` derivados
de la señal de Tutorizar) que la rama remota consumía directamente en
`ModuleExperienceView.tsx` para decidir la forma del refuerzo — en
conflicto con la Adenda A (Documento 5 §4.1: "el frontend nunca deriva
la forma, solo el Boundary").

Decisión al resolver el conflicto: `seleccionar_forma()`/
`formaDelBoundary` sigue siendo la única autoridad sobre la forma;
`andamiaje` queda disponible en `diseno` (ya se usa para `modalidadHonrada`/
`fluencyStreak` — eso es selección de MODALIDAD, dimensión que el
frontend ya leía directo de `diseno.modalidad` desde antes de la Adenda A,
no de FORMA) pero no vuelve a decidir el refuerzo. La lógica de origen
que sí lo hacía (`andamiaje === 'ejemplo'`/`'reto'` reordenando o
sustituyendo la selección) se descartó en esta resolución.

**Pregunta abierta para la Review:** ¿`andamiaje` debe convertirse en un
cuarto insumo declarado de `seleccionar_forma()` (extensión formal de la
Adenda A, ya que RFC-0002 §3/R3 lo respalda), o debe quedar fuera del
alcance del Boundary permanentemente? No se decide en este merge — el
comentario inline en `ModuleExperienceView.tsx` remite aquí en vez de
repetir esta explicación completa.

## Commit 5 — Validación de Aceptación Arquitectónica

Renombrado del usuario: ya no es solo "stress-test", son tres criterios
explícitos por escenario — **Correctitud** (¿el comportamiento coincide
con lo documentado?), **Coherencia** (¿ninguna decisión contradice
Adenda A/B/C, Boundary, Runtime?), **Observabilidad** (¿puede explicarse
qué decidió el Runtime, qué devolvió el Boundary, qué vio el estudiante?).

### Fase A — API/HTTP real (completa)

**Nota de metodología, con honestidad:** toda la suite de pytest —
incluidas estas pruebas nuevas y las de los Commits 1-4 — corre contra
SQLite en memoria (`tests/conftest.py`), no PostgreSQL. Es una convención
preexistente de todo el proyecto, no introducida aquí. La Regla de Cierre
(CLAUDE.md) exige Postgres real para declarar un recorrido cerrado — por
eso, además de la suite, se corrió un spot-check directo contra el
Postgres real en ejecución (`registrar_evidencia_evaluacion` +
`seleccionar_forma()`, sin HTTP ni SQLite de por medio) para el flujo más
crítico (Escenario 2/8). El resto de Fase A se apoya en SQLite — suficiente
para Correctitud a nivel de lógica, no un sustituto de Postgres real.

| # | Escenario | Correctitud | Coherencia | Observabilidad |
|---|---|---|---|---|
| 1 | Dominio alto | ✔ `test_escenario_1...` — HTTP real, cadena completa | ✔ forma automática, nunca consentimiento | ✔ `runtime_decision` expone asunto/diseño/forma |
| 2/8 | Bloqueado / automática | ✔ `test_cycle_evidence_dataset.py` + **spot-check contra Postgres real** (no solo SQLite) | ✔ respeta `alternativas_descartadas` de Adaptar (confirmado con señal real de frustración) | ✔ misma respuesta HTTP, trazable |
| 3/9 | Acepta ayuda / con consentimiento | ⚠ Endpoint probado aislado (`test_consent_response.py`) — **sin caso real activable**: ninguna prioridad selecciona hoy una forma "consentimiento" (ver Adenda A/NOTA §3) | ✔ consistente con la acotación decidida — no se simula un caso inexistente | ✔ el propio vacío es observable (documentado, no oculto) |
| 4 | Rechaza ayuda | ⚠ Mismo límite que 3/9 — el mecanismo de exclusión (`formas_ya_mostradas`) está probado, pero nada dispara un rechazo real hoy | ✔ Adenda B (oferta vs. solicitud) se respeta por diseño | ✔ |
| 5 | Cierre de misión | ✗ **Hallazgo, no bug:** la Síntesis Pedagógica de 3 estados (Doc5 §4.2) no existe en código — `evaluatorVerdict` en `ModuleExperienceView.tsx` sigue siendo la plantilla cliente-side de 3 opciones que ya documentó la Auditoría original (Doc1 §7, punto 12) | ✗ contradice PP3 (el cierre debe ser síntesis de Validar, no una plantilla) | ✔ el hallazgo es explícito, no se ocultó |
| 6 | Retorno al día siguiente | ✔ `tests/runtime/invariants/test_ADR_0008_almacen_memoria.py` | ✔ consolidación solo al cerrar sesión (RFC-0005), restricción ya conocida | ✔ |
| 7 | Transición entre módulos | ✔ `test_escenario_7...` — confirma el comportamiento real | ⚠ **Hallazgo:** PP2 describe la agregación deseada; el desbloqueo sigue siendo snapshot del pre-test, no recalculado dinámicamente (Modelo de Evolución, Categoría A1 — wiring identificado, no construido) | ✔ el test documenta exactamente dónde está la brecha |
| 10 | Recuperación tras interrupción | ✔ `tests/runtime/reconstruction/test_R3_reconstruccion_learning_state.py` | ✔ reconstrucción determinista desde la cadena de transiciones | ✔ |

**Resultado de Fase A: 4/10 escenarios completamente correctos y coherentes
(1, 2/8, 6, 10); 2/10 con límite honesto de activación, no de
implementación (3/9, 4); 2/10 con hallazgos reales de brecha
arquitectura-vs-código, ya existentes antes de este commit y ahora
formalmente registrados (5, 7).** Ningún hallazgo se corrigió aquí — Fase A
es validación, no desarrollo nuevo.

### Fase B — navegador real (completa)

Cuenta descartable: `e2e.validacion.c4574c67@upao.edu.pe` (sesión de demo
real "Maria Garcia" cerrada explícitamente antes de empezar, sin mutarla).
Recorrido completo contra el stack real (backend `:8000`, frontend
`:5173`, Postgres real `upao_postgres`) en Chrome real, sin mocks —
satisface la Regla de Cierre para los 4 escenarios.

| # | Escenario | Correctitud | Coherencia | Observabilidad |
|---|---|---|---|---|
| B1 | Diagnóstico completo | ✔ Onboarding→18 preguntas VARK→perfil "visual" (conf. 80%, lectora de apoyo) coincide exactamente con el patrón de respuestas dado | ✔ Deliberación del enjambre (4 agentes + Motor de Consenso) coherente entre sí; ruta generada honra el perfil | ✔ Trace en vivo de la deliberación + panel "traza real del runtime" durante el diagnóstico |
| B2 | Ciclo completo de una misión | ✔ 3 ciclos (Instrucciones precisas, Variables, Entrada de datos), cada uno Concepto→Práctica→Consolidar; forma automática "infografía" elegida consistentemente para el perfil visual | ✔ Andamiaje decreciente narrado explícitamente ("vamos con menos apoyo") tras cada acierto — los 5 peldaños (Observa→Cambia un detalle→Completa el código→Encuentra el error→Hazlo tú→Profundiza) se citan en el propio "por qué pasó esto"; remediación real (fallo→apoyo con ejemplo resuelto→reintento→éxito) al fallar el ejercicio de práctica del Ciclo 1 | ✔ cada paso expone "por qué pasó esto"; el feedback nunca es solo correcto/incorrecto |
| B3 | Interrumpir y volver | ✔ Salida a mitad del Ciclo 3 (Concepto de `input()`) vía navegación al Dashboard, regreso con "Continuar misión" — resumió exactamente en el mismo punto | ✔ coincide con Adenda C: recupera el contexto exacto, no introduce información nueva | ✔ banner explícito "Bienvenido de nuevo. Continuemos justo donde lo dejaste."; el Dashboard mostró "Mis Conceptos" con el estado real (2/3 dominados, 1 pendiente) antes de reingresar |
| B4 | Cambio de módulo | ✔ al completar la Misión 1, transición automática a la Misión 2 ("Estructuras de control") con nueva pregunta de curiosidad; la Ruta de Aprendizaje refleja "Misión 01 — Completada" + "Misión Final — Disponible" | ✔ progreso (1/2 misiones, 50%, 50/100 pts) consistente entre la pantalla de cierre de misión y la Ruta de Aprendizaje | ✔ toast "Misión completada — Tu progreso quedó guardado"; síntesis final ("Tu hipótesis inicial") conecta explícitamente la pregunta de curiosidad del inicio con lo aprendido |

**Observación honesta sobre el Escenario 5 de Fase A (cierre de misión,
plantilla cliente-side de 3 estados):** este recorrido no ejercitó
específicamente `evaluatorVerdict` en `ModuleExperienceView.tsx` — los
"incorrecto" que sí aparecieron durante B2 fueron feedback de ejercicio
(`Ejecutar`/`Comprobar secuencia`), no el veredicto de cierre de ciclo. El
hallazgo de Fase A no se confirma ni se refuta aquí; sigue documentado
como estaba.

**Resultado de Fase B: 4/4 escenarios validados en navegador real contra
Postgres real — Correctitud y Coherencia completas en los 4; Observabilidad
alta en los 4** (deliberación del enjambre visible en el diagnóstico, "por
qué pasó esto" en cada paso de práctica, banner explícito de recuperación,
toast + síntesis narrada en el cierre de misión). A diferencia de Fase A
(que documentó 2 brechas reales), esta fase no encontró defectos nuevos:
la experiencia visible del estudiante coincide con la arquitectura
documentada en los 4 recorridos ejecutados.

## Cierre del Commit 5

Fase A (10 escenarios, API/HTTP real) + Fase B (4 escenarios, navegador
real) completas. Hallazgos reales quedan registrados donde ocurrieron
(Fase A, Escenarios 5 y 7) — ninguno se corrigió en este commit, consistente
con "Fase A/B es validación, no desarrollo nuevo". Próximo paso: decisión
del usuario sobre push a `origin/runtime/architecture` (no ejecutado sin
confirmación explícita) y, eventualmente, una Engineering Review para la
pregunta abierta de `andamiaje` registrada en el merge del 2026-07-24.
