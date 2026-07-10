# Architecture Integrity Review v1.0

- **Fecha:** 2026-07-10
- **Alcance:** todos los documentos aceptados — Constitución (P1–P15),
  RFC-0000..0004, RFC-0006, RFC-0007, CONCEPT-0001, CONCEPT-0002,
  WALKTHROUGH-0001.
- **Método:** revisión cruzada buscando (a) contradicciones entre
  documentos, (b) términos con más de una definición normativa,
  (c) ciclos de dependencia, (d) estado del registro de hipótesis.
- **Veredicto:** base sólida. **Cero contradicciones conceptuales, cero
  ciclos.** Dos defectos de redacción en documentos aceptados (F1, F2) y
  un hueco de gobernanza (F3).
- **Resolución (2026-07-10):** F1 y F2 aprobados y aplicados (commit
  `00abf02`; RFC-0004 rev. 3, RFC-0002 rev. 4). **F3 rechazado en su forma
  propuesta y resuelto por el tesista con la categoría Concept Standard**
  (autoridad semántica propia, distinta del rango RFC — regla en README y
  RFC-0000 rev. 3). El glosario de esta revisión se convirtió en documento
  vivo: `VOCABULARY.md`. Se añadió además la Revisión de Conformidad de
  Especificación (RFC-0000 rev. 3) para la fase de implementación.

## Hallazgos

### F1 — "Reapertura" en RFC-0004 contradice a CONCEPT-0002 (redacción)

RFC-0004 §4 (tabla de enrutamiento, aceptado ANTES de la taxonomía) dice:
*"deliberación aplazada cuya evidencia faltante ya llegó → **reapertura de
la deliberación**"*. CONCEPT-0002 §5 estableció después que las
deliberaciones jamás se reabren (P14/INV-3): se convoca una **nueva
deliberación que referencia a la anterior**. La semántica pretendida era
la misma; la palabra es incorrecta.

**Corrección propuesta:** en la fila de la tabla, "reapertura de la
deliberación" → "convocatoria de una nueva deliberación enlazada
(CONCEPT-0002 §5)". Micro-enmienda de redacción a RFC aceptado — requiere
aprobación del tesista.

### F2 — Adaptar "escribe una decisión" en RFC-0002 (redacción)

RFC-0002 §3 (tabla de capacidades, anterior a la separación facts/claims)
dice que Adaptar escribe *"**decisión** de diseño de experiencia"*. Desde
RFC-0003/0006, las capacidades escriben **claims tipo propuesta**; solo el
Kernel deriva decisiones (INV-6, P15). Orientar y Remediar ya dicen
"propuesta"; Adaptar es la única fila desalineada.

**Corrección propuesta:** "decisión de diseño de experiencia" →
"propuesta de diseño de experiencia". Micro-enmienda a RFC aceptado —
requiere aprobación del tesista.

### F3 — Las notas conceptuales tienen fuerza normativa sin lugar en la jerarquía (gobernanza)

CONCEPT-0001 fue declarado "criterio normativo del RFC-0006" y
CONCEPT-0002 fija la regla de oro que el RFC-0006 obedece — pero la
jerarquía normativa del README (`Constitución → RFC → ADR → código`) no
menciona las notas conceptuales. Hoy su autoridad es de facto.

**Corrección propuesta:** declarar en el README que las **notas
conceptuales Aceptadas tienen rango normativo de RFC** (mismo ciclo de
vida RFC-0000, misma subordinación a la Constitución). Requiere aprobación
del tesista.

### F4 — Nota menor, sin cambio requerido

RFC-0001 fijó el ciclo canónico *Capturar → Interpretar → Deliberar →
Adaptar → Validar*; RFC-0002 (Contexto) cita el ciclo v2.1 original
(*…Construir…*) como insumo histórico. No es contradicción — una cita
histórica y un canon vigente —, pero se deja documentado que **el ciclo
normativo es el de RFC-0001 §2**.

## Verificaciones que salieron limpias

**Definición normativa única.** Cada término del vocabulario tiene
exactamente un documento definitorio:

| Término | Locus normativo |
|---------|-----------------|
| Kernel, Graph Engine, Platform Boundary, regla de control, Runtime Contract | RFC-0001 |
| responsabilidades R1–R7, 8 capacidades, resultado esperado, sesión agregadora, tensiones canónicas | RFC-0002 |
| anatomía (8 secciones), FactEntry/ClaimEntry, asunto, provenance, cadena epistemológica, StateTransition, INV-1..12 | RFC-0003 |
| TransitionIntent, activación, reglas de enrutamiento, subordinación del motor, separación razonamiento/consistencia | RFC-0004 |
| confianza efectiva, álgebra A1–A8, δ, θ, límite de reconvocatoria, resolución | RFC-0006 |
| plano de observabilidad, auditoría del contrato, telemetría operativa | RFC-0007 |
| paisaje cognitivo, E1–E6, anti-definición, hipótesis operacional | CONCEPT-0001 |
| D1/D2/D3, latente/bloqueante, regla de la raíz, regla de oro, decisión provisional | CONCEPT-0002 |

Los tres sentidos de "evidencia" (materialización del dominio en RFC-0002,
sentido probatorio de P7, objeto de deliberación) están reconciliados por
el puente terminológico de RFC-0003 (Contexto). Esta tabla funciona como
glosario normativo: un término nuevo sin fila aquí no existe.

**Dependencias.** El grafo documental es acíclico:
Constitución → RFC-0000 → RFC-0001 → RFC-0002 → RFC-0003 → RFC-0004 →
CONCEPT-0001 → CONCEPT-0002 → RFC-0006 → RFC-0007. Las referencias hacia
atrás son todas a documentos ya aceptados; las hacia adelante son solo
delegaciones explícitas ("se evalúa en…").

**Registro de hipótesis (H1–H11).** Ocho resueltas, tres abiertas con
sede asignada — ninguna huérfana ni estancada:

| # | Hipótesis | Estado | Sede |
|---|-----------|--------|------|
| H1 | Facts/Claims/Decisions | ADOPTADA | RFC-0003 rev. 3 |
| H2 | Provenance | ADOPTADA | RFC-0003 rev. 3 |
| H3 | Deferred | ADOPTADA (reubicada) | RFC-0003 §4.1 |
| H4 | Intentions/Resolutions | CERRADA (parcial: término "resolución") | RFC-0006 §6 |
| H5 | Método de obtención | ADOPTADA (dimensión de provenance) | RFC-0007 §4 |
| H6 | Clases de intent | ADOPTADA (sin vocabulario nuevo) | RFC-0006 §6 |
| H7 | Scheduler Policy | RESUELTA | RFC-0006 §5 |
| H8 | Landscape Metrics | ADOPTADA | RFC-0007 §2.2 |
| H9 | Decision Debt | PARCIAL — intra-sesión adoptada; inter-sesión abierta | → RFC-0005 |
| H10 | Confidence Calibration | ABIERTA | → diseño experimental |
| H11 | Evidence Query Model | ABIERTA | → RFC-0010 / experimental |

Abiertas adicionales: extensión *reputación de capacidad* (→ RFC-0005) y
la candidata constitucional *«la explicación se recorre, no se redacta»*
(→ decisión del tesista, registro en README).

**Propuestas constitucionales.** P14 y P15 elevadas y consolidadas; el
registro del README refleja su ciclo de vida completo. Ninguna propuesta
huérfana.

## Recomendación

Aplicar F1 y F2 (micro-enmiendas de redacción) y F3 (regla de gobernanza)
en un único acto con aprobación del tesista, y entrar al RFC-0008 con el
corpus limpio. Ningún hallazgo sugiere volver atrás en decisión
irreversible alguna: los dos defectos encontrados son palabras que
sobrevivieron a decisiones posteriores, no ideas en conflicto.
