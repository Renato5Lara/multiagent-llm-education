import { useState } from "react";
import { cn } from "@/lib/utils";
import type { DecisionDimension } from "@/types/trace";
import { Input } from "@/components/ui/input";
import {
  ChevronDown,
  ChevronUp,
  Search,
  ShieldCheck,
  GitBranch,
  Lightbulb,
  XCircle,
  Layers,
} from "lucide-react";

// ── Props ─────────────────────────────────────────────────────────

interface DimensionPanelProps {
  dimensions: DecisionDimension[];
}

// ── Dimension color map ───────────────────────────────────────────

const DIMENSION_COLORS: Record<string, string> = {
  // Pipeline-level dimensions (ConsensusMediator)
  pipeline_completeness: "bg-blue-100 text-blue-800 border-blue-200",
  consistency_gate: "bg-green-100 text-green-800 border-green-200",
  consolidation_quality: "bg-violet-100 text-violet-800 border-violet-200",
  debate_resolution: "bg-amber-100 text-amber-800 border-amber-200",

  // Adaptive learning dimensions
  difficulty: "bg-rose-100 text-rose-800 border-rose-200",
  pace: "bg-cyan-100 text-cyan-800 border-cyan-200",
  bloom_range: "bg-violet-100 text-violet-800 border-violet-200",
  modality: "bg-emerald-100 text-emerald-800 border-emerald-200",
  depth: "bg-sky-100 text-sky-800 border-sky-200",
  reinforcement: "bg-orange-100 text-orange-800 border-orange-200",

  // Legacy swarm demo dimensions
  bloom: "bg-violet-100 text-violet-800 border-violet-200",
  cognitive_load: "bg-amber-100 text-amber-800 border-amber-200",
  prompt: "bg-blue-100 text-blue-800 border-blue-200",
  pacing: "bg-rose-100 text-rose-800 border-rose-200",
  scaffolding: "bg-cyan-100 text-cyan-800 border-cyan-200",
};

const FALLBACK_DIMENSION_COLOR =
  "bg-slate-100 text-slate-700 border-slate-200";

function getDimensionColor(dimension: string): string {
  return DIMENSION_COLORS[dimension] ?? FALLBACK_DIMENSION_COLOR;
}

function prettifyDimension(name: string): string {
  return name
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

// ── Confidence helpers ────────────────────────────────────────────

function getConfidenceBar(confidence: number) {
  if (confidence >= 0.85) return { bar: "bg-green-500", text: "text-green-600" };
  if (confidence >= 0.65) return { bar: "bg-amber-400", text: "text-amber-600" };
  return { bar: "bg-red-400", text: "text-red-500" };
}

// ── Value formatter ───────────────────────────────────────────────

function formatValue(value: unknown): string {
  if (value === null || value === undefined) return "null";
  if (typeof value === "string") return value;
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}

// ── Component ─────────────────────────────────────────────────────

export function DimensionPanel({ dimensions }: DimensionPanelProps) {
  const [search, setSearch] = useState("");

  if (dimensions.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center rounded-lg border border-dashed border-slate-200 bg-slate-50 py-10 text-center">
        <GitBranch className="mx-auto mb-2 h-8 w-8 text-slate-300" />
        <p className="text-sm font-medium text-slate-500">
          No decision dimensions recorded.
        </p>
        <p className="mt-1 text-xs text-slate-400">
          This agent did not register multi-dimensional reasoning.
        </p>
      </div>
    );
  }

  const filtered = search
    ? dimensions.filter(
        (d) =>
          d.dimension.toLowerCase().includes(search.toLowerCase()) ||
          d.result.toLowerCase().includes(search.toLowerCase()),
      )
    : dimensions;

  return (
    <div className="space-y-3">
      {/* Search */}
      <div className="relative">
        <Search className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-slate-400" />
        <Input
          placeholder="Filter by dimension or result…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="pl-8 text-sm"
        />
      </div>

      {/* Count */}
      <p className="text-xs text-slate-400">
        {filtered.length} of {dimensions.length} dimensions
        {search && (
          <span className="text-slate-500">
            {" "}
            matching &ldquo;{search}&rdquo;
          </span>
        )}
      </p>

      {/* Items */}
      {filtered.length === 0 ? (
        <p className="py-6 text-center text-sm text-slate-400">
          No dimensions match your filter.
        </p>
      ) : (
        <div className="space-y-2">
          {filtered.map((dim, idx) => (
            <DimensionCard key={`${dim.dimension}-${idx}`} dimension={dim} />
          ))}
        </div>
      )}
    </div>
  );
}

// ── DimensionCard ─────────────────────────────────────────────────

interface DimensionCardProps {
  dimension: DecisionDimension;
}

function DimensionCard({ dimension: dim }: DimensionCardProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const colorClass = getDimensionColor(dim.dimension);
  const { bar, text } = getConfidenceBar(dim.confidence);
  const pct = Math.round(dim.confidence * 100);
  // Guard against null evidence (defensive — schema says Record but backend could send null)
  const hasEvidence = Object.keys(dim.evidence ?? {}).length > 0;
  const hasAlternative =
    dim.alternative_considered !== null &&
    dim.alternative_considered !== undefined;
  const hasBody = hasEvidence || hasAlternative;

  return (
    <div className="overflow-hidden rounded-lg border border-slate-200 bg-white">
      {/* ── Always-visible header ─────────────────────────────────── */}
      <div
        onClick={() => hasBody && setIsExpanded((v) => !v)}
        className={cn(
          "px-3 pb-2 pt-2.5",
          hasBody && "cursor-pointer hover:bg-slate-50",
        )}
      >
        {/* Row 1 — dimension badge + result + confidence + toggle */}
        <div className="flex items-center gap-2">
          <span
            className={cn(
              "inline-flex shrink-0 items-center gap-1 rounded-full border px-2 py-0.5 text-[10px] font-bold",
              colorClass,
            )}
          >
            <Layers className="h-2.5 w-2.5" />
            {prettifyDimension(dim.dimension)}
          </span>

          <span className="flex-1 truncate text-sm font-semibold text-slate-900">
            {dim.result}
          </span>

          <span className={cn("shrink-0 text-[10px] font-bold", text)}>
            <ShieldCheck className="mr-0.5 inline h-2.5 w-2.5" />
            {pct}%
          </span>

          {hasBody && (
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                setIsExpanded((v) => !v);
              }}
              title={isExpanded ? "Collapse" : "Expand evidence"}
              className="ml-1 shrink-0 rounded p-0.5 text-slate-400 transition-colors hover:bg-slate-100 hover:text-slate-600"
            >
              {isExpanded ? (
                <ChevronUp className="h-3.5 w-3.5" />
              ) : (
                <ChevronDown className="h-3.5 w-3.5" />
              )}
            </button>
          )}
        </div>

        {/* Confidence bar */}
        <div
          title={`${pct}% confidence`}
          className="mt-2 h-1 w-full overflow-hidden rounded-full bg-slate-100"
        >
          <div
            className={cn("h-full rounded-full transition-all duration-500", bar)}
            style={{ width: `${pct}%` }}
          />
        </div>

        {/* Signal — what the agent observed */}
        <div className="mt-2 flex items-start gap-1.5">
          <Lightbulb className="mt-0.5 h-3 w-3 shrink-0 text-amber-500" />
          <p className="text-xs italic leading-relaxed text-slate-500">
            {dim.signal}
          </p>
        </div>

        {/* Rule — the logic applied */}
        <div className="mt-1.5 rounded-md bg-slate-50 px-2 py-1.5">
          <p className="font-mono text-[11px] leading-relaxed text-slate-600">
            {dim.rule}
          </p>
        </div>
      </div>

      {/* ── Expandable body — evidence + alternative ─────────────── */}
      <div
        className={cn(
          "overflow-hidden transition-[max-height] duration-200 ease-in-out",
          isExpanded && hasBody ? "max-h-[600px]" : "max-h-0",
        )}
      >
        <div className="space-y-3 border-t border-slate-100 px-3 pb-3 pt-2">
          {/* Supporting evidence */}
          {hasEvidence && (
            <div>
              <p className="mb-1 text-[10px] font-semibold uppercase tracking-wide text-slate-400">
                Supporting Evidence
              </p>
              <pre className="overflow-x-auto rounded-md bg-slate-900 p-2.5 text-[11px] leading-relaxed text-slate-100">
                <code>{formatValue(dim.evidence)}</code>
              </pre>
            </div>
          )}

          {/* Alternative considered & rejected */}
          {hasAlternative && (
            <div className="rounded-md border border-amber-100 bg-amber-50 p-3">
              <div className="mb-1 flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-wide text-amber-700">
                <XCircle className="h-3 w-3" />
                Alternative Considered &amp; Rejected
              </div>
              <p className="text-xs font-medium text-slate-700">
                {dim.alternative_considered}
              </p>
              {dim.alternative_reason && (
                <p className="mt-1 text-xs text-slate-500">
                  {dim.alternative_reason}
                </p>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
