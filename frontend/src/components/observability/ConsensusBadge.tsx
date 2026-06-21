import type { ElementType } from "react";
import { cn } from "@/lib/utils";
import type { DebateRecommendation, DebateState } from "@/types/trace";
import {
  getDebateStateDescription,
  getDebateStateLabel,
} from "@/types/trace";
import { Brain, CheckCircle2, Zap, Scale } from "lucide-react";

// ── Config ────────────────────────────────────────────────────────

interface BadgeConfig {
  icon: ElementType;
  badgeClass: string;
}

const STATE_CONFIG: Record<DebateState, BadgeConfig> = {
  no_debate: {
    icon: Brain,
    badgeClass: "bg-slate-100 text-slate-500 border-slate-200",
  },
  agreement: {
    icon: CheckCircle2,
    badgeClass: "bg-green-100 text-green-700 border-green-200",
  },
  conflict: {
    icon: Zap,
    badgeClass: "bg-amber-100 text-amber-700 border-amber-200",
  },
  resolved: {
    icon: Scale,
    badgeClass: "bg-blue-100 text-blue-700 border-blue-200",
  },
};

// ── Recommendation display ────────────────────────────────────────

const RECOMMENDATION_LABELS: Partial<Record<DebateRecommendation, string>> = {
  retroceder: "Retroceder",
  simplificar: "Simplificar",
  cambiar_modalidad: "Cambiar Modalidad",
  reforzar: "Reforzar",
  continuar: "Continuar",
};

function prettifyRecommendation(rec: string): string {
  return (
    RECOMMENDATION_LABELS[rec as DebateRecommendation] ??
    rec.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())
  );
}

// ── Props ─────────────────────────────────────────────────────────

interface ConsensusBadgeProps {
  state: DebateState;
  recommendation?: string | null;
}

// ── Component ─────────────────────────────────────────────────────

export function ConsensusBadge({ state, recommendation }: ConsensusBadgeProps) {
  const config = STATE_CONFIG[state];
  const label = getDebateStateLabel(state);
  const description = getDebateStateDescription(state, recommendation);
  const Icon = config.icon;

  const showRecommendation =
    recommendation && state !== "no_debate" && state !== "agreement";

  return (
    <div className="flex flex-col items-start gap-1">
      <div
        role="status"
        aria-label={description}
        title={description}
        className={cn(
          "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1",
          "text-xs font-semibold",
          config.badgeClass,
        )}
      >
        <Icon className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
        <span>{label}</span>
      </div>

      {showRecommendation && (
        <p className="pl-1 text-[11px] text-slate-500">
          Pedagogical Recommendation:{" "}
          <span className="font-medium text-slate-700">
            {prettifyRecommendation(recommendation)}
          </span>
        </p>
      )}
    </div>
  );
}
