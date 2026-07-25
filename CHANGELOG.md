# Changelog

> Hitos del proyecto, no cada commit — un hito es un tag/baseline al
> que se puede volver con confianza (build limpio, QA, documentación
> de cierre). El detalle de cada uno vive en su propio
> `ENGINEERING-GATE-*.md` / `*_COMPLETION.md` / `QA_*.md`.

## `epica-d-complete` — 2026-07-25

**Baseline actual.** Último commit integrado: `7593625`.

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

Épica E — a definir. Punto de partida recomendado: tag
`epica-d-complete`, rama `feature/epica-e-...`.
