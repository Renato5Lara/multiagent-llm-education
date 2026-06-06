import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'

interface MemoryEvent {
  step: number
  operation: string
  key: string
  value: unknown
  narrative?: string
  coherence?: number
}

interface MemoryContinuityProps {
  events: MemoryEvent[]
  narrativeThread?: string
  coherenceScore?: number
}

export function ReplayMemoryContinuity({ events, narrativeThread, coherenceScore }: MemoryContinuityProps) {
  return (
    <Card className="bg-slate-900 border-slate-700">
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="text-cyan-300 text-sm">Continuidad Narrativa</CardTitle>
          {coherenceScore !== undefined && (
            <Badge
              className={`text-xs ${
                coherenceScore > 0.7 ? 'bg-green-600' : coherenceScore > 0.4 ? 'bg-amber-600' : 'bg-red-600'
              }`}
            >
              Coherencia: {(coherenceScore * 100).toFixed(0)}%
            </Badge>
          )}
        </div>
      </CardHeader>
      <CardContent>
        {narrativeThread && (
          <div className="mb-3 p-2 bg-slate-800 rounded border border-slate-600">
            <p className="text-slate-300 text-xs italic">"{narrativeThread}"</p>
          </div>
        )}
        <div className="space-y-2 max-h-64 overflow-y-auto">
          {events.length === 0 && (
            <p className="text-slate-500 text-xs italic">Sin eventos de memoria aún</p>
          )}
          {events.map((ev, i) => (
            <div key={i} className="flex items-start gap-2 text-xs">
              <span className="text-slate-600 font-mono w-6 shrink-0">#{ev.step}</span>
              <Badge variant="outline" className="text-[10px] bg-slate-800 text-slate-300 border-slate-600 shrink-0">
                {ev.operation}
              </Badge>
              <span className="text-slate-400 truncate">{ev.key}</span>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  )
}
