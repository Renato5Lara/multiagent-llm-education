import { useCallback, useEffect, useRef, useState } from 'react'
import { SkipForward, ArrowRight } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { useInteractEngagement, useCompleteEngagement } from '@/hooks/useEngagement'
import type { EngagementSession } from '@/types/engagement'
import { SilenceScreen } from './SilenceScreen'
import { DidYouKnowCard } from './cards/DidYouKnowCard'
import { DetonatingQuestionCard } from './cards/DetonatingQuestionCard'

type Phase = 'silence' | 'curiosity' | 'question'

interface Props {
  session: EngagementSession
  moduleTitle?: string
  onComplete: () => void
  onSkip: () => void
  onProgress?: (index: number) => void
}

/**
 * EntryGate — "La Puerta de Entrada" (Momento 1 del Journey, fase ENGAGE).
 *
 * Fase A (Silencio Visual) → Fase B (Dato Curioso Adaptativo, reusa
 * did_you_know) → Fase C (Activación Cognitiva, reusa detonating_question).
 *
 * Scope decision (2026-07): esta es toda la experiencia de apertura por
 * ahora. prior_knowledge / real_news / mini_quiz / short_challenge siguen
 * existiendo en la sesión y en EngagePhase.tsx sin tocarse — son parte de
 * los siguientes momentos del Journey, aún no implementados. El Tutor IA
 * deliberadamente no aparece aquí.
 */
export function EntryGate({ session, moduleTitle, onComplete, onSkip, onProgress }: Props) {
  const [phase, setPhase] = useState<Phase>('silence')
  const [questionAnswered, setQuestionAnswered] = useState(false)
  const viewedDidYouKnow = useRef(false)

  const { mutate: interactMutate } = useInteractEngagement()
  const { mutate: completeMutate, isPending: isCompleting } = useCompleteEngagement()

  const didYouKnow  = session.resources.find(r => r.resource_type === 'did_you_know')
  const detonating  = session.resources.find(r => r.resource_type === 'detonating_question')

  // Defensive: if the backend didn't produce either resource, don't trap the student.
  useEffect(() => {
    if (!didYouKnow && !detonating) onComplete()
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    onProgress?.(phase === 'silence' ? 0 : phase === 'curiosity' ? 1 : 2)
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [phase])

  const goToCuriosity = useCallback(() => {
    if (!didYouKnow) { setPhase('question'); return }
    setPhase('curiosity')
  }, [didYouKnow])

  useEffect(() => {
    if (phase !== 'curiosity' || !didYouKnow || viewedDidYouKnow.current) return
    viewedDidYouKnow.current = true
    interactMutate({
      session_id:         session.session_id,
      resource_id:        didYouKnow.id,
      interaction_type:   'view',
      time_spent_seconds: 0,
    })
  }, [phase, didYouKnow, session.session_id, interactMutate])

  const finish = useCallback(() => {
    completeMutate(
      { session_id: session.session_id, skipped: false },
      { onSuccess: onComplete, onError: onComplete },
    )
  }, [session.session_id, completeMutate, onComplete])

  const goToQuestion = useCallback(() => {
    if (!detonating) { finish(); return }
    setPhase('question')
  }, [detonating, finish])

  const handleSkip = useCallback(() => {
    completeMutate(
      { session_id: session.session_id, skipped: true },
      { onSuccess: onSkip, onError: onSkip },
    )
  }, [session.session_id, completeMutate, onSkip])

  return (
    <div className="max-w-2xl mx-auto py-6 px-4 space-y-6">
      {phase === 'silence' && (
        <SilenceScreen moduleTitle={moduleTitle} onDone={goToCuriosity} />
      )}

      {phase === 'curiosity' && didYouKnow && (
        <div className="space-y-5 animate-in fade-in duration-500">
          <p className="text-xs font-mono text-neural-muted/40 uppercase tracking-widest text-center">
            Antes de comenzar
          </p>
          <DidYouKnowCard resource={didYouKnow} />
          <div className="flex justify-center">
            <Button onClick={goToQuestion} className="gap-2">
              Continuar
              <ArrowRight className="h-4 w-4" />
            </Button>
          </div>
        </div>
      )}

      {phase === 'question' && detonating && (
        <div className="space-y-5 animate-in fade-in duration-500">
          <DetonatingQuestionCard
            resource={detonating}
            sessionId={session.session_id}
            onSubmitted={() => setQuestionAnswered(true)}
          />
          <div className="flex items-center justify-center gap-3">
            <Button
              onClick={finish}
              disabled={!questionAnswered || isCompleting}
              title={!questionAnswered ? 'Registra tu hipótesis para continuar' : undefined}
              className="gap-2"
            >
              Empezar la misión
              <ArrowRight className="h-4 w-4" />
            </Button>
          </div>
        </div>
      )}

      <div className="flex justify-center">
        <Button
          variant="ghost"
          size="sm"
          className="text-muted-foreground gap-1 text-xs"
          onClick={handleSkip}
          disabled={isCompleting}
        >
          <SkipForward className="h-3.5 w-3.5" />
          Saltar
        </Button>
      </div>
    </div>
  )
}
