export interface InstitutionalCourse {
    id: string
    code: string
    name: string
    credits: number
    cycle: number
    hours_theory?: number
    hours_practice?: number
    hours_lab?: number
    competencies?: string
    created_at: string
    prerequisite_codes: string[]
}

export interface CycleInfo {
    cycle: number
    total_courses: number
    courses: InstitutionalCourse[]
}

export interface TeacherAssignment {
    id: string
    teacher_id: string
    institutional_course_id: string
    created_at: string
    course?: InstitutionalCourse
}
