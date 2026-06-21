import { cn } from "@/lib/utils";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { ExternalLink, Trophy } from "lucide-react";
import type { DebateParticipant } from "@/types/trace";

// ── Difficulty colors ──────────────────────────────────────────────

const DIFFICULTY_STYLES: Record<string, string> = {
  beginner:     "bg-green-100  text-green-700  border-green-200",
  basic:        "bg-green-100  text-green-700  border-green-200",
  intermediate: "bg-blue-100   text-blue-700   border-blue-200",
  advanced:     "bg-purple-100 text-purple-700 border-purple-200",
  expert:       "bg-red-100    text-red-700    border-red-200",
};

function getDifficultyStyle(difficulty: string): string {
  return (
    DIFFICULTY_STYLES[difficulty] ??
    "bg-slate-100 text-slate-600 border-slate-200"
  );
}

// ── Props ──────────────────────────────────────────────────────────

interface DebateCardProps {
  participant: DebateParticipant;
  position: "left" | "right";
  onViewTrace?(traceId: string): void;
}

// ── Component ──────────────────────────────────────────────────────

export function DebateCard({
  participant,
  position,
  onViewTrace,
}: DebateCardProps) {
  const pct = Math.max(
    0,
    Math.min(100, Math.round(participant.confidence * 100)),
  );

  // Defensive: guard against undefined/null proposed_difficulty
  const difficulty = String(
    participant.proposed_difficulty ?? "unknown",
  ).toLowerCase();

  const positionLabel =
    position === "left" ? "Adaptive Proposal" : "Evaluation Override";

  const borderColor =
    position === "left" ? "border-l-blue-400" : "border-l-amber-400";

  const barColor = position === "left" ? "bg-blue-400" : "bg-amber-400";

  return (
    <Card className={cn("border-l-4", borderColor)}>
      <CardHeader className="px-4 pb-2 pt-4">
        <div className="flex items-start justify-between gap-2">
          <div>
            <p className="text-[10px] font-semibold uppercase tracking-widest text-slate-400">
              {positionLabel}
            </p>
            <h4 className="mt-0.5 text-sm font-semibold text-slate-800">
              {participant.agent_display_name}
            </h4>
          </div>

          {participant.is_winner && (
            <span className="inline-flex shrink-0 items-center gap-1 rounded-full border border-amber-200 bg-amber-100 px-2 py-0.5 text-[10px] font-semibold text-amber-700">
              <Trophy className="h-3 w-3" aria-hidden="true" />
              Final
            </span>
          )}
        </div>
      </CardHeader>

      <CardContent className="space-y-3 px-4 pb-4">
        {/* Proposed difficulty */}
        <div className="flex items-center gap-2">
          <span className="text-xs text-slate-500">Proposed:</span>
          <span
            className={cn(
              "inline-flex items-center rounded-full border px-2.5 py-0.5",
              "text-xs font-semibold capitalize",
              getDifficultyStyle(difficulty),
            )}
          >
            {difficulty}
          </span>
        </div>

        {/* Confidence bar */}
        <div className="space-y-1">
          <div className="flex justify-between text-xs text-slate-500">
            <span>Confidence</span>
            <span className="font-medium text-slate-700">{pct}%</span>
          </div>
          <div className="h-1.5 w-full overflow-hidden rounded-full bg-slate-100">
            <div
              className={cn("h-1.5 rounded-full transition-all", barColor)}
              style={{ width: `${pct}%` }}
            />
          </div>
        </div>

        {/* Rationale */}
        <div className="max-h-24 overflow-y-auto rounded-md bg-slate-50 px-3 py-2">
          <p className="text-xs leading-relaxed text-slate-600">
            {participant.rationale}
          </p>
        </div>

        {/* View trace */}
        {onViewTrace && (
          <Button
            variant="ghost"
            size="sm"
            className="h-7 w-full text-xs text-slate-400 hover:text-slate-600"
            onClick={() => onViewTrace(participant.trace_id)}
          >
            <ExternalLink className="mr-1.5 h-3 w-3" aria-hidden="true" />
            View Trace
          </Button>
        )}
      </CardContent>
    </Card>
  );
}
