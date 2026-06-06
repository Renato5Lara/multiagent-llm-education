import { useEffect, useRef, useState } from 'react'

interface ReplayEvent {
  type: string
  data: unknown
  timestamp: number
}

export function useReplaySSE(sessionId?: string) {
  const [events, setEvents] = useState<ReplayEvent[]>([])
  const [connected, setConnected] = useState(false)
  const evtSource = useRef<EventSource | null>(null)

  useEffect(() => {
    const url = sessionId
      ? `/api/observability/stream?session=${sessionId}`
      : '/api/observability/stream'
    const source = new EventSource(url)
    evtSource.current = source

    const replayTypes = [
      'replay:start', 'replay:frame', 'replay:adaptation',
      'replay:consensus', 'replay:memory', 'replay:reasoning',
      'replay:complete',
    ]

    source.onopen = () => setConnected(true)
    source.onerror = () => setConnected(false)

    for (const eventType of replayTypes) {
      source.addEventListener(eventType, (e: MessageEvent) => {
        const data = JSON.parse(e.data)
        setEvents(prev => [...prev, {
          type: eventType,
          data,
          timestamp: Date.now(),
        }])
      })
    }

    return () => {
      source.close()
      setConnected(false)
    }
  }, [sessionId])

  return { events, connected, clear: () => setEvents([]) }
}
