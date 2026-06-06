import axios, { type AxiosError, type InternalAxiosRequestConfig } from 'axios'
import { isTokenExpired } from '@/lib/jwt'
import { useAuthStore } from '@/stores/authStore'

const API_BASE_URL = import.meta.env.VITE_API_URL || ''

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: { 'Content-Type': 'application/json' },
  timeout: 30000,
})

let isRefreshing = false
let pendingRequests: Array<{
  resolve: (token: string) => void
  reject: (error: unknown) => void
}> = []

function clearPendingRequests(error: unknown) {
  pendingRequests.forEach((p) => p.reject(error))
  pendingRequests = []
}

function processPendingRequests(token: string) {
  pendingRequests.forEach((p) => p.resolve(token))
  pendingRequests = []
}

api.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = useAuthStore.getState().token
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error),
)

api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    if (axios.isCancel(error)) return Promise.reject(error)

    const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean }

    if (!error.response) {
      return Promise.reject(error)
    }

    if (error.response.status === 401 && !originalRequest._retry) {
      // NEVER retry auth endpoints — login 401 is a real credential error,
      // and retrying /api/auth/refresh creates an infinite deadlock
      if (originalRequest.url?.includes('/api/auth/')) {
        return Promise.reject(error)
      }

      if (isRefreshing) {
        return new Promise<string>((resolve, reject) => {
          pendingRequests.push({ resolve, reject })
        }).then((token) => {
          originalRequest.headers.Authorization = `Bearer ${token}`
          return api(originalRequest)
        })
      }

      originalRequest._retry = true
      isRefreshing = true

      try {
        // Use a direct axios call to bypass the interceptor entirely
        // This prevents the refresh request from creating a deadlock
        const refreshToken = useAuthStore.getState().refreshToken
        if (!refreshToken) {
          throw new Error('No refresh token available')
        }

        // Verificar si el refresh token ya expiró localmente
        // para evitar el POST innecesario que genera un 401 en consola
        if (isTokenExpired(refreshToken)) {
          useAuthStore.getState().logout()
          window.location.href = '/login'
          return Promise.reject(new Error('Refresh token expired'))
        }

        const controller = new AbortController()
        const timeoutId = setTimeout(() => controller.abort(), 10000)

        const resp = await axios.post(
          `${API_BASE_URL}/api/auth/refresh`,
          { refresh_token: refreshToken },
          {
            headers: { 'Content-Type': 'application/json' },
            signal: controller.signal,
          },
        )
        clearTimeout(timeoutId)

        const { access_token, refresh_token: newRefreshToken, user } = resp.data
        const store = useAuthStore.getState()
        store.login(access_token, newRefreshToken, user || store.user!)
        processPendingRequests(access_token)
        originalRequest.headers.Authorization = `Bearer ${access_token}`
        return api(originalRequest)
      } catch (refreshError: unknown) {
        clearPendingRequests(refreshError)
        const axiosError = refreshError as AxiosError
        if (axiosError.response?.status === 401 || axiosError.response?.status === 403) {
          useAuthStore.getState().logout()
          window.location.href = '/login'
        }
        return Promise.reject(refreshError)
      } finally {
        isRefreshing = false
        if (pendingRequests.length > 0) {
          const token = useAuthStore.getState().token
          if (token) {
            const orphaned = pendingRequests.splice(0)
            orphaned.forEach((p) => p.resolve(token))
          } else {
            clearPendingRequests(new Error('Session expired'))
          }
        }
      }
    }

    return Promise.reject(error)
  },
)

export default api
