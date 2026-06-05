import type { TrustRecord } from '@/types/swarmDemo'

interface TrustEvolutionProps {
  trust: Record<string, TrustRecord>
}

export function TrustEvolution({ trust }: TrustEvolutionProps) {
  const rows = Object.values(trust).sort((a, b) => a.voter_name.localeCompare(b.voter_name))

  return (
    <section className="rounded-lg border bg-white">
      <div className="border-b px-4 py-3">
        <h2 className="text-base font-semibold text-slate-950">Trust Evolution</h2>
      </div>
      <div className="space-y-3 p-4">
        {rows.length === 0 ? (
          <div className="rounded-md border border-dashed p-6 text-sm text-slate-500">
            Trust se actualizara despues de cada voto.
          </div>
        ) : (
          rows.map((record) => (
            <div key={record.voter_name} className="grid gap-2 rounded-md border bg-slate-50 p-3">
              <div className="flex items-center justify-between gap-3">
                <span className="text-sm font-semibold text-slate-950">{record.voter_name}</span>
                <span className="text-sm text-slate-600">{(record.trust_score * 100).toFixed(0)}%</span>
              </div>
              <div className="h-3 overflow-hidden rounded-full bg-white">
                <div
                  className="h-full rounded-full bg-primary transition-all"
                  style={{ width: `${Math.max(4, record.trust_score * 100)}%` }}
                />
              </div>
              <div className="grid grid-cols-3 gap-2 text-xs text-slate-600">
                <span>Accuracy {Math.round(record.accuracy * 100)}%</span>
                <span>Votes {record.total_votes}</span>
                <span>Latency {Math.round(record.avg_latency_ms)}ms</span>
              </div>
            </div>
          ))
        )}
      </div>
    </section>
  )
}

