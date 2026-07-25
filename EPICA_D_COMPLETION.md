# Épica D — Cierre

> Modernización visual (UI/UX) sobre el baseline `epic-c-complete`.
> Documento de cierre corto — el detalle técnico completo de cada
> commit vive en `ENGINEERING-GATE-EPICA-D.md`; esto es el resumen
> ejecutivo para volver a este punto sin releer todo el gate.

- **Fecha de cierre:** 2026-07-25
- **Punto de partida:** tag `epic-c-complete` (`4db318e`).
- **Objetivo:** elevar la calidad visual y la experiencia de uso sin
  modificar la lógica de negocio, el runtime multiagente ni los
  contratos existentes. Ningún commit mezcló cambio funcional con
  cambio visual.

## Commits (apilados, verificado con `git merge-base --is-ancestor`)

```
epic-c-complete (4db318e)
  └─ 3ceb1a8  Commit 1 — Fundamentos de diseño + Dashboard
  └─ 1c181b0  docs — objetivo explícito del gate
  └─ 6c31617  Commit 2 — Lab de Python
  └─ bfac974  docs — sistema semántico de color formalizado
  └─ 393ecbe  Commit 3 — Navegación + CTAs de avance
  └─ 54bd279  Commit 4 — Sistema de movimiento + tailwindcss-animate
```

**Ramas** (secuencia lineal, cada una contiene a la anterior):
`feature/epica-d-ui-foundation` → `feature/epica-d-lab` →
`feature/epica-d-navigation` → `feature/epica-d-animations`.

## Cambios principales

- **Sistema semántico de color**, aditivo (`neural-brand` #7c3aed /
  `neural-brand-bright`, nunca se tocó `neural-glow` ni
  `neural-violet` existentes): violeta de marca para lo que avanza al
  estudiante (CTA, "Continuar", navegación); cian para lo que
  representa ejecución/estado en vivo. Ver tabla completa en
  `ENGINEERING-GATE-EPICA-D.md`.
- **Dashboard**: saludo con degradado de marca, tarjeta "Siguiente
  paso recomendado" en violeta.
- **Lab de Python**: `Continuar →` distinguido de `Ejecutar →` por
  color — hallazgo real de ambigüedad de jerarquía, no solo estético.
- **Navegación**: marca y estado activo del Sidebar en violeta; los 6
  CTA de avance de `ModuleExperienceView.tsx` + 4 componentes
  hermanos (`CuriosityFactCard`, `CuriosityOpening`, `ConceptStep`,
  `ConceptPrimerCard`) unificados tras encontrar una inconsistencia
  real en revisión de navegador.
- **Animaciones**: instalación y registro de `tailwindcss-animate`
  (99 usos de `animate-in`/`fade-in` en 54 archivos de toda la
  plataforma nunca generaban CSS — hallazgo de infraestructura, no
  una animación nueva). Sistema semántico de movimiento
  (`duration-150` feedback inmediato, `duration-300` techo de
  aparición/transición, excepción documentada para animaciones de
  relleno de valor real). Hover con elevación + resplandor en los
  botones de marca.

## Cambios deliberadamente excluidos

- `LearningPath.tsx` ("Comenzar misión →") — misma regla aplicaría,
  pero es una página, no un componente de experiencia; no se tocó
  para no ampliar el alcance sin pedirlo.
- `components/module/`, `components/learningJourney/`,
  `components/engage/`, `components/gamification/` — sistema de
  fallback que atiende los 7 módulos del currículo sin
  `ModuleExperienceDefinition` autorada todavía (solo Módulo 1 y 2 la
  tienen). Superficie distinta a la cubierta por esta épica; sus
  ~80 usos de `duration-*` no se tocaron.
- Ningún ajuste de layout (el hallazgo de móvil, ver Riesgos).

## Riesgos conocidos

- **Superposición de layout en móvil** (preexistente, no introducida
  por esta épica): el botón hamburguesa flotante (`fixed top-4
  left-4`) se superpone visualmente con el header de marca del propio
  Sidebar cuando este se abre en viewport móvil. Es un problema de
  posicionamiento, no de color/semántica — queda para la fase de
  Pulido (responsive) del roadmap original, no se mezcla aquí.
- Los CTA de marca (`neural-brand`) fuera de `LearningPath.tsx` y de
  las 4 carpetas legacy excluidas arriba quedan sin el tratamiento —
  inconsistencia esperada y documentada, no un olvido.

## Validación (Release Gate)

| Área | Estado |
|---|---|
| Build (`tsc -b && vite build`) | ✅ Limpio en los 4 commits |
| Lint | ✅ 33 problemas preexistentes, ninguno nuevo (verificado línea por línea contra los archivos tocados) |
| QA Dashboard | ✅ `docs/qa/epica-d-foundation/` |
| QA Lab | ✅ `docs/qa/epica-d-lab/` |
| QA Navegación | ✅ `docs/qa/epica-d-navigation/` |
| QA Animaciones | ✅ `docs/qa/epica-d-animations/` |
| Responsive (desktop/tablet/móvil) | ✅ Validado; 1 hallazgo preexistente registrado arriba |
| Accesibilidad (contraste WCAG) | ✅ Las 3 combinaciones nuevas de `neural-brand` superan AA (5.7:1–7.1:1) |
| `ENGINEERING-GATE-EPICA-D.md` | ✅ Completo, actualizado en cada commit |
| Evidencias | ✅ Capturas organizadas por fase en `docs/qa/epica-d-*/` |

## Criterio de aceptación

Cumplido: alcance definido por adelantado, cambios pequeños y
reversibles, ningún cambio funcional mezclado con visual, sistema
semántico de color y de movimiento documentados (no decisiones ad
hoc), validación objetiva (WCAG) además de visual, build y lint
limpios, evidencia por commit.

## Recomendación de merge

Integrar únicamente la punta de la pila
(`feature/epica-d-animations`, que ya contiene los 4 commits en
orden) hacia `runtime/architecture`, vía push directo (fast-forward)
— mismo procedimiento usado para cerrar Épica C, dado que el checkout
local de `runtime/architecture` en esta máquina Windows sigue
bloqueado por los nombres de archivo ilegales ya documentados en
memoria (`project_git_illegal_filename_windows`).

**Épica D — CERRADA**, pendiente solo del merge/push final.
