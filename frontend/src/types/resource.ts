export type ResourceType = 'pdf' | 'video' | 'image' | 'text' | 'document' | 'audio' | 'game' | 'interactive'

export interface Resource {
    id: string
    course_id: string
    filename: string
    original_filename: string
    mime_type: string
    size_bytes: number
    resource_type: ResourceType
    uploaded_at: string
}

export interface ResourceObjectiveAssociation {
    objective_ids: string[]
    relevance_score?: number
}
