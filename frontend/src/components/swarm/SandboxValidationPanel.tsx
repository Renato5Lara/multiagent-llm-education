import { ShieldCheck, TerminalSquare } from 'lucide-react'
import type { DemoEvent, SandboxValidationPayload } from '@/types/swarmDemo'

interface SandboxValidationPanelProps {
  events: DemoEvent[]
}

export function SandboxValidationPanel({ events }: SandboxValidationPanelProps) {
  const started = [...events].reverse().find((event) => event.type === 'sandbox:start')?.payload as SandboxValidationPayload | undefined
  const completed = [...events].reverse().find((event) => event.type === 'sandbox:complete')?.payload as SandboxValidationPayload | undefined
  const status = completed?.status ?? (started ? 'running' : 'waiting')
  const result = completed?.sandbox_result
  const confidence = Math.round((completed?.confidence ?? 0) * 100)

  return (
    <section className="rounded-lg border bg-white">
      <div className="flex items-center justify-between border-b px-4 py-3">
        <div className="flex items-center gap-2">
          <ShieldCheck className="h-4 w-4 text-primary" />
          <h2 className="text-base font-semibold text-slate-950">Python REPL Sandbox</h2>
        </div>
        <span className="rounded-md bg-slate-100 px-2 py-1 text-xs font-semibold text-slate-700">{status}</span>
      </div>
      <div className="grid gap-3 p-4 md:grid-cols-3">
        <Metric label="Timeout" value={`${started?.limits?.timeout_seconds ?? 10}s`} />
        <Metric label="Memoria" value={`${started?.limits?.memory_mb ?? 512}MB`} />
        <Metric label="Confianza" value={completed ? `${confidence}%` : 'pendiente'} />
      </div>
      <div className="space-y-3 px-4 pb-4">
        <p className="text-sm text-slate-700">
          {completed?.final_feedback ?? 'ReviewerAgent ejecutara el codigo educativo en un contenedor aislado antes de pasarlo al sistema pedagogico.'}
        </p>
        {result && (
          <div className="grid gap-2 text-xs text-slate-600 sm:grid-cols-3">
            <span className="rounded-md bg-slate-50 p-2">Tiempo: {Math.round(Number(result.execution_time_ms ?? 0))}ms</span>
            <span className="rounded-md bg-slate-50 p-2">RAM: {Number(result.memory_usage_mb ?? 0).toFixed(1)}MB</span>
            <span className="rounded-md bg-slate-50 p-2">Iteraciones: {completed?.iterations ?? 0}/4</span>
          </div>
        )}
        {completed?.code_preview && (
          <pre className="max-h-44 overflow-auto rounded-md bg-slate-950 p-3 text-xs text-slate-100">
            <TerminalSquare className="mb-2 h-4 w-4 text-emerald-300" />
            {completed.code_preview}
          </pre>
        )}
      </div>
    </section>
  )
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border bg-slate-50 p-3">
      <p className="text-xs font-medium uppercase text-slate-500">{label}</p>
      <p className="mt-1 text-sm font-semibold text-slate-950">{value}</p>
    </div>
  )
}
