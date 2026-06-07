import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'

interface ConsensusPoint {
  step: number
  decision: string
  confidence: number
  voterCount: number
  unanimous: boolean
}

interface ConsensusEvolutionProps {
  data: ConsensusPoint[]
  loading?: boolean
}

export function ReplayConsensusEvolution({ data, loading }: ConsensusEvolutionProps) {
  const latest = data.length > 0 ? data[data.length - 1] : null

  const confidenceColor = latest
    ? latest.confidence > 0.8 ? 'text-green-400'
      : latest.confidence > 0.6 ? 'text-amber-400'
      : 'text-red-400'
    : 'text-slate-400'

  return (
    <Card className="bg-slate-900 border-slate-700">
      <CardHeader>
        <CardTitle className="text-cyan-300 text-sm">Evolución de Consenso</CardTitle>
      </CardHeader>
      <CardContent>
        {loading ? (
          <div className="h-32 bg-slate-800 rounded animate-pulse" />
        ) : latest ? (
          <div>
            <div className="flex items-center justify-between mb-3">
              <div>
                <span className="text-slate-400 text-xs block">Decisión final</span>
                <Badge className={latest.unanimous ? 'bg-green-600' : 'bg-amber-600'}>
                  {latest.unanimous ? 'UNÁNIME' : 'MAYORÍA'}
                </Badge>
              </div>
              <div className="text-right">
                <span className="text-slate-400 text-xs block">Confianza</span>
                <span className={`text-lg font-mono font-bold ${confidenceColor}`}>
                  {(latest.confidence * 100).toFixed(0)}%
                </span>
              </div>
              <div className="text-right">
                <span className="text-slate-400 text-xs block">Votantes</span>
                <span className="text-white text-lg font-mono">{latest.voterCount}</span>
              </div>
            </div>

            <div className="space-y-1">
              <span className="text-slate-400 text-[10px]">Historial de confianza</span>
              <div className="flex items-end gap-1 h-16">
                {data.map((d, i) => {
                  const height = Math.max(4, d.confidence * 100)
                  const isLatest = i === data.length - 1
                  return (
                    <div
                      key={i}
                      className="flex-1 rounded-t transition-all duration-300"
                      style={{
                        height: `${height}px`,
                        background: isLatest
                          ? 'linear-gradient(to top, #06b6d4, #22d3ee)'
                          : d.confidence > 0.8
                            ? '#22c55e'
                            : d.confidence > 0.6
                              ? '#eab308'
                              : '#ef4444',
                        opacity: isLatest ? 1 : 0.5,
                      }}
                      title={`#${d.step}: ${(d.confidence * 100).toFixed(0)}%`}
                    />
                  )
                })}
              </div>
              <div className="flex justify-between text-[10px] text-slate-500">
                <span>#{data[0]?.step || 0}</span>
                <span>#{latest.step}</span>
              </div>
            </div>
          </div>
        ) : (
          <p className="text-slate-500 text-xs italic h-32 flex items-center justify-center">
            Esperando datos de consenso...
          </p>
        )}
      </CardContent>
    </Card>
  )
}
