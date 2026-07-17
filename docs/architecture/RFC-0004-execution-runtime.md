# RFC-0004 — Runtime de Ejecución y Modelo de Transiciones

- **Estado:** Aceptado (2026-07-10, rev. 2 — con los cuatro ajustes de la
  Architecture Review del tesista; H7 registrada en la aceptación;
  rev. 3: corrección F1 de la Integrity Review v1, aprobada por el tesista)
- **Autor:** Equipo de arquitectura (Claude + tesista)
- **Fecha:** 2026-07-10
- **Aprueba:** Renato Lara (tesista / Product Owner)
- **Gobernado por:** FOUNDATIONAL_PRINCIPLES.md (P3, P5, P8, P10, P12), RFC-0001, RFC-0002, RFC-0003
- **Capa (RFC-0001 §1):** Graph Engine (con la definición de semántica en el Kernel)
- **Runtime Contract:** hace ejecutables las preguntas 3 y 4 (quién propone,
  cómo se convoca y resuelve la elección); las restantes ya viven en el
  estado (RFC-0003 §5)

## Objetivo

Definir qué significa **ejecutar** el modelo de RFC-0003: la semántica de
una StateTransition, las garantías del ciclo de ejecución, el enrutamiento
del programa pedagógico y — solo al final — el mapeo al motor elegido.
El motor no aparece hasta la §6 por decisión metodológica del tesista: la
tecnología no contamina el modelo.

## Decisión irreversible

**El modelo de ejecución:**

> Producción concurrente de intents; aplicación serializada con orden
> total por sesión; enrutamiento como función pura del estado;
> checkpoint por transición.

Replay, consenso, HITL y observabilidad asumirán estas cuatro garantías.

Igual de importante es lo que **no** es irreversible: la **topología** (qué
productores se activan cuándo, si una capacidad es un nodo o un subgrafo)
es explícitamente reversible por P13 — puede cambiar sin tocar dominio,
estado ni garantías. Este RFC congela la física del runtime, no su
coreografía.

## Contexto

- Herencias: los nodos son productores de propuestas, jamás escritores
  (RFC-0003); la StateTransition es la unidad atómica; la convocatoria de
  deliberación es enrutamiento sobre claims en conflicto (Walkthrough-0001,
  confirmación 1); la fase Validar es estructuralmente obligatoria
  (RFC-0001).
- Registro anticipado: el tesista predijo (2026-07-10) que este RFC
  descubriría el concepto **Transition Intent** — *"antes de existir una
  transición, alguien tiene que querer producirla"*. La predicción se
  cumple en la §1.
- Relación con la hipótesis: aquí se decide cómo la colaboración
  multiagente *ocurre* en el tiempo — el walkthrough narró qué pasa; este
  RFC define por qué pasa en ese orden y qué lo garantiza.

## Propuesta

### 1. ¿Qué significa ejecutar una StateTransition?

Ejecutar una transición es completar este ciclo de siete pasos:

```
1. LEER        el productor toma una vista consistente del LearningState
               (una versión determinada, no un estado cambiante)
2. INTERPRETAR el productor transforma los facts y claims leídos en su
               juicio propio — la interpretación es trabajo de la
               capacidad, jamás del Kernel (para el Boundary este paso es
               traducción sin interpretación: el mundo aporta hechos)
3. PRODUCIR    el productor genera un TRANSITION INTENT: el deseo de
               transicionar, aún sin autoridad
4. VALIDAR     el reducer confronta el intent con las invariantes contra
               el estado ACTUAL (no contra la vista leída)
5. APLICAR     atómicamente: la transición ocurre completa o no ocurre
6. EMITIR      los Domain Events de la transición (INV-10)
7. CHECKPOINT  el estado queda persistido y reanudable (INV-11, P10)
```

El paso 2 conecta el ciclo de ejecución con la cadena epistemológica
(RFC-0003 §1): interpretar es exactamente el tramo `Facts → Claims`.

El **Transition Intent** es el mensaje de primera clase entre productores
y Kernel:

```
TransitionIntent
├── productor   capacidad | boundary | kernel (deliberaciones)
├── entradas    las FactEntry/ClaimEntry/decisiones propuestas
└── base        versión del estado que el productor leyó
```

**Regla de autoridad:**

> **Un `TransitionIntent` no tiene autoridad para modificar el estado.
> Representa únicamente una propuesta de transición. La autoridad de
> modificar el `LearningState` pertenece exclusivamente al Kernel,
> mediante la aplicación de una `StateTransition` válida.**

Un intent es un dato, no un actor: ninguna operación del tipo
`intent.apply()` puede existir en ninguna capa. Por eso la validación
(paso 4) ocurre contra el estado actual y no contra la `base`: si el mundo
cambió desde la lectura, las invariantes deciden si el intent sigue siendo
aplicable (p. ej. INV-5 exige respaldo hacia entradas *vigentes*). La
`base` se registra para observabilidad e investigación: mide cuánta
"realidad vieja" traía cada propuesta. El tesista registró (2026-07-10)
las métricas experimentales que este campo habilita — obsolescencia media
de los intents, tasa de descartes por estado obsoleto, frecuencia de
replanificación, estabilidad bajo concurrencia — como insumo del RFC-0007
y candidatas a resultados de la tesis.

### 2. Las cuatro garantías de ejecución

1. **Atomicidad** — una transición se aplica completa o se rechaza
   completa (y el rechazo se registra, RFC-0003 §4). No existen estados
   intermedios observables.
2. **Orden total por sesión** — las transiciones de una sesión forman una
   secuencia única. La concurrencia existe en la **producción** (varias
   capacidades piensan a la vez — es lo caro, es lo lento, es lo que
   conviene paralelizar), jamás en la **aplicación** (serializada — es
   barata y es la que exige consistencia). Esta separación disuelve el
   clásico conflicto de escrituras concurrentes sin locks ni merges.
   Su formulación profunda es la **separación entre razonamiento y
   consistencia**: las capacidades razonan y producen propuestas; el
   Kernel garantiza la consistencia y las invariantes. **Ninguna capacidad
   es responsable de la consistencia del sistema** — puede equivocarse,
   contradecirse o proponer tarde, y el sistema sigue siendo consistente,
   porque la consistencia nunca estuvo en sus manos.
3. **Enrutamiento puro** — después de cada transición aplicada, la
   siguiente activación es función pura del estado (P12, regla de control
   RFC-0001 §3). Ningún productor decide quién sigue.
4. **Recuperabilidad por transición** — entre transiciones siempre existe
   un checkpoint válido; la sesión puede pausarse, morir y reanudarse en
   la última transición aplicada (P10).

El **replay** queda definido por construcción: re-aplicar la secuencia de
transiciones (con el no-determinismo ya grabado como provenance `llm`)
reproduce exactamente los mismos estados y el mismo enrutamiento (P12.b).

### 3. El ciclo de ejecución

```
        ┌────────────── enrutar(estado) ──────────────┐
        │        (función pura → activaciones)        │
        ▼                                             │
  activar productores  ──▶  producir intents          │
  (en paralelo)             (LLM, reglas,             │
        ▲                    instrumentos)            │
        │                        │                    │
        │                        ▼                    │
   checkpoint ◀── emitir ◀── aplicar ◀── validar ─────┘
                 eventos    (serializado, orden total)
```

El ciclo termina cuando el enrutamiento no produce activaciones (objetivo
cumplido, sesión cerrada por el estudiante, o escalada HITL sin respuesta
dentro de la sesión) — el cierre ejecuta la transición de `salidas`
(RFC-0003 §2).

### 4. El programa pedagógico como reglas de enrutamiento

> **El runtime nunca codifica una secuencia pedagógica. Ejecuta reglas de
> transición sobre el estado; la secuencia observada emerge de esas
> reglas.**

El ciclo Capturar → Interpretar → Deliberar → Adaptar → Validar (RFC-0001
§2) no se cablea: no existe — ni puede existir — un `if módulo == 1:
hacer esto`. Las reglas canónicas iniciales:

| Cuando el estado contiene… | se activa… |
|----------------------------|------------|
| facts del mundo nuevos sin interpretar | Modelar, Diagnosticar |
| interpretaciones nuevas relevantes a la ruta | Orientar, Remediar (según brecha) |
| objetivo de intervención vigente sin diseño de experiencia | Adaptar |
| ≥ 2 claims-propuesta vigentes en conflicto sobre la misma decisión | **deliberación** (operación del Kernel; su regla de resolución es del RFC-0006) |
| deliberación resuelta, o propuesta única sin oposición | la transición de **decisión** |
| decisión sin entregar | el Platform Boundary (entrega al mundo) |
| facts de entrega + facts evaluativos posteriores a una decisión `pendiente-de-validación` | **Validar** (obligatoria — RFC-0001) |
| veredicto de Validar | Modelar (retroalimentación del student model) |
| deliberación aplazada cuya evidencia faltante ya llegó | convocatoria de una **nueva deliberación enlazada** (CONCEPT-0002 §5; disparador — RFC-0006) |

Consecuencias de esta forma: (a) la fase del ciclo es una *proyección*
(`ejecución`), no un mecanismo de control; (b) cambiar la estrategia
pedagógica = cambiar reglas de enrutamiento, no el runtime (P5); (c) toda
regla es una función legible del estado — auditable y citable.

Conforme a P13, cada capacidad puede realizarse como un productor simple o
como un subgrafo interno (p. ej. Adaptar: generar candidatos → autoevaluar
→ proponer); su interior es libre mientras su única salida sean intents.

### 5. Interrupciones (HITL)

Una escalada (deliberación → `escalada`, RFC-0003 §4.1) o una pausa
pedagógica es una transición que registra la interrupción pendiente en
`ejecución` y detiene el ciclo en un checkpoint. La reanudación es
simétrica: la respuesta humana entra por el Boundary como fact (provenance
`humano`), y el enrutamiento — función pura del estado que ahora contiene
ese fact — continúa. **No hay un "modo pausado" especial: hay un estado
que no produce activaciones hasta que llega el fact que espera.** Los
criterios de escalada pertenecen al RFC-0009.

### 6. Mapeo al motor: LangGraph

Recién aquí aparece la tecnología. Elección registrada en RFC-0001
(alternativa 2); este RFC la sustancia con un argumento de *ajuste
estructural*, no de popularidad: el modelo de ejecución de LangGraph
(Pregel / Bulk Synchronous Parallel) coincide con nuestras garantías —
los nodos ejecutan en paralelo dentro de un superstep y sus retornos se
aplican mediante reducers al cierre del superstep. Es exactamente
"producción concurrente, aplicación serializada".

| Concepto del runtime | Realización en LangGraph |
|----------------------|--------------------------|
| LearningState (secciones) | state schema con un channel por sección |
| Reducer del Kernel (INV-*) | reducer functions de los channels append-only |
| Productor / capacidad | node (o subgraph por capacidad, P13) |
| TransitionIntent | el valor retornado por el node hacia los channels |
| Enrutamiento puro (§4) | conditional edges que leen SOLO el estado |
| Checkpoint por transición | checkpointer sobre PostgreSQL |
| Interrupción HITL | interrupt() + reanudación por checkpoint |
| Replay | re-ejecución desde checkpoints con provenance grabada |

**Reglas de subordinación del motor:**

> **El motor nunca redefine el modelo. El adaptador absorbe las
> diferencias.**

- Si una garantía no mapea directamente (p. ej. granularidad de checkpoint
  por superstep vs por transición), se implementa en el adaptador del
  Graph Engine; **jamás se relaja el modelo para complacer al motor**.
- Prohibido en el mapeo: handoffs entre agentes (RFC-0001, alt. 3), nodos
  que escriben canales de otros sin pasar por reducers, canales de
  sobrescritura para las secciones append-only, eventos emitidos desde
  nodos (INV-10).
- LangGraph no aparece fuera del Graph Engine: ni en el dominio, ni en el
  Kernel, ni en el Boundary (RFC-0001 §1).

### 7. Hipótesis registradas

**H7 — Scheduler Policy (REGISTRADA, no incorporada):** propuesta del
tesista en la aceptación de este RFC: cuando existen múltiples intents
válidos simultáneamente, ¿qué política decide el orden de aplicación?
(FIFO, prioridad por capacidad, por criticidad, pedagógica, por deadline,
configurable). Este RFC fija que la aplicación es serializada; no fija la
política de selección. **Se evalúa en el RFC-0006** (afecta la
coordinación y la deliberación). *Restricción del arquitecto para esa
evaluación:* la política elegida debe preservar P12 — el orden tiene que
ser función determinista del estado más el orden de llegada registrado, o
el replay pierde exactitud.

**H6 — Clases de `TransitionIntent` (REGISTRADA, no incorporada):**
propuesta del tesista: estudiar si conviene distinguir clases de intent
según su papel en el consenso — p. ej. *observacionales* (Diagnosticar
aporta juicio sobre la realidad) y *decisionales* (Adaptar propone actuar
sobre ella) — porque probablemente el consenso no deba tratarlas igual.
No corrige un defecto: el sobre actual ya insinúa la distinción (un intent
cuyas entradas son facts/interpretaciones vs uno que trae propuestas).
**Se evalúa en el RFC-0006**, junto con H4 (Intentions/Resolutions), con
la que probablemente converja. La numeración de hipótesis es global al
plano (H1–H5 en RFC-0003).

## Alternativas consideradas y rechazadas

1. **Diseñar el grafo primero y adaptar el dominio** (design-by-framework:
   empezar por StateGraph/START/END): rechazado. Contamina el modelo con
   la tecnología; era el riesgo señalado por el tesista al abrir este RFC.
2. **Aplicación concurrente del estado** (locks, merges, CRDTs):
   rechazado. Una sesión de aprendizaje es un flujo de decisión
   pedagógica, no un sistema de alta contención; el orden total es además
   condición del replay (P12). La concurrencia se gasta donde rinde: en la
   producción.
3. **Ejecución dirigida por eventos** (capacidades suscritas a Domain
   Events): rechazado. Reintroduce coordinación implícita — "quién escucha
   qué" es acoplamiento oculto, exactamente lo que P3 prohíbe — y usa los
   eventos como señal de control cuando son derivada del estado (INV-10).
4. **Un scheduler propio**: ya rechazado en RFC-0001 (alternativa 2);
   reafirmado — el ajuste estructural Pregel/BSP (§6) elimina la última
   razón para construirlo.

## Ventajas / Riesgos / Impacto / Complejidad

- **Ventajas:** el replay es corolario, no feature; el conflicto de
  concurrencia desaparece por construcción; la estrategia pedagógica es
  configuración (reglas de enrutamiento), no código del runtime; el
  argumento LangGraph queda fundado en ajuste estructural (citable).
- **Riesgos:** (1) la aplicación serializada como cuello de botella —
  aceptado conscientemente: lo costoso (LLM) está en la producción
  paralela, la aplicación es barata; (2) desviación del motor respecto a
  las garantías — mitigación: reglas de subordinación §6; (3) reglas de
  enrutamiento que crezcan hasta volverse un motor de reglas —
  mitigación: son las canónicas §4 + las que RFC-0006/0009 añadan, cada
  una con dueño en un RFC; (4) topología prematura — mitigación: la
  topología es reversible y arranca mínima.
- **Impacto:** RFC-0006 hereda la convocatoria mecánica y el disparador de
  reapertura; RFC-0008 hereda "checkpoint por transición" como requisito;
  RFC-0009 hereda el modelo de interrupción sin modo especial; RFC-0010
  hereda al Boundary como productor de facts y entregador de decisiones.
- **Complejidad:** conceptual media (el trabajo duro lo hizo RFC-0003);
  de implementación moderada y acotada al Graph Engine.

## Recomendación

Aceptar el modelo de ejecución (seis pasos, cuatro garantías, enrutamiento
declarativo, motor subordinado). Continuar con el **RFC-0006 (consenso e
inteligencia de enjambre)** antes que los transversales: es el corazón
científico (RFC-0001, riesgo 4) y ya tiene todo su material esperando —
las tres tensiones canónicas, los claims como objeto, la confianza de la
resolución, los disparadores de reapertura y las hipótesis H4 y Knowledge
Claim.

## Consecuencias

- Vocabulario normativo nuevo: **TransitionIntent** (deseo sin autoridad),
  **activación**, **reglas de enrutamiento**, **reglas de subordinación
  del motor**, **separación entre razonamiento y consistencia**.
- La regla de autoridad (§1) es ley de implementación: ningún intent
  expone operación alguna de aplicación; solo el Kernel muta el estado.
- Las cuatro garantías (§2) son criterios de aceptación de la
  implementación del Graph Engine: se prueban, no se presumen.
- La topología es reversible: sus cambios futuros se registran como ADR,
  no como enmienda a este RFC.
- Ningún concepto de LangGraph puede aparecer en RFCs de dominio o Kernel;
  la tabla §6 es el único diccionario autorizado entre ambos mundos.
