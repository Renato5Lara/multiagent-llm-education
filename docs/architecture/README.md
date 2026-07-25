# UPAO-MAS-EDU — Arquitectura del Runtime Multiagente

Este directorio contiene los RFC (Request for Comments) que gobiernan el diseño
del nuevo núcleo de IA del proyecto: un runtime multiagente real sobre LangGraph,
con un grafo de estados compartido como única fuente de verdad.

> **Foundation Phase: cerrada y CONGELADA (2026-07-10).** Constitución,
> lenguaje, física del runtime, semántica, consenso y gobernanza quedaron
> definidos sin una línea de código (decisiones D-001..D-026, ver
> [LEDGER.md](LEDGER.md)). Los documentos de la fase solo admiten
> correcciones editoriales; **todo cambio conceptual pasa por el proceso
> de gobernanza** (RFC-0000). Desde el RFC-0008 el trabajo es de
> ingeniería y se revisa como tal (RFC-0000 rev. 4): la arquitectura
> gobierna al desarrollo, no al revés.
>
> **Closure Review: PASSED (2026-07-10)** — cero conceptos sin definición
> autoritativa; **Implementation Phase: AUTORIZADA**
> ([acta](CLOSURE-REVIEW-v1.md)).

El runtime anterior basado en `BaseAgent` queda archivado como **Legacy Runtime**
(línea base histórica y experimental). No recibe nuevas funcionalidades.

> **Capa pedagógica:** la capa de *qué principios gobiernan el aprendizaje* y *cómo
> se traducen en experiencia* vive en [pedagogical/](pedagogical/README.md)
> (PP0–PP8, Pedagogical Architecture v1.0, congelada 2026-07-23) — complementa esta
> Constitución, no la sustituye. Numeración PP0–PP8 deliberadamente distinta de
> P1–P17 para no colisionar.

## Jerarquía normativa

```
FOUNDATIONAL_PRINCIPLES.md          (constitución — nada la contradice)
        ↓
┌───────────────────────────┬──────────────────────────────────┐
│ RFC-NNNN                  │ CONCEPT-NNNN (Concept Standards) │
│ decisiones de diseño      │ estándar semántico: vocabulario  │
│                           │ y significado, jamás             │
│                           │ implementación                   │
└───────────────────────────┴──────────────────────────────────┘
        ↓
ADR/                                (decisiones puntuales)
        ↓
código                              (+ VOCABULARY.md, glosario vivo)
```

> **Los documentos CONCEPT aceptados constituyen el estándar semántico del
> proyecto. Los RFC pueden apoyarse en ellos y especializarlos, pero no
> redefinir su significado. Si un RFC necesita cambiar un concepto,
> primero debe enmendar el documento CONCEPT correspondiente.**
> *(Regla del tesista, 2026-07-10 — resolución del hallazgo F3.)*

Autoridades distintas, no rangos: el RFC manda sobre el *diseño*; el
CONCEPT manda sobre el *significado*. Ambos bajo la Constitución, ambos
con el ciclo de vida del RFC-0000.

## Reglas

- Ningún RFC contradice [FOUNDATIONAL_PRINCIPLES.md](FOUNDATIONAL_PRINCIPLES.md);
  si un diseño lo necesita, primero se enmienda la constitución.
- Ningún código del nuevo runtime se escribe sin un RFC **Aceptado** que lo respalde.
- Ningún código contradice un RFC Aceptado; si el código lo necesita, primero se
  revisa el RFC (que pasa a **Supersedido** por una nueva versión).
- Solo el tesista aprueba RFCs. El proceso completo está en RFC-0000.

## Índice

| Documento | Título | Estado |
|-----------|--------|--------|
| [Constitución](FOUNDATIONAL_PRINCIPLES.md) | Principios Fundacionales (P1–P17) | Aceptado |
| [RFC-0000](RFC-0000-proceso.md) | Proceso y plantilla de RFC | Aceptado |
| [RFC-0001](RFC-0001-vision.md) | Visión arquitectónica | Aceptado |
| [RFC-0002](RFC-0002-domain-model.md) | Modelo de dominio: responsabilidades, resultados y capacidades | Aceptado |
| [RFC-0003](RFC-0003-learning-state.md) | LearningState: anatomía, mutación e invariantes | Aceptado |
| [RFC-0004](RFC-0004-execution-runtime.md) | Runtime de Ejecución y Modelo de Transiciones | Aceptado |
| [RFC-0005](RFC-0005-memoria.md) | Memoria | Aceptado |
| [RFC-0006](RFC-0006-consenso-enjambre.md) | Consenso e Inteligencia de Enjambre | Aceptado |
| [RFC-0007](RFC-0007-observabilidad.md) | Observabilidad | Borrador |
| [RFC-0008](RFC-0008-checkpointing-persistencia.md) | Checkpointing y Persistencia | Aceptado |
| [RFC-0009](RFC-0009-human-in-the-loop.md) | Human in the Loop | Aceptado |
| [RFC-0010](RFC-0010-frontera-plataforma.md) | Frontera con la Plataforma (contrato de integración) | Aceptado |

**Orden de diseño vigente** (decisión del tesista, 2026-07-10, supersede
el orden interno de los transversales de RFC-0001): 0007 Observabilidad →
0008 Checkpointing → 0005 Memoria → 0009 HITL → 0010 Frontera. Razón: el
consenso ya definió qué observar y qué persistir; la memoria pasa de
requisito previo a consecuencia del modelo.

## Validaciones conceptuales

- [WALKTHROUGH-0001](WALKTHROUGH-0001-diagnostico-a-remediacion-visual.md) —
  del diagnóstico a la remediación visual (2026-07-10): el modelo de
  RFC-0001/0002/0003 narra una ejecución completa; 2 grietas incorporadas
  en RFC-0003 rev. 4, 2 confirmaciones. Habilita el diseño del RFC-0004.

## Concept Standards (estándar semántico)

- [CONCEPT-0001](CONCEPT-0001-inteligencia-de-enjambre.md) — ¿Qué
  entendemos por inteligencia de enjambre en UPAO-MAS-EDU? (Aceptado):
  paisaje cognitivo, criterios E1–E6, anti-definición, hipótesis
  operacional. Criterio normativo del RFC-0006.
- [CONCEPT-0002](CONCEPT-0002-taxonomia-del-consenso.md) — Taxonomía del
  Consenso (Aceptado): D1/D2/D3, latente vs bloqueante, regla de oro del
  espacio de resultados, H9. Agenda cerrada del RFC-0006.

## ADRs (decisiones de ingeniería — Engineering Review)

- [ADR-0001](ADR/ADR-0001-canonical-serialization.md) — Serialización
  Canónica (Aceptado): JCS + IDs deterministas + escala fija decimal
  (contrato; precisión = política) + cadena de hashes (P14 verificable).
- [ADR-0002](ADR/ADR-0002-transition-storage-layout.md) — Layout de
  Almacenamiento (Aceptado): bytes canónicos como verdad, JSONB como
  proyección, blobs por contenido (jamás transiciones), inmutabilidad
  multicapa.
- [ADR-0003](ADR/ADR-0003-runtime-versioning.md) — Runtime Versioning
  (Aceptado): vector de versiones por sesión (`spec_version`, política,
  banco, student model) + `runtime_version` por transición; regla de
  comparabilidad de experimentos.
- [ADR-0004](ADR/ADR-0004-error-handling.md) — Manejo de Errores
  (Aceptado): cinco categorías con un destino cada una; «un bug jamás se
  disfraza de rechazo»; lo inclasificado es defecto del software.
- [ADR-0005](ADR/ADR-0005-testing-strategy.md) — Estrategia de Pruebas
  (Aceptado, rev. 2): cinco suites (el walkthrough como test de
  integración canónico), token canónico de norma (`pytest -k INV_5`),
  cobertura de contrato, lint como suite (`json.dumps` prohibido fuera
  de canonical.py).
- [ADR-0006](ADR/ADR-0006-langgraph-adapter-rules.md) — Reglas del
  Adaptador LangGraph (Aceptado): ocho reglas para el único módulo con
  tecnología externa; el checkpointer nativo jamás es fuente de verdad;
  el estado visible por un nodo es inmutable.
- [ADR-0007](ADR/ADR-0007-integracion-llm-productores-conocimiento.md)
  — Estrategia de Integración LLM para Productores de Conocimiento
  (Aceptado): el tipo de sobre que produce el reducer —no la
  derivabilidad del valor— decide entre grounding (FACT: el LLM nunca
  es la fuente del dato) y regla/vocabulario explícito (CLAIM: el LLM
  interpreta dentro de un contrato declarado); evidencia empírica de
  las 8 capacidades; riesgo de Prompt Drift registrado, no resuelto
  aquí.
- [ADR-0008](ADR/ADR-0008-memory-storage-layout.md) — Layout de
  Almacenamiento de Memoria (Aceptado): la unidad de versionado es el
  cierre de sesión, nunca una invocación del Engine; memoria por
  estudiante (`student_id`, `version`) con `session_id` como
  procedencia; cada versión es una unidad lógica atómica, tecnología
  libre; sin cadena de hashes propia (consolidación derivada, nunca
  reemplaza la historia de transiciones); Consolidar consume
  exactamente `proyectar_salidas()` (M4 PR-2).

## Implementation Phase

- [BLUEPRINT](BLUEPRINT.md) — estructura física del runtime (Aceptado):
  reglas de importación vigiladas por CI, mapa RFC → código, cuatro
  suites de aceptación como evidencia del Gate, orden de construcción.

## Revisiones

- [CLOSURE-REVIEW-v1](CLOSURE-REVIEW-v1.md) — 2026-07-10: acta de cierre
  de la fase de diseño. PASSED — Implementation Phase autorizada.

- [INTEGRITY-REVIEW-v1](INTEGRITY-REVIEW-v1.md) — 2026-07-10, sobre los
  diez documentos aceptados: 0 contradicciones conceptuales, 0 ciclos.
  Resuelta: F1/F2 aplicados (commit 00abf02); F3 resuelto con la categoría
  Concept Standard (decisión del tesista). El glosario vivo es
  [VOCABULARY.md](VOCABULARY.md).

## Registro de propuestas constitucionales

Propuestas registradas pero NO incorporadas; si resultan rectoras, se elevan
por el proceso de enmienda (RFC-0000).

- **«La deliberación selecciona, jamás crea»** — **ELEVADA Y GENERALIZADA
  a P15** (2026-07-10, enmienda aprobada por el tesista durante la
  revisión del RFC-0006): el runtime nunca crea conocimiento de dominio.
- **P14 — Inmutabilidad de la historia** — **ELEVADA** (2026-07-10, en la
  aceptación del RFC-0007, con formulación generalizada del tesista):
  propuesta → adoptada como diseño (RFC-0003, INV-3) → comprobada
  (RFC-0007) → constitucional. Los insumos asociados (LearningState único
  origen de Domain Events; event-sourced ligero) fueron adoptados en
  RFC-0003 §4.
- **Reputación de capacidad** — **DIFERIDA post-tesis** (RFC-0005 §3):
  memoria del sistema que cruza estudiantes; la hipótesis no la necesita.
  Si el análisis experimental muestra sesgo sistemático por capacidad,
  ese hallazgo será un resultado de la tesis y su justificación de
  adopción futura.
- **«La explicación se recorre, no se redacta»** — **ELEVADA a P16**
  (Enmienda Constitucional v1, 2026-07-10, tras la Closure Review).
- **«El humano participa por hechos, jamás por edición»** — **ELEVADA a
  P17** (Enmienda Constitucional v1, 2026-07-10, tras la Closure Review).

## Directorio

```
docs/architecture/
├── README.md          # este índice
├── RFC-NNNN-*.md      # un RFC por decisión mayor
└── ADR/               # decisiones puntuales que no ameritan RFC completo
```
