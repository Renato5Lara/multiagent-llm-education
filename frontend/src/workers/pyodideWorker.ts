/// <reference lib="webworker" />

// Runtime del Worker de Pyodide (Épica B, Commit 1 — aislado, sin
// wiring todavía; ver ENGINEERING-GATE-EPICA-B.md §6). A diferencia de
// usePyodide.ts (que carga Pyodide en el hilo principal), este Worker
// existe para poder bloquear stdin de verdad con Atomics.wait() —
// patrón validado con código real en SPIKE-B1-PYODIDE-WORKER-STDIN.md.
// Este archivo todavía no lo instancia nadie del árbol de componentes.

const PYODIDE_VERSION = '0.26.2'
const PYODIDE_CDN = `https://cdn.jsdelivr.net/pyodide/v${PYODIDE_VERSION}/full/`

interface PyodideInterface {
  runPython: (code: string) => unknown
  setStdout: (options: { batched: (output: string) => void }) => void
  setStdin: (options: { stdin: () => string }) => void
}

declare const self: DedicatedWorkerGlobalScope

/** Vite sirve este archivo como ESM nativo en dev (por los `export`
 *  de más abajo), así que el Worker debe instanciarse con
 *  `{ type: 'module' }` — eso descarta `importScripts` (API exclusiva
 *  de workers clásicos, confirmado con un `SyntaxError: Unexpected
 *  token 'export'` real al probarlo). Pyodide 0.26.2 sí publica un
 *  entrypoint ESM (`pyodide.mjs`, confirmado con `curl` — exporta
 *  `loadPyodide` por nombre) pensado exactamente para este caso. */
async function importLoadPyodide(): Promise<(config: { indexURL: string }) => Promise<PyodideInterface>> {
  const mod: { loadPyodide: (config: { indexURL: string }) => Promise<PyodideInterface> } =
    await import(/* @vite-ignore */ `${PYODIDE_CDN}pyodide.mjs`)
  return mod.loadPyodide
}

// Protocolo de mensajes worker↔hilo principal — tipos exportados para
// que el hook del Commit 2 los reutilice sin duplicarlos.
export type WorkerInboundMessage =
  | { type: 'init'; signalSab: SharedArrayBuffer; dataSab: SharedArrayBuffer }
  | { type: 'run'; code: string }

export type WorkerOutboundMessage =
  | { type: 'ready' }
  | { type: 'load-error'; message: string }
  | { type: 'need-input' }
  | { type: 'result'; stdout: string; error: string | null }

let signal: Int32Array | null = null
let lenView: DataView | null = null
let dataBytes: Uint8Array | null = null
let pyodide: PyodideInterface | null = null

/** Callback SÍNCRONO de stdin que exige `pyodide.setStdin` — bloquea el
 *  hilo del worker de verdad con `Atomics.wait()` hasta que el hilo
 *  principal escriba el valor y llame `Atomics.notify()`. Mismo patrón
 *  ya reproducido dos veces en el Spike B-1. */
function stdinSync(): string {
  if (!signal || !lenView || !dataBytes) return ''
  Atomics.store(signal, 0, 0)
  self.postMessage({ type: 'need-input' } satisfies WorkerOutboundMessage)
  Atomics.wait(signal, 0, 0)
  const len = lenView.getInt32(0, true)
  return new TextDecoder().decode(dataBytes.slice(0, len))
}

self.onmessage = async (e: MessageEvent<WorkerInboundMessage>) => {
  const msg = e.data
  if (msg.type === 'init') {
    signal = new Int32Array(msg.signalSab)
    lenView = new DataView(msg.dataSab)
    dataBytes = new Uint8Array(msg.dataSab, 4)
    try {
      const loadPyodide = await importLoadPyodide()
      pyodide = await loadPyodide({ indexURL: PYODIDE_CDN })
      self.postMessage({ type: 'ready' } satisfies WorkerOutboundMessage)
    } catch (err) {
      self.postMessage({
        type: 'load-error',
        message: err instanceof Error ? err.message : String(err),
      } satisfies WorkerOutboundMessage)
    }
    return
  }
  if (msg.type === 'run') {
    if (!pyodide) return
    const lines: string[] = []
    pyodide.setStdout({ batched: (output: string) => lines.push(output) })
    pyodide.setStdin({ stdin: stdinSync })
    try {
      pyodide.runPython(msg.code)
      self.postMessage({ type: 'result', stdout: lines.join('\n'), error: null } satisfies WorkerOutboundMessage)
    } catch (err) {
      self.postMessage({
        type: 'result',
        stdout: lines.join('\n'),
        error: err instanceof Error ? err.message : String(err),
      } satisfies WorkerOutboundMessage)
    }
  }
}
