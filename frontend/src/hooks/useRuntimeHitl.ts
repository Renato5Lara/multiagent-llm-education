import { useMutation, useQueryClient } from '@tanstack/react-query'
import api from '@/lib/api'

// RFC-0009 §2, entrada 2 (E3, RFC-0010 §1) — juicio espontáneo del
// docente: reutiliza el mismo mecanismo de facts que un hecho estudiantil,
// solo con provenance=humano (invisible aquí, lo fija el backend).
export function useHechoDocente(sessionId: string | undefined) {
    const queryClient = useQueryClient()
    return useMutation({
        mutationFn: async (input: { contenido: Record<string, unknown>; human_reason?: string }) => {
            const resp = await api.post(`/api/runtime/sessions/${sessionId}/hechos-docente`, input)
            return resp.data
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['runtime', 'traza', sessionId] })
            queryClient.invalidateQueries({ queryKey: ['runtime', 'estado', sessionId] })
            queryClient.invalidateQueries({ queryKey: ['runtime', 'replay', sessionId] })
            queryClient.invalidateQueries({ queryKey: ['runtime', 'escaladas', sessionId] })
        },
    })
}

// RFC-0009 §2.1/§3, entrada 1 (E3) — la autoridad humana cierra una
// deliberación escalada. El backend responde 422 (ValueError del
// Boundary) si la escalada no existe, ya fue resuelta, o el claim no es
// uno de sus participantes (P15).
export function useResolverEscalada(sessionId: string | undefined) {
    const queryClient = useQueryClient()
    return useMutation({
        mutationFn: async (input: {
            escalada_id: string
            claim_elegido: string
            human_reason?: string
        }) => {
            const resp = await api.post(
                `/api/runtime/sessions/${sessionId}/escaladas/resolver`,
                input,
            )
            return resp.data
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['runtime', 'traza', sessionId] })
            queryClient.invalidateQueries({ queryKey: ['runtime', 'estado', sessionId] })
            queryClient.invalidateQueries({ queryKey: ['runtime', 'replay', sessionId] })
            queryClient.invalidateQueries({ queryKey: ['runtime', 'escaladas', sessionId] })
        },
    })
}
