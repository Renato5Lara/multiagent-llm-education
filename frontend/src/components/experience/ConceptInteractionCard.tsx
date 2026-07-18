// Predicción tocable dentro de la teoría (Sprint UX-01, jul 2026 — perfil
// kinestésico). El estudiante se compromete con una hipótesis ANTES de ver
// la explicación: las opciones son botones, y `reveal` solo aparece después
// de elegir. Misma mecánica que la apertura de curiosidad del módulo
// (predecir → comprobar), aplicada a escala de concepto — ningún concepto
// nuevo de dominio, solo la versión interactiva del texto que ya existía.

import { useState } from 'react'
import { CheckCircle2, MousePointerClick, XCircle } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { ConceptInteraction } from '@/types/moduleExperience'

interface Props {
  interaction: ConceptInteraction
  /** Posición 1-based mostrada en la etiqueta («Predicción 1»). */
  ordinal: number
  /** Se dispara UNA vez, al responder — el paso de teoría lo usa para
   *  habilitar el botón de continuar cuando todas están respondidas. */
  onAnswered: () => void
}

export function ConceptInteractionCard({ interaction, ordinal, onAnswered }: Props) {
  const [selected, setSelected] = useState<number | null>(null)
  const answered = selected !== null
  const correct = answered && selected === interaction.correctIndex

  const choose = (index: number) => {
    if (answered) return
    setSelected(index)
    onAnswered()
  }

  return (
    <div className="rounded-xl border border-white/[0.08] bg-neural-lowest/60 p-4 space-y-3">
      <div className="flex items-center gap-1.5">
        <MousePointerClick className="h-3.5 w-3.5 text-neural-glow shrink-0" />
        <p className="text-[10px] font-mono tracking-[0.15em] uppercase text-neural-glow">
          Predicción {ordinal} — elige antes de ver la respuesta
        </p>
      </div>

      <p className="text-sm md:text-base text-neural-text/90 leading-relaxed">{interaction.question}</p>

      <div className="space-y-2">
        {interaction.options.map((option, i) => {
          const isSelected = selected === i
          const revealCorrect = answered && i === interaction.correctIndex
          const revealWrong = answered && isSelected && i !== interaction.correctIndex
          return (
            <button
              key={i}
              type="button"
              onClick={() => choose(i)}
              disabled={answered}
              className={cn(
                'w-full text-left text-sm rounded-lg border px-3.5 py-2.5 transition-colors',
                !answered && 'border-white/10 text-neural-text/90 hover:border-neural-glow/40 hover:bg-white/[0.03]',
                revealCorrect && 'border-emerald-500/50 bg-emerald-500/10 text-emerald-200',
                revealWrong && 'border-amber-500/50 bg-amber-500/10 text-amber-200',
                answered && !revealCorrect && !revealWrong && 'border-white/[0.06] text-neural-muted/60',
              )}
            >
              <span className="inline-flex items-center gap-2">
                {revealCorrect && <CheckCircle2 className="h-4 w-4 shrink-0" />}
                {revealWrong && <XCircle className="h-4 w-4 shrink-0" />}
                {option}
              </span>
            </button>
          )
        })}
      </div>

      {answered && (
        <div className="animate-in fade-in slide-in-from-bottom-1 duration-300 rounded-lg border border-white/[0.06] bg-white/[0.02] px-3.5 py-3 space-y-1">
          <p className={cn('text-[11px] font-mono tracking-wide uppercase', correct ? 'text-emerald-400' : 'text-amber-400')}>
            {correct ? 'Tu predicción acertó' : 'Tu predicción falló — y eso también enseña'}
          </p>
          <p className="text-sm text-neural-text/90 leading-relaxed">{interaction.reveal}</p>
        </div>
      )}
    </div>
  )
}
