import { useState } from 'react'
import { Loader2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { useCreateCourse } from '@/hooks/useCourses'
import { useCurriculumCourses } from '@/hooks/useCurriculum'

interface Props { onSuccess: () => void }

export default function CourseForm({ onSuccess }: Props) {
    const create = useCreateCourse()
    const [form, setForm] = useState({ code: '', name: '', description: '', cycle: 3, year: new Date().getFullYear() })
    const { data: curriculumCourses } = useCurriculumCourses()
    const [selectedInstId, setSelectedInstId] = useState('')
    const [mode, setMode] = useState<'manual' | 'curriculum'>('manual')

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault()
        if (!form.code || !form.name || !form.cycle) return
        create.mutate({ code: form.code, name: form.name, description: form.description || undefined, cycle: form.cycle, year: form.year }, { onSuccess })
    }

    const handleSelectCurriculum = () => {
        if (!selectedInstId || !curriculumCourses) return
        const c = curriculumCourses.find(x => x.id === selectedInstId)
        if (!c) return
        create.mutate({
            code: c.code,
            name: c.name,
            cycle: c.cycle,
            year: new Date().getFullYear(),
            institutional_course_id: c.id,
        }, { onSuccess })
    }

    const set = (k: string, v: string | number) => setForm(f => ({ ...f, [k]: v }))

    return (
        <Tabs value={mode} onValueChange={v => setMode(v as 'manual' | 'curriculum')}>
            <TabsList className="w-full mb-4">
                <TabsTrigger value="manual" className="flex-1">Manual</TabsTrigger>
                <TabsTrigger value="curriculum" className="flex-1">De la malla</TabsTrigger>
            </TabsList>

            <TabsContent value="manual">
                <form onSubmit={handleSubmit} className="space-y-4">
                    <div className="grid grid-cols-2 gap-4">
                        <div className="space-y-2"><Label>Código *</Label><Input value={form.code} onChange={e => set('code', e.target.value)} placeholder="IS-301" /></div>
                        <div className="space-y-2"><Label>Ciclo *</Label>
                            <Select value={String(form.cycle)} onValueChange={v => set('cycle', parseInt(v))}>
                                <SelectTrigger><SelectValue /></SelectTrigger>
                                <SelectContent>
                                    {[1,2,3,4,5,6,7,8,9,10].map(c => <SelectItem key={c} value={String(c)}>Ciclo {c}</SelectItem>)}
                                </SelectContent>
                            </Select>
                        </div>
                    </div>
                    <div className="space-y-2"><Label>Nombre *</Label><Input value={form.name} onChange={e => set('name', e.target.value)} placeholder="Fundamentos de Programación" /></div>
                    <div className="space-y-2"><Label>Descripción</Label><Input value={form.description} onChange={e => set('description', e.target.value)} /></div>
                    <div className="space-y-2"><Label>Año</Label><Input type="number" value={form.year} onChange={e => set('year', parseInt(e.target.value))} /></div>
                    <div className="flex justify-end pt-2">
                        <Button type="submit" disabled={create.isPending}>{create.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}Crear curso</Button>
                    </div>
                </form>
            </TabsContent>

            <TabsContent value="curriculum">
                <div className="space-y-4">
                    <div className="space-y-2">
                        <Label>Curso de la malla curricular *</Label>
                        <Select value={selectedInstId} onValueChange={setSelectedInstId}>
                            <SelectTrigger><SelectValue placeholder="Seleccionar curso..." /></SelectTrigger>
                            <SelectContent>
                                {curriculumCourses?.map(c => (
                                    <SelectItem key={c.id} value={c.id}>
                                        [{c.code}] Ciclo {c.cycle} — {c.name} ({c.credits} créd.)
                                    </SelectItem>
                                ))}
                            </SelectContent>
                        </Select>
                    </div>
                    <div className="flex justify-end pt-2">
                        <Button onClick={handleSelectCurriculum} disabled={!selectedInstId || create.isPending}>
                            {create.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                            Crear desde malla
                        </Button>
                    </div>
                </div>
            </TabsContent>
        </Tabs>
    )
}
