# QA integral y cierre — Épica C, Commit 5

> Cierra la deuda de QA que `ENGINEERING-GATE-EPICA-B.md` §9 dejó
> pendiente y que `ENGINEERING-GATE-EPICA-C.md` §6 define como Commit
> 5: recorrido lineal completo, en una sola sesión de navegador real,
> de las 6 etapas de `ciclo3-input.ts` — no introduce código nuevo,
> valida el resultado de los Commits 1–4.

- **Fecha:** 2026-07-25
- **Documento propietario:** `ENGINEERING-GATE-EPICA-C.md` (§6 plan de
  commits, §7 criterios de salida).
- **Máquina:** Windows (la máquina Bazzite que ejecutó los Commits
  1–4 ya no está disponible para esta sesión).

## Método

Recorrido Selenium contra el stack real (frontend Vite + backend
FastAPI + PostgreSQL real + Worker de Pyodide real, sin mocks),
estudiante `estudiante3@upao.edu.pe` (con ruta ya generada), cursor de
`experience-cursor:<moduleId>` reiniciado antes de empezar para
garantizar una sesión limpia desde Ciclo 1 del Módulo 1.

Para las 5 etapas migradas a `input()` real (`manipular`, `completar`,
`corregir`, `escribir_parcial`, `escribir_completo`), se escribió en el
editor el `solutionCode` exacto de `ciclo3-input.ts` (no solo se agotó
intentos para llegar a "Ver solución") y se proveyó un valor de
`input()` real y distinto en cada etapa (nunca el valor legado
hardcodeado `"Ana"`/`"Nico"`), verificando que la consola mostrara ese
valor dinámico y que la tarjeta marcara "Exacto". Adicionalmente:

- **`manipular`**: se ejecutó primero el `starterCode` sin corregir
  (intento deliberadamente incorrecto) para validar el camino de
  error/diagnóstico/`workedExample` antes de escribir la solución.
- **`completar`**: se probó `Cancelar` sobre el panel de `input()` real
  en curso antes de responder — confirma que la ejecución se cierra
  sin colgarse y que `Ejecutar` vuelve a estar disponible.

## Evidencia (capturas)

`docs/qa/epica-c-commit5/` — 11 capturas curadas de la sesión real:
inicio de la escalera (`01`), `observar` con `simulatedInputs` legado
intacto (`02`), el intento incorrecto de `manipular` con diagnóstico y
`workedExample` (`03`), su resolución con `input()` real (`04`), el
panel de `input()` real esperando respuesta (`05`), `Cancelar` en
acción (`06`), y la resolución correcta de `completar`/`corregir`/
`escribir_parcial`/`escribir_completo` (`07`–`10`), y el cierre de
misión con evidencia guardada (`11`).

## Resultado por etapa

| Etapa | `input()` real | `simulatedInputs` | Valor usado | Consola obtenida | Resultado |
|---|---|---|---|---|---|
| `observar` | No (sin migrar, decisión vigente de Arquitectura Pedagógica v1.0) | `['Ana']` (intacto) | `Ana` (legado) | `¿Cómo te llamas? Hola, Ana` | ✅ PASS |
| `manipular` | Sí | — | `Ana` | `¿Cómo te llamas? Bienvenido, Ana` | ✅ PASS |
| `completar` | Sí | — | `Luis` | `¿Cómo te llamas? Hola, Luis` | ✅ PASS |
| `corregir` | Sí | — | `Sofia` | `¿Cómo te llamas? Hola, Sofia` | ✅ PASS |
| `escribir_parcial` | Sí | — | `Toto` | `¿Cuál es tu apodo? Hola, Toto` | ✅ PASS |
| `escribir_completo` | Sí | — | `Renato` | `¿Cómo te llamas? Mucho gusto, Renato` | ✅ PASS |

Casos adicionales verificados:

- **Intento incorrecto (`manipular`)**: ejecutar el `starterCode` sin
  editar produjo `¿Cómo te llamas? Hola, Ana` (input real consumido
  correctamente) sin marcar "Exacto"; el tutor mostró el diagnóstico
  "Tu código corrió sin errores — pero lo que muestra no es
  exactamente lo pedido" junto al `workedExample` de apoyo — ningún
  traceback crudo, ningún estado colgado.
- **Cancelar (`completar`)**: con el panel de `input()` real abierto,
  `Cancelar` cerró la espera de inmediato (`awaitingInput` volvió a
  `false`), `Ejecutar` quedó disponible de nuevo sin recargar la
  página, y un segundo `Ejecutar` completó la etapa normalmente.
- **Cierre de ciclo/misión**: tras `escribir_completo` (sin
  `nextStage`), el ciclo cerró, la evidencia se guardó (toast "Misión
  completada — Tu progreso quedó guardado") y la plataforma navegó
  correctamente a la apertura de curiosidad del Módulo 2 — sin
  pantallas en blanco ni estados rotos.

## Regla de calidad de contenido (§4 de `ENGINEERING-GATE-EPICA-C.md`)

Verificado por `grep` sobre `ciclo3-input.ts`: las únicas menciones
restantes de `"Ana"`/`"Nico"` son (a) narrativa conceptual genérica
sobre por qué hardcodear valores es un problema (no ligada a ninguna
etapa), (b) la etapa `observar`, deliberadamente sin migrar, y (c) un
refuerzo de la fase `decision` fuera del alcance de esta épica (su
propia práctica sigue con `simulatedInputs` intacto, sin tocar). Ningún
`hint`, `hintsByCategory`, `resultExplanation` ni `workedExample` de
las 4 etapas migradas cita un valor hardcodeado que ya no corresponda.

## Regresiones

Sin regresiones observadas en: `OrderingPractice` (Ciclo 1 y 2),
`PredictOutputPractice`, navegación entre fases (concepto → práctica →
consolidar), adaptación real entre etapas (notas "Vamos con calma…" /
"Vas muy bien…" derivadas de respuestas reales de `cycle-evidence`, no
texto fijo), layout de laboratorio (`layout="lab"`, tres zonas), editor
con gutter y consola con chrome de terminal, tarjeta de error traducido
(`PythonErrorCard`), y botón "Ayuda" del tutor.

## Build

```
npm run build   → tsc -b && vite build   ✔ built in 20.64s (sin errores)
```

## Criterios de salida (`ENGINEERING-GATE-EPICA-C.md` §7) — verificación

- [x] Las 4 etapas migradas usan `input()` real, validado con un valor
      dinámico real en navegador (no el legado hardcodeado).
- [x] `observar` sigue exactamente igual que antes — sin tocar.
- [x] Ningún texto visible cita un nombre hardcodeado que ya no
      corresponde a lo escrito realmente.
- [x] Recorrido lineal completo (`observar` → `escribir_completo`, las
      6 etapas, una sola sesión de navegador, un estudiante real).
- [x] Regresión cero en `observar` y en el resto de la plataforma.

## Estado de la Épica C

```
✔ Commit 1 — manipular
✔ Commit 2 — completar
✔ Commit 3 — corregir
✔ Commit 4 — escribir_parcial
✔ Commit 5 — QA integral y cierre (este documento)

Resultado: PASS
```

**Épica C — CERRADA.**
