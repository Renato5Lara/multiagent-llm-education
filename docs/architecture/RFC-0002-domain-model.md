# RFC-0002 — Modelo de dominio: responsabilidades, resultados y capacidades

- **Estado:** Aceptado (2026-07-10, rev. 3 — con modelo de propiedad y registro de la hipótesis Knowledge Claim)
- **Autor:** Equipo de arquitectura (Claude + tesista)
- **Fecha:** 2026-07-10
- **Aprueba:** Renato Lara (tesista / Product Owner)
- **Gobernado por:** FOUNDATIONAL_PRINCIPLES.md (P4, P5, P8, P13), RFC-0001
- **Capa (RFC-0001 §1):** Domain
- **Runtime Contract:** este RFC establece qué capacidad responde cada una
  de las cinco preguntas (ver Verificación de completitud)

## Objetivo

Definir la ontología del dominio: el concepto que lo agrega, las
responsabilidades fundamentales del sistema educativo que el runtime
automatiza, los resultados que cada una produce, y las capacidades que
emergen de ellas. Este vocabulario será el idioma de todos los RFC
posteriores.

## Decisión irreversible

Dos compromisos, y el segundo es el mayor:

1. **El vocabulario del dominio** — responsabilidades, resultados esperados
   y capacidades nombrarán los campos del `LearningState` (RFC-0003), los
   nodos y subgrafos (RFC-0004), los participantes del consenso (RFC-0006)
   y las columnas de la evidencia de la tesis.
2. **El concepto agregador del dominio es la Sesión de Aprendizaje** (§1).
   El RFC-0003 construirá el `LearningState` sobre esta decisión; revertirla
   después significa rediseñar el estado, el checkpointing y el replay.

Por eso el modelo parte de las responsabilidades del sistema educativo
(estables) y no de los agentes existentes (implementación): las capacidades
se *derivan*, no se heredan del Legacy ni se intuyen.

## Contexto

- Método impuesto por el tesista: primero *¿cuáles son las responsabilidades
  fundamentales del sistema educativo que queremos automatizar?*; entre cada
  responsabilidad y su capacidad se declara el **resultado esperado**
  (outcome), de modo que el dominio exprese primero qué conocimiento o
  decisión produce y solo después cómo se implementa.
- Conocimiento del dominio reutilizado de v1 (insumo legítimo, no
  restricción): modelo de perfil multimodal (VARK), competencias cognitivas
  (COMP-0..5) e indicador conductual (IFA), matriz modalidad × profundidad,
  ciclo pedagógico v2.1, módulos 1–9 de Fundamentos de la Programación, y la
  conclusión del análisis de Misión Activa: la sesión de aprendizaje como
  dueña del proceso.
- Relación con la hipótesis: R3 (diseñar la experiencia de aprendizaje) es
  la responsabilidad donde vive la variable dependiente de la tesis — la
  adaptación multimodal. Además, el nivel de resultados esperados conecta el
  dominio con el aporte declarado del proyecto: un modelo de **hipótesis
  pedagógicas validadas por evidencia**.

## Propuesta

### 1. El concepto agregador: la Sesión de Aprendizaje

El centro conceptual del dominio — no confundir con el Aggregate Root
técnico (P1) — es la **Sesión de Aprendizaje**: el período en que un
estudiante trabaja sobre objetivos de su ruta y el sistema observa, decide
y valida. Candidatos evaluados:

- **El Estudiante**: rechazado como agregador. Es la entidad más importante
  del dominio, pero trasciende al runtime (existe también en la plataforma)
  y no acota nada: un dominio agregado por el estudiante no tiene unidad de
  trabajo que abrir, ejecutar y cerrar.
- **El Objetivo de Aprendizaje**: rechazado. Demasiado granular: las señales
  conductuales, las decisiones de adaptación y las deliberaciones cruzan
  objetivos dentro de una misma sesión; agregarlo ahí fragmentaría el
  contexto de decisión.
- **La Sesión de Aprendizaje**: elegida. Toda pasada del ciclo pedagógico
  ocurre dentro de una; los checkpoints, el replay y el Human-in-the-Loop
  se acotan naturalmente a ella; las cinco respuestas del Runtime Contract
  se dan por decisión *dentro* de una sesión.

Consecuencia directa para el RFC-0003: **el `LearningState` es el estado de
UNA sesión de aprendizaje.** Lo que trasciende la sesión — el modelo del
estudiante, la ruta — entra a la sesión como evidencia cargada y sale como
nueva versión a través de la capa de memoria (RFC-0005); la sesión es la
unidad de ejecución, no el límite del conocimiento.

**La sesión es dueña de la ejecución, no del conocimiento.** El modelo de
propiedad del dominio es:

```
Student ──posee──▶ Student Model ──participa (una versión)──▶ Learning Session ──se ejecuta como──▶ LearningState
```

Nunca al revés: el estudiante y su modelo sobreviven a la sesión; la sesión
consume una versión del modelo y propone la siguiente. Así quedan separadas
la persistencia (plataforma y memoria), la ejecución (sesión) y el
aprendizaje acumulado (modelo del estudiante).

Nota de procedencia: el análisis de v1 (SPEC de Misión Activa) llegó a la
misma conclusión — la sesión como dueña del proceso. Se registra como
convergencia de conocimiento del dominio validado, no como herencia de
implementación.

### 2. Responsabilidades fundamentales (R1–R7)

Cada responsabilidad se enuncia sin referencia a agentes ni tecnología, se
clasifica por su naturaleza y declara su **resultado esperado** — el
conocimiento o decisión que produce, en lenguaje del dominio:

| # | Responsabilidad | Naturaleza | Resultado esperado |
|---|-----------------|------------|--------------------|
| R1 | Conocer al estudiante | Cognitiva | Un modelo vivo del estudiante: cómo aprende, qué sabe, cómo se comporta |
| R2 | Determinar qué necesita aprender | Cognitiva → Decisión | Una hipótesis pedagógica: dónde está y cuál es el siguiente objetivo |
| R3 | **Diseñar la experiencia de aprendizaje** | Decisión | Una decisión de adaptación: cómo vivirá el estudiante el objetivo vigente (modalidad, profundidad, ritmo, andamiaje, retroalimentación) |
| R4 | Acompañar mientras aprende | Interacción | Sostén contextual y señales conductuales capturadas |
| R5 | Comprobar que aprendió | Medición | Evidencia evaluativa del dominio de competencias |
| R6 | Reaccionar cuando no aprende | Intervención | Una intervención dirigida a la brecha detectada |
| R7 | Validar sus propias decisiones | Metaevaluación | Un veredicto sobre cada adaptación: funcionó o no, y por qué |

Dos notas sobre la tabla:

- **Alcance de R3.** "Diseñar la experiencia" es más que presentar
  contenido: decide modalidad, ritmo, dificultad, andamiaje y estilo de
  retroalimentación. Pero R3 **compone** a las demás responsabilidades, no
  las absorbe: el *qué* aprender sigue siendo R2, el *si aprendió* R5, el
  *qué hacer si no* R6. Sin esta frontera, R3 degeneraría en la
  responsabilidad-dios y el resto en sus auxiliares.
- **La doble naturaleza de R2** (cognitiva al diagnosticar, de decisión al
  orientar) es precisamente lo que justifica su descomposición en dos
  capacidades — la taxonomía valida la separación.

Lo que **no** es responsabilidad del dominio: la explicabilidad. Explicar
las decisiones no es algo que el dominio *hace*: es una propiedad que el
Kernel *garantiza* (Runtime Contract, P6/P7). Ninguna capacidad "de
explicar" existirá.

### 3. De responsabilidades a capacidades

**Criterio de existencia de una capacidad:** (a) sirve a una
responsabilidad; (b) produce evidencia propia y distinguible en el estado;
(c) es enunciable en lenguaje pedagógico (P4). Si dos candidatas siempre
escriben juntas y nunca pueden discrepar, son una sola.

Ocho capacidades emergen. La evidencia que cada una escribe es el resultado
esperado de su responsabilidad, materializado en el estado:

| Capacidad | Resp. | Lee del estado | Escribe (su evidencia) |
|-----------|-------|----------------|------------------------|
| **Modelar** (al estudiante) | R1 | evidencia conductual y evaluativa acumulada | modelo del estudiante, versionado |
| **Diagnosticar** | R2 | modelo del estudiante + resultados recientes | estado de conocimiento por competencia, con confianza |
| **Orientar** | R2 | diagnóstico + estructura de módulos | propuesta de siguiente objetivo de la ruta |
| **Adaptar** | R3 | objetivo + modelo del estudiante + señales de sesión | decisión de diseño de experiencia (modalidad × profundidad × ritmo × andamiaje) **con las alternativas que evaluó** |
| **Tutorizar** | R4 | estado completo de la sesión | interacciones y señales conductuales detectadas (confusión, frustración, fluidez) |
| **Evaluar** | R5 | objetivo + banco de ítems | resultados con trazabilidad ítem a ítem |
| **Remediar** | R6 | evidencia de no-aprendizaje | propuesta de intervención dirigida |
| **Validar** | R7 | decisión de adaptación + lo que ocurrió después | efecto medido de la adaptación; retroalimenta a Modelar |

Notas de naming:

- **Modelar** reemplaza a "Perfilar": un perfil suena estático; lo que R1
  exige es un modelo vivo que evoluciona con cada evidencia. El término
  coincide además con el canon de la literatura de Intelligent Tutoring
  Systems (*student modeling*), lo que da al dominio anclaje académico
  citable.
- **Adaptar** conserva su nombre aunque R3 se haya renombrado: "adaptación
  multimodal" es la palabra de la hipótesis de la tesis, y la capacidad es
  su ejecutora directa. La responsabilidad describe la ambición; la
  capacidad, el término de investigación.

Distinción que evita una confusión clásica: **Evaluar mide al estudiante;
Validar mide al sistema** (la calidad de sus propias decisiones de
adaptación).

Conforme a P13, ninguna capacidad prejuzga su topología: cada una podrá ser
un nodo, varios o un subgrafo (lo decide RFC-0004), y ninguna conoce a otra
(P3) — solo leen y escriben el estado.

### Registro — hipótesis arquitectónica (no normativa)

> **Propuesta de investigación del tesista (2026-07-10):** durante el diseño
> del RFC-0006 se evaluará introducir el concepto de **Knowledge Claim** —
> la representación explícita de afirmaciones del dominio respaldadas por
> evidencia (p. ej. *"el estudiante domina COMP-2 con confianza 0.81"* ←
> respuestas 3, 4 y 8, tiempos, intentos). Bajo esa hipótesis, las
> capacidades producen afirmaciones, el consenso valida afirmaciones (no
> decisiones) y las decisiones derivan de las afirmaciones aceptadas. Si
> resulta beneficioso, podría convertirse en un elemento estructural del
> consenso multiagente sin modificar el modelo de responsabilidades de este
> RFC. La decisión pertenece al RFC-0006; su impacto en la forma del estado,
> al RFC-0003.

### 4. Tensiones canónicas (dónde vive la deliberación)

Deliberar **no** es una capacidad: es lo que hace el runtime cuando las
capacidades producen evidencia en tensión (P8). Las tensiones legítimas de
este dominio — la agenda del RFC-0006 — son:

1. **¿Avanzar o reforzar?** — Orientar propone el siguiente objetivo;
   Remediar propone intervenir sobre el actual. Es la tensión más frecuente
   y la más valiosa para la hipótesis.
2. **¿Qué modalidad?** — el modelo histórico del estudiante (Modelar)
   sugiere una; las señales de la sesión en curso (Tutorizar, Validar)
   sugieren otra. Adaptar debe resolver con ambas evidencias sobre la mesa.
3. **¿Dominó el objetivo?** — el resultado puntual (Evaluar) y la
   trayectoria (Modelar) pueden contradecirse: un buen examen tras una
   sesión errática, o al revés.

Donde no hay tensión posible, decide una capacidad sola y el consenso no
se convoca (P7, P8).

### 5. Verificación de completitud

El modelo es completo respecto al Runtime Contract (RFC-0001 §4): cada
pregunta tiene capacidades responsables, y cada capacidad alimenta al menos
una pregunta.

| Pregunta del contrato | Responsables |
|-----------------------|--------------|
| 1. ¿Qué observó? | Tutorizar, Evaluar, Validar (captura de evidencia) |
| 2. ¿Qué interpretó? | Modelar, Diagnosticar |
| 3. ¿Qué alternativas evaluó? | Orientar, Adaptar, Remediar (propuestas) |
| 4. ¿Por qué eligió una? | la deliberación registrada por el Kernel sobre esas propuestas |
| 5. ¿Qué ocurrió después? | Validar |

## Alternativas consideradas y rechazadas

1. **Partir de los agentes del Legacy** (Profiler, Tutor, Evaluator,
   ConsensusEngine…): rechazado. Es modelar la implementación, no el
   dominio (P13), y el camino más corto a reconstruir BaseAgent con otro
   motor. Nota: que varios nombres coincidan al final no valida el atajo —
   coinciden porque el Legacy también automatizaba estas responsabilidades,
   pero aquí quedan *derivados* y con fronteras de evidencia definidas.
2. **Una capacidad por fase del ciclo pedagógico** (Capturar, Interpretar…):
   rechazado. Confunde el programa con el dominio (RFC-0001 §2): las fases
   *orquestan* capacidades, no las definen. Modelar, por ejemplo, actúa en
   Capturar y en Validar.
3. **Modelado DDD completo** (bounded contexts formales, ubiquitous language
   exhaustivo, context maps): rechazado por sobreingeniería. El runtime
   tiene UN contexto — aprendizaje adaptativo de Fundamentos de la
   Programación —; auth, gestión y contenido curricular pertenecen a la
   plataforma, del otro lado del boundary (P11).
4. **Estudiante u Objetivo como concepto agregador**: rechazados en §1 —
   el primero no acota la unidad de trabajo, el segundo fragmenta el
   contexto de decisión.

## Ventajas / Riesgos / Impacto / Complejidad

- **Ventajas:** dominio estable ante cambios de topología y de motor; el
  nivel de resultados esperados hace verificable la relación
  responsabilidad → evidencia (el estado materializa outcomes, no
  ocurrencias); las tensiones canónicas dan al RFC-0006 un objeto real que
  deliberar; la sesión como agregador da al RFC-0003 una unidad de trabajo
  con fronteras claras.
- **Riesgos:** (1) que R3 absorba al resto de responsabilidades —
  mitigación: la frontera "compone, no absorbe" (§2); (2) granularidad de
  capacidades (monolitos o micro-agentes teatrales que violan P8) —
  mitigación: el criterio de existencia §3; (3) que Tutorizar gravite hacia
  "el centro del sistema" por ser la cara visible — mitigación: RFC-0001 §6,
  es una capacidad más; (4) anclaje mental en los nombres del Legacy —
  mitigación: cada capacidad queda definida por su evidencia, no por su
  nombre.
- **Impacto:** idioma normativo de RFC-0003 en adelante; el RFC-0003 hereda
  dos obligaciones — construir el `LearningState` como estado de una sesión
  y estructurarlo por las evidencias de la tabla §3.
- **Complejidad:** conceptual media; sin implementación.

## Recomendación

Aceptar el modelo: Sesión de Aprendizaje como concepto agregador, 7
responsabilidades con naturaleza y resultado esperado, 8 capacidades.
Continuar con el RFC-0003 (LearningState) expresando el estado como *el
registro, dentro de una sesión, de la evidencia que estas capacidades leen
y escriben*, más su catálogo de invariantes — requisito de completitud ya
fijado en RFC-0001 §5.

## Consecuencias

- La Sesión de Aprendizaje es el concepto agregador del dominio; el
  `LearningState` (RFC-0003) es el estado de una sesión.
- Las responsabilidades R1–R7 (con naturaleza y resultado esperado) y las
  ocho capacidades son vocabulario normativo; ningún RFC posterior
  introduce capacidades nuevas sin enmendar este documento.
- Lo que trasciende la sesión (modelo del estudiante, ruta) viaja por la
  capa de memoria (RFC-0005) como evidencia versionada.
- Las tres tensiones canónicas §4 son la agenda obligatoria del RFC-0006.
- Nada del Legacy determina nombres, fronteras ni granularidad del dominio.
