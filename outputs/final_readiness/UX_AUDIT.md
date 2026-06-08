# UX AUDIT REPORT

**Auditado:** 2026-06-05
**Enfoque:** Polish visual mínimo — sin cambios arquitectónicos

---

## Correcciones Aplicadas

| Archivo | Cambio | Tipo |
|---------|--------|------|
| `ReplayDashboard.tsx` | RotateCcw → Pause icon en botón Play/Pause | Icon fix |
| `SwarmDemo.tsx` | Signal duplicado → CheckCircle para métrica Decision | Icon fix |
| `policy.py` | +9 nuevas entradas en DENIED_ATTRIBUTES | Security hardening |
| `runner_payload.py` | +9 nuevas entradas + runtime patch io.open | Security hardening |

## Hallazgos (no corregidos por ser post-sustentación)

| Issue | Severidad | Archivo |
|-------|-----------|---------|
| BUG: playMode 'full' y 'week' idénticos (step=1 ambos) | Media | ReplayDashboard.tsx:39 |
| Missing loading spinners en SwarmDemo | Baja | SwarmDemo.tsx |
| Language mixing ES/EN sin estrategia definida | Baja | Múltiples archivos |
| Responsive sidebar 380px hardcoded | Baja | SwarmDemo.tsx:146 |
| AcademicGuard silent pass on failure | Media | AcademicGuard.tsx:37 |
| Sin aria-label en password toggle | Baja | Login.tsx |
| Index-as-key en listas (~48 lugares) | Baja | Múltiples archivos |

## Estado General UX

- Loading states: Suspense global ✓, skeletons parciales
- Empty states: EmptyState reusable ✓, algunos paneles sin él
- Error boundaries: Global ✓, faltan fronteras por panel
- Responsive: Sidebar mobile funcional, algunos hardcoded widths
- Accesibilidad: Iconos SVG sin alt text (no img tags), aria-label faltante en botón password
- Consistencia visual: shadcn/ui, tailwind, diseño consistente
