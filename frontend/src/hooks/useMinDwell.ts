// Anti-clic-rápido (auditoría "criterios de finalización reales", jul 2026):
// varias pantallas de contenido (teoría, ¿sabías que?, microexplicación,
// refuerzo) solo tenían un botón "Continuar" siempre habilitado — el
// estudiante podía saltarlas con un clic inmediato, sin haber visto nada.
// `ready` pasa a true recién tras `ms` desde el montaje — nunca bloquea
// permanentemente ni exige releer nada, solo evita el avance instantáneo.
import { useEffect, useState } from 'react'

export function useMinDwell(ms: number): boolean {
  const [ready, setReady] = useState(false)
  useEffect(() => {
    const timer = setTimeout(() => setReady(true), ms)
    return () => clearTimeout(timer)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])
  return ready
}
