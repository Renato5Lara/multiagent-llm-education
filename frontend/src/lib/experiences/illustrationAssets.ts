// Registro de imágenes reales para infografías/ilustraciones (auditoría
// "infografías", jul 2026 — implementación del mecanismo imageUrl/imageAsset).
// Un `imageAsset` declarado en el contenido de un ciclo es una CLAVE que se
// busca aquí, nunca una ruta de archivo directa — así el contenido no
// depende de dónde vive físicamente el archivo, y agregar la imagen real más
// adelante no exige tocar el archivo del ciclo que ya la declara.
//
// Registro único para las dos categorías de infografía que existen hoy:
// teoría (ConceptVariant.visual, medium 'infografia') y remediación L2
// (RemediationIllustration, medium 'diagrama') — ambas usan la MISMA clave
// `imageAsset` y se resuelven aquí, nunca por rutas dispersas en cada ciclo.
//
// Sprint UX-01 "Adaptación visible" (jul 2026): las 8 piezas del inventario
// (infografias-auditoria.md) existen como SVG vectorial autorado siguiendo
// design-system-ilustraciones.md (§4–§12: paleta cerrada, plantillas A/B con
// variantes de decisión, glassmorphism plano, iconografía outline). SVG y no
// PNG generado: el §13 ya contemplaba "SVG cuando el diagrama es puramente
// geométrico" — estas ocho lo son. Para reemplazar una pieza por una versión
// generada/diseñada mejor, basta sobrescribir la entrada correspondiente
// (versionar con sufijo -v2 según §14 del design system).

import m1c1Teoria from '@/assets/illustrations/m1-c1-teoria-cruza-habitacion.svg'
import m1c1L2 from '@/assets/illustrations/m1-c1-l2-recarga-bateria.svg'
import m1c2Teoria from '@/assets/illustrations/m1-c2-teoria-variable-nombre.svg'
import m1c2L2 from '@/assets/illustrations/m1-c2-l2-caja-vacia.svg'
import m1c3Teoria from '@/assets/illustrations/m1-c3-teoria-pregunta-input.svg'
import m1c3L2 from '@/assets/illustrations/m1-c3-l2-cartel-robot.svg'
import m2c1Teoria from '@/assets/illustrations/m2-c1-teoria-condicion-paraguas.svg'
import m2c1L2 from '@/assets/illustrations/m2-c1-l2-aire-mal.svg'
// Sprint UX-06 "Perfil visual real" (jul 2026): segundo recurso visual por
// concepto — visualiza la MISMA analogía que `secondExample.body` ya cuenta
// en prosa (manual de calibración, compartimento, cartel, pausa real),
// nunca una idea pedagógica nueva. Solo se muestran en el perfil visual.
import m1c1Analogia from '@/assets/illustrations/m1-c1-analogia-manual-calibracion.svg'
import m1c2Analogia from '@/assets/illustrations/m1-c2-analogia-compartimento.svg'
import m1c3Analogia from '@/assets/illustrations/m1-c3-analogia-pausa-real.svg'
import m2c1Analogia from '@/assets/illustrations/m2-c1-analogia-alarma-incendios.svg'

export const ILLUSTRATION_ASSETS: Record<string, string> = {
  'm1-c1-teoria-cruza-habitacion': m1c1Teoria,
  'm1-c1-l2-recarga-bateria': m1c1L2,
  'm1-c2-teoria-variable-nombre': m1c2Teoria,
  'm1-c2-l2-caja-vacia': m1c2L2,
  'm1-c3-teoria-pregunta-input': m1c3Teoria,
  'm1-c3-l2-cartel-robot': m1c3L2,
  'm2-c1-teoria-condicion-paraguas': m2c1Teoria,
  'm2-c1-l2-aire-mal': m2c1L2,
  'm1-c1-analogia-manual-calibracion': m1c1Analogia,
  'm1-c2-analogia-compartimento': m1c2Analogia,
  'm1-c3-analogia-pausa-real': m1c3Analogia,
  'm2-c1-analogia-alarma-incendios': m2c1Analogia,
}

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
