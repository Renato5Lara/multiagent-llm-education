// Muestra la imagen real de una infografía/ilustración cuando el contenido
// declara `imageUrl` o `imageAsset` (auditoría "infografías", jul 2026 —
// segunda vuelta: la primera solo dejó el prompt redactado; esta agrega el
// mecanismo para mostrar la imagen real cuando exista). No genera ni
// descarga ninguna imagen — solo resuelve y muestra lo que el contenido ya
// declara. Acepta PNG, SVG y WebP: el navegador resuelve el formato por el
// propio archivo, este componente no distingue entre ellos.

import { resolveIllustrationAsset } from '@/lib/experiences/illustrationAssets'
import type { VisualAsset } from '@/types/moduleExperience'

interface Props extends Pick<VisualAsset, 'imageUrl' | 'imageAsset'> {
  /** Texto accesible — describe lo que se ve, nunca genérico ("imagen"). */
  alt: string
}

export function IllustrationVisual({ imageUrl, imageAsset, alt }: Props) {
  const src = imageUrl || resolveIllustrationAsset(imageAsset)
  if (!src) return null
  return (
    <img
      src={src}
      alt={alt}
      className="w-full rounded-xl border border-white/[0.08] bg-black/20 object-contain"
    />
  )
}
