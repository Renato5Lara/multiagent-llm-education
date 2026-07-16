import { useEffect, useState } from 'react'
import { Outlet, useLocation } from 'react-router-dom'
import { LayoutDashboard, BookOpen } from 'lucide-react'
import Sidebar, { type SidebarItem } from './Sidebar'
import Header from './Header'
import TutorWidget from '@/components/ai/TutorWidget'
import { useMyCourses } from '@/hooks/useStudent'

// DEBUG-DIAG-LOOP (temporal — quitar tras capturar una ocurrencia real):
function debugDiagLog(event: string, extra?: Record<string, unknown>) {
  // eslint-disable-next-line no-console
  console.log(`[DEBUG-DIAG-LOOP] ${new Date().toISOString()} EstudianteLayout:${event}`, extra ?? '')
}

function findActiveExperienceId(courses: { course_id: string; is_active_experience: boolean }[] | undefined) {
  return courses?.find(c => c.is_active_experience)?.course_id
}

interface OpenTutorDetail {
  courseId?: string
  courseName?: string
  moduleTitle?: string
  bloomLevel?: number
}

export default function EstudianteLayout() {
  const { data: courses } = useMyCourses()
  const fdpId = findActiveExperienceId(courses)
  const location = useLocation()

  useEffect(() => {
    debugDiagLog('route-change', { pathname: location.pathname })
  }, [location.pathname])

  const [tutorConfig, setTutorConfig] = useState<{
    courseId: string
    courseName?: string
    moduleTitle?: string
    bloomLevel?: number
  } | null>(null)

  useEffect(() => {
    const handler = (e: Event) => {
      const detail = (e as CustomEvent<OpenTutorDetail>).detail
      if (detail?.courseId) {
        setTutorConfig({
          courseId: detail.courseId,
          courseName: detail.courseName,
          moduleTitle: detail.moduleTitle,
          bloomLevel: detail.bloomLevel,
        })
      }
    }
    window.addEventListener('open-tutor', handler)
    return () => window.removeEventListener('open-tutor', handler)
  }, [])

  const sidebarItems: SidebarItem[] = [
    { label: 'Mi Aprendizaje',      href: '/estudiante',                                  icon: LayoutDashboard },
    { label: 'Ruta de Aprendizaje', href: fdpId ? `/estudiante/path/${fdpId}` : '#',     icon: BookOpen, disabled: !fdpId },
  ]

  return (
    <div className="min-h-screen bg-neural-surface">
      <Sidebar items={sidebarItems} />
      <div className="lg:ml-64">
        <Header />
        <main className="p-4 md:p-6 pt-16 lg:pt-6">
          <Outlet />
        </main>
      </div>
      <TutorWidget
        courseId={tutorConfig?.courseId || ''}
        courseName={tutorConfig?.courseName}
        moduleTitle={tutorConfig?.moduleTitle}
        bloomLevel={tutorConfig?.bloomLevel}
      />
    </div>
  )
}
