import { useQuery, useMutation } from '@tanstack/react-query'
import api from '@/lib/api'
import { getErrorMessage } from '@/lib/errors'
import { useToast } from '@/hooks/use-toast'
import type {
  EngagementSession,
  InteractRequest,
  InteractResponse,
  CompleteRequest,
  CompleteResponse,
} from '@/types/engagement'

/**
 * Fetches (or creates) the Engage session for a module.
 * Backend is idempotent: returns the same session on repeated calls.
 * staleTime=Infinity prevents auto-refetch — the session is server-managed.
 */
export function useStartEngagement(moduleId: string | undefined) {
  return useQuery({
    queryKey: ['engagement-session', moduleId],
    queryFn: async () => {
      const resp = await api.get<EngagementSession>('/api/engagement/start', {
        params: { module_id: moduleId },
        timeout: 30_000,
      })
      return resp.data
    },
    enabled: !!moduleId,
    staleTime: Infinity,
    retry: 1,
  })
}

/**
 * Records a student interaction with a single Engage resource.
 * Returns XP delta, running total, correctness (for quizzes), and any badge earned.
 */
export function useInteractEngagement() {
  const { toast } = useToast()

  return useMutation({
    mutationFn: async (req: InteractRequest) => {
      const resp = await api.post<InteractResponse>('/api/engagement/interact', req)
      return resp.data
    },
    onError: (error) => {
      toast({
        variant: 'destructive',
        title: 'Error al registrar interacción',
        description: getErrorMessage(error),
      })
    },
  })
}

/**
 * Closes the Engage session (completed or skipped).
 * Returns final XP, breakdown, and full badge list earned during the session.
 */
export function useCompleteEngagement() {
  const { toast } = useToast()

  return useMutation({
    mutationFn: async (req: CompleteRequest) => {
      const resp = await api.post<CompleteResponse>('/api/engagement/complete', req)
      return resp.data
    },
    onError: (error) => {
      toast({
        variant: 'destructive',
        title: 'Error al completar fase Engage',
        description: getErrorMessage(error),
      })
    },
  })
}
