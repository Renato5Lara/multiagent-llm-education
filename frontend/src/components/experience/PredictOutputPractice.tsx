// Práctica de "elegir respuestas" (multimodalidad profunda, jul 2026) — el
// estudiante lee código real y predice su salida, en vez de arrastrar u
// ordenar. Simula mentalmente la ejecución: una mecánica de interacción
// genuinamente distinta a OrderingPractice, no el mismo ejercicio con otro
// disfraz. Mismo contrato de salida (PracticeOutcome) para componer con la
// evidencia y el dominio ya existentes sin tocar esa maquinaria.
import { useMemo, useRef, useState } from 'react'
import { CheckCircle2, GraduationCap, XCircle } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import { AudioNarration } from './AudioNarration'
import { resolveNarrationAudio } from '@/lib/experiences/audioAssets'
import type { PredictOutputPracticeDef } from '@/types/moduleExperience'
import type { PracticeOutcome } from './OrderingPractice'

interface Props {
  practice: PredictOutputPracticeDef
  onAttempt?: (info: { attempt: number; correct: boolean }) => void
  /** Se dispara al resolver o al mostrar la solución (nunca-bloquear). */
  onFinished: (outcome: PracticeOutcome) => void
  /** Mismo contrato que OrderingPractice: quién decide revelar la solución
   *  al agotar los intentos. true (default) — la actividad la revela. false
   *  — cede el control a la escalera vía onExhausted, sin mostrar nada aquí. */
  revealOnExhaust?: boolean
  /** Intentos agotados sin resolver y sin revelar (revealOnExhaust=false). */
  onExhausted?: (outcome: PracticeOutcome) => void
  /** Mismo criterio "earlyHelp" que PythonBridge/OrderingPractice: fundamentos
   *  adelanta el apoyo (ve la solución explicada un intento antes). Solo se
   *  usa cuando el llamador la pasa explícitamente. */
  profundidad?: string
}

const DEFAULT_MAX_ATTEMPTS_BEFORE_SOLUTION = 2

function maxAttemptsFor(profundidad: string | undefined): number {
  if (profundidad === 'fundamentos') return DEFAULT_MAX_ATTEMPTS_BEFORE_SOLUTION - 1
  return DEFAULT_MAX_ATTEMPTS_BEFORE_SOLUTION
}

export function PredictOutputPractice({ practice, onAttempt, onFinished, revealOnExhaust = true, onExhausted, profundidad }: Props) {
  const [selected, setSelected] = useState<string | null>(null)
  const [attempts, setAttempts] = useState(0)
  const maxAttempts = useMemo(() => maxAttemptsFor(profundidad), [profundidad])
  const [status, setStatus] = useState<'idle' | 'wrong' | 'correct' | 'exhausted'>('idle')
  const startRef = useRef<number>(Date.now())
  const finishedRef = useRef(false)

  const finish = (solutionShown: boolean) => {
    if (finishedRef.current) return
    finishedRef.current = true
    onFinished({ attempts, timeMs: Date.now() - startRef.current, solutionShown })
  }

  const handleCheck = () => {
    if (!selected || status === 'correct' || status === 'exhausted') return
    const nextAttempts = attempts + 1
    setAttempts(nextAttempts)
    const correct = selected === practice.correctOptionId
    onAttempt?.({ attempt: nextAttempts, correct })

    if (correct) {
      setStatus('correct')
      finish(false)
      return
    }
    if (nextAttempts >= maxAttempts) {
      if (!revealOnExhaust) {
        finishedRef.current = true
        onExhausted?.({ attempts: nextAttempts, timeMs: Date.now() - startRef.current, solutionShown: false })
        return
      }
      setStatus('exhausted')
      finish(true)
      return
    }
    setStatus('wrong')
  }

  const disabled = status === 'correct' || status === 'exhausted'

  return (
    <div className="space-y-4">
      <p className="text-sm text-neural-text/90">{practice.prompt}</p>
      {/* Auditoría "diversidad pedagógica" (jul 2026, revisión post-sprint):
          antes, el enunciado auditivo podía decir "después de escuchar..."
          sin reproducir nada — mismo componente ya usado por la teoría
          (AudioNarration, síntesis de voz real del navegador), nunca un
          componente nuevo. Ausente para lector/visual/kinestésico —
          comportamiento previo intacto. */}
      {practice.narrationText && (
        <AudioNarration text={practice.narrationText} audioSrc={resolveNarrationAudio(practice)} />
      )}
      <pre className="rounded-lg bg-black/30 border border-white/10 p-3 text-[13px] font-mono text-neural-text overflow-x-auto">
        {practice.code}
      </pre>
      <div className="space-y-2">
        {practice.options.map(option => {
          const isSelected = selected === option.id
          const revealCorrect = disabled && option.id === practice.correctOptionId
          const revealWrong = disabled && isSelected && option.id !== practice.correctOptionId
          return (
            <button
              key={option.id}
              type="button"
              disabled={disabled}
              onClick={() => setSelected(option.id)}
              className={cn(
                'w-full text-left rounded-lg border px-3 py-2 text-sm font-mono transition-colors',
                isSelected && !disabled && 'border-neural-glow bg-neural-glow/10 text-neural-text',
                !isSelected && !disabled && 'border-white/10 text-neural-text/80 hover:border-white/20',
                revealCorrect && 'border-neural-pulse bg-neural-pulse/10 text-neural-text',
                revealWrong && 'border-red-400/50 bg-red-400/10 text-neural-text/70',
              )}
            >
              {option.text}
            </button>
          )
        })}
      </div>

      {status === 'idle' || status === 'wrong' ? (
        <div className="flex items-center justify-between">
          {status === 'wrong' && (
            <p className="text-xs text-red-300/80 flex items-center gap-1.5">
              <XCircle className="h-3.5 w-3.5 shrink-0" /> {practice.wrongFeedback}
            </p>
          )}
          <Button onClick={handleCheck} disabled={!selected} className="gap-2 ml-auto">
            Comprobar
          </Button>
        </div>
      ) : null}

      {status === 'correct' && (
        <p className="text-sm text-neural-pulse flex items-center gap-1.5">
          <CheckCircle2 className="h-4 w-4 shrink-0" /> {practice.successFeedback}
        </p>
      )}

      {status === 'exhausted' && (
        <div className="rounded-lg border border-neural-violet/30 bg-neural-violet/[0.06] p-3 space-y-2">
          <p className="text-xs text-neural-violet flex items-center gap-1.5">
            <GraduationCap className="h-3.5 w-3.5 shrink-0" /> Vamos paso a paso:
          </p>
          {practice.solutionExplanation.map((line, i) => (
            <p key={i} className="text-sm text-neural-text/85 leading-relaxed">{line}</p>
          ))}
        </div>
      )}
    </div>
  )
}
