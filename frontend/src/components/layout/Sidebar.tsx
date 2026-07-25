import { useState, useEffect } from 'react'
import { NavLink } from 'react-router-dom'
import { cn } from '@/lib/utils'
import { Menu, X, type LucideIcon } from 'lucide-react'

export interface SidebarItem {
  label: string
  href: string
  icon: LucideIcon
  disabled?: boolean
  sectionBefore?: boolean
}

interface SidebarProps {
  items: SidebarItem[]
  title?: string
  subtitle?: string
}

export default function Sidebar({
  items,
  title = 'UPAO-MAS-EDU',
  subtitle = 'Swarm Intelligence Platform',
}: SidebarProps) {
  const [isOpen, setIsOpen] = useState(false)

  useEffect(() => {
    document.body.style.overflow = isOpen ? 'hidden' : ''
    return () => { document.body.style.overflow = '' }
  }, [isOpen])

  return (
    <>
      {/* Mobile toggle */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="fixed top-4 left-4 z-50 lg:hidden p-2 rounded-lg glass-panel text-neural-glow shadow-lg transition-colors"
        aria-label={isOpen ? 'Cerrar menú' : 'Abrir menú'}
      >
        {isOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
      </button>

      {/* Mobile backdrop */}
      {isOpen && (
        <div
          className="fixed inset-0 z-30 bg-black/60 backdrop-blur-sm lg:hidden"
          onClick={() => setIsOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={cn(
          'fixed inset-y-0 left-0 z-40 w-64 flex flex-col transition-transform duration-300',
          'bg-neural-lowest border-r border-white/[0.06]',
          'lg:translate-x-0',
          isOpen ? 'translate-x-0' : '-translate-x-full',
        )}
      >
        {/* Hex pattern overlay */}
        <div className="absolute inset-0 hex-bg opacity-40 pointer-events-none" />

        {/* Brand header — Épica D: la marca de la plataforma usa neural-brand
            (violeta), no neural-glow (reservado a estado en vivo/ejecución) —
            ver tabla semántica en ENGINEERING-GATE-EPICA-D.md. */}
        <div className="relative z-10 h-16 flex items-center px-5 border-b border-white/[0.06]">
          <div className="flex items-center gap-3 min-w-0">
            <div className="w-8 h-8 rounded-lg bg-neural-brand/10 border border-neural-brand/30 flex items-center justify-center flex-shrink-0 glow-brand">
              <svg viewBox="0 0 24 24" className="w-4 h-4 text-neural-brand-bright fill-current">
                <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 14H9V8h2v8zm4 0h-2V8h2v8z" />
              </svg>
            </div>
            <div className="min-w-0">
              <p className="text-neural-text font-semibold text-sm leading-tight tracking-tight truncate">
                {title}
              </p>
              <p className="text-neural-brand-bright/70 text-[9px] leading-tight tracking-[0.12em] uppercase font-mono truncate">
                {subtitle}
              </p>
            </div>
          </div>
        </div>

        {/* Nav */}
        <nav className="relative z-10 flex-1 py-4 px-3 space-y-0.5 overflow-y-auto scrollbar-thin">
          {items.map((item) => (
            <div key={item.label}>
              {item.sectionBefore && (
                <div className="mx-3 my-2 border-t border-white/[0.06]" />
              )}
              {item.disabled ? (
                <div className={cn(
                  'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium',
                  'border-l-2 border-transparent',
                  'text-neural-muted/40 cursor-not-allowed select-none',
                )}>
                  <item.icon className="h-4 w-4 flex-shrink-0 text-neural-muted/30" />
                  <span className="truncate">{item.label}</span>
                  <span className="ml-auto text-[9px] font-mono text-neural-muted/30 tracking-wider">PRONTO</span>
                </div>
              ) : (
                <NavLink
                  to={item.href}
                  end={item.href.split('/').length <= 2}
                  onClick={() => setIsOpen(false)}
                  className={({ isActive }) =>
                    cn(
                      'group flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-150',
                      'border-l-2',
                      // Épica D: "dónde estás parado" es navegación/marca
                      // (neural-brand), no un estado en vivo del sistema —
                      // neural-glow queda reservado a ejecución/streaming.
                      isActive
                        ? 'bg-neural-brand/[0.1] text-neural-brand-bright border-neural-brand glow-brand'
                        : 'text-neural-muted hover:text-neural-text hover:bg-white/[0.04] border-transparent',
                    )
                  }
                >
                  {({ isActive }) => (
                    <>
                      <item.icon
                        className={cn(
                          'h-4 w-4 flex-shrink-0 transition-colors duration-150',
                          isActive ? 'text-neural-brand-bright' : 'text-neural-muted group-hover:text-neural-text',
                        )}
                      />
                      <span className="truncate">{item.label}</span>
                      {isActive && (
                        <span className="ml-auto w-1.5 h-1.5 rounded-full bg-neural-brand flex-shrink-0" />
                      )}
                    </>
                  )}
                </NavLink>
              )}
            </div>
          ))}
        </nav>

        {/* Footer */}
        <div className="relative z-10 p-4 border-t border-white/[0.06]">
          <p className="text-[10px] text-neural-muted/40 text-center tracking-widest font-mono uppercase">
            © 2026 UPAO · v1.0.0
          </p>
        </div>
      </aside>
    </>
  )
}
