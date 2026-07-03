export const APP_NAME = 'UPAO-MAS-EDU'
export const APP_NAME_FULL = 'Sistema Multiagente Educativo UPAO'

export const ROLES = {
    ADMIN: 'admin',
    DOCENTE: 'docente',
    ESTUDIANTE: 'estudiante',
} as const

export const BLOOM_LEVELS = [
    { value: 1, label: 'Recordar' },
    { value: 2, label: 'Comprender' },
    { value: 3, label: 'Aplicar' },
    { value: 4, label: 'Analizar' },
    { value: 5, label: 'Evaluar' },
    { value: 6, label: 'Crear' },
] as const

export const COURSE_STATUS_LABELS: Record<string, string> = {
    borrador: 'Borrador',
    publicado: 'Publicado',
    archivado: 'Archivado',
}

export const COURSE_STATUS_COLORS: Record<string, string> = {
    borrador: 'bg-yellow-100 text-yellow-700',
    publicado: 'bg-green-100 text-green-700',
    archivado: 'bg-gray-100 text-gray-700',
}

// El scope de la tesis es un solo curso (THESIS_SCOPE_FREEZE.md).
export const THESIS_COURSE_CODE = 'IS301'

// El código es el criterio estable; el nombre es un fallback para payloads
// que aún no exponen course_code. Mismo criterio ya usado en
// EstudianteLayout.tsx para ubicar el curso.
export function isThesisCourse(course: { code?: string; name?: string }): boolean {
    return course.code === THESIS_COURSE_CODE || !!course.name?.toLowerCase().includes('fundamentos de programaci')
}

export const ACCEPTED_FILE_TYPES = '.pdf,.mp4,.jpg,.jpeg,.png,.txt,.docx,.mp3,.wav,.ogg,.html,.zip'
export const MAX_FILE_SIZE_MB = 50

export const MODALITY_LABELS: Record<string, string> = {
    visual: 'Visual',
    video: 'Video',
    audio: 'Auditivo',
    reading: 'Lectura',
    kinesthetic: 'Kinestésico',
    game: 'Gamificación',
}

export const MODALITY_COLORS: Record<string, string> = {
    visual: 'bg-purple-100 text-purple-700 border-purple-200',
    video: 'bg-blue-100 text-blue-700 border-blue-200',
    audio: 'bg-orange-100 text-orange-700 border-orange-200',
    reading: 'bg-green-100 text-green-700 border-green-200',
    kinesthetic: 'bg-red-100 text-red-700 border-red-200',
    game: 'bg-yellow-100 text-yellow-700 border-yellow-200',
}

// ── Diagnóstico — Sección A: Conocimiento Previo (ids 1-5) ────────────────────
// Escala Likert de auto-evaluación: ¿Cuánto conoces este tema?
// Backend usa ids 1-5 → PRIOR_KNOWLEDGE_TOPIC_MAP (no afecta modality_scores)

export type DiagnosticSection = 'prior_knowledge' | 'modality'

export interface DiagnosticQuestion {
    id: number
    text: string
    section: DiagnosticSection
    topic?: string      // solo para prior_knowledge
    modality?: string   // solo para modality
}

export const DIAGNOSTIC_QUESTIONS: DiagnosticQuestion[] = [
    // Sección A — Conocimiento previo (ids 1-8, uno por tema de Fundamentos)
    { id: 1, section: 'prior_knowledge', topic: 'algorithms',   text: 'Puedo describir los pasos para resolver un problema usando un algoritmo.' },
    { id: 2, section: 'prior_knowledge', topic: 'variables',    text: 'Sé qué es una variable y puedo declararla con su tipo de dato.' },
    { id: 3, section: 'prior_knowledge', topic: 'operators',    text: 'Conozco y puedo usar operadores aritméticos, relacionales y lógicos en código.' },
    { id: 4, section: 'prior_knowledge', topic: 'input_output', text: 'Sé cómo leer datos del usuario e imprimir resultados en pantalla.' },
    { id: 5, section: 'prior_knowledge', topic: 'conditionals', text: 'Puedo escribir una estructura if-else o switch por mi cuenta.' },
    { id: 6, section: 'prior_knowledge', topic: 'loops',        text: 'Entiendo cómo funciona un bucle for o while y puedo usarlo.' },
    { id: 7, section: 'prior_knowledge', topic: 'arrays',       text: 'Conozco qué es un arreglo y puedo declarar, recorrer y modificar sus elementos.' },
    { id: 8, section: 'prior_knowledge', topic: 'functions',    text: 'He definido funciones con parámetros y valor de retorno en algún lenguaje.' },

    // Sección B — Modalidad de aprendizaje (ids 9-18)
    { id: 9,  section: 'modality', modality: 'visual',      text: 'Aprendo mejor con diagramas, esquemas o representaciones visuales.' },
    { id: 10, section: 'modality', modality: 'visual',      text: 'Los colores y las imágenes me ayudan a recordar conceptos nuevos.' },
    { id: 11, section: 'modality', modality: 'reading',     text: 'Prefiero leer una explicación detallada antes de practicar.' },
    { id: 12, section: 'modality', modality: 'reading',     text: 'Me resulta muy útil tener el código comentado paso a paso.' },
    { id: 13, section: 'modality', modality: 'reading',     text: 'Prefiero leer ejemplos escritos antes de ver un video.' },
    { id: 14, section: 'modality', modality: 'audio',       text: 'Aprendo mejor cuando alguien me explica verbalmente un concepto.' },
    { id: 15, section: 'modality', modality: 'audio',       text: 'Escuchar narraciones o podcasts me ayuda a comprender mejor.' },
    { id: 16, section: 'modality', modality: 'kinesthetic', text: 'Prefiero aprender haciendo ejercicios directamente, sin mucha teoría.' },
    { id: 17, section: 'modality', modality: 'kinesthetic', text: 'Aprendo mejor cuando puedo probar, equivocarme y corregir libremente.' },
    { id: 18, section: 'modality', modality: 'kinesthetic', text: 'Me gustan los retos y actividades interactivas para aprender.' },
]

export const SECTION_A_IDS = [1, 2, 3, 4, 5, 6, 7, 8]
export const SECTION_B_IDS = [9, 10, 11, 12, 13, 14, 15, 16, 17, 18]

// Escala Likert — aplica a ambas secciones
// Sección A: ¿Cuánto conoces este tema?
// Sección B: ¿Cuánto te identifica esta afirmación?
export const LIKERT_OPTIONS = [
    { value: 1, label: 'Nada',     emoji: '😕' },
    { value: 2, label: 'Poco',     emoji: '😐' },
    { value: 3, label: 'Algo',     emoji: '🙂' },
    { value: 4, label: 'Bastante', emoji: '😊' },
    { value: 5, label: 'Mucho',    emoji: '🎯' },
]
