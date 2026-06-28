import { AlertTriangle, Shield, ShieldCheck, ShieldAlert, Lightbulb } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import type { StudentRiskPrediction } from '@/types/analytics'

interface Props {
    risk: StudentRiskPrediction | null
}

const RISK_CONFIG = {
    bajo: {
        icon: ShieldCheck,
        color: 'text-neural-pulse',
        bg: 'bg-neural-pulse/[0.05]',
        border: 'border-neural-pulse/20',
        badge: 'bg-neural-pulse/10 text-neural-pulse',
        label: 'Riesgo Bajo',
    },
    medio: {
        icon: Shield,
        color: 'text-amber-400',
        bg: 'bg-amber-400/[0.05]',
        border: 'border-amber-400/20',
        badge: 'bg-amber-400/10 text-amber-400',
        label: 'Riesgo Medio',
    },
    alto: {
        icon: ShieldAlert,
        color: 'text-red-400',
        bg: 'bg-red-400/[0.05]',
        border: 'border-red-400/20',
        badge: 'bg-red-400/10 text-red-400',
        label: 'Riesgo Alto',
    },
}

export default function RiskCard({ risk }: Props) {
    if (!risk) return null

    const config = RISK_CONFIG[risk.risk_level as keyof typeof RISK_CONFIG] || RISK_CONFIG.medio
    const Icon = config.icon

    return (
        <Card className={`border ${config.border} ${config.bg}`}>
            <CardHeader className="pb-2">
                <div className="flex items-center justify-between">
                    <CardTitle className="text-sm flex items-center gap-2">
                        <Icon className={`h-5 w-5 ${config.color}`} />
                        Predicción Académica
                    </CardTitle>
                    <Badge className={config.badge}>{config.label}</Badge>
                </div>
            </CardHeader>
            <CardContent className="space-y-3">
                <p className="text-sm text-muted-foreground">{risk.explanation}</p>

                {risk.factors.length > 0 && (
                    <div>
                        <p className="text-xs font-medium text-muted-foreground mb-1 flex items-center gap-1">
                            <AlertTriangle className="h-3 w-3" /> Factores detectados
                        </p>
                        <ul className="space-y-0.5">
                            {risk.factors.map((f, i) => (
                                <li key={i} className="text-xs text-muted-foreground flex items-start gap-1">
                                    <span className="text-amber-500 mt-0.5">•</span>
                                    {f}
                                </li>
                            ))}
                        </ul>
                    </div>
                )}

                {risk.recommendations.length > 0 && (
                    <div>
                        <p className="text-xs font-medium text-muted-foreground mb-1 flex items-center gap-1">
                            <Lightbulb className="h-3 w-3" /> Recomendaciones
                        </p>
                        <ul className="space-y-0.5">
                            {risk.recommendations.map((r, i) => (
                                <li key={i} className="text-xs text-muted-foreground flex items-start gap-1">
                                    <span className="text-primary mt-0.5">•</span>
                                    {r}
                                </li>
                            ))}
                        </ul>
                    </div>
                )}
            </CardContent>
        </Card>
    )
}
