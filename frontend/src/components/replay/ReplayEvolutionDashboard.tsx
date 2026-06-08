import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'

interface EvolutionMetric {
  name: string
  current: string | number
  previous?: string | number
  delta?: string
  trend?: 'up' | 'down' | 'stable'
}

interface EvolutionPanelProps {
  title: string
  metrics: EvolutionMetric[]
  loading?: boolean
}

function TrendIcon({ trend }: { trend?: 'up' | 'down' | 'stable' }) {
  if (trend === 'up') return <span className="text-green-400 text-xs ml-1">↑</span>
  if (trend === 'down') return <span className="text-red-400 text-xs ml-1">↓</span>
  return <span className="text-gray-400 text-xs ml-1">→</span>
}

export function ReplayEvolutionDashboard({ title, metrics, loading }: EvolutionPanelProps) {
  return (
    <Card className="bg-slate-900 border-slate-700">
      <CardHeader>
        <CardTitle className="text-cyan-300 text-sm flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse" />
          {title}
        </CardTitle>
      </CardHeader>
      <CardContent>
        {loading ? (
          <div className="space-y-2">
            {[...Array(4)].map((_, i) => (
              <Skeleton key={i} className="h-6 bg-slate-800" />
            ))}
          </div>
        ) : (
          <div className="space-y-2">
            {metrics.map((m, i) => (
              <div key={i} className="flex items-center justify-between py-1 border-b border-slate-800 last:border-0">
                <span className="text-slate-400 text-xs">{m.name}</span>
                <div className="flex items-center gap-2">
                  <span className="text-white text-sm font-mono">{m.current}</span>
                  <TrendIcon trend={m.trend} />
                  {m.delta && (
                    <Badge variant="outline" className="text-[10px] bg-slate-800 text-slate-300 border-slate-600">
                      {m.delta}
                    </Badge>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
