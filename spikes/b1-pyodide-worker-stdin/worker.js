// Spike B-1 — Worker de Pyodide con stdin bloqueante real vía Atomics.wait().
// Carga clásica (importScripts), igual que frontend/src/hooks/usePyodide.ts,
// misma versión (0.26.2) para que el resultado sea comparable al proyecto real.

const PYODIDE_VERSION = '0.26.2'
const PYODIDE_CDN = `https://cdn.jsdelivr.net/pyodide/v${PYODIDE_VERSION}/full/`

let signal = null // Int32Array(1) sobre un SharedArrayBuffer — 0=esperando, 1=valor listo
let lenView = null // DataView sobre el buffer de datos, primeros 4 bytes = longitud (Int32 LE)
let dataBytes = null // Uint8Array sobre el buffer de datos, a partir del byte 4

function stdinSync() {
  Atomics.store(signal, 0, 0)
  postMessage({ type: 'need-input' })
  // Bloqueo SÍNCRONO real del hilo del worker — no es un callback async ni
  // un polling: el hilo se detiene aquí hasta que el hilo principal escriba
  // el valor y llame Atomics.notify(). Esto es lo que el Spike B-0 dejó sin
  // verificar con código real.
  Atomics.wait(signal, 0, 0)
  const len = lenView.getInt32(0, true)
  const strBytes = dataBytes.slice(0, len)
  return new TextDecoder().decode(strBytes)
}

self.onmessage = async (e) => {
  const msg = e.data
  if (msg.type === 'init') {
    signal = new Int32Array(msg.signalSab)
    lenView = new DataView(msg.dataSab)
    dataBytes = new Uint8Array(msg.dataSab, 4)
    try {
      importScripts(`${PYODIDE_CDN}pyodide.js`)
      const pyodide = await self.loadPyodide({ indexURL: PYODIDE_CDN })
      self.__pyodide = pyodide
      postMessage({ type: 'ready' })
    } catch (err) {
      postMessage({ type: 'load-error', message: String(err) })
    }
    return
  }
  if (msg.type === 'run') {
    const pyodide = self.__pyodide
    const lines = []
    pyodide.setStdout({ batched: (s) => lines.push(s) })
    pyodide.setStdin({ stdin: stdinSync })
    try {
      pyodide.runPython(msg.code)
      postMessage({ type: 'result', stdout: lines.join('\n'), error: null })
    } catch (err) {
      postMessage({ type: 'result', stdout: lines.join('\n'), error: String(err) })
    }
  }
}
