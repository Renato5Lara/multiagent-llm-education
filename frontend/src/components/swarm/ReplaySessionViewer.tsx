import { ArrowLeft, Eye } from 'lucide-react'
import { useState } from 'react'
import { Button } from '@/components/ui/button'
import type { ReplaySession } from '@/types/replay'

interface ReplaySessionViewerProps {
  replay: ReplaySession
  onBack: () => void
}

export function ReplaySessionViewer({ replay, onBack }: ReplaySessionViewerProps) {
  const [expandedWeek, setExpandedWeek] = useState<number | null>(null)

  return (
    <section className="rounded-lg border bg-white">
      <div className="flex items-center justify-between border-b px-4 py-3">
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="sm" onClick={onBack}>
            <ArrowLeft className="mr-1 h-4 w-4" /> Back
          </Button>
          <h2 className="text-base font-semibold text-slate-950">
            Session: {replay.student_id}
          </h2>
        </div>
        <span className="text-xs text-slate-500">{replay.total_weeks} weeks</span>
      </div>

      <div className="divide-y">
        {replay.steps.map((step) => (
          <div key={step.week_number}>
            <button
              type="button"
              onClick={() => setExpandedWeek(expandedWeek === step.week_number ? null : step.week_number)}
              className="flex w-full items-center justify-between px-4 py-3 text-left transition hover:bg-slate-50"
            >
              <div className="flex items-center gap-3">
                <Eye className="h-4 w-4 text-slate-400" />
                <span className="text-sm font-medium text-slate-900">Week {step.week_number}</span>
              </div>
              <div className="flex items-center gap-4 text-xs text-slate-500">
                <span>Bloom {step.adaptation.bloom.current}</span>
                <span>{step.adaptation.consensus.decision}</span>
                <span>{step.memory.total_records} records</span>
              </div>
            </button>

            {expandedWeek === step.week_number && (
              <div className="grid gap-4 px-4 pb-4 sm:grid-cols-2">
                <div className="rounded-md bg-slate-50 p-3">
                  <p className="text-xs font-medium text-slate-500">Bloom</p>
                  <p className="text-sm font-semibold text-slate-900">
                    {step.adaptation.bloom.previous ?? '?'} → {step.adaptation.bloom.current}
                    <span className="ml-2 text-xs text-slate-400">({step.adaptation.bloom.direction})</span>
                  </p>
                </div>
                <div className="rounded-md bg-slate-50 p-3">
                  <p className="text-xs font-medium text-slate-500">Consensus</p>
                  <p className="text-sm font-semibold text-slate-900">{step.adaptation.consensus.decision}</p>
                  <p className="text-xs text-slate-400">Confidence: {Math.round(step.adaptation.consensus.confidence * 100)}%</p>
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
    </section>
  )
}
