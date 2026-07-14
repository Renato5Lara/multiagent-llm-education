// Python real ejecutándose en el navegador (WebAssembly, vía Pyodide) — el
// Runtime nunca ejecuta código del estudiante, solo recibe la evidencia que
// producen sus intentos. Carga perezosa y compartida: el WASM (~6-10MB) solo
// se descarga la primera vez que una micropráctica de Python aparece en
// pantalla, y una sola instancia se reutiliza en toda la sesión del navegador.

import { useEffect, useRef, useState } from 'react'

const PYODIDE_VERSION = '0.26.2'
const PYODIDE_CDN = `https://cdn.jsdelivr.net/pyodide/v${PYODIDE_VERSION}/full/`

interface PyodideInterface {
  runPython: (code: string) => unknown
  setStdout: (options: { batched: (output: string) => void }) => void
}

declare global {
  interface Window {
    loadPyodide?: (config: { indexURL: string }) => Promise<PyodideInterface>
  }
}

let pyodideSingleton: Promise<PyodideInterface> | null = null

function loadScript(src: string): Promise<void> {
  return new Promise((resolve, reject) => {
    if (document.querySelector(`script[src="${src}"]`)) {
      resolve()
      return
    }
    const script = document.createElement('script')
    script.src = src
    script.onload = () => resolve()
    script.onerror = () => reject(new Error('No se pudo cargar Python en el navegador.'))
    document.head.appendChild(script)
  })
}

function getPyodide(): Promise<PyodideInterface> {
  if (!pyodideSingleton) {
    pyodideSingleton = loadScript(`${PYODIDE_CDN}pyodide.js`).then(() => {
      if (!window.loadPyodide) throw new Error('Python no se inicializó correctamente.')
      return window.loadPyodide({ indexURL: PYODIDE_CDN })
    })
  }
  return pyodideSingleton
}

export interface PythonRunResult {
  stdout: string
  error: string | null
}

export function usePyodide() {
  const [ready, setReady] = useState(false)
  const [loadError, setLoadError] = useState<string | null>(null)
  const pyodideRef = useRef<PyodideInterface | null>(null)

  useEffect(() => {
    let cancelled = false
    getPyodide()
      .then(py => {
        if (cancelled) return
        pyodideRef.current = py
        setReady(true)
      })
      .catch((err: unknown) => {
        if (cancelled) return
        setLoadError(err instanceof Error ? err.message : 'Error cargando Python.')
      })
    return () => {
      cancelled = true
    }
  }, [])

  const run = (code: string): PythonRunResult => {
    const py = pyodideRef.current
    if (!py) return { stdout: '', error: 'Python todavía no está listo.' }
    const lines: string[] = []
    py.setStdout({ batched: (output: string) => lines.push(output) })
    try {
      py.runPython(code)
      return { stdout: lines.join('\n'), error: null }
    } catch (err) {
      return { stdout: lines.join('\n'), error: err instanceof Error ? err.message : String(err) }
    }
  }

  return { ready, loadError, run }
}
