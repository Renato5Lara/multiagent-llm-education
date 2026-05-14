import { useState } from 'react'
import { Loader2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { useCreateUser, useUpdateUser } from '@/hooks/useUsers'
import type { User } from '@/types/user'
import type { UserRole } from '@/types/auth'

interface Props { user?: User | null; onSuccess: () => void }

export default function UserForm({ user, onSuccess }: Props) {
    const isEdit = !!user
    const create = useCreateUser()
    const update = useUpdateUser()
    const [form, setForm] = useState({
        email: user?.email ?? '', first_name: user?.first_name ?? '',
        last_name: user?.last_name ?? '', role: (user?.role ?? 'estudiante') as UserRole,
        password: '', institutional_code: user?.institutional_code ?? '', area: user?.area ?? '',
    })
    const [errors, setErrors] = useState<Record<string, string>>({})

    const validate = () => {
        const e: Record<string, string> = {}
        if (!form.email) e.email = 'Requerido'
        if (!form.first_name) e.first_name = 'Requerido'
        if (!form.last_name) e.last_name = 'Requerido'
        if (!isEdit && !form.password) e.password = 'Requerido'
        if (form.password && form.password.length < 6) e.password = 'Mínimo 6 caracteres'
        setErrors(e); return Object.keys(e).length === 0
    }

    const handleSubmit = (ev: React.FormEvent) => {
        ev.preventDefault()
        if (!validate()) return
        if (isEdit && user) {
            const d: Record<string, string | undefined> = { email: form.email, first_name: form.first_name, last_name: form.last_name, institutional_code: form.institutional_code || undefined, area: form.area || undefined }
            if (form.password) d.password = form.password
            update.mutate({ id: user.id, data: d }, { onSuccess })
        } else {
            create.mutate({ email: form.email, password: form.password, first_name: form.first_name, last_name: form.last_name, role: form.role, institutional_code: form.institutional_code || undefined, area: form.area || undefined }, { onSuccess })
        }
    }

    const pending = create.isPending || update.isPending
    const set = (k: string, v: string) => setForm(f => ({ ...f, [k]: v }))

    return (
        <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                    <Label>Nombre *</Label>
                    <Input value={form.first_name} onChange={e => set('first_name', e.target.value)} className={errors.first_name ? 'border-red-500' : ''} />
                    {errors.first_name && <p className="text-xs text-red-500">{errors.first_name}</p>}
                </div>
                <div className="space-y-2">
                    <Label>Apellido *</Label>
                    <Input value={form.last_name} onChange={e => set('last_name', e.target.value)} className={errors.last_name ? 'border-red-500' : ''} />
                    {errors.last_name && <p className="text-xs text-red-500">{errors.last_name}</p>}
                </div>
            </div>
            <div className="space-y-2">
                <Label>Email *</Label>
                <Input type="email" value={form.email} onChange={e => set('email', e.target.value)} className={errors.email ? 'border-red-500' : ''} />
                {errors.email && <p className="text-xs text-red-500">{errors.email}</p>}
            </div>
            <div className="space-y-2">
                <Label>{isEdit ? 'Nueva contraseña' : 'Contraseña *'}</Label>
                <Input type="password" value={form.password} onChange={e => set('password', e.target.value)} className={errors.password ? 'border-red-500' : ''} />
                {errors.password && <p className="text-xs text-red-500">{errors.password}</p>}
            </div>
            {!isEdit && (
                <div className="space-y-2">
                    <Label>Rol *</Label>
                    <Select value={form.role} onValueChange={v => set('role', v)}>
                        <SelectTrigger><SelectValue /></SelectTrigger>
                        <SelectContent>
                            <SelectItem value="admin">Administrador</SelectItem>
                            <SelectItem value="docente">Docente</SelectItem>
                            <SelectItem value="estudiante">Estudiante</SelectItem>
                            <SelectItem value="investigador">Investigador</SelectItem>
                        </SelectContent>
                    </Select>
                </div>
            )}
            <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2"><Label>Código institucional</Label><Input value={form.institutional_code} onChange={e => set('institutional_code', e.target.value)} /></div>
                <div className="space-y-2"><Label>Área</Label><Input value={form.area} onChange={e => set('area', e.target.value)} /></div>
            </div>
            <div className="flex justify-end pt-2">
                <Button type="submit" disabled={pending}>
                    {pending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                    {isEdit ? 'Guardar' : 'Crear'}
                </Button>
            </div>
        </form>
    )
}
