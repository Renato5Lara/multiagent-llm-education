import { useEffect, useMemo, useState } from 'react'
import type { DemoEvent } from '@/types/swarmDemo'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'

export function useDemoSSE(sessionId: string | null) {
  const [events, setEvents] = useState<DemoEvent[]>([])
  const [status, setStatus] = useState<'idle' | 'connecting' | 'live' | 'closed' | 'error'>('idle')

  useEffect(() => {
    const resetTimer = window.setTimeout(() => setEvents([]), 0)
    if (!sessionId) {
      const statusTimer = window.setTimeout(() => setStatus('idle'), 0)
      return () => {
        window.clearTimeout(resetTimer)
        window.clearTimeout(statusTimer)
      }
    }

    const statusTimer = window.setTimeout(() => setStatus('connecting'), 0)
    const source = new EventSource(`${API_BASE_URL}/api/swarm/demo/events/${sessionId}`)

    const handleMessage = (message: MessageEvent<string>) => {
      const event = JSON.parse(message.data) as DemoEvent
      setEvents((current) => {
        if (current.some((item) => item.id === event.id)) return current
        return [...current, event].slice(-200)
      })
      setStatus(event.type === 'session.completed' ? 'closed' : 'live')
    }

    const eventNames = [
      'session.started',
      'swarm.activated',
      'agent.thinking',
      'vote.cast',
      'memory.published',
      'trust.updated',
      'consensus.updated',
      'anomaly.detected',
      'retrieval:start',
      'retrieval:source',
      'retrieval:complete',
      'contradiction:detected',
      'misconception:detected',
      'prompt:generated',
      'sandbox:start',
      'sandbox:complete',
      'sandbox:violation',
      'consistency:validated',
      'session.completed',
    ]

    eventNames.forEach((name) => source.addEventListener(name, handleMessage as EventListener))
    source.onerror = () => setStatus((current) => (current === 'closed' ? 'closed' : 'error'))

    return () => {
      window.clearTimeout(resetTimer)
      window.clearTimeout(statusTimer)
      eventNames.forEach((name) => source.removeEventListener(name, handleMessage as EventListener))
      source.close()
    }
  }, [sessionId])

  const latestByType = useMemo(() => {
    return events.reduce<Record<string, DemoEvent>>((acc, event) => {
      acc[event.type] = event
      return acc
    }, {})
  }, [events])

  return { events, status, latestByType, setEvents }
}
