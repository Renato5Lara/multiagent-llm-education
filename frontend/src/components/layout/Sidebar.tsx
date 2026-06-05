import { useState, useEffect } from 'react'
import { NavLink } from 'react-router-dom'
import { cn } from '@/lib/utils'
import { Menu, X, type LucideIcon } from 'lucide-react'

export interface SidebarItem {
  label: string
  href: string
  icon: LucideIcon
}

interface SidebarProps {
  items: SidebarItem[]
  title?: string
}

export default function Sidebar({ items, title = 'UPAO-MAS-EDU' }: SidebarProps) {
  const [isOpen, setIsOpen] = useState(false)

  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden'
    } else {
      document.body.style.overflow = ''
    }
    return () => { document.body.style.overflow = '' }
  }, [isOpen])

  return (
    <>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="fixed top-4 left-4 z-50 lg:hidden p-2 rounded-lg bg-[#002550] text-white shadow-lg hover:bg-[#003D7A] transition-colors"
        aria-label={isOpen ? 'Cerrar menú' : 'Abrir menú'}
      >
        {isOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
      </button>

      {isOpen && (
        <div
          className="fixed inset-0 z-30 bg-black/50 lg:hidden"
          onClick={() => setIsOpen(false)}
        />
      )}

      <aside
        className={cn(
          'fixed inset-y-0 left-0 z-40 w-64 bg-[#002550] text-white flex flex-col shadow-xl transition-transform duration-300',
          'lg:translate-x-0',
          isOpen ? 'translate-x-0' : '-translate-x-full',
        )}
      >
        <div className="h-16 flex items-center px-6 border-b border-white/10">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-secondary flex items-center justify-center font-bold text-sm text-white">
              U
            </div>
            <span className="font-bold text-lg tracking-tight">{title}</span>
          </div>
        </div>

        <nav className="flex-1 py-6 px-3 space-y-1 overflow-y-auto scrollbar-thin">
          {items.map((item) => (
            <NavLink
              key={item.href}
              to={item.href}
              end={item.href.split('/').length <= 2}
              onClick={() => setIsOpen(false)}
              className={({ isActive }) =>
                cn(
                  'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-200',
                  isActive
                    ? 'bg-white/15 text-white shadow-sm'
                    : 'text-white/70 hover:text-white hover:bg-white/10',
                )
              }
            >
              <item.icon className="h-5 w-5 flex-shrink-0" />
              {item.label}
            </NavLink>
          ))}
        </nav>

        <div className="p-4 border-t border-white/10">
          <p className="text-[11px] text-white/40 text-center">
            © 2026 UPAO · v1.0.0
          </p>
        </div>
      </aside>
    </>
  )
}
