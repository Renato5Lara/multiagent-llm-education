import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from '@/stores/authStore'

// Auth
import ProtectedRoute from '@/components/auth/ProtectedRoute'

// Layouts
import AdminLayout from '@/components/layout/AdminLayout'
import DocenteLayout from '@/components/layout/DocenteLayout'
import EstudianteLayout from '@/components/layout/EstudianteLayout'

// Pages
import Login from '@/pages/Login'
import NotFound from '@/pages/NotFound'

// Admin
import AdminDashboard from '@/pages/admin/Dashboard'
import AdminUsers from '@/pages/admin/Users'
import AdminRoles from '@/pages/admin/Roles'

// Docente
import DocenteDashboard from '@/pages/docente/Dashboard'
import DocenteCourses from '@/pages/docente/Courses'
import CourseDetail from '@/pages/docente/CourseDetail'

// Estudiante
import EstudianteDashboard from '@/pages/estudiante/Dashboard'
import DiagnosticTest from '@/pages/estudiante/DiagnosticTest'
import LearningPath from '@/pages/estudiante/LearningPath'
import ContentViewer from '@/pages/estudiante/ContentViewer'
import Evaluation from '@/pages/estudiante/Evaluation'

function RootRedirect() {
    const { isAuthenticated, user } = useAuthStore()
    if (!isAuthenticated || !user) return <Navigate to="/login" replace />
    if (user.role === 'admin') return <Navigate to="/admin" replace />
    if (user.role === 'docente') return <Navigate to="/docente" replace />
    if (user.role === 'estudiante') return <Navigate to="/estudiante" replace />
    if (user.role === 'investigador') return <Navigate to="/investigador" replace />
    return <Navigate to="/login" replace />
}

export default function App() {
    return (
        <Routes>
            {/* Public */}
            <Route path="/login" element={<Login />} />
            <Route path="/" element={<RootRedirect />} />

            {/* Admin */}
            <Route element={<ProtectedRoute allowedRoles={['admin']} />}>
                <Route element={<AdminLayout />}>
                    <Route path="/admin" element={<AdminDashboard />} />
                    <Route path="/admin/users" element={<AdminUsers />} />
                    <Route path="/admin/roles" element={<AdminRoles />} />
                </Route>
            </Route>

            {/* Docente */}
            <Route element={<ProtectedRoute allowedRoles={['docente']} />}>
                <Route element={<DocenteLayout />}>
                    <Route path="/docente" element={<DocenteDashboard />} />
                    <Route path="/docente/courses" element={<DocenteCourses />} />
                    <Route path="/docente/courses/:id" element={<CourseDetail />} />
                </Route>
            </Route>

            {/* Estudiante */}
            <Route element={<ProtectedRoute allowedRoles={['estudiante']} />}>
                <Route element={<EstudianteLayout />}>
                    <Route path="/estudiante" element={<EstudianteDashboard />} />
                    <Route path="/estudiante/diagnostic/:courseId" element={<DiagnosticTest />} />
                    <Route path="/estudiante/path/:courseId" element={<LearningPath />} />
                    <Route path="/estudiante/content/:resourceId" element={<ContentViewer />} />
                    <Route path="/estudiante/evaluation/:courseId" element={<Evaluation />} />
                </Route>
            </Route>

            {/* Investigador placeholder */}
            <Route element={<ProtectedRoute allowedRoles={['investigador']} />}>
                <Route path="/investigador" element={
                    <div className="min-h-screen flex items-center justify-center bg-gray-50">
                        <div className="text-center">
                            <h1 className="text-2xl font-bold mb-2">Panel del Investigador</h1>
                            <p className="text-muted-foreground">Disponible en Fase 4</p>
                        </div>
                    </div>
                } />
            </Route>

            {/* 404 */}
            <Route path="/404" element={<NotFound />} />
            <Route path="*" element={<Navigate to="/404" replace />} />
        </Routes>
    )
}
