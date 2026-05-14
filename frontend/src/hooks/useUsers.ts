import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import api, { getErrorMessage } from '@/lib/api'
import type { User, UserCreate, UserUpdate, UserListResponse } from '@/types/user'
import type { UserRole } from '@/types/auth'
import { useToast } from '@/hooks/use-toast'

interface UseUsersParams {
    page?: number
    size?: number
    role?: UserRole | null
    search?: string
}

export function useUsers({ page = 1, size = 20, role = null }: UseUsersParams = {}) {
    return useQuery({
        queryKey: ['users', { page, size, role }],
        queryFn: async () => {
            const params: Record<string, string | number> = { page, size }
            if (role) params.role = role
            const resp = await api.get<UserListResponse>('/api/users', { params })
            return resp.data
        },
    })
}

export function useUser(id: string | undefined) {
    return useQuery({
        queryKey: ['users', id],
        queryFn: async () => {
            const resp = await api.get<User>(`/api/users/${id}`)
            return resp.data
        },
        enabled: !!id,
    })
}

export function useCreateUser() {
    const queryClient = useQueryClient()
    const { toast } = useToast()

    return useMutation({
        mutationFn: async (data: UserCreate) => {
            const resp = await api.post<User>('/api/users', data)
            return resp.data
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['users'] })
            toast({ title: 'Usuario creado exitosamente' })
        },
        onError: (error) => {
            toast({ variant: 'destructive', title: 'Error al crear usuario', description: getErrorMessage(error) })
        },
    })
}

export function useUpdateUser() {
    const queryClient = useQueryClient()
    const { toast } = useToast()

    return useMutation({
        mutationFn: async ({ id, data }: { id: string; data: UserUpdate }) => {
            const resp = await api.put<User>(`/api/users/${id}`, data)
            return resp.data
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['users'] })
            toast({ title: 'Usuario actualizado exitosamente' })
        },
        onError: (error) => {
            toast({ variant: 'destructive', title: 'Error al actualizar', description: getErrorMessage(error) })
        },
    })
}

export function useDeleteUser() {
    const queryClient = useQueryClient()
    const { toast } = useToast()

    return useMutation({
        mutationFn: async (id: string) => {
            const resp = await api.delete<User>(`/api/users/${id}`)
            return resp.data
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['users'] })
            toast({ title: 'Usuario desactivado exitosamente' })
        },
        onError: (error) => {
            toast({ variant: 'destructive', title: 'Error al desactivar', description: getErrorMessage(error) })
        },
    })
}

export function useChangeUserRole() {
    const queryClient = useQueryClient()
    const { toast } = useToast()

    return useMutation({
        mutationFn: async ({ id, role }: { id: string; role: UserRole }) => {
            const resp = await api.patch<User>(`/api/users/${id}/role`, { role })
            return resp.data
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['users'] })
            toast({ title: 'Rol actualizado exitosamente' })
        },
        onError: (error) => {
            toast({ variant: 'destructive', title: 'Error al cambiar rol', description: getErrorMessage(error) })
        },
    })
}

export function useBulkUploadUsers() {
    const queryClient = useQueryClient()
    const { toast } = useToast()

    return useMutation({
        mutationFn: async (file: File) => {
            const formData = new FormData()
            formData.append('file', file)
            const resp = await api.post('/api/users/bulk', formData, {
                headers: { 'Content-Type': 'multipart/form-data' },
            })
            return resp.data
        },
        onSuccess: (data) => {
            queryClient.invalidateQueries({ queryKey: ['users'] })
            toast({
                title: 'Carga masiva completada',
                description: `${data.success} usuarios creados, ${data.errors?.length || 0} errores`,
            })
        },
        onError: (error) => {
            toast({ variant: 'destructive', title: 'Error en carga masiva', description: getErrorMessage(error) })
        },
    })
}
