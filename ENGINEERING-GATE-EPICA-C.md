# Engineering Gate — Épica C: Consolidación del runtime interactivo

> Planifica la implementación. Documento de planificación puro — cero
> código todavía. Sigue la misma disciplina que Épica B
> (`ENGINEERING-GATE-EPICA-B.md`): Gate antes de código, commits
> pequeños, QA real en navegador, evidencia sin inflar.

- **Fecha:** 2026-07-25
- **Documento propietario:** ninguno previo específico de esta épica —
  se apoya directamente en `ENGINEERING-GATE-EPICA-B.md` (arquitectura
  del runtime ya construida y cerrada) y en
  `docs/architecture/pedagogical/` (Arquitectura Pedagógica v1.0,
  congelada — citada, no reabierta).

---

## 1. Hallazgo del relevamiento (motiva y acota esta épica)

Antes de proponer alcance, se relevó **todo** el contenido autorado de
la plataforma buscando usos de `input(` (`ciclo1-instrucciones-
precisas.ts`, `ciclo2-variables.ts`, `module2.ts`,
`experienceOrchestrator.ts`, además de `ciclo3-input.ts`).
**Resultado: `ciclo3-input.ts` es el ÚNICO lugar de toda la
plataforma que usa `input()`.** Los demás archivos con `pythonBridge`
enseñan otros conceptos (instrucciones precisas, variables) y nunca
llaman a `input()`.

**Consecuencia directa para el alcance:** Épica C no es una
generalización transversal del runtime a "otros laboratorios" —no
existen, hoy, otros laboratorios candidatos—. Es la **consolidación
completa del único flujo interactivo existente**: las 5 etapas de
`ciclo3-input.ts` que quedaron en el mecanismo legado tras Épica B
(que migró solo la última, `escribir_completo`).

## 2. Objetivo

Migrar las etapas restantes de `ciclo3-input.ts` que tiene sentido
migrar (ver §3) al mecanismo interactivo real construido en Épica B,
usando exactamente el mismo modelo `{inputN}` ya validado en el
Commit 6 (`ENGINEERING-GATE-EPICA-B.md` §9) — sin inventar ningún
mecanismo nuevo.

## 3. Alcance

**Etapas que migran** (confirmado por el tesista, con justificación
pedagógica explícita):
- `manipular` — el estudiante ya modifica código activamente.
- `completar` — el estudiante ya completa código activamente.
- `corregir` — el estudiante ya corrige código activamente.
- `escribir_parcial` — el estudiante ya escribe código activamente.

**Etapa que NO migra:** `observar`. Su propósito pedagógico es que el
estudiante MIRE un ejemplo ya resuelto correr con un valor predecible
— no experimentar con entradas propias; el estudiante todavía no
escribió ni modificó nada en esa etapa. Pedirle un `input()` real ahí
añadiría una interacción no relacionada con el objetivo de la
actividad (carga cognitiva sin aprendizaje asociado).

**Esto es una decisión de diseño vigente de la Arquitectura
Pedagógica v1.0, no una limitación técnica ni una exclusión
permanente.** Si esa arquitectura cambia en el futuro, la decisión de
`observar` puede revisarse — mediante un nuevo Engineering Gate, no
dentro de esta épica.

**Fuera de alcance:**
- `observar` (ver arriba).
- Cualquier laboratorio fuera de `ciclo3-input.ts` — no existen
  candidatos reales hoy (§1).
- Retirar `simulatedInputs` — sigue vigente la decisión de
  coexistencia de Épica B §5.
- Nuevo mecanismo de validación — se reutiliza `{inputN}` /
  `resolveExpectedOutput` tal cual, sin cambios.
- Seguridad del sandbox Docker — épica de hardening aparte, no
  relacionada con esta (decisión explícita del tesista al priorizar
  Opción B sobre Opción A).

## 4. Contenido real por etapa (auditado, no supuesto)

Las 4 etapas comparten el mismo patrón: **un solo `input()` cada
una** (nunca dos), con un valor hardcodeado en `expectedOutput` y
repetido en `hintsByCategory.salida` — el mismo defecto de contenido
que se corrigió en `escribir_completo` durante el Commit 6.

| Etapa | `simulatedInputs` hoy | `expectedOutput` hoy | Migra a |
|---|---|---|---|
| `manipular` | `['Ana']` | `'¿Cómo te llamas? Bienvenido, Ana'` | `'¿Cómo te llamas? Bienvenido, {input1}'` |
| `completar` | `['Ana']` | `'¿Cómo te llamas? Hola, Ana'` | `'¿Cómo te llamas? Hola, {input1}'` |
| `corregir` | `['Ana']` | `'¿Cómo te llamas? Hola, Ana'` | `'¿Cómo te llamas? Hola, {input1}'` |
| `escribir_parcial` | `['Nico']` | `'¿Cuál es tu apodo? Hola, Nico'` | `'¿Cuál es tu apodo? Hola, {input1}'` |

**Casos especiales ya verificados, sin necesitar cambios adicionales:**
- `corregir` tiene un error de sintaxis intencional en `starterCode`
  (`input(¿Cómo te llamas? )`, sin comillas). Si el estudiante no lo
  corrige, Python lanza `SyntaxError` ANTES de llegar a `input()` —
  `run()` resuelve con `result.error` seteado, nunca llega a pedir
  `awaitingInput`. Ya cubierto por el manejo de errores existente
  (`classifyPythonError` → categoría `sintaxis`), sin tocar código.
- `completar` tiene un hueco (`_____`) en vez de `input`. Si no se
  completa, es un `NameError` (nombre no definido) — mismo
  razonamiento: falla antes de llegar a `input()`, ya cubierto.

## 5. Riesgos

- Bajo. El modelo `{inputN}` y `resolveExpectedOutput` ya están
  construidos, probados con código real (nominal + caso límite) y en
  producción de código (no de despliegue) desde el Commit 6 — esta
  épica los REUTILIZA, no los modifica.
- Único riesgo real: repetir en las etapas restantes la misma pista
  desactualizada (`hintsByCategory.salida` citando el nombre
  hardcodeado) si se migra `expectedOutput` sin revisar el texto de
  las pistas — mitigado explícitamente en el plan de commits (§6).

## 6. Estrategia de implementación

Un commit por etapa (misma disciplina de "cambios pequeños" que
Épica B) — cada uno repite el patrón ya validado: quitar
`simulatedInputs`, `expectedOutput` a `{input1}`, corregir
`hintsByCategory.salida` si cita el valor hardcodeado.

```
Commit 1 — Migra 'manipular'
Commit 2 — Migra 'completar'
Commit 3 — Migra 'corregir'
Commit 4 — Migra 'escribir_parcial'
Commit 5 — E2E real: recorrido lineal completo de las 6 etapas de
           ciclo3-input.ts en un solo paso por un estudiante real,
           en navegador real (deuda explícita que el cierre del
           Commit 6 de Épica B dejó pendiente — ver
           ENGINEERING-GATE-EPICA-B.md §9, "Precisión sobre el
           alcance real de la QA")
```

No es la secuencia final obligatoria — Engineering Gate por commit
sigue vigente (`CLAUDE.md`: 4 preguntas antes de cada uno), aunque
dado que las 4 primeras repiten un patrón ya validado, es esperable
que ese gate sea una verificación corta, no una ronda de revisión
narrada (`CLAUDE.md`, "Engineering Review dirigida").

## 7. Criterios de salida

- Las 4 etapas (`manipular`, `completar`, `corregir`,
  `escribir_parcial`) usan `input()` real, validado con un valor
  dinámico real en navegador (no el valor legado hardcodeado).
- `observar` sigue exactamente igual que hoy — sin tocar.
- Ninguna pista (`hintsByCategory.salida`) cita un nombre hardcodeado
  que ya no corresponde a lo que el estudiante realmente escribió.
- Recorrido lineal completo (`observar` → `escribir_completo`, las 6
  etapas, una sola sesión de navegador, un estudiante real) — cierra
  la precisión que el Commit 6 de Épica B dejó pendiente.
- Regresión cero en `observar` y en el resto de la plataforma
  (`ciclo1`, `ciclo2`, `module2.ts` — nunca tocados por esta épica).
