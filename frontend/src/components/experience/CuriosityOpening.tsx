// Apertura de curiosidad — la pregunta intrigante ANTES de revelar el tema.
// Pantalla casi vacía, una sola cosa en el centro. El nombre del módulo no
// aparece aquí: aparece en la revelación, cuando el estudiante ya quiere saber.

import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import type { CuriosityOpening as CuriosityOpeningDef } from '@/types/moduleExperience'

interface Props {
  opening: CuriosityOpeningDef
  onAnswer: (option: string, freeText: string) => void
}

export function CuriosityOpening({ opening, onAnswer }: Props) {
  const [selected, setSelected] = useState<string | null>(null)
  const [freeText, setFreeText] = useState('')

  return (
    <div className="flex flex-col items-center justify-center min-h-[70vh] px-4 animate-in fade-in duration-700">
      <div className="max-w-xl w-full space-y-8">

        <div className="space-y-3 text-center">
          {opening.questionLines.map((line, i) => (
            <p
              key={i}
              className={cn(
                'leading-snug',
                i === opening.questionLines.length - 1
                  ? 'text-2xl md:text-3xl font-bold text-neural-text mt-6'
                  : 'text-lg md:text-xl text-neural-muted',
              )}
            >
              {line}
            </p>
          ))}
        </div>

        <div className="space-y-2.5">
          {opening.options.map(option => {
            const isSelected = selected === option
            return (
              <button
                key={option}
                type="button"
                onClick={() => setSelected(option)}
                className={cn(
                  'w-full text-left px-5 py-3.5 rounded-xl border-2 transition-all duration-150 cursor-pointer',
                  isSelected
                    ? 'border-neural-glow bg-neural-glow/10 text-neural-text'
                    : 'border-white/[0.08] bg-white/[0.02] text-neural-muted hover:border-white/20 hover:bg-white/[0.04]',
                )}
              >
                <span className="text-sm font-medium">{option}</span>
              </button>
            )
          })}
        </div>

        {selected && opening.freeTextPrompt && (
          <div className="animate-in fade-in slide-in-from-top-2 duration-300">
            <input
              type="text"
              value={freeText}
              onChange={e => setFreeText(e.target.value)}
              placeholder={opening.freeTextPrompt}
              maxLength={140}
              className="w-full px-4 py-3 rounded-xl bg-white/[0.03] border border-white/[0.08] text-sm text-neural-text placeholder:text-neural-muted/50 focus:outline-none focus:border-neural-glow/50 transition-colors"
            />
          </div>
        )}

        {selected && (
          <div className="animate-in fade-in duration-300">
            <Button className="w-full gap-2" onClick={() => onAnswer(selected, freeText.trim())}>
              Ver la respuesta →
            </Button>
          </div>
        )}

      </div>
    </div>
  )
}
