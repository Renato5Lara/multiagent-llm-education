import { Sparkles, AlertTriangle, TrendingUp, Target } from 'lucide-react'
import { Card, CardContent } from '@/components/ui/card'

interface Props {
    strengths: string[]
    warnings: string[]
    nextCourse: { course_id: string; course_code: string; course_name: string; cycle: number } | null
}

export default function StrengthsCard({ strengths, warnings, nextCourse }: Props) {
    return (
        <div className="grid gap-3 md:grid-cols-3 mb-4">
            {strengths.length > 0 && (
                <Card className="border-green-200 bg-green-50/30">
                    <CardContent className="p-4">
                        <div className="flex items-center gap-2 text-green-700 mb-2">
                            <Sparkles className="h-4 w-4" />
                            <span className="text-sm font-medium">Fortalezas</span>
                        </div>
                        <ul className="space-y-1">
                            {strengths.map((s, i) => (
                                <li key={i} className="text-xs text-green-600 flex items-start gap-1">
                                    <TrendingUp className="h-3 w-3 mt-0.5 shrink-0" />
                                    {s}
                                </li>
                            ))}
                        </ul>
                    </CardContent>
                </Card>
            )}

            {warnings.length > 0 && (
                <Card className="border-amber-200 bg-amber-50/30">
                    <CardContent className="p-4">
                        <div className="flex items-center gap-2 text-amber-700 mb-2">
                            <AlertTriangle className="h-4 w-4" />
                            <span className="text-sm font-medium">Alertas</span>
                        </div>
                        <ul className="space-y-1">
                            {warnings.map((w, i) => (
                                <li key={i} className="text-xs text-amber-600 flex items-start gap-1">
                                    <span className="text-amber-500 mt-0.5">•</span>
                                    {w}
                                </li>
                            ))}
                        </ul>
                    </CardContent>
                </Card>
            )}

            {nextCourse && (
                <Card className="border-blue-200 bg-blue-50/30">
                    <CardContent className="p-4">
                        <div className="flex items-center gap-2 text-blue-700 mb-2">
                            <Target className="h-4 w-4" />
                            <span className="text-sm font-medium">Próximo curso sugerido</span>
                        </div>
                        <p className="text-sm font-medium text-blue-800">{nextCourse.course_name}</p>
                        <p className="text-xs text-blue-600">{nextCourse.course_code} · Ciclo {nextCourse.cycle}°</p>
                    </CardContent>
                </Card>
            )}
        </div>
    )
}
