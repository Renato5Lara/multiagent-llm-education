import { useState, useEffect } from 'react'
import { GitCompare, RefreshCw, TrendingUp, TrendingDown, Minus } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { ReplayEvolutionDashboard } from '@/components/replay/ReplayEvolutionDashboard'
import { ReplayBloomEvolution } from '@/components/replay/ReplayBloomEvolution'
import { ReplayConsensusEvolution } from '@/components/replay/ReplayConsensusEvolution'
import api from '@/lib/api'

interface SessionSummary {
  session_id: string
  topic: string
  frame_count: number
  duration_ms: number
  phases: string[]
  phase_count: number
  agents: string[]
  agent_count: number
  bloom_distribution: Record<number, number>
  bloom_diversity: number
  modality_distribution: Record<string, number>
  modality_diversity: number
  prompt_types: Record<string, number>
  prompt_count: number
  bloom_verbs_used: string[]
  learner_signals_count: number
  bloom_aware_decisions: number
  orchestration_trace_length: number
  profile_source: string
  difficulty_level: string
  consensus_confidence: number
}

interface AdvantageRow {
  dimension: string
  description: string
  value_a: number
  value_b: number
  winner: 'a' | 'b' | 'tie'
  delta: number
}

interface SwarmScore {
  session_a_wins: number
  session_b_wins: number
  ties: number
  total_dimensions: number
  advantage_ratio_a: number
  advantage_ratio_b: number
}

interface ComparisonResult {
  session_a: SessionSummary
  session_b: SessionSummary
  advantages: AdvantageRow[]
  swarm_score: SwarmScore
}

interface SessionListItem {
  session_id: string
  topic: string
  frame_count: number
  started_at: number
}

function toBloomData(dist: Record<number, number>) {
  const total = Object.values(dist).reduce((a, b) => a + b, 0)
  if (total === 0) return []
  return [{
    step: 1,
    avgBloom: Object.entries(dist).reduce((s, [k, v]) => s + Number(k) * v, 0) / total,
    maxBloom: Math.max(...Object.keys(dist).map(Number), 1),
    distribution: Object.fromEntries(Object.entries(dist).map(([k, v]) => [k, v])),
    sectionCount: total,
  }]
}

function toConsensusData(confidence: number) {
  if (confidence === 0) return []
  return [{ step: 1, decision: 'approved', confidence, voterCount: 7, unanimous: confidence >= 0.9 }]
}

function toMetrics(s: SessionSummary) {
  return [
    { name: 'Agentes activos', current: s.agent_count, trend: 'stable' as const },
    { name: 'Fases ejecutadas', current: s.phase_count, trend: 'stable' as const },
    { name: 'Prompts generados', current: s.prompt_count, trend: 'stable' as const },
    { name: 'Diversidad multimodal', current: s.modality_diversity, trend: 'stable' as const },
    { name: 'Decisiones Bloom-aware', current: s.bloom_aware_decisions, trend: 'stable' as const },
    { name: 'Señales del aprendiz', current: s.learner_signals_count, trend: 'stable' as const },
    { name: 'Confianza de consenso', current: `${(s.consensus_confidence * 100).toFixed(0)}%`, trend: 'stable' as const },
    { name: 'Fuente de perfil', current: s.profile_source, trend: 'stable' as const },
  ]
}

function WinnerIcon({ winner }: { winner: 'a' | 'b' | 'tie' | string }) {
  if (winner === 'a') return <TrendingUp className="h-3 w-3 text-cyan-400" />
  if (winner === 'b') return <TrendingUp className="h-3 w-3 text-violet-400" />
  return <Minus className="h-3 w-3 text-slate-500" />
}

export default function SwarmComparison() {
  const [sessions, setSessions] = useState<SessionListItem[]>([])
  const [selectedA, setSelectedA] = useState('')
  const [selectedB, setSelectedB] = useState('')
  const [comparison, setComparison] = useState<ComparisonResult | null>(null)
  const [loadingSessions, setLoadingSessions] = useState(true)
  const [loadingCompare, setLoadingCompare] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api.get<{ sessions: SessionListItem[] }>('/api/replay/sessions')
      .then(r => {
        const list = r.data.sessions || []
        setSessions(list)
        if (list.length >= 2) {
          setSelectedA(list[0].session_id)
          setSelectedB(list[1].session_id)
        } else if (list.length === 1) {
          setSelectedA(list[0].session_id)
        }
      })
      .catch(() => setError('No se pudo cargar la lista de sesiones.'))
      .finally(() => setLoadingSessions(false))
  }, [])

  const handleCompare = async () => {
    if (!selectedA || !selectedB || selectedA === selectedB) {
      setError('Selecciona dos sesiones distintas.')
      return
    }
    setError(null)
    setLoadingCompare(true)
    try {
      const r = await api.get<ComparisonResult>(`/api/replay/compare/${selectedA}/${selectedB}`)
      setComparison(r.data)
    } catch {
      setError('Error al obtener la comparación. Verifica que ambas sesiones existan.')
    } finally {
      setLoadingCompare(false)
    }
  }

  const scoreA = comparison?.swarm_score.session_a_wins ?? 0
  const scoreB = comparison?.swarm_score.session_b_wins ?? 0
  const totalDims = comparison?.swarm_score.total_dimensions ?? 1
  const pctA = Math.round((scoreA / totalDims) * 100)
  const pctB = Math.round((scoreB / totalDims) * 100)

  return (
    <div>
      <div className="mb-6">
        <div className="flex items-center gap-2 mb-1">
          <GitCompare className="h-5 w-5 text-cyan-500" />
          <h1 className="text-xl font-bold">Comparación Enjambre</h1>
        </div>
        <p className="text-sm text-muted-foreground">
          Contraste entre condiciones de orquestación — muestra el efecto cuantificable del enjambre multiagente
        </p>
      </div>

      <Card className="mb-6">
        <CardContent className="pt-5">
          <div className="flex flex-col md:flex-row gap-3 items-end">
            <div className="flex-1">
              <label className="text-xs text-muted-foreground block mb-1">Sesión A</label>
              {loadingSessions ? (
                <Skeleton className="h-9 w-full" />
              ) : (
                <select
                  value={selectedA}
                  onChange={e => setSelectedA(e.target.value)}
                  className="w-full h-9 rounded-md border border-input bg-background px-3 text-sm"
                >
                  <option value="">-- Seleccionar sesión --</option>
                  {sessions.map(s => (
                    <option key={s.session_id} value={s.session_id}>
                      [{s.session_id}] {s.topic.slice(0, 50)} ({s.frame_count} frames)
                    </option>
                  ))}
                </select>
              )}
            </div>
            <div className="flex-1">
              <label className="text-xs text-muted-foreground block mb-1">Sesión B</label>
              {loadingSessions ? (
                <Skeleton className="h-9 w-full" />
              ) : (
                <select
                  value={selectedB}
                  onChange={e => setSelectedB(e.target.value)}
                  className="w-full h-9 rounded-md border border-input bg-background px-3 text-sm"
                >
                  <option value="">-- Seleccionar sesión --</option>
                  {sessions.map(s => (
                    <option key={s.session_id} value={s.session_id}>
                      [{s.session_id}] {s.topic.slice(0, 50)} ({s.frame_count} frames)
                    </option>
                  ))}
                </select>
              )}
            </div>
            <Button
              onClick={handleCompare}
              disabled={!selectedA || !selectedB || selectedA === selectedB || loadingCompare}
              className="shrink-0"
            >
              {loadingCompare ? (
                <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
              ) : (
                <GitCompare className="h-4 w-4 mr-2" />
              )}
              Comparar
            </Button>
          </div>
          {error && <p className="text-red-500 text-xs mt-2">{error}</p>}
          {sessions.length === 0 && !loadingSessions && (
            <p className="text-muted-foreground text-xs mt-2">
              No hay sesiones de replay disponibles. Ejecuta una orquestación para generar sesiones.
            </p>
          )}
        </CardContent>
      </Card>

      {comparison && (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
            <div>
              <p className="text-xs text-cyan-400 font-semibold mb-2 uppercase tracking-wide">
                Sesión A — {comparison.session_a.session_id}
              </p>
              <ReplayEvolutionDashboard
                title={comparison.session_a.topic}
                metrics={toMetrics(comparison.session_a)}
              />
            </div>
            <div>
              <p className="text-xs text-violet-400 font-semibold mb-2 uppercase tracking-wide">
                Sesión B — {comparison.session_b.session_id}
              </p>
              <ReplayEvolutionDashboard
                title={comparison.session_b.topic}
                metrics={toMetrics(comparison.session_b)}
              />
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
            <div>
              <p className="text-xs text-slate-400 mb-1">Distribución Bloom — A</p>
              <ReplayBloomEvolution data={toBloomData(comparison.session_a.bloom_distribution)} />
            </div>
            <div>
              <p className="text-xs text-slate-400 mb-1">Distribución Bloom — B</p>
              <ReplayBloomEvolution data={toBloomData(comparison.session_b.bloom_distribution)} />
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
            <div>
              <p className="text-xs text-slate-400 mb-1">Consenso — A</p>
              <ReplayConsensusEvolution data={toConsensusData(comparison.session_a.consensus_confidence)} />
            </div>
            <div>
              <p className="text-xs text-slate-400 mb-1">Consenso — B</p>
              <ReplayConsensusEvolution data={toConsensusData(comparison.session_b.consensus_confidence)} />
            </div>
          </div>

          <Card className="bg-slate-900 border-slate-700">
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="text-cyan-300 text-sm flex items-center gap-2">
                  <TrendingUp className="h-4 w-4" />
                  Ventaja del Enjambre
                </CardTitle>
                <div className="flex items-center gap-3 text-xs">
                  <span className="text-cyan-400 font-mono font-bold">{scoreA}/{totalDims}</span>
                  <span className="text-slate-500">A</span>
                  <span className="text-slate-500">vs</span>
                  <span className="text-slate-500">B</span>
                  <span className="text-violet-400 font-mono font-bold">{scoreB}/{totalDims}</span>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <div className="mb-4 flex gap-2 items-center">
                <div className="flex-1 h-2 bg-slate-800 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-cyan-500 rounded-full transition-all"
                    style={{ width: `${pctA}%` }}
                  />
                </div>
                <span className="text-cyan-400 text-xs font-mono w-8 text-right">{pctA}%</span>
                <span className="text-slate-500 text-xs">A</span>
                <span className="text-slate-500 text-xs mx-1">/</span>
                <span className="text-slate-500 text-xs">B</span>
                <span className="text-violet-400 text-xs font-mono w-8">{pctB}%</span>
                <div className="flex-1 h-2 bg-slate-800 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-violet-500 rounded-full transition-all"
                    style={{ width: `${pctB}%` }}
                  />
                </div>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-xs">
                  <thead>
                    <tr className="border-b border-slate-700">
                      <th className="text-left text-slate-500 py-2 pr-3 font-normal">Dimensión</th>
                      <th className="text-right text-cyan-400 py-2 px-3 font-normal w-16">A</th>
                      <th className="text-right text-violet-400 py-2 px-3 font-normal w-16">B</th>
                      <th className="text-center text-slate-500 py-2 pl-3 font-normal w-20">Ganador</th>
                    </tr>
                  </thead>
                  <tbody>
                    {comparison.advantages.map((row, i) => (
                      <tr key={i} className="border-b border-slate-800 last:border-0">
                        <td className="py-2 pr-3">
                          <span className="text-slate-300">{row.dimension}</span>
                          <span className="block text-[10px] text-slate-500">{row.description}</span>
                        </td>
                        <td className={`text-right py-2 px-3 font-mono ${row.winner === 'a' ? 'text-cyan-300 font-bold' : 'text-slate-400'}`}>
                          {row.value_a}
                        </td>
                        <td className={`text-right py-2 px-3 font-mono ${row.winner === 'b' ? 'text-violet-300 font-bold' : 'text-slate-400'}`}>
                          {row.value_b}
                        </td>
                        <td className="text-center py-2 pl-3">
                          {row.winner === 'tie' ? (
                            <Badge variant="outline" className="text-[9px] border-slate-600 text-slate-500">Empate</Badge>
                          ) : (
                            <div className="flex items-center justify-center gap-1">
                              <WinnerIcon winner={row.winner} />
                              <Badge
                                className={`text-[9px] ${row.winner === 'a' ? 'bg-cyan-900 text-cyan-300' : 'bg-violet-900 text-violet-300'}`}
                              >
                                {row.winner.toUpperCase()} +{row.delta}
                              </Badge>
                            </div>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <div className="mt-4 grid grid-cols-3 gap-2 text-center">
                <div className="bg-slate-800 rounded p-2">
                  <p className="text-[10px] text-slate-500">Victoria A</p>
                  <p className="text-lg font-mono font-bold text-cyan-400">{scoreA}</p>
                </div>
                <div className="bg-slate-800 rounded p-2">
                  <p className="text-[10px] text-slate-500">Empates</p>
                  <p className="text-lg font-mono font-bold text-slate-400">{comparison.swarm_score.ties}</p>
                </div>
                <div className="bg-slate-800 rounded p-2">
                  <p className="text-[10px] text-slate-500">Victoria B</p>
                  <p className="text-lg font-mono font-bold text-violet-400">{scoreB}</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  )
}
