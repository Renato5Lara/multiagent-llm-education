import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { useEffect } from 'react'
import api, { getErrorMessage } from '@/lib/api'
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
            storeLogin(data.access_token, data.user)
            queryClient.clear()
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
    })

    useEffect(() => {
        if (meQuery.data) {
            setUser(meQuery.data)
        }
    }, [meQuery.data, setUser])

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
