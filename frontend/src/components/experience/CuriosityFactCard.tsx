// "¿Sabías que...?" — pantalla propia al inicio del ciclo (sprint "UX ¿Sabías
// que...?", jul 2026): antes aparecía mezclada arriba del concepto, dentro de
// la misma pantalla que la teoría; ahora es su propio paso — dato, fuente
// verificable y un "Continuar" explícito, antes de pasar al contenido
// principal. Misma identidad visual que tenía (glass, borde ámbar, ícono +
// etiqueta mono) y el mismo componente de siempre — solo con fuente y botón.

import { Lightbulb } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { useMinDwell } from '@/hooks/useMinDwell'
import type { CuriosityFact } from '@/types/moduleExperience'

interface Props {
  fact: CuriosityFact
  /** Cuando se omite, la tarjeta se comporta como antes del sprint (sin
   *  botón propio) — hoy siempre se pasa, porque "¿Sabías que...?" es su
   *  propia pantalla con su propio paso de avance. */
  onContinue?: () => void
}

// Auditoría "criterios de finalización reales" (jul 2026): "Continuar"
// estaba siempre habilitado — un clic instantáneo saltaba el dato y su
// fuente sin haberlos leído. Piso bajo, acorde al tamaño real del contenido.
const CURIOSITY_MIN_DWELL_MS = 2500

export function CuriosityFactCard({ fact, onContinue }: Props) {
  const dwellReady = useMinDwell(CURIOSITY_MIN_DWELL_MS)
  return (
    <div className="rounded-2xl border border-amber-400/25 bg-amber-400/[0.04] p-5 space-y-3 animate-in fade-in duration-500">
      <div className="flex items-center gap-2.5">
        <Lightbulb className="h-4 w-4 text-amber-300 shrink-0" />
        <p className="text-[11px] font-mono tracking-[0.2em] uppercase text-amber-300">
          ¿Sabías que...?
        </p>
      </div>
      <p className="text-sm md:text-base text-neural-text/90 leading-relaxed">
        {fact.fact}
      </p>
      <p className="text-sm text-neural-muted leading-relaxed border-t border-amber-400/15 pt-3">
        {fact.connection}
      </p>
      <p className="text-xs text-neural-muted/70 italic">
        Fuente: {fact.source}
      </p>
      {onContinue && (
        <div className="flex justify-end pt-1">
          <Button onClick={onContinue} disabled={!dwellReady} className="gap-2">
            Continuar →
          </Button>
        </div>
      )}
    </div>
  )
}
