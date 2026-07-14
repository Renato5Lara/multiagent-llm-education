import { useQuery } from '@tanstack/react-query'
import api from '@/lib/api'

// Refleja EventoOut / PasoTrazaOut de app/api/routes/runtime.py — vocabulario
// del runtime, sin traducir (RFC-0010 regla 2). `tipo` es uno de los 7
// Domain Events de kernel/events/events.py (RFC-0003 §4, INV-10).
export interface RuntimeEvento {
    tipo: string
    datos: Record<string, unknown>
}

export interface RuntimePasoTraza {
    transicion: number
    eventos: RuntimeEvento[]
}

// Única fuente: GET /api/runtime/sessions/{id}/traza (RFC-0007 §2.1, S3).
// `refetchIntervalMs` es opcional: sin él, comportamiento idéntico al previo
// (una sola lectura). Con él, repoll mientras el componente lo pida — lo usa
// la deliberación en vivo (useLiveDeliberation) durante una espera real.
export function useRuntimeTrace(sessionId: string | undefined, refetchIntervalMs?: number) {
    return useQuery({
        queryKey: ['runtime', 'traza', sessionId],
        queryFn: async () => {
            const resp = await api.get<RuntimePasoTraza[]>(
                `/api/runtime/sessions/${encodeURIComponent(sessionId ?? '')}/traza`,
            )
            return resp.data
        },
        enabled: !!sessionId,
        refetchInterval: refetchIntervalMs,
    })
}
