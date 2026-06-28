import { useState } from 'react'
import { Navigate } from 'react-router-dom'
import { AlertTriangle, Eye, EyeOff, Loader2, Clock, Brain, Wifi } from 'lucide-react'
import axios from 'axios'
import { useAuth } from '@/hooks/useAuth'
import { useAuthStore } from '@/stores/authStore'
import { cn } from '@/lib/utils'

// ── Presentational sub-components ───────────────────────────────────────────

function NeuralInput({
  id,
  type,
  placeholder,
  value,
  onChange,
  hasError,
  autoComplete,
  autoFocus,
  children,
}: {
  id: string
  type: string
  placeholder: string
  value: string
  onChange: (e: React.ChangeEvent<HTMLInputElement>) => void
  hasError?: boolean
  autoComplete?: string
  autoFocus?: boolean
  children?: React.ReactNode
}) {
  return (
    <div className="relative group">
      <input
        id={id}
        type={type}
        placeholder={placeholder}
        value={value}
        onChange={onChange}
        autoComplete={autoComplete}
        autoFocus={autoFocus}
        className={cn(
          'w-full bg-neural-lowest/60 border-0 border-b py-3 px-4 text-sm text-neural-text placeholder:text-neural-muted/40',
          'focus:outline-none focus:ring-0 transition-colors duration-300 font-mono',
          hasError ? 'border-red-500/70' : 'border-white/10 focus:border-neural-glow/60',
        )}
      />
      {/* Animated focus underline */}
      <div className={cn(
        'absolute bottom-0 left-0 h-px bg-neural-glow transition-all duration-500',
        'w-0 group-focus-within:w-full',
      )} />
      {children}
    </div>
  )
}

function ErrorBanner({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex items-start gap-3 p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
      {children}
    </div>
  )
}

// ── Main component ───────────────────────────────────────────────────────────

export default function Login() {
  const { isAuthenticated, user } = useAuthStore()
  const { login, isLoggingIn, loginError } = useAuth()
  const [identifier, setIdentifier]     = useState('')
  const [password, setPassword]         = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [errors, setErrors] = useState<{ identifier?: string; password?: string }>({})

  if (isAuthenticated && user) {
    const home = user.role === 'admin' ? '/admin' : `/${user.role}`
    return <Navigate to={home} replace />
  }

  const validate = () => {
    const newErrors: typeof errors = {}
    if (!identifier) newErrors.identifier = 'El correo o código es obligatorio'
    if (!password) newErrors.password = 'La contraseña es obligatoria'
    else if (password.length < 6) newErrors.password = 'Mínimo 6 caracteres'
    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (validate()) login({ identifier, password })
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-neural-surface relative overflow-hidden">
      {/* Hex + dot grid background layers */}
      <div className="absolute inset-0 hex-bg opacity-60 pointer-events-none" />
      <div className="absolute inset-0 dot-grid pointer-events-none" />

      {/* Ambient glow blobs */}
      <div className="absolute top-1/4 left-1/3 w-96 h-96 bg-neural-glow/5 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute bottom-1/4 right-1/3 w-72 h-72 bg-neural-violet/5 rounded-full blur-3xl pointer-events-none" />

      {/* Card */}
      <div className="relative z-10 w-full max-w-md mx-4 glass-panel rounded-2xl p-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
        {/* Decorative corner accents */}
        <div className="absolute top-0 left-0 w-6 h-6 border-t border-l border-neural-glow/30 rounded-tl-2xl" />
        <div className="absolute bottom-0 right-0 w-6 h-6 border-b border-r border-neural-glow/30 rounded-br-2xl" />

        {/* Brand header */}
        <div className="text-center mb-8">
          <div className="relative mx-auto w-14 h-14 mb-4">
            <div className="absolute inset-0 rounded-xl bg-neural-glow/10 blur-md neural-glow-sm" />
            <div className="relative w-14 h-14 rounded-xl bg-neural-lowest border border-neural-glow/30 flex items-center justify-center">
              <Brain className="h-7 w-7 text-neural-glow" />
            </div>
          </div>
          <h1 className="text-xl font-bold text-neural-text tracking-tight">UPAO-MAS-EDU</h1>
          <p className="text-[10px] text-neural-glow/60 font-mono tracking-[0.2em] uppercase mt-1">
            Swarm Intelligence Platform
          </p>
          <p className="text-xs text-neural-muted mt-3 leading-relaxed max-w-xs mx-auto">
            Plataforma de gestión educativa basada en inteligencia de enjambre para la adaptación de contenido multimodal.
          </p>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-5">
          {/* 429 rate limit */}
          {loginError && axios.isAxiosError(loginError) && loginError.response?.status === 429 && (
            <ErrorBanner>
              <Clock className="h-4 w-4 mt-0.5 shrink-0" />
              <span>
                {(() => {
                  const detail = loginError.response?.data?.detail
                  if (typeof detail === 'object' && detail?.message) {
                    const retryAfter = detail.retry_after_seconds ?? (detail.retry_after_minutes ? detail.retry_after_minutes * 60 : null)
                    const retryText = retryAfter
                      ? retryAfter >= 120
                        ? `Intente de nuevo en ${Math.round(retryAfter / 60)} minutos.`
                        : `Intente de nuevo en ${retryAfter} segundos.`
                      : ''
                    return `${detail.message} ${retryText}`
                  }
                  if (typeof detail === 'string') return detail
                  return 'Demasiados intentos. Intente de nuevo más tarde.'
                })()}
              </span>
            </ErrorBanner>
          )}

          {/* 401 wrong credentials */}
          {loginError && axios.isAxiosError(loginError) && loginError.response?.status === 401 && (
            <ErrorBanner>
              <AlertTriangle className="h-4 w-4 mt-0.5 shrink-0" />
              <span>
                {(() => {
                  const detail = loginError.response?.data?.detail
                  if (typeof detail === 'object' && detail?.remaining_attempts !== undefined) {
                    return `Credenciales incorrectas. Intentos restantes: ${detail.remaining_attempts}`
                  }
                  return 'Credenciales incorrectas'
                })()}
              </span>
            </ErrorBanner>
          )}

          {/* Identifier */}
          <div className="space-y-1.5">
            <label htmlFor="identifier" className="text-[10px] font-mono text-neural-muted/70 tracking-widest uppercase flex items-center gap-1.5">
              Correo o código institucional
            </label>
            <NeuralInput
              id="identifier"
              type="text"
              placeholder="usuario@upao.edu.pe o 20231234"
              value={identifier}
              onChange={(e) => { setIdentifier(e.target.value); setErrors({}) }}
              hasError={!!errors.identifier}
              autoComplete="username"
              autoFocus
            />
            {errors.identifier && (
              <p className="text-xs text-red-400 font-mono">{errors.identifier}</p>
            )}
          </div>

          {/* Password */}
          <div className="space-y-1.5">
            <label htmlFor="password" className="text-[10px] font-mono text-neural-muted/70 tracking-widest uppercase">
              Contraseña
            </label>
            <NeuralInput
              id="password"
              type={showPassword ? 'text' : 'password'}
              placeholder="••••••••"
              value={password}
              onChange={(e) => { setPassword(e.target.value); setErrors({}) }}
              hasError={!!errors.password}
              autoComplete="current-password"
            >
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-neural-muted/50 hover:text-neural-muted transition-colors"
                tabIndex={-1}
              >
                {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </NeuralInput>
            {errors.password && (
              <p className="text-xs text-red-400 font-mono">{errors.password}</p>
            )}
          </div>

          {/* Submit */}
          <button
            type="submit"
            disabled={isLoggingIn}
            className={cn(
              'relative w-full h-12 rounded-lg overflow-hidden',
              'transition-all duration-300 active:scale-[0.98]',
              'disabled:opacity-60 disabled:cursor-not-allowed',
              'group',
            )}
          >
            <div className="absolute inset-0 bg-gradient-to-r from-neural-glow to-neural-violet transition-opacity duration-300" />
            <div className="absolute inset-0 opacity-0 group-hover:opacity-20 bg-white transition-opacity duration-300" />
            <span className="relative flex items-center justify-center gap-2 text-neural-surface font-semibold text-sm tracking-wide">
              {isLoggingIn ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Iniciando sesión...
                </>
              ) : (
                'Iniciar Sesión'
              )}
            </span>
          </button>
        </form>

        {/* System status + footer */}
        <div className="mt-7 pt-5 border-t border-white/[0.06] space-y-3">
          <div className="flex items-center justify-center gap-2">
            <Wifi className="h-3 w-3 text-neural-pulse" />
            <span className="text-[10px] font-mono text-neural-muted/50 tracking-widest uppercase">
              Sistema activo
            </span>
            <span className="w-1.5 h-1.5 rounded-full bg-neural-pulse animate-pulse" />
          </div>
          <p className="text-[10px] text-neural-muted/40 text-center">
            Universidad Privada Antenor Orrego · Trujillo, Perú
          </p>
        </div>
      </div>
    </div>
  )
}
