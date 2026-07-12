import { useQuery } from '@tanstack/react-query'
import api from '@/lib/api'

// Refleja EscaladaOut de app/api/routes/runtime.py — S2 (RFC-0010 §2):
// la notificación dedicada de "qué espera al docente ahora mismo", ya
// filtrada por el Boundary (solo deliberaciones Escalada sin resolver),
// no una vista derivada de /estado en el frontend.
export interface RuntimeEscalada {
    id: string
    participantes: string[]
    resultado: Record<string, unknown>
}

// Única fuente: GET /api/runtime/sessions/{id}/escaladas (RFC-0010 §2, S2).
export function useRuntimeEscaladas(sessionId: string | undefined) {
    return useQuery({
        queryKey: ['runtime', 'escaladas', sessionId],
        queryFn: async () => {
            const resp = await api.get<RuntimeEscalada[]>(
                `/api/runtime/sessions/${sessionId}/escaladas`,
            )
            return resp.data
        },
        enabled: !!sessionId,
    })
}
