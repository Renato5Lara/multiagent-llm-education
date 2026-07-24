# Checkpoint de alineación — Épica B

> Registra las decisiones del tesista tras `AUDITORIA-EPICA-B.md` y
> `SPIKE-B0-PYODIDE-STDIN.md` (ambos commiteados en `6a69b75`). No es
> un roadmap ni una decisión de arquitectura — resuelve las 4
> preguntas diagnósticas pendientes (ver
> `epica_b_auditoria_spike_2026_07_24` en memoria) antes de escribir
> cualquier RFC/ADR o Engineering Gate de implementación.

- **Fecha:** 2026-07-24

---

## 1. ¿Qué parte del problema se ataca primero?

**Decisión: `input()` interactivo real.** No el sandbox Docker por
ahora (ver `AUDITORIA-EPICA-B.md` §5, "Próximo paso").

Razón registrada por el tesista: es el hallazgo principal de la
auditoría (el valor de `input()` siempre lo fija el autor del
contenido, nunca el estudiante en vivo); tiene alcance acotado (no
obliga a rediseñar la infraestructura de ejecución); permite validar
el valor pedagógico antes de introducir una segunda variable (motor de
ejecución distinto); la decisión es reversible (la UI/flujo de
`input()` sigue siendo útil aunque el motor de ejecución cambie
después).

## 2. ¿Qué vía del Spike B-0 se prioriza?

**Decisión: Worker + `SharedArrayBuffer` + `Atomics.wait()`** (opción
2 de las dos vías reales que documentó `SPIKE-B0-PYODIDE-STDIN.md`).

Razón registrada: es la única vía que sostiene una UI propia del
laboratorio (consistente con la estética `neural-glow`/glass del
resto de la plataforma) en vez del diálogo nativo `prompt()`
(funcional pero no estilizable, bloquea la pestaña entera).

**Punto abierto que esta decisión NO resuelve — ver `SPIKE-B0-PYODIDE-STDIN.md`,
"Conclusión técnica" / "No verificado empíricamente en este spike":**
el spike fue de documentación, no de código. No se ejecutó ningún
experimento real contra Pyodide en este proyecto para confirmar que el
patrón Worker+`Atomics.wait()` efectivamente pausa y reanuda `input()`,
ni se verificó si el CDN de Pyodide (`cdn.jsdelivr.net`) es compatible
con las cabeceras `COOP`/`COEP` que este patrón exige. Es exactamente
el tipo de "hipótesis técnica crítica sin verificar" que, por regla
del propio tesista (2026-07-24, citada en `SPIKE-B0-PYODIDE-STDIN.md`),
bloquea escribir un roadmap. **Implica un Spike B-1 (empírico, con
código real) antes del Engineering Gate de implementación** — no
decidido en este checkpoint, queda como recomendación a confirmar.

## 3. ¿Qué hacemos con el endpoint de sandbox sin autenticación?

**Decisión: se registra como mini-épica de seguridad independiente.**
No bloquea Épica B.

Razón registrada: el endpoint (`POST /api/sandbox/execute*`, hallazgo
de `AUDITORIA-EPICA-B.md` §6) es un riesgo preexistente que Épica B no
introduce ni agrava mientras la decisión #1 mantenga la ejecución en
Pyodide/cliente (el sandbox Docker sigue huérfano del flujo del
estudiante). Si en el futuro se decidiera conectar el sandbox Docker
real, esa mini-épica de seguridad debe cerrarse antes de habilitar ese
flujo — no es aceptación pasiva del riesgo, es una dependencia
explícita para ese escenario futuro.

## 4. ¿Qué caso real se usa para el recorrido E2E de cierre?

**Decisión: `ciclo3-input.ts` (Módulo 1).**

Razón registrada: único contenido real que usa `simulatedInputs` hoy;
ya fue el caso empleado durante la auditoría (seis peldaños
encadenados — observar→manipular→completar→corregir→escribir con
andamiaje→escribir sin andamiaje); permite comparar directamente el
comportamiento antes/después de esta mini-épica sobre el mismo
contenido, en vez de un escenario artificial. Contenido nuevo solo se
autoraría si, durante el Engineering Gate, se demuestra que
`ciclo3-input.ts` no ejercita algo necesario (p. ej. múltiples
`input()` consecutivos).

---

## Próximo paso

No se abre el Engineering Gate de implementación todavía. El punto
abierto de la decisión #2 (Spike B-1 empírico) queda pendiente de
confirmación del tesista antes de proceder.
