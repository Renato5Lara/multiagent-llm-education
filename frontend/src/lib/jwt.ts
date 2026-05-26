/**
 * Utilidades para decodificar JWT en el frontend.
 * Solo decodifica el payload (NO valida la firma — eso lo hace el backend).
 * Se usa para verificar la expiración ANTES de enviar requests innecesarios.
 */

interface JwtPayload {
  exp?: number
  sub?: string | number
  type?: string
  [key: string]: unknown
}

/**
 * Decodifica el payload de un JWT sin verificar la firma.
 * Retorna null si el token es inválido o no puede parsearse.
 */
export function decodeJwtPayload(token: string): JwtPayload | null {
  try {
    const parts = token.split('.')
    if (parts.length !== 3) return null

    // Base64url → Base64 → decode
    const base64 = parts[1].replace(/-/g, '+').replace(/_/g, '/')
    const json = atob(base64)
    return JSON.parse(json) as JwtPayload
  } catch {
    return null
  }
}

/**
 * Verifica si un JWT ha expirado (o expirará dentro de `bufferSeconds`).
 * Un buffer de 30s evita enviar un token que expirará durante el round-trip.
 *
 * Retorna true si el token está expirado o es inválido.
 */
export function isTokenExpired(token: string | null, bufferSeconds = 30): boolean {
  if (!token) return true

  const payload = decodeJwtPayload(token)
  if (!payload?.exp) return true

  const nowSec = Math.floor(Date.now() / 1000)
  return payload.exp <= nowSec + bufferSeconds
}
