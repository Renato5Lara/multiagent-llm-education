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
        color: 'text-green-600',
        bg: 'bg-green-50',
        border: 'border-green-200',
        badge: 'bg-green-100 text-green-700',
        label: 'Riesgo Bajo',
    },
    medio: {
        icon: Shield,
        color: 'text-amber-600',
        bg: 'bg-amber-50',
        border: 'border-amber-200',
        badge: 'bg-amber-100 text-amber-700',
        label: 'Riesgo Medio',
    },
    alto: {
        icon: ShieldAlert,
        color: 'text-red-600',
        bg: 'bg-red-50',
        border: 'border-red-200',
        badge: 'bg-red-100 text-red-700',
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
