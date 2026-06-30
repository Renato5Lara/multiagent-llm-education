import type {
  LearningJourneyStep,
  MicroQuestionMeta,
  PredictionMeta,
  MiniActivityMeta,
  CuriosityMeta,
  AnalogyMeta,
} from '@/types/learningJourney'
import type { LearningModality } from '@/types/modality'
import { makeMediaPrompt, makeMediaPromptForced } from './mediaPromptFactory'

// ── Normalize utility (shared with mediaPromptFactory) ────────────────────────

function normalize(text: string): string {
  return text.toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '')
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
      image_hint:  'Una biblioteca con estantes etiquetados (tablas), libros (registros) y un catálogo central (índice).',
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
      image_hint:  'Un mapa de carreteras: ciudades (computadoras), autopistas (banda ancha), cruces (routers), semáforos (protocolos).',
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
      image_hint:  'Una lupa apuntando a un conjunto de puntos que revelan una tendencia clara y una línea de regresión.',
    },
  },
  {
    keywords: ['inteligencia artificial', 'machine learning', 'aprendizaje automatico', 'red neuronal', 'entrenamiento'],
    data: {
      source:      'un niño aprendiendo a hablar',
      explanation: 'Así como un niño aprende a hablar escuchando miles de ejemplos y corrigiendo sus errores, un modelo de machine learning aprende analizando datos y ajustando parámetros hasta acertar.',
      image_hint:  'Un niño escuchando palabras (datos de entrenamiento) y un robot realizando el mismo proceso con pesos numéricos.',
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
      image_hint:  'Planos de un edificio transformándose en código: cada piso es un módulo, las puertas son interfaces.',
    },
  },
  {
    keywords: ['arquitectura', 'hardware', 'procesador', 'microprocesador', 'circuito', 'transistor'],
    data: {
      source:      'una ciudad bien planificada',
      explanation: 'Así como una ciudad tiene calles (buses de datos), edificios (unidades de procesamiento) e infraestructura energética, la arquitectura de computadoras organiza componentes interdependientes.',
      image_hint:  'Una ciudad: el ayuntamiento es la CPU, los barrios son la RAM, los almacenes son el disco.',
    },
  },
  {
    keywords: ['calculo', 'derivada', 'integral', 'limite', 'diferencial', 'matematica'],
    data: {
      source:      'un velocímetro',
      explanation: 'Así como el velocímetro mide el cambio de posición en cada instante del viaje, el cálculo diferencial mide cómo cambia cualquier cantidad en cada instante de un proceso.',
      image_hint:  'Un velocímetro con aguja moviéndose, donde la velocidad instantánea representa la derivada y el área bajo la curva la integral.',
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
      fact:   'El costo global del cibercrimen superó los 8 trillones de dólares en 2023. Una empresa es víctima de ransomware cada 11 segundos.',
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
      fact:   'Las ecuaciones diferenciales del cálculo describen el movimiento de planetas, la propagación de epidemias y el comportamiento de los mercados financieros.',
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

// ── Step factories ────────────────────────────────────────────────────────────

export function makeMicroQuestion(conceptIdx: number): LearningJourneyStep {
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

export function makeAnalogy(moduleTitle: string, conceptIdx: number): LearningJourneyStep {
  const domain   = matchDomain(moduleTitle, ANALOGY_DOMAINS)
  const titleLow = moduleTitle.toLowerCase()
  const meta: AnalogyMeta = domain
    ? { target: moduleTitle, source: domain.source, explanation: domain.explanation, image_hint: domain.image_hint }
    : {
        target:      moduleTitle,
        source:      'una guía de viaje',
        explanation: `Así como una guía de viaje te orienta en un lugar desconocido, ${titleLow} te proporciona los fundamentos para orientarte en su campo de aplicación.`,
        image_hint:  `Una guía de viaje abierta con mapas y notas al margen, donde cada sección representa un concepto de ${titleLow}.`,
      }
  return {
    id:       `analogy-${conceptIdx}`,
    type:     'analogy',
    xpReward: 2,
    metadata: meta as unknown as Record<string, unknown>,
  }
}

export function makeMiniActivity(exampleIdx: number): LearningJourneyStep {
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

export function makePrediction(moduleTitle: string, firstApplication: string | undefined): LearningJourneyStep {
  const titleLow = moduleTitle.toLowerCase()
  const meta: PredictionMeta = {
    question: `¿Qué crees que ocurrirá cuando ${titleLow} se aplique en la práctica?`,
    reveal:   firstApplication
      ?? `En la práctica, ${titleLow} permite resolver problemas reales de forma estructurada y eficiente.`,
    hint: 'Piensa en situaciones cotidianas donde esta idea podría marcar la diferencia.',
  }
  return {
    id:             'prediction-pre-application',
    type:           'prediction',
    xpReward:       3,
    requiresAnswer: true,
    metadata:       meta as unknown as Record<string, unknown>,
  }
}

export function makeKinestheticPrediction(moduleTitle: string, conceptIdx: number): LearningJourneyStep {
  const meta: PredictionMeta = {
    question: `Antes de continuar: ¿cómo crees que se comporta ${moduleTitle.toLowerCase()} en el siguiente caso?`,
    reveal:   'A medida que avances, descubrirás el comportamiento real.',
    hint:     'No hay respuesta incorrecta — es solo una predicción.',
  }
  return {
    id:             `kin-pred-${conceptIdx}`,
    type:           'prediction',
    xpReward:       3,
    requiresAnswer: true,
    metadata:       meta as unknown as Record<string, unknown>,
  }
}

export function makeCuriosity(moduleTitle: string, curiosityIdx: number): LearningJourneyStep {
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

// ── D6.3: Modality-based interactive step picker ──────────────────────────────

export function pickInteractiveStep(
  modality:    LearningModality | undefined,
  idx:         number,
  moduleTitle: string,
  conceptText: string,
): LearningJourneyStep {
  switch (modality) {
    case 'visual':
      return idx % 2 === 0
        ? makeMediaPromptForced(moduleTitle, conceptText, idx, 'image')
        : makeAnalogy(moduleTitle, idx)
    case 'reading':
      return idx % 2 === 0
        ? makeMicroQuestion(idx)
        : makeAnalogy(moduleTitle, idx)
    case 'audio':
      return idx % 2 === 0
        ? makeMediaPromptForced(moduleTitle, conceptText, idx, 'video')
        : makeCuriosity(moduleTitle, idx)
    case 'kinesthetic':
      return idx % 2 === 0
        ? makeKinestheticPrediction(moduleTitle, idx)
        : makeMiniActivity(idx)
    default:
      switch (idx % 3) {
        case 0:  return makeMicroQuestion(idx)
        case 1:  return makeAnalogy(moduleTitle, idx)
        default: return makeMediaPrompt(moduleTitle, conceptText, idx)
      }
  }
}
