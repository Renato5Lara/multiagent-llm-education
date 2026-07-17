// Observabilidad Pedagógica (orden del usuario, 2026-07-15): un gráfico de
// líneas por agente — no "actividad" sin significado, sino la confianza REAL
// de cada claim que ese agente autoró, en el tiempo (eje X = transición del
// Runtime). Más el consenso: la confianza real de cada decisión derivada.
// Nunca tablas técnicas ni logs — visualizaciones, con el mismo criterio que
// ya rechaza "Agente X ejecutado / latency / JSON / prompt / tokens".
import { CAPACIDAD_LABEL } from '@/hooks/useLiveDeliberation'
import type { AgentSeries, SeriesPoint } from '@/hooks/useEvidence'
import { LineSeriesChart } from './LineSeriesChart'

const AGENT_COLOR: Record<string, string> = {
  diagnosticar: '#06b6d4',
  orientar: '#22d3ee',
  adaptar: '#8b5cf6',
  tutorizar: '#fb923c',
  evaluar: '#34d399',
  remediar: '#fbbf24',
  validar: '#2dd4bf',
  modelar: '#f472b6',
}

function toChartPoints(puntos: SeriesPoint[]) {
  return puntos.map(p => ({ x: p.transicion, y: p.confianza, label: `${p.asunto} — ${(p.confianza * 100).toFixed(0)}%` }))
}

interface Props {
  agentSeries: AgentSeries[]
  consensusSeries: SeriesPoint[]
}

export function AgentSeriesCharts({ agentSeries, consensusSeries }: Props) {
  if (agentSeries.length === 0 && consensusSeries.length === 0) {
    return (
      <p className="text-sm text-neural-muted/60 text-center py-6">
        Todavía no hay suficientes decisiones registradas para graficar la evolución de los agentes.
      </p>
    )
  }

  return (
    <div className="grid md:grid-cols-2 gap-4">
      {agentSeries.map(series => (
        <div key={series.agente} className="rounded-xl border border-white/10 bg-white/[0.02] p-4">
          <p className="text-xs font-mono text-neural-glow/70 uppercase tracking-wide mb-1">
            {CAPACIDAD_LABEL[series.agente] ?? `Agente ${series.agente}`}
          </p>
          <p className="text-[11px] text-neural-muted/50 mb-2">Confianza de sus decisiones en el tiempo</p>
          <LineSeriesChart points={toChartPoints(series.puntos)} color={AGENT_COLOR[series.agente] ?? '#06b6d4'} />
        </div>
      ))}
      {consensusSeries.length > 0 && (
        <div className="rounded-xl border border-neural-pulse/20 bg-neural-pulse/[0.04] p-4">
          <p className="text-xs font-mono text-neural-pulse/80 uppercase tracking-wide mb-1">
            Motor de Consenso
          </p>
          <p className="text-[11px] text-neural-muted/50 mb-2">Confianza de cada decisión alcanzada</p>
          <LineSeriesChart points={toChartPoints(consensusSeries)} color="#f0abfc" />
        </div>
      )}
    </div>
  )
}
