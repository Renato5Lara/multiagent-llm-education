# Principios Fundacionales — Runtime Multiagente UPAO-MAS-EDU

- **Estado:** Aceptado (2026-07-10 — acta fundacional del nuevo runtime;
  rev. 2 del mismo día: enmienda P15 aprobada por el tesista durante la
  revisión del RFC-0006)
- **Fecha:** 2026-07-10
- **Autoridad:** Este documento está POR ENCIMA de los RFC. Un RFC puede
  desarrollar o ampliar un principio; no puede contradecirlo. Si un diseño
  necesita violar un principio, primero se enmienda este documento (con
  aprobación explícita del tesista y registro de la razón), y solo después
  se escribe el RFC.

Los principios son deliberadamente independientes del motor concreto.
LangGraph es la tecnología elegida para implementarlos (se registra en los
RFC correspondientes), pero ningún principio depende de ella para ser válido.

---

## P1 — El estado compartido es la única fuente de verdad

Toda información que influye en una decisión del runtime vive en el
`LearningState` o, para el runtime, no existe. No hay canales laterales:
ni variables globales, ni caches privados, ni mensajes fuera del estado.

El `LearningState` no es una clase de datos: es el **Aggregate Root** del
dominio del runtime. Toda transición de estado ocurre a través de él y se
valida en su frontera; todo evento observable nace de una de sus
transiciones; toda garantía de consistencia se define sobre él.
Consecuencia de diseño: las mutaciones pasan por operaciones validadas del
agregado (reducers), nunca por escrituras crudas de un agente.

## P2 — Ningún agente posee estado propio persistente

Un agente puede usar memoria de trabajo efímera durante su turno de
ejecución; nada de eso sobrevive al turno. Todo lo que deba recordarse se
escribe en el `LearningState` o en la capa de memoria del runtime (RFC-0005),
que es compartida y gobernada por el grafo — nunca en el agente.

## P3 — Los agentes no se invocan entre sí

La colaboración ocurre exclusivamente leyendo y escribiendo el estado
compartido. La coordinación (orden, paralelismo, condiciones) pertenece al
grafo, no a los agentes. Un agente que conoce a otro agente es un defecto
de diseño.

## P4 — Los agentes representan capacidades del dominio

Un agente se define por lo que aporta al estado (diagnosticar, adaptar,
remediar, evaluar…), no por su implementación. No representan clases,
servicios ni módulos técnicos. Si una "capacidad" no puede enunciarse en
lenguaje pedagógico, no es un agente.

## P5 — El runtime es mecanismo, no política

El runtime orquesta, persiste, observa e interrumpe. No conoce detalles
pedagógicos: la política pedagógica vive en las capacidades y en su
configuración. Un cambio de estrategia pedagógica jamás debe requerir
tocar el runtime.

## P6 — Toda decisión pedagógica relevante es trazable

De cada decisión debe poder responderse: qué agentes participaron, sobre
qué evidencia, qué alternativas existieron y por qué ganó la elegida.
Lo que no puede explicarse no puede desplegarse.

## P7 — Toda evidencia corresponde a una ejecución real y reproducible

El runtime jamás fabrica eventos, deliberaciones ni métricas. Todo lo que
la observabilidad muestra ocurrió de verdad en el grafo y puede
reproducirse desde sus checkpoints (P10, P12): las deliberaciones
ocurrieron, los votos existieron, los tiempos fueron medidos, las
decisiones fueron tomadas por el sistema. Los datos de demostración
(fixtures, escenarios) viven fuera del runtime, en la plataforma, y se
identifican como tales. *Este principio distingue al nuevo runtime del
Legacy, donde los eventos simulados eran un atajo permitido.*

## P8 — El consenso se usa solo donde agrega valor

El consenso se reserva para decisiones donde existen perspectivas
genuinamente múltiples y evidencia en tensión. Donde no las hay, decide
una capacidad sola. El ceremonial de deliberación sin desacuerdo posible
no es inteligencia de enjambre: es teatro, y P7 lo prohíbe.

## P9 — La observabilidad es parte del runtime desde el diseño

Cada transición del grafo es observable sin instrumentación posterior.
La observabilidad no es una capa que se añade: es una propiedad que se
hereda de ejecutar dentro del runtime.

## P10 — Toda ejecución es interrumpible y reanudable

El checkpointing es propiedad estructural, no un añadido. Human-in-the-Loop
es una interrupción de primera clase del grafo — cualquier punto puede
pausar esperando a un humano y reanudarse sin pérdida — no un caso especial
implementado aparte.

## P11 — El runtime tiene una única frontera con la plataforma

La plataforma educativa consume el runtime a través de un contrato único y
explícito (RFC-0010). El runtime no importa internals de la plataforma ni
nada del Legacy Runtime. Toda concesión al mundo exterior vive en el borde,
nunca dentro.

## P12 — Determinismo arquitectónico

El enrutamiento del grafo es una **función pura del estado**: dado el mismo
`LearningState`, la misma configuración y las mismas dependencias, el
runtime toma exactamente las mismas transiciones. Toda fuente de
no-determinismo (la salida de un LLM, un timestamp, un número aleatorio)
entra primero al estado como dato registrado, y solo entonces puede influir
en una transición. Consecuencias: (a) el flujo solo puede variar entre
ejecuciones porque el contenido registrado varió, nunca por no-determinismo
oculto dentro del runtime; (b) re-ejecutar desde checkpoints con las salidas
registradas reproduce el flujo exacto — fundamento del Replay y de P7;
(c) el modelo de lenguaje es una dependencia inyectada en el borde: cambiar
de modelo no cambia una línea del runtime. La IA cambia; la arquitectura no.

## P13 — Capacidades antes que agentes

El dominio está formado por capacidades (diagnosticar, adaptar, remediar,
evaluar…), no por agentes. Un nodo, tres nodos, cinco agentes o un subgrafo
son implementaciones intercambiables de una capacidad; la capacidad
permanece estable aunque su implementación cambie por completo. Corolario
de P4: P4 define qué es un agente (una capacidad encarnada); P13 define qué
es lo estable (la capacidad, nunca su topología). El modelo de dominio
(RFC-0002) se escribe en términos de capacidades; el runtime (RFC-0004)
decide topologías, y puede cambiarlas sin tocar el dominio.

## P15 — El runtime nunca crea conocimiento de dominio

Toda afirmación y toda propuesta son autoradas por una capacidad o por el
Platform Boundary. Los mecanismos de coordinación — deliberación,
enrutamiento, reducers, scheduler — únicamente **seleccionan, ordenan,
validan o descartan** conocimiento existente; jamás generan conocimiento
nuevo. Si la respuesta correcta es una síntesis, el mecanismo reconvoca a
una capacidad para que la proponga: un mecanismo que redacta es cognición
central disfrazada.

*Nota de numeración:* P14 está reservado para la propuesta registrada
«Inmutabilidad de la historia» (ver README), pendiente de evaluación tras
el RFC-0007; este principio se numera P15 para no invalidar referencias
existentes.

---

## Procedencia

- P1–P6, P8–P10 provienen de los principios enunciados por el tesista
  (2026-07-10), con dos precisiones del arquitecto: P2 distingue memoria de
  trabajo efímera de estado persistente; P8 se endurece conectándolo con P7.
- **P7 y P11 son adiciones del arquitecto**, aceptadas por el tesista en la
  segunda iteración: P7 rompe con el atajo histórico de eventos simulados
  (dentro del runtime) y fue endurecido a principio científico ("real y
  reproducible") a propuesta del tesista; P11 eleva a principio la decisión
  "contrato, no migración".
- **P12, P13 y la elevación del `LearningState` a Aggregate Root (P1) son
  propuestas del tesista** (segunda iteración). P12 fue reformulado por el
  arquitecto como "función pura del estado" para hacerlo compatible con el
  enrutamiento dependiente de contenido (ver RFC-0004 cuando exista).
- **P15 nació como regla local** («la deliberación selecciona, jamás
  crea», CONCEPT-0002 §3), fue registrada como candidata, superó su
  primera prueba de diseño en el RFC-0006 (síntesis por reconvocatoria) y
  fue elevada y **generalizada por el tesista** a prohibición sobre todo
  el runtime (2026-07-10, enmienda aprobada explícitamente).
