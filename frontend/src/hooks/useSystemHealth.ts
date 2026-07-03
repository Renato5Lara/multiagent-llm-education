import { useQuery } from '@tanstack/react-query'
import api from '@/lib/api'

export interface SystemHealth {
    status: 'ok' | 'degraded' | string
    database: string
    tavily: 'available' | 'missing'
    openai: 'available' | 'missing'
    modalities: string[]
    timestamp: string
    version: string
    env: string
}

// Reutiliza GET /health (backend/app/main.py) — no duplica lógica de estado.
export function useSystemHealth() {
    return useQuery({
        queryKey: ['system', 'health'],
        queryFn: async () => {
            const resp = await api.get<SystemHealth>('/health')
            return resp.data
        },
        staleTime: 15 * 1000,
        refetchInterval: 30 * 1000,
    })
}
