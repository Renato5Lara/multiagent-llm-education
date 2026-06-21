import { useState } from "react";
import type { ElementType } from "react";
import { cn } from "@/lib/utils";
import { formatElapsedMs } from "@/types/trace";
import type { AgentReasoningStep, StepType } from "@/types/trace";
import {
  HardDrive,
  SearchCode,
  Sparkles,
  GitBranch,
  Calculator,
  CheckCircle2,
  Upload,
  ChevronDown,
  ChevronUp,
  Clock,
  Brain,
  ArrowRight,
} from "lucide-react";

// ── Props ─────────────────────────────────────────────────────────

interface ReasoningPanelProps {
  reasoning: AgentReasoningStep[];
}

// ── Step type config ──────────────────────────────────────────────

interface StepTypeConfig {
  label: string;
  badgeClass: string;
  dotClass: string;
  lineClass: string;
  icon: ElementType;
}

const STEP_TYPE_CONFIG: Record<StepType, StepTypeConfig> = {
  data_load: {
    label: "Data Load",
    badgeClass: "bg-slate-100 text-slate-600 border-slate-200",
    dotClass: "bg-slate-400 ring-slate-100",
    lineClass: "border-slate-200",
    icon: HardDrive,
  },
  memory_query: {
    label: "Memory Query",
    badgeClass: "bg-violet-100 text-violet-700 border-violet-200",
    dotClass: "bg-violet-500 ring-violet-100",
    lineClass: "border-violet-200",
    icon: SearchCode,
  },
  llm_inference: {
    label: "LLM Inference",
    badgeClass: "bg-amber-100 text-amber-700 border-amber-200",
    dotClass: "bg-amber-500 ring-amber-100",
    lineClass: "border-amber-200",
    icon: Sparkles,
  },
  rule_evaluation: {
    label: "Rule Evaluation",
    badgeClass: "bg-blue-100 text-blue-700 border-blue-200",
    dotClass: "bg-blue-500 ring-blue-100",
    lineClass: "border-blue-200",
    icon: GitBranch,
  },
  computation: {
    label: "Computation",
    badgeClass: "bg-emerald-100 text-emerald-700 border-emerald-200",
    dotClass: "bg-emerald-500 ring-emerald-100",
    lineClass: "border-emerald-200",
    icon: Calculator,
  },
  decision: {
    label: "Decision",
    badgeClass: "bg-green-100 text-green-700 border-green-200",
    dotClass: "bg-green-500 ring-green-100",
    lineClass: "border-green-200",
    icon: CheckCircle2,
  },
  memory_publish: {
    label: "Memory Publish",
    badgeClass: "bg-purple-100 text-purple-700 border-purple-200",
    dotClass: "bg-purple-500 ring-purple-100",
    lineClass: "border-purple-200",
    icon: Upload,
  },
};

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

// ── Empty state ───────────────────────────────────────────────────

function EmptyReasoningState() {
  return (
    <div className="rounded-lg border border-dashed border-slate-200 bg-slate-50 p-6">
      <div className="flex items-start gap-3">
        <Brain className="mt-0.5 h-5 w-5 shrink-0 text-slate-300" />
        <div>
          <p className="text-sm font-medium text-slate-600">
            No explicit reasoning steps were recorded for this agent.
          </p>
          <p className="mt-1 text-xs text-slate-400">
            This agent relied on evidence and decision dimensions. See the{" "}
            <span className="font-medium text-slate-500">Evidence</span> and{" "}
            <span className="font-medium text-slate-500">Dimensions</span> tabs
            for its decision rationale.
          </p>
        </div>
      </div>
    </div>
  );
}

// ── Component ─────────────────────────────────────────────────────

export function ReasoningPanel({ reasoning }: ReasoningPanelProps) {
  if (reasoning.length === 0) {
    return <EmptyReasoningState />;
  }

  return (
    <div>
      <div className="mb-3 flex items-center gap-2 text-xs text-slate-500">
        <ArrowRight className="h-3.5 w-3.5" />
        <span>
          {reasoning.length} reasoning step
          {reasoning.length !== 1 ? "s" : ""} recorded
        </span>
      </div>

      <div>
        {reasoning.map((step, idx) => (
          <ReasoningStep
            key={step.step_number}
            step={step}
            isLast={idx === reasoning.length - 1}
          />
        ))}
      </div>
    </div>
  );
}

// ── ReasoningStep ─────────────────────────────────────────────────

interface ReasoningStepProps {
  step: AgentReasoningStep;
  isLast: boolean;
}

function ReasoningStep({ step, isLast }: ReasoningStepProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const config =
    STEP_TYPE_CONFIG[step.step_type] ?? STEP_TYPE_CONFIG.computation;

  const hasInputs = Object.keys(step.inputs).length > 0;
  const hasOutputs = Object.keys(step.outputs).length > 0;
  const hasBody = hasInputs || hasOutputs || Boolean(step.notes);

  return (
    <div className="flex gap-3">
      {/* ── Left: dot + vertical connector ───────────────────────── */}
      <div className="flex flex-col items-center">
        <div
          className={cn(
            "mt-2.5 h-3 w-3 shrink-0 rounded-full ring-4",
            config.dotClass,
          )}
        />
        {!isLast && (
          <div
            className={cn(
              "mt-1 w-0 flex-1 border-l-2 border-dashed",
              config.lineClass,
            )}
          />
        )}
      </div>

      {/* ── Right: step card ─────────────────────────────────────── */}
      <div className={cn("flex-1", isLast ? "pb-0" : "pb-3")}>
        <div className="overflow-hidden rounded-lg border border-slate-200 bg-white">
          {/* Header — entire row clickable when body exists */}
          <div
            onClick={() => hasBody && setIsExpanded((v) => !v)}
            className={cn(
              "flex items-start gap-2 px-3 py-2.5",
              hasBody && "cursor-pointer hover:bg-slate-50",
            )}
          >
            {/* Step number — zero-padded for visual alignment */}
            <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-slate-100 text-[10px] font-bold text-slate-600">
              {String(step.step_number).padStart(2, "0")}
            </span>

            {/* Content */}
            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-center gap-2">
                <span
                  className={cn(
                    "inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[10px] font-semibold",
                    config.badgeClass,
                  )}
                >
                  <config.icon className="h-2.5 w-2.5" />
                  {config.label}
                </span>

                {step.elapsed_ms !== null && step.elapsed_ms !== undefined && (
                  <span className="inline-flex items-center gap-0.5 text-[10px] text-slate-400">
                    <Clock className="h-2.5 w-2.5" />
                    {formatElapsedMs(step.elapsed_ms)}
                  </span>
                )}
              </div>

              <p className="mt-1 text-sm leading-snug text-slate-700">
                {step.description}
              </p>

              {/* Notes always visible when collapsed */}
              {step.notes && !isExpanded && (
                <p className="mt-0.5 text-xs italic text-slate-400">
                  {step.notes}
                </p>
              )}
            </div>

            {/* Expand toggle */}
            {hasBody && (
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  setIsExpanded((v) => !v);
                }}
                title={isExpanded ? "Collapse details" : "Expand details"}
                className="mt-0.5 shrink-0 rounded p-0.5 text-slate-400 transition-colors hover:bg-slate-100 hover:text-slate-600"
              >
                {isExpanded ? (
                  <ChevronUp className="h-3.5 w-3.5" />
                ) : (
                  <ChevronDown className="h-3.5 w-3.5" />
                )}
              </button>
            )}
          </div>

          {/* Expandable body — max-h transition for smooth animation */}
          <div
            className={cn(
              "overflow-hidden transition-[max-height] duration-200 ease-in-out",
              isExpanded && hasBody ? "max-h-[600px]" : "max-h-0",
            )}
          >
            <div className="space-y-3 border-t border-slate-100 px-3 pb-3 pt-2">
              {step.notes && (
                <p className="text-xs italic text-slate-500">{step.notes}</p>
              )}

              {hasInputs && (
                <div>
                  <p className="mb-1 text-[10px] font-semibold uppercase tracking-wide text-slate-400">
                    Inputs
                  </p>
                  <pre className="overflow-x-auto rounded-md bg-slate-900 p-2.5 text-[11px] leading-relaxed text-slate-100">
                    <code>{formatValue(step.inputs)}</code>
                  </pre>
                </div>
              )}

              {hasOutputs && (
                <div>
                  <p className="mb-1 text-[10px] font-semibold uppercase tracking-wide text-slate-400">
                    Outputs
                  </p>
                  <pre className="overflow-x-auto rounded-md bg-slate-800 p-2.5 text-[11px] leading-relaxed text-emerald-100">
                    <code>{formatValue(step.outputs)}</code>
                  </pre>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
