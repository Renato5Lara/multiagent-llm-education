# Sesión 5, Frente B — Paso 3: Clasificación final

## Metadata

- **Fecha:** 2026-08-05
- **Rama:** `investigacion/sesion5-rendimiento`
- **Protocolo:** observar → medir → verificar → **clasificar** →
  decidir → implementar. Este documento clasifica cada candidato de
  Paso 2 en una categoría final. **No se implementa ni se decide nada
  todavía** — la categoría "contradicción arquitectónica/documental" se
  mantiene deliberadamente separada de "defecto" hasta que exista una
  decisión explícita sobre cuál fuente es la vigente.

---

## Clasificación

### Categoría: Código muerto confirmado

**`app/schemas/decision_trace.py`** (336 líneas). Las 4 salvedades
posibles (API pública, documentación, tests dinámicos, imports
indirectos) se descartaron una por una en Paso 2 — ninguna aplica al
archivo en sí. Candidato limpio de retiro físico, mismo criterio que
ADR-0011 (Fichas 04/anteriores).

### Categoría: Documentación de tesis desactualizada (distinta de código muerto)

**`docs/tddr/TDDR_UPAO-MAS-EDU.md`** (tabla de NFR "Auditabilidad",
línea 229) y **`docs/tddr/fig3_modelo_er.svg`** (entidad
`agent_decision_traces` dibujada como vigente). Ambos citan
`AgentDecisionTraceRecord`, clase ya eliminada por Ficha 04. **No es
"código muerto"** — es documentación desalineada con el estado real
del código, con mayor impacto que el ítem anterior porque es
justamente el documento que un jurado revisaría para verificar
trazabilidad y auditabilidad del sistema. Se clasifica aparte porque su
remediación no es "borrar" sino "corregir texto/diagrama" — una
responsabilidad distinta, candidata a su propio commit si se decide
remediar.

### Categoría: Infraestructura huérfana

**Tabla `agent_decision_traces`** (Postgres, 0 filas). Las 4 preguntas
de descarte (deshabilitada por flag, migración pendiente, reservada
por RFC-0007) se respondieron todas negativamente con evidencia directa
en Paso 2 — sin escritor posible (su único escritor, `TraceStore`, no
existe), sin ninguna razón activa para conservarla como reserva.
Candidato de retiro físico, mismo criterio que el resto de tablas ya
retiradas por ADR-0011 (sin `DROP TABLE` hasta que se decida
explícitamente, siguiendo el mismo patrón conservador ya usado).

### Categoría: Dependencia sin uso

**`@radix-ui/react-dropdown-menu`** (`package.json:18`). Confirmado sin
ningún importador, directo ni indirecto (ni siquiera vía configuración
de shadcn/ui). El componente `dropdown-menu.tsx` que hace el mismo
trabajo a mano **no es parte de esta categoría** — es código vivo,
excluido explícitamente de cualquier remediación de este frente.

### Categoría: Contradicción arquitectónica/documental — deliberadamente NO clasificada como defecto

**El rol "Investigador" en `UserForm.tsx` vs. `Roles.tsx`.** Dos
fuentes documentadas se contradicen:

- `UserForm.tsx` (comentario textual) + `models/user.py`
  (`UserRole.INVESTIGADOR`, docstring "Legado: retirado como usuario de
  negocio... se conserva por compatibilidad") → Investigador **no**
  debe ofrecerse para asignación nueva.
- `Roles.tsx` (Ficha 07, commit `dd2b166`) → Investigador **sí** se
  ofrece, sin condición, para cualquier reasignación.

**Pregunta de arquitectura pendiente, tal como se planteó:** ¿cuál de
las dos fuentes representa la decisión vigente?

- Si Investigador sigue siendo legado → `Roles.tsx` está desalineado,
  candidato a restringir (revertir parcialmente el alcance de Ficha
  07).
- Si Investigador volvió a ser un rol asignable activamente → el
  comentario de `UserForm.tsx` y el docstring de `models/user.py`
  quedaron obsoletos, candidatos a actualizar (y probablemente el
  propio `SelectItem` condicional de `UserForm.tsx` debería volverse
  incondicional, igualándose a `Roles.tsx`).

**Esta categoría se mantiene fuera de "defecto" a propósito.**
Clasificarla como bug forzaría una corrección de código antes de que
exista la decisión de diseño que la corrección necesita para saber en
qué dirección corregir — exactamente el riesgo que se pidió evitar.

---

## Tabla de clasificación

| Candidato | Categoría final | ¿Lista para Paso 4 (decidir remediación)? |
|---|---|---|
| `app/schemas/decision_trace.py` | Código muerto confirmado | Sí — remediación de bajo riesgo (retiro) |
| `TDDR_UPAO-MAS-EDU.md` + `fig3_modelo_er.svg` | Documentación de tesis desactualizada | Sí — remediación de bajo riesgo (corrección de texto/diagrama), pero de mayor impacto que el ítem anterior |
| Tabla `agent_decision_traces` | Infraestructura huérfana | Sí — remediación de bajo riesgo (retiro físico, mismo criterio ADR-0011) |
| `@radix-ui/react-dropdown-menu` | Dependencia sin uso | Sí — remediación de bajo riesgo (quitar de `package.json`) |
| Rol "Investigador" (`UserForm.tsx` vs. `Roles.tsx`) | Contradicción arquitectónica/documental | **No** — requiere decisión de diseño del tesista antes de proponer cualquier cambio de código |

---

## Estado al cierre de Paso 3

Ningún archivo de código modificado. 4 de 5 candidatos quedan listos
para Paso 4 con remediaciones de bajo riesgo, bien acotadas y
verificadas. El quinto (Investigador) requiere una respuesta a la
pregunta de arquitectura antes de que exista algo que decidir en
términos de implementación — Paso 4, si se abre, debe tratarlo aparte
del resto.
