export const APP_NAME = 'UPAO-MAS-EDU'
export const APP_NAME_FULL = 'Sistema Multiagente Educativo UPAO'

export const ROLES = {
    ADMIN: 'admin',
    DOCENTE: 'docente',
    ESTUDIANTE: 'estudiante',
    INVESTIGADOR: 'investigador',
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

export const DIAGNOSTIC_QUESTIONS = [
    { id: 1, text: 'Prefiero aprender leyendo textos escritos y documentación detallada.', modality: 'reading' },
    { id: 2, text: 'Me resulta más fácil comprender conceptos mediante videos o explicaciones visuales.', modality: 'visual' },
    { id: 3, text: 'Aprendo mejor cuando puedo practicar con ejercicios inmediatamente.', modality: 'kinesthetic' },
    { id: 4, text: 'Me motiva superar desafíos difíciles aunque tome más tiempo.', modality: 'kinesthetic' },
    { id: 5, text: 'Prefiero avanzar a mi propio ritmo sin seguir un horario fijo.', modality: 'reading' },
    { id: 6, text: 'Me ayuda revisar el material varias veces antes de sentirme seguro.', modality: 'reading' },
    { id: 7, text: 'Me ayuda escuchar explicaciones o narraciones para comprender mejor.', modality: 'audio' },
    { id: 8, text: 'Prefiero ver videos explicativos antes que leer documentación extensa.', modality: 'video' },
    { id: 9, text: 'Me resulta útil que el contenido esté organizado por niveles de dificultad.', modality: 'reading' },
    { id: 10, text: 'Prefiero sesiones cortas e intensas de estudio sobre sesiones largas.', modality: 'video' },
    { id: 11, text: 'Me motiva recibir retroalimentación inmediata después de cada ejercicio o quiz.', modality: 'game' },
    { id: 12, text: 'Puedo estudiar con concentración aunque haya distracciones a mi alrededor.', modality: 'reading' },
]

export const LIKERT_OPTIONS = [
    { value: 1, label: 'Totalmente en desacuerdo' },
    { value: 2, label: 'En desacuerdo' },
    { value: 3, label: 'Neutral' },
    { value: 4, label: 'De acuerdo' },
    { value: 5, label: 'Totalmente de acuerdo' },
]
