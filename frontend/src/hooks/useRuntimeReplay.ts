import { useQuery } from '@tanstack/react-query'
import api from '@/lib/api'
import type { RuntimeEstado } from '@/hooks/useRuntimeEstado'

// Refleja PasoReplayOut de app/api/routes/runtime.py — el LearningState
// completo tal como quedó DESPUÉS de cada transición (RFC-0008 §3, modo
// Reconstrucción), no solo sus eventos (eso es /traza).
export interface RuntimePasoReplay {
    transicion: number
    estado: RuntimeEstado
}

// Única fuente: GET /api/runtime/sessions/{id}/replay (RFC-0008 §3, S3).
export function useRuntimeReplay(sessionId: string | undefined) {
    return useQuery({
        queryKey: ['runtime', 'replay', sessionId],
        queryFn: async () => {
            const resp = await api.get<RuntimePasoReplay[]>(
                `/api/runtime/sessions/${sessionId}/replay`,
            )
            return resp.data
        },
        enabled: !!sessionId,
    })
}
