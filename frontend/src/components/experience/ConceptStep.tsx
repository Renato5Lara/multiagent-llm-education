// Concepto multimodal — la única celda del ciclo que cambia según el perfil.
// En S1 el medio es un guion mock enmarcado; en S2 el Content Discovery Agent
// lo reemplaza por el recurso curado real sin tocar este componente.

import { useRef } from 'react'
import { Film, Headphones, Image as ImageIcon, BookOpen, Joystick, FileText } from 'lucide-react'
import { Button } from '@/components/ui/button'
import type { CycleConcept, ConceptVariant, TheoryMedium } from '@/types/moduleExperience'
import type { LearningModality } from '@/types/modality'

const MEDIUM_ICON: Partial<Record<TheoryMedium, typeof Film>> = {
  infografia: ImageIcon,
  animacion: Film,
  diagrama: ImageIcon,
  clip_narrado: Headphones,
  podcast: Headphones,
  texto: BookOpen,
  ejemplo_comentado: FileText,
  articulo: BookOpen,
  simulacion: Joystick,
  codigo_anotado: FileText,
}

/** Medios que se presentan como "reproductor" (marco de media) y no como lectura. */
const FRAMED_MEDIA: TheoryMedium[] = ['infografia', 'animacion', 'diagrama', 'clip_narrado', 'podcast', 'simulacion']

interface Props {
  concept: CycleConcept
  modality: LearningModality
  onContinue: (dwellMs: number) => void
}

export function ConceptStep({ concept, modality, onContinue }: Props) {
  const startRef = useRef(Date.now())
  const variant: ConceptVariant = concept.variants[modality] ?? concept.variants.reading
  const Icon = MEDIUM_ICON[variant.medium] ?? BookOpen
  const framed = FRAMED_MEDIA.includes(variant.medium)

  return (
    <div className="max-w-2xl mx-auto space-y-5 animate-in fade-in duration-500">

      <h2 className="text-xl md:text-2xl font-bold text-neural-text leading-snug">
        {concept.title}
      </h2>

      <div className="glass-panel rounded-2xl overflow-hidden">
        <div className="flex items-center gap-2 px-5 py-3 border-b border-white/[0.06]">
          <Icon className="h-4 w-4 text-neural-glow shrink-0" />
          <span className="text-[11px] font-mono tracking-[0.15em] uppercase text-neural-glow">
            {variant.mediumLabel}
          </span>
        </div>

        <div className={framed ? 'bg-neural-lowest/60 px-6 py-6' : 'px-6 py-6'}>
          <div className="space-y-4">
            {variant.body.map((paragraph, i) => (
              <p key={i} className="text-sm md:text-base text-neural-text/90 leading-relaxed">
                {paragraph}
              </p>
            ))}
          </div>
        </div>
      </div>

      {variant.sourceNote && (
        <p className="text-xs text-neural-muted/60 italic px-1">{variant.sourceNote}</p>
      )}

      <div className="flex justify-end">
        <Button onClick={() => onContinue(Date.now() - startRef.current)} className="gap-2">
          Ponerlo a prueba →
        </Button>
      </div>

    </div>
  )
}
