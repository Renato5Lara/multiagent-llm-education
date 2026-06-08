import { Gauge, Pause, Play, RotateCcw, SkipForward } from 'lucide-react'
import { useEffect, useMemo, useRef, useState } from 'react'
import { Button } from '@/components/ui/button'
import type { DemoEvent, ReplayMode } from '@/types/swarmDemo'

interface ReplayControlsProps {
  events: DemoEvent[]
  onFrame: (events: DemoEvent[] | null, index: number) => void
}

const speeds: Record<ReplayMode, number> = {
  realtime: 900,
  accelerated: 180,
  'step-by-step': 0,
  cognitive: 320,
}

export function ReplayControls({ events, onFrame }: ReplayControlsProps) {
  const [mode, setMode] = useState<ReplayMode>('cognitive')
  const [playing, setPlaying] = useState(false)
  const [index, setIndex] = useState(events.length ? events.length - 1 : 0)
  const timer = useRef<number | null>(null)
  const progress = events.length ? ((index + 1) / events.length) * 100 : 0

  const visibleEvents = useMemo(() => events.slice(0, Math.min(events.length, index + 1)), [events, index])

  useEffect(() => {
    const timerId = window.setTimeout(() => {
      setIndex(events.length ? events.length - 1 : 0)
      setPlaying(false)
    }, 0)
    return () => window.clearTimeout(timerId)
  }, [events.length])

  useEffect(() => {
    onFrame(visibleEvents.length ? visibleEvents : null, index)
  }, [index, visibleEvents, onFrame])

  useEffect(() => {
    if (!playing || mode === 'step-by-step') return
    timer.current = window.setInterval(() => {
      setIndex((current) => {
        if (current >= events.length - 1) {
          setPlaying(false)
          return current
        }
        return current + 1
      })
    }, speeds[mode])
    return () => {
      if (timer.current) window.clearInterval(timer.current)
    }
  }, [playing, mode, events.length])

  function restart() {
    setIndex(0)
    setPlaying(mode !== 'step-by-step')
  }

  function step() {
    setPlaying(false)
    setIndex((current) => Math.min(events.length - 1, current + 1))
  }

  function showFull() {
    setPlaying(false)
    setIndex(Math.max(0, events.length - 1))
    onFrame(null, Math.max(0, events.length - 1))
  }

  return (
    <section className="rounded-lg border bg-white">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b px-4 py-3">
        <div>
          <h2 className="text-base font-semibold text-slate-950">Replay Controls</h2>
          <p className="text-xs text-slate-500">realtime, accelerated, step-by-step, cognitive</p>
        </div>
        <span className="flex items-center gap-1.5 text-xs font-medium text-slate-500">
          <Gauge className="h-4 w-4" />
          {events.length ? index + 1 : 0}/{events.length}
        </span>
      </div>
      <div className="grid gap-4 p-4">
        <div className="grid grid-cols-2 gap-2 md:grid-cols-4">
          {(['cognitive', 'accelerated', 'realtime', 'step-by-step'] as ReplayMode[]).map((item) => (
            <button
              key={item}
              type="button"
              onClick={() => {
                setMode(item)
                setPlaying(false)
              }}
              className={`rounded-md border px-3 py-2 text-xs font-medium ${mode === item ? 'border-primary bg-primary text-white' : 'bg-slate-50 text-slate-700'}`}
            >
              {item}
            </button>
          ))}
        </div>
        <div className="h-2.5 overflow-hidden rounded-full bg-slate-100">
          <div className="h-full rounded-full bg-primary transition-all" style={{ width: `${Math.max(2, progress)}%` }} />
        </div>
        <div className="flex flex-wrap gap-2">
          <Button onClick={() => setPlaying((current) => !current)} disabled={!events.length || mode === 'step-by-step'}>
            {playing ? <Pause className="mr-2 h-4 w-4" /> : <Play className="mr-2 h-4 w-4" />}
            {playing ? 'Pause' : 'Play'}
          </Button>
          <Button variant="outline" onClick={restart} disabled={!events.length}>
            <RotateCcw className="mr-2 h-4 w-4" />
            Restart
          </Button>
          <Button variant="outline" onClick={step} disabled={!events.length}>
            <SkipForward className="mr-2 h-4 w-4" />
            Step
          </Button>
          <Button variant="outline" onClick={showFull} disabled={!events.length}>Full session</Button>
        </div>
      </div>
    </section>
  )
}
