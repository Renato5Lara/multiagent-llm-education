// Experiencia de Módulo — orquesta el patrón congelado (jul 2026):
// apertura de curiosidad → ciclos [concepto multimodal → práctica universal →
// feedback → momento de decisión] → cierre del incremento.
// S1: mock-first — sin backend nuevo; la evidencia se registra localmente con
// el mismo contrato que en S3/S4 consumirá el agente evaluador.

import { useCallback, useEffect, useMemo, useState } from 'react'
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
import { DecisionMenu, type DecisionChoice } from './DecisionMenu'
import { readEvidence, recordEvidence, type RemediationEvidence } from '@/lib/experiences/evidence'
import { correctSequence } from '@/lib/experiences/ordering'
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
  | 'reinforcement'
  | 'remediation'
  | 'slice_end'

// A1 — persistencia temporal del cursor en localStorage: reanuda tras recarga o
// salida sin perder el avance. Provisional (S1); migrará a Misión Activa backend
// en S3. Solo se persiste el estado reconstruible.
// 'practice' y 'decision' SÍ reanudan directo: ninguno de los dos depende de
// estado efímero para renderizar (practice arranca limpia; decision solo
// necesita `mastery`, ya persistido). 'reinforcement' y 'remediation' no —
// dependen de qué refuerzo/peldaño estaba activo (estado en memoria, no
// persistido) y resumir ahí en blanco rompería la pantalla; caen al concepto
// del ciclo actual, conservando el dominio (refinamiento de experiencia, jul
// 2026 — "si regreso atrás me reinicia la sesión" rompía la inmersión).
const RESUMABLE_PHASES: Phase[] = ['opening', 'reveal', 'concept', 'practice', 'decision', 'slice_end']

interface ExperienceCursor {
  phase: Phase
  cycleIndex: number
  mastery: Record<string, number>
}

const cursorKey = (moduleId: string) => `experience-cursor:${moduleId}`

function defaultMastery(definition: ModuleExperienceDefinition): Record<string, number> {
  return Object.fromEntries(definition.cycles.map(c => [c.conceptId, c.priorMastery]))
}

function loadCursor(moduleId: string, definition: ModuleExperienceDefinition): ExperienceCursor {
  const base = defaultMastery(definition)
  try {
    const raw = localStorage.getItem(cursorKey(moduleId))
    if (!raw) return { phase: 'opening', cycleIndex: 0, mastery: base }
    const saved = JSON.parse(raw) as Partial<ExperienceCursor>
    const cycleIndex = Math.min(Math.max(saved.cycleIndex ?? 0, 0), definition.cycles.length - 1)
    const phase = saved.phase && RESUMABLE_PHASES.includes(saved.phase) ? saved.phase : 'concept'
    return { phase, cycleIndex, mastery: { ...base, ...(saved.mastery ?? {}) } }
  } catch {
    return { phase: 'opening', cycleIndex: 0, mastery: base }
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

/** Clasificación del desenlace — vale más que una nota para el evaluador. */
function outcomeLabel(outcome: PracticeOutcome): 'domino_solo' | 'con_pistas' | 'solucion_mostrada' {
  if (outcome.solutionShown) return 'solucion_mostrada'
  return outcome.attempts <= 1 ? 'domino_solo' : 'con_pistas'
}

export function ModuleExperienceView({ definition, moduleId, modality, onExit, onFinish }: Props) {
  const effectiveModality: LearningModality = modality ?? 'reading'

  // A1 — rehidratar el cursor persistido una sola vez al montar.
  const [initialCursor] = useState<ExperienceCursor>(() => loadCursor(moduleId, definition))
  const [phase, setPhase] = useState<Phase>(initialCursor.phase)
  const [cycleIndex, setCycleIndex] = useState(initialCursor.cycleIndex)
  const [mastery, setMastery] = useState<Record<string, number>>(initialCursor.mastery)
  const [activeReinforcement, setActiveReinforcement] = useState<Reinforcement | null>(null)
  // PED-005 — refuerzos ya explorados en el ciclo actual: al terminar uno se
  // vuelve al menú (elegir nunca es un callejón) y el dominio del refuerzo se
  // acredita solo la primera vez por tipo.
  const [visitedReinforcements, setVisitedReinforcements] = useState<Set<ReinforcementKind>>(new Set())
  // Peldaño activo de la escalera. 0 = actividad principal (sin remediación).
  const [remediationLevel, setRemediationLevel] = useState<RemediationLevel>(0)
  // Desenlace de la práctica del ciclo actual — habilita Continuar SIEMPRE
  // (nunca-bloquear), incluso cuando se mostró la solución.
  const [practiceOutcome, setPracticeOutcome] = useState<PracticeOutcome | null>(null)

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

  // A1 — persistir el cursor en cada cambio de fase/ciclo/dominio.
  useEffect(() => {
    saveCursor(moduleId, { phase, cycleIndex, mastery })
  }, [moduleId, phase, cycleIndex, mastery])

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

  /** @param pendingGain ganancia que el llamador acaba de aplicar con bumpMastery.
   *  El estado `mastery` de este closure es el ANTERIOR al bump (React agrupa las
   *  actualizaciones), así que sin sumarla aquí el evento `cycle_completed`
   *  reportaría al evaluador un dominio desfasado. */
  const advanceCycle = useCallback((pendingGain = 0) => {
    if (!cycle) return
    const finalMastery = Math.min(1, Math.max(0, (mastery[cycle.conceptId] ?? 0) + pendingGain))
    // PUNTO DE INTEGRACIÓN FUTURA (evaluación continua, sin implementar
    // todavía): este es el momento exacto en que un ciclo cierra con un
    // dominio real medido (intentos, pistas, tiempo — no un puntaje
    // inventado). Hoy `recordEvidence` solo persiste en localStorage y
    // alimenta el mapa de dominio local del estudiante. El día que se decida
    // conectar esta señal al Runtime real, el destino es
    // `runtime_bridge.registrar_evidencia_evaluacion` (mismo contrato que ya
    // usa la evaluación de módulo) — la cadencia (cada ciclo vs. acumulado)
    // es una decisión de diseño pendiente, no una que deba resolverse aquí.
    recordEvidence({
      type: 'cycle_completed',
      moduleId,
      conceptId: cycle.conceptId,
      detail: { cycleId: cycle.id, mastery: Math.round(finalMastery * 100) / 100 },
    })
    // Limpia TODO el estado del ciclo completado antes de avanzar.
    // Sin esto, practiceOutcome del ciclo anterior puede hacer que el
    // botón "Continuar" aparezca instantáneamente al montar el siguiente ciclo.
    setActiveReinforcement(null)
    setVisitedReinforcements(new Set())
    setRemediationLevel(0)
    setPracticeOutcome(null)   // ← crítico: reset entre ciclos
    if (cycleIndex + 1 < definition.cycles.length) {
      setCycleIndex(i => i + 1)
      setPhase('concept')
    } else {
      setPhase('slice_end')
    }
  }, [cycle, cycleIndex, definition.cycles.length, mastery, moduleId])


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
    setPhase('decision')
  }, [activeReinforcement, bumpMastery, cycle, moduleId, visitedReinforcements])

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
            {definition.closing.nextMission ? 'Continuar al siguiente módulo →' : 'Finalizar misión →'}
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
            <PythonBridge bridge={cycle.pythonBridge} />
          )}
          {practiceOutcome && (
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

          {activeReinforcement.pythonBridge && <PythonBridge bridge={activeReinforcement.pythonBridge} />}

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

  // Refuerzo VOLUNTARIO: el estudiante ya superó la baranda de autonomía y eligió
  // profundizar. Terminar la práctica —resolviéndola o viendo la solución— basta
  // para continuar. La exigencia de acertar vive en la escalera, no aquí.
  return (
    <div className="space-y-5">
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
        onFinished={result => {
          recordEvidence({
            type: 'practice_attempt',
            moduleId,
            conceptId,
            detail: {
              practice: 'ordering',
              context: 'reinforcement',
              attempts: result.attempts,
              timeMs: result.timeMs,
              solutionShown: result.solutionShown,
              outcome: outcomeLabel(result),
              final: true,
            },
          })
          setOutcome(result)
        }}
      />
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
