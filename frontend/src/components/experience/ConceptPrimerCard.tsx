// Microexplicación de un término de Python — se muestra ANTES de que el
// ciclo lo use por primera vez (sprint "mejora pedagógica", jul 2026). Misma
// identidad visual que CuriosityFactCard (glass, borde de color, ícono +
// etiqueta mono), pero con su propio acento (neural-glow) para no confundirse
// con "¿Sabías que...?". Nombre → qué es → para qué sirve → ejemplo →
// continuar: nada más. Dura menos de un minuto a propósito, no es una lección.

import { Sparkles } from 'lucide-react'
import { Button } from '@/components/ui/button'
import type { ConceptPrimer } from '@/types/moduleExperience'

interface Props {
  primer: ConceptPrimer
  onContinue: () => void
}

export function ConceptPrimerCard({ primer, onContinue }: Props) {
  return (
    <div className="rounded-2xl border border-neural-glow/25 bg-neural-glow/[0.04] p-5 space-y-4 animate-in fade-in duration-500">
      <div className="flex items-center gap-2.5">
        <Sparkles className="h-4 w-4 text-neural-glow shrink-0" />
        <p className="text-[11px] font-mono tracking-[0.2em] uppercase text-neural-glow">
          ¿Qué es {primer.term}?
        </p>
      </div>

      <p className="text-sm md:text-base text-neural-text/90 leading-relaxed">
        {primer.whatIsIt}
      </p>
      <p className="text-sm text-neural-muted leading-relaxed">
        {primer.whatFor}
      </p>

      <div className="rounded-xl border border-white/[0.08] bg-black/30 overflow-hidden">
        <pre className="px-4 py-3 overflow-x-auto text-[13px] leading-relaxed font-mono text-neural-text/90 whitespace-pre">
          <code>{primer.example.code}</code>
        </pre>
        <div className="border-t border-white/[0.06] px-4 py-2 font-mono text-[12px] text-neural-glow/80">
          → {primer.example.result}
        </div>
      </div>

      <div className="flex justify-end">
        <Button onClick={onContinue} className="gap-2">
          Ahora úsalo →
        </Button>
      </div>
    </div>
  )
}
