// Spike B-1 — hilo principal: crea el worker, arma el SharedArrayBuffer de
// señal y el buffer de datos, y hace de "estudiante simulado" respondiendo
// el prompt real cuando el worker lo pide.

document.getElementById('coi').textContent = String(self.crossOriginIsolated)

const statusEl = document.getElementById('status')
const runBtn = document.getElementById('runBtn')
const outputEl = document.getElementById('output')
const inputPanel = document.getElementById('inputPanel')
const inputPrompt = document.getElementById('inputPrompt')
const inputValue = document.getElementById('inputValue')
const submitBtn = document.getElementById('submitInput')

if (!self.crossOriginIsolated) {
  statusEl.textContent = 'BLOQUEADO: crossOriginIsolated=false — SharedArrayBuffer no disponible. Revisa cabeceras COOP/COEP.'
  throw new Error('crossOriginIsolated=false')
}

const signalSab = new SharedArrayBuffer(4)
const dataSab = new SharedArrayBuffer(4 + 1024)
const signal = new Int32Array(signalSab)

const worker = new Worker('worker.js')
let inputRequestCount = 0

worker.onmessage = (e) => {
  const msg = e.data
  if (msg.type === 'ready') {
    statusEl.textContent = 'worker: Pyodide listo'
    runBtn.disabled = false
  } else if (msg.type === 'load-error') {
    statusEl.textContent = 'worker: ERROR cargando Pyodide — ' + msg.message
  } else if (msg.type === 'need-input') {
    inputRequestCount++
    statusEl.textContent = `worker: BLOQUEADO esperando input() real #${inputRequestCount} (Atomics.wait en curso)`
    inputPrompt.textContent = `Python pidió input() #${inputRequestCount}:`
    inputPanel.style.display = 'block'
    inputValue.value = ''
    inputValue.focus()
  } else if (msg.type === 'result') {
    statusEl.textContent = 'worker: ejecución terminada'
    outputEl.textContent = (msg.stdout || '(sin salida)') + (msg.error ? '\n\nERROR: ' + msg.error : '')
    runBtn.disabled = false
  }
}

worker.postMessage({ type: 'init', signalSab, dataSab })

runBtn.addEventListener('click', () => {
  runBtn.disabled = true
  outputEl.textContent = ''
  inputRequestCount = 0
  worker.postMessage({ type: 'run', code: document.getElementById('code').value })
})

submitBtn.addEventListener('click', () => {
  const value = inputValue.value
  const encoded = new TextEncoder().encode(value)
  const view = new DataView(dataSab)
  view.setInt32(0, encoded.length, true)
  new Uint8Array(dataSab, 4).set(encoded)
  inputPanel.style.display = 'none'
  statusEl.textContent = `worker: valor "${value}" enviado, reanudando...`
  Atomics.store(signal, 0, 1)
  Atomics.notify(signal, 0)
})
