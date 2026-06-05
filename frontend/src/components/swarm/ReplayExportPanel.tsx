import { Download } from 'lucide-react'
import { Button } from '@/components/ui/button'
import type { ReplayExportFormat, ReplaySession } from '@/types/replay'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'

interface ReplayExportPanelProps {
  studentId: string
  replay: ReplaySession
}

export function ReplayExportPanel({ studentId, replay }: ReplayExportPanelProps) {
  const formats: ReplayExportFormat[] = ['json', 'csv', 'markdown', 'latex']

  return (
    <section className="rounded-lg border bg-white">
      <div className="border-b px-4 py-3">
        <h3 className="text-sm font-semibold text-slate-900">Export Replay</h3>
        <p className="mt-1 text-xs text-slate-500">{replay.total_weeks} weeks available for academic evidence.</p>
      </div>
      <div className="flex flex-wrap gap-2 p-4">
        {formats.map((format) => (
          <Button key={format} asChild variant="outline" size="sm">
            <a href={`${API_BASE_URL}/api/replay/student/${studentId}/export?fmt=${format}`}>
              <Download className="mr-1 h-4 w-4" />
              {format.toUpperCase()}
            </a>
          </Button>
        ))}
      </div>
    </section>
  )
}
