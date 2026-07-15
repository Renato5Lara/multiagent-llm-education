// Estado honesto para pestañas del Panel Pedagógico que todavía no tienen
// una agregación real de curso completo detrás — nunca se rellena con datos
// inventados solo para que la pestaña "se vea completa" (regla de veracidad
// del proyecto). Reutilizado por Conceptos y Adaptación.
import { Construction } from 'lucide-react'

interface Props {
  title: string
  reason: string
}

export default function ComingSoonTab({ title, reason }: Props) {
  return (
    <div className="flex flex-col items-center justify-center py-20 text-center max-w-md mx-auto">
      <Construction className="h-8 w-8 text-neural-muted/40 mb-4" />
      <p className="text-sm font-medium text-neural-text mb-2">{title} — pendiente</p>
      <p className="text-xs text-neural-muted/60 leading-relaxed">{reason}</p>
    </div>
  )
}
