// Experiencia de Módulo — orquesta el patrón congelado (jul 2026):
// apertura de curiosidad → ciclos [concepto multimodal → práctica universal →
// feedback → momento de decisión] → cierre del incremento.
// La evidencia se registra localmente (mapa de dominio, cursor) Y, desde el
// refinamiento de evaluación continua, entra al Runtime real al cerrar cada
// ciclo (ver advanceCycle) — el mismo contrato que ya usaba la Evaluación de
// Módulo, solo que ahora también se dispara aquí.

import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import {
  ArrowLeft, BookOpen, CheckCircle2, Compass, FlaskConical, GraduationCap, LifeBuoy, Map, Route, TrendingUp,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import { CuriosityOpening } from './CuriosityOpening'
import { ConceptStep } from './ConceptStep'
import { AnimatedScene } from './AnimatedScene'
import { AudioNarration } from './AudioNarration'
import { PythonBridge } from './PythonBridge'
import { CuriosityFactCard } from './CuriosityFactCard'
import { IllustrationVisual } from './IllustrationVisual'
import { hasIllustrationImage } from '@/lib/experiences/illustrationAssets'
import { resolveNarrationAudio } from '@/lib/experiences/audioAssets'
import { OrderingPractice, type PracticeOutcome } from './OrderingPractice'
import { PredictOutputPractice } from './PredictOutputPractice'
import { ExternalResourceCard } from './ExternalResourceCard'
import { LearningAnchor } from './LearningAnchor'
import { readEvidence, recordEvidence, type RemediationEvidence } from '@/lib/experiences/evidence'
import { useLearningPath, useSubmitCycleEvidence } from '@/hooks/useStudent'
import { correctSequence } from '@/lib/experiences/ordering'
import {
  alternateModality, describeAdaptation, describeResourceFraming,
  MODALITY_ORDER, orderingFallbackOf, resolveConceptForRender, resolvePractice,
  resolveReinforcementPriority, selectReinforcement,
} from '@/lib/experiences/experienceOrchestrator'
import { fetchCourseResource, resourceTypeForModality, type CourseResource } from '@/lib/courseResource'
import { useMinDwell } from '@/hooks/useMinDwell'
import type {
  ConceptVariant, ModuleExperienceDefinition, OrderingPracticeDef,
  Reinforcement, ReinforcementKind, RemediationLevel, RemediationStep,
} from '@/types/moduleExperience'
import { MODALITY_THEME, type LearningModality } from '@/types/modality'

// Barandas de la autonomía: bajo este dominio, la remediación decide (no hay menú);
// sobre AUTONOMY_HIGH el menú sugiere continuar.
const AUTONOMY_LOW = 0.4

/** Semilla de `mastery` para el PRIMER ciclo del módulo, a partir del mismo
 *  `initialProfundidad` que ya siembra `profundidad` (Sprint "Coherencia del
 *  estado interno", jul 2026 — corrige una contradicción, no es todavía
 *  adaptación de contenido: ver Fase B). Antes, `mastery` arrancaba en el
 *  mismo `priorMastery` fijo (0.2) para cualquier estudiante, sin importar
 *  el pre-test — un estudiante "aplicacion" que necesitaba una pista en la
 *  práctica principal caía por debajo de AUTONOMY_LOW exactamente igual que
 *  uno "fundamentos", y el menú de decisión nunca sugería "ya dominas esto"
 *  en el primer ciclo. Los valores no pretenden ser exactos — solo dejar de
 *  ser el MISMO número para perfiles opuestos. */
const MASTERY_SEED_APLICACION = 0.7
const MASTERY_SEED_FUNDAMENTOS = 0.15

// Último respaldo, tipo-seguro, para fallbackSolutionOf (Nivel 3 de la
// escalera): en la práctica nunca se renderiza — todo ciclo con escalera
// define practice en su peldaño de Nivel 2 — pero TypeScript exige un valor
// total. Documentado aquí en vez de silenciado con un cast.
const EMPTY_ORDERING_FALLBACK: OrderingPracticeDef = {
  kind: 'ordering',
  prompt: '',
  items: [],
  successFeedback: '',
  orderFeedback: '',
}

// Sprint UX-03 (jul 2026): la fase 'decision' (menú "¿Cómo quieres
// consolidarlo?") se eliminó — la ayuda ya no se ofrece al final del ciclo,
// se inserta automáticamente en 'adapting' cuando la evidencia real del
// Runtime la pide (mismo mecanismo de auto-refuerzo que ya existía). Los
// refuerzos autorados de cycle.decision siguen siendo el banco de contenido
// del que el sistema elige — solo desapareció la pregunta.
type Phase =
  | 'opening'
  | 'reveal'
  | 'curiosity'
  | 'concept'
  | 'practice'
  | 'adapting'
  | 'reinforcement'
  | 'remediation'
  | 'slice_end'

// Narración real (no agentes inventados, sin cifras de confianza fabricadas):
// describe el mismo tramo Adaptar que ya corre en el backend mientras la
// mutación de cycle-evidence está en vuelo. Si la respuesta llega rápido,
// esta fase apenas se ve — si tarda, el tiempo de espera se siente como
// parte del aprendizaje, no como una pantalla de carga vacía.
const ADAPTING_STEPS = [
  'Analizando cómo resolviste el reto',
  'Detectando qué tanto dominas el concepto',
  'Eligiendo la mejor forma de continuar',
] as const

/** Cuánto queda visible la frase de adaptación antes de transicionar — tiempo
 *  de lectura, no una espera técnica (nunca bloquea: el "Continuar" ya quedó
 *  atrás, el estudiante no necesita tocar nada para que esto avance). */
const ADAPTATION_MESSAGE_MS = 1600

/** Saludo al reanudar una sesión previa (auditoría de continuidad, jul 2026):
 *  el sistema no solo restaura la pantalla, dice explícitamente que recuerda
 *  al estudiante — mismo espíritu que describeAdaptation, nunca jerga técnica. */
function describeWelcomeBack(cursor: Pick<ExperienceCursor, 'phase' | 'remediationLevel'>): string {
  if (cursor.phase === 'remediation' || cursor.phase === 'reinforcement') {
    return 'Bienvenido de nuevo. La última vez vimos que este concepto todavía necesitaba un poco más de práctica — continuemos justo desde ahí.'
  }
  return 'Bienvenido de nuevo. Continuemos justo donde lo dejaste.'
}

/** Cuánto queda visible el saludo de bienvenida antes de apagarse solo —
 *  nunca bloquea ni exige un clic; es un tono, no un paso. */
const WELCOME_BACK_MS = 5000

// A1 — persistencia temporal del cursor en localStorage: reanuda tras recarga o
// salida sin perder el avance. Provisional (S1); migrará a Misión Activa backend
// en S3. Persiste el ESTADO DE APRENDIZAJE completo, no solo la pantalla
// (refinamiento de experiencia, jul 2026 — auditoría de continuidad: salir y
// volver, o refrescar, obligaba a rehacer una práctica ya resuelta porque solo
// se guardaba {phase, cycleIndex, mastery}). 'reinforcement' y 'remediation'
// ahora SÍ reanudan directo: `activeReinforcementKind`/`remediationLevel` ya
// alcanzan para reconstruir qué refuerzo o peldaño estaba activo (se busca de
// nuevo en el propio contenido del ciclo, nunca se serializa el objeto).
const RESUMABLE_PHASES: Phase[] = [
  'opening', 'reveal', 'curiosity', 'concept', 'practice', 'reinforcement', 'remediation', 'slice_end',
]

interface ExperienceCursor {
  phase: Phase
  cycleIndex: number
  mastery: Record<string, number>
  practiceOutcome: PracticeOutcome | null
  pythonOutcome: PracticeOutcome | null
  pythonPracticeDone: boolean
  remediationLevel: RemediationLevel
  visitedReinforcements: ReinforcementKind[]
  activeReinforcementKind: ReinforcementKind | null
  autoReinforcement: boolean
  /** Modalidad real recomendada por Adaptar (runtime_decision.diseno.modalidad)
   *  cuando coincide con una de las 4 modalidades conocidas — antes se recibía
   *  y se descartaba en silencio. `null` = sin recomendación aplicada todavía,
   *  se usa la modalidad diagnosticada del estudiante. */
  modalityOverride: LearningModality | null
  /** Ciclos CONSECUTIVOS cerrados con andamiaje="reto" (fluidez real,
   *  confirmada por Tutorizar con tiempo/ayudas — no solo un acierto
   *  aislado). Nunca decidido por el Runtime: es progresión local pura
   *  (RFC-0002 §3 no declara "racha" como señal del dominio) — se resetea
   *  a 0 en cualquier ciclo que NO cierre con "reto". Gobierna cuántos
   *  peldaños de la escalera de PythonBridge se saltan al entrar al
   *  SIGUIENTE ciclo (ver `pythonSkipStages` más abajo) — nunca contenido
   *  nuevo, solo un punto de entrada distinto en la misma progresión ya
   *  autorada. */
  fluencyStreak: number
  /** Cuántas microexplicaciones de cycle.conceptPrimers ya se confirmaron en
   *  ESTE ciclo (sprint "mejora pedagógica", jul 2026) — gobierna si toca
   *  mostrar la siguiente tarjeta o ya se pasó a curiosityFact/concept. 0 en
   *  un ciclo sin conceptPrimers nunca se consulta (comportamiento previo
   *  exacto). Se reinicia junto con el resto del sub-estado del ciclo. */
  primerIndex: number
}

const cursorKey = (moduleId: string) => `experience-cursor:${moduleId}`

/** Fase de ENTRADA a un ciclo (sprint "UX ¿Sabías que...?", jul 2026): un
 *  ciclo con curiosityFact abre con su propia pantalla ("¿Sabías que...?",
 *  con fuente y Continuar); uno sin ella cae directo al contenido principal
 *  — mismo comportamiento previo exacto para esos ciclos. */
function firstPhaseFor(cycle: { curiosityFact?: unknown } | undefined): 'curiosity' | 'concept' {
  return cycle?.curiosityFact ? 'curiosity' : 'concept'
}

function defaultMastery(definition: ModuleExperienceDefinition): Record<string, number> {
  return Object.fromEntries(definition.cycles.map(c => [c.conceptId, c.priorMastery]))
}

function emptyCursor(mastery: Record<string, number>): ExperienceCursor {
  return {
    phase: 'opening', cycleIndex: 0, mastery,
    practiceOutcome: null, pythonOutcome: null, pythonPracticeDone: false,
    remediationLevel: 0, visitedReinforcements: [], activeReinforcementKind: null,
    autoReinforcement: false, modalityOverride: null, fluencyStreak: 0, primerIndex: 0,
  }
}

/** `resumed` distingue "cursor real recuperado de una sesión anterior" de
 *  "arranque en frío" — gobierna si se muestra el saludo de bienvenida de
 *  regreso (nunca en la primera vez, solo cuando de verdad había algo que
 *  recordar). */
function loadCursor(moduleId: string, definition: ModuleExperienceDefinition): ExperienceCursor & { resumed: boolean } {
  const base = defaultMastery(definition)
  try {
    const raw = localStorage.getItem(cursorKey(moduleId))
    if (!raw) return { ...emptyCursor(base), resumed: false }
    const saved = JSON.parse(raw) as Partial<ExperienceCursor> & { phase?: string }
    const cycleIndex = Math.min(Math.max(saved.cycleIndex ?? 0, 0), definition.cycles.length - 1)
    // UX-03: cursores guardados antes del sprint pueden traer 'decision' (el
    // menú eliminado) — se reanudan en 'practice', donde el Continuar ya
    // resuelto dispara la misma adaptación automática. Nada se pierde.
    const savedPhase = saved.phase === 'decision' ? 'practice' : saved.phase
    const phase = savedPhase && RESUMABLE_PHASES.includes(savedPhase as Phase) ? (savedPhase as Phase) : 'concept'
    return {
      phase,
      cycleIndex,
      mastery: { ...base, ...(saved.mastery ?? {}) },
      practiceOutcome: saved.practiceOutcome ?? null,
      pythonOutcome: saved.pythonOutcome ?? null,
      pythonPracticeDone: saved.pythonPracticeDone ?? false,
      remediationLevel: (saved.remediationLevel as RemediationLevel | undefined) ?? 0,
      visitedReinforcements: saved.visitedReinforcements ?? [],
      activeReinforcementKind: saved.activeReinforcementKind ?? null,
      autoReinforcement: saved.autoReinforcement ?? false,
      modalityOverride: saved.modalityOverride ?? null,
      fluencyStreak: saved.fluencyStreak ?? 0,
      primerIndex: saved.primerIndex ?? 0,
      resumed: phase !== 'opening',
    }
  } catch {
    return { ...emptyCursor(base), resumed: false }
  }
}

function saveCursor(moduleId: string, cursor: ExperienceCursor): void {
  try {
    localStorage.setItem(cursorKey(moduleId), JSON.stringify(cursor))
  } catch {
    // La persistencia local nunca bloquea la experiencia.
  }
}

function clearCursor(moduleId: string): void {
  try {
    localStorage.removeItem(cursorKey(moduleId))
  } catch {
    // no-op
  }
}

interface Props {
  definition: ModuleExperienceDefinition
  moduleId: string
  modality?: LearningModality
  /** Requerido para la evaluación continua (registrar_evidencia_evaluacion
   *  necesita course_id) — opcional solo para no romper llamadas previas al
   *  refinamiento de experiencia; sin él, la evidencia sigue siendo local. */
  courseId?: string
  /** Salida sin completar (botón "Salir" a media misión). */
  onExit: () => void
  /** Cierre de la misión — marca el módulo completado (reusa la lógica legacy).
   *  A2 — recibe el dominio agregado (0-1) derivado de la evidencia para que el
   *  mecanismo existente (ResearchMetric vía record_metric) lo registre. */
  onFinish?: (score?: number) => void
  /** Profundidad que Adaptar ya decidió a partir del pre-test para el módulo
   *  de este curso (misma cadena real Diagnosticar→Remediar/Orientar→Adaptar
   *  de RFC-0002 §3 que decide entre ciclos — el pre-test registra evidencia
   *  real desde el día uno, pero quedaba atada a la competencia del pre-test,
   *  sin conectar nunca con el Ciclo 1 del módulo). Solo se siembra en el
   *  PRIMER ciclo (cycleIndex === 0): del segundo en adelante ya existe
   *  evidencia real de este módulo y el mecanismo de siempre (cycle-evidence
   *  entre etapas) manda. `undefined` conserva el comportamiento previo
   *  exacto (arranque siempre en "más apoyo", sin importar el pre-test). */
  initialProfundidad?: string
}

/** A4 — Ganancia de dominio que refleja el aprendizaje REAL, no solo el acierto.
 *  Fórmula única (sin tramos arbitrarios) sobre las señales que ya trae la
 *  práctica: intentos, pistas (= intentos − 1), uso de solución y tiempo.
 *
 *    ver la solución completa      → 0        (no hubo dominio independiente)
 *    ganancia = BASE − COSTO_PISTA · pistas   (cada pista descuenta lo mismo)
 *    tiempo muy alto (esfuerzo)    → −PENAL_TIEMPO
 *    piso 0.05                     (resolver siempre deja algo)
 *
 *  Con estos valores: 1 intento = 0.30 · 2 = 0.20 · 3 = 0.10 (coherente y
 *  fácil de recalibrar cambiando una sola constante). */
const MASTERY_BASE = 0.30
const MASTERY_HINT_COST = 0.10
const MASTERY_TIME_PENALTY = 0.05
const MASTERY_SLOW_MS = 90_000
const MASTERY_FLOOR = 0.05

/** Umbral de "dominado" — mismo valor que evaluatorVerdict ya usaba (avg >=
 *  0.45) para decidir su tono, nombrado aquí para reutilizarlo también en el
 *  checklist "Hoy dominaste" del cierre (sprint "continuidad del progreso",
 *  jul 2026) sin repetir el número mágico en dos lugares. */
const MASTERY_DOMINATED_THRESHOLD = 0.45

/** Resolver con más andamiaje acredita menos dominio. El Nivel 3 (solución
 *  explicada) no acredita nada: el estudiante continúa, pero el perfil registra
 *  que el concepto sigue sin dominarse. */
const LEVEL_GAIN_FACTOR: Record<RemediationLevel, number> = { 0: 1, 1: 0.6, 2: 0.35, 3: 0 }

function masteryGain(outcome: PracticeOutcome, level: RemediationLevel = 0): number {
  if (outcome.solutionShown || level === 3) return 0
  const hintsUsed = Math.max(0, outcome.attempts - 1)
  let gain = MASTERY_BASE - MASTERY_HINT_COST * hintsUsed
  if (outcome.timeMs > MASTERY_SLOW_MS) gain -= MASTERY_TIME_PENALTY
  const base = Math.max(MASTERY_FLOOR, Math.round(gain * 100) / 100)
  return Math.round(base * LEVEL_GAIN_FACTOR[level] * 100) / 100
}

/** Ganancia de un refuerzo voluntario: repasar aporta, pero mucho menos que
 *  resolver. Se aplica solo en el menú de decisión, nunca en la escalera. */
const REINFORCEMENT_GAIN = 0.05

/** Ganancia de la micropráctica de Python ("ahora hazlo tú") — mismo orden de
 *  magnitud que un refuerzo voluntario: complementa la práctica principal,
 *  nunca la sustituye. Cero si se reveló la solución. */
const PYTHON_PRACTICE_GAIN = 0.05

/** Intentos que la actividad concede antes de agotarse (espejo de
 *  MAX_ATTEMPTS_BEFORE_SOLUTION en OrderingPractice). Solo para la evidencia
 *  del Nivel 3, donde ya no hay actividad que los cuente. */
const MAX_SUPPORT_ATTEMPTS = 3


/** Clasificación del desenlace — vale más que una nota para el evaluador. */
function outcomeLabel(outcome: PracticeOutcome): 'domino_solo' | 'con_pistas' | 'solucion_mostrada' {
  if (outcome.solutionShown) return 'solucion_mostrada'
  return outcome.attempts <= 1 ? 'domino_solo' : 'con_pistas'
}

export function ModuleExperienceView({ definition, moduleId, modality, courseId, onExit, onFinish, initialProfundidad }: Props) {
  const submitCycleEvidence = useSubmitCycleEvidence()
  // Sprint "continuidad del progreso" (jul 2026): mismo hook y mismo endpoint
  // que ya usan Dashboard.tsx y LearningPath.tsx para "X/Y misiones
  // completadas" — reutilizado aquí, no reinventado, para que el cierre de un
  // ciclo pueda mostrar el progreso acumulado del CURSO, no solo el de este
  // módulo. React Query ya cachea esta consulta por courseId: si el
  // estudiante vino de /estudiante/path, este fetch normalmente resuelve
  // desde caché sin una llamada de red nueva. `courseId` ausente (demo local
  // sin evaluación continua) deja el hook deshabilitado — el panel de
  // progreso acumulado simplemente no se muestra, nunca bloquea el cierre.
  const learningPath = useLearningPath(courseId)

  // A1 — rehidratar el cursor persistido una sola vez al montar. Ya no es solo
  // la pantalla: todo el sub-estado pedagógico se restaura junto con ella
  // (auditoría de continuidad, jul 2026) para que reanudar nunca obligue a
  // rehacer una práctica ya resuelta.
  const [initialCursor] = useState(() => loadCursor(moduleId, definition))
  const [phase, setPhase] = useState<Phase>(initialCursor.phase)
  const [cycleIndex, setCycleIndex] = useState(initialCursor.cycleIndex)
  const [mastery, setMastery] = useState<Record<string, number>>(initialCursor.mastery)
  const [activeReinforcement, setActiveReinforcement] = useState<Reinforcement | null>(() => {
    if (!initialCursor.activeReinforcementKind) return null
    const savedCycle = definition.cycles[initialCursor.cycleIndex]
    return savedCycle?.decision?.reinforcements.find(r => r.kind === initialCursor.activeReinforcementKind) ?? null
  })
  // Multimodalidad real: recurso REAL del repositorio del curso para la
  // modalidad recomendada, consultado justo antes de entrar a 'reinforcement'
  // — null casi siempre hoy (repositorio vacío para IS301), nunca persistido
  // en el cursor porque es un intento de red, no estado de progreso.
  const [externalResource, setExternalResource] = useState<CourseResource | null>(null)
  // PED-005 — refuerzos ya explorados en el ciclo actual: al terminar uno se
  // vuelve al menú (elegir nunca es un callejón) y el dominio del refuerzo se
  // acredita solo la primera vez por tipo.
  const [visitedReinforcements, setVisitedReinforcements] = useState<Set<ReinforcementKind>>(
    () => new Set(initialCursor.visitedReinforcements),
  )
  // Peldaño activo de la escalera. 0 = actividad principal (sin remediación).
  const [remediationLevel, setRemediationLevel] = useState<RemediationLevel>(initialCursor.remediationLevel)
  // Profundidad VIGENTE de la misión (jul 2026, Sprint "Adaptación desde el
  // primer segundo"): antes solo se leía dentro del closure de advanceCycle
  // para el mensaje de transición y se descartaba — el siguiente ciclo
  // siempre arrancaba en el valor por defecto, sin importar la decisión real
  // del ciclo anterior. Ahora se persiste: nace de `initialProfundidad`
  // (pre-test, primer ciclo) y cada cycle-evidence real la actualiza — la
  // MISMA fuente de verdad que ya gobierna el refuerzo automático y el
  // mensaje de adaptación, ahora también gobierna la teoría del ciclo
  // siguiente (resolveConceptForRender) y la micropráctica de Python
  // (PythonBridge.initialProfundidad). Ningún concepto nuevo, ninguna
  // llamada nueva al Runtime.
  const [profundidad, setProfundidad] = useState<string | undefined>(initialProfundidad)
  // `initialProfundidad` depende de useKnowledgeTestResult/useLearningPath
  // (React Query, asíncronas): en el primer render del padre casi siempre
  // llegan como `undefined` porque la consulta todavía no resuelve, y el
  // inicializador de useState solo se evalúa una vez al montar — sin este
  // efecto, la profundidad sembrada por el pre-test nunca llega a aplicarse
  // cuando la carga es más lenta que el montaje. `cycleEvidenceAppliedRef`
  // evita que esta siembra tardía pise una decisión real ya recibida de
  // cycle-evidence (esa es siempre la fuente de verdad más reciente).
  const cycleEvidenceAppliedRef = useRef(false)
  useEffect(() => {
    if (cycleEvidenceAppliedRef.current) return
    if (initialProfundidad === undefined) return
    setProfundidad(initialProfundidad)
    // Misma siembra tardía, ahora también para `mastery` — antes esta
    // variable nunca se enteraba del pre-test y arrancaba en el mismo
    // priorMastery fijo para cualquier estudiante (ver MASTERY_SEED_* más
    // arriba). Solo toca el conceptId del PRIMER ciclo, y solo si `mastery`
    // sigue en su valor de arranque intacto — si el estudiante ya generó
    // progreso real en este ciclo (Python, refuerzo) antes de que esta
    // siembra tardía llegara, ese progreso real nunca se pisa.
    const firstCycle = definition.cycles[0]
    if (firstCycle) {
      const seeded = initialProfundidad === 'aplicacion' ? MASTERY_SEED_APLICACION
        : initialProfundidad === 'fundamentos' ? MASTERY_SEED_FUNDAMENTOS
          : firstCycle.priorMastery
      setMastery(prev => (
        prev[firstCycle.conceptId] === firstCycle.priorMastery
          ? { ...prev, [firstCycle.conceptId]: seeded }
          : prev
      ))
    }
  }, [initialProfundidad, definition.cycles])
  // Desenlace de la práctica del ciclo actual — habilita Continuar SIEMPRE
  // (nunca-bloquear), incluso cuando se mostró la solución.
  const [practiceOutcome, setPracticeOutcome] = useState<PracticeOutcome | null>(initialCursor.practiceOutcome)
  // La UI obedece al Runtime (no solo lo notifica): cuando `profundidad`
  // devuelta por cycle-evidence es "fundamentos", se inserta automáticamente
  // un refuerzo del propio ciclo (mismo mecanismo que el menú de decisión, sin
  // agente ni fase nueva) antes de continuar. Esta bandera distingue ese
  // origen del refuerzo elegido voluntariamente, para que al terminar continúe
  // el ciclo en vez de volver al menú.
  const [autoReinforcement, setAutoReinforcement] = useState(initialCursor.autoReinforcement)
  // Pilar 2 — Adaptar ya recomienda una modalidad real (runtime_decision.
  // diseno.modalidad) en cada cycle-evidence; antes se recibía y se
  // descartaba. Cuando coincide con una de las 4 modalidades conocidas
  // (MODALITY_ORDER), reemplaza a la diagnosticada para el resto de la
  // misión — null mantiene el comportamiento previo exacto.
  const [modalityOverride, setModalityOverride] = useState<LearningModality | null>(initialCursor.modalityOverride)
  const effectiveModality: LearningModality = modalityOverride ?? modality ?? 'reading'
  // Progresión natural para fluidez sostenida (ver doc de ExperienceCursor.
  // fluencyStreak): cuántos ciclos SEGUIDOS acaban de cerrar con
  // andamiaje="reto". Solo cuenta racha real y reciente — un solo ciclo
  // fluido no basta ("durante varios ciclos"), y cualquier ciclo que NO
  // cierre en "reto" la corta a 0.
  const [fluencyStreak, setFluencyStreak] = useState(initialCursor.fluencyStreak)
  // Microexplicaciones pendientes del ciclo actual (sprint "mejora
  // pedagógica"): cuántas de cycle.conceptPrimers ya se confirmaron. Un
  // ciclo sin conceptPrimers nunca la consulta (comportamiento previo
  // intacto). Se resetea a 0 en commitAdvance, igual que el resto del
  // sub-estado por ciclo.
  // QA Final: los primers ya no son fase con avance propio — el índice se
  // conserva solo por compatibilidad del cursor persistido (siempre 0).
  const [primerIndex] = useState(initialCursor.primerIndex)
  // Progresión gradual, no un salto: 1 ciclo fluido no altera nada (0
  // peldaños saltados); recién a partir de DOS ciclos seguidos se salta el
  // peldaño "observar" (el más trivial: solo mirar el código correr);
  // cuatro o más salta también "manipular". Tope en 2 — nunca aterriza
  // directo en los peldaños de escritura libre, que ya tienen su propio
  // criterio (`shouldStartBlank`, ligado a `profundidad`, no a la racha).
  const pythonSkipStages = fluencyStreak >= 4 ? 2 : fluencyStreak >= 2 ? 1 : 0
  // "Ahora hazlo tú" (PythonBridge.practice): si el puente del ciclo trae una
  // micropráctica interactiva, Continuar espera a que quede resuelta o con
  // solución mostrada — igual que el refuerzo del menú, nunca bloquea después
  // de eso. Sin `practice` en el puente, este estado nunca se consulta.
  const [pythonPracticeDone, setPythonPracticeDone] = useState(initialCursor.pythonPracticeDone)
  // Evidencia de la micropráctica de Python — se combina con practiceOutcome
  // en advanceCycle para que el Runtime vea el ciclo completo (ordenamiento +
  // Python), no solo la mitad. null mientras no se haya resuelto ni agotado.
  const [pythonOutcome, setPythonOutcome] = useState<PracticeOutcome | null>(initialCursor.pythonOutcome)
  // Frase conversacional de la adaptación (describeAdaptation) — visible
  // durante la fase 'adapting' una vez que la decisión real ya llegó, justo
  // antes de transicionar. null mientras se espera la respuesta del Runtime.
  const [adaptationMessage, setAdaptationMessage] = useState<string | null>(null)
  // Timeout de la pausa de lectura tras mostrar adaptationMessage — se limpia
  // al desmontar para no tocar estado de un componente ya fuera de pantalla
  // (p. ej. el estudiante presiona "Salir" durante esa pausa).
  const adaptationTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  useEffect(() => () => {
    if (adaptationTimeoutRef.current) clearTimeout(adaptationTimeoutRef.current)
  }, [])
  // Saludo de bienvenida al reanudar (describeWelcomeBack) — solo cuando el
  // cursor cargado venía de verdad de una sesión anterior (`resumed`), nunca
  // en el arranque en frío. Se apaga solo (WELCOME_BACK_MS) o al primer gesto
  // del estudiante (cualquier cambio de fase), lo que ocurra primero.
  const [welcomeBackMessage, setWelcomeBackMessage] = useState<string | null>(
    () => (initialCursor.resumed ? describeWelcomeBack(initialCursor) : null),
  )
  const welcomeBackPhaseRef = useRef(initialCursor.phase)
  useEffect(() => {
    if (!welcomeBackMessage) return
    if (phase !== welcomeBackPhaseRef.current) {
      setWelcomeBackMessage(null)
      return
    }
    const timeout = setTimeout(() => setWelcomeBackMessage(null), WELCOME_BACK_MS)
    return () => clearTimeout(timeout)
  }, [phase, welcomeBackMessage])

  const cycle = definition.cycles[cycleIndex]
  // Multimodalidad profunda: la mecánica de la práctica principal, no solo
  // el refuerzo, puede variar por modalidad — resuelta una vez por render,
  // reutilizada en los handlers y en el propio render de la fase 'practice'.
  const resolvedPractice = cycle ? resolvePractice(cycle, effectiveModality) : undefined

  // LEARN-002 — recuperar la hipótesis registrada en la apertura para
  // devolverle su veredicto en el cierre. Se lee solo al llegar al cierre.
  const openingAnswer = useMemo(() => {
    if (phase !== 'slice_end') return null
    const ev = readEvidence(moduleId).find(e => e.type === 'opening_answer')
    if (!ev) return null
    const option = typeof ev.detail.option === 'string' ? ev.detail.option : ''
    const freeText = typeof ev.detail.freeText === 'string' ? ev.detail.freeText.trim() : ''
    return option ? { option, freeText } : null
  }, [moduleId, phase])

  const hypothesisVerdict =
    openingAnswer && definition.closing.hypothesis
      ? definition.closing.hypothesis.verdicts[openingAnswer.option] ?? null
      : null

  // Sprint "continuidad del progreso" (jul 2026): UNA sola derivación de
  // mastery/priorMastery para todo el cierre — evaluatorVerdict ya calculaba
  // `avg` (dominio actual promedio) en su propio useMemo; el checklist "Hoy
  // dominaste" y la frase "tu dominio aumentó" necesitan esa MISMA cifra más
  // el punto de partida (priorMastery, ya definido por cada LearningCycle
  // desde S1 — nunca un dato nuevo). Calculada una vez, consumida en los dos
  // lugares — nunca recomputada ni duplicada.
  const moduleMasterySummary = useMemo(() => {
    const avgBefore = definition.cycles.length
      ? definition.cycles.reduce((sum, c) => sum + c.priorMastery, 0) / definition.cycles.length
      : 0
    const avgAfter = definition.cycles.length
      ? definition.cycles.reduce((sum, c) => sum + (mastery[c.conceptId] ?? 0), 0) / definition.cycles.length
      : 0
    const masteredCycles = definition.cycles.filter(c => (mastery[c.conceptId] ?? 0) >= MASTERY_DOMINATED_THRESHOLD)
    return { avgBefore, avgAfter, masteredCycles }
  }, [definition.cycles, mastery])

  // BUG-002 (C-51) — el cierre lo pronuncia el Agente Evaluador con la
  // evidencia real observada (dominio + remediación), no una pantalla anónima.
  // Decide el TONO, nunca el paso: continuar siempre es posible (PED-06).
  const evaluatorVerdict = useMemo(() => {
    if (phase !== 'slice_end') return null
    const avg = moduleMasterySummary.avgAfter
    const maxRemediation = readEvidence(moduleId)
      .filter(e => e.type === 'remediation_level')
      .reduce((max, e) => Math.max(max, Number(e.detail.level) || 0), 0)
    if (avg >= MASTERY_DOMINATED_THRESHOLD && maxRemediation === 0) {
      return 'Observé tus prácticas: construiste este concepto por tu cuenta, sin necesitar apoyo. Este territorio es tuyo — podemos continuar.'
    }
    if (avg >= 0.3) {
      return 'Observé tus prácticas: lo resolviste con algo de apoyo. Es suficiente para avanzar — llevo anotado qué reforzar contigo más adelante.'
    }
    return 'Observé tus prácticas: este concepto todavía se está construyendo, y necesitaste mi ayuda máxima. Puedes continuar — lo dejé registrado para volver sobre él contigo.'
  }, [moduleMasterySummary, moduleId, phase])

  const bumpMastery = useCallback((conceptId: string, delta: number) => {
    setMastery(prev => ({
      ...prev,
      [conceptId]: Math.min(1, Math.max(0, (prev[conceptId] ?? 0) + delta)),
    }))
  }, [])

  // A1 — persistir el cursor en cada cambio de sub-estado pedagógico, no solo
  // de pantalla — es lo que permite reanudar (P1 de la auditoría de
  // continuidad) sin rehacer una práctica ya resuelta.
  useEffect(() => {
    saveCursor(moduleId, {
      phase, cycleIndex, mastery,
      practiceOutcome, pythonOutcome, pythonPracticeDone,
      remediationLevel,
      visitedReinforcements: Array.from(visitedReinforcements),
      activeReinforcementKind: activeReinforcement?.kind ?? null,
      autoReinforcement,
      modalityOverride,
      fluencyStreak,
      primerIndex,
    })
  }, [
    moduleId, phase, cycleIndex, mastery, practiceOutcome, pythonOutcome, pythonPracticeDone,
    remediationLevel, visitedReinforcements, activeReinforcement, autoReinforcement, modalityOverride,
    fluencyStreak, primerIndex,
  ])

  // Cierre de la misión: se borra el cursor (el repaso posterior parte limpio)
  // y se marca el módulo completado vía la lógica legacy. "Salir" a media misión
  // NO borra el cursor, para poder reanudar.
  const handleFinish = useCallback(() => {
    clearCursor(moduleId)
    if (onFinish) {
      // A2 — el dominio agregado (promedio por concepto, 0-1) es la señal de
      // aprendizaje que alimenta al evaluador a través del completado existente.
      const vals = definition.cycles.map(c => mastery[c.conceptId] ?? 0)
      const score = vals.length
        ? Math.round((vals.reduce((a, b) => a + b, 0) / vals.length) * 100) / 100
        : undefined
      onFinish(score)
    } else {
      onExit()
    }
  }, [moduleId, definition, mastery, onFinish, onExit])

  // Limpia TODO el estado del ciclo completado y avanza al siguiente (o al
  // cierre). Separado de `advanceCycle` para que insertar un refuerzo
  // automático (decisión del Runtime) pueda posponer este commit sin
  // duplicar la lógica de transición.
  const commitAdvance = useCallback(() => {
    setActiveReinforcement(null)
    setVisitedReinforcements(new Set())
    setRemediationLevel(0)
    setPracticeOutcome(null)   // ← crítico: reset entre ciclos
    setAutoReinforcement(false)
    setPythonPracticeDone(false)
    setPythonOutcome(null)
    setAdaptationMessage(null)
    setPrimerIndex(0)
    if (cycleIndex + 1 < definition.cycles.length) {
      setCycleIndex(i => i + 1)
      setPhase(firstPhaseFor(definition.cycles[cycleIndex + 1]))
    } else {
      setPhase('slice_end')
    }
  }, [cycleIndex, definition.cycles])

  /** @param pendingGain ganancia que el llamador acaba de aplicar con bumpMastery.
   *  El estado `mastery` de este closure es el ANTERIOR al bump (React agrupa las
   *  actualizaciones), así que sin sumarla aquí el evento `cycle_completed`
   *  reportaría al evaluador un dominio desfasado. */
  const advanceCycle = useCallback((pendingGain = 0) => {
    if (!cycle) return
    const finalMastery = Math.min(1, Math.max(0, (mastery[cycle.conceptId] ?? 0) + pendingGain))
    recordEvidence({
      type: 'cycle_completed',
      moduleId,
      conceptId: cycle.conceptId,
      detail: { cycleId: cycle.id, mastery: Math.round(finalMastery * 100) / 100 },
    })
    if (!courseId) {
      commitAdvance()
      return
    }
    // Evaluación continua (refinamiento de experiencia, jul 2026): el cierre
    // de CADA ciclo entra al Runtime real, no solo al mapa de dominio local
    // — mismo contrato que ya usa la Evaluación de Módulo
    // (registrar_evidencia_evaluacion), traducción fiel de intentos a items
    // (igual que _registrar_diagnostico_en_runtime con el Likert). Haber
    // necesitado la escalera de remediación (remediationLevel > 0) cuenta
    // como la práctica agotada sin ayuda — el crédito reducido que ya
    // reconoce LEVEL_GAIN_FACTOR localmente es la misma señal que el
    // Runtime necesita ver como "no dominada".
    //
    // La UI ahora OBEDECE la decisión, no solo la notifica: la fase
    // 'adapting' espera la respuesta real (nunca bloquea de forma
    // permanente — un error también resuelve el avance). Si `profundidad`
    // es "fundamentos" (mismo vocabulario que ya usan bloom_target_desde_
    // entrega/decision_adaptativa en el backend), se inserta un refuerzo
    // del propio ciclo antes de continuar — reutiliza el mecanismo de
    // refuerzos ya existente (PED-005), nunca uno nuevo.
    //
    // Cierre del bucle observar→adaptar: si el puente del ciclo trae una
    // micropráctica de Python, su evidencia (pythonOutcome) se COMBINA con la
    // de la práctica de ordenamiento antes de enviarla — el Runtime debe ver
    // el ciclo completo, no solo la mitad. Necesitar la solución en cualquiera
    // de las dos cuenta como "no dominada", igual que la escalera de
    // remediación ya hace con la suya.
    const pythonRequired = !!cycle.pythonBridge?.practice
    const orderingSolved = !!practiceOutcome && !practiceOutcome.solutionShown
    const pythonSolved = !pythonRequired || (!!pythonOutcome && !pythonOutcome.solutionShown)
    const solved = remediationLevel === 0 && orderingSolved && pythonSolved
    const orderingAttempts = remediationLevel > 0 ? MAX_SUPPORT_ATTEMPTS : (practiceOutcome?.attempts ?? 1)
    const attempts = orderingAttempts + (pythonOutcome?.attempts ?? 0)
    const timeMs = (practiceOutcome?.timeMs ?? 0) + (pythonOutcome?.timeMs ?? 0)
    setPhase('adapting')
    submitCycleEvidence.mutate(
      { courseId, competencia: cycle.conceptId, attempts, solved, hintsUsed: remediationLevel, timeMs },
      {
        onSuccess: (data: { runtime_decision?: { diseno?: Record<string, unknown> | null } | null }) => {
          const diseno = data?.runtime_decision?.diseno
          const profundidad = diseno?.profundidad ? String(diseno.profundidad) : undefined
          // Persiste para el SIGUIENTE ciclo (teoría + micropráctica de
          // Python) — antes solo vivía en este closure para el mensaje de
          // transición y se perdía al desmontar.
          setProfundidad(profundidad)
          cycleEvidenceAppliedRef.current = true
          // Adaptar también recomienda una modalidad real
          // (runtime/domain/adaptar/productor.py: DISENO_POR_ACCION) — antes
          // se recibía y se descartaba igual que profundidad. Solo se honra
          // cuando coincide con una de las 4 modalidades conocidas (hoy,
          // "visual" en el caso "reforzar"; "mixta" y el resto de
          // alternativas_descartadas no tienen equivalente y se ignoran a
          // propósito, nunca se inventa una traducción).
          const modalidadRecomendada = diseno?.modalidad ? String(diseno.modalidad) : undefined
          // `andamiaje` (RFC-0002 §3, R3 — cuarta dimensión declarada desde
          // el inicio, sin implementar hasta este sprint): Adaptar ya
          // gobierna QUÉ intervención concreta corresponde a la señal de
          // sesión, no solo su explicabilidad — el frontend renderiza la
          // decisión, no la vuelve a tomar. `alternar-modalidad` reutiliza
          // EXACTAMENTE el mismo mecanismo que ya usa la escalera de
          // remediación local (`alternateModality`/`conceptModality:
          // 'alternate'`, más abajo en este archivo), ahora informado por
          // la señal real del Runtime en vez de solo el conteo de intentos.
          const andamiaje = diseno?.andamiaje ? String(diseno.andamiaje) : undefined
          // Racha de fluidez (ver ExperienceCursor.fluencyStreak): SOLO
          // cuenta cuando ESTE ciclo cerró con "reto" — cualquier otro
          // desenlace (confusión, frustración, o ningún andamiaje) la
          // corta a 0. Progresión local pura, nunca decidida por el
          // Runtime — gobierna cuántos peldaños de PythonBridge se saltan
          // en el PRÓXIMO ciclo (más abajo, junto al render).
          setFluencyStreak(prev => andamiaje === 'reto' ? prev + 1 : 0)
          const modalidadHonrada =
            andamiaje === 'alternar-modalidad'
              ? alternateModality(effectiveModality)
              : modalidadRecomendada && MODALITY_ORDER.includes(modalidadRecomendada as LearningModality)
                ? (modalidadRecomendada as LearningModality)
                : undefined
          if (modalidadHonrada) setModalityOverride(modalidadHonrada)
          // Adaptación multimodal real (no solo cantidad de ayuda): el
          // refuerzo automático se elige según DOS señales reales — qué
          // necesita el estudiante (profundidad: reforzar/desafiar) y cómo
          // aprende mejor (modalidad: la recién recomendada por Adaptar, o
          // si no hubo ninguna esta vez, la ya diagnosticada). "aplicacion"
          // es la propuesta REAL de Orientar cuando Diagnosticar marcó el
          // concepto como dominado (runtime/domain/orientar/productor.py) —
          // antes se descartaba en silencio; "fundamentos" es Remediar.
          // Mismo mecanismo de auto-refuerzo ya existente, ningún concepto
          // nuevo en el Runtime ni recurso inventado en el frontend.
          const modalidadParaRefuerzo = modalidadHonrada ?? effectiveModality
          const basePriority = resolveReinforcementPriority(cycle, modalidadParaRefuerzo)
          // "ejemplo" (señal de confusión): el objetivo es cambiar la
          // REPRESENTACIÓN del concepto, no solo repetirlo con otras
          // palabras — pero el propio kind "ejemplo" (ver los 4 ciclos
          // autorados) nunca trae `sceneId` ni `narrationText`, solo
          // `body` (texto plano); es el ÚNICO kind que garantiza la misma
          // representación de siempre, sin importar la modalidad. Antes
          // esta línea lo forzaba justo a él al frente de la prioridad —
          // el peor caso posible para confusión. Ahora se le resta
          // prioridad (va al final): "animacion" (AnimatedScene,
          // sceneId ya autorado) y "audio" (AudioNarration, narrationText
          // ya autorado) — ambos con representación real distinta al
          // texto — pasan primero, reutilizando exactamente lo que cada
          // ciclo ya trae.
          const reinforcementPriority = andamiaje === 'ejemplo'
            ? ([...basePriority.filter(k => k !== 'ejemplo'), 'ejemplo'] as typeof basePriority)
            : basePriority
          const preferChallenge = profundidad === 'aplicacion'
          // "reto" (señal de fluidez, ya confirmada por Tutorizar con
          // tiempo/ayudas reales): los 4 ciclos autorados YA traen un
          // Reinforcement kind="reto" con su propia práctica real
          // (ordering/predict_output) — una oportunidad de aprendizaje
          // genuina, no una repetición. El sprint anterior lo descartaba
          // siempre (reinforcement = undefined) para evitar el bug real
          // de caer a un refuerzo fácil cuando el ciclo no traía "reto" —
          // pero de paso también descartaba el "reto" cuando SÍ existía.
          // Ahora: si el ciclo trae un "reto" real, se muestra (avanza
          // rápido → desafío mayor, en vez de solo avanzar); si no lo
          // trae, sigue sin ofrecer nada — nunca cae a un tipo distinto.
          const retoDisponible = andamiaje === 'reto'
            ? selectReinforcement(cycle.decision?.reinforcements, visitedReinforcements, modalidadParaRefuerzo, true, ['reto'])
            : undefined
          const reinforcement = andamiaje === 'reto'
            ? retoDisponible?.kind === 'reto' ? retoDisponible : undefined
            : profundidad === 'fundamentos' || profundidad === 'aplicacion'
              ? selectReinforcement(cycle.decision?.reinforcements, visitedReinforcements, modalidadParaRefuerzo, preferChallenge, reinforcementPriority)
              : undefined
          // Capa conversacional (nunca jerga técnica: sin Runtime, agentes ni
          // modalidad) — se muestra dentro de la propia fase 'adapting', una
          // pausa de lectura breve antes de transicionar, nunca un toast aparte.
          // Sprint "coherencia adaptativa" (jul 2026): `andamiaje` ya se
          // computó arriba para decidir `reinforcement` mismo — antes se
          // descartaba al llegar aquí, así que describeAdaptation nunca
          // sabía POR QUÉ había un reinforcement que mostrar y asumía
          // "dificultad" por defecto. Pasarlo es lo que le permite decir
          // "ya dominas esto" cuando `andamiaje === 'reto'`, en vez de
          // contradecir el "sugerido — ya dominas esto" que el estudiante
          // acaba de ver en el menú de decisión.
          setAdaptationMessage(describeAdaptation(
            profundidad, reinforcement, cycle.conceptLabel,
            definition.cycles[cycleIndex + 1]?.conceptLabel,
            andamiaje,
          ))
          // Multimodalidad real: antes de mostrar el refuerzo ya autorado,
          // se consulta si el repositorio del curso tiene un recurso real
          // para la modalidad recomendada — best-effort, nunca bloquea la
          // transición (setExternalResource llega después si acaso).
          setExternalResource(null)
          const resourceType = resourceTypeForModality(modalidadParaRefuerzo)
          if (reinforcement && resourceType) {
            fetchCourseResource(courseId, resourceType).then(setExternalResource)
          }
          adaptationTimeoutRef.current = setTimeout(() => {
            if (reinforcement) {
              setAutoReinforcement(true)
              setActiveReinforcement(reinforcement)
              setPhase('reinforcement')
            } else {
              commitAdvance()
            }
          }, ADAPTATION_MESSAGE_MS)
        },
        onError: () => commitAdvance(),
      },
    )
  }, [commitAdvance, courseId, cycle, cycleIndex, definition, mastery, moduleId, practiceOutcome, pythonOutcome, remediationLevel, submitCycleEvidence, visitedReinforcements])


  // ── Handlers por fase ────────────────────────────────────────────────────────

  const handleOpeningAnswer = useCallback((option: string, freeText: string) => {
    recordEvidence({ type: 'opening_answer', moduleId, detail: { option, freeText } })
    setPhase('reveal')
  }, [moduleId])

  const handleConceptDone = useCallback((dwellMs: number) => {
    if (!cycle) return
    recordEvidence({
      type: 'concept_viewed',
      moduleId,
      conceptId: cycle.conceptId,
      detail: { modality: effectiveModality, medium: cycle.concept.variants[effectiveModality]?.medium, dwellMs },
    })
    setPhase('practice')
  }, [cycle, effectiveModality, moduleId])

  const handlePracticeAttempt = useCallback(({ attempt, status }: { attempt: number; status: string }) => {
    if (!cycle || !resolvedPractice) return
    recordEvidence({
      type: 'practice_attempt',
      moduleId,
      conceptId: cycle.conceptId,
      detail: { practice: resolvedPractice.kind, attempt, status, correct: status === 'correct' },
    })
  }, [cycle, moduleId, resolvedPractice])

  const handlePredictOutputAttempt = useCallback(({ attempt, correct }: { attempt: number; correct: boolean }) => {
    if (!cycle || !resolvedPractice) return
    recordEvidence({
      type: 'practice_attempt',
      moduleId,
      conceptId: cycle.conceptId,
      detail: { practice: resolvedPractice.kind, attempt, correct },
    })
  }, [cycle, moduleId, resolvedPractice])

  /** Evidencia para el agente evaluador — contrato RemediationEvidence.
   *  Se emite en CADA peldaño, se resuelva o se agote. */
  const recordRemediation = useCallback((
    level: RemediationLevel, outcome: PracticeOutcome, solved: boolean, modalityUsed: LearningModality,
    /** Ganancia que el llamador aplicará DESPUÉS de registrar. Cero cuando no
     *  hubo ganancia (peldaño agotado) o cuando el bump ya se aplicó antes —
     *  sumarla aquí en esos casos inflaba el dominio reportado al evaluador. */
    pendingGain = 0,
  ) => {
    if (!cycle) return
    const estimate = Math.min(1, Math.max(0, (mastery[cycle.conceptId] ?? 0) + pendingGain))
    const detail: RemediationEvidence = {
      level,
      attempts: outcome.attempts,
      timeMs: outcome.timeMs,
      hintsUsed: Math.max(0, outcome.attempts - 1),
      modality: modalityUsed,
      solutionShown: outcome.solutionShown,
      masteryEstimate: Math.round(estimate * 100) / 100,
      solved,
    }
    recordEvidence({ type: 'remediation_level', moduleId, conceptId: cycle.conceptId, detail: { ...detail } })
  }, [cycle, mastery, moduleId])

  /** Entrada a la escalera. Si el ciclo no la define, nunca se bloquea: avanza. */
  const enterRemediation = useCallback((level: RemediationLevel) => {
    if (!cycle) return
    const step = cycle.remediation?.steps.find(s => s.level === level)
    if (!step) {
      advanceCycle()
      return
    }
    setRemediationLevel(level)
    setPhase('remediation')
  }, [advanceCycle, cycle])

  const handlePracticeFinished = useCallback((outcome: PracticeOutcome) => {
    if (!cycle || !resolvedPractice) return
    recordEvidence({
      type: 'practice_attempt',
      moduleId,
      conceptId: cycle.conceptId,
      detail: {
        practice: resolvedPractice.kind,
        attempts: outcome.attempts,
        timeMs: outcome.timeMs,
        solutionShown: outcome.solutionShown,
        outcome: outcomeLabel(outcome),
        final: true,
      },
    })
    bumpMastery(cycle.conceptId, masteryGain(outcome, 0))
    setPracticeOutcome(outcome)
  }, [bumpMastery, cycle, moduleId, resolvedPractice])

  /** Nivel 0 agotado: no se revela la solución — escala al Nivel 1. */
  const handlePracticeExhausted = useCallback((outcome: PracticeOutcome) => {
    if (!cycle) return
    recordRemediation(0, outcome, false, effectiveModality)
    enterRemediation(1)
  }, [cycle, effectiveModality, enterRemediation, recordRemediation])

  const handlePracticeContinue = useCallback(() => {
    if (!cycle) return
    // UX-03: sin menú de consolidación al final. Ya pasó por la escalera en
    // este ciclo (no se remedia dos veces) o cerró con dominio suficiente —
    // en ambos casos el cierre va directo a la adaptación automática
    // (advanceCycle → 'adapting'): el Runtime inserta el refuerzo solo
    // cuando la evidencia lo pide, nunca pregunta.
    if (remediationLevel > 0) {
      advanceCycle()
      return
    }
    const current = mastery[cycle.conceptId] ?? 0
    const needsSupport = current < AUTONOMY_LOW
    // Resolvió, pero el dominio no alcanza la baranda: se refuerza antes de
    // continuar. La escalera siempre termina, así que esto no bloquea.
    if (needsSupport) {
      recordRemediation(0, practiceOutcome ?? { attempts: 1, timeMs: 0, solutionShown: false }, true, effectiveModality)
      enterRemediation(1)
    } else {
      advanceCycle()
    }
  }, [advanceCycle, cycle, effectiveModality, enterRemediation, mastery, practiceOutcome, recordRemediation, remediationLevel])

  /** Refuerzo insertado por el sistema (UX-03: ya no existe el voluntario del
   *  menú). Al terminar, el ciclo continúa — la ayuda apareció, cumplió y el
   *  flujo sigue sin preguntar nada. Cursores previos al sprint podían dejar
   *  un refuerzo voluntario activo (autoReinforcement=false): también
   *  continúan, nunca vuelven a un menú que ya no existe. */
  const handleReinforcementDone = useCallback(() => {
    if (!cycle || !activeReinforcement) return
    const kind = activeReinforcement.kind
    const firstView = !visitedReinforcements.has(kind)
    recordEvidence({
      type: 'reinforcement_viewed',
      moduleId,
      conceptId: cycle.conceptId,
      detail: { kind, remediation: false, revisit: !firstView },
    })
    // El dominio se acredita solo la primera vez: repetir el mismo refuerzo
    // no acumula puntos.
    if (firstView) bumpMastery(cycle.conceptId, REINFORCEMENT_GAIN)
    setVisitedReinforcements(prev => new Set(prev).add(kind))
    setActiveReinforcement(null)
    commitAdvance()
  }, [activeReinforcement, bumpMastery, commitAdvance, cycle, moduleId, visitedReinforcements])

  // ── Escalera de remediación ──────────────────────────────────────────────────

  const step: RemediationStep | undefined =
    remediationLevel > 0 ? cycle?.remediation?.steps.find(s => s.level === remediationLevel) : undefined

  const stepModality: LearningModality =
    step?.conceptModality === 'alternate' ? alternateModality(effectiveModality) : effectiveModality

  // Auditoría (2026-07-17): el panel "Concepto re-explicado" del Nivel 1
  // (conceptModality: 'same') pasaba `cycle.concept.variants[stepModality]`
  // — con stepModality === effectiveModality en ese nivel, mostraba
  // EXACTAMENTE la misma variante (mismo `body`, palabra por palabra) que
  // el estudiante ya leyó en la fase 'concept' antes de fallar la práctica.
  // No era "otra forma de explicarlo": era la misma explicación repetida.
  // `reviewModality` rota SIEMPRE a una modalidad distinta de la ya vista,
  // reutilizando exactamente `alternateModality()` (mismo mecanismo de
  // v1.4) — una vez por nivel, para que el Nivel 2 (si el estudiante vuelve
  // a confundirse) tampoco repita lo que el Nivel 1 ya mostró.
  let reviewModality: LearningModality = effectiveModality
  for (let i = 0; i < remediationLevel; i++) reviewModality = alternateModality(reviewModality)

  /** Resolvió en este peldaño: acredita dominio reducido y vuelve al cierre
   *  normal del ciclo (puente a Python si lo trae, luego menú de consolidación)
   *  — antes saltaba directo a advanceCycle() y ambos quedaban inalcanzables
   *  para cualquier estudiante que hubiera necesitado la escalera. */
  const handleStepSolved = useCallback((outcome: PracticeOutcome) => {
    if (!cycle || remediationLevel === 0) return
    const gain = masteryGain(outcome, remediationLevel)
    recordRemediation(remediationLevel, outcome, true, stepModality, gain)
    bumpMastery(cycle.conceptId, gain)
    setPracticeOutcome(outcome)
    setPhase('practice')
  }, [bumpMastery, cycle, recordRemediation, remediationLevel, stepModality])

  /** Agotó este peldaño: escala al siguiente. El Nivel 3 no tiene práctica, así
   *  que la escalera termina siempre — el bloqueo es imposible por construcción. */
  const handleStepExhausted = useCallback((outcome: PracticeOutcome) => {
    if (!cycle || remediationLevel === 0) return
    recordRemediation(remediationLevel, outcome, false, stepModality)
    enterRemediation((remediationLevel + 1) as RemediationLevel)
  }, [cycle, enterRemediation, recordRemediation, remediationLevel, stepModality])

  /** Nivel 3 — ayuda máxima registrada. Vuelve al cierre normal del ciclo, igual
   *  que handleStepSolved: el puente a Python y el menú de consolidación siguen
   *  siendo parte del ciclo aunque la ayuda haya sido máxima. */
  const handleMaxSupportContinue = useCallback(() => {
    if (!cycle) return
    const outcome: PracticeOutcome = { attempts: MAX_SUPPORT_ATTEMPTS, timeMs: 0, solutionShown: true }
    recordRemediation(3, outcome, false, stepModality)
    setPracticeOutcome(outcome)
    setPhase('practice')
  }, [cycle, recordRemediation, stepModality])

  // ── Render ───────────────────────────────────────────────────────────────────

  if (phase === 'opening') {
    return <CuriosityOpening opening={definition.opening} onAnswer={handleOpeningAnswer} />
  }

  if (phase === 'reveal') {
    return (
      <div className="flex flex-col items-center justify-center min-h-[70vh] px-4 animate-in fade-in duration-700">
        <div className="glass-panel rounded-2xl p-8 md:p-10 max-w-xl w-full text-center space-y-6">
          <p className="text-sm md:text-base text-neural-text/90 leading-relaxed">
            {definition.opening.revealHook}
          </p>
          <div className="space-y-2">
            {definition.routeTitle && (
              <p className="text-[10px] font-mono tracking-[0.2em] uppercase text-neural-glow/70">
                Tu misión en «{definition.routeTitle}»
              </p>
            )}
            <h1 className="text-2xl font-bold text-neural-text">{definition.missionTitle}</h1>
            <span className="inline-flex items-center gap-1.5 text-[11px] font-mono tracking-[0.15em] uppercase px-3 py-1 rounded-full border border-neural-violet/30 text-neural-violet bg-neural-violet/5">
              <Compass className="h-3 w-3" />
              Territorio: {definition.territory}
            </span>
          </div>
          <Button className="w-full gap-2" onClick={() => setPhase(firstPhaseFor(cycle))}>
            Comenzar →
          </Button>
        </div>
      </div>
    )
  }

  if (phase === 'adapting') {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] px-4 animate-in fade-in duration-300">
        <div className="glass-panel rounded-2xl p-8 max-w-md w-full text-center space-y-5">
          <span className="relative flex h-2.5 w-2.5 mx-auto">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-neural-pulse opacity-60" />
            <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-neural-pulse" />
          </span>
          {adaptationMessage ? (
            // La decisión ya llegó — la narración reemplaza el checklist
            // (nunca coexisten: decirle "sigo eligiendo" mientras ya se sabe
            // qué sigue sería contradictorio). Última parada antes de que la
            // transición programada (ADAPTATION_MESSAGE_MS) cambie de fase.
            <p className="text-base text-neural-text leading-relaxed animate-in fade-in duration-500">
              {adaptationMessage}
            </p>
          ) : (
            <>
              <p className="text-[11px] font-mono tracking-[0.2em] uppercase text-neural-pulse">
                Personalizando tu siguiente paso
              </p>
              <ul className="space-y-2.5 text-left">
                {ADAPTING_STEPS.map((step, i) => (
                  <li
                    key={step}
                    className="text-sm text-neural-text/80 flex items-center gap-2.5 animate-in fade-in slide-in-from-left-1"
                    style={{ animationDelay: `${i * 450}ms`, animationDuration: '400ms', animationFillMode: 'both' }}
                  >
                    <span className="text-neural-glow shrink-0">✓</span>
                    {step}
                  </li>
                ))}
              </ul>
            </>
          )}
        </div>
      </div>
    )
  }

  if (phase === 'slice_end') {
    // Sprint "continuidad del progreso" (jul 2026): el cierre dejaba de
    // sentirse como una sesión aislada ("100% → Fin") recién con estos tres
    // datos, y los tres ya existían en el sistema — ninguno se inventa aquí:
    //
    //   1. moduleMasterySummary (arriba, useMemo) — mismo dominio real que ya
    //      alimentaba a evaluatorVerdict.
    //   2. learningPath (mismo hook que Dashboard.tsx/LearningPath.tsx ya usan
    //      para "X/Y misiones completadas") — progreso ACUMULADO del curso,
    //      no solo de este módulo. `completedAfter` proyecta el cierre que
    //      handleFinish está a punto de confirmar en el backend (doComplete,
    //      en ModuleLearningView.tsx, marca esta misión 'completed' y navega
    //      de inmediato) — nunca inventa una misión que no exista en items.
    //   3. definition.closing.nextMission (ya existía, ModuleExperienceDefinition)
    //      — de dónde sale la frase de continuidad.
    const pathItems = learningPath.data?.items ?? []
    const totalMissions = pathItems.length
    const completedBefore = pathItems.filter(i => i.status === 'completed').length
    const thisAlreadyCounted = pathItems.find(i => i.id === moduleId)?.status === 'completed'
    const completedAfter = totalMissions > 0
      ? Math.min(totalMissions, completedBefore + (thisAlreadyCounted ? 0 : 1))
      : 0
    const coursePct = totalMissions > 0 ? Math.round((completedAfter / totalMissions) * 100) : null
    const courseComplete = totalMissions > 0 && completedAfter === totalMissions

    const continuityMessage = definition.closing.nextMission
      ? `La próxima vez continuarás directo en «${definition.closing.nextMission.title}».`
      : courseComplete
        ? `Completaste toda tu ruta de ${learningPath.data?.course_name ?? 'aprendizaje'} — tu progreso quedó guardado.`
        : 'Tu progreso quedó guardado — la próxima vez continuarás justo desde aquí.'

    // UX-05 "Workspace pedagógico adaptativo": el cierre dejó de ser una
    // columna de ocho bloques apilados — se reparte en dos columnas por lo
    // que CADA una cuenta: izquierda = la narrativa de esta sesión (qué
    // dominaste, tu hipótesis, el logro); derecha = dónde estás ahora
    // (mapa de dominio, veredicto del evaluador, progreso del curso). La
    // continuidad y el botón siguen a todo el ancho, al final — son el
    // cierre de AMBAS columnas, no de una sola. Ningún dato ni condición
    // cambia, solo su posición.
    const hasRightColumn = evaluatorVerdict || (totalMissions > 0 && coursePct !== null)
    return (
      <div className="max-w-4xl mx-auto py-8 space-y-6 animate-in fade-in duration-500">
        <div className="glass-panel rounded-2xl p-8 space-y-8">
          <div className={cn('grid gap-8 items-start', hasRightColumn && 'lg:grid-cols-2')}>

            {/* ── Columna izquierda: qué pasó en esta sesión ────────────── */}
            <div className="space-y-6">
              {/* "Hoy dominaste" — el mismo dominio de siempre, presentado como
                  un logro de ESTA sesión (checklist), no solo como una barra
                  estática que reemplaza a la anterior sin decir qué cambió. */}
              {moduleMasterySummary.masteredCycles.length > 0 && (
                <div className="space-y-2">
                  <div className="flex items-center gap-2.5">
                    <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0" />
                    <p className="text-[11px] font-mono tracking-[0.2em] uppercase text-emerald-400">
                      Hoy dominaste
                    </p>
                  </div>
                  <ul className="space-y-1.5 pl-0.5">
                    {moduleMasterySummary.masteredCycles.map(c => (
                      <li key={c.conceptId} className="flex items-center gap-2 text-sm text-neural-text/90">
                        <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400 shrink-0" />
                        {c.conceptLabel}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* LEARN-002 — cierre del experimento: la hipótesis de la apertura
                  recibe su veredicto ANTES del botón de salida. */}
              {openingAnswer && hypothesisVerdict && (
                <div className="rounded-xl border border-neural-violet/25 bg-neural-violet/5 p-5 space-y-3">
                  <div className="flex items-center gap-2.5">
                    <FlaskConical className="h-4 w-4 text-neural-violet shrink-0" />
                    <p className="text-[11px] font-mono tracking-[0.2em] uppercase text-neural-violet">
                      Tu hipótesis inicial
                    </p>
                  </div>
                  <p className="text-sm text-neural-muted leading-relaxed">
                    Al empezar respondiste:{' '}
                    <span className="text-neural-text/90">«{openingAnswer.option}»</span>
                    {openingAnswer.freeText && (
                      <>
                        {' '}— y predijiste:{' '}
                        <span className="text-neural-text/90 italic">«{openingAnswer.freeText}»</span>
                      </>
                    )}
                  </p>
                  <p className="text-sm leading-relaxed">
                    <span className="font-semibold text-neural-glow">{hypothesisVerdict.label}.</span>{' '}
                    <span className="text-neural-text/90">{hypothesisVerdict.text}</span>
                  </p>
                  {definition.closing.hypothesis?.coda && (
                    <p className="text-xs text-neural-muted leading-relaxed border-t border-white/[0.06] pt-3">
                      {definition.closing.hypothesis.coda}
                    </p>
                  )}
                </div>
              )}

              <p className="text-sm text-neural-muted leading-relaxed">
                {definition.closing.achievement}
              </p>

              {definition.closing.nextMission && (
                <div className="rounded-xl border border-white/[0.08] bg-white/[0.02] px-4 py-3 space-y-1.5">
                  <p className="text-xs text-neural-muted">
                    <span className="font-mono text-neural-violet">PRÓXIMA MISIÓN ·</span>{' '}
                    <span className="text-neural-text/90">{definition.closing.nextMission.title}</span>
                  </p>
                  <p className="text-xs text-neural-muted leading-relaxed">
                    {definition.closing.nextMission.hook}
                  </p>
                </div>
              )}
            </div>

            {/* ── Columna derecha: dónde estás ahora ────────────────────── */}
            <div className="space-y-6 lg:border-l lg:border-white/[0.06] lg:pl-8">
              {/* "Tu dominio aumentó" — mismo promedio que evaluatorVerdict ya
                  calculaba, ahora también expresado como el DELTA real desde
                  priorMastery (el punto de partida de cada ciclo), no solo el
                  número final. */}
              {moduleMasterySummary.avgAfter > moduleMasterySummary.avgBefore && (
                <div className="flex items-center gap-2.5 rounded-xl border border-neural-glow/20 bg-neural-glow/5 px-4 py-3">
                  <TrendingUp className="h-4 w-4 text-neural-glow shrink-0" />
                  <p className="text-sm text-neural-text/90 leading-relaxed">
                    Tu dominio en este territorio subió de{' '}
                    <span className="font-mono text-neural-glow">{Math.round(moduleMasterySummary.avgBefore * 100)}%</span>
                    {' '}a{' '}
                    <span className="font-mono text-neural-glow">{Math.round(moduleMasterySummary.avgAfter * 100)}%</span>.
                  </p>
                </div>
              )}

              <div className="space-y-4">
                <div className="flex items-center gap-2.5">
                  <Map className="h-4 w-4 text-neural-glow shrink-0" />
                  <p className="text-[11px] font-mono tracking-[0.2em] uppercase text-neural-glow">
                    Tu mapa de dominio
                  </p>
                </div>
                {definition.cycles.map(c => {
                  const value = Math.round((mastery[c.conceptId] ?? 0) * 100)
                  return (
                    <div key={c.conceptId} className="space-y-1.5">
                      <div className="flex items-baseline justify-between">
                        <p className="text-sm font-medium text-neural-text">{c.conceptLabel}</p>
                        <span className="text-xs font-mono text-neural-glow">{value}%</span>
                      </div>
                      <div className="w-full bg-white/[0.06] rounded-full h-1.5 overflow-hidden">
                        <div
                          className="bg-neural-glow h-1.5 rounded-full neural-glow-sm transition-all duration-700"
                          style={{ width: `${value}%` }}
                        />
                      </div>
                    </div>
                  )
                })}
              </div>

              {/* BUG-002 — el Agente Evaluador se pronuncia sobre lo observado. */}
              {evaluatorVerdict && (
                <div className="rounded-xl border border-neural-pulse/25 bg-neural-pulse/5 px-4 py-3.5 flex gap-3">
                  <span className="relative flex h-2 w-2 shrink-0 mt-1.5">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-neural-pulse opacity-60" />
                    <span className="relative inline-flex rounded-full h-2 w-2 bg-neural-pulse" />
                  </span>
                  <div className="min-w-0">
                    <p className="text-[10px] font-mono tracking-[0.2em] uppercase text-neural-pulse mb-1">
                      Agente Evaluador
                    </p>
                    <p className="text-sm text-neural-text/90 leading-relaxed">{evaluatorVerdict}</p>
                  </div>
                </div>
              )}

              {/* "Mostrar progreso acumulado" — mismo dato que ya muestra el
                  Dashboard ("X/Y misiones completadas"), consumido aquí vía el
                  mismo hook (useLearningPath), no reinventado. Ausente sin
                  courseId (demo local) o mientras el fetch está en vuelo — nunca
                  bloquea el cierre. */}
              {totalMissions > 0 && coursePct !== null && (
                <div className="rounded-xl border border-white/[0.08] bg-white/[0.02] p-4 space-y-2.5">
                  <div className="flex items-center gap-2.5">
                    <Route className="h-4 w-4 text-neural-violet shrink-0" />
                    <p className="text-[11px] font-mono tracking-[0.2em] uppercase text-neural-violet">
                      Tu progreso en {learningPath.data?.course_name ?? 'tu ruta de aprendizaje'}
                    </p>
                  </div>
                  <div className="flex items-baseline justify-between">
                    <p className="text-sm text-neural-text/90">{completedAfter}/{totalMissions} misiones</p>
                    <span className="text-sm font-mono text-neural-violet">{coursePct}%</span>
                  </div>
                  <div className="w-full bg-white/[0.06] rounded-full h-1.5 overflow-hidden">
                    <div
                      className="bg-neural-violet h-1.5 rounded-full transition-all duration-700"
                      style={{ width: `${coursePct}%` }}
                    />
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* "La próxima vez continuarás desde aquí" — nombra un mecanismo que
              YA existe (cursor persistido, Misión Activa) en vez de dejar que
              el botón de abajo se sienta como el final de todo. Cierre de
              AMBAS columnas: a todo el ancho, con su propio separador. */}
          <div className="space-y-4 border-t border-white/[0.06] pt-6">
            <p className="text-xs text-neural-muted text-center leading-relaxed">
              {continuityMessage}
            </p>
            <Button className="w-full" onClick={handleFinish}>
              {/* "misión", nunca "módulo" — el resto de la experiencia ya evita esa
                  palabra (missionTitle, routeTitle); este era el único lugar que
                  todavía la usaba, rompiendo la sensación de aprendizaje continuo. */}
              {definition.closing.nextMission ? 'Seguir con la siguiente misión →' : 'Finalizar misión →'}
            </Button>
          </div>
        </div>
      </div>
    )
  }

  // Sprint UX-02 "Laboratorio adaptativo": cuando el ciclo llega al editor
  // de Python (práctica resuelta → puente activo), la pantalla deja de ser
  // una columna estrecha y se convierte en un laboratorio de tres zonas:
  // contexto a la izquierda, editor grande con consola al centro, tutor
  // contextual a la derecha. Solo presentación — la lógica del ciclo, la
  // evidencia y las decisiones del Runtime no cambian.
  const labActive = phase === 'practice' && !!practiceOutcome && !!cycle?.pythonBridge
  // QA Final: el contexto (objetivo + infografía) acompaña TODA la fase de
  // práctica, no solo el laboratorio post-resolución — antes, la actividad
  // sin resolver era una columna estrecha en una página vacía, y el
  // estudiante practicaba sin la teoría a la vista (teoría y práctica deben
  // convivir, no turnarse).
  const practiceContextActive = phase === 'practice' && remediationLevel === 0 && !practiceOutcome && !!cycle
  const labConcept = (labActive || practiceContextActive) && cycle ? resolveConceptForRender(cycle, effectiveModality, profundidad) : null
  const labVariant = labConcept ? (labConcept.variants[effectiveModality] ?? labConcept.variants.reading) : null
  const conceptAside = labConcept && labVariant ? (
    <>
      <div className="glass-panel rounded-2xl p-5 space-y-2">
        <p className="text-[11px] font-mono tracking-[0.15em] uppercase text-neural-violet">Objetivo</p>
        <p className="text-sm font-semibold text-neural-text">{labConcept.title}</p>
        <p className="text-sm text-neural-muted leading-relaxed">
          {labConcept.quickRecap?.body?.[0] ?? labVariant.body[0]}
        </p>
      </div>
      {hasIllustrationImage(labVariant) && (
        <div className="glass-panel rounded-2xl p-4">
          <IllustrationVisual imageUrl={labVariant.imageUrl} imageAsset={labVariant.imageAsset} alt={labConcept.title} />
        </div>
      )}
    </>
  ) : undefined
  const labAside = conceptAside ? (
    <>
      {conceptAside}
      <p className="text-xs text-neural-muted/60 italic px-1">
        El tutor contextual aparece junto al editor solo cuando tiene una
        pista, un ejemplo o una explicación que darte — nunca antes.
      </p>
    </>
  ) : undefined

  // UX-05 "Workspace pedagógico adaptativo" — la práctica principal, una vez
  // resuelta, se define UNA sola vez aquí para envolverla (o no) en
  // LearningAnchor sin duplicar sus props en dos ramas del render.
  const practiceBody = resolvedPractice && cycle && (
    resolvedPractice.kind === 'ordering' ? (
      <OrderingPractice
        key={`${cycle.id}-practice`}
        practice={resolvedPractice}
        onAttempt={handlePracticeAttempt}
        onFinished={handlePracticeFinished}
        revealOnExhaust={!cycle.remediation}
        onExhausted={handlePracticeExhausted}
        profundidad={profundidad}
        modality={effectiveModality}
      />
    ) : (
      <PredictOutputPractice
        key={`${cycle.id}-practice`}
        practice={resolvedPractice}
        onAttempt={handlePredictOutputAttempt}
        onFinished={handlePracticeFinished}
        revealOnExhaust={!cycle.remediation}
        onExhausted={handlePracticeExhausted}
        profundidad={profundidad}
      />
    )
  )
  // Resumen de una línea para la barra colapsada (UX-07: ambas mecánicas
  // citan su respuesta) — predict_output muestra la opción correcta;
  // ordering, el primer y último paso de la secuencia armada.
  const practiceAnchorSummary = (() => {
    if (!resolvedPractice) return undefined
    if (resolvedPractice.kind === 'predict_output') {
      return resolvedPractice.options.find(o => o.id === resolvedPractice.correctOptionId)?.text
    }
    const steps = resolvedPractice.items
      .filter(item => item.position !== null)
      .sort((a, b) => (a.position ?? 0) - (b.position ?? 0))
    if (steps.length === 0) return undefined
    return `${steps.length} pasos: «${steps[0].text}» → … → «${steps[steps.length - 1].text}»`
  })()

  // Fases dentro de un ciclo — cabecera compartida de la misión
  return (
    <div className={cn(
      'mx-auto py-4 space-y-6',
      labActive
        ? 'max-w-[1400px] px-4 lg:px-6'
        : practiceContextActive || phase === 'remediation' || (phase === 'reinforcement' && activeReinforcement?.practice)
          ? 'max-w-[1060px] px-4'
          : 'max-w-2xl',
    )}>
      <div className="flex items-center justify-between gap-3">
        <Button variant="ghost" size="sm" onClick={onExit}>
          <ArrowLeft className="h-4 w-4 mr-1" />
          Salir
        </Button>
        <p className="text-[11px] font-mono tracking-[0.15em] uppercase text-neural-muted/60 truncate">
          {definition.missionTitle}
        </p>
        <div className="flex items-center gap-1.5 shrink-0">
          {/* Sprint UX-01 — adaptación visible: la versión de la experiencia
              que este estudiante está viendo, siempre a la vista, nunca solo
              en notas sueltas. Mismo vocabulario de color que ya usa
              MODALITY_THEME en el resto de la plataforma. */}
          <span
            className={cn(
              'text-[10px] font-mono px-2 py-1 rounded-full border',
              MODALITY_THEME[effectiveModality].bg,
              MODALITY_THEME[effectiveModality].color,
            )}
            title={`Estás viendo la versión ${MODALITY_THEME[effectiveModality].label.toLowerCase()} de esta misión, elegida según tu forma de aprender.`}
          >
            ✦ Versión {MODALITY_THEME[effectiveModality].label}
          </span>
          <span
            className={cn(
              'text-[10px] font-mono px-2 py-1 rounded-full border',
              'border-neural-violet/30 text-neural-violet bg-neural-violet/5',
            )}
          >
            Ciclo {cycleIndex + 1} de {definition.cycles.length}
          </span>
          {/* UX-10 "Gamificación educativa": la racha de dominio YA existía
              como señal interna (fluencyStreak — ciclos cerrados donde el
              Runtime confirmó dominio con andamiaje 'reto'); ahora el
              estudiante la VE. No es un punto vacío: su consecuencia real
              es que el sistema retira andamiaje (pythonSkipStages salta
              los peldaños triviales del próximo ciclo). La recompensa ES
              el aprendizaje demostrado — se corta a 0 con cualquier
              tropiezo real, nunca se acumula por completar pantallas. */}
          {fluencyStreak > 0 && (
            <span
              className={cn(
                'text-[10px] font-mono px-2 py-1 rounded-full border',
                'border-amber-400/40 text-amber-300 bg-amber-400/10',
              )}
              title={`Cerraste ${fluencyStreak} ${fluencyStreak === 1 ? 'concepto' : 'conceptos'} seguidos demostrando dominio sin ayuda — el sistema responde retirándote andamiaje: tu próximo reto de código empieza más adelante.`}
            >
              🔥 Dominio ×{fluencyStreak}
            </span>
          )}
        </div>
      </div>

      {welcomeBackMessage && (
        <div className="rounded-xl border border-neural-glow/25 bg-neural-glow/5 px-4 py-3 flex items-start gap-2.5 animate-in fade-in slide-in-from-top-1 duration-500">
          <span className="relative flex h-2 w-2 shrink-0 mt-1.5">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-neural-glow opacity-60" />
            <span className="relative inline-flex rounded-full h-2 w-2 bg-neural-glow" />
          </span>
          <p className="text-sm text-neural-text/90 leading-relaxed">{welcomeBackMessage}</p>
        </div>
      )}

      {/* "¿Sabías que...?" (sprint "UX ¿Sabías que...?", jul 2026): pantalla
          propia al ENTRAR al ciclo. QA Final: centrada verticalmente — es
          una pausa de curiosidad, no un documento truncado con el 80% de la
          pantalla vacía debajo. */}
      {phase === 'curiosity' && cycle && cycle.curiosityFact && (
        <div className="min-h-[55vh] flex flex-col justify-center">
          <CuriosityFactCard
            fact={cycle.curiosityFact}
            onContinue={() => setPhase('concept')}
          />
        </div>
      )}

      {/* QA Final: las microexplicaciones ya NO son pantallas propias con su
          propio clic — viven compactas arriba de la teoría, dentro de
          ConceptStep (mismo contenido, mismo orden de lectura, sin peaje de
          navegación). El arranque del ciclo pasa de 2-3 interstitials a uno. */}
      {phase === 'concept' && cycle && (
        <div className="space-y-5">
          <ConceptStep
            concept={resolveConceptForRender(cycle, effectiveModality, profundidad)}
            modality={effectiveModality}
            onContinue={handleConceptDone}
            earlyReinforcement={profundidad === 'fundamentos' ? cycle.remediation?.steps[0]?.illustration : undefined}
            profundidad={profundidad}
            conceptLabel={cycle.conceptLabel}
            primers={cycle.conceptPrimers}
          />
        </div>
      )}

      {phase === 'practice' && cycle && resolvedPractice && (
        <div className="space-y-5">
          {/* remediationLevel > 0 significa que se volvió aquí YA resuelto por
           *  la escalera (handleStepSolved/handleMaxSupportContinue) — no se
           *  repite la actividad, solo se completa el cierre normal del ciclo
           *  (puente a Python, menú de consolidación) que antes se saltaba.
           *  Con el laboratorio activo, la práctica ya resuelta conserva su
           *  ancho de lectura, centrada sobre el laboratorio (UX-02). */}
          {/* UX-05: en ciclos con laboratorio, la práctica vive SIEMPRE
           *  dentro de LearningAnchor — desde antes de resolverse, no solo
           *  después — para que el wrapper nunca entre/salga del árbol en
           *  el momento de resolver (eso remontaría la práctica y perdería
           *  su estado ya resuelto; ver el comentario en LearningAnchor.tsx).
           *  `resolved` gobierna su apariencia: invisible mientras está
           *  activa, se colapsa sola en cuanto `practiceOutcome` llega. En
           *  ciclos sin laboratorio, comportamiento previo exacto: expandida
           *  a ancho de lectura, sin ancla. */}
          {remediationLevel === 0 && (
            <div className={cn(
              labActive && 'max-w-2xl mx-auto w-full',
              // QA Final: la actividad sin resolver convive con su contexto
              // (objetivo + infografía a la izquierda, sticky) — la teoría
              // queda a la vista mientras se practica, y el ancho de la
              // pantalla deja de desperdiciarse. Al resolver, practiceOutcome
              // colapsa el aside y el laboratorio toma su lugar.
              practiceContextActive && conceptAside && 'grid gap-5 items-start lg:grid-cols-[minmax(260px,300px)_minmax(0,1fr)]',
            )}>
              {practiceContextActive && conceptAside && (
                <div className="space-y-4 lg:sticky lg:top-4">{conceptAside}</div>
              )}
              {cycle.pythonBridge ? (
                <LearningAnchor
                  label={resolvedPractice.kind === 'ordering' ? 'Secuencia resuelta' : 'Predicción resuelta'}
                  summary={practiceAnchorSummary}
                  resolved={!!practiceOutcome}
                >
                  {practiceBody}
                </LearningAnchor>
              ) : (
                practiceBody
              )}
            </div>
          )}
          {practiceOutcome && cycle.pythonBridge && (
            <PythonBridge
              bridge={cycle.pythonBridge}
              moduleId={moduleId}
              conceptId={cycle.conceptId}
              courseId={courseId}
              initialProfundidad={profundidad}
              initialSkipStages={pythonSkipStages}
              layout={labActive ? 'lab' : 'inline'}
              aside={labAside}
              onPracticeDone={outcome => {
                setPythonPracticeDone(true)
                setPythonOutcome(outcome)
                if (!outcome.solutionShown) bumpMastery(cycle.conceptId, PYTHON_PRACTICE_GAIN)
              }}
            />
          )}
          {practiceOutcome && (!cycle.pythonBridge?.practice || pythonPracticeDone) && (
            <div className="flex justify-end animate-in fade-in duration-300">
              <Button onClick={handlePracticeContinue} className="gap-2">
                Continuar →
              </Button>
            </div>
          )}
        </div>
      )}

      {phase === 'remediation' && cycle && step && (
        <RemediationStepView
          key={`${cycle.id}-remediation-${step.level}`}
          step={step}
          conceptTitle={cycle.concept.title}
          conceptVariant={cycle.concept.variants[reviewModality] ?? cycle.concept.variants.reading}
          modality={stepModality}
          moduleId={moduleId}
          conceptId={cycle.conceptId}
          fallbackSolutionOf={
            cycle.remediation?.steps.find(s => s.level === 2)?.practice ??
            orderingFallbackOf(cycle.practice) ??
            EMPTY_ORDERING_FALLBACK
          }
          onSolved={handleStepSolved}
          onExhausted={handleStepExhausted}
          onContinue={handleMaxSupportContinue}
        />
      )}

      {/* UX-08 "Workspace definitivo": con práctica propia, el refuerzo es
          dos zonas — explicación (sticky) | actividad — no una pila. Sin
          práctica (animación/audio solos), una columna como siempre. */}
      {phase === 'reinforcement' && activeReinforcement && (
        <div
          className={cn(
            'animate-in fade-in duration-500',
            activeReinforcement.practice
              ? 'grid gap-5 items-start lg:grid-cols-[minmax(280px,340px)_minmax(0,1fr)]'
              : 'space-y-5',
          )}
        >
          <div className={cn('space-y-5', activeReinforcement.practice && 'lg:sticky lg:top-4')}>
            {externalResource && cycle && (
              <ExternalResourceCard
                resource={externalResource}
                framing={describeResourceFraming(effectiveModality, cycle.conceptLabel)}
              />
            )}
            <div className="glass-panel rounded-2xl p-5 space-y-4">
              <h3 className="text-base font-semibold text-neural-text">{activeReinforcement.title}</h3>
              {activeReinforcement.sceneId && <AnimatedScene sceneId={activeReinforcement.sceneId} />}
              {activeReinforcement.narrationText && (
                <AudioNarration
                  text={activeReinforcement.narrationText}
                  audioSrc={resolveNarrationAudio(activeReinforcement)}
                />
              )}
              {activeReinforcement.body.map((paragraph, i) => (
                <p key={i} className="text-sm text-neural-text/90 leading-relaxed">
                  {paragraph}
                </p>
              ))}
            </div>
          </div>

          <div className="space-y-5">
            {activeReinforcement.pythonBridge && (
              <PythonBridge
                bridge={activeReinforcement.pythonBridge}
                moduleId={moduleId}
                conceptId={cycle?.conceptId ?? ''}
                courseId={courseId}
              />
            )}

            {activeReinforcement.practice ? (
              <ReinforcementPractice
                practice={activeReinforcement.practice}
                moduleId={moduleId}
                conceptId={cycle?.conceptId ?? ''}
                modality={effectiveModality}
                onDone={handleReinforcementDone}
              />
            ) : (
              // `key` remonta el gate en cada refuerzo distinto (el estudiante
              // puede volver al menú y elegir otro) — el piso de permanencia
              // siempre arranca de cero, nunca hereda el de un refuerzo previo.
              <ReinforcementContinueGate key={activeReinforcement.title} onContinue={handleReinforcementDone} />
            )}
          </div>
        </div>
      )}
    </div>
  )
}

// ── Refuerzo sin práctica propia (animación/audio/ejemplo leído) ───────────────
// Auditoría "criterios de finalización reales" (jul 2026): "Continuar"
// estaba siempre habilitado aquí — un clic instantáneo saltaba la animación,
// la narración o el ejemplo sin haberlos visto. Mismo piso que ConceptStep,
// sin exigir nada más: es contenido de refuerzo voluntario, no una prueba.
const REINFORCEMENT_MIN_DWELL_MS = 3000

function ReinforcementContinueGate({ onContinue }: { onContinue: () => void }) {
  const dwellReady = useMinDwell(REINFORCEMENT_MIN_DWELL_MS)
  return (
    <div className="flex justify-end">
      <Button onClick={onContinue} disabled={!dwellReady} className="gap-2">
        Continuar →
      </Button>
    </div>
  )
}

// ── Reto rápido dentro del refuerzo ─────────────────────────────────────────────

function ReinforcementPractice({
  practice, moduleId, conceptId, modality, onDone,
}: {
  practice: NonNullable<Reinforcement['practice']>
  moduleId: string
  conceptId: string
  modality?: LearningModality
  onDone: () => void
}) {
  const [outcome, setOutcome] = useState<PracticeOutcome | null>(null)

  const finish = (result: PracticeOutcome) => {
    recordEvidence({
      type: 'practice_attempt',
      moduleId,
      conceptId,
      detail: {
        practice: practice.kind,
        context: 'reinforcement',
        attempts: result.attempts,
        timeMs: result.timeMs,
        solutionShown: result.solutionShown,
        outcome: outcomeLabel(result),
        final: true,
      },
    })
    setOutcome(result)
  }

  // Refuerzo VOLUNTARIO: el estudiante ya superó la baranda de autonomía y eligió
  // profundizar. Terminar la práctica —resolviéndola o viendo la solución— basta
  // para continuar. La exigencia de acertar vive en la escalera, no aquí.
  return (
    <div className="space-y-5">
      {practice.kind === 'ordering' ? (
        <OrderingPractice
          practice={practice}
          modality={modality}
          onAttempt={({ attempt, status }) => {
            recordEvidence({
              type: 'practice_attempt',
              moduleId,
              conceptId,
              detail: { practice: 'ordering', context: 'reinforcement', attempt, status, correct: status === 'correct' },
            })
          }}
          onFinished={finish}
        />
      ) : (
        <PredictOutputPractice
          practice={practice}
          onAttempt={({ attempt, correct }) => {
            recordEvidence({
              type: 'practice_attempt',
              moduleId,
              conceptId,
              detail: { practice: 'predict_output', context: 'reinforcement', attempt, correct },
            })
          }}
          onFinished={finish}
        />
      )}
      {outcome && (
        <div className="flex justify-end animate-in fade-in duration-300">
          <Button onClick={onDone} className="gap-2">
            Continuar →
          </Button>
        </div>
      )}
    </div>
  )
}

// ── Peldaño de la escalera de remediación ──────────────────────────────────────
// Estructura fija por nivel: explicación guiada → concepto re-explicado en la
// modalidad del peldaño → ilustración (ejemplo resuelto / otra representación)
// → actividad equivalente distinta. El Nivel 3 no trae actividad: muestra la
// solución explicada y deja continuar. Nunca hay un camino sin salida.

function RemediationStepView({
  step, conceptTitle, conceptVariant, modality, moduleId, conceptId,
  fallbackSolutionOf, onSolved, onExhausted, onContinue,
}: {
  step: RemediationStep
  conceptTitle: string
  conceptVariant: ConceptVariant
  modality: LearningModality
  moduleId: string
  conceptId: string
  /** De qué actividad se muestra la solución en el Nivel 3. */
  fallbackSolutionOf: OrderingPracticeDef
  onSolved: (outcome: PracticeOutcome) => void
  onExhausted: (outcome: PracticeOutcome) => void
  onContinue: () => void
}) {
  const solution = correctSequence(fallbackSolutionOf)

  // UX-08 "Workspace definitivo": la remediación era la última pantalla-
  // documento del flujo (4-5 bloques apilados). Ahora: apoyo a la
  // izquierda (por qué estás aquí + concepto re-explicado + ilustración,
  // sticky), actividad a la derecha — dos zonas, la actividad es el foco.
  return (
    <div className="space-y-5 animate-in fade-in duration-500">
      <div className="flex items-center gap-2.5">
        <LifeBuoy className="h-4 w-4 text-neural-violet shrink-0" />
        <p className="text-[11px] font-mono tracking-[0.2em] uppercase text-neural-violet">
          Apoyo · Nivel {step.level} de 3
        </p>
      </div>

      <div className="grid gap-5 items-start lg:grid-cols-[minmax(280px,340px)_minmax(0,1fr)]">
      <div className="space-y-4 lg:sticky lg:top-4">
      <div className="glass-panel rounded-2xl p-5 space-y-3">
        <h3 className="text-base font-semibold text-neural-text">{step.title}</h3>
        {step.body.map((paragraph, i) => (
          <p key={i} className="text-sm text-neural-text/90 leading-relaxed">{paragraph}</p>
        ))}
      </div>

      {/* Concepto re-explicado en la modalidad de este peldaño */}
      {step.level < 3 && (
        <div className="glass-panel rounded-2xl overflow-hidden">
          <div className="flex items-center gap-2 px-5 py-3 border-b border-white/[0.06]">
            <BookOpen className="h-4 w-4 text-neural-glow shrink-0" />
            <span className="text-[11px] font-mono tracking-[0.15em] uppercase text-neural-glow">
              {conceptTitle} · {conceptVariant.mediumLabel}
            </span>
          </div>
          <div className="px-5 py-5 space-y-4">
            {conceptVariant.body.map((paragraph, i) => (
              <p key={i} className="text-sm text-neural-text/90 leading-relaxed">{paragraph}</p>
            ))}
          </div>
        </div>
      )}

      {/* Ejemplo resuelto (N1) u otra representación (N2) — con imagen real
          declarada (imageUrl/imageAsset), se muestra ESA imagen. */}
      {step.illustration && (
        <div className="rounded-2xl border border-neural-violet/25 bg-neural-violet/5 p-4 space-y-3">
          <p className="text-[11px] font-mono tracking-[0.15em] uppercase text-neural-violet">
            {step.illustration.mediumLabel}
          </p>
          {hasIllustrationImage(step.illustration) ? (
            <IllustrationVisual
              imageUrl={step.illustration.imageUrl}
              imageAsset={step.illustration.imageAsset}
              alt={step.illustration.mediumLabel}
            />
          ) : (
            step.illustration.body.map((paragraph, i) => (
              <p key={i} className="text-sm text-neural-text/85 leading-relaxed">{paragraph}</p>
            ))
          )}
        </div>
      )}
      </div>

      <div className="space-y-5">
      {/* Actividad equivalente — distinta en cada peldaño */}
      {step.practice ? (
        <StepPractice
          practice={step.practice}
          level={step.level}
          modality={modality}
          moduleId={moduleId}
          conceptId={conceptId}
          onSolved={onSolved}
          onExhausted={onExhausted}
        />
      ) : (
        // Nivel 3 — solución completa explicada. Continuar siempre.
        <>
          <div className="rounded-2xl border border-neural-violet/30 bg-neural-violet/5 p-5 space-y-4">
            <div className="flex items-center gap-2.5">
              <GraduationCap className="h-4 w-4 text-neural-violet shrink-0" />
              <p className="text-[11px] font-mono tracking-[0.2em] uppercase text-neural-violet">
                La secuencia correcta, paso a paso
              </p>
            </div>
            <ol className="space-y-1.5">
              {solution.map((item, i) => (
                <li key={item.id} className="flex items-center gap-3 px-3 py-2 rounded-lg bg-white/[0.03] border border-white/[0.06]">
                  <span className="text-[11px] font-mono text-neural-violet shrink-0 w-5">{i + 1}.</span>
                  <span className="text-sm text-neural-text">{item.text}</span>
                </li>
              ))}
            </ol>
            {fallbackSolutionOf.solutionExplanation?.map((paragraph, i) => (
              <p key={i} className="text-sm text-neural-text/85 leading-relaxed">{paragraph}</p>
            ))}
          </div>
          <div className="flex justify-end">
            <Button onClick={onContinue} className="gap-2">Continuar →</Button>
          </div>
        </>
      )}
      </div>
      </div>
    </div>
  )
}

/** Actividad del peldaño: resolverla avanza; agotarla escala. Nunca revela la
 *  solución por su cuenta — eso es competencia exclusiva del Nivel 3. */
function StepPractice({
  practice, level, modality, moduleId, conceptId, onSolved, onExhausted,
}: {
  practice: OrderingPracticeDef
  level: number
  modality: LearningModality
  moduleId: string
  conceptId: string
  onSolved: (outcome: PracticeOutcome) => void
  onExhausted: (outcome: PracticeOutcome) => void
}) {
  const [outcome, setOutcome] = useState<PracticeOutcome | null>(null)

  return (
    <div className="space-y-5">
      <OrderingPractice
        practice={practice}
        modality={modality}
        revealOnExhaust={false}
        onAttempt={({ attempt, status }) => {
          recordEvidence({
            type: 'practice_attempt',
            moduleId,
            conceptId,
            detail: { practice: 'ordering', context: `remediation_l${level}`, modality, attempt, status, correct: status === 'correct' },
          })
        }}
        onFinished={result => {
          recordEvidence({
            type: 'practice_attempt',
            moduleId,
            conceptId,
            detail: {
              practice: 'ordering',
              context: `remediation_l${level}`,
              modality,
              attempts: result.attempts,
              timeMs: result.timeMs,
              solutionShown: result.solutionShown,
              outcome: outcomeLabel(result),
              final: true,
            },
          })
          setOutcome(result)
        }}
        onExhausted={onExhausted}
      />
      {outcome && (
        <div className="flex justify-end animate-in fade-in duration-300">
          <Button onClick={() => onSolved(outcome)} className="gap-2">Continuar →</Button>
        </div>
      )}
    </div>
  )
}
