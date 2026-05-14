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

export const ACCEPTED_FILE_TYPES = '.pdf,.mp4,.jpg,.jpeg,.png,.txt,.docx'
export const MAX_FILE_SIZE_MB = 50

export const DIAGNOSTIC_QUESTIONS = [
    { id: 1, text: 'Prefiero aprender leyendo textos escritos y documentación detallada.' },
    { id: 2, text: 'Me resulta más fácil comprender conceptos mediante videos o explicaciones visuales.' },
    { id: 3, text: 'Aprendo mejor cuando puedo practicar con ejercicios inmediatamente.' },
    { id: 4, text: 'Me motiva superar desafíos difíciles aunque tome más tiempo.' },
    { id: 5, text: 'Prefiero avanzar a mi propio ritmo sin seguir un horario fijo.' },
    { id: 6, text: 'Me ayuda revisar el material varias veces antes de sentirme seguro.' },
    { id: 7, text: 'Disfruto aprender colaborando y discutiendo ideas con otros.' },
    { id: 8, text: 'Necesito ver aplicaciones prácticas para entender la teoría.' },
    { id: 9, text: 'Me resulta útil que el contenido esté organizado por niveles de dificultad.' },
    { id: 10, text: 'Prefiero sesiones cortas e intensas de estudio sobre sesiones largas.' },
    { id: 11, text: 'Me motiva recibir retroalimentación inmediata después de cada ejercicio.' },
    { id: 12, text: 'Puedo estudiar con concentración aunque haya distracciones a mi alrededor.' },
]

export const LIKERT_OPTIONS = [
    { value: 1, label: 'Totalmente en desacuerdo' },
    { value: 2, label: 'En desacuerdo' },
    { value: 3, label: 'Neutral' },
    { value: 4, label: 'De acuerdo' },
    { value: 5, label: 'Totalmente de acuerdo' },
]
