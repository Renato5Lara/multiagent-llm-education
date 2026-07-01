import { useEffect, useRef } from 'react'
import { getTopicSymbol } from '@/lib/topicSymbols'

interface Props {
  moduleTitle?: string
  /** ms before auto-advancing to Fase B. Spec: ~3s. */
  durationMs?: number
  onDone: () => void
}

/**
 * SilenceScreen — Fase A ("Silencio Visual") of Momento 1, "La Puerta de Entrada".
 *
 * Purely atmospheric: no content, no Tutor IA, no Learning Journey. Shows only
 * a symbol related to the module to build expectation before Fase B (dato
 * curioso). Auto-advances after `durationMs`; a subtle skip link keeps the
 * student from ever being blocked (same safety-valve pattern as EngagePhase).
 */
export function SilenceScreen({ moduleTitle, durationMs = 3000, onDone }: Props) {
  const { Icon, label } = getTopicSymbol(moduleTitle)
  const timerRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined)

  useEffect(() => {
    timerRef.current = setTimeout(onDone, durationMs)
    return () => clearTimeout(timerRef.current)
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  return (
    <div className="min-h-[420px] flex flex-col items-center justify-center gap-4 animate-in fade-in duration-700">
      <div className="relative flex items-center justify-center">
        <span className="absolute inline-flex h-24 w-24 rounded-full bg-neural-glow/10 animate-ping" />
        <span className="absolute inline-flex h-24 w-24 rounded-full border border-neural-glow/20" />
        <div className="relative h-24 w-24 rounded-full glass-panel flex items-center justify-center">
          <Icon className="h-9 w-9 text-neural-glow/80" strokeWidth={1.5} />
        </div>
      </div>
      <p className="text-xs font-mono text-neural-muted/40 tracking-[0.2em] uppercase">
        {label}
      </p>

      <button
        type="button"
        onClick={onDone}
        className="mt-6 text-[11px] text-neural-muted/30 hover:text-neural-muted/60 transition-colors"
      >
        Continuar
      </button>
    </div>
  )
}
