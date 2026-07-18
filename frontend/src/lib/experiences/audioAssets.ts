// Registro de narraciones GRABADAS para las variantes auditivas (Sprint
// UX-01 "Adaptación visible", jul 2026 — el perfil auditivo no debe depender
// únicamente de la síntesis de voz del navegador).
//
// Mismo patrón que illustrationAssets.ts: un `narrationAudioAsset` declarado
// en el contenido de un ciclo es una CLAVE que se busca aquí, nunca una ruta
// de archivo directa — así el contenido no depende de dónde vive físicamente
// el archivo, y agregar la grabación real más adelante no exige tocar el
// archivo del ciclo que ya la declara.
//
// Vacío a propósito: no se genera ni se descarga ningún audio
// automáticamente. Cuando exista un MP3/OGG/WebM real para una narración
// (grabación humana o voz sintetizada de calidad producida fuera de la app),
// se agrega aquí con dos pasos:
//   1. Colocar el archivo en frontend/src/assets/narrations/.
//   2. Importarlo y agregar una línea al mapa de abajo, con la MISMA clave
//      que ya usa `narrationAudioAsset` en el ciclo — ejemplo (no ejecutar,
//      solo referencia):
//
//   import teoriaC1 from '@/assets/narrations/m1-c1-teoria.mp3'
//   export const NARRATION_ASSETS: Record<string, string> = {
//     'm1-c1-teoria': teoriaC1,
//   }
//
// Mientras la clave no resuelva, AudioNarration usa speechSynthesis como
// hasta ahora — el estudiante auditivo nunca se queda sin narración.

import type { NarrationAudioRef } from '@/types/moduleExperience'

export const NARRATION_ASSETS: Record<string, string> = {}

/** Resuelve la referencia de audio grabado a una URL reproducible.
 *  Devuelve `undefined` si todavía no hay grabación real — el llamador cae a
 *  la síntesis de voz del navegador, nunca rompe. `narrationAudioUrl` gana
 *  sobre `narrationAudioAsset` (mismo criterio que VisualAsset). */
export function resolveNarrationAudio(ref: NarrationAudioRef | undefined): string | undefined {
  if (!ref) return undefined
  return ref.narrationAudioUrl ?? (ref.narrationAudioAsset ? NARRATION_ASSETS[ref.narrationAudioAsset] : undefined)
}
