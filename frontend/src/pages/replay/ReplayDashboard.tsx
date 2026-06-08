import { useEffect, useMemo, useRef, useState } from 'react'
import { ArrowLeft, Play, Pause, RotateCcw, SkipForward, Gauge } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { ReplayTimeline } from '@/components/swarm/ReplayTimeline'
import { StudentEvolutionView } from '@/components/swarm/StudentEvolutionView'
import { ReplayReasoningPanel } from '@/components/swarm/ReplayReasoningPanel'
import { ReplayMemoryView } from '@/components/swarm/ReplayMemoryView'
import { ReplayConsensusView } from '@/components/swarm/ReplayConsensusView'
import { ReplayExportPanel } from '@/components/swarm/ReplayExportPanel'
import { MemoryInfluencePanel } from '@/components/swarm/MemoryInfluencePanel'
import type { ReplaySession, ReplaySessionListItem, ReplayStep, ReplayTimeline as ReplayTimelineType, LongitudinalMetrics } from '@/types/replay'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'

export default function ReplayDashboard() {
  const [sessions, setSessions] = useState<ReplaySessionListItem[]>([])
  const [selectedStudent, setSelectedStudent] = useState<string | null>(null)
  const [replay, setReplay] = useState<ReplaySession | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [activeStep, setActiveStep] = useState(0)
  const [playing, setPlaying] = useState(false)
  const [playMode, setPlayMode] = useState<'week' | 'full'>('full')
  const [activeTab, setActiveTab] = useState<'adaptation' | 'reasoning' | 'memory' | 'consensus' | 'export'>('adaptation')
  const timerRef = useRef<number | null>(null)
  const [sseConnected, setSseConnected] = useState(false)
  const [sseLog, setSseLog] = useState<string[]>([])
  const eventSourceRef = useRef<EventSource | null>(null)

  useEffect(() => {
    fetch(`${API_BASE_URL}/api/replay/sessions`)
      .then((r) => r.json())
      .then((data) => setSessions(data.sessions || []))
      .catch(() => setError('Failed to load replay sessions'))
  }, [])

  useEffect(() => {
    if (!playing) return
    const step = playMode === 'full' ? 1 : 1
    timerRef.current = window.setInterval(() => {
      setActiveStep((prev) => {
        if (!replay || prev >= replay.total_weeks - 1) {
          setPlaying(false)
          return prev
        }
        return prev + step
      })
    }, 1200)
    return () => {
      if (timerRef.current) window.clearInterval(timerRef.current)
    }
  }, [playing, playMode, replay])

  const currentStep: ReplayStep | null = useMemo(() => {
    if (!replay || !replay.steps.length) return null
    return replay.steps[Math.min(activeStep, replay.steps.length - 1)]
  }, [replay, activeStep])

  function loadStudent(studentId: string) {
    setSelectedStudent(studentId)
    setLoading(true)
    setError(null)
    setActiveStep(0)
    setPlaying(false)
    fetch(`${API_BASE_URL}/api/replay/student/${studentId}`)
      .then((r) => {
        if (!r.ok) throw new Error('Failed to load replay')
        return r.json()
      })
      .then((data) => {
        setReplay(data as ReplaySession)
        setLoading(false)
      })
      .catch((e) => {
        setError(e.message)
        setLoading(false)
      })
  }

  function connectSSE(studentId: string) {
    if (eventSourceRef.current) {
      eventSourceRef.current.close()
    }
    setSseLog([])
    const es = new EventSource(`${API_BASE_URL}/api/replay/stream/${studentId}`)
    eventSourceRef.current = es

    es.addEventListener('replay:start', (e) => {
      setSseConnected(true)
      setSseLog((prev) => [...prev, `replay:start — ${e.data}`])
    })
    es.addEventListener('replay:timeline', (e) => {
      setSseLog((prev) => [...prev, `replay:timeline — ${e.data}`])
    })
    es.addEventListener('replay:adaptation', (e) => {
      setSseLog((prev) => [...prev, `replay:adaptation — ${e.data.slice(0, 80)}...`])
    })
    es.addEventListener('replay:memory', (e) => {
      setSseLog((prev) => [...prev, `replay:memory — ${e.data.slice(0, 80)}...`])
    })
    es.addEventListener('replay:reasoning', (e) => {
      setSseLog((prev) => [...prev, `replay:reasoning — ${e.data.slice(0, 80)}...`])
    })
    es.addEventListener('replay:bloom', (e) => {
      setSseLog((prev) => [...prev, `replay:bloom — ${e.data}`])
    })
    es.addEventListener('replay:misconception', (e) => {
      setSseLog((prev) => [...prev, `replay:misconception — ${e.data}`])
    })
    es.addEventListener('replay:consensus', (e) => {
      setSseLog((prev) => [...prev, `replay:consensus — ${e.data}`])
    })
    es.addEventListener('replay:complete', (e) => {
      setSseLog((prev) => [...prev, `replay:complete — ${e.data}`])
      es.close()
      setSseConnected(false)
    })
    es.onerror = () => {
      setSseConnected(false)
    }
  }

  function disconnectSSE() {
    if (eventSourceRef.current) {
      eventSourceRef.current.close()
      eventSourceRef.current = null
    }
    setSseConnected(false)
  }

  function goBack() {
    setSelectedStudent(null)
    setReplay(null)
    disconnectSSE()
  }

  const progress = replay ? ((activeStep + 1) / replay.total_weeks) * 100 : 0
  const timeline: ReplayTimelineType | null = replay?.timeline ?? null
  const metrics: LongitudinalMetrics | null = replay?.metrics ?? null

  if (!selectedStudent) {
    return (
      <main className="min-h-screen bg-slate-50 p-6">
        <div className="mx-auto max-w-6xl">
          <h1 className="mb-6 text-2xl font-bold text-slate-900">Replay Dashboard</h1>
          <p className="mb-6 text-sm text-slate-500">Select a student to replay their full pedagogical evolution.</p>
          {error && <p className="mb-4 rounded-md bg-red-50 p-3 text-sm text-red-700">{error}</p>}
          {sessions.length === 0 ? (
            <div className="rounded-lg border border-dashed bg-white p-12 text-center">
              <p className="text-slate-500">No replay sessions found. Generate pedagogical plans first.</p>
            </div>
          ) : (
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {sessions.map((s) => (
                <button
                  key={s.student_id}
                  type="button"
                  onClick={() => loadStudent(s.student_id)}
                  className="rounded-lg border bg-white p-5 text-left transition hover:border-primary hover:shadow-sm"
                >
                  <p className="font-semibold text-slate-900">{s.student_name || s.student_id}</p>
                  <p className="mt-1 text-sm text-slate-500">{s.course_name}</p>
                  <p className="mt-2 text-xs text-slate-400">{s.total_weeks} weeks · {s.course_id}</p>
                </button>
              ))}
            </div>
          )}
        </div>
      </main>
    )
  }

  return (
    <main className="min-h-screen bg-slate-50 p-6">
      <div className="mx-auto max-w-7xl">
        <div className="mb-6 flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <Button variant="ghost" size="sm" onClick={goBack}>
              <ArrowLeft className="mr-1 h-4 w-4" /> Back
            </Button>
            <h1 className="text-2xl font-bold text-slate-900">Replay: {selectedStudent}</h1>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" onClick={() => connectSSE(selectedStudent)} disabled={sseConnected}>
              {sseConnected ? 'SSE Connected' : 'Connect SSE'}
            </Button>
            {sseConnected && (
              <Button variant="outline" size="sm" onClick={disconnectSSE}>Disconnect</Button>
            )}
          </div>
        </div>

        {loading && <p className="text-sm text-slate-500">Loading replay...</p>}
        {error && <p className="mb-4 rounded-md bg-red-50 p-3 text-sm text-red-700">{error}</p>}

        {replay && (
          <>
            <div className="mb-6 flex flex-wrap items-center gap-3 rounded-lg border bg-white p-4">
              <span className="flex items-center gap-1.5 text-xs font-medium text-slate-500">
                <Gauge className="h-4 w-4" />
                Week {activeStep + 1} / {replay.total_weeks}
              </span>
              <div className="h-2 flex-1 overflow-hidden rounded-full bg-slate-100">
                <div className="h-full rounded-full bg-primary transition-all" style={{ width: `${Math.max(2, progress)}%` }} />
              </div>
              <div className="flex gap-1">
                <Button size="sm" variant={playMode === 'week' ? 'default' : 'outline'} onClick={() => setPlayMode('week')}>Week</Button>
                <Button size="sm" variant={playMode === 'full' ? 'default' : 'outline'} onClick={() => setPlayMode('full')}>Full</Button>
              </div>
              <Button size="sm" onClick={() => setPlaying((p) => !p)} disabled={!replay.steps.length}>
                {playing ? <><Pause className="mr-1 h-4 w-4" /> Pause</> : <><Play className="mr-1 h-4 w-4" /> Play</>}
              </Button>
              <Button size="sm" variant="outline" onClick={() => { setActiveStep(0); setPlaying(false) }}>
                <RotateCcw className="mr-1 h-4 w-4" /> Restart
              </Button>
              <Button size="sm" variant="outline" onClick={() => setActiveStep((p) => Math.min(replay.total_weeks - 1, p + 1))}>
                <SkipForward className="mr-1 h-4 w-4" /> Step
              </Button>
            </div>

            <div className="mb-6 grid gap-6 lg:grid-cols-2">
              <ReplayTimeline
                events={[]}
                activeIndex={activeStep}
              />
              {currentStep && (
                <MemoryInfluencePanel
                  profile={currentStep.profile}
                  metrics={currentStep.metrics}
                />
              )}
            </div>

            {timeline && metrics && (
              <div className="mb-6">
                <StudentEvolutionView timeline={timeline} metrics={metrics} />
              </div>
            )}

            <div className="mb-4 flex flex-wrap gap-2">
              {(['adaptation', 'reasoning', 'memory', 'consensus', 'export'] as const).map((tab) => (
                <button
                  key={tab}
                  type="button"
                  onClick={() => setActiveTab(tab)}
                  className={`rounded-md px-4 py-2 text-sm font-medium ${activeTab === tab ? 'bg-primary text-white' : 'bg-white text-slate-700 border'}`}
                >
                  {tab.charAt(0).toUpperCase() + tab.slice(1)}
                </button>
              ))}
            </div>

            <div className="mb-6">
              {activeTab === 'adaptation' && currentStep && (
                <AdaptationDetailView step={currentStep} />
              )}
              {activeTab === 'reasoning' && currentStep && (
                <ReplayReasoningPanel explanations={currentStep.reasoning.explanations} decisionGraph={currentStep.reasoning.decision_graph} />
              )}
              {activeTab === 'memory' && currentStep && (
                <ReplayMemoryView snapshot={currentStep.memory} />
              )}
              {activeTab === 'consensus' && currentStep && (
                <ReplayConsensusView consensus={currentStep.adaptation.consensus} bloom={currentStep.adaptation.bloom} />
              )}
              {activeTab === 'export' && replay && (
                <ReplayExportPanel studentId={selectedStudent} replay={replay} />
              )}
            </div>

            {sseLog.length > 0 && (
              <div className="rounded-lg border bg-white">
                <div className="border-b px-4 py-3">
                  <h3 className="text-sm font-semibold text-slate-900">SSE Event Log</h3>
                </div>
                <div className="max-h-48 overflow-y-auto p-4">
                  {sseLog.map((entry, i) => (
                    <p key={i} className="text-xs text-slate-600 font-mono">{entry}</p>
                  ))}
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </main>
  )
}

function AdaptationDetailView({ step }: { step: ReplayStep }) {
  const { bloom, analogy_domain, scaffolding, differentiation } = step.adaptation
  return (
    <div className="rounded-lg border bg-white">
      <div className="border-b px-4 py-3">
        <h3 className="text-sm font-semibold text-slate-900">Week {step.week_number} — Adaptation Decisions</h3>
      </div>
      <div className="grid gap-4 p-4 sm:grid-cols-2">
        <div className="rounded-md bg-slate-50 p-3">
          <p className="text-xs font-medium text-slate-500">Bloom Level</p>
          <p className="mt-1 text-lg font-bold text-slate-900">
            {bloom.previous ?? '?'} → {bloom.current}
            <span className={`ml-2 text-xs ${bloom.direction === 'up' ? 'text-green-600' : bloom.direction === 'down' ? 'text-red-600' : 'text-slate-400'}`}>
              ({bloom.direction})
            </span>
          </p>
          <p className="mt-1 text-xs text-slate-500">{bloom.adjusted_reason}</p>
        </div>
        <div className="rounded-md bg-slate-50 p-3">
          <p className="text-xs font-medium text-slate-500">Analogy Domain</p>
          <p className="mt-1 text-lg font-bold text-slate-900">{analogy_domain.current || '—'}</p>
          {analogy_domain.changed && <p className="text-xs text-amber-600">Changed from {analogy_domain.previous}</p>}
        </div>
        <div className="rounded-md bg-slate-50 p-3">
          <p className="text-xs font-medium text-slate-500">Scaffolding</p>
          <p className="mt-1 text-sm text-slate-900">{scaffolding.current_count} steps</p>
          <ul className="mt-1 list-inside list-disc text-xs text-slate-500">
            {scaffolding.steps.map((s, i) => <li key={i}>{s}</li>)}
          </ul>
        </div>
        <div className="rounded-md bg-slate-50 p-3">
          <p className="text-xs font-medium text-slate-500">Differentiation</p>
          {Object.entries(differentiation).map(([key, val]) => (
            <p key={key} className="mt-1 text-xs text-slate-600"><strong>{key}:</strong> {val}</p>
          ))}
        </div>
      </div>
    </div>
  )
}
