# Changelog

> Hitos del proyecto, no cada commit — un hito es un tag/baseline al
> que se puede volver con confianza (build limpio, QA, documentación
> de cierre). El detalle de cada uno vive en su propio
> `ENGINEERING-GATE-*.md` / `*_COMPLETION.md` / `QA_*.md`.

## `epica-e-complete` — 2026-07-25

**Baseline actual.** Último commit integrado: `487f62f`.

Cierre del ciclo de aprendizaje y consolidación del Design System sobre
`epica-d-complete`. EP-02: causa raíz del bug de invisibilidad de texto
en tres componentes compartidos (`tabs.tsx`, `dropdown-menu.tsx`,
`toaster.tsx`) que llegaba a Docente y Admin. EP-01: Post-Test
enriquecido con los campos que el backend ya calculaba (Nivel,
Tiempo invertido, ganancia normalizada de Hake) y un cierre propio del
Tutor IA, verificado en vivo de punta a punta con una cuenta nueva
(diagnóstico → pretest → 2 módulos → post-test).

Ver `EPICA_E_COMPLETION.md` para el cierre completo. Precedida por
`EPICA_E_AUDIT.md`, la auditoría sin código que redefinió el alcance
original.

## `epica-d-complete` — 2026-07-25

Modernización visual (UI/UX) sobre `epic-c-complete`, sin tocar
lógica de negocio, runtime multiagente ni contratos existentes.
Sistema semántico de color (violeta de marca para lo que avanza al
estudiante, cian para ejecución/estado en vivo) y de movimiento
(`duration-150` feedback inmediato, `duration-300` techo de
aparición/transición). Reactivó 99 animaciones ya escritas en 54
archivos que nunca funcionaron por falta del plugin
`tailwindcss-animate`.

Ver `EPICA_D_COMPLETION.md` para el cierre completo (Release Gate,
riesgos conocidos, exclusiones deliberadas).

## `epic-c-complete` — 2026-07-25

Integración de dos líneas de desarrollo paralelas (Windows + Bazzite):
26 commits de UX (sprints UX-01..UX-10) + 72 commits de Épicas B/C
(Worker aislado de Pyodide, `input()` interactivo real en las 4
etapas migradas de `ciclo3-input.ts`). Fast-forward limpio, sin
reescritura de historial. Épica C cerrada con QA integral de las 6
etapas de la escalera de Python en una sola sesión de navegador real.

Ver `QA_EPICA_C.md` para el detalle de esa validación.

## Próxima línea de trabajo

RC-1 — Auditoría Final de Release, sin funcionalidades nuevas: solo
correcciones, endurecimiento, configuración, documentación y
despliegue. Ver `RC1_AUDITORIA_FINAL_RELEASE.md` (veredicto: ⚠ listo
con observaciones) para la lista priorizada de hallazgos y el estado
de cierre pendiente.
