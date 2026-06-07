import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { useEffect } from 'react'
import api from '@/lib/api'
import { getErrorMessage } from '@/lib/errors'
import { useAuthStore } from '@/stores/authStore'
import type { LoginRequest, TokenResponse, UserAuth } from '@/types/auth'
import { useToast } from '@/hooks/use-toast'

export function useAuth() {
    const { user, token, isAuthenticated, login: storeLogin, logout: storeLogout, setUser } = useAuthStore()
    const navigate = useNavigate()
    const queryClient = useQueryClient()
    const { toast } = useToast()

    const loginMutation = useMutation({
        mutationFn: async (data: LoginRequest) => {
            const resp = await api.post<TokenResponse>('/api/auth/login', data)
            return resp.data
        },
        onSuccess: (data) => {
            storeLogin(data.access_token, data.refresh_token, data.user)
            // WARNING: do NOT call queryClient.clear() here — it wipes ALL cached
            // queries and races meQuery against validateSession, causing intermittent
            // logouts. The meQuery cache entry will naturally become stale.
            const role = data.user.role
            if (role === 'admin') navigate('/admin')
            else if (role === 'docente') navigate('/docente')
            else if (role === 'estudiante') navigate('/estudiante')
            else if (role === 'investigador') navigate('/investigador')
            else navigate('/')
        },
        onError: (error) => {
            toast({
                variant: 'destructive',
                title: 'Error de autenticación',
                description: getErrorMessage(error),
            })
        },
    })

    const logoutMutation = useMutation({
        mutationFn: async () => {
            if (token) {
                await api.post('/api/auth/logout').catch(() => {})
            }
        },
        onSettled: () => {
            storeLogout()
            queryClient.clear()
            navigate('/login')
        },
    })

    const meQuery = useQuery({
        queryKey: ['auth', 'me'],
        queryFn: async () => {
            const resp = await api.get<UserAuth>('/api/auth/me')
            const data = resp.data
            setUser(data)
            return data
        },
        enabled: isAuthenticated && !!token,
        retry: false,
        staleTime: 5 * 60 * 1000,
        throwOnError: false,
    })

    // Auto-logout when /api/auth/me returns 401 or 403 and the interceptor
    // already attempted a refresh. Prevents the broken state where the store
    // says "authenticated" but all subsequent calls will fail.
    useEffect(() => {
        if (!meQuery.error) return
        const status = (meQuery.error as { response?: { status?: number } })?.response?.status
        if (status === 401 || status === 403) {
            storeLogout()
            queryClient.clear()
            navigate('/login')
        }
    }, [meQuery.error, storeLogout, queryClient, navigate])

    // NOTE: setUser is already called inside meQuery.queryFn (line above).
    // A separate useEffect on meQuery.data would call setUser a second time.
    // We removed it to avoid double dispatch.

    const hasRole = (role: string) => user?.role === role

    return {
        user,
        token,
        isAuthenticated,
        login: loginMutation.mutate,
        loginAsync: loginMutation.mutateAsync,
        isLoggingIn: loginMutation.isPending,
        loginError: loginMutation.error,
        logout: logoutMutation.mutate,
        isLoggingOut: logoutMutation.isPending,
        meQuery,
        hasRole,
    }
}
