import { useMemo } from "react";
import { ArrowDown, Brain, Scale } from "lucide-react";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { ConsensusBadge } from "./ConsensusBadge";
import { DebateCard } from "./DebateCard";
import { useTrace } from "@/hooks/useTrace";
import {
  extractDebateFromChain,
  getDebateState,
} from "@/types/trace";
import type { DebateResolution } from "@/types/trace";
import { cn } from "@/lib/utils";

// ── Props ──────────────────────────────────────────────────────────

interface DebateTimelineProps {
  sessionId?: string;
  onViewTrace?(traceId: string): void;
}

// ── Helpers ────────────────────────────────────────────────────────

function capitalize(str: string): string {
  return str.replace(/\b\w/g, (c) => c.toUpperCase());
}

// ── Connector ──────────────────────────────────────────────────────

function TimelineConnector() {
  return (
    <div className="flex justify-center py-0.5">
      <ArrowDown className="h-5 w-5 text-slate-300" aria-hidden="true" />
    </div>
  );
}

// ── Final Decision Card ────────────────────────────────────────────

function FinalDecisionCard({ resolution }: { resolution: DebateResolution }) {
  const difficulty = capitalize(
    String(resolution.resolved_difficulty ?? "unknown").toLowerCase(),
  );

  return (
    <Card className="border-l-4 border-l-blue-600 bg-blue-50/40">
      <CardHeader className="px-4 pb-2 pt-4">
        <div className="flex items-center gap-2">
          <Scale
            className="h-4 w-4 shrink-0 text-blue-600"
            aria-hidden="true"
          />
          <div>
            <p className="text-[10px] font-semibold uppercase tracking-widest text-blue-500">
              Final Decision
            </p>
            <h4 className="mt-0.5 text-sm font-semibold text-slate-800">
              Consensus Mediator
            </h4>
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-3 px-4 pb-4">
        {/* Resolved difficulty */}
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-xs text-slate-500">Resolved Difficulty:</span>
          <span
            className={cn(
              "inline-flex items-center rounded-full border px-2.5 py-0.5",
              "text-xs font-semibold",
              "border-blue-200 bg-blue-100 text-blue-700",
            )}
          >
            {difficulty}
          </span>
        </div>

        {/* Recommendation */}
        {resolution.recommendation && (
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-xs text-slate-500">Recommendation:</span>
            <Badge variant="outline" className="text-xs capitalize">
              {resolution.recommendation.replace(/_/g, " ")}
            </Badge>
          </div>
        )}

        {/* Consensus state badge */}
        <ConsensusBadge state="resolved" />

        {/* Resolution reason */}
        <div className="rounded-md border border-blue-100 bg-white px-3 py-2">
          <p className="text-xs leading-relaxed text-slate-600">
            {resolution.resolution_reason}
          </p>
        </div>
      </CardContent>
    </Card>
  );
}

// ── Loading skeleton ───────────────────────────────────────────────

function DebateTimelineSkeleton() {
  return (
    <div className="space-y-2">
      <Skeleton className="h-36 w-full rounded-lg" />
      <div className="flex justify-center py-0.5">
        <Skeleton className="h-5 w-5 rounded-full" />
      </div>
      <div className="flex justify-center">
        <Skeleton className="h-6 w-36 rounded-full" />
      </div>
      <div className="flex justify-center py-0.5">
        <Skeleton className="h-5 w-5 rounded-full" />
      </div>
      <Skeleton className="h-36 w-full rounded-lg" />
      <div className="flex justify-center py-0.5">
        <Skeleton className="h-5 w-5 rounded-full" />
      </div>
      <Skeleton className="h-28 w-full rounded-lg" />
    </div>
  );
}

// ── Main component ─────────────────────────────────────────────────

export function DebateTimeline({ sessionId, onViewTrace }: DebateTimelineProps) {
  const { data, isLoading, isError } = useTrace(sessionId);

  // Memoized to avoid re-running multiple .find() calls on every render
  const resolution = useMemo(
    () => (data ? extractDebateFromChain(data.chain) : null),
    [data],
  );

  // State 1: No session — don't trigger useQuery
  if (!sessionId) {
    return (
      <div className="flex flex-col items-center justify-center gap-2 py-12 text-slate-400">
        <Brain className="h-8 w-8" aria-hidden="true" />
        <p className="text-sm">Select a session to view the agent debate.</p>
      </div>
    );
  }

  // State 2: Loading
  if (isLoading) return <DebateTimelineSkeleton />;

  // Error or empty response
  if (isError || !data) {
    return (
      <div className="flex flex-col items-center justify-center gap-2 py-12 text-slate-400">
        <p className="text-sm">No trace data available for this session.</p>
      </div>
    );
  }

  // State 3: No debate (missing agents, incomplete chain, or no debate context)
  if (!resolution || !resolution.has_debate_context) {
    return (
      <div className="flex flex-col items-center gap-3 py-12">
        <ConsensusBadge state="no_debate" />
        <p className="max-w-xs text-center text-xs text-slate-500">
          No inter-agent debate information was found for this session.
        </p>
      </div>
    );
  }

  const overallState = getDebateState(resolution);

  // State 4: Agreement — both agents converged, no conflict
  if (overallState === "agreement") {
    return (
      <div className="space-y-1">
        <DebateCard
          participant={resolution.adaptive_participant}
          position="left"
          onViewTrace={onViewTrace}
        />
        <TimelineConnector />
        <div className="flex flex-col items-center gap-1">
          <ConsensusBadge
            state="agreement"
            recommendation={resolution.recommendation}
          />
          <p className="text-xs text-slate-400">
            Both agents proposed the same difficulty.
          </p>
        </div>
        <TimelineConnector />
        <FinalDecisionCard resolution={resolution} />
      </div>
    );
  }

  // State 5: Conflict resolved — full negotiation timeline
  return (
    <div className="space-y-1">
      {/* Adaptive proposal */}
      <DebateCard
        participant={resolution.adaptive_participant}
        position="left"
        onViewTrace={onViewTrace}
      />

      <TimelineConnector />

      {/* Conflict detected */}
      <div className="flex justify-center">
        <ConsensusBadge state="conflict" />
      </div>

      <TimelineConnector />

      {/* Evaluation override */}
      {resolution.evaluation_participant && (
        <DebateCard
          participant={resolution.evaluation_participant}
          position="right"
          onViewTrace={onViewTrace}
        />
      )}

      <TimelineConnector />

      {/* Consensus reached */}
      <div className="flex justify-center">
        <ConsensusBadge
          state="resolved"
          recommendation={resolution.recommendation}
        />
      </div>

      <TimelineConnector />

      {/* Final decision */}
      <FinalDecisionCard resolution={resolution} />
    </div>
  );
}
