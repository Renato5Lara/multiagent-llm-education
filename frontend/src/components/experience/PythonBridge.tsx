// Conecta la analogía recién resuelta (robot, sensor, ejemplo) con su forma
// real en Python — el estudiante entra a "Fundamentos de Python" pero puede
// pasar buena parte del módulo sin ver una sola línea de código; este puente
// aparece justo cuando la analogía ya está resuelta, mientras sigue fresca.
//
// Micropráctica interactiva (opcional, campo `practice`): "ahora hazlo tú" —
// el estudiante escribe Python real, ejecutado con Pyodide en el propio
// navegador (el Runtime nunca ejecuta código, solo recibe la evidencia).

import { useMemo, useState, type ReactNode } from 'react'
import { Code2, Eye, GraduationCap, LifeBuoy, Loader2, Sparkles } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import { classifyPythonError, parsePythonError, usePyodide, type PythonErrorCategory } from '@/hooks/usePyodide'
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

/** Sprint UX-04 — el error como material de aprendizaje, nunca solo un
 *  traceback: señala la LÍNEA del código del estudiante, la muestra
 *  resaltada, traduce la excepción a lenguaje de principiante, y deja el
 *  detalle técnico original disponible sin imponerlo. El botón Ejecutar
 *  sigue activo — reintentar es siempre el siguiente paso natural. */
function PythonErrorCard({ error, code }: { error: string; code: string }) {
  const parsed = parsePythonError(error)
  const codeLines = code.split('\n')
  const offendingLine =
    parsed.line !== null && parsed.line >= 1 && parsed.line <= codeLines.length
      ? codeLines[parsed.line - 1]
      : null
  return (
    <div className="rounded-lg border border-amber-500/30 bg-amber-500/5 px-3.5 py-3 space-y-2">
      <p className="text-[11px] font-mono tracking-[0.15em] uppercase text-amber-400">
        {parsed.line !== null ? `Error en la línea ${parsed.line} — ${parsed.name}` : `Error — ${parsed.name}`}
      </p>
      {offendingLine !== null && offendingLine.trim() !== '' && (
        <pre className="rounded-md border border-amber-500/25 bg-black/40 px-3 py-1.5 font-mono text-[13px] text-amber-200 whitespace-pre overflow-x-auto">
          {offendingLine}
        </pre>
      )}
      <p className="text-sm text-neural-text/90 leading-relaxed">
        {parsed.translation ?? (parsed.message || 'Python no pudo ejecutar el código.')}
      </p>
      <p className="text-xs text-neural-muted/80">
        Corrige la línea y vuelve a presionar <span className="font-semibold text-neural-text/80">Ejecutar</span> — equivocarse y reintentar es exactamente cómo se aprende a programar.
      </p>
      <details className="text-xs text-neural-muted/60">
        <summary className="cursor-pointer select-none">Ver el mensaje original de Python</summary>
        <pre className="mt-1.5 font-mono text-[11px] whitespace-pre-wrap break-words opacity-80">{error}</pre>
      </details>
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
  /** Sprint UX-02 "Laboratorio adaptativo": 'lab' reorganiza las MISMAS
   *  piezas en tres zonas a pantalla ancha — contexto (explicación del
   *  puente + `aside`) a la izquierda, editor grande con consola siempre
   *  visible al centro, y el tutor contextual (pistas, caso análogo,
   *  errores, retroalimentación) a la derecha, solo cuando tiene algo que
   *  decir. Ausente/'inline' = presentación previa exacta (tarjeta única
   *  apilada) — ningún otro llamador cambia. Solo presentación: estado,
   *  intentos, evidencia y decisiones del Runtime son idénticos. */
  layout?: 'inline' | 'lab'
  /** Solo layout 'lab': contenido adicional del panel izquierdo (objetivo
   *  del ciclo, infografía, ayudas) — lo compone el llamador, que es quien
   *  conoce el concepto; el puente no aprende ningún concepto nuevo. */
  aside?: ReactNode
}

export function PythonBridge({ bridge, moduleId = '', conceptId = '', courseId, onPracticeDone, initialProfundidad, initialSkipStages = 0, layout = 'inline', aside }: Props) {
  const explanationCard = (
    <div className="rounded-2xl border border-neural-glow/25 bg-neural-glow/[0.04] overflow-hidden">
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
    </div>
  )

  if (layout === 'lab' && bridge.practice) {
    // UX-05: la columna de contexto cede ancho al editor — sigue siendo
    // cómoda de leer (260-320px), pero deja de competir con el editor por
    // el espacio disponible.
    return (
      <div className="grid gap-5 items-start lg:grid-cols-[minmax(260px,320px)_minmax(0,1fr)] animate-in fade-in slide-in-from-bottom-2 duration-500">
        <div className="space-y-5 lg:sticky lg:top-4">
          {explanationCard}
          {aside}
        </div>
        <PythonMicroPractice
          practice={skipAhead(bridge.practice, initialSkipStages)}
          moduleId={moduleId}
          conceptId={conceptId}
          courseId={courseId}
          onDone={onPracticeDone}
          initialProfundidad={initialProfundidad}
          layout="lab"
        />
      </div>
    )
  }

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

function PythonMicroPractice({ practice, moduleId, conceptId, courseId, onDone, initialProfundidad, layout = 'inline' }: {
  practice: PythonMicroPracticeDef
  moduleId: string
  conceptId: string
  courseId?: string
  onDone?: (outcome: PracticeOutcome) => void
  initialProfundidad?: string
  layout?: 'inline' | 'lab'
}) {
  const { ready, loadError, run } = usePyodide()
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

  const handleRun = () => {
    setRunning(true)
    const result = run(code, stage.simulatedInputs)
    setRunning(false)
    setOutput(result.stdout)
    setError(result.error)
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

  // ── Bloques de UI (Sprint UX-02) ──────────────────────────────────────────
  // Cada pieza se define UNA vez y se compone según el layout: 'inline'
  // conserva exactamente el orden apilado previo; 'lab' reparte las mismas
  // piezas entre el centro (editor + consola) y el tutor contextual de la
  // derecha. Solo presentación — ningún estado ni handler cambia.
  const labMode = layout === 'lab'

  const stageNoteBlock = stageNote && (
    <div className="flex items-start gap-2 rounded-lg border border-neural-glow/20 bg-neural-glow/5 px-3 py-2">
      <Sparkles className="h-3.5 w-3.5 text-neural-glow shrink-0 mt-0.5" />
      <p className="text-sm text-neural-glow/90 leading-relaxed">{stageNote}</p>
    </div>
  )

  const promptBlock = <p className="text-sm text-neural-text/90">{stage.prompt}</p>

  // input() no tiene terminal real en el navegador: en vez de ocultar el
  // valor simulado, se muestra explícitamente — el estudiante ve QUÉ
  // escribe el usuario simulado, nunca un dato que aparece de la nada.
  const simulatedInputsBlock = stage.simulatedInputs && stage.simulatedInputs.length > 0 && (
    <div className="rounded-lg border border-neural-violet/25 bg-neural-violet/5 px-3 py-2 space-y-1.5">
      <p className="text-[11px] font-mono tracking-[0.15em] uppercase text-neural-violet">
        Simularemos que el usuario escribe
      </p>
      {stage.simulatedInputs.map((value, i) => (
        <p key={i} className="font-mono text-[13px] text-neural-text/90">
          {value}
        </p>
      ))}
    </div>
  )

  // El editor crece con el código (acotado) para que escribir sea cómodo sin
  // scroll interno — UX-04 extiende al modo inline lo que el laboratorio ya
  // hacía: la franja fija de 3 líneas quedaba demasiado pequeña apenas el
  // ejercicio pasaba de una línea. UX-05: en el laboratorio, el editor
  // también gana un alto mínimo generoso (no solo "cabe el código") — el
  // estudiante programa ahí, necesita verlo cómodo incluso con una línea.
  const editorRows = labMode
    ? Math.min(20, Math.max(10, code.split('\n').length + 3))
    : Math.min(12, Math.max(5, code.split('\n').length + 2))
  const editorBlock = (
    <textarea
      value={code}
      onChange={e => setCode(e.target.value)}
      disabled={done || showSolution || stage.mode === 'observar' || !!pendingNextStage}
      rows={editorRows}
      spellCheck={false}
      className={cn(
        'w-full rounded-lg border border-white/[0.1] bg-black/30 px-3 py-2 font-mono text-neural-text focus:outline-none focus:border-neural-glow/50 disabled:opacity-70',
        labMode ? 'text-[14px] leading-relaxed min-h-[300px]' : 'text-[13px]',
      )}
    />
  )

  const actionsBlock = (
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
  )

  const loadErrorBlock = loadError && <p className="text-sm text-red-400">{loadError}</p>

  const outputVisible = output !== null && !showSolution
  const outputBlock = outputVisible && (
    <div className="rounded-lg bg-black/40 border border-white/[0.08] px-3 py-2 font-mono text-[12px] text-neural-text/80 whitespace-pre-wrap">
      {output || '(sin salida)'}
    </div>
  )
  // Laboratorio: la consola SIEMPRE está visible — antes de ejecutar muestra
  // una invitación, nunca un hueco que aparece y desaparece. UX-05: gana un
  // alto mínimo (antes era una franja de una sola línea) para que se sienta
  // una zona propia de la pantalla, no una nota al pie del editor.
  const consoleBlock = (
    <div className="rounded-lg bg-black/40 border border-white/[0.08] px-3.5 py-3 space-y-1.5 min-h-[92px]">
      <p className="text-[10px] font-mono tracking-[0.15em] uppercase text-neural-muted/70">Consola de salida</p>
      {outputVisible ? (
        <p className="font-mono text-[13px] text-neural-text/80 whitespace-pre-wrap">{output || '(sin salida)'}</p>
      ) : (
        <p className="font-mono text-[12px] text-neural-muted/50 italic">Ejecuta tu código para ver aquí la salida…</p>
      )}
    </div>
  )

  // UX-04: nunca solo el traceback — línea señalada y resaltada, explicación
  // en lenguaje de estudiante, y el mensaje original disponible sin imponerlo.
  const rawErrorBlock = error && !showSolution && <PythonErrorCard error={error} code={code} />

  // Tras un acierto (etapa intermedia en espera de "Continuar", o la
  // última etapa ya resuelta): la salida ya se ve arriba — aquí solo la
  // frase que conecta concepto+instrucción+resultado, cuando el
  // contenido la trae (sprint "PythonBridge como entorno de aprendizaje
  // real"). Sin `resultExplanation` autorada, el peldaño se ve igual
  // que antes de este sprint.
  const resultExplanationBlock = (pendingNextStage || solved) && stage.resultExplanation && (
    <div className="rounded-lg border border-emerald-500/25 bg-emerald-500/5 px-3 py-2 space-y-1">
      <p className="text-[11px] font-mono tracking-[0.15em] uppercase text-emerald-400">Por qué pasó esto</p>
      <p className="text-sm text-neural-text/80 leading-relaxed">{stage.resultExplanation}</p>
    </div>
  )

  // La ayuda responde a POR QUÉ falló (lastCategory), no solo a cuántas
  // veces — antes, un error real (SyntaxError/NameError) nunca mostraba
  // pista alguna; ahora toda categoría tiene su propio diagnóstico.
  const errorHelpBlock = !done && !showSolution && lastCategory && (
    <div className="space-y-1.5">
      <div className="flex items-start gap-2">
        <Eye className="h-3.5 w-3.5 text-neural-glow shrink-0 mt-0.5" />
        <p className="text-sm text-neural-glow/90 leading-relaxed">{ERROR_CATEGORY_LABEL[lastCategory]}</p>
      </div>
      <p className="text-sm text-neural-muted">
        {stage.hintsByCategory?.[lastCategory] ?? stage.hint}
      </p>
    </div>
  )

  // Apoyo tras el 2º intento fallido — un caso ANÁLOGO, nunca la solución
  // del propio ejercicio (mismo criterio que la escalera de remediación:
  // más acompañamiento antes de ofrecer la respuesta, nunca en su lugar).
  const workedExampleBlock = !done && !showSolution && !pendingNextStage && attempts >= workedExampleThreshold && stage.workedExample && (
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
  )

  const solvedBlock = solved && (
    <p className="text-sm text-emerald-400">
      ✓ Exacto — eso es Python real haciendo lo que pediste.
    </p>
  )
  const pendingCorrectBlock = pendingNextStage && (
    <p className="text-sm text-emerald-400">
      ✓ Exacto — así se ve en pantalla.
    </p>
  )

  const solutionBlock = showSolution && (
    <div className="rounded-lg border border-neural-violet/25 bg-neural-violet/5 px-3 py-2 space-y-1">
      <p className="text-[11px] font-mono tracking-[0.15em] uppercase text-neural-violet">Solución</p>
      <pre className="font-mono text-[13px] text-neural-text/90 whitespace-pre">{stage.solutionCode}</pre>
    </div>
  )

  const modeLabelBlock = (
    <p className="text-[11px] font-mono tracking-[0.15em] uppercase text-neural-violet">
      {MODE_LABEL[stage.mode ?? 'escribir_parcial']}
    </p>
  )

  // Entre etapas, la tarjeta espera la decisión REAL del Runtime antes
  // de mostrar la siguiente — breve (best-effort, nunca más de una
  // llamada), pero real: la etapa que aparece después ya cambia según
  // esa decisión (más apoyo / menos andamiaje), no solo el texto.
  const decidingBlock = (
    <div className="flex items-center gap-2 py-3 text-sm text-neural-muted">
      <Loader2 className="h-4 w-4 animate-spin text-neural-glow shrink-0" />
      Personalizando tu siguiente paso…
    </div>
  )

  if (labMode) {
    // Tutor contextual (derecha): SOLO aparece cuando tiene algo que aportar
    // — nota de adaptación, diagnóstico del error, caso análogo,
    // retroalimentación del acierto o solución. Sin contenido, el editor
    // ocupa todo el ancho: nunca un chat vacío permanente.
    const tutorBlocks = [stageNoteBlock, errorHelpBlock, workedExampleBlock, resultExplanationBlock, solutionBlock].filter(Boolean)
    const tutorVisible = !deciding && tutorBlocks.length > 0
    // UX-05: el tutor cede ancho al editor — sigue siendo legible
    // (220-280px), pero deja de repartirse el ancho a partes casi iguales
    // con la zona donde el estudiante realmente programa.
    return (
      <div className={cn('grid gap-5 items-start', tutorVisible && 'xl:grid-cols-[minmax(0,1fr)_minmax(220px,280px)]')}>
        <div className="rounded-2xl border border-neural-glow/25 bg-neural-glow/[0.04] px-5 py-4 space-y-3">
          {modeLabelBlock}
          {deciding ? decidingBlock : (
            <>
              {promptBlock}
              {simulatedInputsBlock}
              {editorBlock}
              {actionsBlock}
              {loadErrorBlock}
              {consoleBlock}
              {rawErrorBlock}
              {solvedBlock}
              {pendingCorrectBlock}
            </>
          )}
        </div>
        {tutorVisible && (
          <aside className="rounded-2xl border border-white/[0.08] bg-white/[0.02] p-4 space-y-3 xl:sticky xl:top-4 animate-in fade-in slide-in-from-right-2 duration-300">
            <div className="flex items-center gap-2">
              <GraduationCap className="h-4 w-4 text-neural-glow shrink-0" />
              <p className="text-[11px] font-mono tracking-[0.15em] uppercase text-neural-glow">Tutor</p>
            </div>
            {tutorBlocks}
          </aside>
        )}
      </div>
    )
  }

  return (
    <div className="border-t border-neural-glow/15 px-5 py-4 space-y-3">
      {modeLabelBlock}
      {deciding ? decidingBlock : (
        <>
          {stageNoteBlock}
          {promptBlock}
          {simulatedInputsBlock}
          {editorBlock}
          {actionsBlock}
          {loadErrorBlock}
          {outputBlock}
          {rawErrorBlock}
          {resultExplanationBlock}
          {errorHelpBlock}
          {workedExampleBlock}
          {solvedBlock}
          {pendingCorrectBlock}
          {solutionBlock}
        </>
      )}
    </div>
  )
}
