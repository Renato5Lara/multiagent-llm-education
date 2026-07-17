// Resumen — primera pestaña del Panel Pedagógico. Reutiliza EXACTAMENTE el
// mismo hook que la pestaña Investigación (useResearchSummary) — react-query
// cachea por queryKey, así que no hay una segunda consulta al backend, solo
// una lectura distinta del mismo dato real.
import { Loader2, TrendingUp, Users } from 'lucide-react'
import { useResearchSummary } from '@/hooks/useResearch'

function fmt(value: number | null | undefined, suffix = '', digits = 1): string {
  if (value === null || value === undefined) return '—'
  return `${Number(value).toFixed(digits)}${suffix}`
}

function StatTile({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <div className="glass-panel rounded-xl p-5">
      <p className="text-[10px] font-mono text-neural-muted/60 tracking-widest uppercase mb-2">{label}</p>
      <p className="text-2xl font-bold text-neural-text font-mono">{value}</p>
      {hint && <p className="text-[11px] text-neural-muted/70 mt-1">{hint}</p>}
    </div>
  )
}

export default function ResumenTab() {
  const summary = useResearchSummary()

  if (summary.isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[30vh]">
        <Loader2 className="h-8 w-8 animate-spin text-neural-glow" />
      </div>
    )
  }

  const data = summary.data
  if (!data) {
    return <p className="text-neural-muted text-center py-16">No se pudo cargar el resumen.</p>
  }

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatTile
          label="Estudiantes (pre-test)"
          value={String(data.n_students_pretested)}
          hint={`${data.n_students_posttested} con post-test`}
        />
        <StatTile label="Promedio Pre-Test" value={fmt(data.avg_pre_pct, '%')} />
        <StatTile label="Promedio Post-Test" value={fmt(data.avg_post_pct, '%')} />
        <StatTile
          label="Incremento promedio"
          value={data.avg_absolute_gain !== null ? `${data.avg_absolute_gain >= 0 ? '+' : ''}${fmt(data.avg_absolute_gain)}` : '—'}
          hint={data.avg_normalized_gain !== null ? `ganancia normalizada g = ${fmt(data.avg_normalized_gain, '', 2)}` : undefined}
        />
      </div>

      <div className="grid sm:grid-cols-2 gap-4">
        <div className="glass-panel rounded-xl p-5">
          <div className="flex items-center gap-2 mb-4">
            <Users className="h-4 w-4 text-neural-violet" />
            <p className="text-[10px] font-mono text-neural-muted/60 tracking-widest uppercase">
              Estudiantes por perfil
            </p>
          </div>
          {Object.keys(data.students_by_profile).length ? (
            <ul className="space-y-2">
              {Object.entries(data.students_by_profile).map(([style, count]) => (
                <li key={style} className="flex justify-between text-sm">
                  <span className="text-neural-text capitalize">{style}</span>
                  <span className="text-neural-muted font-mono">{count}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-neural-muted/70">Sin perfiles registrados aún.</p>
          )}
        </div>
        <div className="glass-panel rounded-xl p-5">
          <div className="flex items-center gap-2 mb-4">
            <TrendingUp className="h-4 w-4 text-neural-glow" />
            <p className="text-[10px] font-mono text-neural-muted/60 tracking-widest uppercase">
              Rutas y tutor
            </p>
          </div>
          <ul className="space-y-2 text-sm">
            <li className="flex justify-between">
              <span className="text-neural-text">Rutas generadas</span>
              <span className="text-neural-muted font-mono">{data.paths_generated}</span>
            </li>
            <li className="flex justify-between">
              <span className="text-neural-text">Mensajes al Tutor IA</span>
              <span className="text-neural-muted font-mono">{data.tutor_messages_total}</span>
            </li>
          </ul>
        </div>
      </div>
    </div>
  )
}
