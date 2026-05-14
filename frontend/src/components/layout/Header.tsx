import { useAuthStore } from '@/stores/authStore'
import { getRoleLabel } from '@/lib/utils'
import { Badge } from '@/components/ui/badge'
import UserDropdown from '@/components/common/UserDropdown'

export default function Header() {
    const { user } = useAuthStore()

    if (!user) return null

    return (
        <header className="sticky top-0 z-20 h-16 bg-white border-b border-gray-200 flex items-center justify-between px-6 shadow-sm">
            <div />
            <div className="flex items-center gap-4">
                <Badge variant="outline" className="text-xs font-medium">
                    {getRoleLabel(user.role)}
                </Badge>
                <UserDropdown />
            </div>
        </header>
    )
}
