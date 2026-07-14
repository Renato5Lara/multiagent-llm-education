// "¿Sabías que...?" — recuperada del flujo legacy (EngageGateway) pero con la
// identidad visual del patrón de experiencia (oscuro, glass-panel), no la
// tarjeta clara original. Rompe la monotonía teoría→práctica antes de que
// empiece el concepto.

import { Lightbulb } from 'lucide-react'
import type { CuriosityFact } from '@/types/moduleExperience'

export function CuriosityFactCard({ fact }: { fact: CuriosityFact }) {
  return (
    <div className="rounded-2xl border border-amber-400/25 bg-amber-400/[0.04] p-5 space-y-2.5 animate-in fade-in duration-500">
      <div className="flex items-center gap-2.5">
        <Lightbulb className="h-4 w-4 text-amber-300 shrink-0" />
        <p className="text-[11px] font-mono tracking-[0.2em] uppercase text-amber-300">
          ¿Sabías que...?
        </p>
      </div>
      <p className="text-sm md:text-base text-neural-text/90 leading-relaxed">
        {fact.fact}
      </p>
      <p className="text-xs text-neural-muted leading-relaxed border-t border-amber-400/15 pt-2.5">
        {fact.connection}
      </p>
    </div>
  )
}
