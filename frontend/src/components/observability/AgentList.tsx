import { cn } from "@/lib/utils";
import { useTrace, usePipelineNodes } from "@/hooks/useTrace";
import {
  getAgentDisplayName,
  getConfidenceLevel,
  formatElapsedMs,
} from "@/types/trace";
import type { TraceNodeUI } from "@/types/trace";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import {
  CheckCircle2,
  XCircle,
  Clock,
  ShieldCheck,
  BrainCircuit,
} from "lucide-react";

// ── Props ─────────────────────────────────────────────────────────

interface AgentListProps {
  sessionId?: string;
  selectedTraceId?: string;
  onSelect: (traceId: string) => void;
}

// ── Confidence color map ──────────────────────────────────────────

const CONFIDENCE_CLASSES: Record<string, string> = {
  high: "bg-green-100 text-green-700 border-green-200",
  medium: "bg-amber-100 text-amber-700 border-amber-200",
  low: "bg-red-100 text-red-700 border-red-200",
};

// ── Component ─────────────────────────────────────────────────────

export function AgentList({
  sessionId,
  selectedTraceId,
  onSelect,
}: AgentListProps) {
  const { isLoading, isError } = useTrace(sessionId);
  const nodes = usePipelineNodes(sessionId);

  if (isLoading) return <AgentListSkeleton />;

  if (isError) {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 p-4">
        <div className="flex items-center gap-2 text-sm text-red-700">
          <XCircle className="h-4 w-4 shrink-0" />
          <span>Unable to load traces.</span>
        </div>
      </div>
    );
  }

  if (nodes.length === 0) {
    return (
      <div className="rounded-lg border bg-white p-6 text-center">
        <BrainCircuit className="mx-auto mb-2 h-8 w-8 text-slate-300" />
        <p className="text-sm font-medium text-slate-600">
          No traces available for this session.
        </p>
        <p className="mt-1 text-xs text-slate-400">
          Run a pipeline to generate agent traces.
        </p>
      </div>
    );
  }

  const sorted = [...nodes].sort((a, b) => a.sequence - b.sequence);

  // h-full lets TraceExplorer control the panel height
  return (
    <div className="h-full space-y-1.5 overflow-y-auto">
      {sorted.map((node) => (
        <AgentCard
          key={node.id}
          node={node}
          isSelected={node.id === selectedTraceId}
          onSelect={() => onSelect(node.id)}
        />
      ))}
    </div>
  );
}

// ── AgentCard ─────────────────────────────────────────────────────

interface AgentCardProps {
  node: TraceNodeUI;
  isSelected: boolean;
  onSelect: () => void;
}

function AgentCard({ node, isSelected, onSelect }: AgentCardProps) {
  const level = getConfidenceLevel(node.confidence);
  const displayName = getAgentDisplayName(node.agent_name);

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={onSelect}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onSelect();
        }
      }}
      className={cn(
        "cursor-pointer rounded-lg border px-3 py-2.5 transition-all duration-150",
        "hover:border-slate-400 hover:shadow-sm",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-900 focus-visible:ring-offset-1",
        isSelected
          ? "border-slate-900 bg-slate-900 text-white shadow-md"
          : "border-slate-200 bg-white",
      )}
    >
      {/* Row 1 — sequence badge + name + success indicator */}
      <div className="flex items-center gap-2">
        <Badge
          variant="secondary"
          className={cn(
            "flex h-5 w-5 shrink-0 items-center justify-center rounded-full p-0 text-[10px] font-bold",
            isSelected && "border-transparent bg-white/20 text-white",
          )}
        >
          {node.sequence + 1}
        </Badge>

        <span
          title={displayName}
          className={cn(
            "flex-1 truncate text-sm font-medium",
            isSelected ? "text-white" : "text-slate-900",
          )}
        >
          {displayName}
        </span>

        {node.success ? (
          <CheckCircle2
            className={cn(
              "h-4 w-4 shrink-0",
              isSelected ? "text-green-300" : "text-green-500",
            )}
          />
        ) : (
          <XCircle
            className={cn(
              "h-4 w-4 shrink-0",
              isSelected ? "text-red-300" : "text-red-500",
            )}
          />
        )}
      </div>

      {/* Row 2 — confidence + elapsed + dimension/evidence count */}
      <div className="mt-1.5 flex items-center gap-1.5 pl-7">
        <span
          className={cn(
            "inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[10px] font-semibold",
            isSelected
              ? "border-white/30 bg-white/15 text-white"
              : CONFIDENCE_CLASSES[level],
          )}
        >
          <ShieldCheck className="h-2.5 w-2.5" />
          {Math.round(node.confidence * 100)}%
        </span>

        <span
          className={cn(
            "inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[10px]",
            isSelected
              ? "border-white/20 bg-white/10 text-slate-200"
              : "border-slate-200 bg-slate-50 text-slate-500",
          )}
        >
          <Clock className="h-2.5 w-2.5" />
          {formatElapsedMs(node.elapsed_ms)}
        </span>

        {node.dimensions_count > 0 && (
          <span
            title={`${node.dimensions_count} dimensions · ${node.evidence_count} evidences`}
            className={cn(
              "text-[10px]",
              isSelected ? "text-slate-300" : "text-slate-400",
            )}
          >
            {node.dimensions_count}d · {node.evidence_count}e
          </span>
        )}
      </div>
    </div>
  );
}

// ── Skeleton ──────────────────────────────────────────────────────

function AgentListSkeleton() {
  return (
    <div className="space-y-1.5">
      {Array.from({ length: 8 }).map((_, i) => (
        <div
          key={i}
          className="rounded-lg border border-slate-200 bg-white px-3 py-2.5"
        >
          <div className="flex items-center gap-2">
            <Skeleton className="h-5 w-5 rounded-full" />
            <Skeleton className="h-4 flex-1 rounded" />
            <Skeleton className="h-4 w-4 rounded-full" />
          </div>
          <div className="mt-1.5 flex gap-1.5 pl-7">
            <Skeleton className="h-4 w-14 rounded-full" />
            <Skeleton className="h-4 w-12 rounded-full" />
          </div>
        </div>
      ))}
    </div>
  );
}
