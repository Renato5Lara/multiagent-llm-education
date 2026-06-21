import { cn } from '@/lib/utils'
import type { EngagementBadge } from '@/types/engagement'

interface Props {
  badges: EngagementBadge[]
  newBadgeSlug?: string | null
}

export function BadgeShelf({ badges, newBadgeSlug }: Props) {
  if (!badges.length) return null

  return (
    <div className="flex flex-wrap gap-1.5">
      {badges.map(b => (
        <span
          key={b.slug}
          className={cn(
            'inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full border font-medium select-none',
            b.slug === newBadgeSlug
              ? 'border-amber-300 dark:border-amber-600 bg-amber-50 dark:bg-amber-950/40 text-amber-700 dark:text-amber-300 shadow-sm animate-bounce'
              : 'border-border bg-muted/50 text-muted-foreground',
          )}
        >
          {b.icon} {b.label}
        </span>
      ))}
    </div>
  )
}
