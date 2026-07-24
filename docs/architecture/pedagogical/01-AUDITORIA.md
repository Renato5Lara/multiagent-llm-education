# AUDITORÍA PEDAGÓGICA Y ARQUITECTÓNICA DEL SISTEMA ACTUAL — UPAO-MAS-EDU

**Documento 1 de la Arquitectura Pedagógica v1.0.** Estado: cerrado, sin enmiendas posteriores.

Metodología: lectura directa del código fuente (runtime LangGraph completo, servicios
backend, componentes frontend) con verificación cruzada de imports y rutas registradas
— cero suposiciones sobre lo que "debería" existir. Cita `archivo:línea` en cada
afirmación relevante.

---

## 1. ESTADO PEDAGÓGICO ACTUAL

El sistema no tiene un solo modelo pedagógico — tiene dos capas que no siempre hablan
entre sí:

**Capa A — el motor de decisión (`backend/runtime/`, LangGraph real):** un ciclo
genuino de Diagnosticar→Remediar/Orientar→Deliberar→Decidir→Adaptar→Validar→Modelar,
con consenso formal entre propuestas rivales y una fórmula de confianza pensada para
reforzarse o decaer con evidencia nueva.

**Capa B — la experiencia del estudiante (frontend + servicios de contenido):** un
recorrido de fases (concepto→práctica→decisión→cierre) con feedback textual rico,
hints escalonados, y una ruta (`LearningPath`) que se calcula una sola vez, en el
onboarding, a partir de un snapshot del pre-test — no del runtime.

La capa A es arquitectónicamente sofisticada; la capa B es pedagógicamente cuidada en
el detalle (hints, veredictos, feedback nombrado); pero la conexión entre ambas es
parcial, no completa — ver §5 y §9.

---

## 2. ESTADO ARQUITECTÓNICO ACTUAL

El runtime real vive en `backend/runtime/` (LangGraph `StateGraph`,
`runtime/engine/graph/walkthrough.py:358-377`), no en `backend/app/agents/`. Confirmado
por auditoría de imports (no por asunción): **`BaseAgent` y sus 11 subclases están
completamente muertos en el camino en vivo**. Los únicos dos lugares donde algo
instancia una subclase real de `BaseAgent` son:

- `backend/app/experiment/benchmark/real/executor.py` — el grupo de control
  experimental (correcto, documentado, intencional).
- Una cadena de funciones huérfanas (`session_service.start_module_session`,
  `activation_service.activate_enrollments_for_course`) con cero llamadores en todo el
  repositorio y sin ruta registrada en `main.py`.

`main.py:320-341` registra 22 routers; ninguno importa `app.agents.*`. El camino real
de activación de matrícula (`curriculum.py`→`curriculum_service.py`→
`activation_service.activate_enrollments_for_course_sync`) solo escribe un diccionario
JSON inerte (`_get_swarm_config_for_course_sync`, `activation_service.py:58`) — nunca
instancia un swarm real.

El motor tiene 7 "productores" (capacidades) realmente cableados al grafo — no 8:
`diagnosticar, remediar, orientar, validar, modelar, tutorizar, adaptar`
(`walkthrough.py:360-368`). `EVALUAR` existe como capacidad conceptual
(`Capacidad.EVALUAR`, `entries.py:35`) y tiene su propio productor
(`domain/evaluar/productor.py`), pero no es un nodo del grafo — sus facts entran desde
afuera, autorados por el Boundary (RFC-0010 "Grieta A"), no por una ejecución interna
del walkthrough.

---

## 3. ESTADO ADAPTATIVO ACTUAL

Hallazgo más importante de la auditoría, puramente factual:

**La maquinaria de confianza reforzable/decayente existe en código, pero está apagada
por configuración de política.** `kernel/deliberation/politica.py:154-163` define la
única política en producción, `"v1"`:

```
peso_refuerzo=0, peso_refutacion=0, peso_decaimiento=0, theta=0, delta=0
```

`kernel/deliberation/confianza.py` implementa 8 axiomas (A1-A8) sobre cómo una
confianza declarada debería crecer con validaciones positivas y decaer con el tiempo
lógico sin refuerzo — pero con estos pesos en cero, `calcular_confianza_efectiva`
siempre devuelve exactamente la confianza declarada por el productor, sin importar
cuánta evidencia se acumule. El propio código lo documenta sin ambigüedad
(`politica.py:10-16`): *"peso_refuerzo=0... la confianza efectiva de v1 es, por
diseño, la declarada, sin refuerzo ni decaimiento"*.

Del mismo modo, `theta=0` y `delta=0` hacen que las rutas de "evidencia insuficiente"
(aplazamiento) y "escalada al docente por empate" sean matemáticamente inalcanzables
bajo v1 — el propio código lo prueba (`politica.py:56-63,66-75`).

**Lo que SÍ es real y continuo:** el ciclo de re-proposición y "cascada" — cuando
llega evidencia nueva, una decisión vigente puede quedar superseded y las capacidades
vuelven a proponer (`walkthrough.py:267-277`). Esto es diagnóstico continuo en el
sentido de "el estado se sigue extendiendo con cada hecho nuevo, y las propuestas se
recalculan" — pero NO en el sentido de "la confianza en un estudiante crece con el
tiempo": ese mecanismo existe en el código y está clínicamente inerte.

**Lo que tampoco es continuo:** la `LearningPath` (secuencia de módulos que ve el
estudiante) se calcula una sola vez, en el onboarding, por
`student_service.generate_learning_path_adaptive` — una función SQL pura sobre
Postgres que lee el pre-test y no llama al runtime en ningún punto. El runtime solo
interviene después, por dos vías desacopladas de la ruta macro: `decision_adaptativa`
(reordena bloques de contenido dentro de un módulo) y `submitCycleEvidence` (puede
insertar un refuerzo dentro del ciclo actual). La estructura de módulos en sí — cuáles
existen, en qué orden — no se reestructura por el runtime durante la sesión.

---

## 4. INVENTARIO DE AGENTES (runtime real — los 7 productores vivos)

| Capacidad | Observa | Decide/Produce | Confianza declarada | Limitación verificada |
|---|---|---|---|---|
| **Diagnosticar** | Cada fact evaluativo nuevo (`competencia` + `items_incorrectos`) | Claim interpretativo `dominada: bool` (regla: ≥2 errores = no dominado) | 0.78 fija | Regla dura; interpreta cada hecho UNA vez, nunca reinterpreta |
| **Remediar** | Interpretaciones `dominada=False` | Propuesta "reforzar" | 0.82 fija | Solo actúa si no tiene ya "palabra en pie" (anti-churn) |
| **Orientar** | Interpretaciones con `dominada` presente | Propuesta "avanzar-con-andamiaje" | 0.75 fija | No conoce a Remediar (aislamiento por diseño) |
| **Deliberar/Decidir** (mecánica del Kernel) | Propuestas/interpretaciones rivales del mismo asunto | Resuelve por mayor confianza | — | Bajo v1, aplazamiento y escalada son inalcanzables |
| **Adaptar** | La decisión vigente + modalidad diagnosticada + señal de Tutorizar | Diseño pedagógico: modalidad + profundidad + alternativas descartadas | 0.80 fija | Frontera dura correcta (categorías, no recursos físicos); solo 2 diseños tabulados |
| **Tutorizar** | Proporción de errores en cualquier fact evaluativo | FACT de señal conductual: fluidez/confusión/frustración | — (fact, no claim) | Nada en el frontend la consume proactivamente |
| **Validar** | El fact evaluativo posterior a una decisión, misma competencia | Veredicto `funciono: bool` | 0.80 fija | Solo dispara si existe evidencia posterior real |
| **Modelar** | Veredictos de Validar | Claim "esta modalidad funcionó para esta competencia" | 0.80 fija | No escribe el modelo persistente dentro de la sesión — solo al cerrarla (RFC-0005) |
| **Evaluar** | — (no es nodo del grafo) | FACT con trazabilidad ítem a ítem | — | Sus datos entran como parámetro externo; en el flujo real, quien evalúa de facto es el Boundary |

Los 11 agentes de `backend/app/agents/` (AdaptiveAgent, EvaluationAgent,
PedagogicalAgent, RiskAgent, ConsensusMediator, ConsistencyAgent,
MultimodalPlanningAgent, PromptEngineeringAgent, StructuralPedagogicalAgent,
AdaptiveLearningAgent, AdaptiveLearningEvaluationAgent) están confirmadamente muertos
en el flujo en vivo. Diseño no descartado, no producto.

Fuera del runtime, con responsabilidad real y en vivo: **ResearchAgent**
(`services/research_agent.py:15`, no hereda `BaseAgent`, busca en Tavily), **ReviewerAgent**
(`services/reviewer_agent.py:50`, corre código contra el sandbox Docker real — solo en
el panel docente), **EngagementGeneratorAgent** (`services/engagement_generator.py:179`,
genera con LLM real los recursos de enganche).

---

## 5. ¿EXISTE DIAGNÓSTICO CONTINUO?

Parcialmente, y de forma desigual entre capas.

- **Dentro de una sesión, a nivel de estado:** SÍ hay reinterpretación continua — cada
  fact evaluativo nuevo dispara `Diagnosticar` de nuevo, y una decisión puede quedar
  obsoleta y regenerarse en cascada.
- **A nivel de confianza/certeza sobre el estudiante:** NO — la política v1 congela la
  confianza en el valor declarado por la regla, siempre.
- **A nivel de memoria entre sesiones:** el modelo persistente solo se escribe al
  cerrar sesión (`ejecutar_walkthrough(cerrar_sesion=True)`), nunca a mitad de sesión.
- **A nivel de ruta (LearningPath):** NO — se fija una vez en el onboarding, no se
  recalcula por el runtime.

No es un vacío de diseño — es una decisión de política explícitamente documentada
como el estado actual de "v1" mientras no exista un productor cuyas confianzas varíen
legítimamente.

---

## 6. MODELO DE APRENDIZAJE REAL (no el ideal)

- **Mastery learning parcial**: la tensión Remediar/Orientar es literalmente
  "¿dominado o no?" con un umbral de errores fijo (≥2).
- **Scaffolding real** en el nombre de la acción (`avanzar-con-andamiaje`) y en las
  prácticas (hints escalonados de 3 niveles en `OrderingPractice.tsx`).
- **Aprendizaje guiado, no exploratorio ni constructivo**: el estudiante casi nunca
  produce algo libre — incluso "CodeLab" es un puzzle de arrastrar-y-soltar, sin
  editor ni ejecución.
- **Microlearning por ciclo**: fases cortas (concepto→práctica→decisión) por "ciclo".
- **Adaptación de presentación, no de contenido generativo real** salvo LLM en 3
  bloques de concepto por módulo.
- **Gamificación superficial**: existe, no es motor central.
- **NO es práctica deliberada en sentido estricto**: no hay producción activa de
  código verificable por el estudiante en el flujo real, pese a que la infraestructura
  (sandbox Docker con clasificación de errores) existe y funciona.

---

## 7. INVENTARIO DEL FLUJO DE APRENDIZAJE

1. **Inicio real:** login → `ProtectedRoute` → `AcademicGuard` redirige a
   `/estudiante/onboarding` si `experience.state === 'NOT_STARTED'`. Onboarding es una
   sola pantalla explicativa con un botón — no recoge nada.
2. **Pre-Test:** dos instrumentos separados y consecutivos: (a) Likert de 18 ítems (8
   conocimiento previo + 10 modalidad VARK) que calcula `dominant_modality` por
   argmax; (b) MCQ de 12 preguntas reales de contenido (`knowledge_test_bank.py`,
   `BANK_VERSION=2`), sin componente de modalidad.
3. **Agentes:** ver §4.
4. **Ruta:** `generate_learning_path_adaptive` — cálculo SQL puro, una vez.
5. **Cambio durante la sesión:** NO cambia la secuencia de módulos; SÍ cambia el orden
   de bloques de contenido (`decision_adaptativa`) y puede insertarse un refuerzo
   dentro del ciclo activo (`submitCycleEvidence`).
6. **Tutor IA:** genuinamente grounded — lee la decisión de adaptación vigente, las
   señales conductuales de Tutorizar y la memoria consolidada. Solo se activa por
   click manual.
7. **Laboratorio:** puzzle de arrastrar-y-soltar, sin editor ni ejecución real.
8. **Editor:** no existe en el flujo del estudiante.
9. **Runner Python:** existe, real, corre en Docker aislado, clasifica errores en 6
   categorías, preserva el traceback — huérfano del flujo del estudiante.
10. **Presentación de contenidos:** plantillas interpoladas (mayoría), banco estático
    reordenado por modalidad, bloques de concepto por LLM real (hasta 3 por módulo).
11. **Feedback:** rico, con escalación real — 3 intentos con pistas cada vez más
    específicas.
12. **Cierre de misión:** "veredicto del Evaluador" que, pese al comentario del
    código, es en realidad una plantilla de 3 opciones fijas seleccionada
    client-side por umbral numérico — no una llamada a la capacidad `EVALUAR` del
    runtime ni al LLM.

---

## 8. FORTALEZAS

- Runtime genuinamente riguroso: invariantes probadas, trazabilidad causal completa.
- Feedback pedagógico de calidad real en las prácticas.
- Tutor IA genuinamente grounded en evidencia real del estudiante.
- Frontera "Adaptar decide categorías, nunca recursos físicos" limpiamente respetada.
- Capacidad demostrada de evolucionar sin romper la arquitectura (fix de modalidad real).

## 9. DEBILIDADES

- Confianza reforzable/decayente inerte bajo la política en producción.
- Ruta macro estática desde el pre-test.
- "Laboratorio" no es un laboratorio, pese a infraestructura Docker completa y
  desconectada.
- Señal conductual de frustración/confusión sin intervención proactiva.
- "Veredicto del Evaluador" es una ilusión de agente (plantilla cliente-side).
- Dos instrumentos de pre-test consecutivos antes de contenido real.

## 10. OPORTUNIDADES DE EVOLUCIÓN

- Conectar el runner Python real al flujo del estudiante.
- Decidir conscientemente si se activa la confianza reforzable (política v2).
- Decidir si la señal de Tutorizar debería disparar algo proactivo.
- Decidir si el "veredicto del Evaluador" debería conectarse a `EVALUAR` real.
- Evaluar si la ruta macro debería reestructurarse durante la sesión.

## RIESGOS DE MODIFICAR EL SISTEMA

- Invariantes matemáticamente probadas (A1-A8, INV-1 a INV-12) — cambiar `politica.py`
  tiene efectos en cascada documentados.
- `BaseAgent` confirmado muerto — seguro ignorarlo; eliminación física es épica aparte.
- Conectar el runner real toca seguridad ya diseñada — reutilizar es más seguro que
  reconstruir.
- El veredicto ilusorio funciona bien hoy — cambiarlo requiere cuidado narrativo.

## TABLA DE BRECHAS

| Dimensión | YA EXISTE | DEBERÍA EVOLUCIONAR | NO EXISTE TODAVÍA |
|---|---|---|---|
| Adaptación | Modalidad+profundidad por decisión del runtime, dentro de un módulo | Adaptación de la secuencia macro de módulos | Adaptación por dificultad fina |
| Diagnóstico | Reinterpretación por hecho nuevo, cascada de obsolescencia | Activar confianza reforzable/decayente | Diagnóstico a partir de código real |
| Agentes | 7 capacidades del runtime + Tutor grounded + ResearchAgent/EngagementGenerator | Conectar Tutorizar con una acción proactiva | Un "Evaluador" real tras el veredicto de cierre |
| Laboratorio | Sandbox Docker completo, seguro | — | Cualquier pantalla del estudiante que lo use |
| Editor | — | — | Editor de código real |
| Contenidos | Plantillas + banco estático + LLM en concept blocks | Ampliar generación LLM | Generación completa por módulo |
| Feedback | Hints escalonados, explicación del error, fuente/evidencia | — | — |
| Ayudas | Tutor manual, grounded | Ayuda proactiva ante señal | — |
| Progresión | Fases claras por ciclo | Progresión de ruta macro reactiva al runtime | — |
| Evaluación | MCQ pre/post-test, cycle-evidence | Veredicto de cierre conectado a EVALUAR real | Evaluación de código escrito libremente |
| Motivación | AchievementsStrip, "¿Sabías que...?" con fuente | — | Mecánica de motivación central |
| Navegación | Onboarding→2 pre-tests→ruta, guardas claras | Reducir fricción de doble instrumento | — |
| Experiencia continua | Estado del runtime se extiende sin cortes dentro de sesión | Ruta macro continua entre sesiones | — |
