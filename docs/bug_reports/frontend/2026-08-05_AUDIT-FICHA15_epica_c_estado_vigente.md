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

---

## 5. Commit 5 ejecutado — Épica C cerrada (2026-08-05, misma sesión)

Recorrido lineal real de las 6 etapas de `ciclo3-input.ts`, en un solo
paso de navegador, con Claude in Chrome, contra el stack completo
(frontend `localhost:5173` + backend `localhost:8000`, ambos ya
corriendo). **Ninguna mejora ni refactor adicional realizado durante la
validación** — alcance limitado estrictamente a ejecutar y registrar.

**Cuenta usada:** `ux.nuevo.recorrido@upao.edu.pe` — sesión ya
autenticada y ya posicionada exactamente en Ciclo 3 de Misión 1 al
iniciar esta ficha (pestaña de navegador preexistente, no creada por
esta sesión). No se creó una cuenta nueva: **se evitó deliberadamente
el camino original (crear un estudiante vía Admin)** tras un hallazgo
de seguridad no anticipado — ver "Hallazgo colateral" abajo. Se prefirió
una cuenta de QA ya autenticada y ya en el punto exacto de la
validación, en vez de arriesgar una segunda credencial equivocada.

### Recorrido, etapa por etapa (las 6, en orden real de la UI)

| Etapa | Mecanismo esperado | Resultado observado |
|---|---|---|
| **Observar** | `input()` simulado (decisión pedagógica explícita, NO migrada — Épica C nunca la tocó) | ✅ "SIMULAREMOS QUE EL USUARIO ESCRIBE > Ana" — consola: `¿Cómo te llamas? Hola, Ana`. Confirma que la exclusión deliberada de `observar` sigue vigente. |
| **Manipular** (Commit 1) | `input()` real | ✅ "PYTHON ESTÁ ESPERANDO TU RESPUESTA" — se escribió "Renato" a mano; consola: `¿Cómo te llamas? Bienvenido, Renato`. Sin nombre hardcodeado. |
| **Completar** (Commit 2) | `input()` real | ✅ Mismo patrón — "Renato" capturado correctamente tras completar el código con `input(...)`. |
| **Corregir** (Commit 3) | `input()` real, solo tras arreglar la sintaxis | ✅ Código con comillas faltantes corregido a mano (`input("¿Cómo te llamas? ")`); solo entonces apareció el prompt real. Confirma que el error de sintaxis bloquea antes de llegar a `input()`, como documenta el Gate original. |
| **Escribir desde cero (saludo "Hola")** | `input()` real, código completo escrito por el validador | ✅ Se escribió `apodo = input("¿Cuál es tu apodo? ")` + `print("Hola,", apodo)` desde un editor vacío; respuesta libre "Rena" capturada correctamente. |
| **Escribir desde cero (saludo "Mucho gusto")** (Commit 4, `escribir_parcial`/profundización) | `input()` real | ✅ Se escribió el código completo con el patrón exacto pedido ("Mucho gusto, <nombre>"); respuesta libre "Claude" capturada correctamente — "✓ Exacto — eso es Python real haciendo lo que pediste." |

**Las 6 etapas se completaron en una sola sesión continua, sin recargar
la página ni reiniciar el estado**, tal como exige el criterio de cierre
del Gate original. Al terminar la última etapa, el sistema avanzó
limpiamente a "CONSOLIDAR" (generación de práctica personalizada) sin
ningún error visible ni bloqueo — confirma que el recorrido lineal
completo no revela ninguna regresión de integración entre etapas.

**Verificación adicional (no solo las 5 pasos del protocolo, ya
cubiertos arriba):** en las 3 etapas con `input()` real donde se
escribió una respuesta arbitraria distinta a cualquier valor de ejemplo
del contenido ("Renato", "Rena", "Claude" — ninguno es "Ana"/"Nico",
los nombres hardcodeados que Épica B/C corrigieron), el eco en consola
usó siempre la respuesta real tecleada — confirma en vivo, con datos
frescos, que la migración de Épica B/C sigue sin regresión de contenido
hardcodeado.

### Hallazgo colateral (fuera del alcance de Épica C, registrado, no corregido)

Durante el intento de crear una cuenta de estudiante aislada nueva vía
Admin (`admin@upao.edu.pe`), el login devolvió **"Credenciales
incorrectas. Intentos restantes: 1"** con la contraseña
`Admin2026!` documentada en `backend/seed.py:355/677` y confirmada como
correcta en una validación anterior real (memoria
`research_implementation_mode.md`, 2026-07-02). No se intentó una
segunda vez para no arriesgar un bloqueo de cuenta — se abandonó ese
camino y se usó en su lugar la sesión de estudiante ya autenticada
descrita arriba. **No se investiga la causa aquí** (¿contraseña rotada
en otra sesión? ¿bloqueo previo no relacionado con esta sesión?) —
queda registrado como hallazgo para una fila propia de auditoría futura,
fuera del alcance de Épica C.

### Cierre formal de Épica C

**Épica C — Generalización/Consolidación del Runtime Interactivo: CERRADA.**
Commits 1-5/5 completos (`fed03c9`, `d1bf8ef`, `e81a978`, `27f729e` +
esta validación E2E). Mismo criterio de cierre que Épica B: código +
validación real en navegador real, sin mocks de dominio. Sin código
modificado por esta ficha — el cierre es documental, registrando la
validación ya ejecutada.
