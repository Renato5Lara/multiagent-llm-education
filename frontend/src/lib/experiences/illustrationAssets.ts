// Registro de imágenes reales para infografías/ilustraciones (auditoría
// "infografías", jul 2026 — implementación del mecanismo imageUrl/imageAsset).
// Un `imageAsset` declarado en el contenido de un ciclo es una CLAVE que se
// busca aquí, nunca una ruta de archivo directa — así el contenido no
// depende de dónde vive físicamente el archivo, y agregar la imagen real más
// adelante no exige tocar el archivo del ciclo que ya la declara.
//
// Vacío a propósito: no se genera ni se descarga ninguna imagen
// automáticamente. Cuando exista un PNG/SVG/WebP real para una ilustración
// (ver el reporte de "infografías pendientes de ilustración"), se agrega
// aquí con dos pasos:
//   1. Colocar el archivo en frontend/src/assets/illustrations/.
//   2. Importarlo y agregar una línea al mapa de abajo, con la MISMA clave
//      que ya usa `imageAsset` en el ciclo — ejemplo (no ejecutar, solo
//      referencia):
//
//   import cargaBateria from '@/assets/illustrations/m1-c1-recarga-bateria.png'
//   export const ILLUSTRATION_ASSETS: Record<string, string> = {
//     'm1-c1-recarga-bateria': cargaBateria,
//   }

export const ILLUSTRATION_ASSETS: Record<string, string> = {}

/** Resuelve un `imageAsset` (clave) a su URL real ya empaquetada por Vite.
 *  Devuelve `undefined` si la clave todavía no tiene imagen real — el
 *  llamador cae al contenido textual existente, nunca rompe. */
export function resolveIllustrationAsset(key: string | undefined): string | undefined {
  if (!key) return undefined
  return ILLUSTRATION_ASSETS[key]
}

/** true cuando hay una imagen real que mostrar. El llamador la usa para
 *  decidir si cae al contenido textual/estructurado existente — nunca
 *  rompe compatibilidad: sin imagen, el comportamiento previo es intacto. */
export function hasIllustrationImage(asset: { imageUrl?: string; imageAsset?: string }): boolean {
  return !!(asset.imageUrl || resolveIllustrationAsset(asset.imageAsset))
}
