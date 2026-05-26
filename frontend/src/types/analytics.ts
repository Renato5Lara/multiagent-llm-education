export interface CourseAccessStatus {
    course_id: string
    course_code: string
    course_name: string
    is_unlocked: boolean
    prerequisites_met: boolean
    missing_prerequisites: MissingPrerequisite[]
    completed_prerequisites: CompletedPrerequisite[]
    reason: string | null
}

interface MissingPrerequisite {
    course_id: string
    code: string
    name: string
    status: 'enrolled' | 'not_started'
}

interface CompletedPrerequisite {
    course_id: string
    code: string
    name: string
}

export interface CurriculumCourseStatus {
    course_id: string
    course_code: string
    course_name: string
    cycle: number
    is_enrolled: boolean
    is_completed: boolean
    is_unlocked: boolean
    progress_percentage: number
    prerequisite_codes: string[]
    missing_prerequisites: MissingPrerequisite[]
}

export interface StudentRiskPrediction {
    risk_level: string
    risk_score: number
    explanation: string
    factors: string[]
    recommendations: string[]
}

export interface CourseAnalytics {
    course_id: string
    course_name: string
    enrolled_count: number
    avg_progress: number
    at_risk_count: number
    difficult_topics: string[]
    competency_gaps: string[]
    recommendation: string | null
}

export interface IADashboardResponse {
    student_risk: StudentRiskPrediction | null
    course_analytics: CourseAnalytics[]
    next_recommended_course: { course_id: string; course_code: string; course_name: string; cycle: number } | null
    strengths: string[]
    warnings: string[]
    curriculum_status: CurriculumCourseStatus[]
    stats: {
        total: number
        enrolled: number
        completed: number
        blocked: number
        progress_percentage: number
    }
}

export interface DocenteAnalyticsResponse {
    course_analytics: CourseAnalytics[]
    total_students: number
    total_at_risk: number
    general_issues: string[]
}
