import { Award } from 'lucide-react'
import { getModuleExperience } from '@/lib/experiences'
import type { LearningPathItem } from '@/types/student'

/**
 * AchievementsStrip — "logros académicos relacionados con el aprendizaje",
 * no gamificación genérica. Cada logro es el texto de cierre real, autorado
 * por módulo (closing.achievement), de los módulos que el estudiante ya
 * completó — no hay insignias ni puntajes inventados sin respaldo en datos.
 */
export default function AchievementsStrip({ items }: { items: LearningPathItem[] }) {
  const achievements = items
    .filter(i => i.status === 'completed')
    .map(i => ({ title: i.title, text: getModuleExperience(i.title)?.closing.achievement }))
    .filter((a): a is { title: string; text: string } => !!a.text)

  if (achievements.length === 0) {
    return (
      <div className="glass-panel rounded-2xl p-5">
        <h3 className="text-sm font-semibold text-neural-text flex items-center gap-2 mb-2">
          <Award className="h-4 w-4 text-neural-glow" />
          Logros académicos
        </h3>
        <p className="text-xs text-neural-muted/60">
          Completa tu primera misión para ver aquí lo que ya dominas.
        </p>
      </div>
    )
  }

  return (
    <div className="glass-panel rounded-2xl p-5">
      <h3 className="text-sm font-semibold text-neural-text flex items-center gap-2 mb-4">
        <Award className="h-4 w-4 text-neural-glow" />
        Logros académicos
      </h3>
      <div className="space-y-3">
        {achievements.map(a => (
          <div key={a.title} className="flex gap-3 bg-neural-lowest/60 rounded-xl px-3 py-2.5">
            <div className="h-7 w-7 rounded-lg bg-neural-glow/10 border border-neural-glow/25 flex items-center justify-center flex-shrink-0 mt-0.5">
              <Award className="h-3.5 w-3.5 text-neural-glow" />
            </div>
            <div className="min-w-0">
              <p className="text-xs font-medium text-neural-text mb-0.5">{a.title}</p>
              <p className="text-[11px] text-neural-muted/70 leading-relaxed line-clamp-3">{a.text}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
