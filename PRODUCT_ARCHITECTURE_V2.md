# Product Architecture v2 — Un modelo de hipótesis pedagógicas basado en evidencia

> **Estado: APROBADO como modelo conceptual del producto (2026-07-04).**
> Este documento define la visión y los principios del sistema y es la
> referencia conceptual de todos los sprints siguientes.
>
> **Excepción deliberada:** el Anexo D es un **documento vivo**. Sus decisiones
> arquitectónicas permanecen abiertas — son hipótesis a validar durante el
> desarrollo, no compromisos — y **no se convierten automáticamente en backlog
> de implementación**. Se cerrarán cuando exista suficiente evidencia funcional
> de la experiencia real del estudiante para responderlas con seguridad.

---

> **El sistema no adapta porque conoce al estudiante.
> Adapta porque construye continuamente hipótesis sobre cómo está aprendiendo
> y las valida con nueva evidencia.**
>
> Si esta frase deja de ser cierta, la arquitectura debe considerarse incorrecta.

---

## Las dos preguntas que este documento responde

Cualquier persona — asesor, jurado, desarrollador o una IA en una sesión
futura — debe poder responder esto después de leerlo:

**1. ¿Qué aprende el sistema del estudiante en cada interacción?**

En cada interacción el sistema captura **evidencia de aprendizaje** y con ella
actualiza sus creencias sobre **cómo** está aprendiendo el estudiante — no solo
cuánto sabe. Concretamente, revisa hipótesis sobre:

- con qué **modalidad** su comprensión mejora (visual, lectura, práctica…),
- a qué **ritmo** puede avanzar sin sobrecargarse,
- qué **carga cognitiva** está experimentando ahora,
- qué **concepciones erróneas** arrastra,
- hasta qué **nivel de razonamiento** (Bloom) llega en cada concepto,
- qué **analogías y ejemplos** le funcionan.

Cada una de esas creencias tiene una confianza explícita, una fecha y un
origen. Ninguna es permanente: la evidencia nueva puede reforzarla,
debilitarla o contradecirla.

**2. ¿Cómo utiliza ese aprendizaje para decidir la siguiente acción pedagógica?**

Las hipótesis no actúan solas. Cuando una hipótesis implica cambiar algo del
aprendizaje, los agentes **deliberan**: cada uno aporta su lectura de la
evidencia, votan, y el consenso produce una **decisión pedagógica concreta**
(qué modalidad usar en el siguiente contenido, qué profundidad, qué ejercicio,
qué apoyo ofrecer). Esa decisión queda **trazada y justificada** — se puede
mostrar exactamente qué evidencia la causó — y la evidencia posterior la
**valida o la refuta**, cerrando el ciclo.

Todo lo demás del sistema — pantallas, agentes, APIs, dashboards — es una
consecuencia de este modelo, no su definición.

---

## 1. El aporte científico

La arquitectura multiagente **no es el fin; es el medio**. El aporte de la
tesis se formula así:

> **Un modelo continuo de construcción y validación de hipótesis pedagógicas
> basado en evidencia de aprendizaje, implementado mediante una arquitectura
> multiagente colaborativa.**

Esto es defendible porque desplaza la afirmación de "adaptamos" (cualquier
sistema con reglas lo dice) a "**adaptamos porque la evidencia observada
cambió la hipótesis pedagógica, y podemos demostrar la cadena completa**".

---

## 2. La Evidencia de Aprendizaje

> La unidad principal del sistema es la **Evidencia de Aprendizaje**: toda
> observación fechada y atribuible sobre cómo un estudiante aprende, con un
> grado de confianza explícito.

La evidencia proviene de **cuatro fuentes**:

| Fuente | Qué aporta |
|---|---|
| **Observación** | Señales de comportamiento: ritmo, pausas, reintentos, abandono, signos de sobrecarga |
| **Interacción** | Lo que el estudiante hace con el contenido: qué explora, qué pregunta al tutor, qué ejecuta en el laboratorio de código |
| **Evaluación** | Desempeño demostrado: diagnósticos, evaluaciones, ejercicios resueltos |
| **Preferencias emergentes** | Patrones que emergen del historial (no declarados por el estudiante): la modalidad con la que rinde mejor, los dominios de analogía que le conectan |

Toda evidencia, venga de donde venga, cumple cuatro propiedades:
es **atribuible** (quién la observó), **fechada** (cuándo — la evidencia vieja
decae), **graduada** (con qué confianza) y **trazable** (desde qué interacción
se originó).

El mapeo de estas cuatro fuentes a las estructuras técnicas existentes está en
el **Anexo A**. El cuerpo del documento no necesita nombrar tablas: el asesor,
el jurado y el estudiante piensan en evidencia, no en registros.

---

## 3. El ciclo de adaptación

El corazón del sistema es un ciclo de cinco fases — deliberadamente paralelo
al método científico:

```
  1. CAPTURAR EVIDENCIA        cada interacción produce evidencia
        │                      de una o más de las cuatro fuentes
        ▼
  2. INTERPRETAR EVIDENCIA     los agentes leen la evidencia nueva a la luz
        │                      de la acumulada: converge, diverge, contradice
        ▼
  3. CONSTRUIR HIPÓTESIS       las interpretaciones se consolidan en creencias
        │                      con confianza explícita; las contradicciones
        │                      se deliberan hasta consenso
        ▼
  4. ADAPTAR APRENDIZAJE       el consenso produce una decisión pedagógica
        │                      concreta, trazada y justificada
        ▼
  5. VALIDAR HIPÓTESIS         la evidencia posterior confirma o refuta
        │                      la decisión: la confianza sube o baja
        └──────────────────────► vuelve a 1
```

**Estado real del ciclo en el código** (auditoría 2026-07-04): las fases 1–4
existen con distintos grados de madurez; la fase 5 **no existe**. El sistema
decide y explica, pero no aprende de sus propias decisiones de forma
observable. Cerrar la fase 5 es la brecha científica prioritaria: es lo que
permite mostrar ante el jurado *"el sistema creyó X con confianza 0.6, adaptó,
y la evidencia posterior subió/bajó esa confianza"*. El detalle técnico por
fase está en el **Anexo B**.

---

## 4. La hipótesis pedagógica

Una hipótesis es una **creencia revisable** sobre cómo aprende un estudiante:
*"aprende mejor con diagramas"*, *"su carga cognitiva sube en recursividad"*.

Reglas de vida de una hipótesis:

- **Nace débil.** Una primera señal (p. ej. el diagnóstico inicial) crea la
  hipótesis con confianza baja. El diagnóstico es un *punto de partida*, nunca
  una etiqueta permanente.
- **Se fortalece o debilita solo con evidencia.** Nunca por diseño, nunca por
  preferencia declarada, nunca por conveniencia de implementación.
- **Puede morir.** Una hipótesis contradicha por evidencia sostenida se
  descarta, y ese descarte también queda registrado — refutar es un resultado
  científico válido.
- **Decae con el tiempo.** La evidencia antigua pierde peso; lo que el
  estudiante era hace un mes no gobierna lo que es hoy.

---

## 5. Los agentes: una comunidad que observa, delibera y decide

Cada agente se define por **qué evidencia consume y qué evidencia emite**.
Si un agente no puede expresarse en esos términos, no pertenece al enjambre.

| Agente | Consume (evidencia) | Emite (evidencia/decisión) |
|---|---|---|
| Pedagógico | Desempeño y etapa cognitiva | Perfil de nivel y dominio de conceptos |
| Adaptativo | Trayectoria, ritmo, perfil | Ajustes de dificultad, profundidad, pace |
| Planificador multimodal | Hipótesis de modalidad | Qué modalidad usar en el siguiente contenido |
| Generador de engagement | Patrón de engagement | Recursos de enganche adaptados |
| Consistencia | Historia narrativa/visual del estudiante | Vetos de redundancia, continuidad |
| Riesgo | Señales de riesgo acumuladas | Alertas tempranas |
| Evaluación | Progreso demostrado | Evaluaciones calibradas |
| Investigación | Necesidad de contenido fundamentado | Evidencia documental |
| Mediador de consenso | Votos y contradicciones de los demás | Consenso y resolución de conflictos |

(Los nombres de clase reales y el inventario completo están en el Anexo B.
El estudiante nunca ve esta tabla; el jurado la ve en acción en el Modo
Evidencia.)

---

## 6. Fronteras de visibilidad

### El estudiante NUNCA ve
- Cursos, códigos, matrícula, ciclos, mallas, créditos — infraestructura interna.
- El mecanismo: agentes, votos, confidencias numéricas, memoria compartida.
- Etiquetas de expediente sobre sí mismo ("perfil: visual, nivel: básico").

### El estudiante SÍ ve
- Su experiencia de aprendizaje como recorrido personal.
- Su **evolución**: qué puede hacer hoy que antes no podía (delta, no porcentaje).
- Las adaptaciones **narradas**, no etiquetadas: *"notamos que los diagramas te
  funcionan mejor; este tema empieza con uno"*.

### El docente ve
- Evidencia agregada de sus estudiantes: evolución, riesgo, concepciones
  erróneas frecuentes (sus 4 preguntas validadas).

### El Modo Evidencia (jurado) ve TODO
- La cadena completa: evidencia → hipótesis → deliberación → decisión →
  validación. Es la única superficie donde el mecanismo es visible por diseño.

---

## 7. Cómo se demuestra la tesis en la sustentación

La demostración de la adaptación multimodal es una consulta sobre el ciclo:

1. **Capturar** — el diagnóstico fija una hipótesis inicial de modalidad con
   confianza baja.
2. **Interpretar** — la evidencia de observación e interacción converge con
   esa hipótesis o la contradice.
3. **Construir** — la deliberación entre agentes actualiza la hipótesis.
4. **Adaptar** — el contenido servido cambia, y la decisión queda trazada.
5. **Validar** — el desempeño posterior confirma o refuta la adaptación.

El Modo Evidencia (Replay, Decision Trace) reproduce esa cadena sobre datos
reales de la demo. Hoy el sistema cubre 1–4 (parcialmente) y no cubre 5;
además el lazo entre la hipótesis conductual de modalidad y el contenido
servido está cortado (Anexo B, brechas).

---

## 8. Principios arquitectónicos no negociables

Cuando dos implementaciones compitan, gana la que respete estos principios:

1. **Toda decisión debe originarse en evidencia.**
2. **Toda adaptación debe poder justificarse** — mostrar la evidencia que la causó.
3. **Ninguna hipótesis es permanente** — toda creencia es revisable y puede morir.
4. **La evidencia pesa más que las preferencias declaradas.**
5. **Los agentes nunca sustituyen al estudiante; lo acompañan.**
6. **La adaptación es un proceso continuo, no un evento.**
7. **Toda iteración debe mejorar simultáneamente dos dimensiones:**
   la capacidad del sistema para comprender al estudiante (valor científico)
   y la motivación del estudiante para seguir aprendiendo (valor de producto).
   No se puede adaptar sobre evidencia que no existe — y no sirve capturar
   evidencia si el estudiante no tiene ganas de seguir interactuando con la
   plataforma. Las dos cosas crecen juntas.

Corolarios operativos (derivan de los principios, gobiernan el día a día):

- **Triple especificación:** todo sprint declara un **objetivo científico**
  (qué hipótesis o evidencia se valida), un **objetivo de experiencia**
  (qué cambio concreto percibirá el estudiante al terminarlo) y la
  **evidencia esperada** (qué datos exactos se registrarán — la captura se
  diseña antes que la pantalla). Un sprint sin las tres caras no entra al
  backlog. Además declara **la frase del estudiante**: la oración que un
  estudiante real debería poder decir al terminar el sprint.
- **Puerta de cierre:** ningún sprint se cierra sin responder tres preguntas:
  ¿qué evidencia nueva produce?, ¿qué aprende el sistema?, y *¿qué hace que
  el estudiante quiera volver mañana?* La retención no es marketing — una
  plataforma educativa vive o muere por ella, y sin retención no hay
  evidencia longitudinal que sostenga la tesis.
- Los nombres de los sprints describen **el cambio que producen**, no el
  sistema ("El contenido empieza a adaptarse", no "La hipótesis gobierna
  el contenido").
- **Toda nueva funcionalidad debe ser visible para el estudiante o para el
  investigador. Si nadie puede percibirla, no aporta valor al sprint.**

---

> **CONGELAMIENTO (2026-07-04).** La arquitectura conceptual queda congelada.
> Desde este momento no se crean nuevos documentos de arquitectura ni nuevos
> principios: el trabajo pasa a ser **implementación incremental**. Cada
> sprint debe producir una mejora visible para el estudiante, validada en
> navegador, perceptible en menos de cinco minutos de uso. Si durante la
> implementación aparece una mejor idea arquitectónica, se registra como
> propuesta (Anexo D o backlog), pero **no cambia el rumbo del sprint sin
> aprobación explícita**. Este párrafo y el Anexo D (documento vivo) son las
> únicas partes editables de este documento.

- **Evidencia primero:** toda funcionalidad nueva debe declarar qué evidencia
  produce, interpreta o justifica; si no puede, se rechaza. (Extiende la
  puerta de 5 preguntas de CLAUDE.md, no la reemplaza.)
- **Una autoridad por concepto:** evidencia → memoria compartida;
  escenario → servicio de experiencia. Toda segunda vía es deuda a
  neutralizar, nunca a imitar.
- **El estudiante ve narración; el jurado ve mecanismo.** Ninguna superficie
  intermedia.
- **Delta sobre estado:** toda métrica visible se expresa como evolución
  temporal salvo justificación explícita.
- **Neutralizar antes de borrar** (metodología vigente del giro de producto).

---
---

# ANEXOS TÉCNICOS

*Los anexos anclan el modelo al código real (auditoría del 2026-07-04). Son
para desarrollo, no para la narrativa de la tesis.*

## Anexo A — Mapeo de las fuentes de evidencia al código

| Fuente | Estructuras que HOY la capturan | Estado |
|---|---|---|
| Observación | `pedagogical:engagement`, `pedagogical:pacing`, `pedagogical:cognitive_load` (SharedMemory); `LearningSession` | ✅ existe |
| Interacción | Sesiones de tutor, eventos de recursos, CodeLab | ✅ parcial |
| Evaluación | `DiagnosticResult`, `EvaluationAttempt` | ✅ existe |
| Preferencias emergentes | `pedagogical:modality_preference`, `pedagogical:learning_style`, `pedagogical:analogy_domain` (inferidas del historial, `inferred_from: "history"`) | ✅ existe, desconectada del contenido |

**Conclusión estructural:** `SharedMemoryRecord` ya implementa las cuatro
propiedades de la evidencia (`voter_name`, `created_at` + `ttl_seconds`,
`confidence`, `source_trace_id`). **No se crea una entidad nueva** — sería
repetir el error del LMS. Se eleva conceptualmente la memoria compartida como
fuente de evidencia; el cómo (vista, servicio de lectura, o solo lenguaje) es
la pregunta abierta n.º 1.

Tipos de memoria en uso (conteo real de escrituras en código):
`pedagogical_profile` (28), `inference` (23), `observation` (7), `signal` (3),
`pedagogical_decision` (3), `narrative_continuity` (3), `research` (2),
`pattern` (1), `deliberation_vote` (1), `deliberation_result` (1).

## Anexo B — Estado del ciclo y de la arquitectura por fase

| Fase del ciclo | Soporte actual | Brecha |
|---|---|---|
| 1. Capturar | `SharedMemoryStore.publish_observation` (dedup, TTL, savepoints, tracing) | Dedup en camino async pendiente (TODO declarado en `shared_memory.py:92`) |
| 2. Interpretar | `PedagogicalMemory.build_student_profile`, `ConsistencyAgent` | — |
| 3. Construir hipótesis | `ConsensusMediator`, `deliberation_vote/result`, confidence | — |
| 4. Adaptar | `pedagogical_decision`, `AgentDecisionTrace`, `explanation_service` | **El contenido del estudiante se ordena por la etiqueta estática del diagnóstico** (`students.py:352-357`), no por la hipótesis conductual |
| 5. Validar | **No existe** | Brecha científica prioritaria |

Relectura de piezas existentes (nada se tira; cambia su rol):

| Pieza | Rol bajo v2 | Estatus |
|---|---|---|
| `SharedMemoryStore` + `PedagogicalMemory` | Repositorio de evidencia (corazón del producto) | Ascendida |
| `learning_experience_service` | Autoridad del *escenario* — **en transición, no consolidada** hasta que un E2E pruebe que todos los recorridos pasan por ella | Confirmada con alcance acotado |
| `DiagnosticResult.dominant_modality` | Hipótesis inicial (prior), no etiqueta permanente | Degradada |
| Course / LearningPath / Enrollment / PathModule | Infraestructura de contenido, invisible | Interna |
| Ciclo, curriculum, prerequisitos, `current_cycle` | Sin rol en el modelo | Legado a neutralizar |
| Swarm demo (SQLite, seed determinista) | Herramienta de sustentación, separada de la evidencia real | Demo por diseño |
| Agentes reales (22 en `app/agents/`) | La comunidad del §5; clases: `PedagogicalAgent`, `AdaptiveAgent`, `AdaptiveLearningAgent`, `AdaptiveLearningEvaluationAgent`, `MultimodalPlanningAgent`, `EngagementGeneratorAgent`, `ConsistencyAgent`, `RiskAgent`, `EvaluationAgent`, `ResearchAgent`, `PromptEngineeringAgent`, `StructuralPedagogicalAgent`, `ConsensusMediator`, y auxiliares | Confirmados |

## Anexo C — Call sites legados de `activate_student` (análisis, sin tocar código)

| Call site | Propósito | Diagnóstico | Destino propuesto |
|---|---|---|---|
| `user_service.py:76` (crear usuario con ciclo) | Aprovisionar estudiante creado por admin | Vigente, condicionado a `current_cycle` | Converger a `start_experience`, sin condición de ciclo |
| `user_service.py:104` (cambio de ciclo) | Re-aprovisionar al cambiar ciclo | El disparador no existe en v2 | Desaparece con el campo ciclo del admin |
| `user_service.py:128` (rol → estudiante) | Aprovisionar al convertir en estudiante | Vigente | Converger |
| `user_service.py:198` (import CSV) | Alta masiva | Vigente para demo/seed | Converger |
| `student_service.py:799` (`auto_enroll_from_curriculum`) | Auto-matrícula por malla | **CÓDIGO MUERTO — cero llamadores (grep, 2026-07-04)** | Eliminar en limpieza |

`activate_student()` no se elimina hasta que los cuatro sitios vigentes
converjan y un E2E lo confirme.

## Anexo D — Decisiones arquitectónicas abiertas (documento vivo)

> **Estas decisiones NO están cerradas y no deben cerrarse todavía.**
> Son hipótesis arquitectónicas que se validarán durante el desarrollo, a
> medida que la experiencia real del estudiante genere evidencia funcional.
> Afectan meses de trabajo: decidirlas antes de construir el modelo basado en
> evidencia sería decidir la estructura definitiva de una casa antes de vivir
> una semana en ella. Ninguna se convierte en backlog automáticamente.
>
> Cada sprint que produzca evidencia relevante para una de estas preguntas lo
> registra aquí; la decisión se cierra cuando la evidencia sea suficiente.

| # | Decisión abierta | Qué evidencia funcional la responderá |
|---|---|---|
| D1 | ¿La elevación de la memoria compartida a "Evidencia de Aprendizaje" se materializa como servicio de lectura (`LearningEvidenceService`), como vista, o solo como lenguaje del dominio? | Cuántos consumidores distintos necesitan leer evidencia y con qué patrones, tras 1–2 sprints de instrumentación real |
| D2 | ¿Qué entra antes: la **fase 5 (Validar)** del ciclo o la consolidación de la autoridad única del escenario (call sites)? | Dónde aparece primero la fricción real: en la demostrabilidad científica o en inconsistencias de aprovisionamiento durante los recorridos |
| D3 | ¿El campo `current_cycle` del admin se retira en la próxima neutralización o se conserva oculto hasta el final? | Si algún recorrido real (alta admin, CSV) sigue dependiendo de él una vez que el aprovisionamiento converja |
| D4 | ¿El recorte del CRUD de cursos docente sigue diferido bajo v2? | La validación del recorrido docente contra sus 4 preguntas bajo el modelo de evidencia |

Registro de evidencia acumulada por decisión: *(vacío — se llena por sprint)*.

---

*v2.1 — consolidación conceptual del 2026-07-04, tras revisión del arquitecto
de producto sobre la v2.0 (misma fecha). Aprobado como modelo conceptual el
2026-07-04; Anexo D permanece abierto como documento vivo.*
