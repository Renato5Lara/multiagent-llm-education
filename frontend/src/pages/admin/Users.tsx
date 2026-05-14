import { useState } from 'react'
import { Plus, Upload, Search, MoreHorizontal, UserX, Pencil } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import {
    Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select'
import {
    Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '@/components/ui/table'
import {
    Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger,
} from '@/components/ui/dialog'
import {
    DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import PageHeader from '@/components/common/PageHeader'
import UserForm from './UserForm'
import { useUsers, useDeleteUser, useBulkUploadUsers } from '@/hooks/useUsers'
import { getRoleLabel, getRoleBadgeColor, formatDate } from '@/lib/utils'
import type { UserRole } from '@/types/auth'
import type { User } from '@/types/user'

export default function UsersPage() {
    const [page, setPage] = useState(1)
    const [roleFilter, setRoleFilter] = useState<UserRole | 'all'>('all')
    const [search, setSearch] = useState('')
    const [createOpen, setCreateOpen] = useState(false)
    const [editUser, setEditUser] = useState<User | null>(null)
    const [bulkOpen, setBulkOpen] = useState(false)

    const { data, isLoading } = useUsers({
        page,
        size: 20,
        role: roleFilter === 'all' ? null : roleFilter,
    })
    const deleteUser = useDeleteUser()
    const bulkUpload = useBulkUploadUsers()

    const filteredUsers = data?.users?.filter(u => {
        if (!search) return true
        const q = search.toLowerCase()
        return u.first_name.toLowerCase().includes(q)
            || u.last_name.toLowerCase().includes(q)
            || u.email.toLowerCase().includes(q)
    }) ?? []

    const totalPages = Math.ceil((data?.total ?? 0) / 20)

    const handleBulkUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0]
        if (file) {
            bulkUpload.mutate(file, {
                onSuccess: () => setBulkOpen(false),
            })
        }
    }

    return (
        <div>
            <PageHeader title="Gestión de Usuarios" description="Administra los usuarios del sistema">
                <Dialog open={bulkOpen} onOpenChange={setBulkOpen}>
                    <DialogTrigger asChild>
                        <Button variant="outline" size="sm">
                            <Upload className="mr-2 h-4 w-4" />
                            Carga CSV
                        </Button>
                    </DialogTrigger>
                    <DialogContent>
                        <DialogHeader>
                            <DialogTitle>Carga masiva de usuarios</DialogTitle>
                        </DialogHeader>
                        <div className="space-y-4">
                            <p className="text-sm text-muted-foreground">
                                Sube un archivo CSV con columnas: <code className="bg-gray-100 px-1 rounded">email, first_name, last_name, role, institutional_code</code>
                            </p>
                            <Input
                                type="file"
                                accept=".csv"
                                onChange={handleBulkUpload}
                                disabled={bulkUpload.isPending}
                            />
                            {bulkUpload.isPending && <p className="text-sm text-muted-foreground">Procesando...</p>}
                        </div>
                    </DialogContent>
                </Dialog>

                <Dialog open={createOpen} onOpenChange={setCreateOpen}>
                    <DialogTrigger asChild>
                        <Button size="sm">
                            <Plus className="mr-2 h-4 w-4" />
                            Nuevo usuario
                        </Button>
                    </DialogTrigger>
                    <DialogContent className="max-w-lg">
                        <DialogHeader>
                            <DialogTitle>Crear usuario</DialogTitle>
                        </DialogHeader>
                        <UserForm onSuccess={() => setCreateOpen(false)} />
                    </DialogContent>
                </Dialog>
            </PageHeader>

            {/* Filters */}
            <div className="flex gap-3 mb-6">
                <div className="relative flex-1 max-w-sm">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                    <Input
                        placeholder="Buscar por nombre o email..."
                        value={search}
                        onChange={(e) => setSearch(e.target.value)}
                        className="pl-9"
                    />
                </div>
                <Select value={roleFilter} onValueChange={(v) => { setRoleFilter(v as UserRole | 'all'); setPage(1) }}>
                    <SelectTrigger className="w-48">
                        <SelectValue placeholder="Filtrar por rol" />
                    </SelectTrigger>
                    <SelectContent>
                        <SelectItem value="all">Todos los roles</SelectItem>
                        <SelectItem value="admin">Administrador</SelectItem>
                        <SelectItem value="docente">Docente</SelectItem>
                        <SelectItem value="estudiante">Estudiante</SelectItem>
                        <SelectItem value="investigador">Investigador</SelectItem>
                    </SelectContent>
                </Select>
            </div>

            {/* Table */}
            <div className="border rounded-lg bg-white">
                <Table>
                    <TableHeader>
                        <TableRow>
                            <TableHead>Usuario</TableHead>
                            <TableHead>Email</TableHead>
                            <TableHead>Rol</TableHead>
                            <TableHead>Código</TableHead>
                            <TableHead>Estado</TableHead>
                            <TableHead>Creado</TableHead>
                            <TableHead className="w-10" />
                        </TableRow>
                    </TableHeader>
                    <TableBody>
                        {isLoading ? (
                            [...Array(5)].map((_, i) => (
                                <TableRow key={i}>
                                    {[...Array(7)].map((_, j) => (
                                        <TableCell key={j}><Skeleton className="h-5 w-full" /></TableCell>
                                    ))}
                                </TableRow>
                            ))
                        ) : filteredUsers.length === 0 ? (
                            <TableRow>
                                <TableCell colSpan={7} className="text-center py-8 text-muted-foreground">
                                    No se encontraron usuarios
                                </TableCell>
                            </TableRow>
                        ) : (
                            filteredUsers.map((user) => (
                                <TableRow key={user.id}>
                                    <TableCell>
                                        <div className="flex items-center gap-2">
                                            <div className="h-8 w-8 rounded-full bg-primary/10 flex items-center justify-center text-xs font-semibold text-primary">
                                                {user.first_name.charAt(0)}{user.last_name.charAt(0)}
                                            </div>
                                            <span className="font-medium">{user.first_name} {user.last_name}</span>
                                        </div>
                                    </TableCell>
                                    <TableCell className="text-sm text-muted-foreground">{user.email}</TableCell>
                                    <TableCell>
                                        <Badge variant="secondary" className={getRoleBadgeColor(user.role)}>
                                            {getRoleLabel(user.role)}
                                        </Badge>
                                    </TableCell>
                                    <TableCell className="text-sm">{user.institutional_code || '—'}</TableCell>
                                    <TableCell>
                                        <Badge variant={user.is_active ? 'default' : 'destructive'} className="text-xs">
                                            {user.is_active ? 'Activo' : 'Inactivo'}
                                        </Badge>
                                    </TableCell>
                                    <TableCell className="text-sm text-muted-foreground">{formatDate(user.created_at)}</TableCell>
                                    <TableCell>
                                        <DropdownMenu>
                                            <DropdownMenuTrigger asChild>
                                                <Button variant="ghost" size="sm" className="h-8 w-8 p-0">
                                                    <MoreHorizontal className="h-4 w-4" />
                                                </Button>
                                            </DropdownMenuTrigger>
                                            <DropdownMenuContent align="end">
                                                <DropdownMenuItem onClick={() => setEditUser(user)}>
                                                    <Pencil className="mr-2 h-4 w-4" />
                                                    Editar
                                                </DropdownMenuItem>
                                                <DropdownMenuItem
                                                    className="text-red-600"
                                                    onClick={() => { if (confirm('¿Desactivar este usuario?')) deleteUser.mutate(user.id) }}
                                                >
                                                    <UserX className="mr-2 h-4 w-4" />
                                                    Desactivar
                                                </DropdownMenuItem>
                                            </DropdownMenuContent>
                                        </DropdownMenu>
                                    </TableCell>
                                </TableRow>
                            ))
                        )}
                    </TableBody>
                </Table>
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
                <div className="flex items-center justify-between mt-4">
                    <p className="text-sm text-muted-foreground">
                        Mostrando página {page} de {totalPages} ({data?.total} registros)
                    </p>
                    <div className="flex gap-2">
                        <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => setPage(p => p - 1)}>
                            Anterior
                        </Button>
                        <Button variant="outline" size="sm" disabled={page >= totalPages} onClick={() => setPage(p => p + 1)}>
                            Siguiente
                        </Button>
                    </div>
                </div>
            )}

            {/* Edit Dialog */}
            <Dialog open={!!editUser} onOpenChange={(open) => { if (!open) setEditUser(null) }}>
                <DialogContent className="max-w-lg">
                    <DialogHeader>
                        <DialogTitle>Editar usuario</DialogTitle>
                    </DialogHeader>
                    {editUser && <UserForm user={editUser} onSuccess={() => setEditUser(null)} />}
                </DialogContent>
            </Dialog>
        </div>
    )
}
