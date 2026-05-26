// Tipos de autenticación
export interface LoginRequest {
    identifier: string
    password: string
}

export interface TokenResponse {
    access_token: string
    refresh_token: string
    token_type: string
    user: UserAuth
}

export interface UserAuth {
    id: string
    email: string
    first_name: string
    last_name: string
    role: UserRole
    is_active: boolean
    institutional_code?: string
    area?: string
    current_cycle?: number
}

export type UserRole = 'admin' | 'docente' | 'estudiante' | 'investigador'
