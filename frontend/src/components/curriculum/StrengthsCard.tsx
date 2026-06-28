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
                <Card className="border-neural-pulse/20 bg-neural-pulse/[0.05]">
                    <CardContent className="p-4">
                        <div className="flex items-center gap-2 text-neural-pulse mb-2">
                            <Sparkles className="h-4 w-4" />
                            <span className="text-sm font-medium">Fortalezas</span>
                        </div>
                        <ul className="space-y-1">
                            {strengths.map((s, i) => (
                                <li key={i} className="text-xs text-neural-pulse/70 flex items-start gap-1">
                                    <TrendingUp className="h-3 w-3 mt-0.5 shrink-0" />
                                    {s}
                                </li>
                            ))}
                        </ul>
                    </CardContent>
                </Card>
            )}

            {warnings.length > 0 && (
                <Card className="border-amber-400/20 bg-amber-400/[0.05]">
                    <CardContent className="p-4">
                        <div className="flex items-center gap-2 text-amber-400 mb-2">
                            <AlertTriangle className="h-4 w-4" />
                            <span className="text-sm font-medium">Alertas</span>
                        </div>
                        <ul className="space-y-1">
                            {warnings.map((w, i) => (
                                <li key={i} className="text-xs text-amber-400/70 flex items-start gap-1">
                                    <span className="text-amber-400/60 mt-0.5">•</span>
                                    {w}
                                </li>
                            ))}
                        </ul>
                    </CardContent>
                </Card>
            )}

            {nextCourse && (
                <Card className="border-neural-glow/20 bg-neural-glow/[0.05]">
                    <CardContent className="p-4">
                        <div className="flex items-center gap-2 text-neural-glow mb-2">
                            <Target className="h-4 w-4" />
                            <span className="text-sm font-medium">Próximo curso sugerido</span>
                        </div>
                        <p className="text-sm font-medium text-neural-text">{nextCourse.course_name}</p>
                        <p className="text-xs text-neural-glow/60">{nextCourse.course_code} · Ciclo {nextCourse.cycle}°</p>
                    </CardContent>
                </Card>
            )}
        </div>
    )
}
