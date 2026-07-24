# Engineering Gate — Épica B: `input()` interactivo real

> Planifica la implementación. No es todavía código — el Engineering
> Gate se cierra cuando este documento queda aprobado, recién ahí
> empieza el primer commit de implementación (uno por responsabilidad
> arquitectónica, disciplina de "Cambios pequeños" de `CLAUDE.md`).

- **Fecha:** 2026-07-24
- **Documento propietario:** ninguno previo — hoja en blanco
  arquitectónica confirmada en `AUDITORIA-EPICA-B.md` §5 ("Ninguna
  decisión arquitectónica previa que limite esta evolución"). Esta
  cadena de documentos (auditoría → spikes → checkpoint) ES el
  propietario, sustituyendo al RFC/ADR que en otras áreas del proyecto
  ya existía antes de implementar.

---

## 1. Objetivo

Implementar `input()` interactivo real en el laboratorio de
programación del estudiante, usando la arquitectura que
`SPIKE-B1-PYODIDE-WORKER-STDIN.md` verificó con código real: Worker +
`SharedArrayBuffer` + `Atomics.wait()`. Reemplaza (total o
parcialmente — ver §5, decisión abierta) el mecanismo actual de
`simulatedInputs` (cola FIFO precargada por el autor del contenido,
`AUDITORIA-EPICA-B.md` §2) por un flujo donde el estudiante escribe el
valor en el momento real en que Python lo pide.

## 2. Alcance

**Entra:**
- Worker dedicado que carga Pyodide (reemplaza la carga en el hilo
  principal de `usePyodide.ts`).
- Protocolo de `stdin` real vía `Atomics.wait()` (mismo patrón
  validado en el spike).
- Adaptación de `usePyodide.ts` (o hook nuevo con el mismo contrato
  público `{ ready, loadError, run }` que ya consume
  `PythonBridge.tsx`, para que el resto del componente no tenga que
  reescribirse).
- UI en `PythonBridge.tsx` para que el estudiante escriba el valor
  cuando Python lo pide en vivo (nueva; coexiste o reemplaza el panel
  actual "Simularemos que el usuario escribe" — ver §5).
- Soporte para múltiples `input()` consecutivos en la misma etapa
  (confirmado viable por el spike con 2 y 3 llamadas).
- Cabeceras `COOP`/`COEP` en el Vite dev server del proyecto real
  (el spike las sirvió con un servidor Node aislado, no con Vite).
- Auditoría de recursos cross-origin del resto del frontend bajo
  `COEP: require-corp` (riesgo residual del spike, ahora entra al
  alcance en vez de quedar pendiente).

**No entra (expresamente fuera):**
- Sandbox Docker (decisión ya tomada en `CHECKPOINT-EPICA-B.md` §1).
- Refactor general del laboratorio más allá de lo que este cambio
  exige — el Sprint 1A (visual, commits `043fbaa`..`91c7949`) ya cerró
  la modernización visual; no se reabre aquí.
- Cambios pedagógicos al contenido de `ciclo3-input.ts` u otros ciclos
  más allá de lo estrictamente necesario para que sigan funcionando.
- El hallazgo de seguridad del sandbox sin autenticación
  (`CHECKPOINT-EPICA-B.md` §3 — mini-épica aparte).
- Compatibilidad verificada en Firefox/Safari reales (riesgo residual
  documentado, se trata después si aparece necesidad real).

## 3. Dependencias

No se reexplican — se citan:
- `AUDITORIA-EPICA-B.md` (estado real del código antes de esta épica).
- `SPIKE-B0-PYODIDE-STDIN.md` (viabilidad documental, dos vías).
- `CHECKPOINT-EPICA-B.md` (las 4 decisiones del tesista).
- `SPIKE-B1-PYODIDE-WORKER-STDIN.md` (viabilidad empírica, reproducida,
  riesgos residuales).

## 4. Riesgos residuales (heredados del Spike B-1, aún sin resolver)

| Riesgo | Estado |
|---|---|
| Compatibilidad de COOP/COEP con el resto de recursos cross-origin del frontend | Entra al alcance de esta épica (§2) |
| Compatibilidad en Firefox/Safari reales | Fuera de alcance por ahora |
| Impacto sobre el hosting de producción (Render.com) | Entra al alcance — commit dedicado (§5) |
| Integración real con `usePyodide.ts` y `PythonBridge.tsx` | Entra al alcance — es el objetivo mismo de esta épica |
| UX para `input()` cancelado o abandonado a mitad de espera | Entra al alcance — decisión de diseño dentro del plan (§5, Commit 4) |

## 5. Decisión abierta previa al Commit 1 (no asumida en este documento)

**¿Qué pasa con `simulatedInputs`?** El tipo `PythonMicroPracticeDef`
(`moduleExperience.ts:303`) ya lo declara opcional. Tres caminos
posibles, sin decidir aquí cuál:
- (a) Coexistencia: `simulatedInputs` presente conserva el
  comportamiento actual (compatibilidad total con el contenido
  autorado hoy — `ciclo3-input.ts` y cualquier otro ciclo con
  `input()`); su ausencia en una etapa que use `input()` activa el
  mecanismo nuevo.
- (b) Reemplazo total: se retira `simulatedInputs` y se re-autora todo
  el contenido existente para el mecanismo nuevo.
- (c) Mecanismo nuevo como *fallback* explícito activable, sin tocar
  contenido existente, autorando solo casos nuevos con él.

Recomendación (no decisión): (a) — es la que menos contenido rompe y
la que permite un rollback trivial por etapa si algo falla en
producción. Corresponde al tesista confirmarla antes de abrir el
Commit 1.

## 6. Estrategia de implementación (commits pequeños, un cambio por responsabilidad)

```
Commit 1 — Worker runtime aislado
  Nuevo script de Worker (pyodideWorker.ts) que carga Pyodide 0.26.2
  y expone el protocolo de mensajes (init/run/need-input/result),
  sin conectarlo a nada del árbol de componentes todavía.
  Verificable: build limpia, sin comportamiento visible nuevo.

Commit 2 — usePyodide.ts adaptado al Worker
  Mismo contrato público { ready, loadError, run } — el motor interno
  cambia (Worker + SharedArrayBuffer), los consumidores no se tocan.
  Verificable: mismas pruebas/comportamiento que hoy con
  simulatedInputs (regresión cero).

Commit 3 — Protocolo de stdin real (Atomics.wait)
  La función que expone el hook para que el consumidor entregue el
  valor cuando el estudiante lo escribe (reemplaza/complementa el
  consumo FIFO de simulatedInputs, según la decisión de §5).

Commit 4 — UI de solicitud de entrada real en PythonBridge.tsx
  El campo donde el estudiante escribe el valor cuando Python lo pide
  EN VIVO. Incluye la decisión de UX de cancelación (§4).

Commit 5 — Cabeceras COOP/COEP en Vite dev + auditoría cross-origin
  vite.config.ts (dev) + verificación de qué recursos externos del
  frontend rompen bajo COEP:require-corp (fuentes, iconos, etc.).

Commit 6 — E2E real sobre ciclo3-input.ts
  Recorrido en navegador real (Regla de Cierre del proyecto) — no
  alcanza con que compile ni con que pasen tests.
```

No es la secuencia final obligatoria — es la propuesta a validar
contra el código real al empezar el Commit 1 (Engineering Gate por
commit sigue vigente, `CLAUDE.md`: 4 preguntas antes de cada uno).

## 7. Criterios de salida

El Gate se considera cerrado (la épica, completa) solo si:
- `ciclo3-input.ts` funciona con `input()` real en navegador real, no
  simulación.
- Múltiples `input()` consecutivos en la misma etapa funcionan
  (confirmado viable por el spike, falta confirmarlo en la app real).
- Sin regresiones del laboratorio existente (las demás microprácticas
  del proyecto siguen funcionando igual).
- QA manual real (Regla de Cierre — navegador real, no solo build).
- Build limpia (`tsc`, `vite build`).
- Documentación actualizada (este documento + los que correspondan).
