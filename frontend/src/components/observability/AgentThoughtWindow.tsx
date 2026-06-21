import { useState } from "react";
import type { ElementType } from "react";
import { cn } from "@/lib/utils";
import { useTrace, useAgentTrace } from "@/hooks/useTrace";
import type { AgentDecisionTrace } from "@/types/trace";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { ThoughtSummary } from "./ThoughtSummary";
import { EvidencePanel } from "./EvidencePanel";
import { DimensionPanel } from "./DimensionPanel";
import { ReasoningPanel } from "./ReasoningPanel";
import {
  Brain,
  Database,
  GitBranch,
  ListOrdered,
  FileJson,
  BrainCircuit,
  MousePointerClick,
  AlertTriangle,
  Copy,
  Check,
} from "lucide-react";

// ── Props ─────────────────────────────────────────────────────────

interface AgentThoughtWindowProps {
  sessionId?: string;
  traceId?: string;
}

// ── Tab config ────────────────────────────────────────────────────

interface TabConfig {
  value: string;
  label: string;
  icon: ElementType;
  count?: number;
}

// ── State screens ─────────────────────────────────────────────────

function NoTraceSelected() {
  return (
    <div className="flex h-full flex-col items-center justify-center p-8 text-center">
      <MousePointerClick className="mb-3 h-10 w-10 text-slate-200" />
      <p className="text-sm font-medium text-slate-500">
        Select an agent from the list to inspect its reasoning.
      </p>
      <p className="mt-1 text-xs text-slate-400">
        Evidence, dimensions, and reasoning steps will appear here.
      </p>
    </div>
  );
}

function LoadingSkeleton() {
  return (
    <div className="space-y-4 p-4">
      <div className="space-y-3 rounded-lg bg-slate-100 p-4">
        <div className="flex items-center gap-2">
          <Skeleton className="h-8 w-8 rounded-lg" />
          <div className="flex-1 space-y-1.5">
            <Skeleton className="h-2.5 w-14" />
            <Skeleton className="h-4 w-44" />
          </div>
          <Skeleton className="h-6 w-16 rounded-full" />
        </div>
        <div className="flex gap-2">
          <Skeleton className="h-5 w-20 rounded-full" />
          <Skeleton className="h-5 w-16 rounded-full" />
          <Skeleton className="h-5 w-16 rounded-full" />
        </div>
        <Skeleton className="h-1.5 w-full rounded-full" />
      </div>

      <div className="space-y-2">
        <Skeleton className="h-3 w-24" />
        <Skeleton className="h-16 w-full rounded-md" />
      </div>

      <div className="grid grid-cols-4 gap-2">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-16 rounded-lg" />
        ))}
      </div>
    </div>
  );
}

function TraceError() {
  return (
    <div className="m-4 rounded-lg border border-red-200 bg-red-50 p-5 text-center">
      <AlertTriangle className="mx-auto mb-2 h-8 w-8 text-red-400" />
      <p className="text-sm font-medium text-red-700">
        Unable to load trace data.
      </p>
      <p className="mt-1 text-xs text-red-500">
        Check that the backend /api/trace/session endpoint is reachable.
      </p>
    </div>
  );
}

function TraceNotFound() {
  return (
    <div className="flex h-full flex-col items-center justify-center p-8 text-center">
      <BrainCircuit className="mb-3 h-10 w-10 text-slate-200" />
      <p className="text-sm font-medium text-slate-500">
        Agent trace not found.
      </p>
      <p className="mt-1 text-xs text-slate-400">
        The selected trace does not match any agent in this session.
      </p>
    </div>
  );
}

// ── Raw JSON tab (isolated copy state) ───────────────────────────

interface RawJsonTabProps {
  trace: AgentDecisionTrace;
}

function RawJsonTab({ trace }: RawJsonTabProps) {
  const [copied, setCopied] = useState(false);
  const json = JSON.stringify(trace, null, 2);

  async function handleCopy() {
    if (!navigator.clipboard) return;
    try {
      await navigator.clipboard.writeText(json);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // clipboard access denied — silent fail
    }
  }

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <p className="text-xs text-slate-400">
          Full trace object · {(json.length / 1024).toFixed(1)} KB
        </p>
        <Button
          type="button"
          variant="ghost"
          size="sm"
          onClick={handleCopy}
          className="h-7 gap-1.5 px-2 text-xs"
        >
          {copied ? (
            <>
              <Check className="h-3 w-3 text-green-500" />
              <span className="text-green-500">Copied!</span>
            </>
          ) : (
            <>
              <Copy className="h-3 w-3" />
              Copy
            </>
          )}
        </Button>
      </div>

      <div className="max-h-[60vh] overflow-y-auto rounded-lg bg-slate-900">
        <pre className="p-4 text-[11px] leading-relaxed text-slate-100">
          <code>{json}</code>
        </pre>
      </div>
    </div>
  );
}

// ── Component ─────────────────────────────────────────────────────

export function AgentThoughtWindow({
  sessionId,
  traceId,
}: AgentThoughtWindowProps) {
  // Hooks must be called before any early returns (React rules of hooks)
  const { isLoading, isError } = useTrace(sessionId);
  const trace = useAgentTrace(sessionId, traceId);

  // State 1: nothing selected yet
  if (!traceId) return <NoTraceSelected />;

  // State 2: query in flight
  if (isLoading) return <LoadingSkeleton />;

  // State 3: network / server error
  if (isError) return <TraceError />;

  // State 4: traceId set but not found in chain
  if (!trace) return <TraceNotFound />;

  // State 5: ready
  const tabs: TabConfig[] = [
    { value: "summary", label: "Summary", icon: Brain },
    {
      value: "evidence",
      label: "Evidence",
      icon: Database,
      count: trace.evidence.length,
    },
    {
      value: "dimensions",
      label: "Dimensions",
      icon: GitBranch,
      count: trace.dimensions.length,
    },
    {
      value: "reasoning",
      label: "Reasoning",
      icon: ListOrdered,
      count: trace.reasoning_steps.length,
    },
    { value: "raw", label: "Raw JSON", icon: FileJson },
  ];

  return (
    // key={traceId} forces Tabs remount on agent change → resets to defaultValue="summary"
    <Tabs
      key={traceId}
      defaultValue="summary"
      className="flex h-full flex-col overflow-hidden"
    >
      {/* ── Sticky tab bar ──────────────────────────────────────── */}
      <div className="shrink-0 border-b border-slate-200">
        <TabsList
          className={cn(
            "flex h-auto w-full justify-start",
            "gap-0 overflow-x-auto rounded-none bg-transparent p-0",
          )}
        >
          {tabs.map((tab) => (
            <TabsTrigger
              key={tab.value}
              value={tab.value}
              className={cn(
                // Base
                "group flex shrink-0 items-center gap-1.5 rounded-none",
                "border-b-2 border-transparent px-3 py-2.5",
                "bg-transparent text-xs font-medium text-slate-500 shadow-none",
                // Hover
                "hover:bg-slate-50 hover:text-slate-700",
                // Active — overrides component's bg-white + shadow-sm via CSS specificity
                "data-[state=active]:border-slate-900",
                "data-[state=active]:bg-transparent",
                "data-[state=active]:text-slate-900",
                "data-[state=active]:shadow-none",
              )}
            >
              <tab.icon className="h-3.5 w-3.5" />
              {tab.label}
              {tab.count !== undefined && tab.count > 0 && (
                <span
                  className={cn(
                    "rounded-full px-1.5 py-0 text-[10px] font-bold leading-5",
                    "bg-slate-100 text-slate-500",
                    // group inherits data-state="active" from the parent <button>
                    "group-data-[state=active]:bg-slate-900",
                    "group-data-[state=active]:text-white",
                  )}
                >
                  {tab.count}
                </span>
              )}
            </TabsTrigger>
          ))}
        </TabsList>
      </div>

      {/* ── Scrollable content ───────────────────────────────────── */}
      <div className="flex-1 overflow-y-auto p-4">
        <TabsContent value="summary" className="mt-0">
          <ThoughtSummary trace={trace} />
        </TabsContent>

        <TabsContent value="evidence" className="mt-0">
          <EvidencePanel evidence={trace.evidence} />
        </TabsContent>

        <TabsContent value="dimensions" className="mt-0">
          <DimensionPanel dimensions={trace.dimensions} />
        </TabsContent>

        <TabsContent value="reasoning" className="mt-0">
          <ReasoningPanel reasoning={trace.reasoning_steps} />
        </TabsContent>

        <TabsContent value="raw" className="mt-0">
          <RawJsonTab trace={trace} />
        </TabsContent>
      </div>
    </Tabs>
  );
}
