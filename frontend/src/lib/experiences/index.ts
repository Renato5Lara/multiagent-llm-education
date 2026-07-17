// Registro de experiencias de módulo (patrón → instancias).
// Un módulo con experiencia definida usa el flujo de ciclos de aprendizaje;
// los demás conservan el flujo legacy (EngageGateway + LearningJourney).

import type { ModuleExperienceDefinition } from '@/types/moduleExperience'
import { MODULE_1_EXPERIENCE } from './module1'
import { MODULE_2_EXPERIENCE } from './module2'

const EXPERIENCES: ModuleExperienceDefinition[] = [MODULE_1_EXPERIENCE, MODULE_2_EXPERIENCE]

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

// ── Modo módulo de referencia (PED-004) ────────────────────────────────────────
// Mientras el Módulo 1 sea el módulo de referencia, el estudiante no debe ver
// ni alcanzar los módulos legacy (2-4): no aparecen en la ruta, no se anuncian
// y completar el Módulo 1 no navega hacia ellos. Apagar cuando los demás
// módulos tengan su experiencia definida.
export const REFERENCE_MODULE_MODE = true

/** Filtra los ítems de la ruta a los módulos con experiencia definida. */
export function filterToReferenceModules<T extends { title: string }>(items: T[]): T[] {
  if (!REFERENCE_MODULE_MODE) return items
  const visible = items.filter(i => getModuleExperience(i.title) !== null)
  // Nunca dejar la ruta vacía: si ningún título coincide (datos de demo
  // distintos), se muestra la ruta completa antes que una pantalla muerta.
  return visible.length > 0 ? visible : items
}
