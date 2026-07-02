import { useState, useCallback, useRef } from 'react'
import { ChevronLeft, ChevronRight, CheckCircle, X, Zap } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import { JourneyProgress }         from './JourneyProgress'
import { FiveEProgressBar }        from './FiveEProgressBar'
import { MultimodalRenderer }      from './MultimodalRenderer'
import { PhaseTransitionOverlay }  from './PhaseTransitionOverlay'
import { AdaptationEcho }          from './AdaptationEcho'
import { MODALITY_EMOJI, resolveStepPhase } from './journeyStepConfig'
import type { LearningJourney as JourneyData } from '@/types/learningJourney'
import type { Phase5E } from '@/types/learningJourney'
import type { CompletionSignal } from '@/types/learningJourney'
import { MODALITY_LABEL, type LearningModality } from '@/types/modality'

interface Props {
  journey:           JourneyData
  onComplete?:       () => void
  onTotalXpChange?:  (xp: number) => void
}

// Sprint 2.2 — Milestones rediseñados: checklist de progreso del estudiante.
// Protagonista: el estudiante, no el sistema.
// Regla del 20% (ronda 5): responde SOLO "¿Qué logré hasta ahora?".
// Lo que viene después lo narran el hilo conductor (FiveEProgressBar) y el
// StepContextTag — anticipar aquí sería responder una segunda pregunta.
type ModalityKey = LearningModality | 'default'

const MILESTONE_MESSAGES: Record<25 | 50 | 75, Record<ModalityKey, string>> = {
  25: {
    visual:      '\u2714 Exploraste la idea con imágenes y analogías.\n\u2714 Tu punto de partida quedó registrado.',
    reading:     '\u2714 Leíste el concepto a tu ritmo.\n\u2714 Los ejemplos comentados quedaron disponibles.',
    audio:       '\u2714 Escuchaste la idea antes de leerla.\n\u2714 Tu punto de partida quedó registrado.',
    kinesthetic: '\u2714 Probaste antes de recibir la explicación.\n\u2714 Tu intuición quedó registrada.',
    default:     '\u2714 Completaste el primer bloque del recorrido.\n\u2714 Tu punto de partida quedó registrado.',
  },
  50: {
    visual:      '\u2714 Construiste el concepto desde ejemplos visuales.\n\u2714 Lo viste aplicado al menos una vez.',
    reading:     '\u2714 Construiste el concepto a tu propio ritmo.\n\u2714 Los casos concretos completaron la idea.',
    audio:       '\u2714 Escuchaste y leíste el concepto.\n\u2714 Los ejemplos consolidaron la idea.',
    kinesthetic: '\u2714 Probaste y luego construiste el concepto.\n\u2714 La práctica ancló la idea.',
    default:     '\u2714 Construiste el concepto desde la evidencia.\n\u2714 Lo viste aplicado al menos una vez.',
  },
  75: {
    visual:      '\u2714 La teoría quedó construida con imágenes y diagramas.\n\u2714 Ya aplicaste el concepto al menos una vez.',
    reading:     '\u2714 La teoría quedó construida con texto y ejemplos.\n\u2714 Ya aplicaste el concepto al menos una vez.',
    audio:       '\u2714 La teoría quedó consolidada.\n\u2714 Ya aplicaste el concepto al menos una vez.',
    kinesthetic: '\u2714 Construiste y aplicaste el concepto.\n\u2714 La práctica confirmó la comprensión.',
    default:     '\u2714 La teoría quedó construida.\n\u2714 Ya aplicaste el concepto al menos una vez.',
  },
} as const

function getMilestoneMessage(pct: 25 | 50 | 75, modality: LearningModality | undefined): string {
  const byPct = MILESTONE_MESSAGES[pct]
  const key: ModalityKey = (modality && modality in byPct) ? modality : 'default'
  return byPct[key]
}

// ── Sprint 2.1 (rediseño) — banner inspirado en "Contenido Adaptativo" + "Swarm Monitor"
// Estructura: origen de la adaptación → detección → beneficio personal.
// Regla del 20% (ronda 5): responde SOLO "¿Por qué este módulo empieza
// diferente?". La anticipación de secuencia se eliminó — era una segunda
// pregunta; el "¿por qué ahora?" de cada paso lo responde el StepContextTag.
// Referencia visual: CURRENT ADAPTATION section + Agent Decision Stream
// Lenguaje centrado en la adaptación, no en el actor: nada de "el Enjambre
// analizó/detectó" ni "notamos" — el recorrido se ajustó A PARTIR DE las
// respuestas del estudiante. El protagonista es el estudiante.

const MODALITY_BANNER: Record<LearningModality, {
  /** Por qué el módulo se organizó así — centrado en la adaptación, sin nombrar al actor */
  intro:        string
  /** Qué mostraron las respuestas del estudiante */
  detection:    string
  /** Cómo beneficia eso al estudiante — tono personal, no descriptivo */
  benefit:      string
  /** Etiqueta del badge de confianza — referencia: CONFIDENCE 96.4% */
  confidence:   string
}> = {
  visual: {
    intro:      'Este módulo se organizó a partir de tus respuestas iniciales y de cómo construyes conocimiento.',
    detection:  'Tus respuestas muestran que captas ideas más rápido cuando primero las ves.',
    benefit:    'Eso significa que este módulo arranca exactamente como mejor funciona para ti: con imágenes y analogías antes de la teoría.',
    confidence: 'Perfil visual · alta confianza',
  },
  reading: {
    intro:      'Este módulo se organizó a partir de tu ritmo y de tu forma de procesar información nueva.',
    detection:  'Tus respuestas revelan que profundizas mejor cuando lees con calma y a tu propio paso.',
    benefit:    'Por eso este módulo te da primero el texto con ejemplos comentados — sin presión de ritmo.',
    confidence: 'Perfil lector · alta confianza',
  },
  audio: {
    intro:      'Este módulo se organizó a partir de cómo procesas las ideas cuando las escuchas.',
    detection:  'Tus respuestas muestran que retienes mejor las ideas cuando primero las escuchas explicadas.',
    benefit:    'Por eso este módulo priorizará la narración antes de mostrarte el concepto escrito.',
    confidence: 'Perfil auditivo · alta confianza',
  },
  kinesthetic: {
    intro:      'Este módulo se organizó a partir de tus respuestas: tu aprendizaje se activa cuando haces, no solo cuando lees.',
    detection:  'Tus respuestas confirman que construyes comprensión más sólida desde la práctica directa.',
    benefit:    'Por eso este módulo te lleva al reto antes de completar la teoría — aprendes haciendo.',
    confidence: 'Perfil kinestésico · alta confianza',
  },
}

// Modality accent colors for the banner header bar — matches Neural Swarm palette
const MODALITY_ACCENT: Record<LearningModality, string> = {
  visual:      'bg-violet-500',
  reading:     'bg-indigo-500',
  audio:       'bg-sky-500',
  kinesthetic: 'bg-orange-500',
}

const MODALITY_BORDER: Record<LearningModality, string> = {
  visual:      'border-violet-200 dark:border-violet-500/30',
  reading:     'border-indigo-200 dark:border-indigo-500/30',
  audio:       'border-sky-200    dark:border-sky-500/30',
  kinesthetic: 'border-orange-200 dark:border-orange-500/30',
}

const MODALITY_BG: Record<LearningModality, string> = {
  visual:      'bg-violet-50/60  dark:bg-violet-500/5',
  reading:     'bg-indigo-50/60  dark:bg-indigo-500/5',
  audio:       'bg-sky-50/60     dark:bg-sky-500/5',
  kinesthetic: 'bg-orange-50/60  dark:bg-orange-500/5',
}

const MODALITY_COLOR: Record<LearningModality, string> = {
  visual:      'text-violet-600 dark:text-violet-300',
  reading:     'text-indigo-600 dark:text-indigo-300',
  audio:       'text-sky-600    dark:text-sky-300',
  kinesthetic: 'text-orange-600 dark:text-orange-300',
}

function isKnownModality(value: string | undefined): value is LearningModality {
  return value !== undefined && value in MODALITY_LABEL
}

/**
 * LearningJourney — Sprint J1 / Sprint 2.1 (rediseño visual)
 *
 * Responsabilidades:
 * - Navegación lineal entre pasos (prev / next)
 * - Bloqueo de avance cuando step.requiresAnswer y el paso aún no disparó onComplete
 * - Acumulación de XP local + flash animado
 * - Detección de cambio de fase 5E → PhaseTransitionOverlay
 * - Banner CURRENT ADAPTATION rediseñado (referencia: pantalla "Contenido Adaptativo")
 * - Transición de fade entre pasos
 */
export function LearningJourney({ journey, onComplete, onTotalXpChange }: Props) {
  const [currentIndex,     setCurrentIndex]     = useState(0)
  const [completedSteps,   setCompletedSteps]   = useState<Set<string>>(new Set())
  const [totalXp,          setTotalXp]          = useState(0)
  const [xpFlash,          setXpFlash]          = useState<number | null>(null)
  const [cardVisible,      setCardVisible]      = useState(true)
  const [milestone,        setMilestone]        = useState<string | null>(null)
  const [bannerDismissed,  setBannerDismissed]  = useState(false)
  // Sprint 2.1 — overlay de transición de fase
  const [phaseOverlay,     setPhaseOverlay]     = useState<Phase5E | null>(null)
  // Sprint 2.2 — eco de adaptación post-completado
  const [echoSignal,       setEchoSignal]       = useState<CompletionSignal | null>(null)

  // Sprint 2.2 — milestone threshold tracking
  const shownMilestones = useRef<Set<number>>(new Set())

  // Milestones: 25 / 50 / 75 %
  const MILESTONE_THRESHOLDS = [0.25, 0.50, 0.75] as const

  const steps  = journey.steps
  const total  = steps.length
  const step   = steps[currentIndex]
  const isLast = currentIndex === total - 1

  const isCurrentCompleted = step ? completedSteps.has(step.id) : true
  const canAdvance         = !step?.requiresAnswer || isCurrentCompleted

  // ── Navigation ──────────────────────────────────────────────────────────────

  const changeStep = useCallback((nextIndex: number) => {
    setCardVisible(false)
    setTimeout(() => {
      setCurrentIndex(nextIndex)
      setCardVisible(true)
    }, 150)
  }, [])

  const goNext = useCallback(() => {
    if (!canAdvance) return
    if (isLast) {
      onComplete?.()
    } else {
      const nextIndex = currentIndex + 1

      // Milestone check — Sprint 2.2: mensajes como checklist de progreso del estudiante
      const pct = (nextIndex + 1) / total
      for (const threshold of MILESTONE_THRESHOLDS) {
        if (!shownMilestones.current.has(threshold) && pct >= threshold) {
          shownMilestones.current.add(threshold)
          const pctKey = Math.round(threshold * 100) as 25 | 50 | 75
          setMilestone(getMilestoneMessage(pctKey, modality ?? undefined))
          clearTimeout(milestoneTimer.current)
          milestoneTimer.current = setTimeout(() => setMilestone(null), 5000)
          break
        }
      }

      // Sprint 2.1 — fase 5E: detectar cambio de fase antes de navegar
      const currentPhase = resolveStepPhase(step)
      const nextStep     = steps[nextIndex]
      const nextPhase    = nextStep ? resolveStepPhase(nextStep) : null

      if (nextPhase && nextPhase !== currentPhase) {
        // Mostrar overlay de transición; la navegación real ocurre al dismiss
        setPhaseOverlay(nextPhase)
        // changeStep se llama desde handlePhaseOverlayDismiss
      } else {
        changeStep(nextIndex)
      }

      // Guardar el índice pendiente para que el dismiss lo use
      pendingIndexRef.current = nextIndex
    }
  }, [canAdvance, isLast, currentIndex, total, changeStep, onComplete, step, steps])

  // Índice al que iremos después del overlay — evita closure stale
  const pendingIndexRef = useRef<number>(0)

  const handlePhaseOverlayDismiss = useCallback(() => {
    setPhaseOverlay(null)
    changeStep(pendingIndexRef.current)
  }, [changeStep])

  const goPrev = useCallback(() => {
    if (currentIndex > 0) changeStep(currentIndex - 1)
  }, [currentIndex, changeStep])

  // ── Step completion + XP ───────────────────────────────────────────────────

  const handleComplete = useCallback((signal?: CompletionSignal) => {
    if (!step) return
    setCompletedSteps(prev => {
      const next = new Set(prev)
      next.add(step.id)
      return next
    })
    // Sprint 2.2 — mostrar echo si el paso tiene señal significativa
    if (signal) setEchoSignal(signal)
  }, [step])

  const handleXp = useCallback((amount: number) => {
    setTotalXp(prev => {
      const next = prev + amount
      onTotalXpChange?.(next)
      return next
    })
    setXpFlash(amount)
    clearTimeout(xpTimer.current)
    xpTimer.current = setTimeout(() => setXpFlash(null), 2200)
  }, [onTotalXpChange])

  // ── Render ─────────────────────────────────────────────────────────────────

  if (!step) return null

  const modality = isKnownModality(journey.dominantModality) ? journey.dominantModality : null
  const banner   = modality ? MODALITY_BANNER[modality] : null

  // Sprint 2.2 — resetear echo al cambiar de paso
  const prevIndexRef = useRef(currentIndex)
  if (prevIndexRef.current !== currentIndex) {
    prevIndexRef.current = currentIndex
    if (echoSignal !== null) setEchoSignal(null)
  }

  return (
    <>
      {/* Sprint 2.1 — Phase transition overlay (portal-like, covers full viewport) */}
      {phaseOverlay && (
        <PhaseTransitionOverlay
          phase={phaseOverlay}
          onDismiss={handlePhaseOverlayDismiss}
        />
      )}

      <div className="max-w-3xl mx-auto py-8 px-5 space-y-6 animate-in fade-in duration-500">

        {/* ── Sprint 2.1 — Banner "MÓDULO PREPARADO PARA TI"
            Referencia visual: sección "CURRENT ADAPTATION" de Contenido Adaptativo.
            Estructura: thin accent bar + label + origen de la adaptación + detección + beneficio + secuencia */}
        {modality && banner && !bannerDismissed && (
          <div className={cn(
            'relative rounded-xl border overflow-hidden',
            MODALITY_BORDER[modality],
            MODALITY_BG[modality],
            'animate-in fade-in slide-in-from-top-2 duration-500',
          )}>

            {/* Thin accent bar top — referencia: Contenido Adaptativo header */}
            <div className={cn('h-[3px] w-full', MODALITY_ACCENT[modality])} />

            <div className="px-5 py-4 pr-11 space-y-3.5">

              {/* Label "CURRENT ADAPTATION" style */}
              <div className="flex items-center gap-2.5">
                <Zap className={cn('h-3.5 w-3.5 shrink-0', MODALITY_COLOR[modality])} aria-hidden="true" />
                <p className={cn('text-[10px] font-mono font-bold tracking-[0.25em] uppercase', MODALITY_COLOR[modality])}>
                  Módulo preparado para ti
                </p>
                {/* Confidence badge — referencia: CONFIDENCE 96.4% */}
                <span className={cn(
                  'ml-auto text-[10px] font-mono font-semibold tracking-wide px-2 py-0.5 rounded-full border',
                  MODALITY_COLOR[modality],
                  MODALITY_BORDER[modality],
                  'bg-white/40 dark:bg-black/20',
                )}>
                  {MODALITY_EMOJI[modality]} {banner.confidence}
                </span>
              </div>

              {/* Origin sentence — por qué el módulo se organizó así */}
              <p className="text-xs text-gray-500 dark:text-gray-400 leading-relaxed italic">
                {banner.intro}
              </p>

              {/* Detection — qué mostraron las respuestas del estudiante */}
              <p className="text-sm font-medium text-gray-800 dark:text-gray-200 leading-relaxed">
                {banner.detection}
              </p>

              {/* Benefit — qué significa para el estudiante */}
              <p className="text-sm text-gray-700 dark:text-gray-300 leading-relaxed">
                {banner.benefit}
              </p>

            </div>

            {/* Dismiss button */}
            <button
              type="button"
              aria-label="Cerrar aviso de personalización"
              onClick={() => setBannerDismissed(true)}
              className="absolute top-3 right-3 rounded-md p-1 text-muted-foreground/50 hover:text-foreground hover:bg-black/5 dark:hover:bg-white/10 transition-colors"
            >
              <X className="h-3.5 w-3.5" />
            </button>
          </div>
        )}

        {/* Header: module title + progress */}
        <div className="space-y-2">
          <p className="text-xs font-mono text-muted-foreground uppercase tracking-widest">
            🎓 {journey.moduleTitle}
          </p>
          <JourneyProgress
            currentIndex={currentIndex}
            totalSteps={total}
            currentType={step.type}
            totalXp={totalXp}
            xpFlash={xpFlash}
            phase={resolveStepPhase(step)}
          />
          {/* Sprint 2.1 — modelo 5E visible como recorrido narrado */}
          <div className="pt-1">
            <FiveEProgressBar steps={steps} currentIndex={currentIndex} />
          </div>
        </div>

        {/* Milestone overlay */}
        {milestone && (
          <div className={cn(
            'rounded-xl border border-emerald-200 dark:border-emerald-800',
            'bg-gradient-to-r from-emerald-50 via-teal-50 to-cyan-50 dark:from-emerald-950/40 dark:via-teal-950/30',
            'px-5 py-4 text-center',
            'animate-in fade-in zoom-in-95 duration-400',
          )}>
            <p className="text-base font-bold text-emerald-700 dark:text-emerald-300">
              {milestone}
            </p>
          </div>
        )}

        {/* Step card with fade transition */}
        <div className={cn(
          'transition-opacity duration-150',
          cardVisible ? 'opacity-100' : 'opacity-0',
        )}>
          <MultimodalRenderer
            step={step}
            modality={journey.dominantModality as LearningModality | undefined}
            onComplete={handleComplete}
            onXp={handleXp}
          />
        </div>

        {/* Sprint 2.2 — AdaptationEcho: aparece después de completar un paso interactivo
            Siempre causa → consecuencia. Protagonista: el estudiante, no la IA.
            No desaparece solo; el estudiante lo lee cuando quiera antes de Siguiente. */}
        {echoSignal && isCurrentCompleted && (
          <AdaptationEcho
            stepType={step.type}
            quality={echoSignal.quality}
            modality={modality ?? undefined}
          />
        )}

        {/* Navigation */}
        <div className="flex items-center justify-between gap-3">
          <Button
            variant="ghost"
            size="sm"
            onClick={goPrev}
            disabled={currentIndex === 0}
            className="gap-1"
          >
            <ChevronLeft className="h-4 w-4" />
            Anterior
          </Button>

          <Button
            size="sm"
            onClick={goNext}
            disabled={!canAdvance}
            title={!canAdvance ? 'Completa este paso para continuar' : undefined}
            className={cn(
              'gap-1.5 transition-all',
              isLast
                ? 'bg-emerald-600 hover:bg-emerald-700 text-white gap-2 shadow-md shadow-emerald-200 dark:shadow-emerald-900/30'
                : '',
            )}
          >
            {isLast ? (
              <>
                <CheckCircle className="h-4 w-4" />
                Completar módulo
              </>
            ) : (
              <>
                Siguiente
                <ChevronRight className="h-4 w-4" />
              </>
            )}
          </Button>
        </div>

      </div>
    </>
  )
}
