import { useEffect } from 'react'
import { Loader2 } from 'lucide-react'
import { zodResolver } from '@hookform/resolvers/zod'
import { useForm } from 'react-hook-form'
import * as z from 'zod'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { useCreateUser, useUpdateUser } from '@/hooks/useUsers'
import type { User } from '@/types/user'
import type { UserRole } from '@/types/auth'

const userSchema = z.object({
    email: z.string().email('Correo inválido'),
    first_name: z.string().min(1, 'Requerido'),
    last_name: z.string().min(1, 'Requerido'),
    role: z.enum(['admin', 'docente', 'estudiante', 'investigador']),
    password: z.string().min(6, 'Mínimo 6 caracteres').optional().or(z.literal('')),
    institutional_code: z.string().optional().or(z.literal('')),
    area: z.string().optional().or(z.literal('')),
    current_cycle: z.number().min(1).max(10).optional().nullable(),
})

type UserFormData = z.infer<typeof userSchema>

interface Props { user?: User | null; onSuccess: () => void }

export default function UserForm({ user, onSuccess }: Props) {
    const isEdit = !!user
    const create = useCreateUser()
    const update = useUpdateUser()

    const { register, handleSubmit, formState: { errors }, watch, setValue, reset } = useForm<UserFormData>({
        resolver: zodResolver(userSchema),
        defaultValues: {
            email: user?.email ?? '',
            first_name: user?.first_name ?? '',
            last_name: user?.last_name ?? '',
            role: (user?.role ?? 'estudiante') as UserRole,
            password: '',
            institutional_code: user?.institutional_code ?? '',
            area: user?.area ?? '',
            current_cycle: user?.current_cycle ?? null,
        },
    })

    const role = watch('role')

    useEffect(() => {
        if (user) {
            reset({
                email: user.email,
                first_name: user.first_name,
                last_name: user.last_name,
                role: user.role,
                password: '',
                institutional_code: user.institutional_code ?? '',
                area: user.area ?? '',
                current_cycle: user.current_cycle ?? null,
            })
        }
    }, [user, reset])

    const onSubmit = (data: UserFormData) => {
        const payload = {
            ...data,
            password: data.password || undefined,
            institutional_code: data.institutional_code || undefined,
            area: data.area || undefined,
            current_cycle: data.current_cycle || undefined,
        }

        if (isEdit && user) {
            update.mutate({ id: user.id, data: payload }, { onSuccess })
        } else {
            create.mutate(payload as Parameters<typeof create.mutate>[0], { onSuccess })
        }
    }

    const pending = create.isPending || update.isPending

    return (
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                    <Label>Nombre *</Label>
                    <Input {...register('first_name')} className={errors.first_name ? 'border-red-500' : ''} />
                    {errors.first_name && <p className="text-xs text-red-500">{errors.first_name.message}</p>}
                </div>
                <div className="space-y-2">
                    <Label>Apellido *</Label>
                    <Input {...register('last_name')} className={errors.last_name ? 'border-red-500' : ''} />
                    {errors.last_name && <p className="text-xs text-red-500">{errors.last_name.message}</p>}
                </div>
            </div>
            <div className="space-y-2">
                <Label>Email *</Label>
                <Input type="email" {...register('email')} className={errors.email ? 'border-red-500' : ''} />
                {errors.email && <p className="text-xs text-red-500">{errors.email.message}</p>}
            </div>
            <div className="space-y-2">
                <Label>{isEdit ? 'Nueva contraseña' : 'Contraseña *'}</Label>
                <Input type="password" {...register('password')} className={errors.password ? 'border-red-500' : ''} />
                {errors.password && <p className="text-xs text-red-500">{errors.password.message}</p>}
            </div>
            {!isEdit && (
                <div className="space-y-2">
                    <Label>Rol *</Label>
                    <Select value={role} onValueChange={v => setValue('role', v as UserRole, { shouldValidate: true })}>
                        <SelectTrigger><SelectValue /></SelectTrigger>
                        <SelectContent>
                            <SelectItem value="admin">Administrador</SelectItem>
                            <SelectItem value="docente">Docente</SelectItem>
                            <SelectItem value="estudiante">Estudiante</SelectItem>
                            <SelectItem value="investigador">Investigador</SelectItem>
                        </SelectContent>
                    </Select>
                    {errors.role && <p className="text-xs text-red-500">{errors.role.message}</p>}
                </div>
            )}
            <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                    <Label>Código institucional</Label>
                    <Input {...register('institutional_code')} />
                </div>
                {role === 'docente' && (
                    <div className="space-y-2">
                        <Label>Área (solo docentes)</Label>
                        <Input {...register('area')} />
                    </div>
                )}
            </div>
            {role === 'estudiante' && (
                <div className="space-y-2">
                    <Label>Ciclo actual (1-10)</Label>
                    <Select
                        value={watch('current_cycle')?.toString() ?? ''}
                        onValueChange={v => setValue('current_cycle', v ? parseInt(v, 10) : null, { shouldValidate: true })}
                    >
                        <SelectTrigger><SelectValue placeholder="Seleccionar ciclo" /></SelectTrigger>
                        <SelectContent>
                            {Array.from({ length: 10 }, (_, i) => i + 1).map(c => (
                                <SelectItem key={c} value={c.toString()}>{c}</SelectItem>
                            ))}
                        </SelectContent>
                    </Select>
                    {errors.current_cycle && <p className="text-xs text-red-500">{errors.current_cycle.message}</p>}
                </div>
            )}
            <div className="flex justify-end pt-2">
                <Button type="submit" disabled={pending}>
                    {pending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                    {isEdit ? 'Guardar' : 'Crear'}
                </Button>
            </div>
        </form>
    )
}
