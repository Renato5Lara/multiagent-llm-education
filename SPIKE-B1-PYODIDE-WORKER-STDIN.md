# Spike B-1 — Verificación empírica: Worker + SharedArrayBuffer + Atomics.wait()

> Spike experimental (código real, no documentación). Cierra el punto
> abierto que dejó `SPIKE-B0-PYODIDE-STDIN.md` ("no verificado
> empíricamente") y que `CHECKPOINT-EPICA-B.md` §2 marcó como
> condición antes del Engineering Gate. Prototipo funcional en
> `spikes/b1-pyodide-worker-stdin/` (aislado, sin wiring a la app real
> — ver §"Qué NO es este spike").

- **Fecha:** 2026-07-24
- **Hipótesis a verificar:** "El patrón Worker + `SharedArrayBuffer` +
  `Atomics.wait()` pausa y reanuda genuinamente `input()` en Pyodide
  dentro de este proyecto, y el CDN de Pyodide (`cdn.jsdelivr.net`) es
  compatible con las cabeceras `COOP`/`COEP` que el patrón exige."
- **Método:** prototipo real (no simulado) — worker clásico que carga
  Pyodide 0.26.2 (misma versión que `usePyodide.ts`) desde el mismo
  CDN, implementa `stdin` síncrono bloqueante vía `Atomics.wait()`,
  servido por un servidor Node mínimo con cabeceras `COOP: same-origin`
  / `COEP: require-corp` reales — ejecutado en navegador real
  (Chrome vía Claude in Chrome), no en un entorno simulado.

---

## 1. ¿Puede Pyodide pausar realmente un `input()` y reanudar la ejecución?

**Sí, confirmado con código real, no simulación.** Código de prueba
con DOS llamadas consecutivas a `input()` real (no `simulatedInputs`
precargado):

```python
nombre = input("¿Cómo te llamas? ")
print("Hola,", nombre)
edad = input("¿Cuántos años tienes? ")
print("El próximo año tendrás", int(edad) + 1)
```

Resultado observado en navegador:
1. Al ejecutar, la UI mostró `worker: BLOQUEADO esperando input() real #1
   (Atomics.wait en curso)` — el worker se detuvo genuinamente (no un
   `await` disfrazado: `Atomics.wait()` bloquea el hilo de JavaScript
   del worker de verdad) mientras el hilo principal seguía respondiendo
   a clics.
2. Al escribir "Ana" y confirmar, el worker reanudó y de inmediato
   pidió el segundo `input()` real (`#2`) — la ejecución de Python
   continuó exactamente desde donde se había pausado.
3. Al escribir "20", la salida final fue:
   `¿Cómo te llamas? Hola, Ana` / `¿Cuántos años tienes? El próximo año
   tendrás 21` — `int("20") + 1 = 21`, correcto.

Esto es cualitativamente distinto del mecanismo actual
(`usePyodide.ts` + `simulatedInputs`): ahí el valor está fijado ANTES
de ejecutar y una cola FIFO lo entrega sin que el estudiante escriba
nada en tiempo real. Aquí el estudiante (simulado por la interacción
real del navegador) escribe el valor DESPUÉS de que Python ya empezó a
ejecutarse y lo está esperando.

## 2. ¿Funciona con la versión de Pyodide del proyecto?

Sí. Mismo `PYODIDE_VERSION = '0.26.2'` y mismo CDN
(`cdn.jsdelivr.net/pyodide/v0.26.2/full/`) que
`frontend/src/hooks/usePyodide.ts:9-10` — sin parches, sin build
especial de Pyodide.

## 3. ¿Es viable servir las cabeceras COOP/COEP?

**En desarrollo (servidor propio): sí, verificado.** El servidor
mínimo (`spikes/b1-pyodide-worker-stdin/server.mjs`) sirvió
`Cross-Origin-Opener-Policy: same-origin` y
`Cross-Origin-Embedder-Policy: require-corp` en cada respuesta; el
navegador confirmó `self.crossOriginIsolated === true` (la señal
oficial de que ambas cabeceras se aplicaron correctamente y
`SharedArrayBuffer`/`Atomics` están habilitados).

**Compatibilidad del CDN — el punto que SPIKE-B0 dejó sin verificar,
ahora confirmado con evidencia directa:**

```
$ curl -sI https://cdn.jsdelivr.net/pyodide/v0.26.2/full/pyodide.js
cross-origin-resource-policy: cross-origin
access-control-allow-origin: *

$ curl -sI https://cdn.jsdelivr.net/pyodide/v0.26.2/full/pyodide.asm.wasm
cross-origin-resource-policy: cross-origin
access-control-allow-origin: *
```

`cdn.jsdelivr.net` envía `Cross-Origin-Resource-Policy: cross-origin`
en el script y en el binario `.wasm` — exactamente la cabecera que
`COEP: require-corp` exige de un recurso cross-origin. Por eso Pyodide
cargó completo (script + WASM) sin que el navegador bloqueara nada; no
hizo falta el modo `credentialless` (más permisivo) como respaldo.

**Vite dev server / producción (Render.com): NO verificado en este
spike.** El prototipo usa un servidor Node aislado, deliberadamente
separado del Vite de la app real, para no acoplar el experimento a su
configuración mientras la hipótesis seguía sin confirmar (ver
`server.mjs`, comentario de cabecera). Configurar estas cabeceras en
`vite.config.ts` (dev) y en el hosting de producción es trabajo real
pendiente si se decide avanzar — pero es configuración conocida y
documentada (plugins de Vite existen para esto), no una incógnita
técnica como la que este spike sí resolvía.

## 4. ¿Introduce limitaciones importantes?

- **Compatibilidad de navegador:** `SharedArrayBuffer` con aislamiento
  de origen cruzado es soportado por todos los navegadores modernos
  (Chrome/Edge/Firefox/Safari recientes) — no es una API experimental.
  Este spike solo se ejecutó en Chrome; no se probó Firefox/Safari
  reales.
- **Impacto en el resto de la plataforma:** `COOP: same-origin` +
  `COEP: require-corp` aplicados a TODA la app (no solo al laboratorio)
  rompen cualquier recurso cross-origin que no envíe `Cross-Origin-
  Resource-Policy` compatible — habría que auditar TODOS los recursos
  externos que carga el frontend (no solo Pyodide) antes de activar
  estas cabeceras globalmente. No auditado en este spike (fuera de
  alcance: solo Pyodide).
- **Reestructuración real de `usePyodide.ts`:** mover la carga de
  Pyodide del hilo principal a un Worker es un cambio estructural real
  del hook (confirmado por el prototipo, no solo teórico) — no es un
  ajuste menor, aunque el hook ya está aislado (ver
  `AUDITORIA-EPICA-B.md` §5, "Desacoplado / fácil de extender").

---

## Evidencia

- Capturas de navegador real: `crossOriginIsolated: true`,
  bloqueo real (`Atomics.wait en curso`) en dos `input()` consecutivos,
  salida final correcta.
- `curl -I` contra el CDN real (arriba) confirmando `Cross-Origin-
  Resource-Policy: cross-origin`.
- Prototipo funcional conservado en
  `spikes/b1-pyodide-worker-stdin/` (`worker.js`, `main.js`,
  `index.html`, `server.mjs`) — reproducible con `node server.mjs`.

## Decisión

✅ **Viable, con una restricción real identificada:** las cabeceras
COOP/COEP tendrían que aplicarse a toda la aplicación (no solo al
laboratorio), lo que exige auditar el resto de recursos cross-origin
del frontend antes de activarlas — no es un bloqueante técnico, es
trabajo de alcance que el roadmap debe incluir explícitamente.

## Qué NO es este spike

No es una implementación del laboratorio. `usePyodide.ts`,
`PythonBridge.tsx` y el resto de la app **no se tocaron**. El
prototipo vive aislado en `spikes/` y no se importa desde ningún
archivo de `frontend/src/`.

## Próximo paso

Con la hipótesis técnica confirmada, corresponde al tesista decidir si
se abre el Engineering Gate de implementación de Épica B (RFC/ADR +
plan de commits pequeños) — incluyendo explícitamente en ese plan la
auditoría de recursos cross-origin que la restricción de COOP/COEP
exige antes de activarlas en la app real.
