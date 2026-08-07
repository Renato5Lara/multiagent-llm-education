import { lazy, Suspense } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from '@/stores/authStore'
import { LoadingScreen } from '@/components/auth/ProtectedRoute'

import ProtectedRoute from '@/components/auth/ProtectedRoute'
import AcademicGuard from '@/components/auth/AcademicGuard'
import PretestGuard from '@/components/auth/PretestGuard'
import AdminLayout from '@/components/layout/AdminLayout'
import DocenteLayout from '@/components/layout/DocenteLayout'
import EstudianteLayout from '@/components/layout/EstudianteLayout'
import EvidenceLayout from '@/components/layout/EvidenceLayout'

import Login from '@/pages/Login'
import NotFound from '@/pages/NotFound'

const AdminDashboard = lazy(() => import('@/pages/admin/Dashboard'))
const AdminUsers = lazy(() => import('@/pages/admin/Users'))
const AdminRoles = lazy(() => import('@/pages/admin/Roles'))
const AdminSystemStatus = lazy(() => import('@/pages/admin/SystemStatus'))

const DocenteDashboard = lazy(() => import('@/pages/docente/Dashboard'))
const DocenteCourses = lazy(() => import('@/pages/docente/Courses'))
const CourseDetail = lazy(() => import('@/pages/docente/CourseDetail'))
const DocenteAnalytics = lazy(() => import('@/pages/docente/Analytics'))
const PedagogicalPanel = lazy(() => import('@/pages/docente/PedagogicalPanel'))

const EstudianteDashboard = lazy(() => import('@/pages/estudiante/Dashboard'))
const EstudianteOnboarding = lazy(() => import('@/pages/estudiante/Onboarding'))
const DiagnosticTest = lazy(() => import('@/pages/estudiante/DiagnosticTest'))
const LearningPath = lazy(() => import('@/pages/estudiante/LearningPath'))
const ContentViewer = lazy(() => import('@/pages/estudiante/ContentViewer'))
const ModuleLearningView = lazy(() => import('@/pages/estudiante/ModuleLearningView'))
const AdaptiveLearnView = lazy(() => import('@/pages/estudiante/AdaptiveLearnView'))
const CodeLab = lazy(() => import('@/pages/estudiante/CodeLab'))
const Evaluation = lazy(() => import('@/pages/estudiante/Evaluation'))
const KnowledgeTest = lazy(() => import('@/pages/estudiante/KnowledgeTest'))
const StudentTrajectory = lazy(() => import('@/pages/replay/StudentTrajectory'))
const EvidenceHub = lazy(() => import('@/pages/evidencia/EvidenceHub'))
const ResearchDashboard = lazy(() => import('@/pages/evidencia/ResearchDashboard'))
const RuntimeConsole = lazy(() => import('@/pages/evidencia/RuntimeConsole'))

function RootRedirect() {
    const { isAuthenticated, user } = useAuthStore()
    if (!isAuthenticated || !user) return <Navigate to="/login" replace />
    // 'investigador' aterriza en Modo Evidencia — no tiene una ruta propia bajo /investigador
    const home = user.role === 'investigador' ? '/evidencia' : `/${user.role}`
    return <Navigate to={home} replace />
}

export default function App() {
    return (
        <Suspense fallback={<LoadingScreen />}>
            <Routes>
                <Route path="/login" element={<Login />} />
                {/* /swarm-demo (URL antigua, ADR-0017): sin ruta ni componente propio ya — cualquier tráfico residual cae en el catch-all de más abajo hacia /404. */}
                <Route path="/replay" element={<StudentTrajectory />} />
                <Route path="/" element={<RootRedirect />} />

                <Route element={<ProtectedRoute allowedRoles={['admin']} />}>
                    <Route element={<AdminLayout />}>
                        <Route path="/admin" element={<AdminDashboard />} />
                        <Route path="/admin/users" element={<AdminUsers />} />
                        <Route path="/admin/roles" element={<AdminRoles />} />
                        <Route path="/admin/system" element={<AdminSystemStatus />} />
                    </Route>
                </Route>

                <Route element={<ProtectedRoute allowedRoles={['docente']} />}>
                    <Route element={<DocenteLayout />}>
                        <Route path="/docente" element={<DocenteDashboard />} />
                        <Route path="/docente/courses" element={<DocenteCourses />} />
                        <Route path="/docente/courses/:id" element={<CourseDetail />} />
                        <Route path="/docente/analytics" element={<DocenteAnalytics />} />
                        <Route path="/docente/panel-pedagogico" element={<PedagogicalPanel />} />
                    </Route>
                </Route>

                <Route element={<ProtectedRoute allowedRoles={['estudiante']} />}>
                    <Route path="/estudiante/onboarding" element={<EstudianteOnboarding />} />
                    <Route element={<AcademicGuard />}>
                        <Route element={<EstudianteLayout />}>
                            <Route path="/estudiante" element={<EstudianteDashboard />} />
                            <Route path="/estudiante/diagnostic/:courseId" element={<DiagnosticTest />} />
                            <Route path="/estudiante/knowledge-test/:courseId" element={<KnowledgeTest kind="pre" />} />
                            <Route path="/estudiante/post-test/:courseId" element={<KnowledgeTest kind="post" />} />
                            <Route path="/estudiante/path/:courseId" element={<PretestGuard><LearningPath /></PretestGuard>} />
                            <Route path="/estudiante/content/:resourceId" element={<ContentViewer />} />
                            <Route path="/estudiante/module/:moduleId" element={<ModuleLearningView />} />
                            <Route path="/estudiante/learn/:topicSlug" element={<AdaptiveLearnView />} />
                            <Route path="/estudiante/codelab/:topicSlug" element={<CodeLab />} />
                            <Route path="/estudiante/evaluation/:courseId" element={<Evaluation />} />
                        </Route>
                    </Route>
                </Route>

                {/* Modo Evidencia — capacidad de observabilidad, no un rol de usuario */}
                <Route element={<EvidenceLayout />}>
                    <Route path="/evidencia" element={<EvidenceHub />} />
                    <Route path="/evidencia/investigacion" element={<ResearchDashboard />} />
                    <Route path="/evidencia/runtime" element={<RuntimeConsole />} />
                </Route>

                <Route path="/404" element={<NotFound />} />
                <Route path="*" element={<Navigate to="/404" replace />} />
            </Routes>
        </Suspense>
    )
}
