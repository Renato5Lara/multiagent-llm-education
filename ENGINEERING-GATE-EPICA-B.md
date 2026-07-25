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

**Invariante del runtime, añadido durante el Commit 2 (no es un riesgo
a resolver — es una restricción de diseño aceptada explícitamente):**
mientras no exista un protocolo con correlación de mensajes por id, el
Worker (`pyodideWorker.ts`) admite una única ejecución activa a la
vez. Hoy lo garantiza la UI real (`PythonBridge.tsx` deshabilita
"Ejecutar" mientras `running` es true), no el hook. Reutilizar este
Worker para ejecuciones concurrentes requiere diseñar esa correlación
primero — no se asume disponible en ningún commit de esta épica.

## 5. Decisión tomada: coexistencia (opción a)

**Qué pasa con `simulatedInputs`:** el tipo `PythonMicroPracticeDef`
(`moduleExperience.ts:303`) ya lo declara opcional — el tesista
confirmó coexistencia con migración progresiva, no reemplazo total ni
fallback aparte. Razón registrada: mínimo cambio necesario para
validar la capacidad nueva sin romper contenido existente; riesgo de
regresión mínimo (solo migran las etapas que lo decidan
explícitamente); rollback trivial por etapa durante una mini-épica
todavía experimental; permite migración módulo por módulo en vez de
una migración masiva de una sola vez.

**Contrato de compatibilidad (obligatorio para el Commit 2 en
adelante):**

```
Si simulatedInputs existe en la etapa → usar simulatedInputs (legado).
Si simulatedInputs NO existe en la etapa → usar stdin interactivo (Worker+Atomics).

Nunca ambos mecanismos activos para la misma ejecución — la selección
es automática y mutuamente excluyente, no una preferencia configurable.
```

Esto es un contrato, no una sugerencia — cualquier implementación que
permita ambigüedad (p. ej. `simulatedInputs` presente pero el código
también dispara el flujo interactivo) rompe el Engineering Gate de ese
commit.

**Próximo paso, cuando corresponda (fuera del alcance de esta épica):**
una vez que el mecanismo esté estabilizado y validado con varios
recorridos E2E reales, retirar `simulatedInputs` es una mini-épica
aparte — no se decide ni se ejecuta aquí.

## 6. Estrategia de implementación (commits pequeños, un cambio por responsabilidad)

```
Commit 1 — Worker runtime aislado
  Nuevo script de Worker (pyodideWorker.ts) que carga Pyodide 0.26.2
  y expone el protocolo de mensajes (init/run/need-input/result),
  sin conectarlo a nada del árbol de componentes todavía.
  Verificable: build limpia, sin comportamiento visible nuevo.

Commit 2 — usePyodide.ts adaptado al Worker
  Mismo contrato público { ready, loadError, run } en forma — el motor
  interno cambia (Worker + SharedArrayBuffer). Verificable: mismo
  comportamiento que hoy con simulatedInputs (regresión cero).

  EXCEPCIÓN DE ALCANCE (descubierta al planificar el Commit 2, no
  anticipada al escribir este Gate): postMessage es inherentemente
  asíncrono, así que run() pasa de PythonRunResult síncrono a
  Promise<PythonRunResult> — no es una decisión de diseño, es
  consecuencia obligada de comunicarse con un Worker (mantenerlo
  síncrono exigiría Atomics.wait() en el hilo principal, exactamente
  el bloqueo de pestaña que el Worker existe para evitar). Esto rompe
  la compilación de PythonBridge.tsx:handleRun() si no se ajusta, así
  que el Commit 2 incluye un ajuste MECÁNICO ahí: handleRun async +
  await run(...), nada más — cero UI nueva, cero estado nuevo, mismo
  comportamiento observable exacto. El panel de input() real (Commit
  4) sigue intacto y sin tocar.

Commit 3 — Protocolo de stdin real (Atomics.wait)
  La función que expone el hook para que el consumidor entregue el
  valor cuando el estudiante lo escribe — coexiste con el consumo FIFO
  de simulatedInputs sin reemplazarlo (contrato de compatibilidad
  §5: mutuamente excluyentes por etapa, nunca ambos a la vez).

Commit 4 — UI de solicitud de entrada real en PythonBridge.tsx
  El campo donde el estudiante escribe el valor cuando Python lo pide
  EN VIVO. CERRADO sin cancelación (decisión de alcance confirmada
  antes de codear: terminar el Worker compartido no es una decisión de
  UI, es ciclo de vida del runtime — ver Commit 4b, §7).

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

## 7. Commit 4b — Cancelación de una ejecución en curso

> Gate propio, separado del Commit 4 (confirmado antes de codear):
> terminar el Worker compartido no es una decisión de UI — es ciclo de
> vida del runtime, toca el invariante de ejecución única ya
> documentado (§4) y vuelve a modificar `usePyodide.ts`.

**Objetivo:** el estudiante puede cancelar la ejecución completa
mientras el panel de `input()` real está visible (`awaitingInput`),
sin quedar bloqueado indefinidamente si no quiere o no sabe qué
responder.

```
Estado normal
    │
    ▼
run()
    │
    ▼
Worker ejecutando
    │
    ▼
need-input (awaitingInput = true)
    │
 ┌──┴────────────┐
 │                │
 ▼                ▼
provideInput()    cancelRun()
 │                │
 ▼                ▼
continúa          worker.terminate()
                   limpiar singleton (worker/ready/signalSab/dataSab)
                   awaitingInput = false
                   resolver run() pendiente con resultado de cancelación
                   (el próximo run() crea un Worker nuevo, perezoso)
```

### Preguntas semánticas (respondidas aquí, no en el código)

**¿`run()` resuelve o rechaza al cancelar?** Resuelve, con
`{ stdout: '', error: 'Ejecución cancelada por el estudiante.' }` —
mismo patrón que ya usa `run()` cuando `readyPromise` rechaza
(`{ stdout: '', error: 'Python todavía no está listo.' }`, línea 152
actual de `usePyodide.ts`). Rechazar exigiría que `PythonBridge.tsx`
agregue `try/catch` alrededor de `await run(...)` — superficie
adicional que resolver evita, y mantiene el contrato `PythonRunResult`
sin excepciones para el consumidor.

**¿Qué pasa con el stdout parcial?** Se pierde — no se preserva. El
`stdout` acumulado (`lines` en `pyodideWorker.ts`) vive dentro del
closure del Worker, nunca se transmite al hilo principal hasta el
mensaje `'result'` final. `worker.terminate()` mata el Worker
instantáneamente sin darle oportunidad de enviar ese buffer. Preservarlo
exigiría que el worker transmitiera stdout de forma incremental
(cambio de protocolo mayor, explícitamente fuera de alcance de este
commit) — se documenta como limitación real, no se finge que se
preserva.

**¿A qué estado vuelve `awaitingInput`?** `false`, inmediatamente —
mismo efecto que una resolución normal por `'result'`.

**¿Cuándo se crea el Worker nuevo?** Perezosamente, en la próxima
llamada a `run()` (que ya invoca `getWorker()`, y ese ve el singleton
en `null` y crea uno desde cero) — mismo patrón de recuperación que ya
usa el `onError` del Commit 3. `cancelRun()` NO recrea el Worker de
inmediato: recargar Pyodide toma varios segundos: hacerlo eagerly
gastaría ese tiempo aunque el estudiante no vuelva a ejecutar código
enseguida.

**¿La cancelación es inmediata o espera un punto seguro?** Inmediata.
`Worker.terminate()` es una API del navegador que mata la ejecución
del Worker de forma incondicional, incluso en medio de un
`Atomics.wait()` bloqueante — no existe (ni se necesita) un mecanismo
de "punto seguro" para este caso; es distinto de
`setInterruptBuffer`/`KeyboardInterrupt` (que interrumpe Python de
forma controlada) y ese mecanismo queda fuera de alcance aquí.

**¿Qué pasa si `cancelRun()` y el mensaje `'result'` del Worker
compiten por cerrar la misma ejecución?** (pregunta añadida tras
revisión, antes de codear) Aunque JavaScript es de un solo hilo, el
orden en que llegan `provideInput()`→`'result'` del worker vs. un
clic en "Cancelar" no está garantizado por el diseño — ambos son
manejadores de evento independientes. **Invariante a preservar: cada
`run()` se resuelve exactamente una vez.** Se logra con una única
referencia module-level `pendingRun` (no solo el `resolve` suelto) que
se pone en `null` de forma ATÓMICA (dentro del mismo tick, antes de
resolver) apenas uno de los dos caminos la consume — el que llegue
primero gana y limpia la referencia; el que llegue después la
encuentra en `null` y no hace nada (la ejecución ya se cerró). Ningún
camino debe resolver sin antes confirmar que `pendingRun` seguía
activo.

### Alcance

**Entra:**
- `usePyodide.ts`: nueva función `cancelRun()` — `worker.terminate()`,
  reset de `workerSingleton`/`readySingleton`/`signalSabSingleton`/
  `dataSabSingleton`, `setAwaitingInput(false)`, y resolver la
  ejecución pendiente vía `pendingRun` (objeto module-level, no solo
  un `resolve` suelto — consistente con el invariante de ejecución
  única: solo puede haber una activa a la vez, y su resolución debe
  ocurrir exactamente una vez pese a la carrera cancelar-vs-result
  documentada arriba).
- `PythonBridge.tsx`: botón "Cancelar" visible solo junto al panel de
  `awaitingInput` (no un botón general de "detener" mientras el
  código corre sin pedir input) — llama a `cancelRun()`.

**No entra:**
- Cancelación de una ejecución que NO está esperando input (código
  corriendo largo sin `input()`) — el único punto de cancelación es el
  panel de entrada, por diseño de esta mini-épica.
- Preservar stdout parcial (ver arriba).
- `setInterruptBuffer`/Ctrl-C — mecanismo distinto, no este commit.

### Criterios de salida del Commit 4b
- El botón "Cancelar" solo aparece junto al panel de `awaitingInput`.
- Cancelar durante un `input()` real detiene la ejecución de inmediato
  (validado en navegador real, no solo revisión de código).
- El componente vuelve a un estado limpio: editor habilitado,
  `awaitingInput` false, mensaje de cancelación visible.
- Ejecutar de nuevo después de cancelar funciona (Worker nuevo se crea
  solo, sin acción manual del estudiante).
- Sin regresión del mecanismo legado ni del flujo interactivo sin
  cancelar (Commits 3/4 siguen funcionando igual).

### Commit 4b — CERRADO

**QA Evidence:**
- **Quién validó:** el tesista, en navegador real (Chrome, checkout
  Windows), siguiendo los 6 pasos entregados tras el push de
  `b20b5a2` — no el agente (bloqueo de entorno documentado en el
  mensaje de ese commit: implementación y validación ocurrieron en
  checkouts distintos; la extensión Claude in Chrome de esta sesión no
  pudo reconectar a tiempo para repetirla directamente).
- **Qué se verificó:** dos `input()` reales consecutivos con
  `awaitingInput`; cancelar durante el segundo detiene la ejecución de
  inmediato; mensaje "Ejecución cancelada por el estudiante." visible;
  editor vuelve a estar habilitado; "Ejecutar" vuelve a funcionar tras
  recrear el Worker automáticamente (sin acción manual); sin
  regresiones observadas en el flujo legado (`simulatedInputs`) ni en
  el flujo interactivo sin cancelar (Commits 3/4).
- **Confirmación explícita del tesista** (chat, tras pedírsele
  distinguir validación real de inferencia): "Sí, corrí los 6 pasos y
  funcionó todo."
- Commits: `b20b5a2` (feat), Gate en `7561123`+`9476ac1` (docs).

## 8. Commit 5 — COOP/COEP permanentes + auditoría de compatibilidad

> Gate propio (mismo criterio que 4b). Pregunta arquitectónica
> respondida ANTES de escribir código, con evidencia real, no
> supuesta: **¿COOP/COEP es solo de desarrollo o también de
> producción?**

**Respuesta:** ambos. El hosting real de producción del frontend es
**Vercel** (`frontend/vercel.json`, `outputDirectory: dist`) — no
Render (Render solo aloja el backend, `render.yaml`; la mención de
"Render.com" en `CLAUDE.md` bajo DevOps está incompleta/desactualizada
para el frontend, no se corrige aquí por estar fuera de alcance de
Épica B). El objetivo final de esta épica es que un estudiante real
use `input()` interactivo — eso solo puede pasar en producción, no
solo en `localhost`. Configurar solo dev y posponer producción
significaría repetir esta misma auditoría más adelante, con más
superficie ya construida encima.

La auditoría (abajo) no encontró incompatibilidades conocidas con los
recursos que el frontend usa hoy — eso es evidencia a favor de
configurar producción ahora, no una garantía. La aplicación real de
COOP/COEP en producción sigue dependiendo de una validación en el
entorno de despliegue (Vercel): la configuración efectiva del hosting
y cualquier recurso externo que se agregue más adelante también forman
parte del comportamiento final, y ninguno de los dos se puede
confirmar desde una auditoría estática del código.

### Auditoría de recursos cross-origin (hecha con evidencia, no supuesta)

Búsqueda exhaustiva de URLs externas cargadas por el frontend
(`grep -rEoh 'https?://...'` sobre `src/` + `index.html`), con cada
resultado clasificado:

| Recurso | Tipo | ¿Sujeto a COEP? | Estado |
|---|---|---|---|
| `fonts.googleapis.com/css2?...` | `<link rel="stylesheet">`, cross-origin | Sí | ✅ `Cross-Origin-Resource-Policy: cross-origin` (verificado con `curl -I`) |
| `fonts.gstatic.com/s/outfit/...ttf` | Fuente referenciada por el CSS anterior | Sí | ✅ `Cross-Origin-Resource-Policy: cross-origin` (verificado con `curl -I`) |
| `cdn.jsdelivr.net/pyodide/...` | Worker: script + WASM | Sí | ✅ Ya confirmado en `SPIKE-B1-PYODIDE-WORKER-STDIN.md` |
| `chat.openai.com`, `gemini.google.com`, `claude.ai` | `<a href>` en `MediaPromptCard.tsx` — el estudiante los abre en pestaña nueva | No | Enlaces de navegación, nunca cargados como subrecurso — COEP no aplica |
| `w3.org/2000/svg` | `xmlns` de SVG inline (`AnalogyCard.tsx`, `index.css`) | No | Namespace XML, no es una petición de red |
| `127.0.0.1:8000` | Fallback de `VITE_API_URL` en dev | No | Llamada `fetch`/XHR al backend (CORS, no CORP) — COEP no bloquea fetch same-mode con CORS válido |

**Resultado: cero recursos incompatibles encontrados.** Ningún
`<iframe>`, ningún flujo de OAuth por popup que dependa de
`window.opener` (los dos `window.open()` del proyecto ya usan
`noopener` o son descargas directas) — `COOP: same-origin` tampoco
tiene nada que romper.

### Alcance

**Entra:**
- `frontend/vite.config.ts`: cabeceras COOP/COEP permanentes en
  `server.headers` (ya no `TEMPORAL`, se retira ese comentario).
- `frontend/vercel.json`: nueva clave `"headers"` con las mismas dos
  cabeceras para producción (Vercel las soporta de forma nativa, sin
  plugin adicional).
- Verificación de `self.crossOriginIsolated === true` en dev (ya
  reproducido varias veces durante Commits 3/4/4b) y, si el tesista
  autoriza un deploy real, en producción.

**No entra:**
- Corregir la mención desactualizada de "Render.com" para el frontend
  en `CLAUDE.md` (fuera de alcance de Épica B).
- Deploy a producción en sí — modifica infraestructura compartida real
  (Vercel), requiere autorización explícita del tesista antes de
  ejecutarse, no se asume incluida en "abrir el Gate".

### Criterio de salida adicional (entorno, no solo funcional)

> El frontend arranca normalmente con COOP/COEP habilitados y no
> aparecen errores de recursos bloqueados (`COEP`, `CORP` o
> `crossOriginIsolated`) en la consola del navegador durante la carga
> inicial — verificado en dev; en producción, solo si el tesista
> autoriza el deploy de verificación.

## 9. Criterios de salida (Épica B completa)

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
