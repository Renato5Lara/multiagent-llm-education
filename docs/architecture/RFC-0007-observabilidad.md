# RFC-0007 — Observabilidad

- **Estado:** Aceptado (2026-07-10 — con elevación de P14 aprobada en
  formulación generalizada del tesista; H11 registrada en la aceptación)
- **Autor:** Equipo de arquitectura (Claude + tesista)
- **Fecha:** 2026-07-10
- **Aprueba:** Renato Lara (tesista / Product Owner)
- **Gobernado por:** FOUNDATIONAL_PRINCIPLES.md (P6, P7, P9, P12, P15),
  RFC-0003, RFC-0004, RFC-0006, CONCEPT-0001
- **Capa (RFC-0001 §1):** Kernel (emisión) + plano de observabilidad
  (consumidores, fuera del camino caliente)
- **Runtime Contract:** hace auditables las cinco preguntas — este RFC es
  el contrato volviéndose verificable

## Objetivo

Definir cómo el runtime se observa a sí mismo: trazas, métricas,
explicaciones y auditoría del Runtime Contract — todo como derivación de
la historia, jamás como instrumentación añadida. Resolver las herencias
acumuladas: H5, H8, H9 (métricas), las métricas de la `base` (RFC-0004) y
del consenso (RFC-0006), y **el veredicto sobre la elevación de P14**.

## Decisión irreversible

> **Toda observabilidad es derivación de la historia (Domain Events +
> checkpoints): el runtime no se instrumenta — se lee. Los observadores
> jamás escriben.**

No existe una segunda tubería de telemetría dentro del runtime. Cualquier
métrica, traza o explicación que no pueda derivarse de la historia no
existe legítimamente (P7). Y ningún observador produce transiciones: el
plano de observabilidad es estrictamente de lectura — observar no perturba.

## Contexto

Herencias que este RFC debe resolver:

- La verificación mecánica del Runtime Contract (RFC-0001 §4, RFC-0003 §5).
- **H5** — método de obtención en la provenance (RFC-0003 §7).
- **H8** — métricas del paisaje (CONCEPT-0001).
- **H9** — métricas de la Decision Debt, parte intra-sesión (CONCEPT-0002).
- Métricas de la `base` (RFC-0004 §1) y del consenso (RFC-0006).
- **P14** — la elevación constitucional de la inmutabilidad de la
  historia quedó diferida "hasta que se compruebe que la observabilidad y
  el replay descansan en ella" (RFC-0003 §4). Ese momento es este RFC.
- Relación con la hipótesis: este RFC construye el instrumento de medición
  — los criterios E1–E6 y la hipótesis operacional (CONCEPT-0001) se
  responden con lo que aquí se define. El Modo Evidencia de la plataforma
  y la exportación de investigación son sus consumidores.

## Propuesta

### 1. La fuente única: historia, no instrumentación

El circuito de mutación (RFC-0003 §4) ya emite todo lo observable: cada
StateTransition produce sus Domain Events y su checkpoint. El plano de
observabilidad **consume**; no inyecta sondas en nodos, no añade logging
semántico en capacidades, no mantiene contadores propios dentro del
estado. Dos garantías se refuerzan mutuamente:

- **Registro**: el flujo de eventos se persiste al emitirse (el detalle de
  persistencia es del RFC-0008).
- **Reconstruibilidad**: como los eventos son derivada de las transiciones
  (INV-10) y los checkpoints las capturan todas, el flujo de eventos es
  *recomputable* desde los checkpoints. La observabilidad no puede
  perderse sin perder el estado mismo.

### 2. Los tres productos

**2.1 Trazas — qué pasó.** La secuencia de transiciones de una sesión, con
sus eventos, navegable hacia atrás por `respaldo` y hacia adelante por
derivación (claims → deliberación → decisión → entrega → validación). La
traza no se construye: se recorre.

**2.2 Métricas — cuánto y cómo.** Catálogo normativo por fuente; toda
métrica es una función pura sobre la historia (los umbrales de reporte son
política; las definiciones, de este RFC):

| Fuente | Métricas |
|--------|----------|
| Paisaje (H8 — ADOPTADA) | densidad (claims vigentes por asunto), estabilidad (cambio del paisaje entre transiciones), conflicto (tensiones vigentes, latentes vs bloqueantes), entropía (dispersión de confianzas efectivas por asunto), tiempo lógico de estabilización |
| Ejecución (RFC-0004) | obsolescencia media de la `base`, tasa de intents rechazados por estado obsoleto, frecuencia de replanificación, transiciones por sesión |
| Consenso (RFC-0006) | frecuencia de convocatoria (y de no-convocatoria registrada), márgenes de resolución, confianza de resolución, tasas de aplazamiento / provisional / escalada, longitud de cadenas de reconvocatoria |
| Decision Debt (H9 — parte intra-sesión ADOPTADA) | deuda abierta al cierre, edad lógica media de la deuda, tasa de pago (validadas vs no-observadas); la parte inter-sesión queda para RFC-0005 |
| Enjambre (E1–E6) | % de decisiones con deliberación multi-capacidad, distribución de atribución por capacidad, variabilidad de secuencias bajo reglas idénticas, respuesta de confianzas a validación |

**2.3 Explicaciones — por qué.** La explicación de una decisión es el
recorrido de su cadena causal, renderizado: las cinco respuestas del
Runtime Contract extraídas del estado (RFC-0003 §5). **La explicación se
recorre, no se redacta** (P15, P6): ningún LLM resume "lo que el sistema
pensó" — si el recorrido no basta para explicar, el defecto está en el
diseño del nodo, no en el renderizador.

### 3. Auditoría del Runtime Contract

Un auditor — derivación pura, fuera del camino caliente — verifica para
cada decisión que las cinco preguntas son respondibles: la cadena
`decisión → (deliberación) → claims → facts` existe, está completa y sus
referencias son válidas. Sus hallazgos son defectos de diseño (RFC-0001
§4: "un nodo que no puede responder no entra al grafo") y **viven fuera
del estado** — un observador no escribe (decisión irreversible). El
auditor corre en desarrollo y en cada sesión de evidencia; su reporte es
parte del material de la sustentación: *el contrato no se declara, se
audita*.

### 4. Veredictos sobre herencias

- **P14 — SE RECOMIENDA LA ELEVACIÓN.** La comprobación pedida existe:
  los tres productos (§2), la auditoría (§3) y la reconstruibilidad (§1)
  son derivaciones sobre una historia append-only. Si la historia pudiera
  reescribirse, las métricas serían inestables, las explicaciones
  falsificables post-hoc y P7 inverificable. Formulación propuesta para
  la Constitución (decisión del tesista en la aceptación de este RFC):

  > **P14 — La historia es inmutable.** El registro histórico del estado
  > (facts, claims, deliberaciones, decisiones) jamás se reescribe; toda
  > corrección es una nueva entrada que supersede a la anterior. La
  > historia es el activo científico del sistema.

  *Resolución:* el tesista aprobó la elevación con una formulación más
  general que conecta RFC-0003, RFC-0006 y este RFC — el texto vigente es
  el de la Constitución (rev. 3).

- **H5 — ADOPTADA como dimensión del detalle de provenance.** El detalle
  de `instrumento` y `telemetría` declara el método de obtención (opción
  múltiple, ejercicio interactivo, ejecución de código). No es un campo
  nuevo del sobre: es la especificación del `detalle` que RFC-0003 §3.1 ya
  contenía — clarificación, no enmienda.
- **H8 — ADOPTADA** como familia de métricas del paisaje (§2.2), todas
  proyecciones deterministas (coherentes con A3/A4: tiempo lógico, sin
  reloj).
- **H9 — ADOPTADA en su parte intra-sesión** (§2.2); si la deuda cruza
  sesiones se decide en RFC-0005.

### 5. Consumidores (por el Boundary, jamás dentro)

Tres superficies, todas de solo lectura, servidas a través del Platform
Boundary (RFC-0010): la **exportación de investigación** (datasets para el
análisis de la tesis — la plataforma ya tiene la ruta `/api/research` y
`/evidencia/investigacion` como precedente de v1), el **Modo Evidencia**
de la plataforma (visualización en vivo para la sustentación — que por P7
ahora muestra deliberaciones reales, no simuladas), y el **visor de
replay** (cuya mecánica de re-ejecución pertenece al RFC-0008; este RFC
define qué expone: estados, eventos, paisaje reconstruido por transición).

### 6. Hipótesis registrada

**H11 — Evidence Query Model (REGISTRADA, no incorporada):** propuesta del
tesista en la aceptación: definir el modelo conceptual de consulta de la
evidencia — no una API, sino la forma `pregunta → recorrido → conjunto de
evidencia → respuesta verificable`, capaz de expresar formalmente
"¿por qué esta modalidad?", "¿qué claims participaron?", "¿qué evidencia
fue descartada?", "¿qué cambió tras Validar?". Candidata a base de
dashboards, auditorías, investigación y replay interactivo. **Se evalúa
cuando se diseñen las superficies de consumo** (RFC-0010 y el diseño
experimental).

## Alternativas consideradas y rechazadas

1. **Instrumentación por logging en nodos/capacidades**: rechazada. Crea
   una segunda fuente de verdad no gobernada por invariantes (viola
   INV-10 y P7) y se desincroniza de la historia con el primer refactor.
2. **Telemetría APM genérica (OpenTelemetry, etc.) como fuente de
   evidencia**: rechazada como fuente científica — muestreo, reloj de
   pared y pérdida tolerada son incompatibles con P12/P7. Admisible solo
   como telemetría *operativa* (salud del servicio), fuera del plano de
   evidencia y sin mezclarse con él.
3. **"Explainer agent" (un LLM que redacta explicaciones)**: rechazado.
   Viola P15 y P6 — la explicación es un recorrido del estado, no una
   redacción; un resumen generado puede alucinar exactamente aquello que
   la tesis necesita demostrar que no se alucina.
4. **Métricas materializadas dentro del `LearningState`**: rechazada.
   Viola la anatomía cerrada (RFC-0003) y el paisaje-como-proyección
   (CONCEPT-0001): sería una segunda fuente de verdad con esteroides.

## Ventajas / Riesgos / Impacto / Complejidad

- **Ventajas:** cero deriva instrumentación/realidad (lo observado ES la
  historia); el instrumento de medición de la tesis queda definido antes
  de implementar; el Modo Evidencia de v2 será, por construcción, evidencia
  real (P7) — el contraste con los eventos simulados del Legacy es en sí
  mismo un resultado narrable.
- **Riesgos:** (1) costo de derivar métricas en vivo — mitigación: el
  plano corre fuera del camino caliente y sobre proyecciones por asunto;
  (2) catálogo de métricas que crezca sin control — mitigación: toda
  métrica nueva declara su fuente en la tabla §2.2 y su función pura, o
  no existe; (3) confundir telemetría operativa con evidencia —
  mitigación: la alternativa 2 las separa normativamente.
- **Impacto:** RFC-0008 hereda la persistencia del flujo de eventos y la
  mecánica del replay; RFC-0005 hereda la parte inter-sesión de H9;
  RFC-0010 hereda las tres superficies de consumo; la Constitución recibe
  la propuesta P14.
- **Complejidad:** conceptual baja (el trabajo lo hizo la disciplina de
  mutación); de implementación moderada, aislada del Kernel.

## Recomendación

Aceptar el diseño y, en el mismo acto, decidir la **elevación de P14** con
la formulación propuesta en §4 — la condición que el propio tesista fijó
("cuando se compruebe que la observabilidad y el replay descansan en
ella") está cumplida y documentada. Continuar con el RFC-0008
(Checkpointing y Persistencia), que hereda una especificación ya cerrada:
checkpoint por transición, eventos persistidos y reconstruibles, replay
que reproduce estados, enrutamiento y confianzas efectivas.

## Consecuencias

- Vocabulario normativo nuevo: **plano de observabilidad**, **auditoría
  del contrato**, **telemetría operativa** (separada de la evidencia).
- Ninguna métrica, traza o explicación puede tener otra fuente que la
  historia; ningún observador escribe; ningún LLM redacta explicaciones.
- El catálogo §2.2 es el menú de instrumentos del capítulo de Resultados;
  toda métrica adicional se añade por revisión de este RFC o ADR.
- H5, H8 y H9 (intra-sesión) quedan resueltas. Permanecen abiertas: P14
  (decisión en la aceptación de este RFC), H9 inter-sesión y reputación
  de capacidad (→ RFC-0005), H10 (→ diseño experimental).
