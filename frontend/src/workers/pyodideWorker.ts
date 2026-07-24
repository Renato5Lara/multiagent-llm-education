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
// que usePyodide.ts (Commit 2) los reutilice sin duplicarlos.
//
// `signalSab`/`dataSab` son opcionales: sin cabeceras COOP/COEP
// (pendiente hasta el Commit 5), `SharedArrayBuffer` no existe en el
// hilo principal — el hook de todos modos debe poder inicializar el
// Worker para el mecanismo legado (simulatedInputs, síncrono dentro
// del worker, nunca necesitó SharedArrayBuffer). Solo el mecanismo
// interactivo real (Atomics.wait) los requiere.
export type WorkerInboundMessage =
  | { type: 'init'; signalSab?: SharedArrayBuffer; dataSab?: SharedArrayBuffer }
  | { type: 'run'; code: string; stdinValues?: string[] }

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
 *  ya reproducido dos veces en el Spike B-1. Sin SharedArrayBuffer
 *  (COOP/COEP todavía sin configurar, Commit 5) no hay forma de
 *  bloquear de verdad — se degrada devolviendo '' en vez de colgar el
 *  worker; ningún contenido real llama a esta rama hoy (auditoría:
 *  todo `input()` autorado trae `simulatedInputs`). */
function stdinSync(): string {
  if (!signal || !lenView || !dataBytes) {
    console.error('pyodideWorker: stdin interactivo pedido sin SharedArrayBuffer (COOP/COEP pendiente, Commit 5).')
    return ''
  }
  Atomics.store(signal, 0, 0)
  self.postMessage({ type: 'need-input' } satisfies WorkerOutboundMessage)
  Atomics.wait(signal, 0, 0)
  const len = lenView.getInt32(0, true)
  return new TextDecoder().decode(dataBytes.slice(0, len))
}

/** Cola FIFO de valores precargados — mecanismo legado
 *  (`simulatedInputs`), idéntico en efecto al que `usePyodide.ts`
 *  implementaba antes de este commit, solo que ahora corre dentro del
 *  Worker. Contrato de compatibilidad, ENGINEERING-GATE-EPICA-B.md §5. */
function stdinFifo(values: string[]): () => string {
  let cursor = 0
  return () => (cursor < values.length ? values[cursor++] : '')
}

self.onmessage = async (e: MessageEvent<WorkerInboundMessage>) => {
  const msg = e.data
  if (msg.type === 'init') {
    signal = msg.signalSab ? new Int32Array(msg.signalSab) : null
    lenView = msg.dataSab ? new DataView(msg.dataSab) : null
    dataBytes = msg.dataSab ? new Uint8Array(msg.dataSab, 4) : null
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
    // Contrato de compatibilidad (§5): stdinValues presente → legado
    // (FIFO); ausente → interactivo real. Nunca ambos — la selección
    // es automática, nunca configurable.
    pyodide.setStdin({
      stdin: msg.stdinValues && msg.stdinValues.length > 0 ? stdinFifo(msg.stdinValues) : stdinSync,
    })
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
