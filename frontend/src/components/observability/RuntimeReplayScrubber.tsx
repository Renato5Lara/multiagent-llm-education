import { useState } from 'react'
import { ChevronLeft, ChevronRight, Inbox } from 'lucide-react'
import { RuntimeEstadoView } from '@/components/observability/RuntimeEstadoView'
import type { RuntimePasoReplay } from '@/hooks/useRuntimeReplay'

interface RuntimeReplayScrubberProps {
  pasos: RuntimePasoReplay[]
}

// Recorre el estado acumulado transición por transición (RFC-0008 §3,
// modo Reconstrucción) — no un componente de renderizado nuevo: cada
// posición del scrubber reutiliza RuntimeEstadoView tal cual.
export function RuntimeReplayScrubber({ pasos }: RuntimeReplayScrubberProps) {
  const [indice, setIndice] = useState(0)

  if (pasos.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center rounded-lg border border-dashed border-slate-200 bg-slate-50 py-10 text-center">
        <Inbox className="mx-auto mb-2 h-8 w-8 text-slate-300" />
        <p className="text-sm font-medium text-slate-500">Sin transiciones para reproducir.</p>
      </div>
    )
  }

  const paso = pasos[Math.min(indice, pasos.length - 1)]

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={() => setIndice((i) => Math.max(0, i - 1))}
          disabled={indice === 0}
          className="shrink-0 rounded p-1 text-slate-400 transition-colors hover:bg-slate-100 hover:text-slate-600 disabled:pointer-events-none disabled:opacity-30"
        >
          <ChevronLeft className="h-4 w-4" />
        </button>
        <input
          type="range"
          min={0}
          max={pasos.length - 1}
          value={indice}
          onChange={(e) => setIndice(Number(e.target.value))}
          className="w-full"
        />
        <button
          type="button"
          onClick={() => setIndice((i) => Math.min(pasos.length - 1, i + 1))}
          disabled={indice === pasos.length - 1}
          className="shrink-0 rounded p-1 text-slate-400 transition-colors hover:bg-slate-100 hover:text-slate-600 disabled:pointer-events-none disabled:opacity-30"
        >
          <ChevronRight className="h-4 w-4" />
        </button>
        <span className="shrink-0 font-mono text-xs text-slate-500">
          T-{paso.transicion} · {indice + 1}/{pasos.length}
        </span>
      </div>
      <RuntimeEstadoView estado={paso.estado} />
    </div>
  )
}
