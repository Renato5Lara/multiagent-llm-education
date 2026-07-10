# WALKTHROUGH-0001 — Del diagnóstico a la remediación visual

- **Propósito:** validar que los conceptos definidos en RFC-0001, RFC-0002 y
  RFC-0003 bastan para narrar una ejecución completa del sistema — sin
  LangGraph, sin código. Si el recorrido exige un concepto que no existe en
  los RFC, se incorpora antes de diseñar el runtime (orden del tesista,
  2026-07-10).
- **Resultado:** el modelo narra la ejecución completa. Se detectaron **dos
  grietas** (incorporadas en RFC-0003 rev. 4) y **dos confirmaciones** (que
  refuerzan decisiones ya registradas). Detalle en Hallazgos.

## Escenario

María trabaja el módulo *Condicionales*. Responde una actividad
diagnóstica con errores concentrados en COMP-2. El sistema decide remediar
con una explicación visual, la entrega y valida su efecto.

## Recorrido (cada T*n* es una StateTransition)

**T0 — Apertura.** El Platform Boundary abre la sesión: se crea el
`LearningState` con `identidad` completa (sesión, María, student model
v7, objetivo "Condicionales", versiones de banco y política) — INV-1. El
`contexto` carga el student model v7 (tendencia visual moderada, COMP-2
frágil), la ruta y la estructura del módulo — inmutables (INV-2).

**T1–T2 — Capturar (facts).** María envía sus respuestas; el Boundary
traduce.
- T1: facts de resultados — ítems 3, 4 y 8 incorrectos, todos de COMP-2.
  Autor: **Evaluar**; provenance: `instrumento(banco v2, ítems 3,4,8)`.
- T2: facts de telemetría — 35 s por ítem, un intento, sin relecturas.
  Autor: **Platform Boundary** (hecho del mundo, sin capacidad natural
  productora → **Grieta A**); provenance: `telemetría`.
  Los reducers validan INV-4 (autor + provenance, sin respaldo) y aplican;
  cada transición emite sus Domain Events y checkpointea.

**T3–T4 — Interpretar (claims).**
- T3: **Diagnosticar** afirma *"COMP-2 no dominada"*, confianza 0.78,
  respaldo → {T1}; provenance: `regla(scoring)`.
- T4: **Modelar** afirma *"el patrón de error es conceptual, no de
  atención"*, confianza 0.71, respaldo → {T1, T2, contexto: student model
  v7} (referencia al contexto → **Grieta B**); provenance: `llm(modelo,
  versión, prompt-id)` — no-determinismo grabado, replay-safe por P12.

**T5–T6 — Proponer (claims tipo propuesta).**
- T5: **Remediar** propone *"reforzar Condicionales antes de avanzar"*,
  respaldo → {T3, T4}.
- T6: **Orientar** propone *"avanzar al siguiente objetivo con
  andamiaje"*, respaldo → {T3, contexto: ruta}.
  Dos propuestas vigentes en conflicto: **tensión canónica n.º 1**
  (RFC-0002 §4).

**T7 — Deliberar.** El enrutamiento — función pura del estado (regla de
control, RFC-0001 §3) — encuentra dos propuestas en tensión y convoca la
deliberación. El Kernel registra: participantes {T5, T6}, posiciones,
regla de resolución (la define RFC-0006; aquí: prioridad a brecha en
competencia crítica), resultado **resuelta**, claims aceptados {T5},
**confianza de la resolución 0.74**. INV-7 y INV-8 satisfechas: solo
claims sobre la mesa.

**T8 — Decidir (1).** Decisión *"remediar COMP-2 en Condicionales"*,
referencia → T7 (INV-6), estado `pendiente-de-validación` (INV-12). La
transición actualiza la proyección `ejecución`: objetivo de intervención
vigente (INV-9: sigue habiendo uno solo).

**T9 — Adaptar (claim tipo propuesta).** **Adaptar** propone *"explicación
visual interactiva, profundidad fundamentos"*, **con sus alternativas
evaluadas dentro de la propuesta**: textual (descartada: modelo v7 + T4),
ejemplo de código en frío (descartada: prematuro sin el concepto);
respaldo → {T3, T4, T5}; provenance: `llm(...)`. No hay propuesta rival ni
evidencia en contra → **no se convoca deliberación** (P8: el ceremonial
sin desacuerdo posible está prohibido).

**T10 — Decidir (2).** Decisión *"presentar explicación visual X"*,
referencia → T9 (claim-propuesta único, INV-6), `pendiente-de-validación`.

**T11 — Ejecutar en el mundo.** La decisión sale por el Platform Boundary;
la plataforma presenta el contenido. T11: fact *"contenido X entregado y
completado, 4 m 12 s"* — autor: Boundary; provenance: `telemetría`.
(**Confirmación 2**: la distinción Decision/Execution de H4 se expresa hoy
como decisión + fact de entrega.)

**T12–T13 — Validar.**
- T12: facts de la actividad de refuerzo — 4 de 5 ítems de COMP-2
  correctos (Evaluar, `instrumento`).
- T13: **Validar** afirma *"la adaptación funcionó: dominio estimado de
  COMP-2 pasó de 0.40 a 0.75 tras la explicación visual"*, respaldo →
  {T10, T11, T12} (referencia a una decisión → **Grieta B**). La
  transición marca T10 como `validada` (INV-12 cerrada con veredicto).

**T14 — Cierre.** `salidas`: propuesta de student model v8 (Modelar:
eficacia de la modalidad visual en condicionales ↑), ruta actualizada,
resumen destilado para la capa de memoria (RFC-0005). La sesión consumió
v7 y propone v8 — jamás lo mutó (RFC-0002 §1).

## Verificación del Runtime Contract (sobre la decisión T10)

| Pregunta | Respuesta en el estado |
|----------|------------------------|
| ¿Qué observó? | T1, T2 (facts con provenance) |
| ¿Qué interpretó? | T3, T4 (claims con respaldo a los facts) |
| ¿Qué alternativas evaluó? | T5 vs T6 (nivel intervención) y las alternativas internas de T9 (nivel modalidad) |
| ¿Por qué eligió una? | T7 (deliberación con regla y confianza) y T10 → T9 |
| ¿Qué ocurrió después? | T11, T12, T13 (entrega, resultados, veredicto) |

La cadena `T13 → T10 → T7 → {T5,T6} → {T3,T4} → {T1,T2}` es navegable por
respaldo: recorrido causal completo, cinco preguntas respondidas con datos
del estado. **El contrato se satisface sin ningún concepto externo a los
RFC.**

## Hallazgos

**Grietas (incorporadas en RFC-0003 rev. 4, sujetas a ratificación):**

- **A — Hechos del mundo sin autor.** La telemetría cruda y el ciclo de
  vida de la sesión no los produce ninguna capacidad. Ajuste: el Platform
  Boundary puede autorar facts (jamás claims) — INV-4 ampliada.
- **B — Dominio del respaldo incompleto.** T4 necesita citar el contexto
  (student model v7) y T13 necesita citar la decisión que valida; INV-5
  solo permitía facts/claims — mientras la tabla §5 del propio RFC ya
  asumía que Validar se respalda en la decisión. Inconsistencia interna
  detectada y corregida: respaldo → entradas vigentes (facts, claims,
  decisiones) + contexto versionado.

**Confirmaciones (sin cambio, refuerzan lo registrado):**

1. **La convocatoria de deliberación no necesita concepto nuevo**: es
   enrutamiento — función pura del estado sobre claims en conflicto (regla
   de control, P12). Su mecánica pertenece al RFC-0004; su regla de
   convocatoria, al RFC-0006.
2. **Decision ≠ Execution (H4)**: el modelo lo expresa hoy (decisión
   entregada por el Boundary + fact de entrega); la hipótesis H4 evalúa si
   merece representación explícita.

## Conclusión

El modelo conceptual de RFC-0001/0002/0003 es **suficiente para narrar una
ejecución completa**, incluida una deliberación real, una adaptación con
alternativas y su validación. Las dos grietas halladas eran de dominio de
referencias/autoría, no de conceptos faltantes. El diseño del Graph Engine
(RFC-0004) puede comenzar.
