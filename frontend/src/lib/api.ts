import axios from 'axios'
import { useAuthStore } from '@/stores/authStore'

const API_BASE_URL = import.meta.env.VITE_API_URL || ''

const api = axios.create({
    baseURL: API_BASE_URL,
    headers: {
        'Content-Type': 'application/json',
    },
})

// Request interceptor: attach JWT token
api.interceptors.request.use(
    (config) => {
        const token = useAuthStore.getState().token
        if (token) {
            config.headers.Authorization = `Bearer ${token}`
        }
        return config
    },
    (error) => Promise.reject(error)
)

// Response interceptor: handle 401 globally
api.interceptors.response.use(
    (response) => response,
    (error) => {
        if (error.response?.status === 401) {
            useAuthStore.getState().logout()
            window.location.href = '/login'
        }
        return Promise.reject(error)
    }
)

export default api

/**
 * Extrae el mensaje de error de una respuesta Axios en español.
 */
export function getErrorMessage(error: unknown): string {
    if (axios.isAxiosError(error)) {
        const detail = error.response?.data?.detail
        if (typeof detail === 'string') return detail
        if (Array.isArray(detail)) return detail.map((d: { msg?: string }) => d.msg).join(', ')
        if (error.response?.status === 404) return 'Recurso no encontrado'
        if (error.response?.status === 403) return 'No tiene permisos para realizar esta acción'
        if (error.response?.status === 409) return 'Ya existe un registro con esos datos'
        if ((error.response?.status ?? 0) >= 500) return 'Error interno del servidor. Intente de nuevo más tarde'
    }
    return 'Ocurrió un error inesperado'
}
