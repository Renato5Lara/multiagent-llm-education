import { useQuery } from '@tanstack/react-query'
import api from '@/lib/api'

// Refleja MemoriaOut de app/api/routes/runtime.py — la versión de
// memoria que ESTA sesión tiene fijada (RFC-0005 §2), nunca "la más
// reciente" del estudiante.
export interface RuntimeMemoria {
    student_id: string
    session_id: string
    catalogo: Record<string, unknown>
}

// Única fuente: GET /api/runtime/sessions/{id}/memoria (RFC-0005 §2, S3).
// `null` es un estado válido (RFC-0005 §1.1, N=0): sin memoria consolidada.
export function useRuntimeMemoria(sessionId: string | undefined) {
    return useQuery({
        queryKey: ['runtime', 'memoria', sessionId],
        queryFn: async () => {
            const resp = await api.get<RuntimeMemoria | null>(
                `/api/runtime/sessions/${sessionId}/memoria`,
            )
            return resp.data
        },
        enabled: !!sessionId,
    })
}
