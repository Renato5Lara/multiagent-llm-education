// Orden anunciado de bloques = orden de la decisión del Runtime, restringido a los
// tipos que el tema realmente tiene. La decisión (`content_order`) puede nombrar
// tipos que la biblioteca no ofrece para ese tema (p. ej. diagram/video); anunciarlos
// promete contenido que el estudiante nunca recibe. No reordena ni inventa tipos.
export function availableContentOrder(
  contentOrder: readonly string[],
  blocks: readonly { type: string }[],
): string[] {
  const present = new Set(blocks.map(b => b.type))
  return contentOrder.filter(type => present.has(type))
}
