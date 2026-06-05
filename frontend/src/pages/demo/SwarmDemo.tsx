import { useCallback, useEffect, useMemo, useState } from 'react'
import { CheckCircle, Database, Play, RotateCcw, Signal, type LucideIcon } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { BloomProgressionView } from '@/components/swarm/BloomProgressionView'
import { ConsensusTimeline } from '@/components/swarm/ConsensusTimeline'
import { ContradictionViewer } from '@/components/swarm/ContradictionViewer'
import { CognitiveReplayView } from '@/components/swarm/CognitiveReplayView'
import { DeliberationReplay } from '@/components/swarm/DeliberationReplay'
import { LiveSessionFeed } from '@/components/swarm/LiveSessionFeed'
import { NarrativeConsistencyPanel } from '@/components/swarm/NarrativeConsistencyPanel'
import { PedagogicalStructurePanel } from '@/components/swarm/PedagogicalStructurePanel'
import { PromptGroundingPanel } from '@/components/swarm/PromptGroundingPanel'
import { ReplayControls } from '@/components/swarm/ReplayControls'
import { ReplayTimeline } from '@/components/swarm/ReplayTimeline'
import { RetrievalTimeline } from '@/components/swarm/RetrievalTimeline'
import { SandboxValidationPanel } from '@/components/swarm/SandboxValidationPanel'
import { SharedMemoryReplay } from '@/components/swarm/SharedMemoryReplay'
import { SourceDiversityPanel } from '@/components/swarm/SourceDiversityPanel'
import { TrustEvolution } from '@/components/swarm/TrustEvolution'
import { useDemoSSE } from '@/hooks/useDemoSSE'
import type { CognitiveReplay, ConsensusPoint, DemoEvent, DemoReplay, StartDemoResponse, TrustRecord } from '@/types/swarmDemo'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'

export default function SwarmDemo() {
  const initialSession = new URLSearchParams(window.location.search).get('session')
  const [sessionId, setSessionId] = useState<string | null>(initialSession)
  const [session, setSession] = useState<StartDemoResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState<string | null>(null)
  const [cognitiveReplay, setCognitiveReplay] = useState<CognitiveReplay | null>(null)
  const [replayWindow, setReplayWindow] = useState<DemoEvent[] | null>(null)
  const [replayIndex, setReplayIndex] = useState(0)
  const { events, status, setEvents } = useDemoSSE(sessionId)
  const visibleEvents = replayWindow ?? events

  const handleReplayFrame = useCallback((frame: DemoEvent[] | null, index: number) => {
    setReplayWindow(frame)
    setReplayIndex(index)
  }, [])

  useEffect(() => {
    if (!sessionId) {
      fetch(`${API_BASE_URL}/api/swarm/demo/latest`)
        .then((response) => response.json())
        .then((data: { session_id: string | null }) => {
          if (data.session_id) setSessionId(data.session_id)
        })
        .catch(() => undefined)
    }
  }, [sessionId])

  useEffect(() => {
    if (!sessionId) return
    fetch(`${API_BASE_URL}/api/swarm/demo/replay/${sessionId}/cognitive`)
      .then((response) => (response.ok ? response.json() : null))
      .then((data: CognitiveReplay | null) => {
        if (data) setCognitiveReplay(data)
      })
      .catch(() => undefined)
  }, [sessionId])

  const timeline = useMemo(() => {
    const latestVisible = visibleEvents.reduce<Record<string, DemoEvent>>((acc, event) => {
      acc[event.type] = event
      return acc
    }, {})
    const event = latestVisible['consensus.updated']
    const payload = event?.payload as { timeline?: ConsensusPoint[] } | undefined
    return payload?.timeline ?? []
  }, [visibleEvents])

  const trust = useMemo(() => {
    const latestVisible = visibleEvents.reduce<Record<string, DemoEvent>>((acc, event) => {
      acc[event.type] = event
      return acc
    }, {})
    const event = latestVisible['trust.updated']
    const payload = event?.payload as { all_trust?: Record<string, TrustRecord> } | undefined
    return payload?.all_trust ?? {}
  }, [visibleEvents])

  const latestVisibleByType = useMemo(() => {
    return visibleEvents.reduce<Record<string, DemoEvent>>((acc, event) => {
      acc[event.type] = event
      return acc
    }, {})
  }, [visibleEvents])

  const started = latestVisibleByType['session.started']?.payload as unknown as StartDemoResponse | undefined
  const completed = latestVisibleByType['session.completed']?.payload as
    | { decision?: string; confidence?: number; replay?: string }
    | undefined
  const activeReplayEvent = cognitiveReplay?.events[Math.min(replayIndex, Math.max(0, cognitiveReplay.events.length - 1))] ?? null

  async function startDemo() {
    setLoading(true)
    setMessage(null)
    try {
      const response = await fetch(`${API_BASE_URL}/api/swarm/demo/run`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ seed: Math.floor(Math.random() * 900000) + 1 }),
      })
      if (!response.ok) throw new Error(`HTTP ${response.status}`)
      const data = (await response.json()) as StartDemoResponse
      setSession(data)
      setSessionId(data.session_id)
      setCognitiveReplay(null)
      setReplayWindow(null)
      window.history.replaceState(null, '', `/swarm-demo?session=${data.session_id}`)
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'No se pudo iniciar la demo')
    } finally {
      setLoading(false)
    }
  }

  async function loadReplay() {
    if (!sessionId) return
    setLoading(true)
    setMessage(null)
    try {
      const response = await fetch(`${API_BASE_URL}/api/swarm/demo/replay/${sessionId}`)
      if (!response.ok) throw new Error(`HTTP ${response.status}`)
      const replay = (await response.json()) as DemoReplay
      setEvents(replay.events)
      setReplayWindow(null)
      const cognitiveResponse = await fetch(`${API_BASE_URL}/api/swarm/demo/replay/${sessionId}/cognitive`)
      if (cognitiveResponse.ok) {
        setCognitiveReplay((await cognitiveResponse.json()) as CognitiveReplay)
      }
      setMessage(`Replay cargado: ${replay.events.length} eventos`)
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'No se pudo cargar replay')
    } finally {
      setLoading(false)
    }
  }

  const student = session?.student ?? started?.student
  const module = session?.module ?? started?.module

  return (
    <main className="min-h-screen bg-slate-100">
      <div className="mx-auto grid max-w-7xl gap-5 px-4 py-5 lg:grid-cols-[1fr_380px]">
        <section className="space-y-5">
          <div className="rounded-lg border bg-white p-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <h1 className="text-2xl font-bold text-slate-950">Swarm Demonstration Mode</h1>
                <p className="text-sm text-slate-600">Deliberacion visual con SSE, trust, memoria compartida y replay.</p>
              </div>
              <div className="flex items-center gap-2">
                <Button onClick={startDemo} disabled={loading}>
                  <Play className="mr-2 h-4 w-4" />
                  Run
                </Button>
                <Button variant="outline" onClick={loadReplay} disabled={loading || !sessionId}>
                  <RotateCcw className="mr-2 h-4 w-4" />
                  Replay
                </Button>
              </div>
            </div>
            <div className="mt-4 grid gap-3 md:grid-cols-3">
              <Metric icon={Signal} label="SSE" value={status} />
              <Metric icon={Database} label="Session" value={sessionId ?? 'waiting'} />
              <Metric
                icon={CheckCircle}
                label="Decision"
                value={completed?.decision ? `${completed.decision} ${(Number(completed.confidence) * 100).toFixed(0)}%` : 'deliberating'}
              />
            </div>
            {message && <p className="mt-3 rounded-md bg-slate-50 p-2 text-sm text-slate-700">{message}</p>}
          </div>

          <div className="grid gap-5 xl:grid-cols-2">
            <ReplayControls
              events={events}
              onFrame={handleReplayFrame}
            />
            <CognitiveReplayView replay={cognitiveReplay} activeEvent={activeReplayEvent} />
          </div>

          <div className="grid gap-5 xl:grid-cols-[1.1fr_0.9fr]">
            <ReplayTimeline events={cognitiveReplay?.events ?? []} activeIndex={replayIndex} />
            <div className="grid gap-5">
              <DeliberationReplay events={(cognitiveReplay?.events ?? []).slice(0, replayIndex + 1)} />
              <SharedMemoryReplay events={(cognitiveReplay?.events ?? []).slice(0, replayIndex + 1)} />
            </div>
          </div>

          <div className="grid gap-5 xl:grid-cols-2">
            <RetrievalTimeline events={visibleEvents} />
            <SourceDiversityPanel events={visibleEvents} />
          </div>

          <div className="grid gap-5 xl:grid-cols-[1.05fr_0.95fr]">
            <PedagogicalStructurePanel events={visibleEvents} />
            <BloomProgressionView events={visibleEvents} />
          </div>

          <div className="grid gap-5 xl:grid-cols-2">
            <PromptGroundingPanel events={visibleEvents} />
            <ContradictionViewer events={visibleEvents} />
          </div>

          <SandboxValidationPanel events={visibleEvents} />

          <div className="grid gap-5 xl:grid-cols-2">
            <ConsensusTimeline timeline={timeline} />
            <TrustEvolution trust={trust} />
          </div>

          <NarrativeConsistencyPanel events={visibleEvents} />

          <section className="rounded-lg border bg-white p-4">
            <h2 className="mb-3 text-base font-semibold text-slate-950">Explainable Context</h2>
            <div className="grid gap-3 md:grid-cols-2">
              <pre className="overflow-auto rounded-md bg-slate-50 p-3 text-xs text-slate-700">
                {JSON.stringify(student ?? { status: 'waiting for synthetic student' }, null, 2)}
              </pre>
              <pre className="overflow-auto rounded-md bg-slate-50 p-3 text-xs text-slate-700">
                {JSON.stringify(module ?? { status: 'waiting for synthetic module' }, null, 2)}
              </pre>
            </div>
          </section>
        </section>

        <LiveSessionFeed events={visibleEvents} />
      </div>
    </main>
  )
}

interface MetricProps {
  icon: LucideIcon
  label: string
  value: string
}

function Metric({ icon: Icon, label, value }: MetricProps) {
  return (
    <div className="rounded-md border bg-slate-50 p-3">
      <div className="flex items-center gap-2 text-xs font-medium uppercase text-slate-500">
        <Icon className="h-4 w-4" />
        {label}
      </div>
      <p className="mt-2 truncate text-sm font-semibold text-slate-950">{value}</p>
    </div>
  )
}
