// Auditoría "infografías" (jul 2026): varias ilustraciones de la escalera de
// remediación se etiquetan `medium: 'diagrama'` pero RemediationStepView las
// renderiza como párrafos de texto plano (el arte ASCII del body — 📊/├──/└──
// — no es un elemento visual real). En vez de generar imágenes automáticamente,
// cada `RemediationIllustration` puede llevar un `imagePrompt` ya redactado
// (composición/estilo/colores/iconos/distribución/elementos) listo para pegar
// en un generador de imágenes (ChatGPT/GPT Image) cuando alguien decida crear
// el recurso real.
//
// Este archivo NO genera ninguna imagen ni llama a ningún servicio: solo
// recorre las definiciones de módulo ya existentes y junta los prompts en un
// solo lugar, para no tener que ir ciclo por ciclo copiándolos a mano.

import { MODULE_1_EXPERIENCE } from './module1'
import { MODULE_2_EXPERIENCE } from './module2'
import type { ModuleExperienceDefinition } from '@/types/moduleExperience'

export interface ImagePromptEntry {
  /** "Módulo 1 · Ciclo 2 · Variables" — para ubicar el prompt en el recorrido. */
  location: string
  mediumLabel: string
  prompt: string
}

const MODULES: ModuleExperienceDefinition[] = [MODULE_1_EXPERIENCE, MODULE_2_EXPERIENCE]

/** Junta todos los `imagePrompt` ya redactados en el contenido de los
 *  módulos — nada se genera aquí, solo se recolecta lo que cada ciclo ya
 *  trae escrito en su `remediation.steps[].illustration.imagePrompt`. */
export function collectImagePrompts(): ImagePromptEntry[] {
  const entries: ImagePromptEntry[] = []
  for (const mod of MODULES) {
    for (const cycle of mod.cycles) {
      for (const step of cycle.remediation?.steps ?? []) {
        if (!step.illustration?.imagePrompt) continue
        entries.push({
          location: `Módulo ${mod.moduleNumber} · ${cycle.conceptLabel} · Nivel ${step.level}`,
          mediumLabel: step.illustration.mediumLabel,
          prompt: step.illustration.imagePrompt,
        })
      }
    }
  }
  return entries
}
