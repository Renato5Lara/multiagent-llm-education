import { Inbox } from 'lucide-react'
import type { RuntimeMemoria } from '@/hooks/useRuntimeMemoria'

interface RuntimeMemoriaViewProps {
  memoria: RuntimeMemoria | null
}

export function RuntimeMemoriaView({ memoria }: RuntimeMemoriaViewProps) {
  if (memoria === null) {
    return (
      <div className="flex flex-col items-center justify-center rounded-lg border border-dashed border-slate-200 bg-slate-50 py-10 text-center">
        <Inbox className="mx-auto mb-2 h-8 w-8 text-slate-300" />
        <p className="text-sm font-medium text-slate-500">Sin memoria consolidada.</p>
        <p className="mt-1 text-xs text-slate-400">
          RFC-0005 §1.1 — el estudiante todavía no cerró ninguna sesión previa.
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap gap-x-6 gap-y-1 text-xs text-muted-foreground">
        <span>
          estudiante: <span className="font-mono text-slate-600">{memoria.student_id}</span>
        </span>
        <span>
          consolidada por sesión:{' '}
          <span className="font-mono text-slate-600">{memoria.session_id}</span>
        </span>
      </div>
      <pre className="overflow-x-auto rounded-md bg-slate-900 p-3 text-[11px] leading-relaxed text-slate-100">
        <code>{JSON.stringify(memoria.catalogo, null, 2)}</code>
      </pre>
    </div>
  )
}
