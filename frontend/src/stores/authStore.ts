import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { UserAuth } from '@/types/auth'

interface AuthState {
  user: UserAuth | null
  token: string | null
  isAuthenticated: boolean
  _hydrated: boolean
}

interface AuthActions {
  login: (token: string, user: UserAuth) => void
  logout: () => void
  setUser: (user: UserAuth) => void
  setHydrated: () => void
}

type AuthStore = AuthState & AuthActions

export const useAuthStore = create<AuthStore>()(
  persist(
    (set) => ({
      user: null,
      token: null,
      isAuthenticated: false,
      _hydrated: false,

      login: (token, user) =>
        set({ token, user, isAuthenticated: true }),

      logout: () => {
        set({ token: null, user: null, isAuthenticated: false })
      },

      setUser: (user) =>
        set({ user }),

      setHydrated: () =>
        set({ _hydrated: true }),
    }),
    {
      name: 'upao-auth',
      partialize: (state) => ({
        token: state.token,
        user: state.user,
        isAuthenticated: state.isAuthenticated,
      }),
      onRehydrateStorage: () => (state) => {
        if (state) state.setHydrated()
      },
    },
  ),
)
