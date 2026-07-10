# RFC-0003 — LearningState: anatomía, disciplina de mutación e invariantes

- **Estado:** Aceptado (2026-07-10, rev. 4 — aprobado por el tesista con sus
  refinamientos de precisión; incluye dos ajustes del Walkthrough-0001
  señalados en §7, sujetos a su ratificación)
- **Autor:** Equipo de arquitectura (Claude + tesista)
- **Fecha:** 2026-07-10
- **Aprueba:** Renato Lara (tesista / Product Owner)
- **Gobernado por:** FOUNDATIONAL_PRINCIPLES.md (P1, P2, P6, P7, P10, P12), RFC-0001, RFC-0002
- **Capa (RFC-0001 §1):** Kernel
- **Runtime Contract:** define los campos del estado que satisfacen las
  cinco preguntas (§5)

## Objetivo

Definir la realidad educativa que el `LearningState` representa, su
anatomía, la disciplina con la que muta y el catálogo de invariantes que
lo protege. Todo lo demás — grafo, consenso, memoria, replay — se apoyará
en esta forma.

## Decisión irreversible

> **El `LearningState` es el único modelo autorizado de la realidad del
> runtime.**

Ningún nodo tiene verdad propia; ningún agente conserva estado; ningún
consenso mantiene datos ocultos; ningún LLM recuerda nada fuera del estado.
Lo que no está en el `LearningState` no ocurrió para el runtime.

La anatomía (§2) y la disciplina de mutación (§4) — contexto inmutable +
registro *append-only* de facts, claims, deliberaciones y decisiones +
proyección de ejecución, mutado solo por reducers que validan invariantes y
emiten los Domain Events — son las consecuencias operativas de ese
compromiso. Checkpointing (RFC-0008), replay, consenso (RFC-0006) y
auditoría (RFC-0007) asumirán esta forma; cambiarla después implica
rediseñarlos.

## Contexto

- Obligaciones heredadas: el `LearningState` es el Aggregate Root (P1) y el
  estado de UNA sesión de aprendizaje (RFC-0002 §1); debe estructurarse por
  lo que las ocho capacidades leen y escriben (RFC-0002 §3); su catálogo de
  invariantes es requisito de completitud (RFC-0001 §5); debe declarar qué
  campos satisfacen el Runtime Contract (RFC-0001 Consecuencias).
- Insumos resueltos en este RFC: la propuesta constitucional **P14**
  (adoptada como diseño, §4), el patrón *event-sourced ligero* (§4), el
  `LearningState` como único origen de Domain Events (§4), y la hipótesis
  **Knowledge Claim** (RFC-0002): su *forma* queda materializada aquí como
  la sección `claims`; su *semántica* de consenso se decide en RFC-0006.
- Puente terminológico con RFC-0002: la "evidencia" que las capacidades
  escriben (RFC-0002 §3) se materializa en el estado como **facts +
  claims**. No hay contradicción: RFC-0002 habla el lenguaje del dominio;
  este RFC define su forma en el Kernel.
- Relación con la hipótesis de la tesis: el estado es donde la adaptación
  deja de ser afirmación y se vuelve dato. Las cinco preguntas del Runtime
  Contract se responden leyendo el estado, no instrumentando código.

## Propuesta

### 1. La realidad que representa

El `LearningState` representa **una sesión de aprendizaje en curso**: lo
que el sistema sabía al abrirla, los hechos que observó, las
interpretaciones y propuestas que sus capacidades afirmaron, lo que
deliberó y decidió y por qué, y lo que propone que se recuerde al cerrarla.
No representa al estudiante (eso es el Student Model, que la trasciende) ni
al currículo (plataforma).

El registro distingue tres naturalezas que no deben confundirse:

- un **fact** es una observación objetiva: *"tiempo empleado: 35 s"*;
- un **claim** es una interpretación respaldada: *"35 segundos indican
  fluidez"* — o una propuesta: *"conviene una explicación visual"*;
- una **decisión** es la acción que el sistema adoptó.

Los agentes pueden discrepar sobre claims; jamás sobre facts. Un fact solo
puede ser cuestionado por un nuevo fact que lo supersede — nunca por una
opinión.

> **El `LearningState` representa la evolución del conocimiento del runtime
> mediante una cadena epistemológica:**
> `Facts → Claims → Deliberación → Decisión → Validación`
> — *¿qué sé? → ¿qué creo? → ¿qué debatimos? → ¿qué decidimos? →
> ¿teníamos razón?*

### 2. Anatomía

Ocho secciones, con tres regímenes de mutabilidad:

```
LearningState
├── identidad      [inmutable]    session_id, student_id, versión del
│                                 student model cargada, objetivo(s) al
│                                 abrir, versiones de configuración
│                                 (banco de ítems, política pedagógica)
├── contexto       [inmutable]    student model (versión cargada), ruta
│                                 vigente, estructura del módulo — solo
│                                 lectura durante toda la sesión
├── facts          [append-only]  observaciones objetivas, con provenance
├── claims         [append-only]  interpretaciones y propuestas de las
│                                 capacidades, con respaldo y confianza
├── deliberaciones [append-only]  registradas por el Kernel: claims en
│                                 tensión, posiciones, regla de resolución,
│                                 resultado (P8)
├── decisiones     [append-only]  derivadas de una deliberación o de un
│                                 claim-propuesta único; cada una con sus
│                                 campos del Runtime Contract
├── ejecución      [proyección]   fase del ciclo, transición actual,
│                                 interrupciones HITL pendientes — lo único
│                                 genuinamente "actual"; cada cambio es una
│                                 transición registrada
└── salidas        [al cierre]    nueva versión propuesta del student
                                  model, ruta actualizada, resumen para la
                                  capa de memoria (RFC-0005)
```

No existe sección `Memory`: lo que la sesión sabe entra por `contexto` y lo
que propone recordar sale por `salidas` — la sesión es dueña de la
ejecución, no del conocimiento (RFC-0002 §1).

### 3. Los sobres

Dos sobres, porque facts y claims tienen naturalezas — e invariantes —
distintas. Solo el payload es libre.

```
FactEntry                             ClaimEntry
├── autor       capacidad|boundary¹   ├── autor       capacidad
├── contenido   payload libre         ├── tipo        interpretación | propuesta
├── provenance  de qué mecanismo      ├── afirmación  payload libre
│               salió (§3.1)          ├── respaldo    refs a entradas vigentes²
└── vigencia    vigente |             ├── confianza   grado declarado
                superseded-por(ref)   ├── provenance  de qué mecanismo salió (§3.1)
                                      └── vigencia    vigente | superseded-por(ref)
```

¹ *Ajuste del Walkthrough-0001:* los **hechos del mundo** (ciclo de vida de
la sesión, telemetría cruda de la plataforma) no tienen capacidad natural
que los produzca: su autor es el **Platform Boundary**. El Boundary jamás
autora claims — el mundo aporta hechos; solo las capacidades interpretan.

² *Ajuste del Walkthrough-0001:* el respaldo referencia entradas vigentes
del registro — facts, claims **o decisiones** (Validar se respalda en la
decisión que valida) — y elementos versionados del `contexto` (p. ej. el
student model cargado).

Un fact **no lleva respaldo**: su sustento es su origen (provenance), no
otra afirmación. Un claim **exige respaldo**: referencias a los facts u
otros claims que lo sostienen. Esa asimetría es la corrección de fondo de
esta revisión (antes, INV-4 exigía respaldo a todo por igual — un defecto).

#### 3.1 Provenance

Toda entrada declara de qué mecanismo salió su contenido:

```
provenance ∈ { llm(modelo, versión, prompt-id),
               instrumento(banco, ítem),
               humano(rol, vía HITL),
               regla(id),
               telemetría(fuente en la plataforma) }
```

`autor` y `provenance` son complementarios: *qué capacidad lo afirma* vs
*de qué mecanismo salió*. La provenance no es un metadato opcional — es
requisito de P7 (la evidencia real se prueba por su origen) y de P12 (el
replay debe distinguir el no-determinismo grabado — llm — de lo
recomputable — regla, instrumento).

### 4. Disciplina de mutación (event-sourced ligero)

Ningún nodo escribe el estado. El circuito único es:

```
Nodo ──propuesta de cambio──▶ Reducer ──valida invariantes──▶ LearningState
                                  │
                                  ├──▶ Domain Event ──▶ Observabilidad (RFC-0007)
                                  └──▶ Checkpoint     (RFC-0008)
```

- Los reducers son las **operaciones del agregado**: validan invariantes
  antes de aplicar. Tienen exactamente **dos** resultados: *aplicado* o
  *rechazado-y-registrado* (un rechazo es información, no una excepción
  silenciosa). El aplazamiento **no** es un resultado de reducer: es un
  resultado de deliberación (§4.1) — un reducer que "espera evidencia"
  sería política dentro del mecanismo (violación de P5).
- Los Domain Events nacen exclusivamente de transiciones del estado; no
  existe otro emisor (queda prohibido el patrón Nodo → EventBus).
- No es Event Sourcing completo: el estado es la fuente primaria y los
  eventos su derivada, no al revés. Se heredan las propiedades necesarias
  (mutación centralizada, invariantes en un solo lugar, replay) sin el
  costo de proyecciones y versionado de eventos.

**La StateTransition es la unidad atómica del runtime** — ciudadana de
primera clase, no un detalle del circuito:

```
StateTransition = propuesta → validación de invariantes → aplicación
                  → Domain Events → checkpoint
```

Todo lo que el runtime hace es una secuencia de transiciones. El RFC-0004
no orquestará nodos que "hacen cosas": orquestará productores de propuestas
cuyas transiciones ocurren aquí.

**Evaluación de P14 (inmutabilidad de la historia):** se ADOPTA como
decisión de diseño de este RFC. Las secciones facts, claims, deliberaciones
y decisiones son append-only; una corrección es una nueva entrada que marca
`superseded-por` a la anterior — la historia nunca se reescribe (INV-3).
Recomendación sobre su elevación constitucional: decidirla tras el
RFC-0007, cuando se compruebe que la observabilidad y el replay descansan
en ella; la enmienda estará entonces justificada por evidencia de diseño.

#### 4.1 Resultados de una deliberación

```
resultado ∈ { resuelta   (con regla de resolución, claims aceptados y
                          confianza de la resolución),
              aplazada   (registrando QUÉ evidencia falta y qué condición
                          dispara la reevaluación),
              escalada   (a humano, vía HITL — RFC-0009) }
```

Una deliberación aplazada queda registrada append-only: *"el sistema supo
que no sabía"* es evidencia de primer orden para la explicabilidad. Los
disparadores de reevaluación son agenda del RFC-0006; los criterios de
escalada, del RFC-0009.

### 5. Satisfacción del Runtime Contract

| Pregunta | Dónde se responde en el estado |
|----------|--------------------------------|
| 1. ¿Qué observó? | `facts` (Tutorizar, Evaluar, Validar) |
| 2. ¿Qué interpretó? | `claims` tipo interpretación (Modelar, Diagnosticar), con `respaldo` hacia los facts |
| 3. ¿Qué alternativas evaluó? | `claims` tipo propuesta (Orientar, Adaptar, Remediar), incluidas las alternativas descartadas por la propia capacidad |
| 4. ¿Por qué eligió una? | `deliberaciones` (posiciones, regla de resolución, resultado) y `decisiones` (referencia a su origen) |
| 5. ¿Qué ocurrió después? | `facts` posteriores + `claims` de Validar con `respaldo` hacia la decisión validada |

La cadena `decisión → deliberación → claims → facts` es navegable por
referencias (`respaldo`): la explicabilidad es un **recorrido causal del
estado** — tipado (`Fact → Claim → Decision → Validation`) y no
cronológico —, no un módulo (P6, RFC-0002 §2).

### 6. Catálogo de invariantes

Aplicadas por los reducers en la frontera del agregado (P1). Violación =
rechazo registrado.

| # | Invariante |
|---|-----------|
| INV-1 | No existe `LearningState` sin identidad completa: sesión, estudiante, versión del student model y versiones de configuración se fijan atómicamente al abrir |
| INV-2 | `identidad` y `contexto` son inmutables durante la sesión; una nueva versión del student model solo puede aparecer en `salidas`, nunca reemplazar el contexto cargado |
| INV-3 | `facts`, `claims`, `deliberaciones` y `decisiones` son append-only; corregir es añadir una entrada que supersede, jamás modificar o borrar |
| INV-4 | Todo fact declara autor (una capacidad, o el Platform Boundary para hechos del mundo) y provenance; un fact jamás lleva respaldo — su sustento es su origen |
| INV-5 | Todo claim declara autor (siempre una capacidad), provenance, confianza y respaldo hacia entradas vigentes (facts, claims o decisiones) o elementos versionados del contexto; no existen afirmaciones sin origen causal |
| INV-6 | Toda decisión referencia la deliberación o el claim-propuesta único que la produjo; no existen decisiones huérfanas |
| INV-7 | Toda deliberación registra participantes, posiciones, regla de resolución y resultado (resuelta / aplazada / escalada); si es resuelta, registra la confianza de la resolución; si es aplazada, registra qué evidencia falta |
| INV-8 | Los objetos de una deliberación son siempre claims; los facts no se deliberan y solo pueden ser cuestionados por nuevos facts, jamás por claims |
| INV-9 | Hay a lo sumo un objetivo vigente y una ruta activa por sesión |
| INV-10 | Los Domain Events nacen solo de transiciones aplicadas por reducers; ningún otro componente emite eventos |
| INV-11 | El estado es serializable entre transiciones en todo momento (condición de checkpointing, P10) |
| INV-12 | Toda decisión de adaptación queda `pendiente-de-validación` hasta que Validar registre su efecto o el cierre de sesión la marque `no-observada`; ninguna desaparece sin veredicto |

### 7. Registro de hipótesis: resolución y nuevas entradas

Trazabilidad de la revisión del tesista (2026-07-10):

- **H1 (Facts/Claims/Decisions): ADOPTADA en esta revisión.** Dejó de ser
  hipótesis al comprobarse que corrige un defecto (la antigua INV-4 exigía
  respaldo a observaciones crudas) y que entrega al RFC-0006 su objeto
  limpio: el consenso discute claims, jamás facts (INV-8).
- **H2 (Provenance): ADOPTADA en esta revisión** (§3.1) como requisito de
  P7 y P12.
- **H3 (Deferred): ADOPTADA, reubicada.** No es resultado de reducer sino
  de deliberación (§4.1).
- **H4 — Intentions / Resolutions (REGISTRADA, no incorporada):** propuesta
  del tesista: evaluar si conviene distinguir explícitamente entre la
  propuesta emitida por una capacidad (*intención*) y la decisión adoptada
  por el sistema (*resolución*), de modo que el consenso opere sobre
  intenciones y produzca resoluciones antes de la ejecución
  (`Intent → Resolution → Execution`), renombrando eventualmente
  `decisiones`. No corrige un defecto del modelo actual (los claims tipo
  propuesta ya capturan la intención; INV-6 ya distingue propuesta de
  decisión): es una posible ganancia de expresividad. **Se evalúa en el
  RFC-0006**, donde se decide cómo fluye una propuesta desde una capacidad
  hasta una acción ejecutada. *Ampliación del tesista (rev. 4):* la cadena
  real termina en `Decision → Execution → Validation` — la decisión no
  modifica el mundo; la ejecución sí. El Walkthrough-0001 muestra que el
  modelo actual ya lo expresa (decisión entregada por el Boundary + fact
  de entrega); la distinción explícita es parte de lo que H4 evalúa.
- **H5 — Método de obtención en la provenance (REGISTRADA, no
  incorporada):** propuesta del tesista: además de *de qué mecanismo salió*
  (§3.1), registrar *cómo fue obtenido* el contenido (opción múltiple,
  ejercicio interactivo, ejecución de código). No corrige un defecto;
  enriquece el análisis de investigación. **Se evalúa en el RFC-0007**,
  donde se decidirá si es una dimensión de la provenance o una convención
  de payload del instrumento.

**Ajustes del Walkthrough-0001 (incorporados en rev. 4, sujetos a
ratificación del tesista):** (a) los hechos del mundo pueden ser autorados
por el Platform Boundary (INV-4); (b) el respaldo se amplía a decisiones y
a elementos versionados del contexto (INV-5) — el walkthrough reveló que la
tabla §5 ya lo asumía para Validar y las invariantes no lo permitían.

## Alternativas consideradas y rechazadas

1. **Estado mutable clásico** (campos que se sobrescriben — el uso ingenuo
   del estado en LangGraph): rechazado. Pierde la historia, vuelve
   imposible responder "¿qué alternativas evaluó?" y "¿qué ocurrió
   después?" (contrato), y reduce el replay a re-ejecutar a ciegas.
2. **Event Sourcing completo** (los eventos como fuente primaria, el estado
   como proyección): rechazado por sobreingeniería. Exige versionado de
   eventos, proyecciones y reprocesamiento — costo permanente sin beneficio
   a la escala de este proyecto. El híbrido §4 hereda las propiedades que
   la tesis necesita.
3. **`LearningState` como historial completo del estudiante**: rechazado.
   Contradice el concepto agregador (RFC-0002 §1), vuelve inabordables el
   checkpointing y el replay, y mezcla ejecución con conocimiento — la
   sesión consume una versión del modelo, no lo posee.
4. **Sub-estados privados por capacidad**: rechazado. Viola P1/P2 y
   reintroduce la SharedMemory fragmentada del Legacy con otro nombre.
5. **Registro homogéneo de "evidencia"** (diseño de la rev. 1 de este RFC):
   rechazado y reemplazado por facts/claims. Trataba observaciones e
   interpretaciones con las mismas invariantes, lo que hacía INV-4
   incorrecta para observaciones crudas y privaba al consenso de su objeto
   propio.

## Ventajas / Riesgos / Impacto / Complejidad

- **Ventajas:** la explicabilidad y el replay son propiedades de la forma
  del estado (recorrido causal tipado), no módulos; el consenso del
  RFC-0006 recibe claims respaldados y con confianza — y la garantía de que
  nunca deliberará hechos; la provenance hace demostrable P7 y ejecutable
  P12; los invariantes viven en un solo lugar (reducers); P14 queda
  materializada sin esperar su decisión constitucional.
- **Riesgos:** (1) crecimiento del estado en sesiones largas (append-only)
  — mitigación: la sesión acota por diseño y `salidas` destila hacia
  memoria; el detalle de checkpoints diferenciales es del RFC-0008;
  (2) rigidez de los sobres — mitigación: los sobres son fijos, los
  payloads libres por capacidad; (3) clasificación errónea fact/claim por
  una capacidad (disfrazar interpretación de hecho) — mitigación: INV-4/5
  hacen barata la detección (un "fact" con contenido interpretativo carece
  de provenance instrumental plausible) y la auditoría del RFC-0007 lo
  vigila; (4) invariantes costosas — mitigación: todas son verificables
  localmente en la transición.
- **Impacto:** RFC-0004 queda obligado a que los nodos produzcan propuestas
  (nunca escrituras); RFC-0005 define qué cruza sesiones (`contexto` de
  entrada, `salidas` de salida); RFC-0006 hereda su objeto (claims), los
  disparadores de reevaluación de deliberaciones aplazadas y la hipótesis
  H4; RFC-0007 audita leyendo Domain Events; RFC-0009 hereda la escalada.
- **Complejidad:** conceptual alta (es el corazón), de implementación
  moderada — el circuito §4 mapea con naturalidad a reducers/channels del
  motor (detalle del Graph Engine, RFC-0004).

## Recomendación

Aceptar la anatomía de ocho secciones, los dos sobres con provenance, el
circuito de mutación event-sourced ligero con resultados de deliberación
{resuelta, aplazada, escalada} y el catálogo INV-1..INV-12. Diferir la
elevación constitucional de P14 hasta el RFC-0007, y la semántica de
consenso sobre claims junto con H4 hasta el RFC-0006 — todas quedan
habilitadas por esta forma sin quedar decididas.

## Consecuencias

- El vocabulario `identidad / contexto / facts / claims / deliberaciones /
  decisiones / ejecución / salidas`, los sobres `FactEntry`/`ClaimEntry`,
  la provenance, la cadena epistemológica y la **StateTransition** son
  normativos para todos los RFC posteriores.
- El RFC-0004 se define en términos de transiciones: los nodos son
  productores de propuestas; la StateTransition es la unidad que valida,
  aplica, emite y checkpointea.
- Ningún nodo escribe el estado: propone. Los reducers son el único punto
  de mutación y de emisión de eventos (INV-10), con exactamente dos
  resultados.
- El consenso (RFC-0006) delibera claims, jamás facts (INV-8), y hereda:
  disparadores de reevaluación de deliberaciones aplazadas, la semántica
  Knowledge Claim y la hipótesis H4 (Intentions/Resolutions).
- El RFC-0007 no inventa instrumentación: consume los Domain Events del
  circuito §4.
- Queda prohibido introducir secciones fuera de las ocho, sobres distintos
  de los dos definidos, o canales de escritura que no pasen por reducers.
