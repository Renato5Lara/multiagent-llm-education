# Spike B-0 — Capacidades reales de interacción de Pyodide

> Spike técnico, no roadmap ni arquitectura. Responde únicamente si es
> viable un `stdin` interactivo real en Pyodide. **Sin código
> reutilizable, sin UI, sin decisión de diseño.** Precondición
> explícita antes de escribir el roadmap de Épica B (regla del
> tesista, 2026-07-24: "ningún roadmap se redactará mientras exista
> una hipótesis técnica crítica sin verificar").

- **Fecha:** 2026-07-24
- **Hipótesis a verificar:** "Pyodide puede ofrecer una experiencia de
  stdin interactivo adecuada."
- **Método:** documentación oficial de Pyodide, misma versión que ya
  usa el proyecto (`0.26.2`, ver `frontend/src/hooks/usePyodide.ts:9-10`),
  leída en navegador real (no resumen de memoria ni de terceros).
  Fuentes primarias:
  - https://pyodide.org/en/0.26.2/usage/streams.html
  - https://pyodide.org/en/0.26.2/usage/keyboard-interrupts.html

---

## 1. ¿Puede pausarse la ejecución esperando entrada del usuario?

**Sí, de dos formas distintas, con requisitos muy diferentes:**

**(a) En el hilo principal (donde corre Pyodide hoy en este proyecto)
— solo mediante el diálogo nativo del navegador.** La propia
documentación oficial dice, textual: *"In the browser, the default is
the same as `pyodide.setStdin({ stdin: () => prompt() })`."* —
`window.prompt()` es una llamada síncrona del navegador que sí
bloquea de verdad la ejecución hasta que el usuario responde. Es,
literalmente, el comportamiento **por defecto** de Pyodide sin
configurar nada.

**(b) Con una UI propia (no el diálogo feo del navegador) que bloquee
la ejecución de verdad** — requiere mover Pyodide a un **Web Worker**
y usar `SharedArrayBuffer` + `Atomics.wait()`. Confirmado en
"Interrupting execution" (misma familia de restricción que aplica a
interrumpir con Ctrl-C, y por extensión al patrón de stdin
interactivo vía worker): *"In order to use interrupts you must be
using Pyodide in a webworker. You also will need to use a
SharedArrayBuffer, which means that your server must set appropriate
security headers."*

## 2. ¿Puede reanudarse después?

Sí, en ambos casos. `prompt()` bloquea y devuelve el valor escrito
cuando el usuario acepta el diálogo — la ejecución de Python continúa
normalmente desde ahí. El patrón worker + `Atomics.wait()` despierta
el worker cuando el hilo principal escribe la respuesta en el buffer
compartido y llama `Atomics.notify()` — mismo efecto, sin depender del
diálogo nativo.

## 3. ¿Puede hacerse sin hacks?

Sí, ambas rutas son **oficiales y documentadas por el propio proyecto
Pyodide**, no workarounds de terceros. Ninguna es un hack. Pero tienen
costos de infraestructura muy distintos:
- (a) `prompt()`: cero cambios de infraestructura — funciona ya, hoy,
  con la carga de Pyodide en el hilo principal que ya existe
  (`usePyodide.ts`).
- (b) Worker + `Atomics`: exige (i) mover la carga de Pyodide del hilo
  principal a un Web Worker, (ii) que el servidor (Vite dev server y
  el hosting de producción) envíe las cabeceras de aislamiento de
  origen cruzado `Cross-Origin-Opener-Policy: same-origin` y
  `Cross-Origin-Embedder-Policy: require-corp` en TODAS las
  respuestas, incluidos los recursos externos (hoy Pyodide se carga
  desde `cdn.jsdelivr.net` — si ese CDN no envía las cabeceras CORP/CORS
  compatibles, la carga rompería bajo COEP; no verificado en este
  spike, queda como detalle de implementación si se elige esta vía).

## 4. ¿Qué APIs ofrece Pyodide oficialmente?

- `pyodide.setStdin({ stdin, isatty, error })` — `stdin` es un
  callback **síncrono**, de cero argumentos, que debe devolver de
  inmediato uno de: una cadena de texto, un buffer/`Uint8Array` de
  bytes utf8, un número 0-255, o `undefined`/`null` (EOF). **No puede
  devolver una `Promise`** — no hay ninguna variante async de esta
  API. Esto es lo que hace que un callback "normal" en el hilo
  principal (p. ej. uno que espere un evento de clic) sea inviable:
  tiene que devolver el valor ya mismo, no puede "esperar".
- `pyodide.setInterruptBuffer(buffer)` — para interrupciones
  (Ctrl-C/`KeyboardInterrupt`), mismo requisito de Worker +
  `SharedArrayBuffer`.

## 5. ¿Qué limitaciones impone el navegador?

El hilo principal de JavaScript no puede bloquearse sincrónicamente
esperando un evento asíncrono arbitrario (como que el estudiante
escriba en un campo de texto propio) — esa es la razón de fondo detrás
de todo lo anterior. Las únicas excepciones que el navegador concede
son sus propios diálogos síncronos nativos (`prompt`, `confirm`,
`alert`), que sí bloquean pero con una UI que el navegador controla,
no la aplicación. Para lograr un bloqueo real con una UI propia hace
falta sacar la ejecución del hilo principal (Worker) y usar
`Atomics.wait()`, que a su vez solo está disponible bajo aislamiento
de origen cruzado — una restricción de seguridad del navegador
(Spectre/Meltdown), no una limitación de Pyodide.

## 6. ¿Qué alternativas recomienda la propia documentación?

La documentación oficial no presenta ninguna tercera vía además de
las dos ya descritas. No hay ningún patrón documentado para "una UI
HTML propia que pause la ejecución sin worker ni `SharedArrayBuffer`"
— esa combinación no existe porque el modelo de ejecución de
JavaScript no lo permite, según el propio texto citado en el punto 1.

---

## Conclusión técnica

**La hipótesis se confirma parcialmente, con una condición
importante.** Sí es posible un `stdin` que realmente pause y reanude
la ejecución de Pyodide — pero solo por dos caminos con perfiles muy
distintos:

1. **`prompt()` nativo del navegador** — viable hoy, sin ningún cambio
   de infraestructura, es literalmente el default de Pyodide. Costo:
   una UI que no se puede estilizar (rompe con la estética
   `neural-glow`/glass del resto de la plataforma) y bloquea la
   pestaña entera del navegador mientras espera, no solo el editor.
2. **Worker + `SharedArrayBuffer` + `Atomics.wait()`** — la única vía
   para una experiencia interactiva con UI propia. Costo real: requiere
   reestructurar `usePyodide.ts` para correr en un Worker, y requiere
   que el servidor (dev y producción) envíe cabeceras COOP/COEP —
   ninguna de las dos cosas existe hoy en el proyecto, y la segunda no
   se pudo verificar completamente en este spike (compatibilidad del
   CDN de Pyodide bajo COEP).

**No verificado empíricamente en este spike:** no se ejecutó código
real contra Pyodide para confirmar el patrón worker+Atomics en este
proyecto específico (sería ya un experimento de implementación, fuera
del alcance de un spike de documentación); tampoco se disparó
`prompt()` de verdad en el navegador de esta sesión porque un diálogo
nativo bloquearía la automatización del navegador usada para leer la
documentación — su comportamiento síncrono-bloqueante es, no obstante,
semántica estándar y documentada del navegador, no algo que requiera
prueba adicional.

**Lo que esto implica para el roadmap de Épica B (sin decidirlo
aquí):** la Opción A ya no tiene una hipótesis técnica abierta. Existen
dos caminos reales y documentados, con trade-offs claros y opuestos
(cero infraestructura pero UI no controlable vs. UI propia pero
reestructuración + cabeceras de servidor) — la decisión entre ellos (o
mantener `simulatedInputs` autorado por el estudiante en vez de por el
contenido, la opción más barata de las tres) le corresponde al
tesista, no a este spike.
