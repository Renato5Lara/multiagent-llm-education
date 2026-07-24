import { Map, FlaskConical, FileText, Gauge } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import type { LearningPathItem } from '@/types/student'

interface QuickLink {
  label: string
  icon: typeof Map
  onClick: () => void
  disabled?: boolean
}

/**
 * QuickAccessRow — atajos a superficies que ya existen en el producto.
 * "Laboratorio" y "Recursos" apuntan a la misión/recurso actual del
 * estudiante (los únicos ids reales disponibles aquí); si no hay uno
 * vigente, el atajo se deshabilita en vez de apuntar a una ruta inventada.
 */
export default function QuickAccessRow({
  courseId, currentMission,
}: { courseId: string; currentMission: LearningPathItem | null }) {
  const navigate = useNavigate()

  const links: QuickLink[] = [
    {
      label: 'Ruta de aprendizaje',
      icon: Map,
      onClick: () => navigate(`/estudiante/path/${courseId}`),
    },
    {
      label: 'Laboratorio',
      icon: FlaskConical,
      disabled: !currentMission,
      onClick: () => currentMission && navigate(
        `/estudiante/module/${currentMission.id}?courseId=${courseId}&title=${encodeURIComponent(currentMission.title)}`
      ),
    },
    {
      label: 'Recursos',
      icon: FileText,
      disabled: !currentMission?.resource_id,
      onClick: () => currentMission?.resource_id && navigate(`/estudiante/content/${currentMission.resource_id}`),
    },
    {
      label: 'Progreso',
      icon: Gauge,
      onClick: () => document.getElementById('progreso')?.scrollIntoView({ behavior: 'smooth', block: 'start' }),
    },
  ]

  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
      {links.map(link => (
        <button
          key={link.label}
          disabled={link.disabled}
          onClick={link.onClick}
          className={[
            'glass-panel rounded-xl p-3.5 flex flex-col items-center gap-2 text-center transition-all duration-200',
            link.disabled
              ? 'opacity-40 cursor-not-allowed'
              : 'hover:border-neural-glow/30 hover:-translate-y-0.5 cursor-pointer',
          ].join(' ')}
        >
          <link.icon className="h-5 w-5 text-neural-glow" />
          <span className="text-xs font-medium text-neural-text">{link.label}</span>
        </button>
      ))}
    </div>
  )
}
