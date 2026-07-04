import { useAuthStore } from '@/stores/authStore'
import { getRoleLabel } from '@/lib/utils'
import UserDropdown from '@/components/common/UserDropdown'
import { cn } from '@/lib/utils'

const ROLE_COLORS: Record<string, string> = {
  admin:         'border-neural-glow/40 text-neural-glow bg-neural-glow/[0.06]',
  docente:       'border-neural-violet/40 text-neural-violet bg-neural-violet/[0.06]',
  estudiante:    'border-neural-pulse/40 text-neural-pulse bg-neural-pulse/[0.06]',
}

export default function Header() {
  const { user } = useAuthStore()

  if (!user) return null

  const roleColor = ROLE_COLORS[user.role] ?? 'border-white/20 text-neural-muted bg-white/[0.04]'

  return (
    <header className="sticky top-0 z-20 h-14 glass-panel border-b border-white/[0.06] flex items-center justify-between px-6">
      {/* Spacer — el buscador global se retiró (no era funcional) */}
      <div className="flex-1" />

      <div className="flex items-center gap-3">
        {/* System status dot */}
        <div className="hidden sm:flex items-center gap-2 px-2.5 py-1.5 rounded-md bg-neural-surface/60 border border-white/[0.06]">
          <span className="relative flex h-1.5 w-1.5">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-neural-pulse opacity-75" />
            <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-neural-pulse" />
          </span>
          <span className="text-[10px] font-mono text-neural-muted tracking-widest uppercase">
            Sistema Activo
          </span>
        </div>

        {/* Role badge */}
        <div className={cn('px-2.5 py-1 rounded-md border text-[11px] font-semibold tracking-wide uppercase font-mono', roleColor)}>
          {getRoleLabel(user.role)}
        </div>

        <UserDropdown />
      </div>
    </header>
  )
}
