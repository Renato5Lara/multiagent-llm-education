/* eslint-disable react-refresh/only-export-components */
import { createContext, useContext, useCallback, useEffect, useRef, useState, type ReactNode } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import api from '@/lib/api'
import { isTokenExpired } from '@/lib/jwt'
import { useAuthStore } from '@/stores/authStore'
import type { UserAuth } from '@/types/auth'

interface AuthContextValue {
  isReady: boolean
  isValidating: boolean
  token: string | null
  user: UserAuth | null
  isAuthenticated: boolean
}

const AuthContext = createContext<AuthContextValue>({
  isReady: false,
  isValidating: true,
  token: null,
  user: null,
  isAuthenticated: false,
})

export function useAuthContext() {
  return useContext(AuthContext)
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const {
    token,
    user,
    isAuthenticated,
    _hydrated,
    logout: storeLogout,
    setUser,
  } = useAuthStore()

  const [isValidating, setIsValidating] = useState(false)
  const [isReady, setIsReady] = useState(false)
  const validatingRef = useRef(false)
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const validateSession = useCallback(async () => {
    const stored = useAuthStore.getState()
    if (!stored.token) {
      setIsValidating(false)
      setIsReady(true)
      return
    }

    // Si ambos tokens están expirados, hacemos logout inmediato
    // sin contactar al servidor (evita los 401 innecesarios en consola)
    if (isTokenExpired(stored.token) && isTokenExpired(stored.refreshToken)) {
      storeLogout()
      queryClient.clear()
      setIsValidating(false)
      setIsReady(true)
      return
    }

    if (validatingRef.current) return
    validatingRef.current = true
    setIsValidating(true)

    try {
      const resp = await api.get<UserAuth>('/api/auth/me')
      setUser(resp.data)
    } catch {
      storeLogout()
      queryClient.clear()
    } finally {
      validatingRef.current = false
      setIsValidating(false)
      setIsReady(true)
    }
  }, [setUser, storeLogout, queryClient])

  // Validate when hydration completes AND token exists
  useEffect(() => {
    if (_hydrated && !!useAuthStore.getState().token) {
      const timer = window.setTimeout(() => {
        validateSession()
      }, 0)
      return () => window.clearTimeout(timer)
    } else if (_hydrated && !useAuthStore.getState().token) {
      const timer = window.setTimeout(() => {
        setIsReady(true)
      }, 0)
      return () => window.clearTimeout(timer)
    }
  }, [_hydrated, validateSession])

  // Validate when token appears (e.g. login in another tab)
  useEffect(() => {
    if (_hydrated && token && !validatingRef.current) {
      validateSession()
    }
    // Only run when token changes
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, _hydrated])

  // Multi-tab sync: react to storage changes from other tabs
  useEffect(() => {
    const handleStorageChange = (e: StorageEvent) => {
      if (e.key !== 'upao-auth') return

      if (!e.newValue) {
        // Auth data cleared in another tab → logout
        storeLogout()
        queryClient.clear()
        navigate('/login')
      } else {
        // Auth data changed (login in another tab) → re-validate
        try {
          const parsed = JSON.parse(e.newValue)
          if (parsed?.state?.token && parsed?.state?.token !== token) {
            validateSession()
          }
        } catch {
          // ignore parse errors
        }
      }
    }
    window.addEventListener('storage', handleStorageChange)
    return () => window.removeEventListener('storage', handleStorageChange)
  }, [storeLogout, queryClient, navigate, token, validateSession])

  return (
    <AuthContext.Provider
      value={{
        isReady,
        isValidating,
        token,
        user,
        isAuthenticated,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}
