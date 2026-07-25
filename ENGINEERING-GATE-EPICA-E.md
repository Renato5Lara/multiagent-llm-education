# Engineering Gate — Épica E: Cierre del ciclo de aprendizaje y consolidación del Design System

> Punto de partida: tag `epica-d-complete` (`e5306aa`). Precedida por
> `EPICA_E_AUDIT.md` — auditoría sin código que redefinió el alcance:
> el Post-Test ya funciona de punta a punta (brecha de presentación,
> no de arquitectura); el bug visual de Admin/Docente/Estudiante tiene
> causa raíz en 2-3 componentes compartidos, no en veinte pantallas.

- **Fecha de inicio:** 2026-07-25 (continuación de la sesión de
  Épica D).
- **Objetivo:** (1) exponer en la pantalla de resultado del Post-Test
  los indicadores que el backend ya calcula y agregar una
  retroalimentación del Tutor IA propia para el cierre del
  aprendizaje; (2) corregir la causa raíz del bug de invisibilidad en
  componentes de UI compartidos. Ningún cambio de lógica de negocio,
  Runtime ni contratos — EP-02 es CSS/tokens puro; EP-01 es
  exposición de datos ya calculados, sin backend nuevo salvo,
  eventualmente, una función de redacción para la recomendación de
  cierre.
- **Explícitamente fuera de alcance** (ver `EPICA_E_AUDIT.md`): los
  ~60 archivos con fondo blanco sólido en `components/swarm/`,
  `components/observability/` y el sistema legacy
  (`module/`/`learningJourney/`/`engage/`) — candidato a una épica
  futura de migración, no una corrección puntual.

## EP-02 — Corrección del Design System (primer commit)

### Causa raíz confirmada (3 archivos, no una auditoría por rol)

| Archivo | Bug antes | Corrección |
|---|---|---|
| `ui/tabs.tsx` (`TabsTrigger` activo) | `bg-white text-foreground` — `--foreground` en modo oscuro es un color CLARO (`233 20% 90%`): texto casi invisible sobre fondo blanco | `bg-white/[0.08] text-neural-text shadow-sm` (superficie elevada, mismo lenguaje que `.glass-panel-elevated`) |
| `ui/tabs.tsx` (`TabsList`) | `bg-gray-100 text-muted-foreground` (contenedor claro) | `bg-white/[0.04] text-neural-muted` |
| `ui/dropdown-menu.tsx` (`Content`) | `border bg-white` — menú de tema claro flotando sobre app 100% oscura (legible pero inconsistente, no invisible) | `glass-panel-elevated` (utilidad ya existente) |
| `ui/dropdown-menu.tsx` (`Label`/`Separator`/`Item`) | `text-gray-900`/`bg-gray-100`/`text-gray-700` | `text-neural-text`/`bg-white/[0.08]`/`text-neural-muted hover:text-neural-text` |
| `ui/toaster.tsx` | `bg-white border-gray-200 text-gray-900` (default) / `bg-red-50 border-red-200 text-red-900` (destructive) — ambos tema claro | `glass-panel-elevated text-neural-text` (default) / `bg-red-500/10 border-red-500/30 text-red-200` (destructive) |

**Corrección a la propia auditoría, encontrada durante la
verificación en navegador:** `EPICA_E_AUDIT.md` afirmaba que el bug de
`Tabs` alcanzaba `pages/admin/Users.tsx`. Verificado con `grep`
preciso: **`Users.tsx` no importa `ui/tabs`** — el import real que
alcanza Admin es el de `dropdown-menu.tsx` (menú de cuenta del
header, presente en toda pantalla autenticada). El consumidor real de
`Tabs` con el bug es **Docente** (`PedagogicalPanel.tsx`,
`Dashboard.tsx`, `Courses.tsx`, `CourseDetail.tsx`, `CourseForm.tsx`)
y **Modo Evidencia** (`RuntimeConsole.tsx`), más los componentes
compartidos `WeeklyPedagogicalPlanner.tsx`
(docente)/`StudentWeeklyLearningView.tsx` (estudiante). No cambia la
conclusión (arreglar el componente compartido resuelve todos los
consumidores a la vez) pero sí a quién alcanzaba exactamente — se
corrige aquí para que el registro quede preciso.

### Validación en navegador real

- **Admin** (`admin@upao.edu.pe`): dropdown de cuenta ("MI CUENTA" /
  "Cerrar sesión") ahora en vidrio oscuro, legible, consistente con
  el resto de la plataforma.
- **Docente** (`docente@upao.edu.pe`, `/docente/panel-pedagogico`):
  pestaña activa "Resumen" ahora con fondo y texto claramente
  legibles (antes: texto casi invisible). De paso, esta pantalla ya
  consume datos reales de `ExperimentResult` a nivel agregado
  (Promedio Pre-Test, Promedio Post-Test, Incremento, ganancia
  normalizada `g`) — confirma que la infraestructura de comparación
  Pre/Post ya está en uso real, no solo calculada.

### Build

```
npm run build   → tsc -b && vite build   ✔ limpio
```

## EP-01 — Cierre del ciclo de aprendizaje (Post-Test Experience)

_Pendiente — siguiente commit de esta rama/otra rama según se
decida._
