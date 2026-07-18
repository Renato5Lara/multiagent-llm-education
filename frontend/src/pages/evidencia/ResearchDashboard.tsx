import { useState, type ReactNode } from 'react'
import { Clock, Download, FileSpreadsheet, FlaskConical, GitBranch, Loader2, Route, TrendingUp, Users } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  useCycleAggregates,
  useResearchStudents,
  useResearchSummary,
  useStudentCycles,
  type StudentCycleRow,
} from '@/hooks/useResearch'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'

const LEVEL_LABELS: Record<string, string> = {
  basico: 'Básico',
  intermedio: 'Intermedio',
  avanzado: 'Avanzado',
}

const LEVEL_BAR: Record<string, string> = {
  basico: 'bg-amber-400',
  intermedio: 'bg-neural-glow',
  avanzado: 'bg-neural-pulse',
}

function fmt(value: number | null | undefined, suffix = '', digits = 1): string {
  if (value === null || value === undefined) return '—'
  return `${Number(value).toFixed(digits)}${suffix}`
}

function fmtMs(value: number | null | undefined): string {
  if (value === null || value === undefined) return '—'
  return value >= 1000 ? `${(value / 1000).toFixed(1)} s` : `${value.toFixed(0)} ms`
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

function LevelDistribution({ title, distribution }: { title: string; distribution: Record<string, number> }) {
  const total = Object.values(distribution).reduce((a, b) => a + b, 0)
  return (
    <div className="glass-panel rounded-xl p-5">
      <p className="text-[10px] font-mono text-neural-muted/60 tracking-widest uppercase mb-4">{title}</p>
      <div className="space-y-3">
        {(['basico', 'intermedio', 'avanzado'] as const).map((level) => {
          const count = distribution[level] ?? 0
          const pct = total > 0 ? (count / total) * 100 : 0
          return (
            <div key={level}>
              <div className="flex justify-between text-xs mb-1">
                <span className="text-neural-text">{LEVEL_LABELS[level]}</span>
                <span className="text-neural-muted font-mono">{count}</span>
              </div>
              <div className="h-2 rounded-full bg-white/5 overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all duration-500 ${LEVEL_BAR[level]}`}
                  style={{ width: `${pct}%` }}
                />
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

function fmtSeconds(value: number | null | undefined): string {
  if (value === null || value === undefined) return '—'
  return value >= 60 ? `${(value / 60).toFixed(1)} min` : `${value.toFixed(0)} s`
}

const MODALITY_LABELS: Record<string, string> = {
  visual: 'Visual',
  reading: 'Lector',
  audio: 'Auditivo',
  kinesthetic: 'Kinestésico',
  mixta: 'Mixta',
}

const PROFUNDIDAD_LABELS: Record<string, string> = {
  fundamentos: 'Fundamentos',
  aplicacion: 'Aplicación',
}

/** Barra horizontal genérica para un mapa clave→número — reutilizada para
 *  tiempo por concepto, tasa de remediación, frecuencia de modalidad y
 *  distribución de profundidad, para no repetir el mismo layout 4 veces. */
function BarMap({
  title,
  icon,
  entries,
  formatValue,
  labelFor,
  maxHint,
}: {
  title: string
  icon: ReactNode
  entries: [string, number | null][]
  formatValue: (v: number | null) => string
  labelFor?: (key: string) => string
  maxHint?: number
}) {
  const max = maxHint ?? Math.max(1, ...entries.map(([, v]) => v ?? 0))
  return (
    <div className="glass-panel rounded-xl p-5">
      <div className="flex items-center gap-2 mb-4">
        {icon}
        <p className="text-[10px] font-mono text-neural-muted/60 tracking-widest uppercase">{title}</p>
      </div>
      {entries.length ? (
        <div className="space-y-3">
          {entries.map(([key, value]) => {
            const pct = value !== null ? Math.min(100, (value / max) * 100) : 0
            return (
              <div key={key}>
                <div className="flex justify-between text-xs mb-1">
                  <span className="text-neural-text capitalize">{labelFor ? labelFor(key) : key}</span>
                  <span className="text-neural-muted font-mono">{formatValue(value)}</span>
                </div>
                <div className="h-2 rounded-full bg-white/5 overflow-hidden">
                  <div
                    className="h-full rounded-full bg-neural-glow transition-all duration-500"
                    style={{ width: `${pct}%` }}
                  />
                </div>
              </div>
            )
          })}
        </div>
      ) : (
        <p className="text-sm text-neural-muted/70">Sin ciclos registrados aún.</p>
      )}
    </div>
  )
}

function CycleTraceCard({ row }: { row: StudentCycleRow }) {
  const resultadoLabel =
    row.resultado === true ? 'Resuelto sin ayuda' : row.resultado === false ? 'No resuelto sin ayuda' : 'Sin registrar'
  const resultadoColor =
    row.resultado === true ? 'text-neural-pulse' : row.resultado === false ? 'text-amber-400' : 'text-neural-muted'
  return (
    <div className="glass-panel rounded-xl p-4 space-y-3">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <p className="text-sm font-semibold text-neural-text capitalize">{row.concepto ?? 'Concepto sin registrar'}</p>
        <span className="text-[10px] font-mono text-neural-muted/60">{row.fecha ? new Date(row.fecha).toLocaleString() : '—'}</span>
      </div>

      <div className="grid sm:grid-cols-2 gap-x-4 gap-y-1.5 text-xs">
        <p className="text-neural-muted">
          Evidencia: <span className="text-neural-text">{row.intentos ?? '—'} intento(s)</span>,{' '}
          <span className={resultadoColor}>{resultadoLabel}</span>, {row.ayudas ?? 0} pista(s)
          {row.tiempo_ms !== null && <>, {fmtMs(row.tiempo_ms)}</>}
        </p>
        <p className="text-neural-muted">
          Decisión:{' '}
          <span className="text-neural-text">
            {row.modalidad_refuerzo ? MODALITY_LABELS[row.modalidad_refuerzo] ?? row.modalidad_refuerzo : '—'}
          </span>
          {row.profundidad && (
            <> · Bloom: <span className="text-neural-text">{PROFUNDIDAD_LABELS[row.profundidad] ?? row.profundidad}</span></>
          )}
        </p>
      </div>

      <p className="text-xs text-neural-muted/80 italic border-t border-white/[0.06] pt-2.5">{row.justificacion}</p>
    </div>
  )
}

export default function ResearchDashboard() {
  const summary = useResearchSummary()
  const students = useResearchStudents()
  const aggregates = useCycleAggregates()
  const [selectedStudent, setSelectedStudent] = useState<string | null>(null)
  const cycles = useStudentCycles(selectedStudent)

  if (summary.isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[50vh]">
        <Loader2 className="h-10 w-10 animate-spin text-neural-glow" />
      </div>
    )
  }

  const data = summary.data
  if (!data) {
    return (
      <div className="max-w-4xl mx-auto text-center py-16">
        <p className="text-neural-muted">No se pudo cargar el resumen de investigación.</p>
      </div>
    )
  }

  return (
    <div className="max-w-5xl mx-auto space-y-8">
      {/* Header */}
      <div className="flex items-start justify-between flex-wrap gap-4">
        <div className="space-y-1">
          <div className="flex items-center gap-2.5">
            <FlaskConical className="h-5 w-5 text-neural-violet" />
            <h1 className="text-2xl font-bold text-neural-text tracking-tight">Dashboard del Investigador</h1>
          </div>
          <p className="text-sm text-neural-muted leading-relaxed max-w-2xl">
            Evidencia del experimento pre-test → post-test (diseño pre-experimental, grupo único{' '}
            <span className="text-neural-text">{data.group_label}</span>). Todas las métricas provienen de la
            base de datos del recorrido real — sin datos simulados.
          </p>
        </div>

        {/* Exportación */}
        <div className="flex gap-2">
          <Button asChild variant="outline" size="sm" className="gap-2">
            <a href={`${API_BASE_URL}/api/research/export?fmt=csv`} download>
              <Download className="h-3.5 w-3.5" />
              Exportar CSV
            </a>
          </Button>
          <Button asChild variant="outline" size="sm" className="gap-2">
            <a href={`${API_BASE_URL}/api/research/export?fmt=xlsx`} download>
              <FileSpreadsheet className="h-3.5 w-3.5" />
              Exportar Excel
            </a>
          </Button>
          <Button asChild size="sm" className="gap-2">
            <a href={`${API_BASE_URL}/api/research/export-experiment`} download>
              <FileSpreadsheet className="h-3.5 w-3.5" />
              Exportar experimento
            </a>
          </Button>
        </div>
      </div>

      {/* KPIs del experimento */}
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

      {/* Distribución de niveles */}
      <div className="grid sm:grid-cols-2 gap-4">
        <LevelDistribution title="Distribución de niveles · Pre-Test" distribution={data.level_distribution_pre} />
        <LevelDistribution title="Distribución de niveles · Post-Test" distribution={data.level_distribution_post} />
      </div>

      {/* Métricas del sistema */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatTile label="Rutas generadas" value={String(data.paths_generated)} />
        <StatTile label="Generación de ruta (prom.)" value={fmtMs(data.avg_path_generation_ms)} />
        <StatTile label="Orquestación IA (prom.)" value={fmtMs(data.avg_ai_orchestration_ms)} />
        <StatTile
          label="Resolución del test (prom.)"
          value={data.avg_pre_duration_seconds !== null ? `${(data.avg_pre_duration_seconds / 60).toFixed(1)} min` : '—'}
          hint={data.avg_post_duration_seconds !== null ? `post: ${(data.avg_post_duration_seconds / 60).toFixed(1)} min` : undefined}
        />
      </div>

      {/* Ciclos de aprendizaje — agregados en vivo de research_metrics/CYCLE_EVIDENCE */}
      <div className="space-y-1">
        <div className="flex items-center gap-2 flex-wrap">
          <GitBranch className="h-4 w-4 text-neural-violet" />
          <h2 className="text-sm font-semibold text-neural-text">Ciclos de aprendizaje ({aggregates.data?.n_ciclos ?? (aggregates.isLoading ? '…' : 0)})</h2>
          {aggregates.data?.tasa_remediacion_global_pct !== null && aggregates.data?.tasa_remediacion_global_pct !== undefined && (
            <span className="text-[10px] font-mono px-2 py-0.5 rounded-full border border-amber-500/30 text-amber-300/90 bg-amber-500/10">
              remediación global {aggregates.data.tasa_remediacion_global_pct}%
            </span>
          )}
        </div>
        <p className="text-xs text-neural-muted/70 max-w-2xl">
          Cada ciclo es un envío real de práctica (<span className="font-mono">/cycle-evidence</span>). La tasa de
          remediación se define como el % de ciclos en los que el estudiante no resolvió sin que se revelara la
          solución.
        </p>
      </div>
      <div className="grid sm:grid-cols-2 gap-4">
        <BarMap
          title="Tiempo promedio por concepto"
          icon={<Clock className="h-4 w-4 text-neural-glow" />}
          entries={Object.entries(aggregates.data?.tiempo_promedio_por_concepto_seg ?? {})}
          formatValue={fmtSeconds}
        />
        <BarMap
          title="Tasa de remediación por concepto"
          icon={<TrendingUp className="h-4 w-4 text-amber-400" />}
          entries={Object.entries(aggregates.data?.tasa_remediacion_por_concepto_pct ?? {})}
          formatValue={(v) => (v !== null ? `${v}%` : '—')}
          maxHint={100}
        />
      </div>
      <div className="grid sm:grid-cols-2 gap-4">
        <BarMap
          title="Rutas adaptativas (modalidad de refuerzo decidida)"
          icon={<Route className="h-4 w-4 text-neural-violet" />}
          entries={Object.entries(aggregates.data?.frecuencia_modalidad_refuerzo ?? {})}
          formatValue={(v) => String(v ?? 0)}
          labelFor={(k) => MODALITY_LABELS[k] ?? k}
        />
        <BarMap
          title="Distribución de profundidad (Bloom)"
          icon={<TrendingUp className="h-4 w-4 text-neural-pulse" />}
          entries={Object.entries(aggregates.data?.distribucion_profundidad ?? {})}
          formatValue={(v) => String(v ?? 0)}
          labelFor={(k) => PROFUNDIDAD_LABELS[k] ?? k}
        />
      </div>

      {/* Estudiantes por perfil + tutor */}
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
              Interacción con el Tutor IA
            </p>
          </div>
          <ul className="space-y-2 text-sm">
            <li className="flex justify-between">
              <span className="text-neural-text">Mensajes totales</span>
              <span className="text-neural-muted font-mono">{data.tutor_messages_total}</span>
            </li>
            <li className="flex justify-between">
              <span className="text-neural-text">Promedio por estudiante</span>
              <span className="text-neural-muted font-mono">{fmt(data.avg_tutor_messages_per_student)}</span>
            </li>
            <li className="flex justify-between">
              <span className="text-neural-text">Latencia tutor (prom.)</span>
              <span className="text-neural-muted font-mono">{fmtMs(data.avg_tutor_latency_ms)}</span>
            </li>
          </ul>
        </div>
      </div>

      {/* Tabla de resultados por estudiante */}
      <div className="glass-panel rounded-xl p-5 overflow-x-auto">
        <p className="text-[10px] font-mono text-neural-muted/60 tracking-widest uppercase mb-4">
          Resultados por estudiante ({students.data?.total ?? 0})
        </p>
        {students.isLoading ? (
          <div className="py-8 text-center">
            <Loader2 className="h-6 w-6 animate-spin text-neural-glow mx-auto" />
          </div>
        ) : students.data && students.data.rows.length > 0 ? (
          <table className="w-full text-xs">
            <thead>
              <tr className="text-left text-neural-muted/70 border-b border-white/10">
                <th className="py-2 pr-3 font-medium">Estudiante</th>
                <th className="py-2 pr-3 font-medium">Pre</th>
                <th className="py-2 pr-3 font-medium">Post</th>
                <th className="py-2 pr-3 font-medium">Δ</th>
                <th className="py-2 pr-3 font-medium">Nivel</th>
                <th className="py-2 pr-3 font-medium">Perfil</th>
                <th className="py-2 pr-3 font-medium">T. IA</th>
                <th className="py-2 pr-3 font-medium">Fecha</th>
              </tr>
            </thead>
            <tbody>
              {students.data.rows.map((row) => (
                <tr key={row.student_id} className="border-b border-white/5 text-neural-text">
                  <td className="py-2 pr-3 font-mono text-neural-muted">{row.student_id.slice(0, 8)}</td>
                  <td className="py-2 pr-3 font-mono">{fmt(row.pre_pct, '%', 0)}</td>
                  <td className="py-2 pr-3 font-mono">{fmt(row.post_pct, '%', 0)}</td>
                  <td className={`py-2 pr-3 font-mono ${
                    (row.absolute_gain ?? 0) > 0 ? 'text-neural-pulse' : (row.absolute_gain ?? 0) < 0 ? 'text-red-400' : ''
                  }`}>
                    {row.absolute_gain !== null ? `${row.absolute_gain >= 0 ? '+' : ''}${row.absolute_gain.toFixed(1)}` : '—'}
                  </td>
                  <td className="py-2 pr-3">{row.level ? LEVEL_LABELS[row.level] ?? row.level : '—'}</td>
                  <td className="py-2 pr-3 capitalize">{row.profile ?? '—'}</td>
                  <td className="py-2 pr-3 font-mono">{fmtMs(row.ai_time_ms)}</td>
                  <td className="py-2 pr-3 font-mono text-neural-muted">{row.date ?? '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <p className="text-sm text-neural-muted/70 py-4">
            Aún no hay estudiantes con pre-test completado. Los resultados aparecerán aquí conforme
            los estudiantes recorran la plataforma.
          </p>
        )}
      </div>

      {/* Trazabilidad de la adaptación — evidencia → decisión → justificación por estudiante */}
      <div className="glass-panel rounded-xl p-5 space-y-4">
        <div className="flex items-center justify-between flex-wrap gap-3">
          <div className="flex items-center gap-2">
            <GitBranch className="h-4 w-4 text-neural-violet" />
            <p className="text-[10px] font-mono text-neural-muted/60 tracking-widest uppercase">
              Trazabilidad de la adaptación
            </p>
          </div>
          <select
            value={selectedStudent ?? ''}
            onChange={(e) => setSelectedStudent(e.target.value || null)}
            className="text-xs bg-neural-lowest/60 border border-white/10 rounded-lg px-3 py-1.5 text-neural-text"
          >
            <option value="">Selecciona un estudiante…</option>
            {students.data?.rows.map((row) => (
              <option key={row.student_id} value={row.student_id}>
                {row.student_id.slice(0, 8)} · {row.profile ?? 'sin perfil'}
              </option>
            ))}
          </select>
        </div>

        {!selectedStudent ? (
          <p className="text-sm text-neural-muted/70">
            Elige un estudiante para ver, ciclo por ciclo, la evidencia real que recibió el motor de adaptación, la
            decisión que tomó Adaptar y la justificación derivada de esa misma evidencia.
          </p>
        ) : cycles.isLoading ? (
          <div className="py-8 text-center">
            <Loader2 className="h-6 w-6 animate-spin text-neural-glow mx-auto" />
          </div>
        ) : cycles.data && cycles.data.rows.length > 0 ? (
          <div className="space-y-3 max-h-[32rem] overflow-y-auto pr-1">
            {cycles.data.rows.map((row, i) => (
              <CycleTraceCard key={`${row.concepto}-${row.fecha}-${i}`} row={row} />
            ))}
          </div>
        ) : (
          <p className="text-sm text-neural-muted/70">Este estudiante todavía no tiene ciclos de práctica registrados.</p>
        )}
      </div>
    </div>
  )
}
