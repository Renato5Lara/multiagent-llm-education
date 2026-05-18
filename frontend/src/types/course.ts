export type CourseStatus = 'borrador' | 'publicado' | 'archivado'

export interface Course {
    id: string
    code: string
    name: string
    description?: string
    cycle: number
    year: number
    status: CourseStatus
    teacher_id: string
    created_at: string
    updated_at: string
}

export interface CourseCreate {
    code: string
    name: string
    description?: string
    cycle: number
    year: number
}

export interface CourseUpdate {
    code?: string
    name?: string
    description?: string
    cycle?: number
    year?: number
}

export interface CourseListResponse {
    courses: Course[]
    total: number
    page: number
    size: number
}

export interface LearningObjective {
    id: string
    course_id: string
    title: string
    description?: string
    bloom_level: number
    order: number
}

export interface ObjectiveCreate {
    title: string
    description?: string
    bloom_level: number
    order: number
}

export interface ObjectiveUpdate {
    title?: string
    description?: string
    bloom_level?: number
    order?: number
}

export interface EnrollRequest {
    student_ids: string[]
}

export interface EnrollResult {
    success: number
    errors: Array<{ student_id: string; message: string }>
}
