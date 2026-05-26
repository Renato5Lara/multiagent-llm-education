import { useState, useEffect } from 'react'
import { Outlet } from 'react-router-dom'
import { LayoutDashboard, BarChart3 } from 'lucide-react'
import Sidebar, { type SidebarItem } from './Sidebar'
import Header from './Header'
import TutorWidget from '@/components/ai/TutorWidget'

const estudianteItems: SidebarItem[] = [
  { label: 'Dashboard', href: '/estudiante', icon: LayoutDashboard },
  { label: 'Progreso', href: '/estudiante/progress', icon: BarChart3 },
]

export default function EstudianteLayout() {
  const [tutorConfig, setTutorConfig] = useState<{
    courseId: string
    courseName?: string
    moduleTitle?: string
    bloomLevel?: number
  } | null>(null)

  useEffect(() => {
    const handler = (e: Event) => {
      const detail = (e as CustomEvent).detail
      if (detail?.courseId) {
        setTutorConfig({ courseId: detail.courseId, courseName: detail.courseName, moduleTitle: detail.moduleTitle, bloomLevel: detail.bloomLevel })
      }
    }
    window.addEventListener('open-tutor' as any, handler)
    return () => window.removeEventListener('open-tutor' as any, handler)
  }, [])

  return (
    <div className="min-h-screen bg-gray-50">
      <Sidebar items={estudianteItems} />
      <div className="lg:ml-64">
        <Header />
        <main className="p-4 md:p-6 pt-16 lg:pt-6">
          <Outlet />
        </main>
      </div>
      {tutorConfig && (
        <TutorWidget
          courseId={tutorConfig.courseId}
          courseName={tutorConfig.courseName}
          moduleTitle={tutorConfig.moduleTitle}
          bloomLevel={tutorConfig.bloomLevel}
        />
      )}
    </div>
  )
}
