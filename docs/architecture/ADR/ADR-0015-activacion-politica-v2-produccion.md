# ADR-0015 — Activación de `POLITICAS["v2"]` como línea base de producción

- **Estado:** Aceptado como decisión arquitectónica — **activación
  ejecutada y revertida el mismo día** tras encontrar, en validación
  E2E real, un defecto de integración no cubierto por el análisis de
  riesgo original (ver §8). Pendiente de cumplir la precondición ahí
  descrita antes de una reactivación (`ADR-0016`, todavía no escrito).
- **Fecha:** 2026-08-04
- **Preserva:** `runtime/kernel/deliberation/mecanica.py` (sin cambios),
  `runtime/kernel/deliberation/politica.py` (`POLITICAS["v1"]`/`["v2"]`,
  sin cambios — ya definidas por ADR-0012), `runtime/kernel/deliberation/
  confianza.py` (sin cambios), ADR-0013/ADR-0014 (sin cambios de
  comportamiento)
- **Criterio de aceptación:** ver §5

## 1. Contexto

`ADR-0012` (2026-08-01) definió `POLITICAS["v2"]` (δ=0.10, θ=0.5) y
demostró con datos reales que produce comportamiento deliberativo
observable (aplazamiento ante evidencia insuficiente) donde `"v1"`
(degenerada, δ=0) siempre resuelve en un paso. Dejó **explícitamente
condicionada** su activación en producción a dos precondiciones
(§5): que la confianza declarada de Remediar/Orientar estuviera
calibrada (sin eso, el margen que δ evalúa es ruido de muestreo del
LLM, no señal) y que existiera trazabilidad suficiente para auditar
cada decisión sin depender de recomputar métricas en cada lectura.

Ambas precondiciones ya se cumplieron, en esta misma rama:

- **ADR-0013** (calibración) — cerrado y **re-medido con LLM real**
  (`consenso_remediar_orientar_llm_por_perfil.py`, Auditoría 5): el
  ruido intra-perfil cae de 0.0289 a 0.0 tras la calibración; Orientar
  deja de declarar confianza constante. La misma corrida encontró el
  primer caso real de empate matemático (`dominio_marginal`,
  margen=0) — el escenario exacto para el que δ existe.
- **ADR-0014** (trazabilidad) — margen y razón de cada deliberación
  quedan persistidos, no recalculados; la regresión real de
  compatibilidad que introdujo (409/734 sesiones) fue encontrada y
  corregida mediante validación E2E contra Postgres real.
- **Validación funcional E2E** (misma sesión) — recorrido completo de
  Estudiante (dashboard, ruta, misión, Tutor IA con LLM real),
  Docente (Panel Pedagógico, Analítica IA, Runtime Console) y
  Administrador (dashboard, Estado del Sistema), sin bloqueadores
  funcionales.

## 2. Decisión

Cambiar `VERSION_POLITICA` en `app/services/runtime_connection.py` de
`"v1"` a `"v2"` — **una constante, un archivo**. Esto basta porque la
arquitectura ya está preparada para esto desde RFC-0003/ADR-0003:
`Identidad.version_politica` se fija atómicamente al abrir cada sesión
(INV-1/INV-2) y `resolver_politica(identidad.version_politica)`
(`politica.py`) es el único punto donde `walkthrough.py` obtiene la
`Politica` real (`walkthrough.py:376`) antes de cada `convocar()`
(`walkthrough.py:91`). Ningún otro componente decide política por su
cuenta.

**Efecto:** toda sesión **nueva** abierta después del despliegue corre
bajo v2 (δ=0.10, θ=0.5, `limite_reconvocatoria=2`, `pesos_asunto`/
`asuntos_reservados` neutros — única variable independiente activada:
δ, igual que en el experimento de ADR-0012). Toda sesión **ya
existente** conserva `"v1"` para siempre (INV-1/INV-2: la identidad de
una sesión, incluida su versión de política, es inmutable) — no hay
migración de historia, no hace falta ninguna.

**Qué componentes consumen la política nueva (auditado, no supuesto):**
únicamente `runtime/engine/graph/walkthrough.py` vía
`resolver_politica()`. Todo lo demás que hoy expone información de
consenso (RFC-0007 §2.2 `derivar_consenso`, Runtime Console, Panel
Pedagógico → Observabilidad Pedagógica, Modo Evidencia) ya lee la
política de cada sesión individualmente desde su propia `Identidad` —
ninguno de ellos asume `"v1"` en ningún punto del código, así que
ninguno requiere cambio.

**Riesgo de UX contenido, no solo argumentado:** un aplazamiento (rama
`Aplazada` de `convocar()`) nunca deja al estudiante esperando — RFC-
0006 §4 Parte E (`ROADMAP-RFC-0006`, mini-épica 4b, ya cerrada) resuelve
provisionalmente (`REGLA_PROVISIONAL`) cuando el slot es urgente, y
Parte F (mini-épica 5, ya cerrada) escala al docente tras
`limite_reconvocatoria` reconvocatorias sin discriminar. El walkthrough
siempre converge a una decisión en la misma sesión de uso — v2 no
introduce ningún estado nuevo de "colgado".

## 3. Engineering Gate (CLAUDE.md)

1. **¿Qué decisión implementa?** Cierra la condición que el propio
   `ADR-0012 §5` y `ADR-0013 §7` dejaron pendiente explícitamente — no
   responde a un RFC nuevo.
2. **¿Introduce concepto nuevo?** No. `POLITICAS["v2"]` ya existe,
   probada desde el 2026-08-01 (script aislado) y re-validada hoy con
   LLM real. Esto solo cambia qué valor lee producción por defecto.
3. **¿Rompe algún principio P1–P17?** No. `mecanica.py` no cambia
   ninguna rama; el mecanismo de aplazamiento/escalada ya está
   probado end-to-end (`test_parteE_walkthrough_aplazamiento.py`,
   `test_parteF_escalada_organica_grafo.py`, ambos en la suite de 430
   verdes de hoy).
4. **¿Requiere modificar un RFC?** No.

## 4. Alcance NO cubierto (deliberado)

- **No introduce selección por cohorte, banderas ni activación
  gradual/porcentual.** El propio comentario de
  `runtime_connection.py` ya lo advertía: *"No existe todavía un
  catálogo real entre el cual elegir — inventar un contrato para
  elegirlo fabricaría una capacidad inexistente"* (ADR-0009 §4). Un
  mecanismo de despliegue progresivo es una capacidad nueva que, si
  hiciera falta, requeriría su propio RFC — no se improvisa aquí.
- **No modifica `pesos_asunto` ni `asuntos_reservados`** — siguen
  neutros en v2, igual que en el experimento original de ADR-0012;
  esa es la "Escenario B" que ADR-0012 §5 dejó fuera a propósito.
- **No toca las sesiones ya persistidas** — quedan en v1 para siempre,
  por diseño (INV-1/INV-2), no por omisión.
- **No añade ninguna capacidad de swarm nueva** ni cambia qué
  capacidad tiene autoridad de propuesta (eso sería "Escenario C" de
  ADR-0012 §5, fuera de alcance).

## 5. Criterios de cierre

- `VERSION_POLITICA = "v2"` en `runtime_connection.py`; diff de una
  línea, verificado por `git diff` — ninguna otra línea de producción
  cambia.
- Cero regresión: suite completa `tests/runtime/` (430 casos a la
  fecha de este ADR) sigue en verde tras el cambio.
- **Validación E2E real posterior al cambio** (no antes — el cambio en
  sí es lo que hay que observar): al menos una sesión de estudiante
  nueva, con productores LLM reales, completa el walkthrough de
  extremo a extremo sin quedar bloqueada. Si el margen entre Remediar
  y Orientar resulta insuficiente en algún punto (como el caso
  `dominio_marginal` de la Auditoría 5), se observa una `Aplazada`
  seguida de resolución provisional o avance normal — nunca un estado
  sin decisión visible para el estudiante.
- `derivar_consenso` (RFC-0007 §2.2) sobre esa sesión nueva muestra al
  menos un `margen` y un `regla`/`evidencia_faltante` reales — cierre
  visible del círculo completo: calibración → margen → trazabilidad →
  decisión deliberativa observable.

## 6. Métricas de observación posteriores a la activación

Sin estas, "activar v2" sería un acto de fe, no una decisión de
ingeniería medible:

- **Distribución de resultados de deliberación** (`Resuelta` /
  `Aplazada`→provisional / `Escalada`) en sesiones nuevas bajo v2,
  comparada contra la distribución histórica bajo v1 (100% `Resuelta`
  por diseño matemático — ver `ADR-0012 §2`, "margen ≥ delta=0 siempre
  se cumple"). El cambio esperado y buscado: aparición de aplazamientos
  reales donde antes no había ninguno.
- **Frecuencia de escalada al docente** (Parte F) — debe mantenerse
  baja; una escalada frecuente indicaría `limite_reconvocatoria=2`
  demasiado bajo para la evidencia real disponible, señal para una
  iteración futura, no para revertir esta.
- **Margen observado en el momento de resolución/aplazamiento** —
  reutilizando exactamente el campo que ADR-0014 ya persiste; permite
  auditar, sesión por sesión, si δ=0.10 sigue siendo el punto de corte
  correcto sin necesidad de volver a instrumentar nada.

## 7. Estrategia de rollback

Trivial por diseño, no por suerte: revertir `VERSION_POLITICA` a
`"v1"` es un cambio de una línea, sin migración, sin efecto sobre
sesiones ya abiertas bajo v2 (permanecen v2 para siempre — INV-1/
INV-2, igual que las v1 anteriores permanecen v1). No existe una
ventana de inconsistencia: cada sesión sabe bajo qué política nació y
la mecánica nunca la reinterpreta con una política distinta a la que
declaró su propia `Identidad`.

## 8. Resultado de la activación real — revertida el mismo día

El §7 (rollback) resultó necesario, y exactamente tan trivial como se
diseñó: se ejecutó, se validó, se usó.

**Secuencia real ejecutada:** `VERSION_POLITICA` cambiado a `"v2"` →
suite completa `tests/runtime/` (430 casos) verde → cuenta de
estudiante genuinamente nueva creada, diagnóstico de 12 preguntas
respondido con perfil real mixto (100/50/100/50/50/50%) →
walkthrough completo hasta ruta generada, sin bloqueo → confirmado en
Postgres: `runtime.runtime_sessions.version_politica = 'v2'` para esa
sesión → deliberación real encontrada con **margen 0.1131** (apenas
sobre δ=0.10 — el caso límite exacto que motivó esta ADR) → **hasta
aquí, todo funcionó como se diseñó.**

**Lo que el análisis de riesgo original no cubrió:** corrida la suite
de integración app-level completa (`tests/test_pedagogy_runtime_
bridge.py`, `tests/test_students_evaluation_runtime_wiring.py`,
`tests/test_module_orchestration_bloom_target.py`, `tests/
test_runtime_bridge.py` — no incluida en el criterio de cierre
original, que solo mencionaba `tests/runtime/`), aparecieron **6
fallos reales, reproducibles, con LLM real** — todos con la misma
causa raíz:

```
app/services/runtime_bridge.py:48  PeticionAbrirSesion(...) nunca pasa `urgente`
runtime/boundary/inbound/dto.py:50  urgente: bool = False (default silencioso)
```

Con `urgente` fijo en `False` para todo el tráfico real, un margen
real por debajo de δ=0.10 produce una `Aplazada` genuina (correcta,
por diseño de RFC-0006 §4 Parte E) — pero **varios consumidores de
producción asumen que una decisión existe siempre**: la sugerencia
semanal del docente contó `estudiantes_con_evidencia=0` en vez de 3
(degradación silenciosa, no crash), y la orquestación de módulo
lanzó `TypeError: 'NoneType' object is not subscriptable` (crash
real). El §2 de esta ADR afirmaba *"el walkthrough siempre converge a
una decisión... v2 no introduce ningún estado nuevo de colgado"* —
cierto **dentro del kernel** (Parte E/F, ya probadas), **falso en la
frontera de integración de producción**, porque nada conecta
`urgente=True` a un evento real todavía — el mismo hueco que
`RFC-0006/5 (Parte F, escalada orgánica)` ya había dejado registrado
como *"activación EN VIVO bloqueada"*, y que esta activación fue la
primera en ejercitar de verdad.

**Acción tomada:** `VERSION_POLITICA` revertido a `"v1"` en la misma
sesión (diff idéntico al commit anterior — nunca llegó a commitearse
como `"v2"`). Ningún consumidor se modificó todavía a propósito: la
pregunta real no es "cómo parcheo cada consumidor uno por uno" sino
**quién decide cuándo una deliberación de producción es urgente** —
eso es una decisión de contrato (qué eventos disparan `urgente=True`,
qué actores pueden hacerlo, qué camino de fallback usa cada
consumidor mientras no hay decisión), no un fix local.

**Precondición para una reactivación futura (`ADR-0016`, no escrito
todavía):** conectar `urgente` a un disparador real de producción
(RFC-0006 §4 Parte E/F) y hacer que cada consumidor de `Entrega`/
decisión maneje explícitamente el caso "todavía sin decisión" — no
asumirlo implícitamente. Solo entonces se reintenta esta activación.

---

*Origen: condición dejada explícitamente pendiente por ADR-0012 §5 y
ADR-0013 §7, cerrada tras validación funcional E2E completa
(Estudiante/Docente/Administrador) en la misma sesión. Rama:
`feat/confidence-calibration-remediation-orientation`. Activación
ejecutada y revertida el mismo día tras hallazgo de integración real
(§8) — ver también `DEMO_RECOVERY.md` para el hallazgo no relacionado
del loop intermitente encontrado en la misma validación E2E.*
