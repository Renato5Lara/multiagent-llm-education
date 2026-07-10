# UPAO-MAS-EDU — Arquitectura del Runtime Multiagente

Este directorio contiene los RFC (Request for Comments) que gobiernan el diseño
del nuevo núcleo de IA del proyecto: un runtime multiagente real sobre LangGraph,
con un grafo de estados compartido como única fuente de verdad.

El runtime anterior basado en `BaseAgent` queda archivado como **Legacy Runtime**
(línea base histórica y experimental). No recibe nuevas funcionalidades.

## Jerarquía normativa

```
FOUNDATIONAL_PRINCIPLES.md   (constitución — los RFC no pueden contradecirla)
        ↓
RFC-NNNN                     (decisiones mayores)
        ↓
ADR/                         (decisiones puntuales)
        ↓
código
```

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
| [Constitución](FOUNDATIONAL_PRINCIPLES.md) | Principios Fundacionales (P1–P13) | Aceptado |
| [RFC-0000](RFC-0000-proceso.md) | Proceso y plantilla de RFC | Aceptado |
| [RFC-0001](RFC-0001-vision.md) | Visión arquitectónica | Aceptado |
| [RFC-0002](RFC-0002-domain-model.md) | Modelo de dominio: responsabilidades, resultados y capacidades | Aceptado |
| [RFC-0003](RFC-0003-learning-state.md) | LearningState: anatomía, mutación e invariantes | Aceptado |
| [RFC-0004](RFC-0004-execution-runtime.md) | Runtime de Ejecución y Modelo de Transiciones | Aceptado |
| RFC-0005 | Memoria | Pendiente |
| RFC-0006 | Consenso e inteligencia de enjambre | Pendiente |
| RFC-0007 | Observabilidad | Pendiente |
| RFC-0008 | Checkpointing y persistencia | Pendiente |
| RFC-0009 | Human in the Loop | Pendiente |
| RFC-0010 | Frontera con la plataforma (contrato de integración) | Pendiente |

## Validaciones conceptuales

- [WALKTHROUGH-0001](WALKTHROUGH-0001-diagnostico-a-remediacion-visual.md) —
  del diagnóstico a la remediación visual (2026-07-10): el modelo de
  RFC-0001/0002/0003 narra una ejecución completa; 2 grietas incorporadas
  en RFC-0003 rev. 4, 2 confirmaciones. Habilita el diseño del RFC-0004.

## Registro de propuestas constitucionales

Propuestas registradas pero NO incorporadas; si resultan rectoras, se elevan
por el proceso de enmienda (RFC-0000).

- **P14 — Inmutabilidad de la historia** (tesista, 2026-07-10): la historia de
  estados no se reescribe retrospectivamente; una corrección es un nuevo evento
  que produce un nuevo estado. Se evaluará durante RFC-0003 (LearningState) y
  RFC-0007 (Observabilidad). Insumos asociados para RFC-0003: el `LearningState`
  como único origen autorizado de Domain Events (Reducer → Estado → Evento →
  Observabilidad → Persistencia; nunca Nodo → EventBus) y el patrón
  *event-sourced ligero* (mutaciones centralizadas sin Event Sourcing completo).

## Directorio

```
docs/architecture/
├── README.md          # este índice
├── RFC-NNNN-*.md      # un RFC por decisión mayor
└── ADR/               # decisiones puntuales que no ameritan RFC completo
```
