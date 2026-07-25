// Python real ejecutándose en el navegador (WebAssembly, vía Pyodide) — el
// Runtime nunca ejecuta código del estudiante, solo recibe la evidencia que
// producen sus intentos. Carga perezosa y compartida: el WASM (~6-10MB) solo
// se descarga la primera vez que una micropráctica de Python aparece en
// pantalla, y una sola instancia se reutiliza en toda la sesión del navegador.
//
// Épica B, Commit 2 (ENGINEERING-GATE-EPICA-B.md §6): Pyodide corre dentro
// de un Worker dedicado (frontend/src/workers/pyodideWorker.ts) en vez del
// hilo principal — necesario para poder bloquear stdin de verdad más
// adelante (Commit 3), validado con código real en SPIKE-B1. `run()` pasa
// de síncrono a `Promise<PythonRunResult>` como consecuencia obligada de
// comunicarse por `postMessage` (no una decisión de diseño — mantenerlo
// síncrono exigiría `Atomics.wait()` en el hilo principal, el mismo
// bloqueo de pestaña que el Worker existe para evitar). El resto del
// contrato público (`{ ready, loadError, run }`) no cambia de forma.

import { useEffect, useState } from 'react'
import type { WorkerInboundMessage, WorkerOutboundMessage } from '@/workers/pyodideWorker'

export interface PythonRunResult {
  stdout: string
  error: string | null
}

/** Mensaje exacto que `run()` devuelve cuando `cancelRun()` interrumpe una
 *  ejecución en curso (Commit 4b) — exportado para que el consumidor
 *  (PythonBridge.tsx) pueda distinguir una cancelación real de un error de
 *  Python, sin duplicar el string a mano en dos archivos. */
export const CANCELLED_RESULT_ERROR = 'Ejecución cancelada por el estudiante.'

/** En qué se equivocó el estudiante — no CUÁNTAS veces, sino DE QUÉ tipo. */
export type PythonErrorCategory = 'sintaxis' | 'variables' | 'logica' | 'salida'

const SYNTAX_ERROR_NAMES = ['SyntaxError', 'IndentationError', 'TabError']
const VARIABLE_ERROR_NAMES = ['NameError', 'UnboundLocalError']

/** Deriva de la propia excepción de Python (`error`) que Pyodide ya entrega
 *  en `PythonRunResult.error` (traceback de CPython incluido) — no es una
 *  capacidad nueva, es leer lo que el intérprete ya dijo. `null` (sin
 *  excepción, pero salida distinta a la esperada) clasifica como `salida`.
 *  El resto de excepciones reales (TypeError, ValueError, ZeroDivisionError,
 *  etc.) caen en `logica` — no son de sintaxis ni de variable no definida. */
export function classifyPythonError(error: string | null): PythonErrorCategory {
  if (!error) return 'salida'
  const exceptionName = error.match(/(\w+Error):/)?.[1]
  if (exceptionName && SYNTAX_ERROR_NAMES.includes(exceptionName)) return 'sintaxis'
  if (exceptionName && VARIABLE_ERROR_NAMES.includes(exceptionName)) return 'variables'
  return 'logica'
}

// ── Sprint UX-04 — el error como material de aprendizaje ─────────────────────
// El traceback crudo de CPython es ilegible para un principiante. Estas
// funciones EXTRAEN lo que el intérprete ya dijo (nunca inventan): qué
// excepción fue, en qué línea del código del estudiante, y una traducción
// breve al español de las excepciones que un principiante realmente ve.

export interface ParsedPythonError {
  /** Nombre de la excepción tal como la dio Python (p. ej. "NameError"). */
  name: string
  /** Mensaje original de la excepción (tras los dos puntos). */
  message: string
  /** Línea (1-based) DEL CÓDIGO DEL ESTUDIANTE donde ocurrió, si el
   *  traceback la señala — solo frames de `<exec>`, nunca internos. */
  line: number | null
  /** Traducción breve para un principiante, o null si la excepción no está
   *  en el mapa (se muestra `message` tal cual). */
  translation: string | null
}

/** Traducciones de las excepciones que un principiante encuentra de verdad.
 *  Cada una dice QUÉ pasó en lenguaje de estudiante — el CÓMO corregirlo lo
 *  aportan las pistas autoradas del ejercicio (hintsByCategory/hint). */
const ERROR_TRANSLATION: Record<string, string> = {
  SyntaxError: 'Python no pudo leer esta línea — revisa comillas, paréntesis y signos: algo quedó incompleto o de más.',
  IndentationError: 'La sangría (los espacios al inicio de la línea) no es la que Python espera aquí.',
  NameError: 'Esta línea usa un nombre que no existe todavía — o nunca se creó, o está escrito distinto a como lo creaste.',
  TypeError: 'Se intentó combinar cosas incompatibles — por ejemplo, sumar un texto con un número.',
  ValueError: 'La operación existe, pero el valor que recibió no sirve para ella — por ejemplo, convertir a número un texto que no lo es.',
  ZeroDivisionError: 'Se intentó dividir entre cero — y eso no está definido, ni en matemáticas ni en Python.',
  EOFError: 'El programa pidió una respuesta con input(), pero el usuario simulado ya no tenía más respuestas que dar — revisa cuántas veces preguntas.',
  IndexError: 'Se intentó acceder a una posición que no existe — la secuencia es más corta de lo que esta línea asume.',
  KeyError: 'Se buscó una clave que no está guardada — revisa el nombre exacto.',
}

/** Extrae nombre, mensaje y línea del traceback que Pyodide entrega en
 *  `PythonRunResult.error`. Nunca lanza: con un formato inesperado devuelve
 *  lo que pueda extraer y deja el resto en null. */
export function parsePythonError(error: string): ParsedPythonError {
  // Última línea con forma "AlgoError: mensaje" — la excepción real.
  const headline = [...error.matchAll(/^(\w+(?:Error|Exception)):?\s?(.*)$/gm)].pop()
  const name = headline?.[1] ?? 'Error'
  const message = headline?.[2]?.trim() ?? ''
  // Último frame que apunta al código del estudiante (`<exec>`); los frames
  // internos de Pyodide se ignoran. SyntaxError usa `File "<exec>", line N`
  // igual que los frames de ejecución.
  const execLines = [...error.matchAll(/File "<exec>", line (\d+)/g)]
  const line = execLines.length > 0 ? Number(execLines[execLines.length - 1][1]) : null
  return { name, message, line, translation: ERROR_TRANSLATION[name] ?? null }
}

// Singleton del Worker + su promesa de "listo" — mismo criterio que el
// singleton de Pyodide en el hilo principal que este commit reemplaza (una
// sola instancia por sesión de navegador, compartida por todos los usos de
// `usePyodide()`). `signalSab`/`dataSab` solo se crean si el documento está
// cross-origin isolated (COOP/COEP, Commit 5 — todavía sin configurar en
// este proyecto): sin eso, `SharedArrayBuffer` ni siquiera existe como
// global, y el mecanismo legado (simulatedInputs) no lo necesita para nada.
let workerSingleton: Worker | null = null
let readySingleton: Promise<void> | null = null
// Mismos buffers que recibió el Worker en 'init' — necesarios aquí también
// para que `provideInput` (Commit 3) escriba en la misma memoria
// compartida que el worker lee al despertar de `Atomics.wait()`.
let signalSabSingleton: SharedArrayBuffer | undefined
let dataSabSingleton: SharedArrayBuffer | undefined

const MAX_INPUT_BYTES = 1024 // debe coincidir con el tamaño de dataSab

/** Referencia a la ÚNICA ejecución `run()` activa (Commit 4b,
 *  ENGINEERING-GATE-EPICA-B.md §7) — consistente con el invariante de
 *  ejecución única ya documentado. No es solo el `resolve` suelto: se
 *  limpia a `null` de forma atómica (dentro del mismo tick, ANTES de
 *  llamar a `resolve`) apenas uno de los dos caminos posibles la
 *  consume — el mensaje `'result'` real del worker, o `cancelRun()`.
 *  Quien llegue primero gana y resuelve; el que llegue después encuentra
 *  `pendingRun !== current` (o ya `null`) y no hace nada. Garantiza que
 *  cada `run()` se resuelve EXACTAMENTE una vez, incluso si ambos
 *  caminos compiten por cerrar la misma ejecución casi al mismo tiempo. */
let pendingRun: { resolve: (result: PythonRunResult) => void } | null = null

function getWorker(): { worker: Worker; ready: Promise<void> } {
  if (!workerSingleton || !readySingleton) {
    const worker = new Worker(new URL('../workers/pyodideWorker.ts', import.meta.url), { type: 'module' })
    workerSingleton = worker
    const canUseSharedBuffers = typeof SharedArrayBuffer !== 'undefined' && self.crossOriginIsolated
    signalSabSingleton = canUseSharedBuffers ? new SharedArrayBuffer(4) : undefined
    dataSabSingleton = canUseSharedBuffers ? new SharedArrayBuffer(4 + MAX_INPUT_BYTES) : undefined
    readySingleton = new Promise<void>((resolve, reject) => {
      const onMessage = (e: MessageEvent<WorkerOutboundMessage>) => {
        if (e.data.type === 'ready') {
          worker.removeEventListener('message', onMessage)
          resolve()
        } else if (e.data.type === 'load-error') {
          worker.removeEventListener('message', onMessage)
          reject(new Error(e.data.message))
        }
      }
      // Sin esto, si el propio script del worker falla al cargar (p. ej. un
      // 503 transitorio del dev server, encontrado validando el Commit 3 en
      // navegador real), el evento 'error' del Worker nunca tenía quién lo
      // escuchara — la promesa quedaba colgada para siempre y el laboratorio
      // quedaba roto hasta recargar la página completa. Al rechazar y
      // limpiar el singleton, una futura llamada a `usePyodide()` puede
      // reintentar desde cero en vez de heredar el estado roto.
      const onError = (e: ErrorEvent) => {
        worker.removeEventListener('message', onMessage)
        worker.removeEventListener('error', onError)
        workerSingleton = null
        readySingleton = null
        reject(new Error(e.message || 'No se pudo cargar el worker de Python.'))
      }
      worker.addEventListener('message', onMessage)
      worker.addEventListener('error', onError)
      worker.postMessage({
        type: 'init',
        signalSab: signalSabSingleton,
        dataSab: dataSabSingleton,
      } satisfies WorkerInboundMessage)
    })
  }
  return { worker: workerSingleton, ready: readySingleton }
}

export function usePyodide() {
  const [ready, setReady] = useState(false)
  const [loadError, setLoadError] = useState<string | null>(null)
  // true mientras el worker está bloqueado en Atomics.wait() esperando un
  // input() real (Commit 3) — el consumidor (Commit 4) lo usa para mostrar
  // el panel donde el estudiante escribe el valor. Nunca se activa en el
  // mecanismo legado (simulatedInputs), por el contrato de compatibilidad §5.
  const [awaitingInput, setAwaitingInput] = useState(false)

  useEffect(() => {
    let cancelled = false
    getWorker()
      .ready.then(() => {
        if (!cancelled) setReady(true)
      })
      .catch((err: unknown) => {
        if (cancelled) return
        setLoadError(err instanceof Error ? err.message : 'Error cargando Python.')
      })
    return () => {
      cancelled = true
    }
  }, [])

  /** `stdinValues`: respuestas simuladas de input(), en el orden en que el
   *  código las consume (mecanismo legado, contrato de compatibilidad
   *  ENGINEERING-GATE-EPICA-B.md §5). Sin este parámetro, el worker usa el
   *  mecanismo interactivo real (Commit 3 en adelante) — hoy, sin UI que lo
   *  sirva, cualquier `input()` sin `simulatedInputs` sigue sin recibir
   *  valor, igual que antes de esta capacidad.
   *
   *  INVARIANTE DEL RUNTIME (Épica B): mientras no exista un protocolo con
   *  correlación de mensajes por id, el Worker admite una única ejecución
   *  activa. El consumidor NO DEBE invocar `run()` de nuevo hasta que la
   *  anterior haya resuelto — hoy lo garantiza la UI real (deshabilita
   *  "Ejecutar" mientras `running` es true), no este hook. Sin esa
   *  correlación, dos `run()` concurrentes recibirían resultados cruzados
   *  (el primer 'result' que llegue resuelve el primer listener que siga
   *  activo, sin importar cuál lo disparó). No es una limitación a
   *  resolver todavía — reutilizar este Worker para ejecuciones
   *  concurrentes requiere diseñar esa correlación primero, explícitamente,
   *  no asumirla disponible. */
  const run = async (code: string, stdinValues?: string[]): Promise<PythonRunResult> => {
    const { worker, ready: readyPromise } = getWorker()
    try {
      await readyPromise
    } catch {
      return { stdout: '', error: 'Python todavía no está listo.' }
    }
    return new Promise<PythonRunResult>(resolve => {
      const current = { resolve }
      pendingRun = current
      const onMessage = (e: MessageEvent<WorkerOutboundMessage>) => {
        if (e.data.type === 'result') {
          worker.removeEventListener('message', onMessage)
          // Carrera cancelar-vs-result (Commit 4b, §7): si cancelRun() ya
          // resolvió esta misma ejecución, pendingRun ya no es `current` (o
          // ya es null) — no resolver de nuevo.
          if (pendingRun !== current) return
          pendingRun = null
          setAwaitingInput(false)
          resolve({ stdout: e.data.stdout, error: e.data.error })
        } else if (e.data.type === 'need-input') {
          setAwaitingInput(true)
        }
      }
      worker.addEventListener('message', onMessage)
      worker.postMessage({ type: 'run', code, stdinValues } satisfies WorkerInboundMessage)
    })
  }

  /** Cancela la ejecución en curso — solo tiene efecto real mientras el
   *  Worker está bloqueado esperando un `input()` real (`awaitingInput`);
   *  la UI solo expone el botón que la llama en ese estado
   *  (ENGINEERING-GATE-EPICA-B.md §7, alcance: no es un "detener"
   *  general). `worker.terminate()` mata la ejecución de inmediato, sin
   *  punto seguro — no existe (ni se necesita) uno para un
   *  `Atomics.wait()` bloqueante. El stdout que el worker ya había
   *  acumulado internamente se PIERDE (vive en su closure, nunca llegó
   *  al hilo principal) — límite real, no se finge que se preserva. El
   *  Worker siguiente se crea perezosamente en el próximo `run()`, no
   *  aquí (recargar Pyodide toma varios segundos). */
  const cancelRun = () => {
    const current = pendingRun
    pendingRun = null
    if (workerSingleton) workerSingleton.terminate()
    workerSingleton = null
    readySingleton = null
    signalSabSingleton = undefined
    dataSabSingleton = undefined
    setAwaitingInput(false)
    current?.resolve({ stdout: '', error: CANCELLED_RESULT_ERROR })
  }

  /** Entrega al worker el valor real que el estudiante escribió — solo
   *  tiene efecto mientras `awaitingInput` es true (el worker está
   *  bloqueado en `Atomics.wait()`, patrón validado en SPIKE-B1). Sin
   *  UI todavía que la llame (eso es el Commit 4): esta función existe
   *  pero ningún componente la usa aún, igual que el Worker del Commit 1
   *  no tenía wiring. Trunca defensivamente a `MAX_INPUT_BYTES` — el
   *  buffer compartido tiene tamaño fijo (`dataSab`, Commit 1/2); un
   *  valor más largo se recorta en vez de tirar un RangeError. */
  const provideInput = (value: string) => {
    if (!signalSabSingleton || !dataSabSingleton) return
    let encoded = new TextEncoder().encode(value)
    if (encoded.length > MAX_INPUT_BYTES) encoded = encoded.slice(0, MAX_INPUT_BYTES)
    new DataView(dataSabSingleton).setInt32(0, encoded.length, true)
    new Uint8Array(dataSabSingleton, 4).set(encoded)
    const signal = new Int32Array(signalSabSingleton)
    Atomics.store(signal, 0, 1)
    Atomics.notify(signal, 0)
    setAwaitingInput(false)
  }

  return { ready, loadError, run, awaitingInput, provideInput, cancelRun }
}
