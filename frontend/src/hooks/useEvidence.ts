import { useQuery } from '@tanstack/react-query'
import api from '@/lib/api'

export interface StudentTrajectoryDiagnostic {
    dominant_modality: string | null
    confidence: number | null
    completed_at: string | null
}

export interface StudentTrajectoryModule {
    id: string
    title: string
    order: number
    status: string
    score: number | null
    completed_at: string | null
}

export interface StudentTrajectoryEvaluation {
    id: string
    module_id: string | null
    module_title: string | null
    score: number | null
    max_score: number
    passed: boolean
    attempted_at: string | null
}

export interface StudentTrajectoryEvidence {
    id: string
    voter_name: string
    module_id: string | null
    module_title: string | null
    memory_type: string
    key: string
    value: unknown
    confidence: number
    created_at: string | null
}

export interface StudentTrajectory {
    student: { id: string; first_name: string; last_name: string; email: string }
    course_id: string | null
    summary: {
        dominant_modality: string | null
        confidence: number | null
        total_modules: number
        completed_modules: number
        avg_evaluation_score: number | null
        persisted_evidence_count: number
        agents_involved: string[]
    }
    diagnostic: StudentTrajectoryDiagnostic | null
    modules: StudentTrajectoryModule[]
    evaluations: StudentTrajectoryEvaluation[]
    evidence: StudentTrajectoryEvidence[]
}

// Única fuente de datos del Modo Evidencia — ver evidence_service.py.
export function useStudentTrajectory(studentId: string | undefined) {
    return useQuery({
        queryKey: ['evidence', 'trajectory', studentId],
        queryFn: async () => {
            const resp = await api.get<StudentTrajectory>(`/api/evidence/student/${studentId}/trajectory`)
            return resp.data
        },
        enabled: !!studentId,
    })
}
