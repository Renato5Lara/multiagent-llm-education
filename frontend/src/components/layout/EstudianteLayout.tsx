import { useEffect, useState } from 'react'
import { Outlet } from 'react-router-dom'
import { LayoutDashboard, BookOpen, Code2, Activity, Settings } from 'lucide-react'
import Sidebar, { type SidebarItem } from './Sidebar'
import Header from './Header'
import TutorWidget from '@/components/ai/TutorWidget'

const estudianteItems: SidebarItem[] = [
  { label: 'Dashboard',      href: '/estudiante', icon: LayoutDashboard },
  { label: 'Learning Path',  href: '#',           icon: BookOpen,        disabled: true },
  { label: 'Code Lab',       href: '#',           icon: Code2,           disabled: true },
  { label: 'Swarm Monitor',  href: '#',           icon: Activity,        disabled: true },
  { label: 'Settings',       href: '#',           icon: Settings,        disabled: true, sectionBefore: true },
]

interface OpenTutorDetail {
  courseId?: string
  courseName?: string
  moduleTitle?: string
  bloomLevel?: number
}

export default function EstudianteLayout() {
  const [tutorConfig, setTutorConfig] = useState<{
    courseId: string
    courseName?: string
    bloomLevel?: number
  } | null>(null)

  useEffect(() => {
    const handler = (e: Event) => {
      const detail = (e as CustomEvent<OpenTutorDetail>).detail
      if (detail?.courseId) {
        setTutorConfig({ courseId: detail.courseId, courseName: detail.courseName, bloomLevel: detail.bloomLevel })
      }
    }
    window.addEventListener('open-tutor', handler)
    return () => window.removeEventListener('open-tutor', handler)
  }, [])

  return (
    <div className="min-h-screen bg-neural-surface">
      <Sidebar items={estudianteItems} />
      <div className="lg:ml-64">
        <Header />
        <main className="p-4 md:p-6 pt-16 lg:pt-6">
          <Outlet />
        </main>
      </div>
      <TutorWidget
        courseId={tutorConfig?.courseId || ''}
        courseName={tutorConfig?.courseName}
        bloomLevel={tutorConfig?.bloomLevel}
      />
    </div>
  )
}
