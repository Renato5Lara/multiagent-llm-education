# Sesión 5, Frente B — Paso 1: Inventario de código muerto y deuda técnica

## Metadata

- **Fecha:** 2026-08-05
- **Rama:** `investigacion/sesion5-rendimiento` (mismo frente de sesión;
  se evalúa una rama propia solo si Paso 4 aprueba remediación)
- **Protocolo:** observar → medir → clasificar → decidir → implementar.
  Este documento es Paso 1 — inventario verificado con evidencia real
  (grep, lectura de código, consultas de solo lectura a Postgres real),
  **ningún archivo de código modificado**.
- **Frente A (Rendimiento) — cerrado** en Paso 3
  (`2026-08-05_SESION5_PASO3_clasificacion_latencia.md`): sin defecto
  encontrado, latencia es coste esperado de arquitectura + proveedor.
- **Insumo:** §12 ("Código redundante") y §13 ("Código innecesario")
  del `.docx` de auditoría original, **extraídos textualmente** (no
  citados de memoria):

  > **12 — Código redundante.** El enum de roles vive duplicado sin
  > sincronía garantizada: `userrole` de PostgreSQL (admite
  > investigador) vs. enum de UI del frontend (no lo admite) — ver §3.
  > "Panel Pedagógico → Resumen" y "Modo Evidencia → Dashboard del
  > Investigador" muestran las mismas cifras agregadas en dos rutas con
  > layouts distintos — razonable si son audiencias distintas, vale la
  > pena confirmar que es intencional.
  >
  > **13 — Código innecesario.** El trío `routes/traces.py` +
  > `models/agent_decision_trace.py` + `observability/trace_store.py`,
  > sin productor, es funcionalidad muerta que sigue compilando y
  > respondiendo peticiones — el candidato más claro para retiro
  > físico, mismo criterio que ADR-0011.

  Más las 6 "Observaciones registradas" del documento de consolidación
  de la propia remediación (`AUDIT-2026-08-05_REMEDIATION_STATUS.md`),
  registradas como hallazgos colaterales durante Fichas 04/07/08 pero
  nunca elevadas a su propia investigación.

---

## Verificación de cada candidato — con evidencia fresca, no reciclada

### 1. §13 — Trío `traces.py`/`agent_decision_trace.py`/`trace_store.py`: CONFIRMADO YA RESUELTO

```
find backend/app -iname "traces.py" -o -iname "agent_decision_trace.py" -o -iname "trace_store.py"
→ (sin resultados)
```

Ficha 04 (commit `ab3860b`) ya lo eliminó físicamente. **No pasa a
Paso 2** — cerrado, sin acción pendiente.

### 2. Residuo de Ficha 04 — `app/schemas/decision_trace.py`: CONFIRMADO huérfano

```
find backend/app -iname "decision_trace.py"  → backend/app/schemas/decision_trace.py (336 líneas)
grep -rl "decision_trace" backend/app --include=*.py  → solo el propio archivo
```

Cero importadores en todo `backend/app`. Ya estaba registrado como
observación #2 de la consolidación de Fichas 01-08 ("candidato a un
futuro retiro") — confirmado con evidencia fresca, sigue siendo cierto
hoy.

### 3. Residuo de Ficha 04 — tabla `agent_decision_traces` en Postgres: CONFIRMADO, 0 filas

Consulta real (solo lectura, Postgres real `upao_mas_edu`):

```sql
SELECT COUNT(*) FROM agent_decision_traces;  → 0
```

Sigue existiendo, sigue vacía, mismo criterio que ADR-0011 (que tampoco
hizo `DROP TABLE` al retirar BaseAgent/SwarmOrchestrator) — ya
registrado como observación #3, confirmado vigente.

### 4. Residuo de Ficha 08 — `dropdown-menu.tsx` custom vs. `@radix-ui/react-dropdown-menu`: CONFIRMADO

```
grep "@radix-ui/react-dropdown-menu" frontend/package.json
  → "@radix-ui/react-dropdown-menu": "^2.1.16"   (declarada, instalada)
grep -rl "@radix-ui/react-dropdown-menu" frontend/src
  → (sin resultados — cero imports en todo el frontend)
```

La dependencia real de Radix está instalada y pagada (bundle size,
`node_modules`) pero nunca importada; `components/ui/dropdown-menu.tsx`
es una reimplementación propia completa del mismo patrón. Ya registrado
como observación #5, confirmado vigente.

### 5. §12a — Gap del enum de roles en `UserForm.tsx`: CONFIRMADO, sin cambios desde Ficha 07

```tsx
// UserForm.tsx:18-20
// 'investigador' no se ofrece en el selector (rol legado); queda en el
// esquema...
role: z.enum(['admin', 'docente', 'estudiante', 'investigador']),
// línea 124:
{role === 'investigador' && <SelectItem value="investigador">Investigador (le...
```

El tipo central `UserRole` del frontend (`types/auth.ts:28`) **ya**
incluye `'investigador'` — el enum en sí no está desincronizado como
temía la auditoría original. El gap real es más específico: el
`SelectItem` de "Investigador" en `UserForm.tsx` solo se renderiza
`{role === 'investigador' && ...}` — es decir, **solo visible si el
usuario editado YA es investigador**; nunca aparece como opción al
crear un usuario nuevo o reasignar un rol distinto. `Roles.tsx` (Ficha
07, commit `dd2b166`) sí lo ofrece siempre, sin condición. Confirmado
como observación #1, vigente, con la causa raíz más precisa que la
auditoría original arriesgó ("enum duplicado") — no es un enum
desincronizado, es una condición de renderizado asimétrica entre dos
componentes que deberían comportarse igual.

### 6. §12b — "Panel Pedagógico → Resumen" vs. "Modo Evidencia → Dashboard del Investigador": NO investigado a fondo

Ubicados: `frontend/src/pages/docente/panel/ResumenTab.tsx` (Panel
Pedagógico) y `frontend/src/pages/evidencia/ResearchDashboard.tsx`
(candidato más probable para "Dashboard del Investigador" dentro de
Modo Evidencia — `EvidenceHub.tsx` es el contenedor). **No se comparó
línea a línea si muestran exactamente las mismas cifras** — la propia
auditoría original ya marcó esto como "razonable si son audiencias
distintas, vale la pena confirmar" (no como un defecto). Queda como
pregunta abierta, no como hallazgo confirmado — requeriría una
comparación visual/de datos que este Paso 1 no alcanzó a hacer.

### 7. Barrido adicional — TODOs/FIXMEs reales (descontando falsos positivos del español "TODO"=/"todo/a"/)

Backend (`backend/app`, excluyendo tests): 2 marcadores reales de 4
coincidencias (2 son la palabra española "todo/a", no marcadores):

- `app/memory/shared_memory.py:92` — `TODO: implement async-compatible
  dedup (Phase 2)`. Sin ficha propia, no investigado en este documento.
- `app/services/student_service.py:318` — `TODO(Sprint 1 — Misión
  Activa, registrado 2026-07-06): este GET aprovisiona...` — deuda ya
  conocida y registrada en memoria de proyecto
  (`sprint1_mision_activa_state.md`), no es un hallazgo nuevo.

Frontend (`frontend/src`): 1 marcador real de 4 coincidencias (3 son la
palabra española "todo/a"):

- `frontend/src/types/trace.ts:345` — `TODO: if replay / multi-run is
  added, prefer the trace with highest sequence.` Archivo **no**
  huérfano (usado por `AgentThoughtStream.tsx`, `AgentDebateBubbles.tsx`,
  `RealTraceTimeline.tsx` — parte viva de Modo Evidencia/RFC-0007, no
  relacionado con el trío ya retirado de Ficha 04 pese al nombre
  similar).

### 8. Rutas huérfanas mencionadas en `CLAUDE.md` (actualización 2026-07-12): CONFIRMADO ya no existen

`CLAUDE.md` documenta históricamente `sessions.py`, `orchestration.py`,
`observability.py` como "rutas nunca registradas en `main.py`... código
huérfano, no un camino en vivo". Verificado con `find` en esta sesión:
ninguno de los tres archivos existe ya en `backend/app/api/routes/` —
limpieza ya completada en algún punto posterior (probablemente ADR-0011
u otra limpieza no documentada explícitamente como tal). **No pasa a
Paso 2** — ya resuelto.

---

## Resumen del inventario

| # | Candidato | Estado de verificación | ¿Nuevo o ya conocido? |
|---|---|---|---|
| 1 | Trío `traces.py`+`agent_decision_trace.py`+`trace_store.py` | Ya resuelto (Ficha 04) | Conocido — cerrado |
| 2 | `app/schemas/decision_trace.py` huérfano | Confirmado, 336 líneas, 0 importadores | Conocido (obs. #2), reconfirmado |
| 3 | Tabla `agent_decision_traces` (0 filas) | Confirmado con consulta real | Conocido (obs. #3), reconfirmado |
| 4 | `dropdown-menu.tsx` custom vs. Radix instalado sin usar | Confirmado, 0 imports de la librería real | Conocido (obs. #5), reconfirmado |
| 5 | Gap de "Investigador" en `UserForm.tsx` | Confirmado, causa raíz más precisa que la auditoría original | Conocido (obs. #1), reconfirmado y refinado |
| 6 | Posible duplicación Panel Pedagógico / Modo Evidencia | Ubicado, no comparado a fondo | De la auditoría original (§12b), sin cerrar |
| 7 | 2 TODOs reales backend + 1 frontend | Localizados, sin ficha propia previa | **Nuevo** (barrido de este documento) |
| 8 | Rutas huérfanas `sessions.py`/`orchestration.py`/`observability.py` | Confirmado ya no existen | Conocido (`CLAUDE.md`) — cerrado |

**4 candidatos identificados para Paso 2** (2, 3, 4, 5). La inspección
inicial proporciona una hipótesis fuerte sobre su causa en cada caso,
que deberá confirmarse mediante el mismo proceso de verificación
aplicado en las sesiones anteriores (¿es API pública? ¿lo referencia
documentación? ¿lo cargan tests dinámicamente? ¿hay imports indirectos?
¿existe un feature flag o migración pendiente detrás?) antes de
clasificar cualquiera de ellos como defecto o código muerto — "cero
importadores hoy" o "cero filas hoy" todavía no demuestra "muerto",
solo "no usado en este momento". **1 candidato requiere más trabajo
antes de clasificar** (6). **3 quedan cerrados sin acción** (1, 7
parcialmente — quedan registrados pero sin ficha, 8).

## Estado al cierre de este Paso 1

Ningún archivo de código modificado. El siguiente paso natural es
Paso 2: verificar cada uno de los 4 candidatos con el mismo rigor que
Ficha 05/09/Rendimiento — no asumir "código muerto" a partir de una
sola señal (ausencia de importadores, tabla vacía) sin descartar antes
las explicaciones alternativas (feature flag, carga dinámica,
observabilidad futura, referencia externa). Recién con eso clasificar
cada uno como defecto / deuda aceptada deliberadamente / mejora
opcional, antes de decidir cuáles retirar.
