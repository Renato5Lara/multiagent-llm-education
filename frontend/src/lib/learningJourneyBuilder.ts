import type {
  LearningJourney,
  LearningJourneyStep,
  MicroQuestionMeta,
  PredictionMeta,
  MiniActivityMeta,
  CuriosityMeta,
  AnalogyMeta,
  MediaPromptMeta,
} from '@/types/learningJourney'
import type {
  EngagementSession,
  EngagementResourceType,
} from '@/types/engagement'
import type { ModuleOrchestrationResponse, ConceptBlock } from '@/types/pedagogy'

// ── Knowledge level (written by PriorKnowledgeCard during Engage) ─────────────

type KnowledgeLevel = 'never_seen' | 'heard_about_it' | 'know_a_bit' | 'know_well'

function readKnowledgeLevel(sessionId: string): KnowledgeLevel | null {
  try {
    const v = sessionStorage.getItem(`engage:knowledge_level:${sessionId}`)
    if (v === 'never_seen' || v === 'heard_about_it' || v === 'know_a_bit' || v === 'know_well') return v
    return null
  } catch {
    return null
  }
}

// ── Depth configuration ───────────────────────────────────────────────────────

interface DepthConfig {
  maxIntroParagraphs:       number
  maxExplanationParagraphs: number
  maxExamples:              number
  maxMisconceptions:        number
}

function getDepthConfig(level: KnowledgeLevel | null): DepthConfig {
  switch (level) {
    case 'never_seen':
    case 'heard_about_it':
      return { maxIntroParagraphs: Infinity, maxExplanationParagraphs: Infinity, maxExamples: Infinity, maxMisconceptions: Infinity }
    case 'know_a_bit':
      return { maxIntroParagraphs: 1, maxExplanationParagraphs: 4, maxExamples: Infinity, maxMisconceptions: 2 }
    case 'know_well':
      return { maxIntroParagraphs: 1, maxExplanationParagraphs: 2, maxExamples: Infinity, maxMisconceptions: 1 }
    default:
      return { maxIntroParagraphs: 2, maxExplanationParagraphs: Infinity, maxExamples: Infinity, maxMisconceptions: Infinity }
  }
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function splitParagraphs(text: string): string[] {
  return text.split(/\n\n+/).map(p => p.trim()).filter(Boolean)
}

function cap<T>(arr: T[], max: number): T[] {
  return max === Infinity ? arr : arr.slice(0, max)
}

// Normalize text for accent-insensitive keyword matching
function normalize(text: string): string {
  return text.toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '')
}

// Extract meaningful keywords from concept text for specific media prompts
function extractKeyTerms(text: string, count: number): string {
  const stop = new Set([
    'que', 'una', 'los', 'las', 'del', 'con', 'para', 'por', 'son',
    'como', 'este', 'esta', 'estos', 'estas', 'cuando', 'puede', 'pero',
    'mas', 'entre', 'tiene', 'dentro', 'traves', 'siendo', 'donde',
  ])
  const words = normalize(text)
    .replace(/[.,;:!?()[\]{}"']/g, ' ')
    .split(/\s+/)
    .filter(w => w.length >= 5 && !stop.has(w))
  // Deduplicate while preserving order
  const seen = new Set<string>()
  const unique: string[] = []
  for (const w of words) {
    if (!seen.has(w)) { seen.add(w); unique.push(w) }
    if (unique.length >= count) break
  }
  return unique.join(', ')
}

// ── Domain knowledge tables ───────────────────────────────────────────────────

interface AnalogyDomain { source: string; explanation: string; image_hint: string }
interface CuriosityDomain { fact: string; stat: string; source: string }

const ANALOGY_DOMAINS: ReadonlyArray<{
  keywords: readonly string[]
  data: AnalogyDomain
}> = [
  {
    keywords: ['base de datos', 'database', 'sql', 'relacional', 'nosql'],
    data: {
      source:      'una biblioteca',
      explanation: 'Así como una biblioteca organiza libros en estantes y catálogos para que los encuentres rápidamente, una base de datos organiza información en tablas e índices para recuperarla en milisegundos.',
      image_hint:  'Una biblioteca con estantes etiquetados (tablas), libros (registros) y un catálogo central (índice). Flechas muestran el camino desde una búsqueda hasta el libro correcto.',
    },
  },
  {
    keywords: ['sistema operativo', 'linux', 'windows', 'kernel', 'proceso', 'planificacion'],
    data: {
      source:      'un director de orquesta',
      explanation: 'Así como el director coordina cada sección de la orquesta para que suenen en armonía sin interferirse, el sistema operativo coordina CPU, memoria y procesos para que convivan sin conflictos.',
      image_hint:  'Un director señalando secciones de una orquesta: percusión (CPU), cuerdas (memoria), viento (procesos de E/S).',
    },
  },
  {
    keywords: ['red', 'redes', 'protocolo', 'internet', 'tcp', 'ip', 'enrutamiento', 'topologia'],
    data: {
      source:      'un sistema de carreteras',
      explanation: 'Así como las carreteras conectan ciudades y los semáforos regulan el tráfico, las redes conectan computadoras y los protocolos regulan cómo fluye la información entre ellas.',
      image_hint:  'Un mapa de carreteras: ciudades (computadoras), autopistas (banda ancha), cruces (routers), semáforos (protocolos de control).',
    },
  },
  {
    keywords: ['programacion', 'algoritmo', 'codigo', 'funcion', 'variable', 'bucle'],
    data: {
      source:      'una receta de cocina',
      explanation: 'Así como una receta indica ingredientes exactos y pasos en orden para obtener un plato, un programa define datos y instrucciones secuenciales para resolver un problema.',
      image_hint:  'Una receta con ingredientes (variables) y pasos numerados (instrucciones) al lado del código equivalente.',
    },
  },
  {
    keywords: ['estadistica', 'probabilidad', 'regresion', 'muestra', 'distribucion', 'hipotesis'],
    data: {
      source:      'una lupa científica',
      explanation: 'Así como una lupa revela detalles que el ojo no percibe, la estadística revela patrones y verdades ocultas dentro de grandes conjuntos de datos.',
      image_hint:  'Una lupa apuntando a un conjunto de puntos dispersos que, vistos a través de ella, revelan una tendencia clara y una línea de regresión.',
    },
  },
  {
    keywords: ['inteligencia artificial', 'machine learning', 'aprendizaje automatico', 'red neuronal', 'entrenamiento'],
    data: {
      source:      'un niño aprendiendo a hablar',
      explanation: 'Así como un niño aprende a hablar escuchando miles de ejemplos y corrigiendo sus errores, un modelo de machine learning aprende analizando datos y ajustando parámetros hasta acertar.',
      image_hint:  'Un niño escuchando palabras (datos de entrenamiento) y un robot a su lado realizando el mismo proceso con neuronas artificiales y pesos numéricos.',
    },
  },
  {
    keywords: ['seguridad', 'ciberseguridad', 'cifrado', 'autenticacion', 'criptografia', 'vulnerabilidad'],
    data: {
      source:      'una caja fuerte bancaria',
      explanation: 'Así como un banco usa candados, cámaras y controles de acceso en capas para proteger el dinero, la ciberseguridad usa cifrado, autenticación y firewalls en capas para proteger la información.',
      image_hint:  'Una caja fuerte con capas visibles: llave (contraseña), combinación (cifrado), guardia (firewall), cámara (monitoreo).',
    },
  },
  {
    keywords: ['ingenieria de software', 'metodologia', 'agile', 'scrum', 'patron', 'arquitectura de software'],
    data: {
      source:      'los planos de un arquitecto',
      explanation: 'Así como un arquitecto dibuja planos antes de construir para evitar errores costosos, la ingeniería de software diseña la estructura del sistema antes de escribir código.',
      image_hint:  'Planos de un edificio transformándose en código: cada piso es un módulo, las puertas son interfaces, los pilares son las dependencias críticas.',
    },
  },
  {
    keywords: ['arquitectura', 'hardware', 'procesador', 'microprocesador', 'circuito', 'transistor'],
    data: {
      source:      'una ciudad bien planificada',
      explanation: 'Así como una ciudad tiene calles (buses de datos), edificios (unidades de procesamiento) e infraestructura de agua y luz (energía), la arquitectura de computadoras organiza componentes interdependientes.',
      image_hint:  'Una ciudad: el ayuntamiento es la CPU, los barrios son la RAM, los almacenes son el disco, las autopistas son los buses de datos.',
    },
  },
  {
    keywords: ['calculo', 'derivada', 'integral', 'limite', 'diferencial', 'matematica'],
    data: {
      source:      'un velocímetro',
      explanation: 'Así como el velocímetro mide el cambio de posición en cada instante del viaje, el cálculo diferencial mide cómo cambia cualquier cantidad en cada instante de un proceso.',
      image_hint:  'Un velocímetro con aguja moviéndose, donde la velocidad instantánea representa la derivada y el área bajo la curva representa la integral.',
    },
  },
]

const CURIOSITY_DOMAINS: ReadonlyArray<{
  keywords: readonly string[]
  data: CuriosityDomain
}> = [
  {
    keywords: ['base de datos', 'database', 'sql', 'relacional', 'nosql'],
    data: {
      fact:   'Netflix almacena más de 700 petabytes de datos y procesa millones de consultas por segundo. Cada recomendación que ves es el resultado de una base de datos bien diseñada.',
      stat:   '700 PB',
      source: 'Netflix Tech Blog, 2023',
    },
  },
  {
    keywords: ['sistema operativo', 'linux', 'windows', 'kernel', 'proceso'],
    data: {
      fact:   'Android, el sistema operativo más usado del mundo, está basado en el kernel Linux. Más del 70% de los supercomputadores del mundo también ejecutan Linux.',
      stat:   '70%',
      source: 'Top500 & StatCounter, 2024',
    },
  },
  {
    keywords: ['red', 'redes', 'protocolo', 'internet', 'tcp', 'ip', 'enrutamiento'],
    data: {
      fact:   'Google opera más de 100,000 km de cables de fibra óptica submarinos y transporta cerca del 25% de todo el tráfico de Internet mundial.',
      stat:   '25%',
      source: 'Google Network Infrastructure, 2023',
    },
  },
  {
    keywords: ['programacion', 'algoritmo', 'codigo', 'funcion'],
    data: {
      fact:   'El algoritmo PageRank de Google nació como un proyecto universitario. Hoy procesa más de 8,500 millones de búsquedas diarias y es la base de la publicidad digital más grande del mundo.',
      stat:   '8.5B/día',
      source: 'Google Search Statistics, 2024',
    },
  },
  {
    keywords: ['estadistica', 'probabilidad', 'regresion', 'muestra', 'distribucion'],
    data: {
      fact:   'Los modelos estadísticos meteorológicos procesan más de 200 millones de observaciones diarias. Un pronóstico de 7 días hoy es más preciso que uno de 1 día hace 30 años.',
      stat:   '200M obs/día',
      source: 'NOAA & ECMWF, 2023',
    },
  },
  {
    keywords: ['inteligencia artificial', 'machine learning', 'aprendizaje automatico', 'red neuronal'],
    data: {
      fact:   'GPT-4 fue entrenado con aproximadamente 1 trillón de tokens de texto. El consumo energético del entrenamiento equivale al de un hogar durante más de 1,000 años.',
      stat:   '1T tokens',
      source: 'OpenAI & AI Energy Research, 2023',
    },
  },
  {
    keywords: ['seguridad', 'ciberseguridad', 'cifrado', 'autenticacion', 'criptografia'],
    data: {
      fact:   'El costo global del cibercrimen superó los 8 trillones de dólares en 2023. Una empresa es víctima de ransomware cada 11 segundos, según Cybersecurity Ventures.',
      stat:   '$8T',
      source: 'Cybersecurity Ventures, 2023',
    },
  },
  {
    keywords: ['ingenieria de software', 'metodologia', 'agile', 'scrum'],
    data: {
      fact:   'Un bug en el software del cohete Ariane 5 causó la pérdida de $500 millones en 1996. La causa: reutilizar código de Ariane 4 sin verificar su compatibilidad.',
      stat:   '$500M',
      source: 'ESA Post-Flight Investigation, 1996',
    },
  },
  {
    keywords: ['arquitectura', 'hardware', 'procesador', 'microprocesador', 'circuito', 'transistor'],
    data: {
      fact:   'El Intel 4004 (1971) tenía 2,300 transistores. Los procesadores modernos superan los 50,000 millones. Un crecimiento de 20 millones de veces en 50 años.',
      stat:   '50B',
      source: 'Intel Architecture History, 2023',
    },
  },
  {
    keywords: ['calculo', 'derivada', 'integral', 'limite', 'diferencial'],
    data: {
      fact:   'Las ecuaciones diferenciales del cálculo describen el movimiento de planetas, la propagación de epidemias y el comportamiento de los mercados financieros. Newton las desarrolló para explicar la gravedad.',
      stat:   '350+ años',
      source: 'Historia de la Matemática, 2023',
    },
  },
]

// ── Domain matcher ────────────────────────────────────────────────────────────

function matchDomain<T>(
  moduleTitle: string,
  domains: ReadonlyArray<{ keywords: readonly string[]; data: T }>,
): T | null {
  const titleNorm = normalize(moduleTitle)
  for (const domain of domains) {
    if (domain.keywords.some(kw => titleNorm.includes(normalize(kw)))) {
      return domain.data
    }
  }
  return null
}

// ── Sprint L4/L4.5: Interactive step factories ────────────────────────────────

function makeMicroQuestion(conceptIdx: number): LearningJourneyStep {
  const meta: MicroQuestionMeta = {
    question: '¿Te imaginabas esto?',
    options:  ['Sí, lo imaginaba', 'No, fue una sorpresa', 'Un poco'],
    feedback: 'Reflexionar sobre lo que sabías antes de leer ayuda a consolidar el aprendizaje.',
  }
  return {
    id:             `micro-q-${conceptIdx}`,
    type:           'micro_question',
    title:          '¿Te imaginabas esto?',
    xpReward:       2,
    requiresAnswer: true,
    metadata:       meta as unknown as Record<string, unknown>,
  }
}

function makeAnalogy(moduleTitle: string, conceptIdx: number): LearningJourneyStep {
  const domain  = matchDomain(moduleTitle, ANALOGY_DOMAINS)
  const titleLow = moduleTitle.toLowerCase()
  const meta: AnalogyMeta = domain
    ? {
        target:      moduleTitle,
        source:      domain.source,
        explanation: domain.explanation,
        image_hint:  domain.image_hint,
      }
    : {
        target:      moduleTitle,
        source:      'una guía de viaje',
        explanation: `Así como una guía de viaje te orienta en un lugar desconocido con mapas y consejos prácticos, ${titleLow} te proporciona los fundamentos para orientarte en su campo de aplicación.`,
        image_hint:  `Una guía de viaje abierta con mapas y notas al margen, donde cada sección representa un concepto de ${titleLow}.`,
      }
  return {
    id:       `analogy-${conceptIdx}`,
    type:     'analogy',
    xpReward: 2,
    metadata: meta as unknown as Record<string, unknown>,
  }
}

function makeMediaPrompt(
  moduleTitle: string,
  conceptText: string,
  conceptIdx:  number,
): LearningJourneyStep {
  const keyTerms = extractKeyTerms(conceptText, 5)
  const titleLow = moduleTitle.toLowerCase()

  // Rotate image/video for variety across multiple media prompts
  const mediaType: 'image' | 'video' = (Math.floor(conceptIdx / 3) % 2 === 0) ? 'image' : 'video'

  const imagePrompt = keyTerms
    ? `Crea una infografía educativa sobre "${moduleTitle}" que visualice los siguientes términos clave: ${keyTerms}. Usa íconos, flechas y colores para mostrar sus relaciones. Fondo blanco, estilo limpio y profesional.`
    : `Crea una infografía educativa que explique "${moduleTitle}" usando ejemplos cotidianos. Incluye íconos y flechas que muestren las relaciones entre sus conceptos principales. Fondo blanco, estilo profesional.`

  const videoPrompt = keyTerms
    ? `Escribe el guion de un video animado de 90 segundos sobre "${moduleTitle}" enfocándose en: ${keyTerms}. Usa metáforas cotidianas, narración clara y al menos un ejemplo del mundo real.`
    : `Escribe el guion de un video animado de 90 segundos que explique "${moduleTitle}" de forma clara. Usa una metáfora cotidiana al inicio y cierra con una aplicación práctica.`

  const meta: MediaPromptMeta = mediaType === 'image'
    ? {
        type:          'image',
        title:         `Visualiza: ${moduleTitle}`,
        prompt:        imagePrompt,
        learning_goal: `Construir una imagen mental del concepto refuerza la memoria a largo plazo y facilita la comprensión de ideas abstractas en ${titleLow}.`,
      }
    : {
        type:             'video',
        title:            `Explora en video: ${moduleTitle}`,
        prompt:           videoPrompt,
        learning_goal:    `Los videos activan múltiples canales sensoriales a la vez, lo que puede incrementar la retención de ${titleLow} hasta en un 65%.`,
        duration_seconds: 90,
      }

  return {
    id:       `media-${conceptIdx}`,
    type:     'media_prompt',
    xpReward: 2,
    metadata: meta as unknown as Record<string, unknown>,
  }
}

function makeMiniActivity(exampleIdx: number): LearningJourneyStep {
  const meta: MiniActivityMeta = {
    instructions: 'Refuerza la idea principal del ejemplo que acabas de leer.',
    steps: [
      'Lee nuevamente el ejemplo.',
      'Identifica el concepto clave que ilustra.',
      'Escribe mentalmente una palabra que lo resuma.',
    ],
  }
  return {
    id:             `mini-act-${exampleIdx}`,
    type:           'mini_activity',
    xpReward:       3,
    requiresAnswer: true,
    metadata:       meta as unknown as Record<string, unknown>,
  }
}

function makePrediction(moduleTitle: string, firstApplication: string | undefined): LearningJourneyStep {
  const titleLow = moduleTitle.toLowerCase()
  const meta: PredictionMeta = {
    question: `¿Qué crees que ocurrirá cuando ${titleLow} se aplique en la práctica?`,
    reveal:   firstApplication
      ?? `En la práctica, ${titleLow} permite resolver problemas reales de forma estructurada y eficiente, con impacto directo en los resultados.`,
    hint:     'Piensa en situaciones cotidianas donde esta idea podría marcar la diferencia.',
  }
  return {
    id:             'prediction-pre-application',
    type:           'prediction',
    xpReward:       3,
    requiresAnswer: true,
    metadata:       meta as unknown as Record<string, unknown>,
  }
}

function makeCuriosity(moduleTitle: string, curiosityIdx: number): LearningJourneyStep {
  const domain = matchDomain(moduleTitle, CURIOSITY_DOMAINS)
  const meta: CuriosityMeta = domain
    ?? {
        fact:   `Profesionales de todo el mundo aplican los principios de ${moduleTitle.toLowerCase()} en industrias tan diversas como medicina, finanzas y entretenimiento.`,
        stat:   'global',
        source: 'Tendencias profesionales, 2024',
      }
  return {
    id:       `curiosity-${curiosityIdx}`,
    type:     'curiosity',
    xpReward: 2,
    metadata: meta as unknown as Record<string, unknown>,
  }
}

// ── Main builder ──────────────────────────────────────────────────────────────

// Maximum interactive (non-concept, non-example) steps per journey.
// Prevents bloat in long modules without penalizing short ones.
const MAX_INTERACTIVE_STEPS = 8

// ── Sprint L1: ConceptBlock → LearningJourney ─────────────────────────────────

/**
 * Builds a LearningJourney from backend-generated ConceptBlocks.
 * Each block contains pre-computed enrichment (analogy, curiosity, media_prompt,
 * mini_activity) so this builder is a pure mapper — no domain heuristics here.
 *
 * The interactive step budget (MAX_INTERACTIVE_STEPS) still applies so that
 * large modules don't produce overwhelming journeys.
 */
function buildJourneyFromConceptBlocks(
  engagementSession: EngagementSession,
  moduleContent:     ModuleOrchestrationResponse,
): LearningJourney {
  const steps: LearningJourneyStep[] = []
  const { concept_blocks, module_title, module_id, course_id } = moduleContent
  let interactiveUsed = 0

  const tryPush = (step: LearningJourneyStep): void => {
    if (interactiveUsed >= MAX_INTERACTIVE_STEPS) return
    steps.push(step)
    interactiveUsed++
  }

  // ── Phase 1: Concept blocks ───────────────────────────────────────────────
  concept_blocks.forEach((block: ConceptBlock, i: number) => {
    // Sprint M1: prediction gate BEFORE concept (LLM-only, never null on template path)
    if (block.prediction_question) {
      const predMeta: PredictionMeta = {
        question: block.prediction_question,
        reveal:   '¡Sigue leyendo para descubrir si tu predicción fue correcta!',
        hint:     'Reflexiona un momento antes de continuar.',
      }
      tryPush({
        id:             `cb-predict-${i}`,
        type:           'prediction',
        xpReward:       1,
        requiresAnswer: true,
        metadata:       predMeta as unknown as Record<string, unknown>,
      })
    }

    // Core concept step
    steps.push({
      id:       block.id,
      type:     'concept',
      title:    block.title,
      content:  block.explanation,
      xpReward: 2,
    })

    // Curiosity — passive, before positional step (every 2 blocks)
    if ((i + 1) % 2 === 0 && block.curiosity) {
      const meta: CuriosityMeta = {
        fact:   block.curiosity.fact,
        stat:   block.curiosity.stat,
        source: block.curiosity.source,
      }
      tryPush({
        id:       `cb-curiosity-${i}`,
        type:     'curiosity',
        xpReward: 2,
        metadata: meta as unknown as Record<string, unknown>,
      })
    }

    // Positional interactive step — round-robin per block index
    switch (i % 3) {
      case 0: {
        // micro_question — generic reflection pause
        const meta: MicroQuestionMeta = {
          question: '¿Te imaginabas esto?',
          options:  ['Sí, lo imaginaba', 'No, fue una sorpresa', 'Un poco'],
          feedback: 'Reflexionar sobre lo que sabías antes de leer ayuda a consolidar el aprendizaje.',
        }
        tryPush({
          id:             `cb-mq-${i}`,
          type:           'micro_question',
          title:          '¿Te imaginabas esto?',
          xpReward:       2,
          requiresAnswer: true,
          metadata:       meta as unknown as Record<string, unknown>,
        })
        break
      }
      case 1: {
        if (!block.analogy) break
        const meta: AnalogyMeta = {
          target:      module_title,
          source:      block.analogy.source,
          explanation: block.analogy.explanation,
          image_hint:  block.analogy.image_hint,
        }
        tryPush({
          id:       `cb-analogy-${i}`,
          type:     'analogy',
          xpReward: 2,
          metadata: meta as unknown as Record<string, unknown>,
        })
        break
      }
      case 2: {
        if (!block.media_prompt) break
        const meta: MediaPromptMeta = {
          type:             block.media_prompt.type,
          title:            block.media_prompt.title,
          prompt:           block.media_prompt.prompt,
          learning_goal:    block.media_prompt.learning_goal,
          duration_seconds: block.media_prompt.duration_seconds,
        }
        tryPush({
          id:       `cb-media-${i}`,
          type:     'media_prompt',
          xpReward: 2,
          metadata: meta as unknown as Record<string, unknown>,
        })
        break
      }
    }

    // Example from block (if any)
    if (block.example) {
      steps.push({
        id:       `cb-example-${i}`,
        type:     'example',
        content:  block.example,
        xpReward: 3,
      })
    }

    // Mini activity — LLM always generates one, so push independent of example
    if (block.mini_activity) {
      const miniMeta: MiniActivityMeta = {
        instructions: block.mini_activity.instructions,
        steps:        block.mini_activity.steps,
      }
      tryPush({
        id:             `cb-mini-${i}`,
        type:           'mini_activity',
        xpReward:       3,
        requiresAnswer: true,
        metadata:       miniMeta as unknown as Record<string, unknown>,
      })

      // Sprint M1: reflection checkpoint AFTER mini_activity (LLM-only)
      if (block.reflection_question) {
        const refMeta: MicroQuestionMeta = {
          question: block.reflection_question,
          options:  ['Puedo explicarlo', 'Lo entiendo parcialmente', 'Necesito repasarlo'],
          feedback: '¡La reflexión metacognitiva fortalece el aprendizaje a largo plazo!',
        }
        tryPush({
          id:             `cb-reflect-${i}`,
          type:           'micro_question',
          title:          block.reflection_question,
          xpReward:       2,
          requiresAnswer: true,
          metadata:       refMeta as unknown as Record<string, unknown>,
        })
      }
    }
  })

  // ── Phase 2: Application (with prediction gate) ───────────────────────────
  const realNewsResource = engagementSession.resources
    .find(r => r.resource_type === ('real_news' as EngagementResourceType))
  const applicationItems: string[] = [
    ...(realNewsResource ? [realNewsResource.content] : []),
    ...moduleContent.real_applications,
  ]
  if (applicationItems.length > 0) {
    const predMeta: PredictionMeta = {
      question: `¿Qué crees que ocurrirá cuando ${module_title.toLowerCase()} se aplique en la práctica?`,
      reveal:   applicationItems[0],
      hint:     'Piensa en situaciones cotidianas donde esta idea podría marcar la diferencia.',
    }
    steps.push({
      id:             'cb-prediction',
      type:           'prediction',
      xpReward:       3,
      requiresAnswer: true,
      metadata:       predMeta as unknown as Record<string, unknown>,
    })
    steps.push({
      id:       'cb-application',
      type:     'application',
      xpReward: 2,
      metadata: { items: applicationItems },
    })
  }

  // ── Phase 3: Reflections ──────────────────────────────────────────────────
  moduleContent.misconceptions.forEach((item, i) => {
    steps.push({
      id:       `cb-reflection-${i}`,
      type:     'reflection',
      title:    item.misconception,
      content:  item.correction,
      xpReward: 5,
      metadata: { severity: item.severity },
    })
  })

  return {
    id:          `journey-${module_id}`,
    moduleTitle: module_title,
    courseId:    course_id,
    steps,
    sessionId:   engagementSession.session_id,
  }
}

// ── Public entry point ────────────────────────────────────────────────────────

/**
 * Builds a module-only LearningJourney. The Engage phase already ran and is
 * NOT repeated here. No engage resource types appear as steps.
 *
 * Sprint L1: if concept_blocks are present, delegates to
 * buildJourneyFromConceptBlocks (backend intelligence). Otherwise falls back
 * to the heuristic L4.5 legacy builder (frontend intelligence).
 */
export function buildJourneyFromLegacy(
  engagementSession: EngagementSession,
  moduleContent:     ModuleOrchestrationResponse,
): LearningJourney {
  // Sprint L1: use enriched backend builder when concept_blocks are populated
  if (moduleContent.concept_blocks && moduleContent.concept_blocks.length > 0) {
    return buildJourneyFromConceptBlocks(engagementSession, moduleContent)
  }

  const steps: LearningJourneyStep[] = []

  // ── Personalization ────────────────────────────────────────────────────────
  const knowledgeLevel = readKnowledgeLevel(engagementSession.session_id)
  const cfg            = getDepthConfig(knowledgeLevel)

  // ── Content pools ──────────────────────────────────────────────────────────
  const introParagraphs       = cap(splitParagraphs(moduleContent.introduction),            cfg.maxIntroParagraphs)
  const explanationParagraphs = cap(splitParagraphs(moduleContent.pedagogical_explanation), cfg.maxExplanationParagraphs)
  const examples              = cap(moduleContent.examples, cfg.maxExamples)

  const conceptPool: Array<{ id: string; text: string }> = [
    ...introParagraphs.map((text, i)       => ({ id: `intro-concept-${i}`, text })),
    ...explanationParagraphs.map((text, i) => ({ id: `concept-${i}`,       text })),
  ]

  const moduleTitle     = moduleContent.module_title
  let   curiosityCount  = 0
  let   interactiveUsed = 0

  // Helper: push a step only while budget allows
  const tryPush = (step: LearningJourneyStep): void => {
    if (interactiveUsed >= MAX_INTERACTIVE_STEPS) return
    steps.push(step)
    interactiveUsed++
  }

  // ── Phase 1: Zip concepts (+ inserts) with examples (+ mini_activity) ─────
  const phaseLen = Math.max(conceptPool.length, examples.length)
  for (let i = 0; i < phaseLen; i++) {

    // ── Concept block ─────────────────────────────────────────────────────────
    if (i < conceptPool.length) {
      const { id, text } = conceptPool[i]
      steps.push({ id, type: 'concept', content: text, xpReward: 2 })

      // Rule 6: curiosity every 2 concepts, before positional step
      if ((i + 1) % 2 === 0) {
        tryPush(makeCuriosity(moduleTitle, curiosityCount++))
      }

      // Rules 1/2/3: positional step by concept index mod 3
      switch (i % 3) {
        case 0: tryPush(makeMicroQuestion(i));                         break
        case 1: tryPush(makeAnalogy(moduleTitle, i));                  break
        case 2: tryPush(makeMediaPrompt(moduleTitle, text, i));        break
      }
    }

    // ── Example block ─────────────────────────────────────────────────────────
    if (i < examples.length) {
      steps.push({ id: `example-${i}`, type: 'example', content: examples[i], xpReward: 3 })
      // Rule 4: mini_activity after every example
      tryPush(makeMiniActivity(i))
    }
  }

  // ── Phase 2: Application (with prediction gate) ────────────────────────────
  const realNewsResource = engagementSession.resources
    .find(r => r.resource_type === ('real_news' as EngagementResourceType))
  const applicationItems: string[] = [
    ...(realNewsResource ? [realNewsResource.content] : []),
    ...moduleContent.real_applications,
  ]
  if (applicationItems.length > 0) {
    // Rule 5: prediction before application (not subject to interactive budget —
    // it's the culmination of the learning arc and should always appear)
    steps.push(makePrediction(moduleTitle, applicationItems[0]))
    steps.push({
      id:       'application-combined',
      type:     'application',
      xpReward: 2,
      metadata: { items: applicationItems },
    })
  }

  // ── Phase 3: Reflections (misconceptions as checkpoints) ──────────────────
  cap(moduleContent.misconceptions, cfg.maxMisconceptions).forEach((item, i) => {
    steps.push({
      id:       `reflection-${i}`,
      type:     'reflection',
      title:    item.misconception,
      content:  item.correction,
      xpReward: 5,
      metadata: { severity: item.severity },
    })
  })

  return {
    id:          `journey-${moduleContent.module_id}`,
    moduleTitle: moduleContent.module_title,
    courseId:    moduleContent.course_id,
    steps,
    sessionId:   engagementSession.session_id,
  }
}
