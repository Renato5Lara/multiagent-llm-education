// Gráfico de líneas mínimo, sin dependencia nueva (SVG puro) — Observabilidad
// Pedagógica (orden del usuario, 2026-07-15): cada punto es un valor REAL del
// Runtime (confianza de un claim/decisión), nunca datos simulados. Un eje Y
// sin significado pedagógico no se grafica — por eso el rango es siempre
// [0, 1] (confianza real, ADR-0001 §4), nunca "actividad" sin unidad.
interface Point {
  x: number
  y: number
  label?: string
}

interface Props {
  points: Point[]
  color?: string
  height?: number
}

const WIDTH = 280

export function LineSeriesChart({ points, color = '#06b6d4', height = 80 }: Props) {
  if (points.length === 0) {
    return <p className="text-xs text-neural-muted/50 py-4 text-center">Sin puntos registrados todavía.</p>
  }

  const xs = points.map(p => p.x)
  const minX = Math.min(...xs)
  const maxX = Math.max(...xs)
  const spanX = maxX - minX || 1

  const toSvgX = (x: number) => ((x - minX) / spanX) * (WIDTH - 8) + 4
  const toSvgY = (y: number) => height - 8 - y * (height - 16)

  const path = points
    .map((p, i) => `${i === 0 ? 'M' : 'L'} ${toSvgX(p.x).toFixed(1)} ${toSvgY(p.y).toFixed(1)}`)
    .join(' ')

  return (
    <svg viewBox={`0 0 ${WIDTH} ${height}`} className="w-full" style={{ height }}>
      <line x1={4} y1={height - 8} x2={WIDTH - 4} y2={height - 8} stroke="rgba(255,255,255,0.08)" strokeWidth={1} />
      <path d={path} fill="none" stroke={color} strokeWidth={2} strokeLinejoin="round" strokeLinecap="round" />
      {points.map((p, i) => (
        <circle key={i} cx={toSvgX(p.x)} cy={toSvgY(p.y)} r={2.5} fill={color}>
          <title>{p.label ?? `${p.y.toFixed(2)}`}</title>
        </circle>
      ))}
    </svg>
  )
}
