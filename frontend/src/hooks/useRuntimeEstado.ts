import { useQuery } from '@tanstack/react-query'
import api from '@/lib/api'

// Refleja EstadoOut de app/api/routes/runtime.py — el LearningState
// completo (RFC-0002 §1), sin proyectar ni resumir (RFC-0010 regla 2).
export interface RuntimeEntrada {
    [campo: string]: unknown
}

export interface RuntimeEstado {
    transicion: number
    facts: RuntimeEntrada[]
    claims: RuntimeEntrada[]
    deliberaciones: RuntimeEntrada[]
    decisiones: RuntimeEntrada[]
}

// Única fuente: GET /api/runtime/sessions/{id}/estado (RFC-0002 §1, S3).
export function useRuntimeEstado(sessionId: string | undefined) {
    return useQuery({
        queryKey: ['runtime', 'estado', sessionId],
        queryFn: async () => {
            const resp = await api.get<RuntimeEstado>(
                `/api/runtime/sessions/${sessionId}/estado`,
            )
            return resp.data
        },
        enabled: !!sessionId,
    })
}
