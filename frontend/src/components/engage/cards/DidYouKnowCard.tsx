import type { EngagementResource } from '@/types/engagement'

interface Props {
  resource: EngagementResource
}

/**
 * DidYouKnowCard — Sprint C1
 *
 * Renders a "¿Sabías que...?" discovery card with an immersive visual
 * identity: warm amber gradient, large fact display, decorative circles.
 * The card handles only its own content — framing (badge, pista count,
 * tagline) lives in EngagePhase.tsx.
 */
export function DidYouKnowCard({ resource }: Props) {
  return (
    <div className="relative overflow-hidden rounded-xl border border-amber-200 dark:border-amber-800 bg-gradient-to-br from-amber-50 via-yellow-50 to-orange-50 dark:from-amber-950/30 dark:via-yellow-950/30 dark:to-orange-950/20 min-h-[220px]">

      {/* Decorative background bubbles */}
      <div className="pointer-events-none absolute -top-10 -right-10 w-40 h-40 rounded-full bg-amber-200/40 dark:bg-amber-500/10" />
      <div className="pointer-events-none absolute -bottom-16 -left-10 w-52 h-52 rounded-full bg-yellow-200/30 dark:bg-yellow-500/10" />

      <div className="relative p-6 space-y-5">

        {/* Header: emoji + label */}
        <div className="flex items-center gap-3">
          <span className="text-4xl select-none leading-none">💡</span>
          <div>
            <p className="text-xs font-mono font-bold tracking-widest text-amber-600 dark:text-amber-400 uppercase">
              ¿Sabías que...?
            </p>
            <p className="text-xs text-amber-700/60 dark:text-amber-400/50 mt-0.5">
              Un dato que pocas personas conocen
            </p>
          </div>
        </div>

        {/* Main fact */}
        <p className="text-base sm:text-lg font-medium leading-relaxed text-gray-800 dark:text-gray-100">
          {resource.content}
        </p>

        {/* Title as attribution when it adds context beyond the content */}
        {resource.title && !resource.content.startsWith(resource.title.slice(0, 30)) && (
          <p className="text-xs text-amber-700/70 dark:text-amber-400/60 border-t border-amber-200/70 dark:border-amber-700/40 pt-3 italic">
            {resource.title}
          </p>
        )}
      </div>
    </div>
  )
}
