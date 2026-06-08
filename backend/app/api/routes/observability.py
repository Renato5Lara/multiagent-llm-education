"""
Observability API — real-time metrics, SSE stream, and dashboard.

Endpoints:
    GET  /api/observability/metrics            — Prometheus text format
    GET  /api/observability/metrics.json        — JSON snapshot
    GET  /api/observability/stream              — SSE real-time stream
    GET  /api/observability/dashboard           — HTML dashboard
    GET  /api/observability/swarm               — SwarmDiagnostics summary
    GET  /api/observability/anomalies           — List/filter anomaly signals
    GET  /api/observability/anomalies/{id}      — Single anomaly detail
    GET  /api/observability/anomalies/export    — Export anomalies as CSV
    GET  /api/observability/anomalies/metrics   — Aggregated anomaly metrics
    GET  /api/observability/timeline            — DecisionTimeline entries
    GET  /api/observability/lineage             — EventLineageTracker chains
    POST /api/observability/reset               — Reset in-process metrics
"""
from __future__ import annotations

import csv
import io
import json
import logging
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse, StreamingResponse

from app.observability.metrics_exporter import exporter
from app.observability.stream import stream
from app.observability.swarm_diagnostics import diagnostics

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/observability", tags=["Observabilidad"])

# ── SSE anomaly hook registration ────────────────────────────────────────
# Wire the diagnostics engine to push anomaly signals to the SSE stream.
_tried_hook = False


def _register_anomaly_sse_hook():
    global _tried_hook
    if _tried_hook:
        return
    _tried_hook = True
    try:
        from app.swarm_diagnostics import diagnostics_engine

        def _push_to_stream(signals):
            if not signals:
                return
            serialized = [s.to_dict() for s in signals]
            stream.push_sync("anomaly", serialized)

        diagnostics_engine.register_post_anomaly_hook(_push_to_stream)
    except Exception:
        logger.debug("Could not register anomaly SSE hook (engine not ready)")


_register_anomaly_sse_hook()


# ── Anomaly filtering helpers ────────────────────────────────────────────

def _get_anomaly_store():
    """Lazy import to avoid circular dependency at module load."""
    from app.swarm_diagnostics import diagnostics_engine
    return diagnostics_engine


def _filter_anomalies(
    anomalies: list[dict],
    *,
    severity: str | None = None,
    scope: str | None = None,
    detector_name: str | None = None,
    anomaly_type: str | None = None,
    since: str | None = None,
    until: str | None = None,
    search: str | None = None,
) -> list[dict]:
    """Apply filters to a list of serialized anomaly dicts. All filters AND."""
    if severity:
        anomalies = [a for a in anomalies if a.get("severity") == severity]
    if scope:
        anomalies = [a for a in anomalies if scope in a.get("scope", "")]
    if detector_name:
        anomalies = [a for a in anomalies if a.get("detector_name") == detector_name]
    if anomaly_type:
        anomalies = [a for a in anomalies if a.get("anomaly_type") == anomaly_type]
    if since:
        try:
            since_dt = datetime.fromisoformat(since)
            anomalies = [a for a in anomalies if _parse_iso(a.get("created_at", "")) >= since_dt]
        except (ValueError, TypeError):
            pass
    if until:
        try:
            until_dt = datetime.fromisoformat(until)
            anomalies = [a for a in anomalies if _parse_iso(a.get("created_at", "")) <= until_dt]
        except (ValueError, TypeError):
            pass
    if search:
        q = search.lower()
        anomalies = [
            a for a in anomalies
            if q in (a.get("title", "") or "").lower()
            or q in (a.get("description", "") or "").lower()
            or q in (a.get("detector_name", "") or "").lower()
        ]
    return anomalies


def _parse_iso(iso_str: str) -> datetime:
    """Parse ISO datetime string, tolerant of missing timezone."""
    try:
        return datetime.fromisoformat(iso_str)
    except (ValueError, TypeError):
        return datetime.min


@router.get("/metrics")
async def metrics_prometheus():
    """Prometheus-format text, suitable for scraping."""
    return PlainTextResponse(exporter.prometheus())


@router.get("/metrics.json")
async def metrics_json():
    """Full JSON snapshot of all in-process metrics."""
    return JSONResponse(exporter.json_snapshot())


@router.get("/stream")
async def metrics_stream(request: Request):
    """Server-Sent Events stream of real-time metric updates."""

    async def event_generator():
        async with stream.subscribe() as queue:
            async for event in stream.generate(queue):
                if await request.is_disconnected():
                    break
                yield event

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/dashboard")
async def dashboard():
    """Self-contained real-time dashboard (HTML + JS)."""
    return HTMLResponse(content=DASHBOARD_HTML)


@router.get("/swarm")
async def swarm_summary() -> JSONResponse:
    """SwarmDiagnostics summary — decisions, event chains, module reports."""
    return JSONResponse({
        "summary": diagnostics.summary(),
        "timeline_count": len(diagnostics.timeline.records),
        "chain_count": len(diagnostics.chain_tracker.all_chains()),
    })


@router.get("/anomalies")
async def list_anomalies(
    limit: int = Query(default=50, ge=1, le=1000, description="Max items to return"),
    offset: int = Query(default=0, ge=0, description="Number of items to skip"),
    severity: str | None = Query(default=None, description="Filter by severity: critical, warning, info"),
    scope: str | None = Query(default=None, description="Filter by scope substring match"),
    detector_name: str | None = Query(default=None, description="Filter by detector name"),
    anomaly_type: str | None = Query(default=None, description="Filter by anomaly type"),
    since: str | None = Query(default=None, description="ISO datetime lower bound"),
    until: str | None = Query(default=None, description="ISO datetime upper bound"),
    search: str | None = Query(default=None, description="Full-text search on title/description"),
    sort: str = Query(default="desc", pattern="^(asc|desc)$", description="Sort direction"),
) -> JSONResponse:
    """List anomaly signals with filtering, pagination, and sorting."""
    try:
        engine = _get_anomaly_store()
        signals = [s.to_dict() for s in engine.anomalies]
    except (ImportError, AttributeError):
        signals = []

    # Apply filters
    signals = _filter_anomalies(
        signals,
        severity=severity,
        scope=scope,
        detector_name=detector_name,
        anomaly_type=anomaly_type,
        since=since,
        until=until,
        search=search,
    )

    # Sort
    signals.sort(key=lambda a: a.get("created_at", ""), reverse=(sort == "desc"))

    total = len(signals)
    page = signals[offset:offset + limit]

    return JSONResponse({
        "anomalies": page,
        "total": total,
        "offset": offset,
        "limit": limit,
        "returned": len(page),
    })


@router.get("/anomalies/metrics")
async def anomaly_metrics() -> JSONResponse:
    """Aggregated anomaly statistics."""
    try:
        engine = _get_anomaly_store()
    except (ImportError, AttributeError):
        return _empty_anomaly_metrics()

    with engine._lock:
        all_anomalies = list(engine._anomalies)

    if not all_anomalies:
        return _empty_anomaly_metrics()

    by_severity: dict[str, int] = {}
    by_type: dict[str, int] = {}
    by_detector: dict[str, int] = {}
    severities_list: list[str] = []
    scopes: set[str] = set()

    for a in all_anomalies:
        sev = a.severity.value if hasattr(a.severity, "value") else str(a.severity)
        atype = a.anomaly_type.value if hasattr(a.anomaly_type, "value") else str(a.anomaly_type)
        by_severity[sev] = by_severity.get(sev, 0) + 1
        by_type[atype] = by_type.get(atype, 0) + 1
        by_detector[a.detector_name] = by_detector.get(a.detector_name, 0) + 1
        severities_list.append(sev)
        scopes.add(a.scope)

    critical_weight = 3
    warning_weight = 1
    info_weight = 0
    health_score = 100.0
    total_weighted = (
        by_severity.get("critical", 0) * critical_weight
        + by_severity.get("warning", 0) * warning_weight
    )
    if total_weighted > 0:
        health_score = max(0.0, 100.0 - min(total_weighted * 5.0, 100.0))

    return JSONResponse({
        "total": len(all_anomalies),
        "by_severity": by_severity,
        "by_type": by_type,
        "by_detector": by_detector,
        "unique_scopes": len(scopes),
        "health_score": round(health_score, 1),
    })


def _empty_anomaly_metrics() -> JSONResponse:
    return JSONResponse({
        "total": 0,
        "by_severity": {},
        "by_type": {},
        "by_detector": {},
        "unique_scopes": 0,
        "health_score": 100.0,
    })


@router.get("/anomalies/export", response_model=None)
async def export_anomalies(
    severity: str | None = Query(default=None),
    scope: str | None = Query(default=None),
    detector_name: str | None = Query(default=None),
    anomaly_type: str | None = Query(default=None),
    since: str | None = Query(default=None),
    until: str | None = Query(default=None),
    format: str = Query(default="csv", pattern="^(csv|json)$"),
):
    """Export anomaly signals as CSV or JSON."""
    try:
        engine = _get_anomaly_store()
        signals = [s.to_dict() for s in engine.anomalies]
    except (ImportError, AttributeError):
        signals = []

    signals = _filter_anomalies(
        signals,
        severity=severity,
        scope=scope,
        detector_name=detector_name,
        anomaly_type=anomaly_type,
        since=since,
        until=until,
    )

    if format == "json":
        return JSONResponse({"anomalies": signals, "total": len(signals)})

    # CSV export
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "anomaly_id", "detector_name", "anomaly_type", "severity",
        "scope", "title", "description", "metric_value", "threshold",
        "created_at", "correlation_id",
    ])
    for a in signals:
        writer.writerow([
            a.get("anomaly_id", ""),
            a.get("detector_name", ""),
            a.get("anomaly_type", ""),
            a.get("severity", ""),
            a.get("scope", ""),
            a.get("title", ""),
            a.get("description", ""),
            a.get("metric_value", ""),
            a.get("threshold", ""),
            a.get("created_at", ""),
            a.get("correlation_id", ""),
        ])
    return PlainTextResponse(
        output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=anomalies.csv"},
    )


@router.get("/anomalies/{anomaly_id}")
async def get_anomaly(anomaly_id: str) -> JSONResponse:
    """Get a single anomaly signal by ID."""
    try:
        engine = _get_anomaly_store()
        for s in engine.anomalies:
            if s.anomaly_id == anomaly_id:
                return JSONResponse(s.to_dict())
    except (ImportError, AttributeError):
        pass
    return JSONResponse({"error": "Anomaly not found"}, status_code=404)


@router.get("/timeline")
async def timeline(
    student_id: str | None = None,
    module_id: str | None = None,
    limit: int = 100,
) -> JSONResponse:
    """DecisionTimeline entries, optionally filtered."""
    records = diagnostics.timeline.records
    if student_id:
        records = [r for r in records if r.student_id == student_id]
    if module_id:
        records = [r for r in records if r.module_id == module_id]
    return JSONResponse({
        "total": len(records),
        "records": [r.to_dict() for r in records[-limit:]],
    })


@router.get("/lineage")
async def lineage(chain_id: str | None = None) -> JSONResponse:
    """EventLineageTracker chains."""
    chains = diagnostics.chain_tracker.all_chains()
    if chain_id:
        chains = {chain_id: chains.get(chain_id, [])}
    return JSONResponse({
        "total_chains": len(chains),
        "chains": chains,
    })


@router.post("/reset")
async def reset_metrics():
    """Reset all in-process metrics (admin)."""
    from app.observability.consensus_metrics import metrics as consensus
    consensus.reset()
    diagnostics.reset()
    return JSONResponse({"status": "ok", "message": "Metrics reset"})


# ====================================================================
# Embedded Dashboard HTML (~400 lines, zero build step)
# ====================================================================

DASHBOARD_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Swarm Observability Dashboard</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script>
<style>
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
       background: #0f172a; color: #e2e8f0; padding: 20px; }
h1 { font-size: 1.5rem; margin-bottom: 1rem; color: #38bdf8; }
h2 { font-size: 1rem; margin-bottom: 0.5rem; color: #94a3b8; }
.grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(340px, 1fr)); gap: 16px; }
.card { background: #1e293b; border: 1px solid #334155; border-radius: 12px; padding: 16px; }
.stat-row { display: flex; justify-content: space-between; padding: 4px 0; font-size: 0.875rem; }
.stat-label { color: #94a3b8; }
.stat-value { color: #e2e8f0; font-weight: 600; font-variant-numeric: tabular-nums; }
.badge { display: inline-block; padding: 2px 8px; border-radius: 99px; font-size: 0.75rem;
         font-weight: 600; }
.badge-ok { background: #065f46; color: #6ee7b7; }
.badge-warn { background: #78350f; color: #fbbf24; }
.badge-err { background: #7f1d1d; color: #fca5a5; }
canvas { max-height: 180px; }
.mono { font-family: 'SF Mono', 'Fira Code', monospace; font-size: .8rem; }
.anomaly-list { max-height: 240px; overflow-y: auto; }
.anomaly-item { display: flex; gap: 8px; padding: 6px 0; border-bottom: 1px solid #334155;
                font-size: .8rem; }
.header-bar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.uptime { font-size: .85rem; color: #64748b; }
.tab-bar { display: flex; gap: 4px; margin-bottom: 16px; }
.tab { padding: 6px 14px; border-radius: 8px; border: none; cursor: pointer;
       font-size: .8rem; background: #334155; color: #94a3b8; transition: all .15s; }
.tab.active { background: #0ea5e9; color: #fff; }
.tab:hover { background: #475569; }
</style>
</head>
<body>
<div class="header-bar">
  <h1>Swarm Observability</h1>
  <span class="uptime" id="uptime">Uptime: --</span>
</div>
<div class="tab-bar">
  <button class="tab active" data-tab="overview">Overview</button>
  <button class="tab" data-tab="consensus">Consensus</button>
  <button class="tab" data-tab="resilience">Resilience</button>
  <button class="tab" data-tab="propagation">Propagation</button>
</div>

<div id="tab-overview" class="tab-content">
<div class="grid">
  <div class="card">
    <h2>Consensus</h2>
    <div class="stat-row"><span class="stat-label">Runs</span><span class="stat-value" id="cons-runs">0</span></div>
    <div class="stat-row"><span class="stat-label">Approval Rate</span><span class="stat-value" id="cons-approval-rate">0%</span></div>
    <div class="stat-row"><span class="stat-label">Rejection Rate</span><span class="stat-value" id="cons-rejection-rate">0%</span></div>
    <div class="stat-row"><span class="stat-label">Disagreements</span><span class="stat-value" id="cons-disagreements">0</span></div>
    <div class="stat-row"><span class="stat-label">Avg Latency</span><span class="stat-value" id="cons-latency">0ms</span></div>
    <div class="stat-row"><span class="stat-label">Rollbacks</span><span class="stat-value" id="cons-rollbacks">0</span></div>
    <div class="stat-row"><span class="stat-label">Errors</span><span class="stat-value" id="cons-errors">0</span></div>
  </div>
  <div class="card">
    <h2>Activations & Sessions</h2>
    <div class="stat-row"><span class="stat-label">Active Activations</span><span class="stat-value" id="act-active">0</span></div>
    <div class="stat-row"><span class="stat-label">Activation History</span><span class="stat-value" id="act-history">0</span></div>
    <div class="stat-row"><span class="stat-label">Active Sessions</span><span class="stat-value" id="sess-active">0</span></div>
    <div class="stat-row"><span class="stat-label">Session History</span><span class="stat-value" id="sess-history">0</span></div>
  </div>
  <div class="card">
    <h2>Resilience</h2>
    <div class="stat-row"><span class="stat-label">Recovery Rate</span><span class="stat-value" id="rec-rate">100%</span></div>
    <div class="stat-row"><span class="stat-label">Recovery Attempts</span><span class="stat-value" id="rec-attempts">0</span></div>
    <div class="stat-row"><span class="stat-label">Recovery Successes</span><span class="stat-value" id="rec-successes">0</span></div>
    <div class="stat-row"><span class="stat-label">Circuit Breakers</span><span class="stat-value" id="cb-count">0</span></div>
  </div>
  <div class="card">
    <h2>Propagation</h2>
    <div class="stat-row"><span class="stat-label">Active Chains</span><span class="stat-value" id="prop-chains">0</span></div>
    <div class="stat-row"><span class="stat-label">Total Hops</span><span class="stat-value" id="prop-hops">0</span></div>
  </div>
  <div class="card">
    <h2>Sandbox</h2>
    <div class="stat-row"><span class="stat-label">Status</span><span class="stat-value" id="sb-status">--</span></div>
    <div class="stat-row"><span class="stat-label">Executions</span><span class="stat-value" id="sb-executions">0</span></div>
    <div class="stat-row"><span class="stat-label">Docker / Fallback</span><span class="stat-value" id="sb-docker">0 / 0</span></div>
    <div class="stat-row"><span class="stat-label">Avg Time</span><span class="stat-value" id="sb-avg-ms">0ms</span></div>
    <div class="stat-row"><span class="stat-label">Security Violations</span><span class="stat-value" id="sb-violations">0</span></div>
    <div class="stat-row"><span class="stat-label">Timeouts / OOM</span><span class="stat-value" id="sb-timeouts">0 / 0</span></div>
  </div>
  <div class="card" style="grid-column: span 2;">
    <h2>Consensus Decision Distribution</h2>
    <canvas id="consensusChart"></canvas>
  </div>
  <div class="card" style="grid-column: span 2;">
    <h2>Anomaly Timeline</h2>
    <div class="anomaly-list" id="anomalyList"><em style="color:#64748b;">No anomalies detected</em></div>
  </div>
</div>
</div>

<div id="tab-consensus" class="tab-content" style="display:none;">
<div class="grid">
  <div class="card">
    <h2>Voter Stats</h2>
    <div id="voterStats"><em style="color:#64748b;">No voters yet</em></div>
  </div>
  <div class="card" style="grid-column: span 2;">
    <h2>Latency Trend (last 20 runs)</h2>
    <canvas id="latencyChart"></canvas>
  </div>
  <div class="card">
    <h2>Top Rejection Reasons</h2>
    <div id="rejectionReasons"><em style="color:#64748b;">None</em></div>
  </div>
  <div class="card">
    <h2>Top Abstention Reasons</h2>
    <div id="abstentionReasons"><em style="color:#64748b;">None</em></div>
  </div>
</div>
</div>

<div id="tab-resilience" class="tab-content" style="display:none;">
<div class="grid">
  <div class="card">
    <h2>Circuit Breaker States</h2>
    <div id="cbStates"><em style="color:#64748b;">No circuit breakers</em></div>
  </div>
  <div class="card">
    <h2>Retry Counts</h2>
    <div id="retryCounts"><em style="color:#64748b;">No retries</em></div>
  </div>
  <div class="card" style="grid-column: span 2;">
    <h2>Recovery Rate</h2>
    <canvas id="recoveryChart"></canvas>
  </div>
</div>
</div>

<div id="tab-propagation" class="tab-content" style="display:none;">
<div class="grid">
  <div class="card" style="grid-column: span 3;">
    <h2>Propagation Chains</h2>
    <div id="propChains"><em style="color:#64748b;">No propagation chains</em></div>
  </div>
</div>
</div>

<script>
// ── Tab switching ──────────────────────────────────────────────
document.querySelectorAll('.tab').forEach(tab => {
  tab.addEventListener('click', () => {
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(tc => tc.style.display = 'none');
    tab.classList.add('active');
    document.getElementById('tab-' + tab.dataset.tab).style.display = '';
  });
});

// ── Chart instances ────────────────────────────────────────────
const consensusCtx = document.getElementById('consensusChart').getContext('2d');
const consensusChart = new Chart(consensusCtx, {
  type: 'doughnut',
  data: { labels: ['Approvals', 'Rejections', 'Abstentions'],
          datasets: [{ data: [0, 0, 0],
                       backgroundColor: ['#22c55e', '#ef4444', '#f59e0b'] }] },
  options: { responsive: true, maintainAspectRatio: true,
             plugins: { legend: { position: 'bottom', labels: { color: '#94a3b8' } } } }
});

const latencyCtx = document.getElementById('latencyChart').getContext('2d');
const latencyChart = new Chart(latencyCtx, {
  type: 'line',
  data: { labels: [], datasets: [{ label: 'Latency (ms)', data: [],
           borderColor: '#38bdf8', backgroundColor: 'rgba(56,189,248,0.1)', fill: true,
           tension: 0.3 }] },
  options: { responsive: true, maintainAspectRatio: true,
             scales: { x: { ticks: { color: '#64748b' } },
                       y: { ticks: { color: '#64748b' } } },
             plugins: { legend: { labels: { color: '#94a3b8' } } } }
});

const recoveryCtx = document.getElementById('recoveryChart').getContext('2d');
const recoveryChart = new Chart(recoveryCtx, {
  type: 'doughnut',
  data: { labels: ['Success', 'Failure'],
          datasets: [{ data: [1, 0],
                       backgroundColor: ['#22c55e', '#ef4444'] }] },
  options: { responsive: true, maintainAspectRatio: true,
             plugins: { legend: { position: 'bottom', labels: { color: '#94a3b8' } } } }
});

// ── Data store for trends ──────────────────────────────────────
const latencyTrend = []; // last 20
const LATENCY_MAX = 20;

  // ── SSE client ─────────────────────────────────────────────────
const evtSource = new EventSource('/api/observability/stream');

evtSource.addEventListener('snapshot', e => {
  const data = JSON.parse(e.data);
  updateDashboard(data);
});

evtSource.addEventListener('anomaly', e => {
  // Real-time anomaly notification — update anomaly list immediately
  const anomalies = JSON.parse(e.data);
  renderAnomalies(anomalies);
});

evtSource.addEventListener('consensus', e => {
  // individual consensus event — optionally handle specially
});

evtSource.onerror = () => {
  console.warn('SSE connection lost, retrying...');
};

function updateDashboard(data) {
  // Uptime
  document.getElementById('uptime').textContent =
    'Uptime: ' + formatDuration(data.uptime_seconds);

  // Consensus
  const c = data.consensus || {};
  document.getElementById('cons-runs').textContent = c.total_runs || 0;
  document.getElementById('cons-approval-rate').textContent =
    (c.approval_rate * 100).toFixed(1) + '%';
  document.getElementById('cons-rejection-rate').textContent =
    (c.rejection_rate * 100).toFixed(1) + '%';
  document.getElementById('cons-disagreements').textContent = c.disagreements || 0;
  document.getElementById('cons-latency').textContent =
    (c.avg_latency_ms || 0).toFixed(1) + 'ms';
  document.getElementById('cons-rollbacks').textContent = c.rollbacks || 0;
  document.getElementById('cons-errors').textContent = c.errors || 0;

  // Consensus chart
  consensusChart.data.datasets[0].data = [c.approvals || 0, c.rejections || 0, c.abstentions || 0];
  consensusChart.update();

  // Activations & Sessions
  const act = data.activations || {};
  document.getElementById('act-active').textContent = act.active_count || 0;
  document.getElementById('act-history').textContent = act.history_count || 0;
  const sess = data.sessions || {};
  document.getElementById('sess-active').textContent = sess.active_count || 0;
  document.getElementById('sess-history').textContent = sess.history_count || 0;

  // Resilience
  const res = data.resilience || {};
  const recRate = res.recovery_rate !== undefined ? res.recovery_rate : 1;
  document.getElementById('rec-rate').textContent = (recRate * 100).toFixed(1) + '%';
  document.getElementById('rec-attempts').textContent = res.recovery_attempts || 0;
  document.getElementById('rec-successes').textContent = res.recovery_successes || 0;
  const cbCount = Object.keys(res.circuit_breakers || {}).length;
  document.getElementById('cb-count').textContent = cbCount;

  // Propagation
  const prop = data.propagation || {};
  document.getElementById('prop-chains').textContent = prop.active_chains || 0;
  document.getElementById('prop-hops').textContent = prop.total_hops || 0;

  // Sandbox
  const sb = data.sandbox || {};
  document.getElementById('sb-status').textContent = sb.status || 'unregistered';
  const sbExecs = sb.executions || {};
  document.getElementById('sb-executions').textContent = sbExecs.total || 0;
  document.getElementById('sb-docker').textContent = (sbExecs.docker || 0) + ' / ' + (sbExecs.fallback || 0);
  document.getElementById('sb-avg-ms').textContent = (sbExecs.avg_time_ms || 0).toFixed(1) + 'ms';
  const sbErrors = sb.errors || {};
  document.getElementById('sb-violations').textContent = sbErrors.security_violations || 0;
  document.getElementById('sb-timeouts').textContent = (sbErrors.timeouts || 0) + ' / ' + (sbErrors.memory_exceeded || 0);

  // Latency trend
  if (c.avg_latency_ms !== undefined && c.avg_latency_ms > 0) {
    latencyTrend.push(c.avg_latency_ms);
    if (latencyTrend.length > LATENCY_MAX) latencyTrend.shift();
    latencyChart.data.labels = latencyTrend.map((_, i) => '#' + (i+1));
    latencyChart.data.datasets[0].data = latencyTrend;
    latencyChart.update();
  }

  // Recovery chart
  const recSuccess = res.recovery_successes || 0;
  const recFail = (res.recovery_attempts || 0) - recSuccess;
  recoveryChart.data.datasets[0].data = [Math.max(recSuccess, 1), Math.max(recFail, 0)];
  recoveryChart.update();

  // Voter stats
  const vs = c.voter_stats;
  if (vs && Object.keys(vs).length) {
    let html = '';
    for (const [name, s] of Object.entries(vs)) {
      html += `<div class="stat-row"><span class="stat-label">${name}</span>
               <span class="stat-value">${s.votes} votes, ${s.avg_latency_ms}ms avg</span></div>`;
    }
    document.getElementById('voterStats').innerHTML = html;
  }

  // Rejection reasons
  const rej = c.top_rejection_reasons;
  if (rej && rej.length) {
    let html = '';
    for (const [reason, count] of rej) {
      html += `<div class="stat-row"><span class="stat-label">${reason.slice(0, 40)}</span>
               <span class="stat-value">${count}</span></div>`;
    }
    document.getElementById('rejectionReasons').innerHTML = html;
  }

  // Anomalies — render from snapshot data or SSE push
  const aData = data.anomalies || {};
  if (aData.latest && aData.latest.length) {
    renderAnomalies(aData.latest);
  } else {
    // Fallback REST fetch if no snapshot data
    fetchAnomalies();
  }
}

let _lastAnomalyIds = new Set();

function renderAnomalies(anomalyList) {
  const list = document.getElementById('anomalyList');
  if (!anomalyList || !anomalyList.length) {
    list.innerHTML = '<em style="color:#64748b;">No anomalies detected</em>';
    return;
  }
  let html = '';
  for (const a of anomalyList.slice(-20).reverse()) {
    _lastAnomalyIds.add(a.anomaly_id);
    const badge = a.severity === 'critical'
      ? 'badge-err' : a.severity === 'warning' ? 'badge-warn' : 'badge-ok';
    const sevLabel = a.severity || 'info';
    const typeLabel = a.anomaly_type || 'unknown';
    const desc = (a.description || a.title || '').slice(0, 100);
    html += `<div class="anomaly-item">
      <span class="badge ${badge}">${sevLabel}</span>
      <span class="mono">${typeLabel}</span>
      <span style="color:#94a3b8;flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${desc}</span>
    </div>`;
  }
  list.innerHTML = html;
}

function fetchAnomalies() {
  fetch('/api/observability/anomalies?limit=20&sort=desc')
    .then(r => r.json())
    .then(d => {
      if (d.anomalies && d.anomalies.length) {
        renderAnomalies(d.anomalies);
      }
    })
    .catch(() => {});
}

function formatDuration(secs) {
  if (!secs) return '--';
  const d = Math.floor(secs / 86400);
  const h = Math.floor((secs % 86400) / 3600);
  const m = Math.floor((secs % 3600) / 60);
  const s = Math.floor(secs % 60);
  let parts = [];
  if (d) parts.push(d + 'd');
  if (h) parts.push(h + 'h');
  if (m) parts.push(m + 'm');
  parts.push(s + 's');
  return parts.join(' ');
}

// Initial load
fetch('/api/observability/metrics.json')
  .then(r => r.json())
  .then(data => updateDashboard(data))
  .catch(() => {});
</script>
</body>
</html>
"""


@router.get("/static/dashboard.html", include_in_schema=False)
async def dashboard_alt():
    """Alias for dashboard at a more conventional static path."""
    return await dashboard()
