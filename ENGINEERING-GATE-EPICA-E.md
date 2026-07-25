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

Sin backend nuevo — los 6 campos que faltaban ya estaban en
`ExperimentComparisonOut`/`KnowledgeTestResultOut` (ver
`EPICA_E_AUDIT.md`). Todo el trabajo es de `KnowledgeTest.tsx`
(pantalla de resultado), en `frontend/src/pages/estudiante/`.

### Cambios

1. **Segunda fila de la tarjeta de comparación** (además de Pre/Post/
   Incremento, ya existente): Nivel (`pre_level → post_level`, con
   las mismas etiquetas de `LEVEL_STYLES` ya usadas en el resto de la
   pantalla), Tiempo invertido (`pre_duration_seconds`/
   `post_duration_seconds`, formateados a minutos), y ganancia
   normalizada `g` (con etiqueta cualitativa Alta/Media/Baja
   efectividad — convención de Hake, 1998, el mismo valor que ya se
   le muestra al docente en Panel Pedagógico). `percent_gain` se
   agregó como texto secundario junto al incremento absoluto, sin
   quitarle protagonismo visual a la métrica principal.
2. **`group_label` deliberadamente NO se muestra al estudiante** —
   es la etiqueta de cohorte del experimento (Experimental/Control);
   revelar el grupo asignado a un participante es una práctica de
   diseño experimental a evitar (podría sesgar su comportamiento).
   Campo reservado para vistas de investigador, no para el estudiante.
3. **Nuevo panel "Tutor IA Multiagente — Cierre de tu aprendizaje"**,
   mismo lenguaje visual que `TutorInsightsPanel.tsx` del Dashboard
   (ícono `Bot` en círculo violeta, nota con `Sparkles`). Usa
   `describePostTestClosing()` — una función nueva, puramente de
   frontend, que compone `mastered_modules`/`critical_modules`
   (ya presentes en el resultado, sin cambios de backend) + el
   incremento, con redacción propia de CIERRE ("mejoraste X puntos…
   si quieres seguir profundizando…"), nunca la de
   `competency_profile.recommendation` (que dice "tu ruta empezará
   por X" — verificado con datos reales que sigue devolviendo esa
   redacción también para intentos `post`, confirmando el hallazgo
   de la auditoría).

### Validación (sin modificar datos de producción/experimento)

Se intentó reproducir un post-test fresco borrando el intento
existente de una cuenta QA (`qa.luis.auditivo@upao.edu.pe`) para
volver a rendirlo — **la base de datos rechazó el borrado por la
restricción de llave foránea `experiment_results_post_attempt_id_fkey`**:
el dato de comparación ya materializado protege la integridad del
intento que lo originó. Correcto — no se fuerza el borrado (dato de
experimento real, aunque la cuenta sea de QA). Se verificó en su
lugar contra la API real, sin mutar nada:

```
GET /api/students/knowledge-test/{course}/comparison  (qa.luis.auditivo)
→ pre=25.0% post=58.33% absolute_gain=33.33 percent_gain=133.32
  normalized_gain=0.4444 pre_level=basico post_level=intermedio

GET /api/students/knowledge-test/{course}/result?kind=post
→ mastered_modules=[1] critical_modules=[4]
  competency_profile.recommendation = "Tu fortaleza es Comprensión
  del problema (100%)... tu ruta comenzará por ahí." ← confirma que
  el backend sigue redactando en clave de PRE-test también para post,
  exactamente como anticipó la auditoría.
```

Trazado a mano contra el código: `normalizedGainLabel(0.4444)` →
"Efectividad media" (0.3 ≤ g < 0.7, correcto); `LEVEL_STYLES['basico'/
'intermedio']` → "Básico"/"Intermedio" (claves coinciden con
`classify_level()` del backend, verificado); `describePostTestClosing(
['Introducción a la Programación'], ['Condicionales'], 33.33)` →
"Mejoraste 33 puntos desde tu diagnóstico inicial — un avance real y
medible. Tu punto más fuerte fue introducción a la programación. Si
quieres seguir profundizando por tu cuenta, condicionales sigue
siendo el área con más margen de mejora." — coherente, nunca dice
"tu ruta empezará".

Build limpio (`tsc -b` confirma que los 6 campos nuevos están
correctamente tipados desde `ExperimentComparison`/`KnowledgeTestResult`,
sin `any`).
