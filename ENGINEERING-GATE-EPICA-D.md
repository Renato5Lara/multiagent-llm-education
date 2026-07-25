# Engineering Gate — Épica D: Modernización de la experiencia visual

> Modernización visual pura (UI/UX) sobre una base ya estabilizada
> (`epic-c-complete`). No introduce comportamiento nuevo, no toca el
> Runtime ni ningún contrato Boundary/HTTP — solo presentación. Sigue
> la misma disciplina de "cambios pequeños" que Épicas B/C: un
> commit por superficie, sin reescribir tokens ya usados en cientos
> de lugares.

- **Fecha de inicio:** 2026-07-25
- **Punto de partida:** tag `epic-c-complete` (`4db318e`).

## Fase 1 — Fundamentos de diseño

### Decisión: regla híbrida de color

Referencia visual aportada por el tesista (CodeMorph): estética
violeta/índigo dominante. El proyecto ya documenta en `CLAUDE.md` una
paleta cian-primaria/violeta-secundaria, usada en cientos de lugares
(`neural-glow` cian, `neural-violet` #ce5dff). Revertir ese balance
globalmente reescribiría el token compartido `bg-primary` que usan
`Ejecutar`, `Continuar`, `Comprobar`, `Enviar` en toda la plataforma —
alto riesgo, sin beneficio real.

**Decisión del tesista: regla híbrida, no reemplazo total.**

- 🟣 **Violeta/índigo** (`neural-brand` #7c3aed, nuevo token) — marca,
  hero, CTA que **inicia** una acción nueva (ej. "Comenzar
  diagnóstico", "Continuar misión", "Ver ruta adaptativa", titulares
  de bienvenida).
- 🔵 **Cian** (`neural-glow` #00dbe7, existente, sin tocar) — todo lo
  que representa **estado en vivo**: activo, progreso, ejecución,
  streaming, indicadores del sistema multiagente (`Ejecutar →`,
  `Comprobar`, nodo "ACTIVO" del mapa de aprendizaje, stat tiles,
  badge de porcentaje).

**Por qué es aditivo, no una migración:** `neural.brand` /
`neural.brand-bright` son tokens NUEVOS en `tailwind.config.js`,
distintos de `neural.violet` (#ce5dff, ya usado en el anillo de
dominio y acentos del tutor — se deja intacto). Ningún uso existente
de `bg-primary`/`text-neural-glow` cambia de significado.

### Tokens nuevos (`tailwind.config.js`, `index.css`)

```
neural.brand         #7c3aed   — CTA principal, marca, hero
neural.brand-bright  #a78bfa   — texto/glow claro sobre fondo oscuro

.gradient-text-brand  — degradado de marca para titulares hero (NO usar en texto de cuerpo ni etiquetas chicas — pierde legibilidad)
.glow-brand / .glow-brand-lg — sombra de marca, distinta de .glow-violet existente
```

### Tipografía / espaciado / radios / duraciones

No se introduce una escala nueva — la escala de Tailwind (`text-xs`
… `text-3xl`, espaciado `4`/`8`/etc., `rounded-2xl` ya convención de
`glass-panel`) ya cubre lo necesario. Se amplía tamaño/línea de los
titulares hero puntualmente donde corresponde (ver Dashboard abajo),
no se inventa un token de tamaño nuevo sin un consumidor real
(regla de derivación, `CLAUDE.md`).

## Superficies migradas

### Dashboard del estudiante (`Dashboard.tsx`) — ✅ primer commit

- `Greeting`: nombre en `gradient-text-brand`, `text-3xl` (antes
  `text-2xl` plano).
- `NextMissionCard` ("Siguiente paso recomendado"): badge, glow
  ambiental y los 4 botones de acción (`Comenzar diagnóstico`,
  `Rendir Post-Test`, `Continuar misión`, `Ver ruta adaptativa`) pasan
  a `neural-brand`.
- **Sin tocar** (correctamente cian, por la regla híbrida):
  `StatTile` (avance/misiones/competencias/dificultad),
  `DifficultyLevelCard` (anillo, ya violeta claro existente — no se
  toca), nodo "ACTIVO" y badge "% completado" del mapa de
  aprendizaje, panel del Tutor.

**Hallazgo real de esta sesión (no un bug del código, un artefacto del
entorno dev):** el servidor de Vite no regeneró las utilidades
Tailwind derivadas del nuevo token `neural.brand` hasta reiniciarlo —
`bg-neural-brand` no existía en absoluto en el CSS servido pese a
estar en `tailwind.config.js` (confirmado via
`getComputedStyle().backgroundColor` = `rgba(0,0,0,0)` antes del
reinicio, `rgb(124,58,237)` después). Si una futura sesión agrega un
token de color nuevo y no lo ve reflejado en el navegador, reiniciar
el dev server antes de asumir un error de implementación.

## Próximos pasos (no en este commit)

- `feature/epica-d-dashboard` (continuación): resto de tarjetas de
  logros/accesos rápidos si aportan algo más allá de lo ya aplicado.
- `feature/epica-d-lab`: laboratorio de Python (`PythonBridge.tsx`,
  `ModuleExperienceView.tsx` layout `lab`) bajo la misma regla híbrida
  — `Ejecutar`/`Comprobar` se quedan cian (ejecución en vivo), posible
  aplicación de `neural-brand` en encabezados de sección o CTAs de
  cierre de ciclo.
- `feature/epica-d-navigation`: Sidebar (estado activo del link).
- `feature/epica-d-animations`: detalles premium (microanimaciones,
  skeleton loaders) — última fase, según lo acordado con el tesista.
