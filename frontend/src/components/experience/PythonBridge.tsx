// Conecta la analogía recién resuelta (robot, sensor, ejemplo) con su forma
// real en Python — el estudiante entra a "Fundamentos de Python" pero puede
// pasar buena parte del módulo sin ver una sola línea de código; este puente
// aparece justo cuando la analogía ya está resuelta, mientras sigue fresca.
//
// Micropráctica interactiva (opcional, campo `practice`): "ahora hazlo tú" —
// el estudiante escribe Python real, ejecutado con Pyodide en el propio
// navegador (el Runtime nunca ejecuta código, solo recibe la evidencia).

import { useLayoutEffect, useMemo, useRef, useState } from 'react'
import { Code2, Eye, LifeBuoy, Loader2, Sparkles } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { CANCELLED_RESULT_ERROR, classifyPythonError, usePyodide, type PythonErrorCategory } from '@/hooks/usePyodide'
import { recordEvidence } from '@/lib/experiences/evidence'
import { useSubmitCycleEvidence } from '@/hooks/useStudent'
import type { PythonBridge as PythonBridgeDef, PythonMicroPracticeDef, PythonPracticeMode } from '@/types/moduleExperience'
import type { PracticeOutcome } from './OrderingPractice'

const MAX_ATTEMPTS_BEFORE_SOLUTION = 3

/** Progresión gradual para fluidez sostenida (ExperienceCursor.
 *  fluencyStreak en ModuleExperienceView, "un solo slice, sin Runtime, sin
 *  contenido nuevo"): en vez de arrancar siempre en el primer peldaño
 *  (observar — el más trivial: mirar el código correr, sin escribir nada),
 *  un estudiante con varios ciclos fluidos seguidos entra directamente unos
 *  peldaños más adelante en la MISMA cadena ya autorada (practice.
 *  nextStage...) — reutiliza exactamente el contenido existente, nunca
 *  genera uno nuevo. `n` acotado por el propio llamador (máx. 2, nunca
 *  aterriza en escritura libre) y por el largo real de la cadena aquí. */
function skipAhead(practice: PythonMicroPracticeDef, n: number): PythonMicroPracticeDef {
  let stage = practice
  for (let i = 0; i < n && stage.nextStage; i++) stage = stage.nextStage
  return stage
}

/** Encabezado de la tarjeta por peldaño — nombra la actividad real (nunca
 *  "Etapa X de Y"), mismo espíritu que `describeStageAdaptation`. Ausente
 *  `mode` (contenido previo al Sprint "Andamiaje completo") conserva el
 *  título original. */
const MODE_LABEL: Record<PythonPracticeMode, string> = {
  observar: 'Obsérvalo',
  manipular: 'Ahora tú: cambia un detalle',
  completar: 'Completa el código',
  corregir: 'Encuentra y corrige el error',
  escribir_parcial: 'Ahora hazlo tú',
  escribir_completo: 'Ahora profundiza',
}

/** Solo los peldaños de ESCRITURA (o contenido previo al andamiaje, sin
 *  `mode`) ceden ante "aplicacion" y arrancan en blanco — observar/
 *  manipular/completar/corregir dependen de que el scaffold autorado esté
 *  presente: es el ejercicio en sí, no un apoyo que un buen desempeño deba
 *  retirar. */
function shouldStartBlank(mode: PythonPracticeMode | undefined, profundidad: string | undefined): boolean {
  return profundidad === 'aplicacion' && (mode === undefined || mode === 'escribir_parcial' || mode === 'escribir_completo')
}

/** Diagnóstico genérico por categoría — verdadero para cualquier ejercicio,
 *  no autorado por contenido (a diferencia de `hintsByCategory`, que sí lo
 *  es). Nunca revela nada del ejercicio concreto, solo nombra lo que Python
 *  ya dijo en un lenguaje que un principiante entiende. */
const ERROR_CATEGORY_LABEL: Record<PythonErrorCategory, string> = {
  sintaxis: 'Python no pudo ni empezar a ejecutar tu código — algo en la escritura (comillas, paréntesis, dos puntos) no cuadra.',
  variables: 'Python buscó algo que todavía no existe — un nombre usado antes de crearlo.',
  logica: 'Tu código se ejecutó, pero algo en el camino no hizo lo que esperabas.',
  salida: 'Tu código corrió sin errores — pero lo que muestra no es exactamente lo pedido.',
}

// ── Editor / consola — puramente presentacionales (Sprint 1A) ──────────────
// Ningún componente de esta sección lee ni decide estado: reciben value/
// onChange/disabled ya calculados por PythonMicroPractice y solo cambian
// cómo se ven. Mismo contrato que el <textarea> plano que reemplazan.

/** "Ventana" de editor con gutter de líneas — mismo <textarea> controlado
 *  de siempre (value/onChange/disabled), solo con chrome visual alrededor.
 *  `wrap="off"` es la única diferencia de comportamiento del navegador: sin
 *  eso, una línea larga que envuelve visualmente desalinea el número de
 *  línea del gutter contra la línea real. No cambia el string que ve
 *  Pyodide (el wrap "soft" nunca insertaba saltos reales).
 *
 *  El gutter numera TODAS las líneas reales (no solo `visibleRows`) y
 *  sincroniza su scroll vertical con el del `<textarea>` — sin esto, un
 *  código de más de 12 líneas desalinea los números apenas el estudiante
 *  se desplaza (encontrado validando manualmente, no en revisión de
 *  código: el gutter quedaba fijo en 1-12 mientras el textarea ya
 *  mostraba líneas más abajo). Contenido autorado hoy llega como máximo
 *  a 6 líneas, pero el editor debe sostenerse igual si eso cambia.
 *
 *  La altura del gutter se MIDE del propio DOM (altura real de una de
 *  sus líneas, que comparte fuente/leading exactos con el `<textarea>`)
 *  en vez de un valor fijo — así no se desincroniza si cambia la
 *  tipografía o el `leading` de estas clases más adelante. */
function CodeEditorPanel({
  code,
  onChange,
  disabled,
}: {
  code: string
  onChange: (value: string) => void
  disabled: boolean
}) {
  const gutterRef = useRef<HTMLDivElement>(null)
  // Estimación previa a medir (13px * leading-relaxed 1.625) — solo evita
  // un salto de layout en el primer render; useLayoutEffect la reemplaza
  // por la altura real antes de que el navegador pinte.
  const [lineHeightPx, setLineHeightPx] = useState(21.125)
  const lineCount = code.split('\n').length
  const visibleRows = Math.min(12, Math.max(3, lineCount))

  useLayoutEffect(() => {
    const firstLine = gutterRef.current?.firstElementChild
    if (firstLine) setLineHeightPx(firstLine.getBoundingClientRect().height)
  }, [])

  return (
    <div className="rounded-xl border border-white/[0.1] bg-black/30 overflow-hidden transition-colors focus-within:border-neural-glow/50">
      <div className="flex items-center gap-1.5 px-3 py-1.5 border-b border-white/[0.06] bg-white/[0.02]">
        <span className="h-2.5 w-2.5 rounded-full bg-red-400/30" />
        <span className="h-2.5 w-2.5 rounded-full bg-amber-400/30" />
        <span className="h-2.5 w-2.5 rounded-full bg-emerald-400/30" />
        <span className="ml-2 text-[10px] font-mono text-neural-muted/40 tracking-wide">python3</span>
      </div>
      <div className="flex">
        <div
          ref={gutterRef}
          aria-hidden
          style={{ maxHeight: `${visibleRows * lineHeightPx}px` }}
          className="select-none overflow-hidden py-2 pl-3 pr-2 text-right font-mono text-[13px] leading-relaxed text-neural-muted/25"
        >
          {Array.from({ length: lineCount }, (_, i) => (
            <div key={i}>{i + 1}</div>
          ))}
        </div>
        <textarea
          value={code}
          onChange={e => onChange(e.target.value)}
          onScroll={e => {
            if (gutterRef.current) gutterRef.current.scrollTop = e.currentTarget.scrollTop
          }}
          disabled={disabled}
          rows={visibleRows}
          wrap="off"
          spellCheck={false}
          className="flex-1 bg-transparent px-3 py-2 font-mono text-[13px] leading-relaxed text-neural-text focus:outline-none disabled:opacity-70 overflow-x-auto"
        />
      </div>
    </div>
  )
}

/** Panel de salida tipo consola — mismo texto/condicionales de siempre
 *  (output/error), solo con chrome de terminal y un punto de estado en el
 *  header (neutral / advertencia) sin duplicar el mensaje textual que ya
 *  trae cada caso. */
function ConsoleOutput({
  output,
  error,
}: {
  output: string | null
  error: string | null
}) {
  if (output === null && !error) return null
  const dotColor = error ? 'bg-amber-400/60' : 'bg-neural-glow/50'
  return (
    <div className="rounded-xl border border-white/[0.08] bg-black/40 overflow-hidden">
      <div className="flex items-center gap-1.5 px-3 py-1 border-b border-white/[0.06] bg-white/[0.02]">
        <span className={`h-1.5 w-1.5 rounded-full ${dotColor}`} />
        <span className="text-[10px] font-mono text-neural-muted/40 tracking-wide">consola</span>
      </div>
      <div className="px-3 py-2 space-y-1.5">
        {output !== null && (
          <pre className="font-mono text-[12px] text-neural-text/80 whitespace-pre-wrap">
            {output || '(sin salida)'}
          </pre>
        )}
        {error && <p className="text-sm text-amber-400">{error}</p>}
      </div>
    </div>
  )
}

interface Props {
  bridge: PythonBridgeDef
  /** Solo obligatorios cuando `bridge.practice` existe (evidencia de la
   *  micropráctica). Los llamadores sin práctica interactiva pueden omitirlos. */
  moduleId?: string
  conceptId?: string
  /** Solo necesario cuando `bridge.practice.nextStage` existe: habilita la
   *  llamada real a cycle-evidence ENTRE etapas de una misma progresión (no
   *  solo al cerrar el ciclo completo) — mismo endpoint, mismo Runtime, sin
   *  agente nuevo. Sin `courseId` las etapas se encadenan igual, solo sin
   *  la nota de adaptación intermedia. */
  courseId?: string
  /** Se llama una sola vez, cuando la micropráctica queda resuelta o se reveló
   *  la solución — nunca antes, nunca bloquea el avance. Mismo contrato
   *  (`PracticeOutcome`) que la práctica de ordenamiento, para que el llamador
   *  pueda combinar ambas señales en la evidencia que recibe el Runtime. */
  onPracticeDone?: (outcome: PracticeOutcome) => void
  /** Profundidad ya decidida por Adaptar ANTES de esta micropráctica (RFC-0002
   *  §3): el pre-test registra evidencia real por competencia desde el primer
   *  día (Diagnosticar→Remediar/Orientar→Adaptar, sin capacidad nueva), pero
   *  esa cadena queda atada a la competencia del pre-test — la primera etapa
   *  de un módulo nunca la había leído y arrancaba siempre en el valor por
   *  defecto (más apoyo), sin importar el resultado real. Mismo vocabulario y
   *  mismo efecto que `applyStage` ya aplica ENTRE etapas — aquí solo siembra
   *  el mismo criterio en la etapa inicial. `undefined` conserva el
   *  comportamiento previo exacto (starterCode + sin aviso). */
  initialProfundidad?: string
  /** Peldaños de la escalera a saltar antes de mostrar el primero — ver
   *  `skipAhead()` arriba. `0`/`undefined` conserva el comportamiento previo
   *  exacto (arranca siempre en `bridge.practice`, el peldaño "observar"). */
  initialSkipStages?: number
}

export function PythonBridge({ bridge, moduleId = '', conceptId = '', courseId, onPracticeDone, initialProfundidad, initialSkipStages = 0 }: Props) {
  return (
    <div className="rounded-2xl border border-neural-glow/25 bg-neural-glow/[0.04] overflow-hidden animate-in fade-in slide-in-from-bottom-2 duration-500">
      <div className="flex items-center gap-2 px-5 py-3 border-b border-neural-glow/15">
        <Code2 className="h-4 w-4 text-neural-glow shrink-0" />
        <span className="text-[11px] font-mono tracking-[0.15em] uppercase text-neural-glow">
          {bridge.label}
        </span>
      </div>
      <pre className="px-5 py-4 overflow-x-auto text-[13px] leading-relaxed font-mono text-neural-text/90 whitespace-pre">
        <code>{bridge.code}</code>
      </pre>
      <p className="px-5 pb-4 text-sm text-neural-muted leading-relaxed">
        {bridge.explanation}
      </p>
      {bridge.practice && (
        <PythonMicroPractice
          practice={skipAhead(bridge.practice, initialSkipStages)}
          moduleId={moduleId}
          conceptId={conceptId}
          courseId={courseId}
          onDone={onPracticeDone}
          initialProfundidad={initialProfundidad}
        />
      )}
    </div>
  )
}

/** Nota breve entre etapas de una misma progresión, derivada de la
 *  respuesta REAL del Runtime (nunca texto de relleno) — mismo criterio
 *  que `describeAdaptation` en ModuleExperienceView, versión corta porque
 *  aquí no hay refuerzo que insertar, solo una micropráctica que continúa. */
function describeStageAdaptation(profundidad: string | undefined): string | null {
  if (profundidad === 'aplicacion') return 'Vas muy bien con esto — vamos con menos apoyo.'
  if (profundidad === 'fundamentos') return 'Vamos con calma en esta parte — aquí tienes más apoyo.'
  return null
}

function PythonMicroPractice({ practice, moduleId, conceptId, courseId, onDone, initialProfundidad }: {
  practice: PythonMicroPracticeDef
  moduleId: string
  conceptId: string
  courseId?: string
  onDone?: (outcome: PracticeOutcome) => void
  initialProfundidad?: string
}) {
  const { ready, loadError, run, awaitingInput, provideInput, cancelRun } = usePyodide()
  const submitCycleEvidence = useSubmitCycleEvidence()
  // `stage` es la etapa EN CURSO de la progresión (practice.nextStage.
  // nextStage...) — el estudiante nunca ve "Etapa 1 de 3": es la misma
  // tarjeta que va cambiando de prompt/código a medida que profundiza en el
  // mismo concepto. `practice` (el prop) sigue siendo la primera etapa.
  const [stage, setStage] = useState<PythonMicroPracticeDef>(practice)
  // Mismo criterio que applyStage: "aplicacion" retira el andamiaje desde el
  // arranque (reto en blanco), "fundamentos"/sin dato conserva el starter
  // precargado de siempre.
  const [code, setCode] = useState(shouldStartBlank(practice.mode, initialProfundidad) ? '' : practice.starterCode)
  const [attempts, setAttempts] = useState(0)
  const [output, setOutput] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [solved, setSolved] = useState(false)
  const [showSolution, setShowSolution] = useState(false)
  const [running, setRunning] = useState(false)
  // Valor que el estudiante está escribiendo para el input() real EN CURSO
  // (Commit 4, Épica B) — solo tiene sentido mientras `awaitingInput` es
  // true. Nunca se usa en el mecanismo legado (simulatedInputs), por el
  // contrato de compatibilidad ENGINEERING-GATE-EPICA-B.md §5.
  const [inputDraft, setInputDraft] = useState('')
  // POR QUÉ falló el último intento, no solo CUÁNTAS veces — deriva del error
  // real de Pyodide (o su ausencia), nunca de un conteo. Gobierna qué pista
  // y qué diagnóstico se muestran.
  const [lastCategory, setLastCategory] = useState<PythonErrorCategory | null>(null)
  // Evidencia ACUMULADA de las etapas ya superadas de esta misma cadena — el
  // Runtime SIGUE recibiendo un solo resultado combinado al terminar la
  // progresión completa (cycle-evidence de cierre de ciclo, sin cambios).
  // Lo nuevo es la llamada ADICIONAL por etapa, abajo: evidencia real ENTRE
  // etapas del mismo concepto, no solo al final.
  //
  // `priorAttempts` acumula ERRORES reales, no intentos ni peldaños (bug
  // real de la escalera, jul 2026): un peldaño resuelto al primer intento
  // aporta 0, nunca 1 — de lo contrario, superar los 6 peldaños de la
  // escalera sin ningún error se reportaba como "6 intentos" y el Runtime
  // (que resta 1 y compara contra un umbral de 2) marcaba erróneamente al
  // estudiante como "no dominada" solo por haber recorrido más pantallas.
  // La escalera es un mecanismo de aprendizaje, no de evaluación: superarla
  // completa sin errores debe seguir significando cero errores.
  const [priorAttempts, setPriorAttempts] = useState(0)
  const [priorSolutionShown, setPriorSolutionShown] = useState(false)
  // Regla 6 (jul 2026) — conteo informativo de peldaños, solo evidencia
  // local (recordEvidence, nunca cycle-evidence): no cambia ninguna decisión
  // del Runtime hoy, pero preserva la señal para una futura adaptación más
  // rica sin romper compatibilidad con `attempts`.
  const totalSteps = useMemo(() => {
    let n = 1
    let cur: PythonMicroPracticeDef | undefined = practice
    while (cur?.nextStage) {
      n += 1
      cur = cur.nextStage
    }
    return n
  }, [practice])
  const [stepIndex, setStepIndex] = useState(1)
  // Nota real de adaptación entre etapas (Pilar 2 — adaptación no solo entre
  // ciclos): se llena con la respuesta REAL de cycle-evidence, nunca un
  // texto fijo; `null` mientras no hay nada que decir todavía. En la etapa
  // inicial, si el pre-test ya decidió una profundidad para este módulo, se
  // siembra con el mismo mensaje que usaría applyStage entre etapas — nunca
  // texto nuevo, misma función.
  const [stageNote, setStageNote] = useState<string | null>(describeStageAdaptation(initialProfundidad))
  // Espera breve mientras el Runtime real decide la siguiente etapa — nunca
  // más de una llamada real (best-effort, ver applyStage/goToStage).
  const [deciding, setDeciding] = useState(false)
  // Etapa intermedia recién resuelta, esperando confirmación del estudiante
  // antes de avanzar (sprint "PythonBridge como entorno de aprendizaje
  // real", jul 2026): antes, un acierto en una etapa con `nextStage` movía
  // `applyStage`/`goToStage` en el MISMO ciclo síncrono que fijaba `output`,
  // así que React nunca llegaba a renderizar la salida correcta — el
  // estudiante avanzaba sin verla (bug real, no solo falta de explicación).
  // Ahora la etapa siguiente queda en espera aquí y la salida permanece
  // visible hasta que el estudiante confirma.
  const [pendingNextStage, setPendingNextStage] = useState<{ next: PythonMicroPracticeDef; attempts: number } | null>(null)
  // La decisión real ya NO solo cambia el texto: "fundamentos" adelanta el
  // apoyo (caso resuelto visible antes, solución disponible antes) y
  // "aplicacion" retira el andamiaje (arranca en blanco, sin la respuesta
  // anterior precargada) — mismo criterio de la escalera de remediación
  // (más o menos acompañamiento), aplicado ahora dentro de la progresión.
  const [earlyHelp, setEarlyHelp] = useState(initialProfundidad === 'fundamentos')

  // Mostrar la solución de una etapa intermedia NO termina la cadena de
  // golpe: el estudiante pidió verla, se queda visible hasta que decide
  // continuar (pendingContinue) — solo la ÚLTIMA etapa marca `done` real.
  const pendingContinue = showSolution && !!stage.nextStage
  const done = solved || (showSolution && !stage.nextStage)
  const attemptsBeforeSolution = earlyHelp ? 2 : MAX_ATTEMPTS_BEFORE_SOLUTION
  const workedExampleThreshold = earlyHelp ? 1 : 2
  const exhausted = attempts >= attemptsBeforeSolution

  const applyStage = (next: PythonMicroPracticeDef, profundidad: string | undefined) => {
    setStage(next)
    setCode(shouldStartBlank(next.mode, profundidad) ? '' : next.starterCode)
    setEarlyHelp(profundidad === 'fundamentos')
    setAttempts(0)
    setOutput(null)
    setError(null)
    setLastCategory(null)
    setShowSolution(false)
    setStageNote(describeStageAdaptation(profundidad))
    setDeciding(false)
    setPendingNextStage(null)
  }

  /** `stageAttempts` se recibe explícito, nunca leído de `attempts` por
   *  closure: cuando se llama justo tras `setAttempts(nextAttempts)` en el
   *  mismo evento (handleRun), React todavía no aplicó ese update — leerlo
   *  del closure enviaba `attempts: 0` al backend, que exige `ge=1` (bug
   *  real encontrado validando en navegador, no en revisión de código).
   *
   *  `stageAttempts` sigue siendo el conteo crudo de intentos de ESTA etapa
   *  (se envía tal cual al cycle-evidence POR ETAPA, abajo — el backend ya
   *  resta 1 correctamente ahí). Lo que se ACUMULA en `priorAttempts` es
   *  distinto: los ERRORES reales de esta etapa (0 si se resolvió al primer
   *  intento), para que la suma final entre etapas siga significando
   *  "errores totales", nunca "intentos" ni "peldaños recorridos". */
  const goToStage = (next: PythonMicroPracticeDef, solutionShownHere: boolean, stageAttempts: number) => {
    const stageErrors = solutionShownHere ? stageAttempts : Math.max(0, stageAttempts - 1)
    setPriorAttempts(prev => prev + stageErrors)
    setPriorSolutionShown(prev => prev || solutionShownHere)
    setStepIndex(prev => prev + 1)
    setStageNote(null)
    // Evidencia real de ESTA etapa (no la acumulada) hacia el mismo Runtime
    // que ya evalúa el ciclo completo — misma competencia, mismo endpoint,
    // sin agente nuevo. Best-effort: sin courseId, o si falla, la etapa
    // siguiente se aplica igual, solo sin decisión real (sin andamiaje extra
    // ni reto abierto) — nunca bloquea al estudiante.
    if (!courseId) {
      applyStage(next, undefined)
      return
    }
    setDeciding(true)
    submitCycleEvidence.mutate(
      { courseId, competencia: conceptId, attempts: stageAttempts, solved: !solutionShownHere },
      {
        onSuccess: (data: { runtime_decision?: { diseno?: Record<string, unknown> | null } | null }) => {
          const profundidad = data?.runtime_decision?.diseno?.profundidad
          applyStage(next, profundidad ? String(profundidad) : undefined)
        },
        onError: () => applyStage(next, undefined),
      },
    )
  }

  const handleRun = async () => {
    setRunning(true)
    // run() es async desde Épica B/Commit 2 (usePyodide.ts delega en un
    // Worker vía postMessage) — mismo comportamiento observable, solo
    // async donde antes era síncrono. Ver ENGINEERING-GATE-EPICA-B.md
    // §6, excepción de alcance del Commit 2.
    const result = await run(code, stage.simulatedInputs)
    setRunning(false)
    setOutput(result.stdout)
    setError(result.error)
    // Cancelación real (Commit 4b, "Cancelar" junto al panel de input()) —
    // no es un error de Python: no cuenta como intento, no genera evidencia
    // ni la pista categorizada de classifyPythonError (que le asignaría
    // 'logica' por defecto y mostraría un diagnóstico engañoso, ya que el
    // código nunca terminó de correr por sí solo). El mensaje ya quedó
    // visible arriba vía ConsoleOutput (setError).
    if (result.error === CANCELLED_RESULT_ERROR) return
    const nextAttempts = attempts + 1
    setAttempts(nextAttempts)
    const correct = !result.error && result.stdout.trim() === stage.expectedOutput.trim()
    recordEvidence({
      type: 'practice_attempt',
      moduleId,
      conceptId,
      detail: {
        practice: 'python', attempt: nextAttempts, status: correct ? 'correct' : 'incorrect', correct,
        stepIndex, stepsTotal: totalSteps,
      },
    })
    if (!correct) {
      setLastCategory(classifyPythonError(result.error))
      return
    }
    setLastCategory(null)
    if (stage.nextStage) {
      // No avanzar todavía: dejar la salida real visible (código→ejecución→
      // salida→explicación) hasta que el estudiante confirme con "Continuar".
      setPendingNextStage({ next: stage.nextStage, attempts: nextAttempts })
    } else {
      setSolved(true)
      // Última etapa: solo los intentos FALLIDOS de esta etapa son errores
      // (Regla 1) — el intento que acaba de acertar no se cuenta.
      onDone?.({ attempts: priorAttempts + Math.max(0, nextAttempts - 1), timeMs: 0, solutionShown: priorSolutionShown })
    }
  }

  /** Entrega al Worker el valor real que el estudiante escribió para el
   *  input() en curso — provideInput() ya despierta al worker y limpia
   *  `awaitingInput` (Commit 3, usePyodide.ts); aquí solo se limpia el
   *  campo local para el siguiente input() si la etapa pide más de uno. */
  const handleProvideInput = () => {
    provideInput(inputDraft)
    setInputDraft('')
  }

  /** Cancela la ejecución en curso mientras Python espera un input() real
   *  (Commit 4b) — cancelRun() resuelve run() con CANCELLED_RESULT_ERROR,
   *  que handleRun ya reconoce para no contarlo como intento. */
  const handleCancel = () => {
    cancelRun()
    setInputDraft('')
  }

  const handleContinueAfterCorrect = () => {
    if (!pendingNextStage) return
    goToStage(pendingNextStage.next, false, pendingNextStage.attempts)
  }

  const handleShowSolution = () => {
    recordEvidence({
      type: 'practice_attempt',
      moduleId,
      conceptId,
      detail: { practice: 'python', attempts, solutionShown: true, final: true, stepIndex, stepsTotal: totalSteps },
    })
    setShowSolution(true)
    if (!stage.nextStage) {
      // Nunca se resolvió esta etapa: todos los intentos fueron errores
      // reales (mismo criterio que ya usaba el backend para este caso).
      onDone?.({ attempts: priorAttempts + attempts, timeMs: 0, solutionShown: true })
    }
  }

  const handleContinueAfterSolution = () => {
    if (!stage.nextStage) return
    goToStage(stage.nextStage, true, attempts)
  }

  return (
    <div className="border-t border-neural-glow/15 px-5 py-4 space-y-3">
      <span className="inline-flex items-center rounded-full border border-neural-violet/25 bg-neural-violet/5 px-2.5 py-1 text-[11px] font-mono tracking-[0.15em] uppercase text-neural-violet">
        {MODE_LABEL[stage.mode ?? 'escribir_parcial']}
      </span>
      {/* Entre etapas, la tarjeta espera la decisión REAL del Runtime antes
          de mostrar la siguiente — breve (best-effort, nunca más de una
          llamada), pero real: la etapa que aparece después ya cambia según
          esa decisión (más apoyo / menos andamiaje), no solo el texto. */}
      {deciding ? (
        <div className="flex items-center gap-2 py-3 text-sm text-neural-muted">
          <Loader2 className="h-4 w-4 animate-spin text-neural-glow shrink-0" />
          Personalizando tu siguiente paso…
        </div>
      ) : (
        <>
          {stageNote && (
            <div className="flex items-start gap-2 rounded-lg border border-neural-glow/20 bg-neural-glow/5 px-3 py-2">
              <Sparkles className="h-3.5 w-3.5 text-neural-glow shrink-0 mt-0.5" />
              <p className="text-sm text-neural-glow/90 leading-relaxed">{stageNote}</p>
            </div>
          )}
          <p className="text-sm text-neural-text/90">{stage.prompt}</p>
      {/* input() no tiene terminal real en el navegador: en vez de ocultar el
          valor simulado, se muestra explícitamente — el estudiante ve QUÉ
          escribe el usuario simulado, nunca un dato que aparece de la nada. */}
      {stage.simulatedInputs && stage.simulatedInputs.length > 0 && (
        <div className="rounded-xl border border-neural-violet/20 bg-neural-violet/[0.04] px-3 py-2.5 space-y-1">
          <p className="text-[11px] font-mono tracking-[0.15em] uppercase text-neural-violet/80 mb-1">
            Simularemos que el usuario escribe
          </p>
          {stage.simulatedInputs.map((value, i) => (
            <p key={i} className="font-mono text-[13px] text-neural-text/90">
              <span className="text-neural-violet/50">{'>'}</span> {value}
            </p>
          ))}
        </div>
      )}
      <CodeEditorPanel
        code={code}
        onChange={setCode}
        disabled={done || showSolution || stage.mode === 'observar' || !!pendingNextStage || awaitingInput}
      />
      <div className="flex items-center gap-2 flex-wrap">
        <Button size="sm" onClick={handleRun} disabled={!ready || done || showSolution || running || !!pendingNextStage} className="gap-2">
          {running && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
          {ready ? 'Ejecutar →' : 'Cargando Python…'}
        </Button>
        {!done && !showSolution && !pendingNextStage && exhausted && (
          <Button size="sm" variant="ghost" onClick={handleShowSolution}>
            Ver solución
          </Button>
        )}
        {pendingContinue && (
          <Button size="sm" onClick={handleContinueAfterSolution} className="gap-2">
            Continuar →
          </Button>
        )}
        {pendingNextStage && (
          <Button size="sm" onClick={handleContinueAfterCorrect} className="gap-2">
            Continuar →
          </Button>
        )}
      </div>
      {loadError && <p className="text-sm text-red-400">{loadError}</p>}
      {/* Panel de input() real EN VIVO (Commit 4, Épica B) — aparece solo
          mientras el Worker está bloqueado esperando la respuesta que el
          propio estudiante escribe, a diferencia del panel "Simularemos que
          el usuario escribe" (arriba), que muestra un valor ya fijado ANTES
          de ejecutar. Cancelar la ejecución completa queda para un commit
          aparte (ENGINEERING-GATE-EPICA-B.md, decisión de alcance del
          Commit 4) — por ahora el estudiante solo puede responder. */}
      {awaitingInput && (
        <div className="rounded-xl border-2 border-neural-glow/40 bg-neural-glow/[0.04] px-3 py-2.5 space-y-2">
          <p className="text-[11px] font-mono tracking-[0.15em] uppercase text-neural-glow">
            Python está esperando tu respuesta
          </p>
          <div className="flex items-center gap-2">
            <input
              type="text"
              value={inputDraft}
              onChange={e => setInputDraft(e.target.value)}
              onKeyDown={e => {
                if (e.key === 'Enter') handleProvideInput()
              }}
              autoFocus
              className="flex-1 rounded-lg border border-white/[0.1] bg-black/30 px-3 py-1.5 font-mono text-[13px] text-neural-text focus:outline-none focus:border-neural-glow/50"
            />
            <Button size="sm" onClick={handleProvideInput}>
              Enviar →
            </Button>
            <Button size="sm" variant="ghost" onClick={handleCancel}>
              Cancelar
            </Button>
          </div>
        </div>
      )}
      {!showSolution && <ConsoleOutput output={output} error={error} />}
      {/* Tras un acierto (etapa intermedia en espera de "Continuar", o la
          última etapa ya resuelta): la salida ya se ve arriba — aquí solo la
          frase que conecta concepto+instrucción+resultado, cuando el
          contenido la trae (sprint "PythonBridge como entorno de aprendizaje
          real"). Sin `resultExplanation` autorada, el peldaño se ve igual
          que antes de este sprint. */}
      {(pendingNextStage || solved) && stage.resultExplanation && (
        <div className="rounded-lg border border-emerald-500/25 bg-emerald-500/5 px-3 py-2 space-y-1">
          <p className="text-[11px] font-mono tracking-[0.15em] uppercase text-emerald-400">Por qué pasó esto</p>
          <p className="text-sm text-neural-text/80 leading-relaxed">{stage.resultExplanation}</p>
        </div>
      )}
      {/* La ayuda responde a POR QUÉ falló (lastCategory), no solo a cuántas
          veces — antes, un error real (SyntaxError/NameError) nunca mostraba
          pista alguna; ahora toda categoría tiene su propio diagnóstico. */}
      {!done && !showSolution && lastCategory && (
        <div className="space-y-1.5">
          <div className="flex items-start gap-2">
            <Eye className="h-3.5 w-3.5 text-neural-glow shrink-0 mt-0.5" />
            <p className="text-sm text-neural-glow/90 leading-relaxed">{ERROR_CATEGORY_LABEL[lastCategory]}</p>
          </div>
          <p className="text-sm text-neural-muted">
            {stage.hintsByCategory?.[lastCategory] ?? stage.hint}
          </p>
        </div>
      )}
      {/* Apoyo tras el 2º intento fallido — un caso ANÁLOGO, nunca la solución
          del propio ejercicio (mismo criterio que la escalera de remediación:
          más acompañamiento antes de ofrecer la respuesta, nunca en su lugar). */}
      {!done && !showSolution && !pendingNextStage && attempts >= workedExampleThreshold && stage.workedExample && (
        <div className="rounded-lg border border-neural-violet/25 bg-neural-violet/5 px-3 py-2.5 space-y-2">
          <div className="flex items-center gap-2">
            <LifeBuoy className="h-3.5 w-3.5 text-neural-violet shrink-0" />
            <p className="text-[11px] font-mono tracking-[0.15em] uppercase text-neural-violet">
              Apoyo — veamos un caso parecido
            </p>
          </div>
          <pre className="font-mono text-[13px] text-neural-text/90 whitespace-pre">{stage.workedExample.code}</pre>
          <p className="text-sm text-neural-muted">→ {stage.workedExample.output}</p>
          <p className="text-sm text-neural-text/80 leading-relaxed">{stage.workedExample.explanation}</p>
        </div>
      )}
      {solved && (
        <p className="text-sm text-emerald-400">
          ✓ Exacto — eso es Python real haciendo lo que pediste.
        </p>
      )}
      {pendingNextStage && (
        <p className="text-sm text-emerald-400">
          ✓ Exacto — así se ve en pantalla.
        </p>
      )}
      {showSolution && (
        <div className="rounded-lg border border-neural-violet/25 bg-neural-violet/5 px-3 py-2 space-y-1">
          <p className="text-[11px] font-mono tracking-[0.15em] uppercase text-neural-violet">Solución</p>
          <pre className="font-mono text-[13px] text-neural-text/90 whitespace-pre">{stage.solutionCode}</pre>
        </div>
      )}
        </>
      )}
    </div>
  )
}
