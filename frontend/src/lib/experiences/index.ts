// Registro de experiencias de módulo (patrón → instancias).
// Un módulo con experiencia definida usa el flujo de ciclos de aprendizaje;
// los demás conservan el flujo legacy (EngageGateway + LearningJourney).

import type { ModuleExperienceDefinition } from '@/types/moduleExperience'
import { MODULE_1_EXPERIENCE } from './module1'

const EXPERIENCES: ModuleExperienceDefinition[] = [MODULE_1_EXPERIENCE]

function normalize(value: string): string {
  return value
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .trim()
}

export function getModuleExperience(moduleTitle: string | undefined): ModuleExperienceDefinition | null {
  if (!moduleTitle) return null
  const title = normalize(moduleTitle)
  return (
    EXPERIENCES.find(exp => exp.matchTitles.some(m => title.includes(normalize(m)))) ?? null
  )
}
