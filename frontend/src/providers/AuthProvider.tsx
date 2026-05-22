import { createContext, useContext, useCallback, useEffect, useRef, useState, type ReactNode } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import api from '@/lib/api'
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
    logout: storeLogout,
    setUser,
  } = useAuthStore()

  const [isValidating, setIsValidating] = useState(() => !!token)
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

    if (validatingRef.current) return
    validatingRef.current = true

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

  useEffect(() => {
    validateSession()
  }, [validateSession])

  useEffect(() => {
    const handleStorageChange = (e: StorageEvent) => {
      if (e.key === 'upao-auth' && !e.newValue) {
        storeLogout()
        queryClient.clear()
        navigate('/login')
      }
    }
    window.addEventListener('storage', handleStorageChange)
    return () => window.removeEventListener('storage', handleStorageChange)
  }, [storeLogout, queryClient, navigate])

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
