import { cn } from '@/lib/utils'

// 50 XP per level — gives visible progression within a single engage session.
export function levelFromXp(totalXp: number) {
  const level    = Math.floor(totalXp / 50) + 1
  const progress = totalXp % 50
  return { level, progress, max: 50 }
}

interface Props {
  xp: number
  className?: string
}

export function XpLevelBar({ xp, className }: Props) {
  const { level, progress, max } = levelFromXp(xp)
  const pct = Math.round((progress / max) * 100)

  return (
    <div className={cn('space-y-1', className)}>
      <div className="flex items-center justify-between text-xs">
        <span className="font-semibold text-amber-600 dark:text-amber-400">
          ⭐ Nivel {level}
        </span>
        <span className="text-muted-foreground tabular-nums">
          {progress}/{max} XP
        </span>
      </div>
      <div className="h-2 rounded-full bg-muted overflow-hidden">
        <div
          className="h-full rounded-full bg-gradient-to-r from-amber-400 to-amber-500 dark:from-amber-500 dark:to-amber-400 transition-all duration-700"
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  )
}
