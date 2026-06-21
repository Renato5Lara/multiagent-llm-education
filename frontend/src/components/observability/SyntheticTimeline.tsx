import { PIPELINE_STEPS, TOTAL_ESTIMATED_MS } from '@/constants/agentPipeline'

interface Props {
  techMode: boolean
}

/**
 * SyntheticTimeline — always-available student-facing thought stream.
 *
 * Uses PIPELINE_STEPS constants (no API call needed).
 * Renders when GET /api/trace returns 404 or when the backend ran in
 * deterministic-template mode (no LLM API keys).
 *
 * Each step is visually identical to a real trace step so the transition
 * from Synthetic → Real is seamless once API keys are configured.
 */
export function SyntheticTimeline({ techMode }: Props) {
  const maxMs = Math.max(...PIPELINE_STEPS.map(s => s.estimatedMs))

  return (
    <div className="space-y-1">
      {PIPELINE_STEPS.map((step, i) => (
        <div
          key={step.technicalName}
          className="animate-in fade-in slide-in-from-left-2 fill-mode-both"
          style={{ animationDelay: `${i * 80}ms` }}
        >
          <div className="flex items-center gap-3 py-2.5 px-3 rounded-lg hover:bg-muted/40 transition-colors">

            {/* Icon circle */}
            <div className="w-8 h-8 rounded-full bg-primary/8 dark:bg-primary/10 flex items-center justify-center shrink-0 text-base select-none">
              {step.icon}
            </div>

            {/* Label + duration bar */}
            <div className="flex-1 min-w-0 space-y-1.5">
              <p className="text-sm leading-none">
                {techMode ? (
                  <span className="font-mono text-xs text-muted-foreground">{step.technicalName}</span>
                ) : (
                  <span className="font-medium text-foreground/80">{step.studentLabel}</span>
                )}
              </p>
              <div className="h-1 rounded-full bg-muted overflow-hidden">
                <div
                  className="h-full rounded-full bg-primary/30 dark:bg-primary/40 animate-in slide-in-from-left-4 fill-mode-both"
                  style={{
                    width: `${Math.round((step.estimatedMs / maxMs) * 100)}%`,
                    animationDelay: `${i * 80 + 200}ms`,
                  }}
                />
              </div>
            </div>

            {/* Duration */}
            <span className="text-xs text-muted-foreground shrink-0 tabular-nums">
              ✓ ~{(step.estimatedMs / 1000).toFixed(1)}s
            </span>
          </div>
        </div>
      ))}

      {/* Footer note */}
      <div className="pt-2 px-3 flex items-center justify-between">
        <p className="text-xs text-muted-foreground/60 italic">
          {techMode
            ? 'Tiempos estimados · trazas reales disponibles con LLM configurado'
            : 'Tiempos estimados basados en el pipeline de orquestación'}
        </p>
        <span className="text-xs text-muted-foreground/60 tabular-nums">
          ~{(TOTAL_ESTIMATED_MS / 1000).toFixed(0)}s total
        </span>
      </div>
    </div>
  )
}
