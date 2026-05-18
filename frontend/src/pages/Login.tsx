import { useState } from 'react'
import { Navigate } from 'react-router-dom'
import { Eye, EyeOff, GraduationCap, Loader2 } from 'lucide-react'
import { useAuth } from '@/hooks/useAuth'
import { useAuthStore } from '@/stores/authStore'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'

export default function Login() {
    const { isAuthenticated, user } = useAuthStore()
    const { login, isLoggingIn } = useAuth()
    const [identifier, setIdentifier] = useState('')
    const [password, setPassword] = useState('')
    const [showPassword, setShowPassword] = useState(false)
    const [errors, setErrors] = useState<{ identifier?: string; password?: string }>({})

    // If already authenticated, redirect to role-based home
    if (isAuthenticated && user) {
        const home = user.role === 'admin' ? '/admin' : `/${user.role}`
        return <Navigate to={home} replace />
    }

    const validate = () => {
        const newErrors: typeof errors = {}
        if (!identifier) newErrors.identifier = 'El correo o código es obligatorio'
        if (!password) newErrors.password = 'La contraseña es obligatoria'
        else if (password.length < 6) newErrors.password = 'Mínimo 6 caracteres'
        setErrors(newErrors)
        return Object.keys(newErrors).length === 0
    }

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault()
        if (validate()) {
            login({ identifier, password })
        }
    }

    return (
        <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-[#001a3a] via-[#003D7A] to-[#00509e] relative overflow-hidden">
            {/* Background decorative elements */}
            <div className="absolute inset-0">
                <div className="absolute top-0 left-0 w-96 h-96 bg-secondary/10 rounded-full blur-3xl -translate-x-1/2 -translate-y-1/2" />
                <div className="absolute bottom-0 right-0 w-96 h-96 bg-blue-400/10 rounded-full blur-3xl translate-x-1/2 translate-y-1/2" />
                <div className="absolute top-1/2 left-1/2 w-64 h-64 bg-white/5 rounded-full blur-2xl -translate-x-1/2 -translate-y-1/2" />
            </div>

            <Card className="w-full max-w-md mx-4 shadow-2xl border-0 relative z-10 bg-white/95 backdrop-blur-xl">
                <CardHeader className="text-center pb-2">
                    <div className="mx-auto w-16 h-16 rounded-2xl bg-gradient-to-br from-primary to-[#00509e] flex items-center justify-center mb-4 shadow-lg">
                        <GraduationCap className="h-9 w-9 text-white" />
                    </div>
                    <CardTitle className="text-2xl font-bold text-gray-900">UPAO-MAS-EDU</CardTitle>
                    <CardDescription className="text-sm">
                        Sistema Multiagente Educativo
                    </CardDescription>
                </CardHeader>
                <CardContent>
                    <form onSubmit={handleSubmit} className="space-y-5">
                        <div className="space-y-2">
                            <Label htmlFor="identifier">Correo o código institucional</Label>
                            <Input
                                id="identifier"
                                type="text"
                                placeholder="usuario@upao.edu.pe o 20231234"
                                value={identifier}
                                onChange={(e) => setIdentifier(e.target.value)}
                                className={errors.identifier ? 'border-red-500' : ''}
                                autoComplete="username"
                                autoFocus
                            />
                            {errors.identifier && <p className="text-xs text-red-500">{errors.identifier}</p>}
                        </div>

                        <div className="space-y-2">
                            <Label htmlFor="password">Contraseña</Label>
                            <div className="relative">
                                <Input
                                    id="password"
                                    type={showPassword ? 'text' : 'password'}
                                    placeholder="••••••••"
                                    value={password}
                                    onChange={(e) => setPassword(e.target.value)}
                                    className={errors.password ? 'border-red-500 pr-10' : 'pr-10'}
                                    autoComplete="current-password"
                                />
                                <button
                                    type="button"
                                    onClick={() => setShowPassword(!showPassword)}
                                    className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                                    tabIndex={-1}
                                >
                                    {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                                </button>
                            </div>
                            {errors.password && <p className="text-xs text-red-500">{errors.password}</p>}
                        </div>

                        <Button
                            type="submit"
                            className="w-full bg-primary hover:bg-primary/90 h-11 text-base font-semibold"
                            disabled={isLoggingIn}
                        >
                            {isLoggingIn ? (
                                <>
                                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                    Iniciando sesión...
                                </>
                            ) : (
                                'Iniciar sesión'
                            )}
                        </Button>
                    </form>

                    <div className="mt-6 text-center">
                        <p className="text-xs text-muted-foreground">
                            Universidad Privada Antenor Orrego · Trujillo, Perú
                        </p>
                    </div>
                </CardContent>
            </Card>
        </div>
    )
}
