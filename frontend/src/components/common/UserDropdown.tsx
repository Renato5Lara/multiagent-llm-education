import { LogOut, User } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '@/stores/authStore'
import { useAuth } from '@/hooks/useAuth'
import { getInitials } from '@/lib/utils'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuItem,
} from '@/components/ui/dropdown-menu'

export default function UserDropdown() {
  const { user } = useAuthStore()
  const { logout } = useAuth()
  const navigate = useNavigate()

  if (!user) return null

  return (
    <DropdownMenu>
      <DropdownMenuTrigger className="flex items-center gap-2.5 hover:bg-white/[0.05] rounded-lg px-2 py-1.5 transition-colors outline-none">
        <Avatar className="h-7 w-7 border border-neural-glow/30">
          <AvatarFallback className="bg-neural-glow/10 text-neural-glow text-xs font-semibold">
            {getInitials(user.first_name, user.last_name)}
          </AvatarFallback>
        </Avatar>
        <div className="text-left hidden sm:block">
          <p className="text-xs font-medium leading-none text-neural-text">
            {user.first_name} {user.last_name}
          </p>
          <p className="text-[10px] text-neural-muted mt-0.5 font-mono">{user.email}</p>
        </div>
      </DropdownMenuTrigger>

      <DropdownMenuContent align="end" className="w-56 glass-panel border-white/[0.08]">
        <DropdownMenuLabel className="text-neural-muted text-xs font-mono tracking-widest uppercase">
          Mi cuenta
        </DropdownMenuLabel>
        <DropdownMenuSeparator className="bg-white/[0.06]" />
        <DropdownMenuItem
          disabled
          className="text-neural-muted focus:text-neural-text focus:bg-white/[0.05]"
        >
          <User className="mr-2 h-4 w-4" />
          Perfil
        </DropdownMenuItem>
        <DropdownMenuSeparator className="bg-white/[0.06]" />
        <DropdownMenuItem
          onClick={() => { logout(); navigate('/login') }}
          className="text-red-400 focus:text-red-300 focus:bg-red-500/[0.08] cursor-pointer"
        >
          <LogOut className="mr-2 h-4 w-4" />
          Cerrar sesión
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
