import { useState } from 'react'
import { Loader2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { useCreateCourse } from '@/hooks/useCourses'

interface Props { onSuccess: () => void }

export default function CourseForm({ onSuccess }: Props) {
    const create = useCreateCourse()
    const [form, setForm] = useState({ code: '', name: '', description: '', cycle: '', year: new Date().getFullYear() })

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault()
        if (!form.code || !form.name || !form.cycle) return
        create.mutate({ code: form.code, name: form.name, description: form.description || undefined, cycle: form.cycle, year: form.year }, { onSuccess })
    }

    const set = (k: string, v: string | number) => setForm(f => ({ ...f, [k]: v }))

    return (
        <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2"><Label>Código *</Label><Input value={form.code} onChange={e => set('code', e.target.value)} placeholder="INF-301" /></div>
                <div className="space-y-2"><Label>Ciclo *</Label><Input value={form.cycle} onChange={e => set('cycle', e.target.value)} placeholder="2026-I" /></div>
            </div>
            <div className="space-y-2"><Label>Nombre *</Label><Input value={form.name} onChange={e => set('name', e.target.value)} placeholder="Ingeniería de Software I" /></div>
            <div className="space-y-2"><Label>Descripción</Label><Input value={form.description} onChange={e => set('description', e.target.value)} /></div>
            <div className="space-y-2"><Label>Año</Label><Input type="number" value={form.year} onChange={e => set('year', parseInt(e.target.value))} /></div>
            <div className="flex justify-end pt-2">
                <Button type="submit" disabled={create.isPending}>{create.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}Crear curso</Button>
            </div>
        </form>
    )
}
