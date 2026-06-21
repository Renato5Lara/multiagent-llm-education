import { useState } from "react";
import type { ElementType } from "react";
import { cn } from "@/lib/utils";
import type { AgentEvidence, EvidenceSource } from "@/types/trace";
import { Input } from "@/components/ui/input";
import {
  Server,
  Database,
  FileJson,
  Sparkles,
  Calculator,
  ChevronDown,
  ChevronUp,
  Search,
  ShieldCheck,
  Inbox,
} from "lucide-react";

// ── Props ─────────────────────────────────────────────────────────

interface EvidencePanelProps {
  evidence: AgentEvidence[];
}

// ── Source config ─────────────────────────────────────────────────

interface SourceConfig {
  label: string;
  badgeClass: string;
  icon: ElementType;
}

const SOURCE_CONFIG: Record<EvidenceSource, SourceConfig> = {
  shared_memory: {
    label: "Shared Memory",
    badgeClass: "bg-violet-100 text-violet-700 border-violet-200",
    icon: Server,
  },
  database: {
    label: "Database",
    badgeClass: "bg-blue-100 text-blue-700 border-blue-200",
    icon: Database,
  },
  state_dict: {
    label: "State",
    badgeClass: "bg-slate-100 text-slate-700 border-slate-200",
    icon: FileJson,
  },
  llm_response: {
    label: "LLM Response",
    badgeClass: "bg-amber-100 text-amber-700 border-amber-200",
    icon: Sparkles,
  },
  computation: {
    label: "Computation",
    badgeClass: "bg-emerald-100 text-emerald-700 border-emerald-200",
    icon: Calculator,
  },
};

// ── Formatters ────────────────────────────────────────────────────

function formatValue(value: unknown): string {
  if (value === null || value === undefined) return "null";
  if (typeof value === "string") return value;
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}

function formatTimestamp(ts: string): string {
  if (!ts) return "—";
  const date = new Date(ts);
  if (Number.isNaN(date.getTime())) return "—";
  return date.toLocaleTimeString(undefined, {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

// ── Component ─────────────────────────────────────────────────────

export function EvidencePanel({ evidence }: EvidencePanelProps) {
  const [search, setSearch] = useState("");

  if (evidence.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center rounded-lg border border-dashed border-slate-200 bg-slate-50 py-10 text-center">
        <Inbox className="mx-auto mb-2 h-8 w-8 text-slate-300" />
        <p className="text-sm font-medium text-slate-500">
          No evidence recorded.
        </p>
        <p className="mt-1 text-xs text-slate-400">
          This agent did not read from shared memory, database, or state.
        </p>
      </div>
    );
  }

  const filtered = search
    ? evidence.filter((e) =>
        e.key.toLowerCase().includes(search.toLowerCase()),
      )
    : evidence;

  return (
    <div className="space-y-3">
      {/* Search */}
      <div className="relative">
        <Search className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-slate-400" />
        <Input
          placeholder="Filter by key…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="pl-8 text-sm"
        />
      </div>

      {/* Count */}
      <p className="text-xs text-slate-400">
        {filtered.length} of {evidence.length} items
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
          No items match your filter.
        </p>
      ) : (
        <div className="space-y-2">
          {filtered.map((item, idx) => (
            <EvidenceItem key={`${item.key}-${idx}`} item={item} />
          ))}
        </div>
      )}
    </div>
  );
}

// ── EvidenceItem ──────────────────────────────────────────────────

interface EvidenceItemProps {
  item: AgentEvidence;
}

function EvidenceItem({ item }: EvidenceItemProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  // Fallback to state_dict if backend introduces a new EvidenceSource
  const config = SOURCE_CONFIG[item.source] ?? SOURCE_CONFIG.state_dict;
  const pct = Math.round(item.confidence * 100);
  const hasValue =
    item.value_summary !== null && item.value_summary !== undefined;

  return (
    <div className="overflow-hidden rounded-lg border border-slate-200 bg-white">
      {/* Header — entire row is clickable */}
      <div
        onClick={() => hasValue && setIsExpanded((v) => !v)}
        className={cn(
          "flex items-center gap-2 px-3 py-2.5",
          hasValue && "cursor-pointer hover:bg-slate-50",
        )}
      >
        {/* Source badge */}
        <span
          className={cn(
            "inline-flex shrink-0 items-center gap-1 rounded-full border px-2 py-0.5 text-[10px] font-semibold",
            config.badgeClass,
          )}
        >
          <config.icon className="h-2.5 w-2.5" />
          {config.label}
        </span>

        {/* Key */}
        <span
          title={item.key}
          className="flex-1 truncate font-mono text-xs text-slate-700"
        >
          {item.key}
        </span>

        {/* Confidence */}
        <span
          className={cn(
            "shrink-0 text-[10px] font-semibold",
            pct >= 85
              ? "text-green-600"
              : pct >= 65
                ? "text-amber-600"
                : "text-red-500",
          )}
        >
          <ShieldCheck className="mr-0.5 inline h-2.5 w-2.5" />
          {pct}%
        </span>

        {/* Expand toggle — visual indicator */}
        {hasValue && (
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              setIsExpanded((v) => !v);
            }}
            title={isExpanded ? "Collapse value" : "Expand value"}
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

      {/* Expanded body — value + metadata */}
      {isExpanded && hasValue && (
        <div className="border-t border-slate-100 px-3 pb-3 pt-2">
          <pre className="overflow-x-auto rounded-md bg-slate-900 p-3 text-[11px] leading-relaxed text-slate-100">
            <code>{formatValue(item.value_summary)}</code>
          </pre>

          <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-[10px] text-slate-400">
            {item.memory_type && (
              <span>
                memory_type:{" "}
                <span className="font-medium text-slate-600">
                  {item.memory_type}
                </span>
              </span>
            )}
            {item.record_id && (
              <span title={item.record_id}>
                record:{" "}
                <span className="font-mono font-medium text-slate-600">
                  {item.record_id.slice(0, 8)}…
                </span>
              </span>
            )}
            <span>
              retrieved:{" "}
              <span className="font-medium text-slate-600">
                {formatTimestamp(item.retrieved_at)}
              </span>
            </span>
          </div>
        </div>
      )}
    </div>
  );
}
