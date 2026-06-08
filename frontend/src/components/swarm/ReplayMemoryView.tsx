import { Database } from 'lucide-react'
import type { MemorySnapshot } from '@/types/replay'

interface ReplayMemoryViewProps {
  snapshot: MemorySnapshot
}

export function ReplayMemoryView({ snapshot }: ReplayMemoryViewProps) {
  const groups = Object.entries(snapshot.grouped || {})

  return (
    <section className="rounded-lg border bg-white">
      <div className="flex items-center justify-between border-b px-4 py-3">
        <div className="flex items-center gap-2">
          <Database className="h-4 w-4 text-slate-500" />
          <h3 className="text-sm font-semibold text-slate-900">Memory Replay</h3>
        </div>
        <span className="text-xs text-slate-500">{snapshot.total_records} records</span>
      </div>
      <div className="grid gap-3 p-4">
        {groups.length === 0 ? (
          <p className="text-sm text-slate-500">No memory records for this step.</p>
        ) : groups.map(([type, records]) => (
          <div key={type} className="rounded-md border bg-slate-50 p-3">
            <p className="text-xs font-semibold uppercase text-slate-500">{type}</p>
            <div className="mt-2 grid gap-2">
              {records.slice(0, 5).map((record) => (
                <div key={record.id} className="rounded bg-white p-2 text-xs">
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-medium text-slate-800">{record.key}</span>
                    <span className="text-slate-400">{Math.round(record.confidence * 100)}%</span>
                  </div>
                  <p className="mt-1 truncate text-slate-500">{JSON.stringify(record.value)}</p>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </section>
  )
}
