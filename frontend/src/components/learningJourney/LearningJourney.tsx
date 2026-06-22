import { useState, useCallback, useRef } from 'react'
import { ChevronLeft, ChevronRight, CheckCircle } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import { JourneyProgress }      from './JourneyProgress'
import { LearningJourneyStep }  from './LearningJourneyStep'
import type { LearningJourney as JourneyData } from '@/types/learningJourney'

interface Props {
  journey:           JourneyData
  onComplete?:       () => void
  onTotalXpChange?:  (xp: number) => void
}

/**
 * LearningJourney — Sprint J1
 *
 * Orquestador principal del Unified Learning Journey.
 *
 * Responsabilidades:
 * - Navegación lineal entre pasos (prev / next)
 * - Bloqueo de avance cuando step.requiresAnswer === true y el paso
 *   aún no disparó onComplete
 * - Acumulación de XP local + flash animado
 * - Transición de fade entre pasos (misma duración que EngagePhase)
 *
 * Sprint J2 conectará JourneyData con EngagementSession +
 * ModuleOrchestrationResponse a través de un adapter builder.
 */
export function LearningJourney({ journey, onComplete, onTotalXpChange }: Props) {
  const [currentIndex,    setCurrentIndex]    = useState(0)
  const [completedSteps,  setCompletedSteps]  = useState<Set<string>>(new Set())
  const [totalXp,         setTotalXp]         = useState(0)
  const [xpFlash,         setXpFlash]         = useState<number | null>(null)
  const [cardVisible,     setCardVisible]     = useState(true)
  const xpTimer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined)

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
      changeStep(currentIndex + 1)
    }
  }, [canAdvance, isLast, currentIndex, changeStep, onComplete])

  const goPrev = useCallback(() => {
    if (currentIndex > 0) changeStep(currentIndex - 1)
  }, [currentIndex, changeStep])

  // ── Step completion + XP ───────────────────────────────────────────────────

  const handleComplete = useCallback(() => {
    if (!step) return
    setCompletedSteps(prev => {
      const next = new Set(prev)
      next.add(step.id)
      return next
    })
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

  return (
    <div className="max-w-2xl mx-auto py-6 px-4 space-y-6 animate-in fade-in duration-500">

      {/* Header: module title + progress */}
      <div className="space-y-1.5">
        <p className="text-xs font-mono text-muted-foreground uppercase tracking-widest">
          🎓 {journey.moduleTitle}
        </p>
        <JourneyProgress
          currentIndex={currentIndex}
          totalSteps={total}
          currentType={step.type}
          totalXp={totalXp}
          xpFlash={xpFlash}
        />
      </div>

      {/* Step card with fade transition */}
      <div className={cn(
        'transition-opacity duration-150',
        cardVisible ? 'opacity-100' : 'opacity-0',
      )}>
        <LearningJourneyStep
          step={step}
          onComplete={handleComplete}
          onXp={handleXp}
        />
      </div>

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
  )
}
