# Tavily Search API — Integration Architecture

## Purpose

Integrate Tavily Search API as a production-grade, academically-defensible external retrieval layer within the pedagogical swarm architecture. The integration enables ResearchAgent to perform real web searches instead of relying solely on LLM-generated content, providing verifiable sources, current information, and multi-perspective research.

## Architecture Overview

```
ResearchAgent
  └─ PedagogicalRetrievalStrategy
       ├─ TavilyClient (async httpx + tenacity retries)
       ├─ TavilyCache (PostgreSQL + in-memory fallback)
       ├─ TavilyRateLimiterChain (rate limiter + circuit breaker)
       └─ TavilyDiagnostics (events + metrics)
  └─ LLM enrichment (always runs, complements retrieval)
  └─ AggregatedResearch → SharedMemory
       ├─ research:findings
       ├─ research:concepts / examples / analogies
       ├─ research:misconceptions / contradictions
       └─ research:retrieval (full AggregatedResearch dump)

ConsistencyAgent
  └─ Reads research.contradictions → ConsistencyIssue(category="contradiction")
  └─ Reads research.confidence → ConsistencyIssue(category="research_quality")

PromptEngineeringAgent
  └─ Reads research.concepts / misconceptions / real_applications → injects into all 5 prompt generators
```

## Data Flow

1. **ResearchAgent.analyze(state)** — entry point (sync, called by orchestrator)
2. Wraps async Tavily calls via `asyncio.run()` (same pattern as existing LLM calls)
3. **Phase 1**: `PedagogicalRetrievalStrategy.research(RetrievalContext)`
   - Generates 8 pedagogically-optimized queries per topic
   - Executes queries with rate limiting + circuit breaker
   - Checks cache before each query (PostgreSQL → in-memory fallback)
   - Aggregates results: deduplicates URLs, classifies by category, detects contradictions
   - Returns `AggregatedResearch` with 9 category buckets
4. **Phase 2**: LLM enrichment (always runs, even if Tavily succeeds)
   - Structured JSON with concepts, subtopics, difficulties, strategies
5. **Merge**: Tavily + LLM → unified result with confidence scoring
6. **Publish**: to shared memory for downstream agents

## Key Design Decisions

### 1. Separate Integration Package (`integrations/tavily/`)
- Swarm-agnostic, testable, swappable
- Each component (client, cache, rate limit, retrieval, observability) in its own module
- Singleton pattern for client, cache, rate limiter chain

### 2. PostgreSQL + In-Memory Cache
- **PostgreSQL** via `RetrievalCache` table: SHA256 hashing, TTL, reuse counting
- **In-memory fallback** (1000-entry bounded dict): graceful degradation when DB is down
- Clear-expired batch cleanup on both layers

### 3. Async-Only Client
- `httpx.AsyncClient` with connection pooling
- `tenacity` retry: exponential backoff, stop-after-3, only on timeout/5xx
- Matching existing async infrastructure (AsyncUnitOfWork, AsyncSession, LangGraph)

### 4. Rate Limiter + Circuit Breaker
- **Token-bucket rate limiter**: 20 requests/minute sliding window
- **Circuit breaker**: closes after 5 failures, resets after 60s, half-open probe
- Both emit Prometheus metrics and diagnostics events

### 5. Pedagogical Query Strategy
- 8 query categories: introductory, conceptual, practical, misconception, beginner, bloom_level, analogy, real_application, exercise
- Multi-query dispatch maximizes source coverage and diversity
- Semantic aggregation with source dedup, domain diversity counting, confidence scoring

### 6. Graceful Degradation
- No API key → `TavilyClient` disabled → `PedagogicalRetrievalStrategy` captures error → ResearchAgent falls back to LLM-only
- Rate limited → queries skipped, remaining queries still execute
- Circuit open → fast-fail all queries, ResearchAgent degrades
- DB unavailable → in-memory cache fallback (no persistence but no crash)

### 7. Contradiction Detection
- Between query answers: heuristic keyword-pair matching (always/never, must/must not, etc.)
- Flagged as `ConsistencyIssue(category="contradiction")` in ConsistencyAgent
- Production-ready for LLM-based contradiction classifier swap

## Limits & Risks

| Risk | Mitigation |
|------|------------|
| API key leak | Load from env only, masked in logs, never hardcoded |
| Rate limit exceeded | 20 req/min limiter + circuit breaker + graceful degradation |
| External API down | Degraded to LLM-only mode, circuit breaker auto-recovers |
| DB cache unavailable | In-memory fallback (1000 entries) |
| Stale cache results | TTL expiry (default 1h, max 7d) |
| Cost overrun | BASIC search depth, max 5 results, max 8 queries per research call |
| Contradiction false positives | Heuristic detection is conservative; LLM classifier planned |

## Metrics & Observability

### Prometheus Counters
- `tavily_queries_total`, `tavily_queries_success`, `tavily_query_errors`
- `tavily_cache_hits`, `tavily_cache_misses`, `tavily_cache_expired`
- `tavily_rate_limited`, `tavily_auth_errors`, `tavily_timeouts`
- `tavily_contradictions_detected`, `tavily_research_completed`
- `circuit_breaker_tavily_open`, `circuit_breaker_tavily_recovery`

### Prometheus Histograms
- `tavily_query_duration_ms`, `tavily_research_duration_ms`, `tavily_research_sources`

### Diagnostics Events (SSE)
- `tavily:query:start|ok|error|skipped|cache_hit|cache_miss`
- `tavily:research:start|complete|degraded|failed`
- `tavily:contradiction:detected`
- `tavily:rate_limiter:limit_reached`
- `tavily:circuit_breaker:open|closed|half_open`

## Configuration

```env
TAVILY_API_KEY=tvly-...     # Required. Get at https://tavily.com
```

- `SearchDepth.BASIC` — faster, cheaper, sufficient for pedagogical retrieval
- `max_results=5` per query — balances coverage vs cost
- `TTL=3600s` (1h) — cache freshness
- Circuit breaker: 5 failures → open, 60s reset

## Test Strategy

- **Unit tests**: client retries/timeouts/auth, cache set/get/expiry, retrieval strategy query gen/aggregation/contradiction
- **Mocked HTTP**: httpx mock for client tests, MagicMock for research agent pipeline
- **No external dependencies**: all 35 tests pass without Tavily API key or real DB

## Files

```
app/integrations/tavily/
├── __init__.py
├── schemas.py            # Data contracts
├── errors.py             # Typed exception hierarchy
├── client.py             # Async HTTP client with retry
├── cache.py              # PostgreSQL + in-memory cache
├── rate_limit.py         # Rate limiter + circuit breaker
├── retrieval.py          # Pedagogical query strategy + aggregation
└── observability.py      # Diagnostics events + metrics

app/models/retrieval.py   # DB models: RetrievalCache, RetrievalHistory, ResearchSession
app/agents/research_agent.py           # Rewritten with Tavily integration
app/agents/consistency_agent.py        # + contradiction detection
app/agents/prompt_engineering_agent.py # + retrieval content injection
app/core/config.py                     # + TAVILY_API_KEY
.env.example                           # + TAVILY_API_KEY entry

tests/
├── test_tavily_client.py
├── test_tavily_cache.py
├── test_retrieval_strategy.py
└── test_research_agent.py

docs/tavily-integration-architecture.md  # This file
```
