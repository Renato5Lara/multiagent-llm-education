# Sesión 5, Frente B — Paso 2: Verificación de los 4 candidatos

## Metadata

- **Fecha:** 2026-08-05
- **Rama:** `investigacion/sesion5-rendimiento`
- **Protocolo:** observar → medir → **verificar** → clasificar →
  decidir → implementar. Este documento verifica los 4 candidatos de
  Paso 1 con el mismo rigor que Ficha 05/09/Rendimiento — "cero
  importadores hoy" o "cero filas hoy" no demuestra "muerto" sin antes
  descartar explicaciones alternativas. **Ningún archivo de código
  modificado.**
- **Orden y preguntas, tal como se pidieron explícitamente:**
  1. `decision_trace.py` — ¿API pública? ¿documentación? ¿tests
     dinámicos? ¿imports indirectos?
  2. `agent_decision_traces` — ¿deshabilitada? ¿feature flag?
     ¿migración pendiente? ¿observabilidad futura?
  3. `dropdown-menu.tsx` — ¿sin imports, sin rutas, sin consumidores?
  4. Gap de Investigador — confirmar la causa raíz refinada de Paso 1.

---

## 1. `app/schemas/decision_trace.py` — confirmado código muerto, con un hallazgo colateral mayor

### Las 4 preguntas, respondidas

- **¿Era una API pública?** No. Ningún router lo importa (el único que
  lo usaba, `routes/traces.py`, ya fue eliminado en Ficha 04). Nunca
  estuvo expuesto vía HTTP tras esa eliminación.
- **¿Lo referencia documentación?** **Sí — pero no a este archivo
  específico.** El propio docstring del schema dice textualmente:
  *"Stored in `result['_decision_trace']` by `BaseAgent.run()` and
  persisted to `agent_decision_traces` table by `TraceStore`"* — ambos,
  `BaseAgent` y `TraceStore`, ya no existen (retirados por ADR-0011). Y
  **el documento técnico oficial de la tesis** (`docs/tddr/
  TDDR_UPAO-MAS-EDU.md:229`) todavía cita `AgentDecisionTraceRecord`
  (el modelo SQLAlchemy hermano, `models/agent_decision_trace.py`, ya
  eliminado también por Ficha 04) como evidencia concreta del
  requisito no funcional "Auditabilidad":

  > | Auditabilidad | Registro verificable de acciones y decisiones |
  > `AuditLog`, `AgentDecisionTraceRecord`, cadena de hash (ADR-0001) |

  El diagrama de entidad-relación de la tesis (`docs/tddr/
  fig3_modelo_er.svg:107-109`) **también** dibuja `agent_decision_traces`
  como tabla del modelo de datos vigente.

  **Esto no es un hallazgo sobre `decision_trace.py`** (el archivo en
  sí no está citado por nombre en ningún lado) — es un hallazgo sobre
  su **hermano ya eliminado** (`models/agent_decision_trace.py`,
  Ficha 04): su retiro dejó dos referencias obsoletas en el documento
  oficial de la tesis que nadie corrigió, porque Ficha 04 nunca revisó
  `docs/tddr/` antes de eliminar. Encontrado únicamente porque este
  Paso 2 preguntó "¿lo referencia documentación?" en vez de asumir que
  "cero importadores en el código" bastaba.
- **¿Hay tests que lo carguen dinámicamente?** No — `grep` en
  `backend/tests/` no encuentra ninguna referencia a `decision_trace`
  ni a `AgentDecisionTrace`.
- **¿Hay imports indirectos?** No — `app/schemas/__init__.py` está
  vacío (19 bytes, un comentario), sin re-exports; se verificaron todos
  los usos de `importlib`/`__import__` del backend y ninguno se
  relaciona con este archivo.

### Clasificación

`app/schemas/decision_trace.py` (336 líneas): **código muerto
confirmado**, sin ninguna de las 4 salvedades pedidas. Su eliminación
es segura en sí misma. **Pero no debe cerrarse como un ítem aislado**
— el hallazgo real y de mayor prioridad es la **desactualización del
documento técnico de la tesis** (`TDDR_UPAO-MAS-EDU.md` + `fig3_modelo_
er.svg`), que sigue citando una clase que Ficha 04 ya eliminó hace
varios commits. Corregir solo el código sin corregir la tesis dejaría
la inconsistencia intacta donde más importa.

---

## 2. Tabla `agent_decision_traces` — confirmado infraestructura huérfana, no reservada

### Las 4 preguntas, respondidas

- **¿Está deshabilitada (feature flag)?** No se encontró ningún flag —
  `grep` de `AGENT_DECISION_TRACE`/variantes contra `backend/app` y los
  archivos `.env*` no arroja resultados.
- **¿Existe una migración pendiente?** No — el head actual de Alembic
  aplicado contra Postgres real es `f3a4b5c6d7e8`; la migración que
  crea esta tabla (`c3d4e5f6a7b8_add_agent_decision_traces.py`) es un
  ancestro ya aplicado, no una migración pendiente de correr.
- **¿Es para observabilidad futura (RFC-0007)?** **No** — se leyó
  `docs/architecture/RFC-0007-observabilidad.md` completo por este
  término: cero menciones de `agent_decision_trace`/`AgentDecisionTrace`.
  La observabilidad que RFC-0007 sí implementó y que hoy está en vivo
  (Runtime Console, Plataforma 3) usa un modelo de datos
  **completamente distinto** (`runtime_transitions`, `runtime_sessions`,
  `runtime_blobs` — event-sourced, verificado existente en Postgres real
  en esta misma sesión) — no reutiliza ni depende de
  `agent_decision_traces` en absoluto. La necesidad de observabilidad
  futura ya fue cubierta por otro sistema; esta tabla no es una reserva
  para ella.

### Clasificación

**Infraestructura actualmente no utilizada, sin ninguna razón activa
encontrada para conservarla como "reservada".** No es simplemente
"cero filas hoy" — es cero filas, sin escritor posible (su único
escritor, `TraceStore`, ya no existe), sin flag que la reactive, sin
migración pendiente, y con su rol de observabilidad ya cubierto por un
sistema distinto y ya en producción. La clasificación correcta, tal
como pediste, no es todavía "muerta" sin más contexto — pero con las 4
preguntas respondidas, el contexto no deja ninguna razón activa para
conservarla: **candidato sólido para retiro físico**, mismo criterio
que ya se aplicó (sin ejecutar `DROP TABLE`) al resto de tablas
retiradas por ADR-0011.

---

## 3. `dropdown-menu.tsx` — el archivo NO es el candidato; la dependencia sí

### Verificación (sin imports, sin rutas, sin consumidores — la condición exacta pedida)

```
grep -rl "dropdown-menu|DropdownMenu" frontend/src (excluyendo el propio archivo)
  → frontend/src/components/common/UserDropdown.tsx
  → frontend/src/pages/admin/Users.tsx
```

**El componente `dropdown-menu.tsx` SÍ tiene consumidores reales (2)** —
no cumple la condición de "sin imports, sin rutas, sin consumidores"
que harían de él un candidato de limpieza. Precisión importante sobre
el propio Paso 1: el candidato de deuda técnica nunca fue el archivo
en sí, sino la dependencia declarada y no usada:

```
package.json:18  → "@radix-ui/react-dropdown-menu": "^2.1.16"
grep -rl "@radix-ui/react-dropdown-menu" frontend/src → (sin resultados)
components.json (config de shadcn/ui) → sin mención de dropdown-menu
```

### Clasificación

`@radix-ui/react-dropdown-menu` (la dependencia de `package.json`, NO
el archivo `dropdown-menu.tsx`): **confirmado candidato limpio de
limpieza** — instalada, pagada en el bundle/lockfile, sin ningún
importador real ni siquiera indirecto vía configuración de shadcn/ui.
El componente `dropdown-menu.tsx` permanece intacto — es código vivo,
no debe tocarse en ninguna limpieza de este frente.

---

## 4. Gap de "Investigador" — revisión mayor: no es un gap, es una contradicción sin resolver

### Lo que Paso 1 no había leído todavía: el comentario completo de `UserForm.tsx`

```ts
// 'investigador' no se ofrece en el selector (rol legado); queda en el
// schema para que editar un usuario existente con ese rol no lo reasigne.
role: z.enum(['admin', 'docente', 'estudiante', 'investigador']),
```

Esto **no es un descuido** — es una decisión documentada, textual,
alineada con `models/user.py:21-22` (`UserRole.INVESTIGADOR`):

```python
# Legado: retirado como usuario de negocio (las herramientas viven en el
# Modo Evidencia). Se conserva por compatibilidad con filas existentes.
INVESTIGADOR = "investigador"
```

**`UserForm.tsx` implementa exactamente lo que el modelo documenta:**
Investigador es un rol retirado, que no debería asignarse a usuarios
nuevos — solo se preserva para no romper filas existentes.

### El contraste — `Roles.tsx` (Ficha 07, commit `dd2b166`) contradice esto directamente

```tsx
<SelectItem value="admin">Administrador</SelectItem>
<SelectItem value="docente">Docente</SelectItem>
<SelectItem value="estudiante">Estudiante</SelectItem>
<SelectItem value="investigador">Investigador</SelectItem>
```

Sin ninguna condición, sin ningún comentario — `Roles.tsx` ofrece
"Investigador" como destino de reasignación para **cualquier** usuario,
en cualquier momento, contradiciendo directamente la intención
documentada en `UserForm.tsx`/`models/user.py`.

### Reclasificación (cambia respecto a Paso 1)

Paso 1 describió esto como "condición de renderizado asimétrica" —
implicando que `UserForm.tsx` tenía el defecto y `Roles.tsx` tenía el
comportamiento correcto (mismo marco que la propia Ficha 07 asumió al
"corregir" el selector vacío). **Con el comentario completo leído, la
lectura correcta es la opuesta, o al menos no es obvia sin una
decisión del tesista:** `UserForm.tsx` es el que sigue la arquitectura
documentada; **`Roles.tsx` es el que podría estar equivocado.**

Esto no se resuelve en este documento — es exactamente el tipo de
contradicción que requiere una decisión explícita, no una corrección
automática:

- **Opción A:** Investigador nunca debe ser asignable desde ninguna UI
  de administración — `Roles.tsx` debería restringirse igual que
  `UserForm.tsx` (revertir parte de Ficha 07).
- **Opción B:** Investigador sí debe ser asignable (la intención
  original de Ficha 07 era correcta) — el comentario de `UserForm.tsx`
  y la nota de `models/user.py` deberían actualizarse para reflejar
  que ya no es un rol puramente heredado.

**No se decide aquí cuál es correcta.**

---

## Resumen de clasificación (Paso 3 pendiente de apertura)

| # | Candidato | Clasificación tras verificación | Acción propuesta (sin decidir) |
|---|---|---|---|
| 1a | `app/schemas/decision_trace.py` | Código muerto confirmado, sin salvedades | Candidato de retiro físico |
| 1b | **`TDDR_UPAO-MAS-EDU.md` + `fig3_modelo_er.svg`** (hallazgo colateral, mayor prioridad) | Documentación de tesis desactualizada — cita una clase ya eliminada | Requiere corrección de la tesis, no solo del código |
| 2 | Tabla `agent_decision_traces` | Infraestructura huérfana confirmada, sin flag/migración/reserva de RFC-0007 | Candidato de retiro físico (mismo criterio que ADR-0011) |
| 3 | `dropdown-menu.tsx` (archivo) | **No es candidato** — código vivo, 2 consumidores reales | Ninguna — no tocar |
| 3b | `@radix-ui/react-dropdown-menu` (dependencia) | Confirmado sin uso, ni directo ni indirecto | Candidato de limpieza de `package.json` |
| 4 | Gap/contradicción de "Investigador" | **No es deuda técnica simple — es una contradicción arquitectónica sin resolver entre dos componentes** | Requiere decisión del tesista (Opción A vs B) antes de tocar cualquiera de los dos archivos |

## Estado al cierre de Paso 2

Ningún archivo de código modificado. El resultado más importante de
este paso no estaba en el inventario original de Paso 1: la
desactualización del documento de tesis (ítem 1b) y la contradicción
arquitectónica sobre "Investigador" (ítem 4) — ninguno de los dos se
habría encontrado sin aplicar exactamente las preguntas que pediste
antes de clasificar. Paso 3 (clasificación final para decidir) queda
pendiente de apertura explícita.
