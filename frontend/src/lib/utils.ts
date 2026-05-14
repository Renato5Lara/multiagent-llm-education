import { type ClassValue, clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'
import type { UserRole } from '@/types/auth'

export function cn(...inputs: ClassValue[]) {
    return twMerge(clsx(inputs))
}

export function formatDate(date: string | Date) {
    return new Intl.DateTimeFormat('es-PE', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
    }).format(new Date(date))
}

export function formatFileSize(bytes: number): string {
    if (bytes === 0) return '0 B'
    const k = 1024
    const sizes = ['B', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`
}

export function getRoleLabel(role: UserRole): string {
    const labels: Record<UserRole, string> = {
        admin: 'Administrador',
        docente: 'Docente',
        estudiante: 'Estudiante',
        investigador: 'Investigador',
    }
    return labels[role] ?? role
}

export function getRoleBadgeColor(role: UserRole): string {
    const colors: Record<UserRole, string> = {
        admin: 'bg-red-100 text-red-700',
        docente: 'bg-blue-100 text-blue-700',
        estudiante: 'bg-green-100 text-green-700',
        investigador: 'bg-purple-100 text-purple-700',
    }
    return colors[role] ?? 'bg-gray-100 text-gray-700'
}

export function getInitials(firstName: string, lastName: string): string {
    return `${firstName.charAt(0)}${lastName.charAt(0)}`.toUpperCase()
}

export function getResourceIcon(mimeType: string): string {
    if (mimeType === 'application/pdf') return 'file-text'
    if (mimeType.startsWith('video/')) return 'video'
    if (mimeType.startsWith('image/')) return 'image'
    if (mimeType.startsWith('text/')) return 'file'
    return 'file'
}
