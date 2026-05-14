import type { UserRole } from './auth'

export interface User {
    id: string
    email: string
    first_name: string
    last_name: string
    role: UserRole
    is_active: boolean
    institutional_code?: string
    area?: string
    created_at: string
    updated_at: string
}

export interface UserCreate {
    email: string
    password: string
    first_name: string
    last_name: string
    role: UserRole
    institutional_code?: string
    area?: string
}

export interface UserUpdate {
    email?: string
    first_name?: string
    last_name?: string
    institutional_code?: string
    area?: string
    is_active?: boolean
}

export interface UserListResponse {
    users: User[]
    total: number
    page: number
    size: number
}

export interface BulkUploadResult {
    success: number
    errors: Array<{ row: number; email: string; error: string }>
}
