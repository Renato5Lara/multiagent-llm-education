# RFC-0001 — Visión arquitectónica

- **Estado:** Aceptado (2026-07-10, rev. 2 — tras Architecture Review del tesista)
- **Autor:** Equipo de arquitectura (Claude + tesista)
- **Fecha:** 2026-07-10
- **Aprueba:** Renato Lara (tesista / Product Owner)
- **Gobernado por:** FOUNDATIONAL_PRINCIPLES.md (P1–P13), RFC-0000

## Objetivo

Definir qué es el UPAO Runtime, su arquitectura interna, la regla de control
que lo gobierna y el contrato que todo nodo debe satisfacer. Este documento
es el mapa; los RFC 0002–0010 son el territorio.

## Contexto

- **Tesis:** "Efecto de una arquitectura multiagente basada en inteligencia
  de enjambre en la adaptación de contenido multimodal en estudiantes del
  curso Fundamentos de Programación."
- La plataforma v1 (FastAPI, PostgreSQL, React; auth, dashboards,
  diagnóstico, adaptación, remediación, evaluación, Módulo 1) es funcional
  y permanece. El Legacy Runtime (`BaseAgent`) queda archivado como línea
  base histórica.
- El **modelo conceptual del dominio ya aprobado** (Product Architecture
  v2.1: ciclo Capturar → Interpretar → Construir → Adaptar → Validar) se
  conserva como conocimiento del dominio. Este RFC no rediseña la pedagogía:
  le da una máquina digna de ella.
- Pregunta de investigación que este diseño fortalece: ¿la colaboración
  multiagente con inteligencia de enjambre produce adaptación multimodal
  observable y explicable? La visión convierte esa pregunta en propiedad
  estructural del sistema.

## Propuesta

### 1. Definición: qué es el Runtime

El **UPAO Runtime** es un subsistema autocontenido de decisión pedagógica
que la plataforma consume como servicio interno a través de un contrato
único. No es una librería, ni un conjunto de endpoints, ni un alias de
LangGraph. Es la unión de cuatro capas con dependencias en un solo sentido:

```
UPAO Runtime
├── Domain             capacidades pedagógicas y su proceso — la política
│                      (P4, P5, P13; se diseña en RFC-0002)
├── Kernel             LearningState (Aggregate Root), reducers e
│                      invariantes, memoria, Runtime Contract,
│                      observabilidad — mecanismo propio, sin dependencias
│                      de motor (RFC-0003, 0005, 0007)
├── Graph Engine       ejecución del grafo, checkpointing, interrupciones —
│                      implementado con LangGraph, detalle exclusivo de
│                      esta capa (RFC-0004, 0008, 0009)
└── Platform Boundary  contrato único con la plataforma (P11, RFC-0010)
```

Posición en el sistema:

```
React → FastAPI (application layer de la plataforma)
                → Platform Boundary → Kernel + Domain → Graph Engine
```

Regla de dependencias: `Domain` se expresa en términos del estado que
define el `Kernel`; el `Graph Engine` adapta Kernel y Domain a las
primitivas del motor; el `Platform Boundary` traduce el mundo exterior al
estado y viceversa. **LangGraph aparece únicamente dentro del Graph
Engine**: si mañana cambia el motor, cambian los adaptadores de esa capa y
nada más (P12.c). El runtime NO ES LangGraph; LangGraph es el motor de
ejecución de una de sus cuatro capas.

*Nota de naming:* la capa central se llama `Kernel` (no `Runtime`) para
evitar la colisión Runtime-dentro-de-Runtime, que volvería ambiguo cada
RFC posterior.

### 2. Los dos niveles: la máquina y el programa

**Nivel 1 — Arquitectura del runtime (la máquina).** Estable y agnóstica
del contenido pedagógico (P5):

```
Sesión → LearningState → Capacidades → Grafo → Memoria → Persistencia
```

**Nivel 2 — Proceso pedagógico (el programa).** Vive SOBRE el nivel 1,
expresado como topología del grafo y capacidades del dominio:

```
Capturar → Interpretar → Deliberar → Adaptar → Validar
```

El ciclo pedagógico es un programa; el runtime es su máquina. Cambiar el
programa (otra estrategia pedagógica, otro orden de fases) jamás exige
cambiar la máquina. Dos posiciones dentro del programa quedan fijadas
desde ya: *Deliberar* existe solo cuando hay evidencia en tensión (P8), y
*Validar* — la brecha reconocida del modelo v2.1 — deja de ser aspiración
y pasa a ser fase estructural: toda adaptación registra si funcionó y esa
retroalimentación reentra al estado.

### 3. Regla de control

> **El flujo de control pertenece al grafo, nunca al modelo de lenguaje.**

Un LLM produce contenido; ese contenido se registra en el estado (P12) y
la siguiente transición la decide el grafo como función pura de ese estado.
No es una preferencia: es el corolario operativo de P3 (la coordinación
pertenece al grafo) y P12 (determinismo arquitectónico), y es la línea
divisoria entre un runtime y un chatbot con herramientas. Esta regla es la
que hace posibles el replay, la auditoría y la comparación de experimentos.

### 4. Runtime Contract

Todo nodo del grafo — y el runtime en su conjunto — debe poder responder,
con datos reales (P7) registrados en el estado (P1):

1. **¿Qué observó?**
2. **¿Qué interpretó?**
3. **¿Qué alternativas evaluó?**
4. **¿Por qué eligió una?**
5. **¿Qué ocurrió después?**

Esto no es documentación: es un contrato verificable. **Un nodo que no
puede responder las cinco preguntas está mal diseñado y no entra al
grafo.** La verificación mecánica (qué campos del estado satisfacen cada
respuesta, cómo se audita) se diseña en RFC-0003 y RFC-0007. El contrato
es además el puente con la tesis: sus cinco respuestas son las columnas de
la evidencia de Resultados y Discusión, y todo RFC posterior declara cuál
de ellas ayuda a responder.

### 5. Invariantes (anuncio)

El `LearningState` tendrá un **catálogo explícito de invariantes**,
definido en RFC-0003 y aplicado en la frontera del agregado (P1).
Ejemplos ilustrativos, aún no normativos: no existe estado sin estudiante
y sesión; nunca hay dos rutas de aprendizaje activas; un consenso
registrado incluye siempre sus votos y su regla de resolución; la
evidencia no se pierde ni se sobrescribe. **El RFC-0003 no se considera
completo sin ese catálogo.**

### 6. Qué NO es

- No es la plataforma: UI, autenticación, gestión educativa y persistencia
  de la experiencia siguen siendo responsabilidad de v1.
- No es LangGraph: el motor es un detalle del Graph Engine (§1).
- No es un framework genérico de agentes: solo existe para las capacidades
  de este dominio.
- No es un chatbot con herramientas: viola la regla de control (§3).
- No es el Legacy con otro motor: un pipeline secuencial con nombres de
  agente violaría P3, P4 y P13.

## Alternativas consideradas y rechazadas

1. **Evolucionar BaseAgent**: rechazado. Es un paradigma de servicios
   secuenciales; la colaboración real por estado compartido no puede
   añadírsele sin reescribirlo, y la decisión de archivo ya fue tomada.
2. **Orquestador propio ad-hoc**: rechazado. Reimplementar grafo,
   checkpointing y replay no aporta nada a la hipótesis; es esfuerzo de
   infraestructura sin valor científico. Se adopta LangGraph como motor
   del Graph Engine (registrado aquí; su diseño, en RFC-0004).
3. **Agentes autónomos con transferencia de control (handoffs)**:
   rechazado por la regla de control (§3): el flujo pertenece al grafo,
   nunca al modelo de lenguaje. Un agente que decide "a quién llamar
   después" traslada el enrutamiento al LLM, rompe la función pura del
   estado (P12) y hace irreproducible el replay.
4. **Pipeline determinista sin multiagente**: rechazado. Sería más simple
   y más barato, pero no puede evidenciar la hipótesis: sin colaboración
   ni consenso no hay nada que medir. La complejidad multiagente es el
   objeto de estudio, no un costo accidental.

## Ventajas / Riesgos / Impacto / Complejidad

- **Ventajas:** la hipótesis es observable por construcción (Runtime
  Contract), no por instrumentación posterior; el dominio queda estable
  ante cambios de topología (P13) y de motor (§1); la plataforma v1 no se
  toca (P11).
- **Riesgos:** (1) que la separación Kernel/Graph Engine degenere en capas
  especulativas — mitigación: dentro del Graph Engine se permite
  acoplamiento pragmático a LangGraph; la regla es que no se filtre a
  Domain ni Kernel, no fingir que el motor no existe; (2) sobreingeniería
  del mecanismo antes de conocer las capacidades — mitigación: RFC-0002 se
  diseña antes que RFC-0004; (3) costo y latencia de deliberación LLM —
  mitigación: P8 la restringe a decisiones con tensión real; (4) que la
  "inteligencia de enjambre" quede reducida a una votación trivial —
  riesgo científico mayor del proyecto, se ataca de frente en RFC-0006.
- **Impacto:** define vocabulario (Kernel, Graph Engine, Runtime Contract,
  regla de control), orden y criterio de evaluación de todos los RFC
  siguientes.
- **Complejidad:** conceptual media; de implementación, diferida por diseño.

## Recomendación

Aprobar esta visión y diseñar a continuación el **RFC-0002 (modelo de
dominio y capacidades)** antes que cualquier RFC de mecanismo. El dominio
manda sobre la máquina (P5, P13): dimensionar el grafo antes de conocer
las capacidades sería construir el motor antes de saber qué debe mover.

## Consecuencias

- Vocabulario normativo desde este RFC: **Kernel**, **Graph Engine**,
  **Platform Boundary**, **Runtime Contract**, **regla de control**.
- Orden de diseño: 0002 (dominio) → 0003 (LearningState) → 0004 (grafo) →
  0006 (consenso/enjambre) → 0005/0007/0008/0009 (transversales) → 0010
  (frontera, al final, cuando el contrato pueda enunciarse completo).
- RFC-0003 debe incluir el catálogo de invariantes del `LearningState` y
  los campos que satisfacen el Runtime Contract; RFC-0007 define su
  auditoría.
- Todo RFC posterior declara a qué capa de §1 pertenece y qué pregunta del
  Runtime Contract ayuda a responder.
- La fase Validar es obligatoria en el diseño del grafo (RFC-0004); no
  puede posponerse a "una versión futura".
