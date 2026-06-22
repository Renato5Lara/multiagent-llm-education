import { cn } from '@/lib/utils'

export type HintVariant = 'tip' | 'warning' | 'remember' | 'application'

interface Props {
  variant:  HintVariant
  content:  string
  title?:   string
  className?: string
}

const VARIANT_CONFIG: Record<HintVariant, {
  icon:        string
  defaultTitle: string
  border:      string
  bg:          string
  iconBg:      string
  text:        string
  titleColor:  string
  leftBar:     string
}> = {
  tip: {
    icon:         '💡',
    defaultTitle: 'Consejo',
    border:       'border-blue-200 dark:border-blue-800',
    bg:           'bg-blue-50/80 dark:bg-blue-950/30',
    iconBg:       'bg-blue-100 dark:bg-blue-900/40',
    text:         'text-blue-700 dark:text-blue-300',
    titleColor:   'text-blue-600 dark:text-blue-400',
    leftBar:      'bg-blue-400 dark:bg-blue-600',
  },
  warning: {
    icon:         '⚠️',
    defaultTitle: 'Error común',
    border:       'border-amber-200 dark:border-amber-800',
    bg:           'bg-amber-50/80 dark:bg-amber-950/30',
    iconBg:       'bg-amber-100 dark:bg-amber-900/40',
    text:         'text-amber-700 dark:text-amber-300',
    titleColor:   'text-amber-600 dark:text-amber-400',
    leftBar:      'bg-amber-400 dark:bg-amber-600',
  },
  remember: {
    icon:         '🧠',
    defaultTitle: 'Recuerda',
    border:       'border-violet-200 dark:border-violet-800',
    bg:           'bg-violet-50/80 dark:bg-violet-950/30',
    iconBg:       'bg-violet-100 dark:bg-violet-900/40',
    text:         'text-violet-700 dark:text-violet-300',
    titleColor:   'text-violet-600 dark:text-violet-400',
    leftBar:      'bg-violet-400 dark:bg-violet-600',
  },
  application: {
    icon:         '🚀',
    defaultTitle: 'Aplicación práctica',
    border:       'border-emerald-200 dark:border-emerald-800',
    bg:           'bg-emerald-50/80 dark:bg-emerald-950/30',
    iconBg:       'bg-emerald-100 dark:bg-emerald-900/40',
    text:         'text-emerald-700 dark:text-emerald-300',
    titleColor:   'text-emerald-600 dark:text-emerald-400',
    leftBar:      'bg-emerald-400 dark:bg-emerald-600',
  },
}

export function PedagogicalHintCard({ variant, content, title, className }: Props) {
  const cfg = VARIANT_CONFIG[variant]

  return (
    <div className={cn(
      'flex gap-0 rounded-lg border overflow-hidden',
      'animate-in fade-in slide-in-from-bottom-1 duration-300',
      cfg.border,
      cfg.bg,
      className,
    )}>
      {/* Left accent bar */}
      <div className={cn('w-1 shrink-0', cfg.leftBar)} />

      {/* Content */}
      <div className="flex items-start gap-3 px-4 py-3 flex-1">
        <span className={cn(
          'text-lg leading-none select-none shrink-0 mt-0.5 rounded-md p-1',
          cfg.iconBg,
        )}>
          {cfg.icon}
        </span>
        <div className="flex-1 min-w-0">
          <p className={cn('text-xs font-bold uppercase tracking-wider mb-1', cfg.titleColor)}>
            {title ?? cfg.defaultTitle}
          </p>
          <p className={cn('text-sm leading-relaxed', cfg.text)}>
            {content}
          </p>
        </div>
      </div>
    </div>
  )
}
