# ARCHITECTURE BLUEPRINT — Estructura física del runtime

- **Estado:** Aceptado (2026-07-10, Engineering Review — el tesista
  verificó: cero decisiones nuevas)
- **Fecha:** 2026-07-10
- **Naturaleza:** documento **derivado y no normativo**. Materializa
  decisiones ya aprobadas; no introduce ninguna. Si algo aquí contradice
  un RFC, gana el RFC y este documento se corrige.

## Estructura del repositorio

El runtime vive junto a la plataforma, separado de ella (D-001, P11):

```
backend/
├── app/                     # Plataforma v1 (intocada; consume el Boundary)
└── runtime/                 # UPAO Runtime (RFC-0001 §1)
    ├── domain/              # RFC-0002 — la política pedagógica
    │   ├── modelar/  diagnosticar/  orientar/  adaptar/
    │   ├── tutorizar/  evaluar/  remediar/  validar/
    │   │   (una carpeta por capacidad: su productor y sus payloads;
    │   │    su única salida son TransitionIntents)
    │   └── shared/          # tipos pedagógicos comunes (competencias,
    │                        # modalidades) — jamás lógica de coordinación
    ├── kernel/              # RFC-0003/0006 — mecanismo puro, sin motor
    │   ├── state/           # LearningState, 8 secciones, sobres
    │   ├── reducers/        # operaciones del agregado + INV-1..12
    │   ├── transitions/     # StateTransition, TransitionIntent
    │   ├── landscape/       # proyección del paisaje + confianza
    │   │                    # efectiva (álgebra A1–A8)
    │   ├── deliberation/    # convocatoria, resolución D1/D2,
    │   │                    # regla de oro, escalada
    │   ├── memory/          # cargar / consolidar (RFC-0005)
    │   ├── contract/        # Runtime Contract + auditor (RFC-0007 §3)
    │   └── events/          # Domain Events (derivados de transiciones)
    ├── engine/              # Graph Engine — ÚNICO lugar con langgraph
    │   ├── graph/           # construcción del grafo; edges = reglas
    │   │                    # de enrutamiento (RFC-0004 §4)
    │   ├── channels/        # secciones → channels; reducers → reducer fns
    │   ├── checkpoint/      # R1–R6; ADR-0001 (canónico) + ADR-0002 (tablas)
    │   └── replay/          # reconstrucción + re-derivación contrafactual
    ├── boundary/            # RFC-0010 — el contrato
    │   ├── inbound/         # E1 abrir · E2 hechos · E3 palabra humana · E4 cerrar
    │   ├── outbound/        # S1 entregas · S2 notificaciones de escalada
    │   └── surfaces/        # S3: export investigación, Modo Evidencia,
    │                        # replay, student model vigente (solo lectura)
    ├── policy/              # política pedagógica versionada — DATOS, no
    │                        # código: pesos, δ, θ, curvas, escala de
    │                        # precisión, catálogo de asuntos
    └── observability/       # plano de observabilidad (RFC-0007) —
                             # consumidores de eventos, métricas, auditor
                             # runner; jamás escribe
tests/runtime/               # espejo de la estructura; ver §Suites
```

## Reglas de importación (los límites físicos)

La tabla es la materialización de las capas de RFC-0001; se hace cumplir
con lint de imports en CI (evidencia estándar del Engineering Gate):

| Paquete | Puede importar | Prohibido |
|---------|----------------|-----------|
| `domain/` | `kernel/` (tipos: estado, sobres, intents) | `engine/`, `boundary/`, `langgraph`, `app/`, otra capacidad (P3) |
| `kernel/` | — (puro; lee `policy/` como datos) | `domain/`, `engine/`, `boundary/`, `langgraph`, `app/` |
| `engine/` | `kernel/`, `domain/`, `langgraph` | `app/` |
| `boundary/` | `kernel/` (tipos), `engine/` (invocar ejecución) | `langgraph`, internals de `app/` (expone interfaz; el transporte lo decide un ADR) |
| `observability/` | `kernel/` (eventos, estado — lectura) | todo lo demás; jamás escribe |
| `app/` (plataforma) | `boundary/` únicamente | `kernel/`, `domain/`, `engine/`, tablas del runtime (ADR-0002 §5 lo impide además por permisos) |

Tres prohibiciones absolutas, de las que derivan todas: **`langgraph`
solo existe dentro de `engine/`** (RFC-0001 §1); **ninguna capacidad
importa a otra** (P3); **nada del runtime importa `app/` ni nada del
Legacy** (P11, D-001).

## Mapa RFC → código

| Documento | Se materializa en |
|-----------|-------------------|
| RFC-0002 (capacidades) | `domain/*` |
| RFC-0003 (estado, sobres, INV) | `kernel/state`, `kernel/reducers`, `kernel/transitions` |
| RFC-0004 (ejecución, enrutamiento) | `engine/graph`, `engine/channels` + regla de autoridad en `kernel/transitions` |
| RFC-0005 (memoria) | `kernel/memory` (+ ADR futuro de storage) |
| RFC-0006 (consenso, A1–A8) | `kernel/landscape`, `kernel/deliberation` + `policy/` |
| RFC-0007 (observabilidad) | `observability/` + `kernel/contract` |
| RFC-0008 + ADR-0001/0002/0003 | `engine/checkpoint`, `engine/replay` |
| RFC-0009 (HITL) | `boundary/inbound` (E3) + `kernel/deliberation` (escalada) |
| RFC-0010 (contrato) | `boundary/*` |

## Suites de aceptación (la evidencia del Gate)

Los contratos se prueban, no se presumen (RFC-0004, RFC-0008). Cuatro
suites con nombre desde el día uno:

- `tests/runtime/invariants/` — INV-1..INV-12: cada invariante con su
  caso de violación rechazada-y-registrada.
- `tests/runtime/guarantees/` — las 4 garantías de ejecución (RFC-0004
  §2), incluida la reproducibilidad del enrutamiento.
- `tests/runtime/reconstruction/` — R1–R6: matar el proceso a mitad de
  sesión y reanudar; replay bit a bit contra la ejecución original.
- `tests/runtime/algebra/` — A1–A8 sobre la función de confianza de cada
  versión de política (criterio de activación de configuraciones,
  RFC-0006).

Estas suites son las filas de evidencia del Engineering Gate: un PR del
runtime las referencia, no las reemplaza con prosa.

## Lo que este documento NO decide

Transporte del Boundary (HTTP/in-process — ADR), DTOs concretos (ADR),
nombres de clases, wiring fino de LangGraph, migraciones (la primera
creará las tres tablas de ADR-0002), framework de tests. Todo eso es
implementación bajo el Gate.

## Orden de construcción sugerido (no normativo)

1. `kernel/state` + `kernel/reducers` + suite de invariantes — el corazón
   sin motor.
2. `engine/checkpoint` (ADR-0001/0002) + suite R1–R6 — la persistencia
   antes que el grafo: sin ella ninguna transición "existe".
3. `kernel/landscape` + `kernel/deliberation` + suite A1–A8.
4. `engine/graph` con la topología mínima del walkthrough (dos
   capacidades reales, una tensión) — el primer recorrido vivo.
5. `boundary/` + una capacidad por vez hasta las ocho.

La razón del orden: cada paso produce evidencia de Gate por sí mismo, y
el primer código que se escribe es exactamente el que más principios
protege.
