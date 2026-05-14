import { ReactNode } from 'react'

interface PageHeaderProps {
    title: string
    description?: string
    children?: ReactNode
}

export default function PageHeader({ title, description, children }: PageHeaderProps) {
    return (
        <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between mb-8">
            <div>
                <h1 className="text-2xl font-bold tracking-tight text-gray-900">{title}</h1>
                {description && (
                    <p className="text-muted-foreground mt-1">{description}</p>
                )}
            </div>
            {children && <div className="flex items-center gap-2 mt-4 sm:mt-0">{children}</div>}
        </div>
    )
}
