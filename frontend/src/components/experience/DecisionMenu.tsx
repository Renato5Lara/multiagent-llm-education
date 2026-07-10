// Momento de Decisión — autonomía con barandas.
// Aparece tras la práctica: el estudiante elige cómo reforzar (o continuar).
// Con dominio alto se sugiere continuar; con dominio bajo el menú no se
// muestra (la remediación decide, no el estudiante). Cada elección es
// evidencia: preferencia revelada vs perfil declarado.

import { Check, Sparkles } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { DecisionMenuDef, ReinforcementKind } from '@/types/moduleExperience'

export type DecisionChoice = ReinforcementKind | 'continuar'

interface Props {
  menu: DecisionMenuDef
  /** Dominio actual del concepto (0-1) — define la baranda. */
  mastery: number
  /** Refuerzos ya explorados en este ciclo (PED-005): el menú se re-visita
   *  tras cada refuerzo, marcando lo visto — elegir nunca es un callejón. */
  visited?: ReadonlySet<ReinforcementKind>
  onChoose: (choice: DecisionChoice) => void
}

export function DecisionMenu({ menu, mastery, visited, onChoose }: Props) {
  const suggestContinue = mastery >= 0.75
  const revisit = (visited?.size ?? 0) > 0

  return (
    <div className="glass-panel rounded-2xl p-6 space-y-4 animate-in fade-in slide-in-from-bottom-2 duration-500">

      <div className="flex items-center gap-2.5">
        <Sparkles className="h-4 w-4 text-neural-violet shrink-0" />
        <p className="text-sm font-medium text-neural-text leading-snug">
          {revisit ? '¿Quieres reforzarlo de otra forma, o continuamos?' : menu.question}
        </p>
      </div>

      <div className="space-y-2">
        {menu.reinforcements.map(r => {
          const seen = visited?.has(r.kind) ?? false
          return (
            <button
              key={r.kind}
              type="button"
              onClick={() => onChoose(r.kind)}
              className={cn(
                'w-full text-left px-4 py-3 rounded-xl border text-sm transition-colors',
                'border-white/[0.08] bg-white/[0.02] hover:border-neural-violet/40 hover:bg-neural-violet/5 hover:text-neural-text',
                seen ? 'text-neural-muted/50' : 'text-neural-muted',
              )}
            >
              <span className="flex items-center justify-between gap-2">
                {r.label}
                {seen && (
                  <span className="inline-flex items-center gap-1 text-[10px] font-mono tracking-wide uppercase text-neural-glow/70 shrink-0">
                    <Check className="h-3 w-3" /> visto
                  </span>
                )}
              </span>
            </button>
          )
        })}

        <button
          type="button"
          onClick={() => onChoose('continuar')}
          className={cn(
            'w-full text-left px-4 py-3 rounded-xl border text-sm transition-colors',
            suggestContinue
              ? 'border-neural-glow/50 bg-neural-glow/10 text-neural-text hover:bg-neural-glow/15'
              : 'border-white/[0.08] bg-white/[0.02] text-neural-muted hover:border-white/20 hover:bg-white/[0.04] hover:text-neural-text',
          )}
        >
          Continuar
          {suggestContinue && (
            <span className="ml-2 text-[10px] font-mono tracking-wide uppercase text-neural-glow">
              · sugerido — ya dominas esto
            </span>
          )}
        </button>
      </div>

    </div>
  )
}
