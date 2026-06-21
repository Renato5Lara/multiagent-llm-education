import { useEffect, useRef } from 'react'
import { Button } from '@/components/ui/button'
import { levelFromXp } from './XpLevelBar'
import type { CompleteResponse } from '@/types/engagement'

interface Props {
  result: CompleteResponse
  /** XP the student had at the start of the session (before any interactions). */
  initialXp: number
  onContinue: () => void
}

/**
 * EngageCompletionCelebration — full-screen overlay shown after completing the
 * Engage phase.
 *
 * Displays:
 *   - Total XP earned this session (result.xp_earned)
 *   - Level before → after (with animated progress bar)
 *   - Badge unlocks (if any)
 *   - "Continuar" button + 4s auto-advance
 *
 * Auto-advances so the student is never blocked, even if distracted.
 */
export function EngageCompletionCelebration({ result, initialXp, onContinue }: Props) {
  const autoTimer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined)

  useEffect(() => {
    autoTimer.current = setTimeout(onContinue, 4200)
    return () => clearTimeout(autoTimer.current)
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const totalXpAfter  = initialXp + result.xp_earned
  const { level: lvlAfter, progress: progAfter, max } = levelFromXp(totalXpAfter)
  const { level: lvlBefore }                          = levelFromXp(initialXp)
  const leveledUp = lvlAfter > lvlBefore
  const pct        = Math.round((progAfter / max) * 100)

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center"
      style={{ background: 'rgba(0,0,0,0.72)' }}
    >
      <div className="mx-4 w-full max-w-sm rounded-2xl bg-card border border-border shadow-2xl overflow-hidden animate-in zoom-in-90 fade-in duration-300">

        {/* ── Top accent bar ───────────────────────────────────────────── */}
        <div className="h-1.5 bg-gradient-to-r from-amber-400 via-yellow-400 to-amber-500" />

        <div className="px-6 py-7 space-y-5 text-center">

          {/* ── Heading ───────────────────────────────────────────────── */}
          <div className="space-y-1">
            <p className="text-3xl">🎉</p>
            <h2 className="text-lg font-bold">¡Misión completada!</h2>
            <p className="text-sm text-muted-foreground">Exploraste todas las pistas del módulo</p>
          </div>

          {/* ── XP earned ─────────────────────────────────────────────── */}
          <div className="rounded-xl border border-amber-200 dark:border-amber-800 bg-amber-50 dark:bg-amber-950/30 py-4">
            <p className="text-3xl font-bold text-amber-600 dark:text-amber-400 tabular-nums">
              +{result.xp_earned} XP
            </p>
            {leveledUp && (
              <p className="text-sm font-semibold text-emerald-600 dark:text-emerald-400 mt-1">
                Nivel {lvlBefore} → Nivel {lvlAfter} 🚀
              </p>
            )}
          </div>

          {/* ── Level progress bar ────────────────────────────────────── */}
          <div className="space-y-1.5 text-left">
            <div className="flex items-center justify-between text-xs font-medium">
              <span className="text-amber-600 dark:text-amber-400">⭐ Nivel {lvlAfter}</span>
              <span className="text-muted-foreground tabular-nums">{progAfter}/{max} XP</span>
            </div>
            <div className="h-2.5 rounded-full bg-muted overflow-hidden">
              <div
                className="h-full rounded-full bg-gradient-to-r from-amber-400 to-amber-500 transition-all duration-1000 delay-200"
                style={{ width: `${pct}%` }}
              />
            </div>
          </div>

          {/* ── Badges earned ─────────────────────────────────────────── */}
          {result.badges.length > 0 && (
            <div className="space-y-2 text-left">
              <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
                Insignias desbloqueadas
              </p>
              <div className="space-y-1.5">
                {result.badges.map(b => (
                  <div
                    key={b.slug}
                    className="flex items-center gap-2.5 rounded-lg border border-amber-200 dark:border-amber-800 bg-amber-50/60 dark:bg-amber-950/20 px-3 py-2 animate-in fade-in slide-in-from-left-2 duration-500"
                  >
                    <span className="text-xl shrink-0">{b.icon}</span>
                    <div className="min-w-0">
                      <p className="text-sm font-semibold">{b.label}</p>
                      <p className="text-xs text-muted-foreground">+{b.xp} XP bonus</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* ── Continue button ───────────────────────────────────────── */}
          <Button
            className="w-full bg-primary hover:bg-primary/90 shadow-md shadow-primary/25"
            onClick={() => { clearTimeout(autoTimer.current); onContinue() }}
          >
            Continuar al módulo →
          </Button>
        </div>
      </div>
    </div>
  )
}
