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

// Singleton del Worker + su promesa de "listo" — mismo criterio que el
// singleton de Pyodide en el hilo principal que este commit reemplaza (una
// sola instancia por sesión de navegador, compartida por todos los usos de
// `usePyodide()`). `signalSab`/`dataSab` solo se crean si el documento está
// cross-origin isolated (COOP/COEP, Commit 5 — todavía sin configurar en
// este proyecto): sin eso, `SharedArrayBuffer` ni siquiera existe como
// global, y el mecanismo legado (simulatedInputs) no lo necesita para nada.
let workerSingleton: Worker | null = null
let readySingleton: Promise<void> | null = null

function getWorker(): { worker: Worker; ready: Promise<void> } {
  if (!workerSingleton || !readySingleton) {
    const worker = new Worker(new URL('../workers/pyodideWorker.ts', import.meta.url), { type: 'module' })
    workerSingleton = worker
    const canUseSharedBuffers = typeof SharedArrayBuffer !== 'undefined' && self.crossOriginIsolated
    const signalSab = canUseSharedBuffers ? new SharedArrayBuffer(4) : undefined
    const dataSab = canUseSharedBuffers ? new SharedArrayBuffer(4 + 1024) : undefined
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
      worker.addEventListener('message', onMessage)
      worker.postMessage({ type: 'init', signalSab, dataSab } satisfies WorkerInboundMessage)
    })
  }
  return { worker: workerSingleton, ready: readySingleton }
}

export function usePyodide() {
  const [ready, setReady] = useState(false)
  const [loadError, setLoadError] = useState<string | null>(null)

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
      const onMessage = (e: MessageEvent<WorkerOutboundMessage>) => {
        if (e.data.type === 'result') {
          worker.removeEventListener('message', onMessage)
          resolve({ stdout: e.data.stdout, error: e.data.error })
        }
        // 'need-input' sin manejar todavía — el Commit 3 agrega la forma
        // en que el consumidor entrega el valor real al worker.
      }
      worker.addEventListener('message', onMessage)
      worker.postMessage({ type: 'run', code, stdinValues } satisfies WorkerInboundMessage)
    })
  }

  return { ready, loadError, run }
}
