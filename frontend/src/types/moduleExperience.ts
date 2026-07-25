// Patrón de Experiencia de Módulo — referencia funcional congelada (jul 2026).
// Un módulo NO es una secuencia de pantallas: es una apertura de curiosidad,
// una cadena de ciclos [concepto multimodal → práctica universal → feedback →
// decisión], un reto integrador y un cierre en tres tiempos.
// S1 implementa apertura + ciclos con práctica de ordenamiento; los demás
// tipos de práctica (fill_blank, predict_output, write_code, trace_table)
// amplían PracticeDef en S3 sin cambiar este patrón.

import type { LearningModality } from '@/types/modality'
import type { PythonErrorCategory } from '@/hooks/usePyodide'

// ── Teoría multimodal ──────────────────────────────────────────────────────────

export type TheoryMedium =
  | 'infografia'
  | 'animacion'
  | 'diagrama'
  | 'clip_narrado'
  | 'podcast'
  | 'texto'
  | 'ejemplo_comentado'
  | 'articulo'
  | 'simulacion'
  | 'codigo_anotado'

/** Infografía comparativa real (RC-FINAL): la variante visual debe SER visual,
 *  no texto con etiqueta de infografía. Dos paneles: la instrucción ambigua con
 *  las preguntas que el robot no puede responder, y la precisa con sus partes. */
export interface ConceptInfographic {
  vague: { instruction: string; questions: string[] }
  precise: { instruction: string; parts: string[] }
  caption: string
}

export interface ConceptVariant {
  medium: TheoryMedium
  mediumLabel: string
  /** Párrafos de apoyo. En S1 es mock; en S2 lo alimenta el Content Discovery Agent. */
  body: string[]
  /** "Elegido para ti — fuente: ..." (explicabilidad sin interrumpir) */
  sourceNote?: string
  /** Solo variantes visuales: comparación gráfica renderizada de verdad. */
  infographic?: ConceptInfographic
  /** Solo variantes de audio: texto narrado con voz real (AudioNarration),
   *  nunca un guion de desarrollador visible al estudiante. */
  narrationText?: string
}

/** Un segundo ejemplo concreto DEL MISMO concepto — no un refuerzo opcional:
 *  parte del recorrido obligatorio, para que la teoría no dependa de un solo
 *  caso (refinamiento de experiencia, jul 2026 — "más ejemplos... durante
 *  toda la explicación", no solo al final). */
export interface SecondExample {
  label: string
  body: string[]
}

export interface CycleConcept {
  title: string
  variants: Record<LearningModality, ConceptVariant>
  /** Un segundo caso concreto, distinto del de `variants`, mostrado siempre
   *  (no depende de la modalidad) — refuerza con variación, no repetición. */
  secondExample?: SecondExample
  /** Puente a Python del PROPIO ejemplo de la teoría (no el de la práctica) —
   *  aparece durante el desarrollo del concepto, antes de la actividad. */
  pythonBridge?: PythonBridge
  /** Recordatorio breve del MISMO concepto (no un concepto distinto) para un
   *  estudiante que el pre-test ya mostró que domina el tema — Adaptar
   *  (profundidad="aplicacion") condensa en vez de repetir la explicación
   *  completa + segundo ejemplo + puente pasivo, que son refuerzo por
   *  repetición: apropiado para quien recién lo ve, redundante para quien
   *  ya lo demostró. Sin este campo, el ciclo se comporta exactamente igual
   *  que antes (resolveConceptForRender cae al comportamiento de siempre). */
  quickRecap?: { body: string[] }
}

// ── Práctica universal (idéntica para todas las modalidades) ──────────────────

export interface OrderingItem {
  id: string
  text: string
  /** Posición correcta (1-based). null = distractor que debe descartarse. */
  position: number | null
  /** Feedback diagnóstico si el estudiante lo incluye (solo distractores). */
  whyWrong?: string
}

export interface OrderingPracticeDef {
  kind: 'ordering'
  prompt: string
  items: OrderingItem[]
  successFeedback: string
  /** Feedback diagnóstico cuando la secuencia usa los ítems correctos en orden incorrecto. */
  orderFeedback: string
  /** Pista general del intento 1 — señala que algo falla sin decir qué. */
  generalHint?: string
  /** Explicación que acompaña a la solución completa (se muestra al 3er intento fallido). */
  solutionExplanation?: string[]
}

// Multimodalidad profunda (jul 2026): el tipo de interacción también cambia
// con el estudiante, no solo el recurso mostrado. `predict_output` ya estaba
// anunciado en la cabecera de este archivo desde S1 ("los demás tipos de
// práctica... amplían PracticeDef en S3") — "elegir respuestas" que exige
// simular mentalmente la ejecución, no solo reconocer un patrón visual.
export interface PredictOutputOption {
  id: string
  text: string
}

export interface PredictOutputPracticeDef {
  kind: 'predict_output'
  prompt: string
  /** Fragmento real de Python — nunca pseudocódigo. */
  code: string
  options: PredictOutputOption[]
  correctOptionId: string
  successFeedback: string
  /** Feedback tras una opción incorrecta — señala QUÉ se confundió, no solo que falló. */
  wrongFeedback: string
  /** Explicación paso a paso de la ejecución — se muestra tras agotar los intentos. */
  solutionExplanation: string[]
  /** Narra el enunciado con voz real (AudioNarration, el MISMO componente que
   *  ya usa la teoría) — auditoría "diversidad pedagógica" (jul 2026, revisión
   *  post-sprint): sin esto, un ejercicio para el perfil auditivo podía decir
   *  "después de escuchar..." sin reproducir ningún audio — una etiqueta que
   *  prometía una modalidad que la pantalla no entregaba. Opcional: sin este
   *  campo, la práctica se ve exactamente igual que antes (comportamiento
   *  previo intacto para lector/visual/kinestésico, que nunca lo necesitaron). */
  narrationText?: string
}

export type PracticeDef = OrderingPracticeDef | PredictOutputPracticeDef

// ── Momento de Decisión (autonomía con barandas) ───────────────────────────────

export type ReinforcementKind = 'reto' | 'ejemplo' | 'animacion' | 'audio'

export interface Reinforcement {
  kind: ReinforcementKind
  label: string
  title: string
  body: string[]
  medium?: TheoryMedium
  /** Escena de AnimatedScene a renderizar. Obligatoria cuando el refuerzo se
   *  presenta como animación: la etiqueta debe cumplirse con una animación
   *  real, nunca con un guion de texto (PED-002). */
  sceneId?: string
  /** Texto a narrar con AudioNarration. Obligatorio cuando el refuerzo se
   *  presenta como audio: «Escuchar» debe cumplirse con voz real, nunca con
   *  un guion de texto (PED-003). Texto plano — sin emojis ni comillas. */
  narrationText?: string
  /** Solo para kind 'reto': una variante corta de práctica — cualquier
   *  PracticeDef, no solo ordering (multimodalidad profunda, jul 2026). */
  practice?: PracticeDef
  /** Solo para kind 'ejemplo': su propio puente a Python — si el estudiante
   *  explora un ejemplo adicional, también ve su código, no solo el del
   *  ejemplo principal del ciclo. */
  pythonBridge?: PythonBridge
}

export interface DecisionMenuDef {
  question: string
  reinforcements: Reinforcement[]
}

// ── Escalera de remediación (política jul 2026) ────────────────────────────────
// Se entra por FALLO (agotó los intentos) o por dominio insuficiente pese a
// resolver. Escala en experiencias distintas: nunca repite la misma actividad.
// El Nivel 3 SIEMPRE deja continuar — el bloqueo es imposible por construcción,
// no por un contador. El objetivo no es acertar: es comprender antes de avanzar.

export type RemediationLevel = 0 | 1 | 2 | 3

/** Con qué modalidad se re-explica el concepto en este peldaño.
 *  'same'      — L1: el estilo declarado del estudiante, otra explicación.
 *  'alternate' — L2: otra representación del mismo concepto. */
export type RemediationModality = 'same' | 'alternate'

/** Representación de apoyo del peldaño: ejemplo resuelto (L1), otra
 *  representación (L2). Es lo que hace que la experiencia sea distinta. */
export interface RemediationIllustration {
  medium: TheoryMedium
  mediumLabel: string
  body: string[]
}

export interface RemediationStep {
  level: Exclude<RemediationLevel, 0>
  title: string
  /** Explicación guiada — más guiada a mayor nivel. */
  body: string[]
  conceptModality: RemediationModality
  illustration?: RemediationIllustration
  /** Actividad equivalente, distinta en cada peldaño y más simple al bajar.
   *  El Nivel 3 no la tiene: muestra la solución explicada y deja continuar. */
  practice?: OrderingPracticeDef
}

export interface RemediationLadder {
  steps: RemediationStep[]
}

// ── ¿Sabías que...? ─────────────────────────────────────────────────────────────
// El flujo legacy (EngageGateway) ya tenía esta tarjeta; el patrón de
// experiencia (S1) no. Recuperada aquí como dato del ciclo — rompe la
// monotonía teoría→práctica y sirve de transición antes del concepto
// (refinamiento de experiencia, jul 2026 — prioridad del usuario).
export interface CuriosityFact {
  /** El dato en sí — verificable, no una curiosidad inventada. */
  fact: string
  /** Por qué este dato conecta con lo que el estudiante está por aprender. */
  connection: string
  /** Origen verificable del dato (sprint "UX ¿Sabías que...?", jul 2026) —
   *  nunca una referencia inventada. No es cita APA: solo el nombre de la
   *  fuente real donde el dato puede confirmarse (p. ej. "Computer History
   *  Museum", "National Inventors Hall of Fame", "Python.org", "PEP 20",
   *  "Real Python", "MDN"). Obligatorio: un dato sin fuente verificable no
   *  debería mostrarse como curiosidad. */
  source: string
}

// ── Puente a Python ─────────────────────────────────────────────────────────────
// El estudiante resuelve la analogía (robot, sensor, etc.) pero pasa buena
// parte del módulo sin sentir que está aprendiendo Python. El puente conecta
// EXACTAMENTE lo que acaba de construir con su forma real en Python, en el
// momento en que la analogía ya está resuelta (refinamiento de experiencia,
// jul 2026 — prioridad del usuario, no un concepto nuevo del dominio).
export interface PythonBridge {
  /** Ej. "Esto ya es Python". */
  label: string
  /** Código real, ejecutable — nunca pseudocódigo disfrazado. */
  code: string
  /** Une la analogía recién resuelta con el fragmento de arriba. */
  explanation: string
  /** Micropráctica interactiva opcional — "ahora hazlo tú": el estudiante
   *  escribe Python real (ejecutado con Pyodide, en el navegador) inmediatamente
   *  después del puente, mientras la analogía sigue fresca. */
  practice?: PythonMicroPracticeDef
}

// Andamiaje de Python (jul 2026, Sprint "Andamiaje completo"): cada peldaño
// de la MISMA escalera que ya describía el comentario de `nextStage` más
// abajo ("arrastrar → completar → escribir → modificar → aplicar"), ahora
// nombrada explícitamente para que la UI pueda variar su interacción sin
// inventar un componente nuevo por peldaño. `undefined` = comportamiento
// previo exacto (editor libre, con o sin starterCode según `profundidad`).
export type PythonPracticeMode =
  | 'observar' // el código YA está completo y es correcto: el estudiante solo lo ejecuta y ve qué hace, sin escribir nada.
  | 'manipular' // el código funciona; el estudiante cambia SOLO el detalle que el prompt señala (un valor, un texto).
  | 'completar' // el código tiene un hueco explícito (ej. una línea con ____); el estudiante completa esa parte.
  | 'corregir' // el código tiene un error deliberado; el estudiante lo encuentra y lo corrige.
  | 'escribir_parcial' // el estudiante escribe desde un scaffold (starterCode no vacío).
  | 'escribir_completo' // el estudiante escribe todo, sin scaffold (starterCode vacío).

export interface PythonMicroPracticeDef {
  /** Peldaño de la escalera de andamiaje — gobierna cómo se presenta el
   *  editor (solo lectura en 'observar', libre en el resto). Ausente =
   *  comportamiento previo (editor libre siempre). */
  mode?: PythonPracticeMode
  /** Qué debe lograr el código que escriba (consigna corta, 1-2 líneas). */
  prompt: string
  /** Scaffold inicial del editor — nunca la solución. */
  starterCode: string
  /** Salida esperada por stdout (comparación exacta, recortando espacios).
   *
   *  Para etapas SIN `simulatedInputs` (input() real, Commit 4 en adelante):
   *  puede contener marcadores posicionales `{input1}`, `{input2}`, ... que
   *  `PythonBridge.tsx` sustituye por los valores reales que el estudiante
   *  escribió, en el mismo orden (Commit 6, ENGINEERING-GATE-EPICA-B.md §9).
   *  Posicional, nunca nominal (`{nombre}`): el runtime nunca parsea el
   *  código del estudiante, solo conoce el orden de entrega. Ejemplo:
   *  antes (legado, `simulatedInputs: ['Camila']`):
   *    `'¿Cómo te llamas? Mucho gusto, Camila'`
   *  ahora (input() real, sin `simulatedInputs`):
   *    `'¿Cómo te llamas? Mucho gusto, {input1}'`
   *  Sin marcadores, el comportamiento es idéntico al de siempre —
   *  compatibilidad total con etapas legadas. Un `{inputN}` para el que no
   *  hubo un `input()` real correspondiente (desajuste con el código de
   *  referencia) NUNCA se resuelve como cadena vacía — fuerza la etapa a
   *  "incorrecto" de forma determinista y deja un diagnóstico visible
   *  (`resolveExpectedOutput` en `PythonBridge.tsx`), en vez de arriesgar
   *  una coincidencia accidental. */
  expectedOutput: string
  /** Pista genérica tras el primer intento fallido — fallback cuando la
   *  categoría del error (sintaxis/variables/lógica/salida, derivada del
   *  propio error de Pyodide) no tiene una pista específica en
   *  `hintsByCategory`, o cuando este campo no está definido. */
  hint: string
  /** Pista específica por tipo de error — la ayuda responde a POR QUÉ falló,
   *  no solo a CUÁNTAS veces. Opcional y parcial: las categorías ausentes
   *  caen en `hint`. Sin este campo, el comportamiento es idéntico al de
   *  antes (siempre `hint`). */
  hintsByCategory?: Partial<Record<PythonErrorCategory, string>>
  /** Apoyo tras el segundo intento fallido — un caso resuelto ANÁLOGO (mismo
   *  patrón, datos distintos), nunca la solución del propio ejercicio. Mismo
   *  espíritu que `RemediationIllustration`, aplicado a la micropráctica de
   *  Python. Opcional: sin él, el intento 2 no agrega apoyo nuevo (compatible
   *  con el contenido ya autorado). */
  workedExample?: {
    code: string
    output: string
    explanation: string
  }
  /** Explicación breve que conecta, tras una ejecución CORRECTA, el
   *  concepto con la instrucción usada y el resultado observado (sprint
   *  "PythonBridge como entorno de aprendizaje real", jul 2026) — el
   *  estudiante debe ver código→ejecución→salida→explicación en TODOS los
   *  peldaños, no solo en el último. Opcional: sin ella, el peldaño sigue
   *  mostrando código, salida y el mensaje de acierto, solo sin la frase
   *  adicional que conecta sintaxis y concepto. */
  resultExplanation?: string
  /** Solución — se ofrece solo tras agotar los intentos, nunca antes. */
  solutionCode: string
  /** Valor(es) que "escribe" el usuario simulado, en el mismo orden en que el
   *  código del estudiante llama a input(). Se muestran en la UI ANTES de
   *  ejecutar — el estudiante ve exactamente qué recibirá su input(), nunca
   *  un valor mágico — y se inyectan a pyodide.setStdin en ese orden.
   *  Ausente = sin stdin conectado (comportamiento previo, sin cambios para
   *  las microprácticas de print()/variables que no lo necesitan). */
  simulatedInputs?: string[]
  /** Progresión pedagógica del MISMO concepto (jul 2026, v1 — infraestructura
   *  mínima, no el diseño final del flujo adaptativo): al resolver esta etapa,
   *  si existe nextStage se muestra en el mismo componente, sin pantalla
   *  nueva ni "Etapa X de Y" — el estudiante nunca cambia de actividad, solo
   *  profundiza. Con `mode` (Sprint "Andamiaje completo"), la cadena
   *  encadena los peldaños reales: observar → manipular → completar →
   *  corregir → escribir parcial → escribir completo.
   *  Cadena lineal por ahora: decidir cuándo reforzar, repetir o saltar una
   *  etapa según evidencia queda para una iteración futura, no esta. */
  nextStage?: PythonMicroPracticeDef
}

// Multimodalidad profunda (jul 2026, primer paso de arquitectura): la
// práctica PRINCIPAL del ciclo —no solo el refuerzo opcional— puede variar
// según la modalidad efectiva. `default` es obligatorio (comportamiento
// previo, cero autores rotos); las demás claves son variantes explícitas —
// nunca un fallback implícito entre modalidades, para no atribuirle a una
// modalidad una mecánica pensada para otra.
export interface ModalityPracticeVariants {
  default: PracticeDef
  visual?: PracticeDef
  reading?: PracticeDef
  audio?: PracticeDef
  kinesthetic?: PracticeDef
}

// Experience Recipe (jul 2026, Etapa 2 del Experience Orchestrator): hasta
// aquí, cada pieza de la experiencia (teoría, práctica, orden de refuerzo)
// se resolvía por separado para la misma modalidad — sin que existiera un
// objeto que representara "la experiencia visual completa de este
// concepto". Una receta agrupa esas piezas en una sola unidad componible.
// Opcional y aditivo: un ciclo sin `recipes` sigue resolviendo pieza por
// pieza exactamente como antes (concept.variants + ModalityPracticeVariants
// + prioridad global de refuerzo) — ningún contenido existente se reescribe
// para adoptar este modelo.
export interface ExperienceRecipe {
  /** Presentación teórica de esta receta — mismo tipo que ya usa
   *  CycleConcept.variants[modalidad], reutilizado sin cambios. */
  concept: ConceptVariant
  /** Mecánica de interacción principal de esta receta. */
  practice: PracticeDef
  /** Orden de refuerzo preferido de ESTA receta — reemplaza la entrada de
   *  esa modalidad en la prioridad global cuando la receta existe. */
  reinforcementPriority: ReinforcementKind[]
}

export type ExperienceRecipeBook = Partial<Record<LearningModality, ExperienceRecipe>>

// ── Microexplicación de concepto ────────────────────────────────────────────
// Tarjeta MUY corta (menos de un minuto) que nombra un término de Python justo
// ANTES de que el ciclo lo use por primera vez — antes, `print`, `if`, etc.
// aparecían directamente dentro del código de PythonBridge sin que ningún
// lugar del recorrido dijera qué es o para qué sirve (sprint "mejora
// pedagógica", jul 2026). No es la teoría del ciclo (eso ya lo cubre
// CycleConcept: la analogía completa) ni parte de PythonBridge (que sigue
// intacto): es una definición mínima y reutilizable del TÉRMINO en sí.
export interface ConceptPrimer {
  /** El término tal como aparece en Python, p. ej. "print". */
  term: string
  /** Definición de una frase — nunca un párrafo. */
  whatIsIt: string
  /** Para qué sirve, en una frase. */
  whatFor: string
  /** Ejemplo mínimo, siempre código real ejecutable — nunca pseudocódigo. */
  example: {
    code: string
    result: string
  }
}

// ── Ciclo de aprendizaje ───────────────────────────────────────────────────────

export interface LearningCycle {
  id: string
  conceptId: string
  conceptLabel: string
  /** Prior de dominio (en S4 lo carga el evaluador desde el pre-test). */
  priorMastery: number
  concept: CycleConcept
  /** PracticeDef único (comportamiento previo) o ModalityPracticeVariants —
   *  cuándo la mecánica de la práctica principal, no solo el refuerzo, debe
   *  cambiar completamente según cómo aprende el estudiante. */
  practice: PracticeDef | ModalityPracticeVariants
  decision?: DecisionMenuDef
  /** Escalera de remediación del ciclo. Sin ella, agotar los intentos revela la
   *  solución en la propia práctica (comportamiento previo a la política). */
  remediation?: RemediationLadder
  /** Se muestra justo al resolver la práctica — el momento "esto era Python". */
  pythonBridge?: PythonBridge
  /** Se muestra antes del concepto — la pausa "¿Sabías que...?". */
  curiosityFact?: CuriosityFact
  /** Microexplicaciones a mostrar, EN ORDEN, antes de curiosityFact/concept —
   *  una por término nuevo que este ciclo introduce por primera vez (p. ej.
   *  ["print"], o ["if", "else"] cuando ambos aparecen juntos). Sin este
   *  campo, el ciclo se comporta exactamente igual que antes. */
  conceptPrimers?: ConceptPrimer[]
  /** Experiencias completas por modalidad (Etapa 2 del Experience
   *  Orchestrator) — cuando existe una receta para la modalidad efectiva,
   *  gobierna teoría+práctica+prioridad de refuerzo como una sola unidad,
   *  en vez de resolverlas por separado desde `concept`/`practice`. */
  recipes?: ExperienceRecipeBook
}

// ── Apertura de curiosidad ─────────────────────────────────────────────────────

export interface CuriosityOpening {
  /** La pregunta intrigante — el tema NO se menciona aquí. */
  questionLines: string[]
  options: string[]
  freeTextPrompt?: string
  /** La revelación: por qué la pregunta importa, recién aquí aparece la misión. */
  revealHook: string
}

// ── Cierre del módulo ──────────────────────────────────────────────────────────
// La continuidad narrativa vive en los DATOS del módulo, nunca hardcodeada en el
// componente: el cierre debe nombrar lo que el estudiante construyó y tender el
// puente hacia la misión REAL que sigue en la ruta (no hacia promesas de sprint).

// LEARN-002 — Cierre de la hipótesis inicial: el ciclo del experimento se
// completa. La apertura registró qué predijo el estudiante; el cierre se lo
// devuelve con veredicto y explicación: qué pensaste, si estabas en lo cierto,
// y por qué ahora entiendes más. Sin esto la hipótesis quedaba sin respuesta.
export interface HypothesisVerdict {
  /** Etiqueta corta del veredicto («Acertaste», «Te acercaste», «Ahora lo sabes»). */
  label: string
  /** Qué pensó al inicio vs. qué comprobó — y por qué cambió o se confirmó. */
  text: string
}

export interface HypothesisClosure {
  /** Veredicto por opción de la apertura (clave = texto EXACTO de la opción). */
  verdicts: Record<string, HypothesisVerdict>
  /** Cierre común tras el veredicto (p. ej., el puente hacia Python). */
  coda?: string
}

export interface ModuleClosing {
  /** Qué construyó el estudiante, en términos del módulo. */
  achievement: string
  /** LEARN-002: respuesta a la hipótesis que el estudiante dio en la apertura. */
  hypothesis?: HypothesisClosure
  /** Puente narrativo hacia la siguiente misión tal como existe en la ruta.
   *  OMITIR en modo módulo de referencia (PED-004): mientras los módulos
   *  legacy estén fuera de la experiencia, el cierre no anuncia nada externo
   *  y todo termina dentro del módulo. */
  nextMission?: {
    /** Título exacto de la siguiente misión (el que el estudiante verá al llegar). */
    title: string
    /** Por qué lo aprendido aquí desemboca en esa misión. */
    hook: string
  }
}

// ── Definición del módulo ──────────────────────────────────────────────────────

export interface ModuleExperienceDefinition {
  moduleNumber: number
  missionTitle: string
  /** Título con el que la RUTA presenta este módulo (m-6): la revelación lo
   *  cita para que el estudiante entienda que la misión temática ES el módulo
   *  que eligió, no otro lugar. */
  routeTitle?: string
  territory: string
  /** Títulos de PathModule que activan esta experiencia (normalizados sin tildes/case). */
  matchTitles: string[]
  opening: CuriosityOpening
  cycles: LearningCycle[]
  closing: ModuleClosing
}
