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
  setStdout: (options: { write: (buffer: Uint8Array) => number }) => void
  setStdin: (options: { stdin: () => string | null }) => void
}

declare global {
  interface Window {
    loadPyodide?: (config: { indexURL: string }) => Promise<PyodideInterface>
  }
}

let pyodideSingleton: Promise<PyodideInterface> | null = null

/** Borra los nombres creados por el estudiante en ejecuciones anteriores
 *  (el intérprete es un singleton compartido por toda la sesión). Solo los
 *  nombres "visibles" — los internos (`__builtins__`, etc.) empiezan con
 *  guion bajo y se conservan. */
const RESET_USER_GLOBALS =
  'for _k in [k for k in list(globals()) if not k.startswith("_")]:\n    del globals()[_k]'

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

  /** `stdinValues`: respuestas simuladas de input(), en el orden en que el
   *  código las consume.
   *
   *  Sprint UX-04 — cada ejecución es un mundo limpio (tres bugs reales,
   *  verificados en navegador):
   *  1. stdout se captura por BYTES (`write`), no por líneas (`batched`):
   *     antes, el prompt de input() (sin salto de línea) se PERDÍA cuando el
   *     código fallaba después — el estudiante veía la consola vacía y un
   *     traceback, nunca la pregunta que su programa sí alcanzó a mostrar.
   *  2. stdin se REINICIA siempre: antes, las respuestas simuladas de una
   *     ejecución anterior quedaban pegadas al intérprete compartido — "Ana"
   *     aparecía como respuesta automática en ejercicios que no la pedían.
   *     Agotadas las respuestas (o sin ninguna), input() recibe fin de
   *     entrada (EOFError) — un error explicable, nunca un '' silencioso.
   *  3. los globals del estudiante se LIMPIAN antes de cada ejecución: una
   *     variable creada en una etapa anterior ya no puede hacer pasar (ni
   *     fallar) el código de la siguiente — cada Run se comporta como
   *     Python de verdad ejecutando un archivo desde cero. */
  const run = (code: string, stdinValues?: string[]): PythonRunResult => {
    const py = pyodideRef.current
    if (!py) return { stdout: '', error: 'Python todavía no está listo.' }
    const decoder = new TextDecoder()
    let captured = ''
    py.setStdout({
      write: (buffer: Uint8Array) => {
        captured += decoder.decode(buffer, { stream: true })
        return buffer.length
      },
    })
    let cursor = 0
    const values = stdinValues ?? []
    py.setStdin({ stdin: () => (cursor < values.length ? values[cursor++] : null) })
    try {
      py.runPython(RESET_USER_GLOBALS)
      py.runPython(code)
      captured += decoder.decode()
      return { stdout: captured, error: null }
    } catch (err) {
      captured += decoder.decode()
      return { stdout: captured, error: err instanceof Error ? err.message : String(err) }
    }
  }

  return { ready, loadError, run }
}
