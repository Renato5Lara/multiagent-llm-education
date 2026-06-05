import { lazy, Suspense } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from '@/stores/authStore'
import { LoadingScreen } from '@/components/auth/ProtectedRoute'

import ProtectedRoute from '@/components/auth/ProtectedRoute'
import AcademicGuard from '@/components/auth/AcademicGuard'
import AdminLayout from '@/components/layout/AdminLayout'
import DocenteLayout from '@/components/layout/DocenteLayout'
import EstudianteLayout from '@/components/layout/EstudianteLayout'
import InvestigadorLayout from '@/components/layout/InvestigadorLayout'

import Login from '@/pages/Login'
import NotFound from '@/pages/NotFound'

const AdminDashboard = lazy(() => import('@/pages/admin/Dashboard'))
const AdminUsers = lazy(() => import('@/pages/admin/Users'))
const AdminRoles = lazy(() => import('@/pages/admin/Roles'))

const DocenteDashboard = lazy(() => import('@/pages/docente/Dashboard'))
const DocenteCourses = lazy(() => import('@/pages/docente/Courses'))
const CourseDetail = lazy(() => import('@/pages/docente/CourseDetail'))
const DocenteAnalytics = lazy(() => import('@/pages/docente/Analytics'))

const EstudianteDashboard = lazy(() => import('@/pages/estudiante/Dashboard'))
const EstudianteOnboarding = lazy(() => import('@/pages/estudiante/Onboarding'))
const DiagnosticTest = lazy(() => import('@/pages/estudiante/DiagnosticTest'))
const LearningPath = lazy(() => import('@/pages/estudiante/LearningPath'))
const ContentViewer = lazy(() => import('@/pages/estudiante/ContentViewer'))
const ModuleLearningView = lazy(() => import('@/pages/estudiante/ModuleLearningView'))
const Evaluation = lazy(() => import('@/pages/estudiante/Evaluation'))
const SwarmDemo = lazy(() => import('@/pages/demo/SwarmDemo'))
const ReplayDashboard = lazy(() => import('@/pages/replay/ReplayDashboard'))
const InvestigadorDashboard = lazy(() => import('@/pages/investigador/Dashboard'))

function RootRedirect() {
    const { isAuthenticated, user } = useAuthStore()
    if (!isAuthenticated || !user) return <Navigate to="/login" replace />
    const home = `/${user.role}`
    return <Navigate to={home} replace />
}

export default function App() {
    return (
        <Suspense fallback={<LoadingScreen />}>
            <Routes>
                <Route path="/login" element={<Login />} />
                <Route path="/swarm-demo" element={<SwarmDemo />} />
                <Route path="/replay" element={<ReplayDashboard />} />
                <Route path="/" element={<RootRedirect />} />

                <Route element={<ProtectedRoute allowedRoles={['admin']} />}>
                    <Route element={<AdminLayout />}>
                        <Route path="/admin" element={<AdminDashboard />} />
                        <Route path="/admin/users" element={<AdminUsers />} />
                        <Route path="/admin/roles" element={<AdminRoles />} />
                    </Route>
                </Route>

                <Route element={<ProtectedRoute allowedRoles={['docente']} />}>
                    <Route element={<DocenteLayout />}>
                        <Route path="/docente" element={<DocenteDashboard />} />
                        <Route path="/docente/courses" element={<DocenteCourses />} />
                        <Route path="/docente/courses/:id" element={<CourseDetail />} />
                        <Route path="/docente/analytics" element={<DocenteAnalytics />} />
                    </Route>
                </Route>

                <Route element={<ProtectedRoute allowedRoles={['estudiante']} />}>
                    <Route path="/estudiante/onboarding" element={<EstudianteOnboarding />} />
                    <Route element={<AcademicGuard />}>
                        <Route element={<EstudianteLayout />}>
                            <Route path="/estudiante" element={<EstudianteDashboard />} />
                            <Route path="/estudiante/diagnostic/:courseId" element={<DiagnosticTest />} />
                            <Route path="/estudiante/path/:courseId" element={<LearningPath />} />
                            <Route path="/estudiante/content/:resourceId" element={<ContentViewer />} />
                            <Route path="/estudiante/module/:moduleId" element={<ModuleLearningView />} />
                            <Route path="/estudiante/evaluation/:courseId" element={<Evaluation />} />
                        </Route>
                    </Route>
                </Route>

                <Route element={<ProtectedRoute allowedRoles={['investigador']} />}>
                    <Route element={<InvestigadorLayout />}>
                        <Route path="/investigador" element={<InvestigadorDashboard />} />
                    </Route>
                </Route>

                <Route path="/404" element={<NotFound />} />
                <Route path="*" element={<Navigate to="/404" replace />} />
            </Routes>
        </Suspense>
    )
}
