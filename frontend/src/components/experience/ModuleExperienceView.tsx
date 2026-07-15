// Experiencia de Módulo — orquesta el patrón congelado (jul 2026):
// apertura de curiosidad → ciclos [concepto multimodal → práctica universal →
// feedback → momento de decisión] → cierre del incremento.
// La evidencia se registra localmente (mapa de dominio, cursor) Y, desde el
// refinamiento de evaluación continua, entra al Runtime real al cerrar cada
// ciclo (ver advanceCycle) — el mismo contrato que ya usaba la Evaluación de
// Módulo, solo que ahora también se dispara aquí.

import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { ArrowLeft, BookOpen, Compass, FlaskConical, GraduationCap, LifeBuoy, Map } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import { CuriosityOpening } from './CuriosityOpening'
import { ConceptStep } from './ConceptStep'
import { AnimatedScene } from './AnimatedScene'
import { AudioNarration } from './AudioNarration'
import { PythonBridge } from './PythonBridge'
import { CuriosityFactCard } from './CuriosityFactCard'
import { OrderingPractice, type PracticeOutcome } from './OrderingPractice'
import { PredictOutputPractice } from './PredictOutputPractice'
import { DecisionMenu, type DecisionChoice } from './DecisionMenu'
import { ExternalResourceCard } from './ExternalResourceCard'
import { readEvidence, recordEvidence, type RemediationEvidence } from '@/lib/experiences/evidence'
import { useSubmitCycleEvidence } from '@/hooks/useStudent'
import { correctSequence } from '@/lib/experiences/ordering'
import { fetchCourseResource, resourceTypeForModality, type CourseResource } from '@/lib/courseResource'
import type {
  ConceptVariant, ModuleExperienceDefinition, OrderingPracticeDef,
  Reinforcement, ReinforcementKind, RemediationLevel, RemediationStep,
} from '@/types/moduleExperience'
import type { LearningModality } from '@/types/modality'

// Barandas de la autonomía: bajo este dominio, la remediación decide (no hay menú);
// sobre AUTONOMY_HIGH el menú sugiere continuar.
const AUTONOMY_LOW = 0.4

type Phase =
  | 'opening'
  | 'reveal'
  | 'concept'
  | 'practice'
  | 'decision'
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

// Capa conversacional de la adaptación (refinamiento de experiencia, jul
// 2026): lo que antes era un toast técnico ("Modalidad: visual · reforzando
// fundamentos") pasa a ser una frase en primera persona, sin mencionar
// Runtime/agentes/modalidad — el estudiante nunca "abre otra herramienta",
// el sistema simplemente le ofrece la ayuda que ya decidió. Extensible por
// diseño: cuando existan más ReinforcementKind (video, imagen, podcast,
// simulación), esos casos solo agregan una entrada aquí — la mecánica
// (mensaje → pausa breve → transición) no cambia.
const REINFORCEMENT_OFFER: Record<ReinforcementKind, string> = {
  ejemplo: 'Creo que un ejemplo diferente puede ayudarte a entenderlo mejor.',
  animacion: 'Vamos a probar otra forma de explicarlo.',
  audio: 'Si prefieres, escuchemos otra explicación antes de continuar.',
  reto: 'Antes de seguir, resolvamos un reto más para afianzarlo.',
}

/** Frase que acompaña la transición entre ciclos — nunca jerga técnica.
 *  `reinforcement` ya viene filtrado por "no visitado"; su sola presencia
 *  significa que el Runtime decidió reforzar (profundidad=fundamentos). */
/** Conversación pedagógica de la transición (Pilar 3 — continuidad): nombra
 *  el concepto que el estudiante acaba de dominar y, cuando lo hay, el
 *  siguiente — nunca "esta parte" genérico. `conceptLabel`/`nextConceptLabel`
 *  ya existen en `LearningCycle` para otros fines (mapa de dominio); esto
 *  solo los reutiliza en la frase, ningún dato nuevo. */
function describeAdaptation(
  profundidad: string | undefined,
  reinforcement: Reinforcement | undefined,
  conceptLabel: string,
  nextConceptLabel: string | undefined,
): string {
  const concept = conceptLabel.toLowerCase()
  if (profundidad === 'aplicacion' && reinforcement) {
    return `Ya dominas ${concept} — ${REINFORCEMENT_OFFER[reinforcement.kind]}`
  }
  if (reinforcement) {
    return `Veo que ${concept} todavía te está costando un poco. ${REINFORCEMENT_OFFER[reinforcement.kind]}`
  }
  if (profundidad === 'fundamentos') {
    return `Vamos a reforzar ${concept} un poco más antes de seguir.`
  }
  if (nextConceptLabel) {
    return `Ya dominas ${concept}. No cambiamos de tema — vamos a construir sobre esa misma idea: ${nextConceptLabel.toLowerCase()}.`
  }
  return `Perfecto, ya dominas ${concept}. Continuemos con el siguiente desafío.`
}

/** Framing conversacional de un recurso REAL del repositorio (nunca un
 *  enlace suelto): nombra el concepto y por qué esa modalidad ayuda —
 *  mismo espíritu que describeAdaptation, mismo vocabulario de modalidad
 *  que el resto del componente. */
function describeResourceFraming(modality: LearningModality, conceptLabel: string): string {
  const concept = conceptLabel.toLowerCase()
  if (modality === 'visual') return `Creo que ${concept} se entiende mejor con una representación visual. Mira esto:`
  if (modality === 'audio') return `Escuchemos ${concept} explicado de otra forma:`
  return `Probemos ${concept} de otra manera:`
}

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
  'opening', 'reveal', 'concept', 'practice', 'decision', 'reinforcement', 'remediation', 'slice_end',
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
}

const cursorKey = (moduleId: string) => `experience-cursor:${moduleId}`

function defaultMastery(definition: ModuleExperienceDefinition): Record<string, number> {
  return Object.fromEntries(definition.cycles.map(c => [c.conceptId, c.priorMastery]))
}

function emptyCursor(mastery: Record<string, number>): ExperienceCursor {
  return {
    phase: 'opening', cycleIndex: 0, mastery,
    practiceOutcome: null, pythonOutcome: null, pythonPracticeDone: false,
    remediationLevel: 0, visitedReinforcements: [], activeReinforcementKind: null,
    autoReinforcement: false, modalityOverride: null,
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
    const saved = JSON.parse(raw) as Partial<ExperienceCursor>
    const cycleIndex = Math.min(Math.max(saved.cycleIndex ?? 0, 0), definition.cycles.length - 1)
    const phase = saved.phase && RESUMABLE_PHASES.includes(saved.phase) ? saved.phase : 'concept'
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

const MODALITY_ORDER: LearningModality[] = ['visual', 'reading', 'audio', 'kinesthetic']

/** Otra representación del mismo concepto (Nivel 2): la primera modalidad
 *  disponible distinta a la del perfil del estudiante. */
function alternateModality(current: LearningModality): LearningModality {
  return MODALITY_ORDER.find(m => m !== current) ?? current
}

/** Motor de selección de experiencias (Pilar 1 + Pilar 2 integrados):
 *  el refuerzo automático ya no es "el primero sin visitar" — es el tipo de
 *  ACTIVIDAD (interactiva/guiada/visual/auditiva) que mejor corresponde a
 *  cómo aprende el estudiante, entre los que el propio ciclo ya trae
 *  autorados. Nunca genera nada: si el tipo ideal no está en este ciclo
 *  (p. ej. módulo 2 sin 'animacion' todavía), cae al siguiente de la lista
 *  — reutilización con prioridad, exactamente como se pidió, cero recursos
 *  inventados. `reto` siempre encabeza cuando `preferChallenge` (Orientar/
 *  "aplicacion"): un desafío es interactivo por naturaleza, no depende de
 *  la modalidad de consumo. */
const REINFORCEMENT_BY_MODALITY: Record<LearningModality, ReinforcementKind[]> = {
  visual: ['animacion', 'ejemplo', 'reto', 'audio'],
  reading: ['ejemplo', 'animacion', 'reto', 'audio'],
  audio: ['audio', 'ejemplo', 'animacion', 'reto'],
  kinesthetic: ['reto', 'ejemplo', 'animacion', 'audio'],
}

function selectReinforcement(
  reinforcements: Reinforcement[] | undefined,
  visited: Set<ReinforcementKind>,
  modality: LearningModality,
  preferChallenge: boolean,
): Reinforcement | undefined {
  if (!reinforcements?.length) return undefined
  const priority = preferChallenge
    ? (['reto', ...REINFORCEMENT_BY_MODALITY[modality].filter(k => k !== 'reto')] as ReinforcementKind[])
    : REINFORCEMENT_BY_MODALITY[modality]
  for (const kind of priority) {
    const match = reinforcements.find(r => r.kind === kind && !visited.has(r.kind))
    if (match) return match
  }
  return reinforcements.find(r => !visited.has(r.kind))
}

/** Clasificación del desenlace — vale más que una nota para el evaluador. */
function outcomeLabel(outcome: PracticeOutcome): 'domino_solo' | 'con_pistas' | 'solucion_mostrada' {
  if (outcome.solutionShown) return 'solucion_mostrada'
  return outcome.attempts <= 1 ? 'domino_solo' : 'con_pistas'
}

export function ModuleExperienceView({ definition, moduleId, modality, courseId, onExit, onFinish }: Props) {
  const submitCycleEvidence = useSubmitCycleEvidence()

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
  const conceptMastery = cycle ? (mastery[cycle.conceptId] ?? 0) : 0

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

  // BUG-002 (C-51) — el cierre lo pronuncia el Agente Evaluador con la
  // evidencia real observada (dominio + remediación), no una pantalla anónima.
  // Decide el TONO, nunca el paso: continuar siempre es posible (PED-06).
  const evaluatorVerdict = useMemo(() => {
    if (phase !== 'slice_end') return null
    const values = definition.cycles.map(c => mastery[c.conceptId] ?? 0)
    const avg = values.length ? values.reduce((a, b) => a + b, 0) / values.length : 0
    const maxRemediation = readEvidence(moduleId)
      .filter(e => e.type === 'remediation_level')
      .reduce((max, e) => Math.max(max, Number(e.detail.level) || 0), 0)
    if (avg >= 0.45 && maxRemediation === 0) {
      return 'Observé tus prácticas: construiste este concepto por tu cuenta, sin necesitar apoyo. Este territorio es tuyo — podemos continuar.'
    }
    if (avg >= 0.3) {
      return 'Observé tus prácticas: lo resolviste con algo de apoyo. Es suficiente para avanzar — llevo anotado qué reforzar contigo más adelante.'
    }
    return 'Observé tus prácticas: este concepto todavía se está construyendo, y necesitaste mi ayuda máxima. Puedes continuar — lo dejé registrado para volver sobre él contigo.'
  }, [definition.cycles, mastery, moduleId, phase])

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
    })
  }, [
    moduleId, phase, cycleIndex, mastery, practiceOutcome, pythonOutcome, pythonPracticeDone,
    remediationLevel, visitedReinforcements, activeReinforcement, autoReinforcement, modalityOverride,
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
    if (cycleIndex + 1 < definition.cycles.length) {
      setCycleIndex(i => i + 1)
      setPhase('concept')
    } else {
      setPhase('slice_end')
    }
  }, [cycleIndex, definition.cycles.length])

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
    setPhase('adapting')
    submitCycleEvidence.mutate(
      { courseId, competencia: cycle.conceptId, attempts, solved },
      {
        onSuccess: (data: { runtime_decision?: { diseno?: Record<string, unknown> | null } | null }) => {
          const diseno = data?.runtime_decision?.diseno
          const profundidad = diseno?.profundidad ? String(diseno.profundidad) : undefined
          // Adaptar también recomienda una modalidad real
          // (runtime/domain/adaptar/productor.py: DISENO_POR_ACCION) — antes
          // se recibía y se descartaba igual que profundidad. Solo se honra
          // cuando coincide con una de las 4 modalidades conocidas (hoy,
          // "visual" en el caso "reforzar"; "mixta" y el resto de
          // alternativas_descartadas no tienen equivalente y se ignoran a
          // propósito, nunca se inventa una traducción).
          const modalidadRecomendada = diseno?.modalidad ? String(diseno.modalidad) : undefined
          const modalidadHonrada =
            modalidadRecomendada && MODALITY_ORDER.includes(modalidadRecomendada as LearningModality)
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
          const reinforcement = profundidad === 'fundamentos'
            ? selectReinforcement(cycle.decision?.reinforcements, visitedReinforcements, modalidadParaRefuerzo, false)
            : profundidad === 'aplicacion'
              ? selectReinforcement(cycle.decision?.reinforcements, visitedReinforcements, modalidadParaRefuerzo, true)
              : undefined
          // Capa conversacional (nunca jerga técnica: sin Runtime, agentes ni
          // modalidad) — se muestra dentro de la propia fase 'adapting', una
          // pausa de lectura breve antes de transicionar, nunca un toast aparte.
          setAdaptationMessage(describeAdaptation(
            profundidad, reinforcement, cycle.conceptLabel,
            definition.cycles[cycleIndex + 1]?.conceptLabel,
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
    if (!cycle) return
    recordEvidence({
      type: 'practice_attempt',
      moduleId,
      conceptId: cycle.conceptId,
      detail: { practice: cycle.practice.kind, attempt, status, correct: status === 'correct' },
    })
  }, [cycle, moduleId])

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
    if (!cycle) return
    recordEvidence({
      type: 'practice_attempt',
      moduleId,
      conceptId: cycle.conceptId,
      detail: {
        practice: cycle.practice.kind,
        attempts: outcome.attempts,
        timeMs: outcome.timeMs,
        solutionShown: outcome.solutionShown,
        outcome: outcomeLabel(outcome),
        final: true,
      },
    })
    bumpMastery(cycle.conceptId, masteryGain(outcome, 0))
    setPracticeOutcome(outcome)
  }, [bumpMastery, cycle, moduleId])

  /** Nivel 0 agotado: no se revela la solución — escala al Nivel 1. */
  const handlePracticeExhausted = useCallback((outcome: PracticeOutcome) => {
    if (!cycle) return
    recordRemediation(0, outcome, false, effectiveModality)
    enterRemediation(1)
  }, [cycle, effectiveModality, enterRemediation, recordRemediation])

  const handlePracticeContinue = useCallback(() => {
    if (!cycle) return
    if (!cycle.decision) {
      advanceCycle()
      return
    }
    const current = mastery[cycle.conceptId] ?? 0
    const needsSupport = current < AUTONOMY_LOW
    // Resolvió, pero el dominio no alcanza la baranda: se refuerza antes de
    // ofrecerle autonomía. La escalera siempre termina, así que esto no bloquea.
    if (needsSupport) {
      recordRemediation(0, practiceOutcome ?? { attempts: 1, timeMs: 0, solutionShown: false }, true, effectiveModality)
      enterRemediation(1)
    } else {
      setPhase('decision')
    }
  }, [advanceCycle, cycle, effectiveModality, enterRemediation, mastery, practiceOutcome, recordRemediation])

  const handleDecision = useCallback((choice: DecisionChoice) => {
    if (!cycle) return
    recordEvidence({
      type: 'choice',
      moduleId,
      conceptId: cycle.conceptId,
      detail: { choice, declaredModality: effectiveModality, masteryAtChoice: mastery[cycle.conceptId] ?? 0 },
    })
    if (choice === 'continuar') {
      advanceCycle()
      return
    }
    const reinforcement = cycle.decision?.reinforcements.find(r => r.kind === choice)
    if (reinforcement) {
      setActiveReinforcement(reinforcement)
      setPhase('reinforcement')
    } else {
      advanceCycle()
    }
  }, [advanceCycle, cycle, effectiveModality, mastery, moduleId])

  /** Refuerzo VOLUNTARIO elegido en el menú de decisión (nunca remediación).
   *  PED-005: al terminar se VUELVE AL MENÚ con lo visto marcado — el
   *  estudiante puede explorar otro refuerzo o continuar, nunca queda en un
   *  callejón por haber "elegido mal". */
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
    // Refuerzo auto-insertado por la decisión del Runtime (profundidad =
    // fundamentos): a diferencia del refuerzo voluntario del menú, aquí no
    // hay a qué menú volver — el ciclo ya se cerró, así que continúa.
    if (autoReinforcement) {
      commitAdvance()
    } else {
      setPhase('decision')
    }
  }, [activeReinforcement, autoReinforcement, bumpMastery, commitAdvance, cycle, moduleId, visitedReinforcements])

  // ── Escalera de remediación ──────────────────────────────────────────────────

  const step: RemediationStep | undefined =
    remediationLevel > 0 ? cycle?.remediation?.steps.find(s => s.level === remediationLevel) : undefined

  const stepModality: LearningModality =
    step?.conceptModality === 'alternate' ? alternateModality(effectiveModality) : effectiveModality

  /** Resolvió en este peldaño: acredita dominio reducido y sigue. */
  const handleStepSolved = useCallback((outcome: PracticeOutcome) => {
    if (!cycle || remediationLevel === 0) return
    const gain = masteryGain(outcome, remediationLevel)
    recordRemediation(remediationLevel, outcome, true, stepModality, gain)
    bumpMastery(cycle.conceptId, gain)
    advanceCycle(gain)
  }, [advanceCycle, bumpMastery, cycle, recordRemediation, remediationLevel, stepModality])

  /** Agotó este peldaño: escala al siguiente. El Nivel 3 no tiene práctica, así
   *  que la escalera termina siempre — el bloqueo es imposible por construcción. */
  const handleStepExhausted = useCallback((outcome: PracticeOutcome) => {
    if (!cycle || remediationLevel === 0) return
    recordRemediation(remediationLevel, outcome, false, stepModality)
    enterRemediation((remediationLevel + 1) as RemediationLevel)
  }, [cycle, enterRemediation, recordRemediation, remediationLevel, stepModality])

  /** Nivel 3 — ayuda máxima registrada, se continúa siempre. */
  const handleMaxSupportContinue = useCallback(() => {
    if (!cycle) return
    recordRemediation(3, { attempts: MAX_SUPPORT_ATTEMPTS, timeMs: 0, solutionShown: true }, false, stepModality)
    advanceCycle()
  }, [advanceCycle, cycle, recordRemediation, stepModality])

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
          <Button className="w-full gap-2" onClick={() => setPhase('concept')}>
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
    return (
      <div className="max-w-2xl mx-auto py-8 space-y-6 animate-in fade-in duration-500">
        <div className="glass-panel rounded-2xl p-8 space-y-6">
          <div className="flex items-center gap-2.5">
            <Map className="h-4 w-4 text-neural-glow shrink-0" />
            <p className="text-[11px] font-mono tracking-[0.2em] uppercase text-neural-glow">
              Tu mapa de dominio
            </p>
          </div>

          <div className="space-y-4">
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

          <Button className="w-full" onClick={handleFinish}>
            {/* "misión", nunca "módulo" — el resto de la experiencia ya evita esa
                palabra (missionTitle, routeTitle); este era el único lugar que
                todavía la usaba, rompiendo la sensación de aprendizaje continuo. */}
            {definition.closing.nextMission ? 'Seguir con la siguiente misión →' : 'Finalizar misión →'}
          </Button>
        </div>
      </div>
    )
  }

  // Fases dentro de un ciclo — cabecera compartida de la misión
  return (
    <div className="max-w-2xl mx-auto py-4 space-y-6">
      <div className="flex items-center justify-between gap-3">
        <Button variant="ghost" size="sm" onClick={onExit}>
          <ArrowLeft className="h-4 w-4 mr-1" />
          Salir
        </Button>
        <p className="text-[11px] font-mono tracking-[0.15em] uppercase text-neural-muted/60 truncate">
          {definition.missionTitle}
        </p>
        <span
          className={cn(
            'text-[10px] font-mono px-2 py-1 rounded-full border shrink-0',
            'border-neural-violet/30 text-neural-violet bg-neural-violet/5',
          )}
        >
          Ciclo {cycleIndex + 1} de {definition.cycles.length}
        </span>
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

      {phase === 'concept' && cycle && (
        <div className="space-y-5">
          {cycle.curiosityFact && <CuriosityFactCard fact={cycle.curiosityFact} />}
          <ConceptStep concept={cycle.concept} modality={effectiveModality} onContinue={handleConceptDone} />
        </div>
      )}

      {phase === 'practice' && cycle && (
        <div className="space-y-5">
          <OrderingPractice
            key={`${cycle.id}-practice`}
            practice={cycle.practice}
            onAttempt={handlePracticeAttempt}
            onFinished={handlePracticeFinished}
            // Con escalera, agotar intentos NO revela la solución: escala al Nivel 1.
            revealOnExhaust={!cycle.remediation}
            onExhausted={handlePracticeExhausted}
          />
          {practiceOutcome && cycle.pythonBridge && (
            <PythonBridge
              bridge={cycle.pythonBridge}
              moduleId={moduleId}
              conceptId={cycle.conceptId}
              courseId={courseId}
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

      {phase === 'decision' && cycle?.decision && (
        <DecisionMenu
          menu={cycle.decision}
          mastery={conceptMastery}
          visited={visitedReinforcements}
          onChoose={handleDecision}
        />
      )}

      {phase === 'remediation' && cycle && step && (
        <RemediationStepView
          key={`${cycle.id}-remediation-${step.level}`}
          step={step}
          conceptTitle={cycle.concept.title}
          conceptVariant={cycle.concept.variants[stepModality] ?? cycle.concept.variants.reading}
          modality={stepModality}
          moduleId={moduleId}
          conceptId={cycle.conceptId}
          fallbackSolutionOf={cycle.remediation?.steps.find(s => s.level === 2)?.practice ?? cycle.practice}
          onSolved={handleStepSolved}
          onExhausted={handleStepExhausted}
          onContinue={handleMaxSupportContinue}
        />
      )}

      {phase === 'reinforcement' && activeReinforcement && (
        <div className="space-y-5 animate-in fade-in duration-500">
          {externalResource && cycle && (
            <ExternalResourceCard
              resource={externalResource}
              framing={describeResourceFraming(effectiveModality, cycle.conceptLabel)}
            />
          )}
          <div className="glass-panel rounded-2xl p-6 space-y-4">
            <h3 className="text-base font-semibold text-neural-text">{activeReinforcement.title}</h3>
            {activeReinforcement.sceneId && <AnimatedScene sceneId={activeReinforcement.sceneId} />}
            {activeReinforcement.narrationText && <AudioNarration text={activeReinforcement.narrationText} />}
            {activeReinforcement.body.map((paragraph, i) => (
              <p key={i} className="text-sm text-neural-text/90 leading-relaxed">
                {paragraph}
              </p>
            ))}
          </div>

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
              onDone={handleReinforcementDone}
            />
          ) : (
            <div className="flex justify-end">
              <Button onClick={handleReinforcementDone} className="gap-2">
                Continuar →
              </Button>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

// ── Reto rápido dentro del refuerzo ─────────────────────────────────────────────

function ReinforcementPractice({
  practice, moduleId, conceptId, onDone,
}: {
  practice: NonNullable<Reinforcement['practice']>
  moduleId: string
  conceptId: string
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

  return (
    <div className="space-y-5 animate-in fade-in duration-500">
      <div className="flex items-center gap-2.5">
        <LifeBuoy className="h-4 w-4 text-neural-violet shrink-0" />
        <p className="text-[11px] font-mono tracking-[0.2em] uppercase text-neural-violet">
          Apoyo · Nivel {step.level} de 3
        </p>
      </div>

      <div className="glass-panel rounded-2xl p-6 space-y-4">
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
          <div className="px-6 py-6 space-y-4">
            {conceptVariant.body.map((paragraph, i) => (
              <p key={i} className="text-sm text-neural-text/90 leading-relaxed">{paragraph}</p>
            ))}
          </div>
        </div>
      )}

      {/* Ejemplo resuelto (N1) u otra representación (N2) */}
      {step.illustration && (
        <div className="rounded-2xl border border-neural-violet/25 bg-neural-violet/5 p-5 space-y-3">
          <p className="text-[11px] font-mono tracking-[0.15em] uppercase text-neural-violet">
            {step.illustration.mediumLabel}
          </p>
          {step.illustration.body.map((paragraph, i) => (
            <p key={i} className="text-sm text-neural-text/85 leading-relaxed">{paragraph}</p>
          ))}
        </div>
      )}

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
