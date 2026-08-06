# Ficha 15 — Estado de Épica C (Commit 5 pendiente desde 2026-07-25)

## Metadata

- **Fecha:** 2026-08-05
- **Rama:** `feat/confidence-calibration-remediation-orientation`
- **Protocolo pedido (Fase 7):** (1) revisar el estado original de la
  Épica C y el commit pendiente; (2) confirmar si quedó resuelta por
  cambios posteriores (LangGraph Runtime, retiro de BaseAgent,
  ConsensusEngine, E2E real, auditorías nuevas); (3) separar deuda
  vigente / trabajo superado / pendiente real; (4) no reabrir si ya fue
  absorbida por cambios posteriores. **Ningún archivo de código
  modificado, ninguna validación E2E ejecutada todavía en esta ficha.**
- **Fuente primaria:** `ENGINEERING-GATE-EPICA-C.md` (roadmap y
  criterios de cierre originales) + memoria `epica_c_gate_2026_07_25.md`
  (estado al cierre de sesión).

---

## 1. Estado original y commit pendiente

Épica C — "Generalización/Consolidación del Runtime Interactivo" —
migra las 4 etapas restantes de `ciclo3-input.ts`
(`manipular`/`completar`/`corregir`/`escribir_parcial`) del mecanismo
legado de `input()` simulado a `input()` real (Epíca B ya había migrado
`escribir_completo`; `observar` queda deliberadamente fuera por decisión
pedagógica explícita, no técnica).

**Commits 1-4/5 cerrados y pusheados**, confirmado en `git log`:
`fed03c9` (manipular), `d1bf8ef` (completar), `e81a978` (corregir),
`27f729e` (escribir_parcial) — los cuatro son ancestros directos de
HEAD en esta rama.

**Commit pendiente — Commit 5**, con su alcance exacto citado
textualmente de `ENGINEERING-GATE-EPICA-C.md:137-142`:

> "Commit 5 — E2E real: recorrido lineal completo de las 6 etapas de
> `ciclo3-input.ts` en un solo paso por un estudiante real, en navegador
> real (deuda explícita que el cierre del Commit 6 de Épica B dejó
> pendiente...)"

No es código nuevo — es una validación de navegador real (mismo
criterio de cierre que gobernó Épica B) más el cierre formal de la
épica.

---

## 2. ¿Quedó resuelta por cambios posteriores?

**No — y con evidencia directa de que ningún cambio posterior la toca,
no solo ausencia de mención:**

- `git log --oneline 27f729e..HEAD -- frontend/src/lib/experiences/
  module1/ciclo3-input.ts` → **vacío**. Ningún commit tocó el archivo
  desde que se cerró el Commit 4.
- `git log --since=2026-07-25 -- frontend/src/components/experience/
  PythonBridge.tsx frontend/src/hooks/usePyodide.ts` → **vacío**. El
  mecanismo subyacente de `input()` real (Worker, puente Pyodide) no
  tiene ningún cambio desde entonces tampoco — no hay drift que
  invalide lo ya migrado ni que obligue a repetir los Commits 1-4.
- `git log --all --since=2026-07-25 --grep="ciclo3|Épica C|CodeLab" -i`
  → **vacío** en todas las ramas locales. Ninguna sesión posterior tocó
  esta línea de trabajo, ni la retomó ni la mencionó.

**Por qué no aplica ninguno de los tres escenarios de "superación
arquitectónica":** la migración a LangGraph Runtime, el retiro de
BaseAgent/SwarmOrchestrator (ADR-0011) y los cambios del ConsensusEngine
(RFC-0006) son **exclusivamente backend** (`backend/runtime/`). Épica C
es **exclusivamente frontend/contenido pedagógico** — un laboratorio de
Python interactivo (`CodeLab.tsx` + Pyodide en el navegador) que no
depende de ningún agente, capacidad ni deliberación del runtime. No hay
ningún punto de contacto arquitectónico entre ambas líneas de trabajo
que pudiera hacer que una absorbiera o superara a la otra.

---

## 3. Clasificación

**Pendiente real — ni deuda que haya quedado obsoleta, ni trabajo
superado por arquitectura nueva.** El escenario correcto (de los tres
que planteaste) es el que no involucra ningún cambio de arquitectura: el
trabajo sigue exactamente donde se dejó, sin ningún factor externo que
lo haya invalidado o completado por otro camino.

- **No es deuda superada**: nada reemplazó la necesidad del recorrido
  E2E — Épica B ya había dejado la misma deuda una vez (QA no lineal),
  y Épica C repitió el patrón sin cerrarlo tampoco.
- **No requiere código nuevo**: los Commits 1-4 ya migraron las 4
  etapas con el patrón validado (`{input1}`, sin `simulatedInputs`, sin
  valores hardcodeados) — confirmado sin drift.
- **Sí sigue siendo una validación real pendiente**, bajo la propia
  Regla de Cierre de CLAUDE.md ("un recorrido no se considera terminado
  hasta que un usuario real pueda completarlo de principio a fin... en
  navegador real") — el mecanismo de `input()` real de las 4 etapas
  nunca se probó encadenado con las otras 2 (`observar`,
  `escribir_completo`) en una sola sesión de estudiante.

---

## 4. No se reabre la línea sin decisión — queda una pregunta operativa, no arquitectónica

A diferencia de las Fases 4-6, aquí no hay una decisión de producto o
arquitectura pendiente — el criterio de cierre ya está definido y
acordado desde el propio Gate original. Lo único que falta es
**ejecutar** esa validación (recorrido de navegador real de las 6
etapas de `ciclo3-input.ts`) y cerrar formalmente la épica, tal como se
hizo con Épica B.

**No se ejecuta en este documento** — queda como decisión operativa
simple para la siguiente acción: ¿se retoma ahora el Commit 5 (recorrido
E2E + cierre), o se mantiene diferido mientras continúa esta cadena de
fases de auditoría?
