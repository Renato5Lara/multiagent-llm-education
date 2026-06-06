import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

interface BloomData {
  step: number
  avgBloom: number
  maxBloom: number
  distribution: Record<string, number>
  sectionCount: number
}

interface BloomEvolutionProps {
  data: BloomData[]
  loading?: boolean
}

const BLOOM_LABELS: Record<string, string> = {
  '1': 'Recordar',
  '2': 'Comprender',
  '3': 'Aplicar',
  '4': 'Analizar',
  '5': 'Evaluar',
  '6': 'Crear',
}

const BLOOM_COLORS = ['#3b82f6', '#22c55e', '#eab308', '#f97316', '#ef4444', '#a855f7']

export function ReplayBloomEvolution({ data, loading }: BloomEvolutionProps) {
  const latest = data.length > 0 ? data[data.length - 1] : null
  const maxBarHeight = 120

  const barHeights = latest
    ? Object.entries(latest.distribution).map(([level, count]) => ({
        level: parseInt(level),
        count,
        height: Math.max(4, (count / Math.max(...Object.values(latest.distribution), 1)) * maxBarHeight),
        label: BLOOM_LABELS[level] || `Nivel ${level}`,
        color: BLOOM_COLORS[parseInt(level) - 1] || '#64748b',
      }))
    : []

  return (
    <Card className="bg-slate-900 border-slate-700">
      <CardHeader>
        <CardTitle className="text-cyan-300 text-sm">Evolución Bloom</CardTitle>
      </CardHeader>
      <CardContent>
        {loading ? (
          <div className="h-32 bg-slate-800 rounded animate-pulse" />
        ) : latest ? (
          <div>
            <div className="flex items-end gap-2 h-32 mb-2">
              {barHeights.map((b, i) => (
                <div key={i} className="flex-1 flex flex-col items-center gap-1">
                  <span className="text-[10px] text-slate-400">{b.count}</span>
                  <div
                    className="w-full rounded-t transition-all duration-500"
                    style={{
                      height: `${b.height}px`,
                      backgroundColor: b.color,
                      opacity: 0.8,
                    }}
                  />
                  <span className="text-[8px] text-slate-500 text-center leading-tight">
                    {b.label}
                  </span>
                </div>
              ))}
            </div>
            <div className="flex justify-between text-xs text-slate-400">
              <span>Promedio: <span className="text-white font-mono">{latest.avgBloom.toFixed(1)}</span></span>
              <span>Máximo: <span className="text-white font-mono">{latest.maxBloom}</span></span>
              <span>Secciones: <span className="text-white font-mono">{latest.sectionCount}</span></span>
            </div>
          </div>
        ) : (
          <p className="text-slate-500 text-xs italic h-32 flex items-center justify-center">
            Esperando datos de Bloom...
          </p>
        )}
      </CardContent>
    </Card>
  )
}
