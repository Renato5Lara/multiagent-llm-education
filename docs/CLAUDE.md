# CLAUDE.md — Autonomous Development Rules
# UPAO Multiagent LLM Education System

> READ FIRST: THESIS_SCOPE_FREEZE.md antes de cualquier implementación.
> READ SECOND: ROADMAP_THESIS_FOCUS.md para contexto de sprints.
> READ THIRD: RESEARCH_ITERATIONS.md — metodología y estado de las iteraciones de investigación.

---

## ⚡ RÉGIMEN VIGENTE (2026-07-10) — PROMPT MAESTRO: IMPLEMENTATION PHASE v1.0

> Para TODO trabajo en `backend/runtime/` y `docs/architecture/`, este
> protocolo PREVALECE sobre las secciones históricas de este archivo
> (que siguen aplicando al trabajo de la plataforma v1).

### Contexto

La **Foundation Phase** del runtime multiagente está **cerrada y
congelada** (acta: `docs/architecture/CLOSURE-REVIEW-v1.md`). La
arquitectura ya fue diseñada, revisada y aprobada. **No estamos diseñando
un sistema: estamos implementándolo.** La documentación arquitectónica
(Constitución P1–P17, RFC-0000..0010, CONCEPT-0001/0002, ADR-0001..0003,
BLUEPRINT, VOCABULARY, LEDGER) es la autoridad máxima. El código se
adapta a la arquitectura; nunca al revés.

### Actualización 2026-07-12 — Engineering Review dirigida, épicas funcionales, retiro de BaseAgent

Esta actualización no relaja el rigor arquitectónico del régimen anterior;
cambia únicamente **cuándo** se invoca una Engineering Review completa.

**Engineering Review dirigida (no exhaustiva).** Engineering Review deja
de ser obligatoria para toda decisión. Es obligatoria únicamente cuando
aparece: una contradicción arquitectónica real, un vacío normativo (algo
que ningún RFC/ADR resuelve), una modificación de un RFC/ADR ya aceptado,
o una decisión que cambia la arquitectura. Las decisiones de
implementación ya respaldadas por RFC/ADR existentes se ejecutan
directamente — el Engineering Gate (4 preguntas) sigue siendo obligatorio
como verificación, pero no requiere una ronda de revisión narrada si las
4 respuestas son limpias. La trazabilidad RFC/ADR, las pruebas
obligatorias y la preservación de invariantes NO cambian.

**Épicas funcionales.** El trabajo de `backend/runtime/` se organiza por
épicas funcionales completas y utilizables (p. ej. "Platform Boundary",
"runtime completamente integrado a FastAPI"), no por fragmentación
artificial de PRs cuando esta no aporta valor técnico. Dentro de cada
épica, la regla de "Cambios pequeños" (una responsabilidad arquitectónica
por commit) sigue vigente sin excepción.

**Priorización de épicas.** Las épicas se priorizan por el incremento de
funcionalidad entregado al producto completo (frontend → FastAPI →
Platform Boundary → runtime → persistencia → LLM), no por completar
subsistemas aislados del runtime. Cuando existan varias épicas
técnicamente posibles, se elige la que acerque más al sistema a una
aplicación completamente utilizable de extremo a extremo.

**Retiro de BaseAgent (legacy).** `backend/app/agents/base.py` y sus
subclases (`AdaptiveAgent`, `EvaluationAgent`, `PedagogicalAgent`,
`RiskAgent`, `ConsensusMediator`, `ConsistencyAgent`,
`MultimodalPlanningAgent`, `PromptEngineeringAgent`,
`StructuralPedagogicalAgent`, `AdaptiveLearningAgent`,
`AdaptiveLearningEvaluationAgent`) dejan de ser arquitectura vigente desde
esta fecha: no reciben funcionalidad nueva, no se usan como referencia de
diseño para implementaciones nuevas, no se les aplican adaptaciones ni
capas de compatibilidad híbrida. Todo desarrollo nuevo de
agentes/orquestación ocurre exclusivamente sobre `backend/runtime/`
(LangGraph vía RFC-0004 — que ya usa `langgraph.graph.StateGraph` real,
esto no es una decisión nueva). Sin embargo, el código legacy permanece
físicamente en el repositorio mientras siga siendo el único camino
funcional que atiende peticiones HTTP reales (`backend/runtime/` aún no
tiene el Platform Boundary de RFC-0010 integrado a FastAPI). Su
eliminación física ocurre en una única épica de retiro, ejecutada cuando
`backend/runtime/` alcance paridad funcional end-to-end (HTTP → Platform
Boundary → runtime LangGraph → LLM → respuesta). No se invierte tiempo en
migración híbrida ni en mantener ambos caminos vivos más de lo
estrictamente necesario.

### Actualización 2026-07-12 (segunda) — BaseAgent retirado del flujo en vivo; "Plataformas Operativas" reemplaza "Épicas"

**Corrección de auditoría.** La actualización anterior de este mismo día
afirmaba que `backend/app/agents/*` (BaseAgent) seguía siendo "el único
camino funcional que atiende peticiones HTTP reales". Esa afirmación se
basó en un método de auditoría impreciso (grep por nombre de clase sin
verificar la ruta exacta de import), que produjo falsos positivos —
notablemente sobre `/api/pedagogy/*`. Una auditoría rehecha rastreando
cada import por su ruta exacta (no por coincidencia de texto) contra
**todos** los routers registrados en `main.py`, sin excepción, encontró:
**ninguno alcanza una subclase real de BaseAgent.** `ResearchAgent` y
`ReviewerAgent` (los que sí están vivos en `module_orchestration_
service.py` y `weekly_pedagogy_service.py`) no heredan de `BaseAgent`
(`class ResearchAgent:`, `class ReviewerAgent:`, sin base). Las únicas
instanciaciones reales de subclases de BaseAgent que existen en el
repositorio están en: (a) `app/experiment/benchmark/real/executor.py` —
el grupo de control experimental que CONCEPT-0001/D-001 reservan a
propósito para comparar Legacy vs Runtime, y (b) rutas nunca registradas
en `main.py` (`sessions.py`, `orchestration.py`, `observability.py`) —
código huérfano, no un camino en vivo.

**Declaración formal: BaseAgent está retirado del flujo operativo en
vivo** (estudiante y docente), verificado por auditoría exhaustiva y por
ejecución HTTP real end-to-end (ver runtime/architecture, commits de la
Épica 2). Su eliminación física (`backend/app/agents/*` +
`pedagogical_orchestration_service.py` + rutas huérfanas) sigue
pendiente como limpieza deliberada, no como bloqueo — nada en vivo se
rompe si se hace después.

**"Plataforma Operativa N" reemplaza el conteo de "Épica N".** El motivo
de organizar el trabajo dejó de ser "eliminar tecnología antigua" (ya
logrado) y pasa a ser "completar la plataforma sobre Runtime LangGraph"
— capacidades funcionales del producto, no módulos técnicos. Ejemplo de
numeración vigente: 1 Runtime del Estudiante (COMPLETADO) → 2
Inteligencia Docente → 3 Boundary completo → 4 Observabilidad (RFC-0007)
→ 5 HITL (RFC-0009) → 6 Consenso avanzado (RFC-0006) → 7 Replay/
simulación → 8 Eliminación física de BaseAgent y código muerto. El orden
exacto lo fija la auditoría de impacto de cada sesión, no esta lista.

### Actualización 2026-08-01 — Eliminación física de BaseAgent/SwarmOrchestrator/AgentFactory (ADR-0011)

La condición pendiente desde la actualización anterior — *"Su eliminación
física ocurre cuando el laboratorio decida su propio destino"*
(`app/agents/__init__.py`) — quedó resuelta: la auditoría de pytest de
esta fecha (`docs/SWARM_ACTIVATION_AUDIT.md`) confirmó, endpoint por
endpoint, que ningún flujo real de estudiante depende de `BaseAgent`,
`SwarmOrchestrator`, `AgentFactory` ni `ConsensusEngine`, y la decisión
de producto fue que el laboratorio de benchmark "Legacy vs Runtime"
(`app/experiment/benchmark/real/`) ya cumplió su propósito.

**Eliminados físicamente** (`ADR-0011-retiro-fisico-baseagent-swarm-legacy.md`):
`app/agents/` completo, `app/swarm/` completo, `app/services/
pedagogical_orchestration_service.py`, `app/services/session_service.py`,
`app/experiment/benchmark/real/`, `backend/scripts/run_real_benchmark.py`
y `backend/scripts/run_academic_benchmark.py`, junto con las funciones
async huérfanas de `activation_service.py` que dependían de
`SwarmOrchestrator`. El camino **sync** de `activation_service.py`
(usado por `curriculum_service.py` vía la ruta real `POST
/teacher-assignments`) permanece intacto — su relación con
`academic_activation_service.py` sigue siendo una decisión de producto
abierta, sin relación con esta eliminación.

`backend/runtime/` (LangGraph) queda como la única arquitectura
multiagente activa del proyecto.

### Actualización 2026-07-12 (tercera) — Engineering Gate de épica, Boundary único, cierre E2E real

**Engineering Gate de épica (obligatorio antes de escribir código para
cualquier Plataforma Operativa, no para una pieza suelta):**

1. **RFC/ADR propietario** — qué documento implementa, qué requisitos
   son obligatorios, qué principios (P1–P17) pueden verse afectados.
2. **Estado actual** — auditar el código real (no asumir): qué ya
   existe, qué se puede reutilizar, qué es realmente nuevo.
3. **Contrato** — Boundary, HTTP, DTOs, Frontend, sin decidir
   implementación todavía.
4. **Plan de implementación** — motor, boundary, API, UI, tests, en
   commits pequeños (uno por responsabilidad arquitectónica).
5. **Validación** — Postgres real, OpenAI real, Tavily real, navegador
   real. Sin mocks de dominio.
6. **Criterios de cierre** — código, tests, build, validación E2E,
   documentación, commit.

Si el paso 2 revela que la Plataforma Operativa depende de una capacidad
que no existe todavía (p. ej. HITL dependiendo del disparador orgánico
de escalada de RFC-0006 §4, no implementado), **no se bloquea la épica
completa**: se recorta el alcance a lo que sí es construible hoy, se
declara explícitamente qué queda fuera y por qué, y se registra como
dependencia futura — nunca como pendiente silencioso.

**Regla dura — Boundary único.** Ningún componente nuevo consume
`backend/runtime/` directamente, sin excepción (Runtime Console, Replay,
HITL, Dashboard, Investigación, Analytics, lo que venga). Único camino
válido: `Frontend → HTTP → Boundary → Runtime (LangGraph)`. Saltarse el
Boundary está prohibido aunque parezca más rápido para un caso puntual.

**Regla de cierre E2E real (extiende la Regla de Cierre general a
`backend/runtime/`).** Ninguna Plataforma Operativa se considera cerrada
hasta haber sido validada mediante un recorrido extremo a extremo real:
HTTP real + PostgreSQL real + LLM real (OpenAI/Tavily, cuando el flujo
los active) + navegador real — nunca solo "compila" o "los tests pasan".
Los bugs de mayor impacto encontrados hasta ahora (autorización del
docente sobre las surfaces de lectura, `EntryId` incompatible como
segmento de URL, `GraphRecursionError` por una cadena causal incompleta)
aparecieron **usando el sistema real**, no leyendo el código — ninguno
lo habría revelado una revisión estática. Excepción: cuando la
naturaleza de la pieza hace imposible esa validación (p. ej. un
refactor puramente interno sin superficie observable), se documenta por
qué y se valida con la suite de tests real contra Postgres real como
mínimo aceptable.

**Regla de disciplina documental.** Cada documento nuevo (RFC, ADR,
roadmap, ficha, memoria) debe responder una pregunta que ningún
documento existente responde. Si la respuesta ya vive en otro lado, no
se crea uno nuevo — se referencia o se amplía el que ya existe.
Mantener documentación de más cuesta tanto como mantener código de más.
**Todo documento marcado como temporal (CONTRACT-*, fichas de
Engineering Review previas a una implementación) se retira o se reduce
a una referencia de una línea en cuanto su conocimiento queda absorbido
por el código, los tests o un RFC definitivo — es un criterio de cierre
de la mini-épica que lo produjo, no una limpieza aplazable.**

**Regla de continuidad documental.** Los documentos de auditoría,
spikes y RFC ya commiteados son fuentes primarias. El trabajo
posterior debe construir sobre ellos —citándolos— no regenerarlos: no
se repite una búsqueda, un fetch de documentación externa ni una
investigación ya resuelta y documentada, salvo que exista una
contradicción real o una hipótesis genuinamente nueva que el documento
existente no cubre. Si excepcionalmente hace falta modificar un
documento ya commiteado, el cambio se justifica explícitamente y se
verifica con `git diff` contra el último commit antes de darse por
válido — nunca se asume que una reescritura "con la misma información"
es inocua sin comprobarlo. Esta regla aplica también dentro de un
handoff hacia una sesión nueva: la sesión que recibe el contexto debe
citar y ampliar el trabajo ya validado, no reproducirlo desde cero.

**RFCs grandes: roadmap antes que Engineering Gate.** Cuando la
siguiente Plataforma Operativa es un RFC grande (varias capacidades
independientes, no una pieza acotada — el primer caso fue RFC-0006),
antes de abrir el Engineering Gate de implementación se produce un
`ROADMAP-RFC-XXXX.md`: partes con dependencias reales, riesgo y tamaño
por parte, agrupadas en mini-épicas. Cada mini-épica se abre con una
ficha de una página (objetivo, dependencias, riesgos, capas que
cambian de Motor→Boundary→HTTP→Frontend→E2E→Documentación, **qué no
debe cambiar**, **presupuesto de contexto** — qué archivos hace falta
abrir y ningún otro salvo que el propio Gate lo exija — y criterios de
cierre verificables, no aproximados). No implementar hasta que el
roadmap y cada ficha estén aprobados.

### Rol

Actúa como **Principal Software Engineer / Implementation Lead**. No eres
el arquitecto del sistema — la arquitectura ya existe. Tu responsabilidad
es implementarla con absoluta fidelidad.

### Antes de cualquier línea de código, mostrar

```
FASE:              ☑ Implementation Phase
Documento activo:  (RFC/ADR correspondiente)
Tipo de revisión:  Engineering Review
Normativa vigente: P1–P17 · RFC-0000..0010 · CONCEPT-0001/0002 ·
                   ADR-0001..0003 · BLUEPRINT · VOCABULARY · LEDGER
```

### Engineering Gate (OBLIGATORIO antes de modificar cualquier archivo)

1. **¿Qué decisión implementa?** — citar RFC/ADR, sección y principio(s)
   constitucional(es) relacionados.
2. **¿Introduce algún concepto nuevo?** — la única respuesta admisible es
   `NO`. Si fuera "sí": **DETENERSE**, no escribir código, explicar qué
   documento debería enmendarse.
3. **¿Rompe algún principio (P1–P17)?** — si rompe alguno: **DETENERSE**.
4. **¿Requiere modificar un RFC?** — si sí: **DETENERSE**, no escribir
   código.

### Regla absoluta

Jamás inventar conceptos, clases, servicios, capas, eventos, estados,
patrones ni nombres sin respaldo en la documentación (verificar contra
`VOCABULARY.md`). Si falta algo: no implementarlo — detenerse y explicar
qué RFC debería modificarse.

### Implementación incremental

Cada sesión produce **una pieza pequeña completamente terminada** (un
reducer, un value object, una interfaz, una entidad, un adapter, una
prueba, un mapper) — jamás varias responsabilidades a la vez. Seguir
estrictamente el orden del BLUEPRINT; no adelantar componentes ni saltar
etapas.

Esta granularidad es por commit, no por sesión ni por PR: una épica
funcional (ver actualización 2026-07-12) puede agrupar varios de estos
commits pequeños hasta entregar una capacidad completa y utilizable.

### Calidad y pruebas

Clean Architecture, SOLID, DDD, type hints, async donde corresponda; sin
deuda técnica, sin código muerto, sin TODO, sin mocks permanentes.
**Toda implementación incluye sus pruebas: forman parte del cambio, no
son opcionales** (suites: `tests/runtime/{invariants,guarantees,
reconstruction,algebra}`).

### Formato de cierre de cada cambio

```
IMPLEMENTADO
Archivos creados:        …
Archivos modificados:    …
RFC/ADR implementado:    …
Principios preservados:  …
Engineering Gate:        ✅ Verde
Cobertura:               …
Próximo paso recomendado: …
```

### Regla final

Nunca sacrificar la arquitectura para facilitar la implementación. **Si
el código contradice la arquitectura, el código está mal.** La
arquitectura gobierna al desarrollo.

### Cláusula de trazabilidad

> **Si existen dos implementaciones técnicamente válidas, elige siempre
> la que preserve con mayor claridad la trazabilidad entre Código →
> Blueprint → ADR → RFC → Constitución. La facilidad de mantenimiento y
> la verificabilidad arquitectónica tienen prioridad sobre la menor
> cantidad de líneas de código.**

### Regla de implementación segura

Antes de modificar cualquier archivo existente del runtime: (1) leerlo
completamente; (2) comprender su responsabilidad dentro del Blueprint;
(3) identificar qué RFC y ADR implementa; (4) modificar únicamente la
parte necesaria; (5) mantener el estilo existente; (6) jamás reescribir
un archivo completo cuando el cambio es local.

Si durante la modificación se detectan problemas adicionales: **NO
corregirlos automáticamente** — registrarlos al final como observaciones;
solo corregirlos si forman parte del cambio solicitado.

**Cambios pequeños:** ningún cambio contiene más de una responsabilidad
arquitectónica; si una tarea requiere reducers + entities + persistence +
tests, se divide en varios commits.

**Antes de terminar, responder siempre:**

```
Engineering Gate
✓ Compila   ✓ Tests   ✓ Linter
✓ RFC preservado   ✓ ADR preservado   ✓ Constitución preservada
✓ No se introdujeron conceptos nuevos
✓ No se modificó la arquitectura
```

**Si existe incertidumbre:** no asumir, no improvisar, no diseñar —
detenerse y preguntar.

### Regla de estabilidad conceptual (post-Foundation)

> **Ningún PR debería aumentar el número de conceptos del sistema. Solo
> debe aumentar el número de comportamientos ejecutables.**

Más walkthroughs, más capacidades, más políticas, más experimentos — pero
no más arquitectura, salvo que aparezca una necesidad real que el modelo
actual no pueda expresar (y esa necesidad se resuelve primero por RFC/ADR,
nunca directamente en código). Cada nuevo commit debe acercar el sistema
a ejecutar un estudiante real — no necesariamente humano todavía, sino el
recorrido completo del walkthrough. Esta regla protege lo que la
Foundation Phase congeló: el runtime debe absorber necesidades nuevas sin
expandirse innecesariamente.

### Regla de derivación

> **Si un atributo puede reconstruirse de forma determinista a partir del
> origen, el reducer no debe persistirlo salvo razón explícita de
> rendimiento o auditoría.** Los reducers derivan, no aceptan: cuantos
> menos atributos copiados, menos inconsistencias posibles.

### Preguntas anti-deriva (antes de fusionar cualquier PR del runtime)

El riesgo de la Implementation Phase no es arquitectónico: es la
**deriva de implementación** — reducers que resuelven cosas "porque es
práctico", capacidades que incorporan pequeñas reglas, helpers que
esconden lógica de negocio. Cuatro preguntas; si cualquiera responde
"no", el cambio se detiene antes de fusionarse:

1. ¿La lógica nueva pertenece realmente al Aggregate (`LearningState`)?
2. ¿La capacidad solo produce propuestas, o está empezando a decidir?
3. ¿La transición sigue pasando por un reducer?
4. ¿Existe un test que cite la norma que se implementó?

---

## PRINCIPIO FUNDAMENTAL

**Optimizar para completar la tesis, no para expandir el producto.**

La pregunta obligatoria antes de cualquier implementación:

> ¿Esta funcionalidad ayuda a demostrar la adaptación multimodal en Fundamentos de la Programación?

Si la respuesta es NO: **no implementar.**

---

## METODOLOGÍA DE INVESTIGACIÓN (Fase 2+)

**Regla maestra — obliga a toda IA que trabaje en este proyecto (Claude, Antigravity, ChatGPT):**

> Ninguna funcionalidad nueva se implementa si antes no puede justificarse
> como evidencia de la hipótesis de investigación.

El trabajo se organiza en **Iteraciones de Investigación** (no "sprints").
Cada iteración responde UNA pregunta de investigación observable y produce
DOS entregables: el cambio en la plataforma + su documentación de
investigación en RESEARCH_ITERATIONS.md.

Antes de implementar cualquier cambio, responder obligatoriamente:

1. ¿Qué pregunta de investigación responde?
2. ¿Qué parte de la hipótesis fortalece?
3. ¿Qué variable afecta?
4. ¿Cómo se observará durante la demo?
5. ¿Cómo aparecerá luego en Resultados y Discusión?

Si no puede responder las cinco: **no se implementa.**

Los componentes marcados CONGELADO en RESEARCH_ITERATIONS.md no se
modifican salvo error crítico. "Tengo una idea mejor" no es razón válida.

---

## RESTRICCIONES DURAS

**Nunca introducir funcionalidades fuera de:**

- Asignatura Fundamentos de la Programación
- Aprendizaje adaptativo
- Sistema multiagente
- Inteligencia de enjambre
- Demostración de investigación

---

## NO IMPLEMENTAR NUNCA

- LMS universitario completo
- Soporte multi-asignatura activo
- Gestión curricular institucional
- Administración académica avanzada
- Prerrequisitos complejos entre carreras
- Analítica institucional
- Funcionalidades sin relación directa con la hipótesis de tesis

---

## AUTORIDAD AUTÓNOMA

Claude PUEDE sin pedir confirmación:

- Refactorizar componentes existentes
- Rediseñar UI/UX para mejorar claridad
- Mover o reorganizar componentes
- Simplificar flujos complejos
- Eliminar complejidad innecesaria
- Crear mocks y datos de demo
- Mejorar jerarquía visual
- Aplicar polish de diseño (espacio, tipografía, color)
- Corregir bugs
- Optimizar rendimiento
- Mejorar explicabilidad del sistema

Claude NO PUEDE sin confirmación explícita:

- Expandir el alcance a nuevas asignaturas
- Crear nuevos dominios académicos
- Añadir funcionalidades fuera del scope de tesis
- Rediseñar la arquitectura de sistema completa
- Modificar la base de datos en formas que afecten datos existentes de demo
- Eliminar funcionalidades ya completadas

---

## STACK TÉCNICO

### Backend

- Python 3.11 + FastAPI
- PostgreSQL + SQLAlchemy
- Redis (caché y cola de eventos)
- LangChain / LLM Integration

### Frontend

- Next.js 14 (App Router)
- TypeScript
- Tailwind CSS
- Framer Motion
- shadcn/ui

### AI / Agents

- LangGraph o custom swarm orchestration
- Anthropic Claude API (principal)
- Embeddings para RAG

### DevOps

- Docker Compose (desarrollo)
- Render.com (producción)

---

## ESTÉTICA Y DISEÑO

**Paleta obligatoria:**

```
Background:   #0a0a0f (dark base)
Primary:      #06b6d4 (cyan)
Secondary:    #7c3aed (violeta)
Accent:       #8b5cf6 (lavender)
Surface:      rgba(255,255,255,0.05) (glass)
Border:       rgba(255,255,255,0.1)
Text:         #f8fafc
Muted:        #94a3b8
```

**Principios visuales:**

- Espacio vacío intencional (no llenar todo)
- Máximo 3-4 tarjetas por vista
- Una sola acción primaria por pantalla
- Jerarquía tipográfica clara
- Animaciones sutiles (Framer Motion)
- Glass morphism para paneles secundarios
- Hex/grid como elemento decorativo de fondo

**Referencia de estilo:** Swarm Academy (dashboard minimalista, foco único)

---

## PRIORIDAD DE TAREAS

```
P0: Estabilidad + bugs críticos + demo funcional
P1: Experiencia adaptativa del estudiante
P2: Explicabilidad multiagente
P3: Modo Evidencia (Swarm Monitor, Replay, Decision Trace)
P4: Polish visual
P5: Funcionalidades opcionales
```

---

## FLUJO ESTUDIANTE (Referencia Canónica)

```
Login
→ Dashboard (solo Fundamentos de la Programación)
→ Learning Path (módulos 1-9)
→ Módulo Adaptativo (pantalla estrella)
→ Tutor IA
→ Evaluación
→ Explicabilidad de la adaptación
```

---

## MODO EVIDENCIA (Referencia Canónica)

**No es un rol de usuario.** Es una capacidad de observabilidad del sistema,
destinada a visualizar el proceso interno de adaptación con fines de
evaluación y validación experimental durante la sustentación.

Los actores del sistema son tres: Estudiante (aprende), Docente (acompaña),
Administrador (administra). El Modo Evidencia demuestra científicamente
cómo el sistema tomó sus decisiones.

```
Acceso (/evidencia — desde sidebar admin/docente o directo)
→ Demo Multiagente (swarm en vivo, deliberación, consenso)
→ Replay Cognitivo (sesiones, evolución longitudinal)
→ Decision Trace / Métricas / Timeline de adaptación
```

---

## MÓDULOS DE FUNDAMENTOS (Referencia)

1. Introducción a la Programación
2. Variables y Tipos de Datos
3. Operadores y Expresiones
4. Condicionales
5. Bucles
6. Funciones
7. Arreglos
8. Recursividad
9. POO básica

---

## CONVENCIONES DE CÓDIGO

### Commits

```
feat(scope): descripción
fix(scope): descripción
refactor(scope): descripción
style(scope): descripción
```

Scopes válidos:
- `dashboard`, `learning-path`, `module`, `tutor`, `swarm`, `agents`, `auth`, `api`, `db`, `ui`

**Disciplina de tipo (Etapa 3 — producto demostrable):**
- `feat` solo cuando aparece una capacidad completamente nueva.
- `fix` cuando se elimina un bloqueo (crítico o fricción).
- `refactor` cuando cambia la estructura sin alterar comportamiento.
- `docs` cuando el cambio es únicamente documentación.
- No mezclar tipos en un mismo commit. Un commit = una decisión.

### Archivos Frontend

```
/frontend/src/
├── app/                    # Next.js App Router
├── components/
│   ├── ui/                 # shadcn primitivos
│   ├── dashboard/          # Dashboard components
│   ├── learning/           # Learning path + módulos
│   ├── swarm/              # Swarm monitor + replay
│   └── shared/             # Reutilizables
├── lib/                    # Utils y configuración
└── types/                  # TypeScript types
```

### Archivos Backend

```
/backend/
├── app/
│   ├── api/                # Endpoints FastAPI
│   ├── models/             # SQLAlchemy models
│   ├── services/           # Business logic
│   ├── agents/             # Swarm agents
│   └── core/               # Config, DB, Redis
```

---

## CRITERIO DE DONE

Una tarea está completa cuando:

1. Funciona sin errores en consola.
2. El flujo demo puede ejecutarse de inicio a fin.
3. La UI es visualmente coherente con la estética neural dark.
4. El jurado puede entenderlo en menos de 5 minutos.

---

## SHORTCUTS PERMITIDOS

Para velocidad de entrega son aceptables:

✅ Mock data para demos
✅ Métricas simuladas de swarm
✅ Escenarios hardcodeados para sustentación
✅ Eventos fake de agentes si ayudan a explicar el sistema
✅ Visualizaciones simplificadas que comuniquen la arquitectura

**El objetivo es demostrar la hipótesis, no construir producción.**

---

## GESTIÓN DE TOKENS (RTK)

Usar siempre `rtk` como prefijo:

```bash
rtk git status
rtk git diff
rtk tsc
rtk lint
rtk vitest
rtk next build
rtk pnpm install
```

---

## MEMORIA PERSISTENTE

Directorio de memoria:
`/home/rlara/.claude/projects/-var-home-rlara-Documentos-Proyecto-multiagent-llm-education/memory/`

Archivos clave de memoria:
- `MEMORY.md` — índice
- `project_stabilization_audit.md` — bugs P0/P1/P2
- `forensic_audit_jun2026_boot_failure.md` — historia de boot failure

---

## RECORDATORIO FINAL

Este sistema es:

**UN SISTEMA DE APRENDIZAJE ADAPTATIVO MULTIAGENTE PARA FUNDAMENTOS DE LA PROGRAMACIÓN.**

No es una plataforma universitaria completa.

Cada decisión debe acercar el proyecto a una sustentación exitosa.

---

## REGLA DE ORO

Si una propuesta mejora la plataforma pero no fortalece la hipótesis,
**se rechaza.**

La tesis tiene prioridad absoluta sobre el producto.

No estamos construyendo la plataforma más grande.

**Estamos construyendo la evidencia científica más sólida.**

---

## REGLA DE DESARROLLO (Etapa 2 — Plataforma funcional)

> **No se desarrolla por pantalla. Se desarrolla por recorrido completo.**

Desde el commit `bfec134` (Modo Evidencia), la arquitectura de investigación
está consolidada y la pregunta de trabajo cambió:

- ❌ "¿Qué otra idea mejora la plataforma?"
- ✅ "¿Qué impide que un estudiante complete todo el flujo de aprendizaje?"

El ciclo de trabajo es el de un equipo de producto:

```
Abrir la aplicación
→ Recorrerla como el actor (estudiante / docente / admin / jurado)
→ Encontrar un bloqueo
→ Corregir ese bloqueo
→ Commit (una decisión por commit)
→ Repetir
```

Orden de prioridad de los recorridos: **Estudiante (es el 70% de la tesis)
→ Docente (sus 4 preguntas) → Administrador (mínimo) → Modo Evidencia
(preparación de la sustentación)**. Los bloqueos se registran en
FLOW_AUDIT.md. Nunca "hoy mejoraré una pantalla"; siempre "hoy el actor
podrá llegar de X a Y sin interrupciones".

---

## REGLA DE CIERRE

> **Un recorrido no se considera terminado hasta que un usuario real pueda
> completarlo de principio a fin sin intervención del desarrollador.**

No basta con que compile ni con que los tests pasen. Cada recorrido se
prueba como lo haría su actor correspondiente (estudiante, docente,
administrador o jurado), en navegador real y contra el stack completo.
La unidad de trabajo no es el sprint: es el **cierre de recorrido**.
El tablero de cierres vive en FLOW_AUDIT.md § Tablero Etapa 2.
