// Concepto multimodal — la única celda del ciclo que cambia según el perfil.
// En S1 el medio es un guion mock enmarcado; en S2 el Content Discovery Agent
// lo reemplaza por el recurso curado real sin tocar este componente.

import { useRef } from 'react'
import { Film, Headphones, Image as ImageIcon, BookOpen, Joystick, FileText } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { AudioNarration } from './AudioNarration'
import { PythonBridge } from './PythonBridge'
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
  /** Refuerzo previo a la práctica cuando el pre-test ya marcó "fundamentos"
   *  para este ciclo (Sprint "Adaptación real", Fase B item 1): reutiliza el
   *  MISMO ejemplo resuelto que ya existe en remediation.steps[0].illustration
   *  — antes solo se mostraba reactivamente, después de fallar la práctica;
   *  ahora también se ofrece proactivamente, antes de intentarla. Ningún
   *  campo ni componente nuevo — mismo contenido, mostrado antes. */
  earlyReinforcement?: { mediumLabel: string; body: string[] }
}

export function ConceptStep({ concept, modality, onContinue, earlyReinforcement }: Props) {
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
            {/* RC-FINAL: la variante visual ES visual — comparación gráfica real */}
            {variant.infographic && (
              <div className="space-y-3">
                <div className="rounded-xl border border-amber-500/30 bg-amber-500/5 p-4 space-y-2">
                  <p className="text-[10px] font-mono tracking-[0.15em] uppercase text-amber-400">✗ Ambigua</p>
                  <p className="text-sm md:text-base text-neural-text font-medium">
                    «{variant.infographic.vague.instruction}»
                  </p>
                  <div className="flex flex-wrap gap-1.5">
                    {variant.infographic.vague.questions.map((q, i) => (
                      <span key={i} className="text-xs px-2 py-0.5 rounded-full border border-amber-500/30 text-amber-300/90 bg-amber-500/10">
                        {q}
                      </span>
                    ))}
                  </div>
                </div>
                <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/5 p-4 space-y-2">
                  <p className="text-[10px] font-mono tracking-[0.15em] uppercase text-emerald-400">✓ Precisa</p>
                  <p className="text-sm md:text-base text-neural-text font-medium">
                    «{variant.infographic.precise.instruction}»
                  </p>
                  <div className="flex flex-wrap gap-1.5">
                    {variant.infographic.precise.parts.map((p, i) => (
                      <span key={i} className="text-xs px-2 py-0.5 rounded-full border border-emerald-500/30 text-emerald-300/90 bg-emerald-500/10">
                        ✓ {p}
                      </span>
                    ))}
                  </div>
                </div>
                <p className="text-xs text-neural-muted italic px-1">{variant.infographic.caption}</p>
              </div>
            )}

            {/* RC-FINAL: la variante de audio SUENA — narración con voz real */}
            {variant.narrationText && <AudioNarration text={variant.narrationText} />}

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

      {/* Un segundo caso — no un refuerzo opcional, parte del recorrido:
          la teoría no depende de un solo ejemplo para fijar la idea. */}
      {concept.secondExample && (
        <div className="glass-panel rounded-2xl p-5 space-y-3">
          <p className="text-[11px] font-mono tracking-[0.15em] uppercase text-neural-violet">
            {concept.secondExample.label}
          </p>
          {concept.secondExample.body.map((paragraph, i) => (
            <p key={i} className="text-sm text-neural-text/90 leading-relaxed">
              {paragraph}
            </p>
          ))}
        </div>
      )}

      {earlyReinforcement && (
        <div className="glass-panel rounded-2xl p-5 space-y-3">
          <p className="text-[11px] font-mono tracking-[0.15em] uppercase text-neural-violet">
            {earlyReinforcement.mediumLabel} — repaso antes de practicar
          </p>
          {earlyReinforcement.body.map((paragraph, i) => (
            <p key={i} className="text-sm text-neural-text/90 leading-relaxed">
              {paragraph}
            </p>
          ))}
        </div>
      )}

      {/* Puente a Python del propio ejemplo de la teoría — el estudiante ve
          código real mientras aprende el concepto, no solo al final. */}
      {concept.pythonBridge && <PythonBridge bridge={concept.pythonBridge} />}

      <div className="flex justify-end">
        <Button onClick={() => onContinue(Date.now() - startRef.current)} className="gap-2">
          Ponerlo a prueba →
        </Button>
      </div>

    </div>
  )
}
