// Evidencia de aprendizaje — S1 (mock persistence).
// Toda interacción emite un evento. En S1 se acumulan en localStorage para que
// la experiencia sea observable de inmediato; en S3/S4 el mismo contrato se
// envía al backend y alimenta ConceptMastery del agente evaluador.

export type EvidenceType =
  | 'opening_answer'
  | 'concept_viewed'
  | 'practice_attempt'
  | 'choice'
  | 'reinforcement_viewed'
  | 'cycle_completed'
  | 'remediation_level'

/** Contrato que el agente evaluador consumirá para actualizar el perfil del
 *  estudiante. Hoy se acumula en localStorage (S1); el envío al backend es
 *  trabajo posterior y NO debe cambiar estos campos. */
export interface RemediationEvidence {
  /** Peldaño alcanzado: 0 = actividad principal, 3 = ayuda máxima. */
  level: number
  attempts: number
  timeMs: number
  /** Pistas consumidas antes de resolver o agotar. */
  hintsUsed: number
  /** Modalidad con la que se re-explicó el concepto en este peldaño. */
  modality: string
  solutionShown: boolean
  /** Dominio estimado tras aplicar la ganancia del peldaño (0-1). */
  masteryEstimate: number
  /** true cuando el estudiante resolvió por su cuenta en este peldaño. */
  solved: boolean
}

export interface EvidenceEvent {
  type: EvidenceType
  moduleId: string
  conceptId?: string
  detail: Record<string, unknown>
  at: string
}

const storageKey = (moduleId: string) => `experience-evidence:${moduleId}`

export function recordEvidence(event: Omit<EvidenceEvent, 'at'>): void {
  const full: EvidenceEvent = { ...event, at: new Date().toISOString() }
  try {
    const key = storageKey(event.moduleId)
    const prev = JSON.parse(localStorage.getItem(key) ?? '[]') as EvidenceEvent[]
    prev.push(full)
    localStorage.setItem(key, JSON.stringify(prev))
  } catch {
    // La evidencia local nunca bloquea la experiencia.
  }
}

export function readEvidence(moduleId: string): EvidenceEvent[] {
  try {
    return JSON.parse(localStorage.getItem(storageKey(moduleId)) ?? '[]') as EvidenceEvent[]
  } catch {
    return []
  }
}
