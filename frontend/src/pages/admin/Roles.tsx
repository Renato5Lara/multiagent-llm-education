import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import PageHeader from '@/components/common/PageHeader'
import { useUsers, useChangeUserRole } from '@/hooks/useUsers'
import { getRoleLabel, getRoleBadgeColor } from '@/lib/utils'
import type { UserRole } from '@/types/auth'

export default function RolesPage() {
    const { data, isLoading } = useUsers({ page: 1, size: 100 })
    const changeRole = useChangeUserRole()
    const users = data?.users ?? []

    const handleRoleChange = (userId: string, newRole: UserRole) => {
        if (confirm('¿Confirmar cambio de rol?')) {
            changeRole.mutate({ id: userId, role: newRole })
        }
    }

    return (
        <div>
            <PageHeader title="Gestión de Roles" description="Cambia los roles de los usuarios del sistema" />
            <div className="border rounded-lg bg-white">
                <Table>
                    <TableHeader>
                        <TableRow>
                            <TableHead>Usuario</TableHead>
                            <TableHead>Email</TableHead>
                            <TableHead>Rol actual</TableHead>
                            <TableHead>Cambiar rol</TableHead>
                        </TableRow>
                    </TableHeader>
                    <TableBody>
                        {isLoading ? [...Array(5)].map((_, i) => (
                            <TableRow key={i}>{[...Array(4)].map((_, j) => <TableCell key={j}><Skeleton className="h-5 w-full" /></TableCell>)}</TableRow>
                        )) : users.length === 0 ? (
                            <TableRow><TableCell colSpan={4} className="text-center py-8 text-muted-foreground">No hay usuarios</TableCell></TableRow>
                        ) : users.map(user => (
                            <TableRow key={user.id}>
                                <TableCell className="font-medium">{user.first_name} {user.last_name}</TableCell>
                                <TableCell className="text-muted-foreground">{user.email}</TableCell>
                                <TableCell><Badge variant="secondary" className={getRoleBadgeColor(user.role)}>{getRoleLabel(user.role)}</Badge></TableCell>
                                <TableCell>
                                    <Select value={user.role} onValueChange={(v) => handleRoleChange(user.id, v as UserRole)}>
                                        <SelectTrigger className="w-44"><SelectValue /></SelectTrigger>
                                        <SelectContent>
                                            <SelectItem value="admin">Administrador</SelectItem>
                                            <SelectItem value="docente">Docente</SelectItem>
                                            <SelectItem value="estudiante">Estudiante</SelectItem>
                                            <SelectItem value="investigador">Investigador</SelectItem>
                                        </SelectContent>
                                    </Select>
                                </TableCell>
                            </TableRow>
                        ))}
                    </TableBody>
                </Table>
            </div>
        </div>
    )
}
