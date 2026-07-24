import { CheckCircle2, Lock, Loader2 } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import type { LearningPathItem } from '@/types/student'

const NODE_STYLE = {
  completed: {
    ring: 'border-neural-pulse/50 bg-neural-pulse/10 text-neural-pulse',
    line: 'border-neural-pulse/40',
  },
  available: {
    ring: 'border-neural-glow bg-neural-glow/15 text-neural-glow shadow-[0_0_24px_rgba(0,219,231,0.3)]',
    line: 'border-white/15',
  },
  locked: {
    ring: 'border-white/[0.08] bg-white/[0.02] text-neural-muted/30',
    line: 'border-white/[0.06]',
  },
} as const

// Denso (>6 módulos): fila con scroll horizontal, nodos compactos.
// Disperso (<=6): centrado y con más presencia — es el protagonista visual
// del dashboard, no debe verse igual de "chico" con 2 módulos que con 10.
const DENSE_THRESHOLD = 6

function NodeIcon({ status, size }: { status: string; size: 'lg' | 'sm' }) {
  const cls = size === 'lg' ? 'h-6 w-6' : 'h-4 w-4'
  if (status === 'completed') return <CheckCircle2 className={cls} />
  if (status === 'available') return <Loader2 className={`${cls} animate-spin`} style={{ animationDuration: '2.5s' }} />
  return <Lock className={size === 'lg' ? 'h-5 w-5' : 'h-3.5 w-3.5'} />
}

/**
 * LearningMap — recorrido visual de los módulos de la ruta adaptativa.
 * Se adapta a la cantidad real de módulos en vez de imponer un layout fijo:
 * pocas misiones se ven grandes y centradas; muchas pasan a scroll horizontal
 * compacto. El conector es una línea punteada (no sólida) para sentirse como
 * un recorrido vivo, no como una tabla.
 */
export default function LearningMap({
  items, courseId,
}: { items: LearningPathItem[]; courseId: string }) {
  const navigate = useNavigate()
  const dense = items.length > DENSE_THRESHOLD
  const nodeSize = dense ? 'sm' : 'lg'

  return (
    <div className={dense ? 'overflow-x-auto -mx-1 px-1' : 'flex flex-wrap justify-center'}>
      <div className={`flex items-start gap-x-1 ${dense ? 'w-max' : 'flex-wrap justify-center'} gap-y-6`}>
        {items.map((item, idx) => {
          const cfg = NODE_STYLE[item.status as keyof typeof NODE_STYLE] ?? NODE_STYLE.locked
          const isLast = idx === items.length - 1
          const isActive = item.status === 'available'
          const boxSize = nodeSize === 'lg' ? 'h-16 w-16' : 'h-11 w-11'
          const nodeWidth = nodeSize === 'lg' ? 'w-28' : 'w-20'

          return (
            <div key={item.id} className="flex items-start flex-shrink-0">
              <button
                disabled={item.status === 'locked'}
                onClick={() => navigate(
                  `/estudiante/module/${item.id}?courseId=${courseId}&title=${encodeURIComponent(item.title)}`
                )}
                className={[
                  'group flex flex-col items-center text-center flex-shrink-0',
                  nodeWidth,
                  item.status === 'locked' ? 'cursor-not-allowed' : 'cursor-pointer',
                ].join(' ')}
              >
                <div className="relative">
                  {isActive && nodeSize === 'lg' && (
                    <div className="absolute inset-0 rounded-2xl bg-neural-glow/40 animate-pulse-ring" />
                  )}
                  <div
                    className={[
                      'relative rounded-2xl border flex items-center justify-center transition-transform duration-200',
                      boxSize, cfg.ring,
                      item.status !== 'locked' ? 'group-hover:scale-105' : '',
                    ].join(' ')}
                  >
                    <NodeIcon status={item.status} size={nodeSize} />
                  </div>
                </div>
                {isActive && (
                  <span className="mt-1.5 text-[9px] font-mono tracking-widest text-neural-glow uppercase">
                    Activo
                  </span>
                )}
                <p
                  className={[
                    'mt-1 leading-tight line-clamp-2',
                    nodeSize === 'lg' ? 'text-xs' : 'text-[10px]',
                    item.status === 'locked' ? 'text-neural-muted/40' : 'text-neural-text',
                  ].join(' ')}
                >
                  {item.title}
                </p>
              </button>

              {!isLast && (
                <div
                  className={`${nodeSize === 'lg' ? 'w-8 sm:w-14 mt-8' : 'w-6 mt-[22px]'} border-t-2 border-dashed ${cfg.line}`}
                />
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
