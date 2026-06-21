import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import type { AxiosError } from "axios";
import api from "@/lib/api";
import type {
  AgentDecisionTrace,
  TraceChainResponse,
  TraceEdgeUI,
  TraceNodeUI,
} from "@/types/trace";

// ── Fetcher ───────────────────────────────────────────────────────

async function fetchTraceBySession(
  sessionId: string,
): Promise<TraceChainResponse> {
  const { data } = await api.get<TraceChainResponse>(
    `/api/trace/session/${sessionId}`,
  );
  return data;
}

// ── Primary hook ──────────────────────────────────────────────────

export function useTrace(sessionId?: string) {
  return useQuery<TraceChainResponse, AxiosError>({
    queryKey: ["trace", "session", sessionId] as const,
    queryFn: () => fetchTraceBySession(sessionId!),
    enabled: Boolean(sessionId),
    staleTime: 30_000,
    retry: (failureCount, error) => {
      if (error.response?.status === 404) return false;
      return failureCount < 1;
    },
  });
}

// ── Derived selectors ─────────────────────────────────────────────

export function useAgentTrace(
  sessionId: string | undefined,
  traceId: string | undefined,
): AgentDecisionTrace | undefined {
  const { data } = useTrace(sessionId);

  return useMemo(() => {
    if (!data || !traceId) return undefined;
    return data.chain.find((t) => t.trace_id === traceId);
  }, [data, traceId]);
}

export function usePipelineNodes(sessionId?: string): TraceNodeUI[] {
  const { data } = useTrace(sessionId);
  return data?.nodes ?? [];
}

export function usePipelineEdges(sessionId?: string): TraceEdgeUI[] {
  const { data } = useTrace(sessionId);
  return data?.edges ?? [];
}
