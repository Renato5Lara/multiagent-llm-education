# Sprint 1A — Modernización visual del laboratorio de programación

**Estado:** Aprobado por el tesista (conversación 2026-07-24, sesión de
implementación directa) tras `AUDITORIA-EPICA-B.md` y
`SPIKE-B0-PYODIDE-STDIN.md` (ambos commiteados en `6a69b75`). Esta
aprobación se registró en el chat, no en un documento previo del
repositorio — este archivo sustituye esa ausencia.

## Alcance aprobado

Objetivo: modernizar visualmente el laboratorio de programación del
estudiante (`frontend/src/components/experience/PythonBridge.tsx` +
lo que consume de `frontend/src/hooks/usePyodide.ts`) sin modificar el
comportamiento funcional.

**Permitido:**
- Reorganización del layout del laboratorio.
- Mejora visual del editor, la consola/salida y los controles.
- Mejora de estilos, espaciado, tipografía, jerarquía visual y diseño
  responsive.
- Extracción o reorganización de componentes de presentación cuando
  ayude a la organización del código, sin alterar comportamiento.

**Fuera de alcance (expresamente prohibido):**
- Lógica de ejecución, flujo de Pyodide, manejo de `input()`.
- Arquitectura, backend, APIs.
- Comportamiento observable (mismos props, mismo estado, mismos
  eventos hacia `handleRun`/`goToStage`/`recordEvidence`/
  `submitCycleEvidence`).
- Detección dinámica de `input()` (explícitamente fuera — ver
  `AUDITORIA-EPICA-B.md` §2, es hipótesis no implementada).
- Sprint 1B o posterior.

## Próximo paso tras este sprint

Volver al checkpoint de alineación pendiente (4 preguntas
diagnósticas) antes de aprobar cualquier decisión de arquitectura para
Épica B — ver memoria `epica_b_auditoria_spike_2026_07_24` y
`feedback_handoff_prompt_no_redo_work`.
