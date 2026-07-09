// Evaluador de secuencias — función pura, evalúa la SECUENCIA COMPLETA
// (no instrucciones aisladas). El componente decide cómo comunicar el
// resultado según el número de intento (retroalimentación progresiva).

import type { OrderingItem, OrderingPracticeDef } from '@/types/moduleExperience'

export type SequenceEvaluation =
  | { status: 'correct' }
  | { status: 'decoy'; decoys: OrderingItem[] }
  | { status: 'incomplete'; missingCount: number }
  | { status: 'order'; firstWrongIndex: number; expected: OrderingItem }

export function correctSequence(def: OrderingPracticeDef): OrderingItem[] {
  return def.items
    .filter(item => item.position !== null)
    .sort((a, b) => (a.position ?? 0) - (b.position ?? 0))
}

export function evaluateSequence(sequence: string[], def: OrderingPracticeDef): SequenceEvaluation {
  const byId = new Map(def.items.map(item => [item.id, item]))
  const correct = correctSequence(def)

  // 1. La secuencia completa se revisa primero por distractores (todos, no el primero).
  const decoys = sequence
    .map(id => byId.get(id))
    .filter((item): item is OrderingItem => !!item && item.position === null)
  if (decoys.length > 0) {
    return { status: 'decoy', decoys }
  }

  // 2. Ítems correctos pero faltan pasos.
  if (sequence.length < correct.length) {
    return { status: 'incomplete', missingCount: correct.length - sequence.length }
  }

  // 3. Todos los ítems correctos: verificar el orden completo.
  for (let i = 0; i < correct.length; i++) {
    if (sequence[i] !== correct[i].id) {
      return { status: 'order', firstWrongIndex: i, expected: correct[i] }
    }
  }

  return { status: 'correct' }
}
