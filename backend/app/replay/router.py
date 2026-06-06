from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Query
from fastapi.responses import HTMLResponse, JSONResponse

from app.replay.engine import engine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/replay", tags=["Replay Cognitivo"])


@router.get("/sessions")
async def list_sessions(limit: int = Query(default=20, ge=1, le=100)):
    sessions = engine.list_sessions(limit=limit)
    return JSONResponse({
        "count": len(sessions),
        "sessions": sessions,
    })


@router.get("/sessions/{session_id}")
async def get_session(session_id: str):
    session = engine.get_session(session_id)
    if not session:
        return JSONResponse({"error": "Session not found"}, status_code=404)
    return JSONResponse(session.to_dict())


@router.get("/frames/{session_id}")
async def get_frames(
    session_id: str,
    phase: str | None = Query(default=None, description="Filter by phase"),
    step_from: int | None = Query(default=None, ge=1),
    step_to: int | None = Query(default=None, ge=1),
):
    session = engine.get_session(session_id)
    if not session:
        return JSONResponse({"error": "Session not found"}, status_code=404)
    frames = session.frames
    if phase:
        frames = [f for f in frames if f.phase.value == phase]
    if step_from:
        frames = [f for f in frames if f.step >= step_from]
    if step_to:
        frames = [f for f in frames if f.step <= step_to]
    return JSONResponse({
        "session_id": session_id,
        "count": len(frames),
        "frames": [f.to_dict() for f in frames],
    })


@router.get("/cognitive")
async def get_cognitive_tracks():
    return JSONResponse(engine.cognitive.snapshot())


@router.get("/cognitive/{track_name}")
async def get_cognitive_track(track_name: str):
    tracks = engine.cognitive.snapshot()
    if track_name not in tracks:
        return JSONResponse({"error": f"Track '{track_name}' not found"}, status_code=404)
    return JSONResponse(tracks[track_name])


@router.get("/dashboard")
async def replay_dashboard():
    return HTMLResponse(content=REPLAY_DASHBOARD_HTML)


@router.post("/reset")
async def reset_replay():
    engine.reset()
    return JSONResponse({"status": "ok", "message": "Replay engine reset"})


REPLAY_DASHBOARD_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Replay Cognitivo — Dashboard</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script>
<style>
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
       background: #0f172a; color: #e2e8f0; padding: 20px; }
h1 { font-size: 1.3rem; margin-bottom: 0.5rem; color: #22d3ee; display: flex; align-items: center; gap: 8px; }
h2 { font-size: 0.9rem; margin-bottom: 0.5rem; color: #94a3b8; }
h3 { font-size: 0.8rem; color: #64748b; margin-bottom: 0.3rem; }
.grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 12px; }
.grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.card { background: #1e293b; border: 1px solid #334155; border-radius: 12px; padding: 14px; }
.stat-row { display: flex; justify-content: space-between; padding: 3px 0; font-size: 0.8rem; }
.stat-label { color: #64748b; }
.stat-value { color: #e2e8f0; font-weight: 600; font-variant-numeric: tabular-nums; }
canvas { max-height: 140px; width: 100% !important; }
.mono { font-family: 'SF Mono', 'Fira Code', monospace; font-size: .75rem; }
.header-bar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
.status-dot { width: 8px; height: 8px; border-radius: 50%; display: inline-block; margin-right: 6px; }
.dot-connected { background: #22c55e; box-shadow: 0 0 6px #22c55e; }
.dot-disconnected { background: #ef4444; }
.tab-bar { display: flex; gap: 4px; margin-bottom: 12px; flex-wrap: wrap; }
.tab { padding: 5px 12px; border-radius: 8px; border: none; cursor: pointer;
       font-size: .75rem; background: #334155; color: #94a3b8; transition: all .15s; }
.tab.active { background: #0ea5e9; color: #fff; }
.tab:hover { background: #475569; }
.reasoning-panel { max-height: 400px; overflow-y: auto; }
.reasoning-step { position: relative; padding-left: 16px; padding-bottom: 12px; border-left: 2px solid #334155; }
.reasoning-step.active { border-left-color: #22d3ee; }
.reasoning-dot { position: absolute; left: -5px; top: 0; width: 8px; height: 8px; border-radius: 50%; background: #475569; }
.reasoning-step.active .reasoning-dot { background: #22d3ee; box-shadow: 0 0 8px #22d3ee; }
.agent-badge { display: inline-block; padding: 1px 8px; border-radius: 99px; font-size: .65rem; font-weight: 600; color: #fff; }
.signal-text { color: #fbbf24; font-size: .7rem; }
.decision-text { color: #6ee7b7; font-size: .7rem; }
.bloom-bar { display: flex; align-items: flex-end; gap: 4px; height: 100px; margin: 8px 0; }
.bloom-col { flex: 1; display: flex; flex-direction: column; align-items: center; gap: 2px; }
.bloom-fill { width: 100%; border-radius: 4px 4px 0 0; transition: height 0.5s; min-height: 4px; }
.bloom-label { font-size: .6rem; color: #64748b; text-align: center; }
.consensus-bar { display: flex; align-items: flex-end; gap: 2px; height: 60px; margin: 8px 0; }
.consensus-col { flex: 1; border-radius: 2px 2px 0 0; transition: height 0.3s; }
.badge { display: inline-block; padding: 2px 8px; border-radius: 99px; font-size: .65rem; font-weight: 600; }
.badge-green { background: #065f46; color: #6ee7b7; }
.badge-amber { background: #78350f; color: #fbbf24; }
.badge-red { background: #7f1d1d; color: #fca5a5; }
details summary { cursor: pointer; color: #64748b; font-size: .7rem; }
details summary:hover { color: #94a3b8; }
pre.evidence { font-size: .65rem; color: #64748b; background: #0f172a; padding: 4px; border-radius: 4px; margin-top: 4px; overflow-x: auto; }
</style>
</head>
<body>

<div class="header-bar">
  <h1><span>🧠</span> Replay Cognitivo</h1>
  <div>
    <span class="status-dot" id="statusDot"></span>
    <span class="mono text-slate-400" id="statusText">Desconectado</span>
  </div>
</div>

<div class="tab-bar">
  <button class="tab active" data-tab="evolucion">Evolución</button>
  <button class="tab" data-tab="razonamiento">Razonamiento</button>
  <button class="tab" data-tab="narrativa">Narrativa</button>
  <button class="tab" data-tab="consenso">Consenso</button>
</div>

<div id="tab-evolucion" class="tab-content">
  <div class="grid">
    <div class="card" style="grid-column: span 2;">
      <h2>📊 Evolución Bloom</h2>
      <div id="bloomContainer"><p class="mono" style="color:#64748b;height:100px;display:flex;align-items:center;justify-content:center;">Esperando datos...</p></div>
    </div>
    <div class="card">
      <h2>📈 Confianza</h2>
      <canvas id="confidenceChart"></canvas>
      <div id="confidenceStats" class="stat-row"><span class="stat-label">Promedio</span><span class="stat-value">--</span></div>
    </div>
    <div class="card">
      <h2>🎨 Multimodal</h2>
      <canvas id="multimodalChart"></canvas>
      <div id="multimodalStats" class="stat-row"><span class="stat-label">Diversidad</span><span class="stat-value">--</span></div>
    </div>
    <div class="card">
      <h2>📝 Prompts</h2>
      <canvas id="promptChart"></canvas>
      <div id="promptStats" class="stat-row"><span class="stat-label">Total</span><span class="stat-value">0</span></div>
    </div>
    <div class="card">
      <h2>🧠 Carga Cognitiva</h2>
      <canvas id="cognitiveChart"></canvas>
      <div id="cognitiveStats" class="stat-row"><span class="stat-label">Score</span><span class="stat-value">--</span></div>
    </div>
    <div class="card">
      <h2>🔄 Pacing</h2>
      <div id="pacingContainer"><p class="mono" style="color:#64748b;">Sin cambios de pacing</p></div>
    </div>
    <div class="card">
      <h2>⚠️ Misconceptions</h2>
      <div id="misconceptionsContainer"><p class="mono" style="color:#64748b;">Sin datos</p></div>
    </div>
  </div>
</div>

<div id="tab-razonamiento" class="tab-content" style="display:none;">
  <div class="grid-2">
    <div class="card" style="grid-column: span 2;">
      <h2>🔍 Razonamiento paso a paso</h2>
      <div class="reasoning-panel" id="reasoningPanel">
        <p class="mono" style="color:#64748b;">Esperando frames de razonamiento...</p>
      </div>
    </div>
  </div>
</div>

<div id="tab-narrativa" class="tab-content" style="display:none;">
  <div class="grid">
    <div class="card" style="grid-column: span 2;">
      <h2>📖 Continuidad Narrativa</h2>
      <div id="narrativeContainer"><p class="mono" style="color:#64748b;">Esperando datos narrativos...</p></div>
    </div>
    <div class="card">
      <h2>💾 Eventos de Memoria</h2>
      <div id="memoryEvents" style="max-height:200px;overflow-y:auto;"><p class="mono" style="color:#64748b;">Sin eventos</p></div>
    </div>
  </div>
</div>

<div id="tab-consenso" class="tab-content" style="display:none;">
  <div class="grid">
    <div class="card" style="grid-column: span 2;">
      <h2>🤝 Evolución de Consenso</h2>
      <canvas id="consensusTrendChart"></canvas>
      <div id="consensusStats"></div>
    </div>
    <div class="card">
      <h2>📊 Distribución de Decisiones</h2>
      <canvas id="consensusDistChart"></canvas>
    </div>
  </div>
</div>

<script>
// ── SSE Connection ───────────────────────────────────────────
const evtSource = new EventSource('/api/observability/stream');
const statusDot = document.getElementById('statusDot');
const statusText = document.getElementById('statusText');

evtSource.onopen = () => {
  statusDot.className = 'status-dot dot-connected';
  statusText.textContent = 'Conectado';
};
evtSource.onerror = () => {
  statusDot.className = 'status-dot dot-disconnected';
  statusText.textContent = 'Desconectado';
};

// ── Data stores ──────────────────────────────────────────────
const reasoningSteps = [];
const bloomHistory = [];
const confidenceHistory = [];
const consensusHistory = [];
const multimodalHistory = [];
const promptHistory = [];
const cognitiveHistory = [];
const narrativeHistory = [];
const pacingHistory = [];
const misconceptionHistory = [];
const memoryEvents = [];

// ── Chart instances ──────────────────────────────────────────
const confidenceCtx = document.getElementById('confidenceChart').getContext('2d');
const confidenceChart = new Chart(confidenceCtx, {
  type: 'line',
  data: { labels: [], datasets: [{
    label: 'Confianza', data: [],
    borderColor: '#22d3ee', backgroundColor: 'rgba(34,211,238,0.1)',
    fill: true, tension: 0.3, pointRadius: 2,
  }]},
  options: {
    responsive: true, maintainAspectRatio: true,
    scales: {
      x: { ticks: { color: '#64748b', font: { size: 9 } }, display: false },
      y: { min: 0, max: 1, ticks: { color: '#64748b', font: { size: 9 } } },
    },
    plugins: { legend: { display: false } },
  },
});

const multimodalCtx = document.getElementById('multimodalChart').getContext('2d');
const multimodalChart = new Chart(multimodalCtx, {
  type: 'doughnut',
  data: { labels: [], datasets: [{ data: [], backgroundColor: ['#22c55e','#3b82f6','#a855f7','#f59e0b','#ef4444'] }] },
  options: { responsive: true, maintainAspectRatio: true, plugins: { legend: { position: 'bottom', labels: { color: '#94a3b8', font: { size: 9 } } } } },
});

const promptCtx = document.getElementById('promptChart').getContext('2d');
const promptChart = new Chart(promptCtx, {
  type: 'bar',
  data: { labels: [], datasets: [{
    label: 'Prompts', data: [],
    backgroundColor: '#f43f5e', borderRadius: 4,
  }]},
  options: {
    responsive: true, maintainAspectRatio: true,
    scales: { x: { ticks: { color: '#64748b', font: { size: 8 } } }, y: { ticks: { color: '#64748b', font: { size: 8 } } } },
    plugins: { legend: { display: false } },
  },
});

const cognitiveCtx = document.getElementById('cognitiveChart').getContext('2d');
const cognitiveChart = new Chart(cognitiveCtx, {
  type: 'line',
  data: { labels: [], datasets: [{
    label: 'Carga Cognitiva', data: [],
    borderColor: '#f97316', backgroundColor: 'rgba(249,115,22,0.1)',
    fill: true, tension: 0.3, pointRadius: 2,
  }]},
  options: {
    responsive: true, maintainAspectRatio: true,
    scales: { x: { ticks: { color: '#64748b', font: { size: 9 } }, display: false }, y: { min: 0, max: 100, ticks: { color: '#64748b', font: { size: 9 } } } },
    plugins: { legend: { display: false } },
  },
});

const consensusTrendCtx = document.getElementById('consensusTrendChart').getContext('2d');
const consensusTrendChart = new Chart(consensusTrendCtx, {
  type: 'line',
  data: { labels: [], datasets: [{
    label: 'Confianza de Consenso', data: [],
    borderColor: '#a855f7', backgroundColor: 'rgba(168,85,247,0.1)',
    fill: true, tension: 0.3, pointRadius: 3,
  }]},
  options: {
    responsive: true, maintainAspectRatio: true,
    scales: { x: { ticks: { color: '#64748b', font: { size: 9 } } }, y: { min: 0, max: 1, ticks: { color: '#64748b', font: { size: 9 } } } },
    plugins: { legend: { display: false } },
  },
});

const consensusDistCtx = document.getElementById('consensusDistChart').getContext('2d');
const consensusDistChart = new Chart(consensusDistCtx, {
  type: 'doughnut',
  data: { labels: ['Aprobado', 'Rechazado', 'Abstenido'], datasets: [{ data: [10, 0, 0], backgroundColor: ['#22c55e', '#ef4444', '#f59e0b'] }] },
  options: { responsive: true, maintainAspectRatio: true, plugins: { legend: { position: 'bottom', labels: { color: '#94a3b8', font: { size: 9 } } } } },
});

// ── SSE Event Handlers ───────────────────────────────────────

evtSource.addEventListener('replay:start', e => {
  const data = JSON.parse(e.data);
  document.querySelector('h1').innerHTML = '<span>🧠</span> Replay: ' + data.topic.slice(0, 40);
});

evtSource.addEventListener('replay:frame', e => {
  const frame = JSON.parse(e.data);
  reasoningSteps.push({
    step: frame.step,
    agent: frame.agent,
    reasoning: frame.reasoning,
    signal: frame.signal,
    decision: frame.agent_decision,
    evidence: frame.evidence || {},
  });
  renderReasoning();
});

evtSource.addEventListener('replay:adaptation', e => {
  const ad = JSON.parse(e.data);
  pacingHistory.push(ad);
  renderPacing();
});

evtSource.addEventListener('replay:consensus', e => {
  const cs = JSON.parse(e.data);
  consensusHistory.push(cs);
  renderConsensus();
});

evtSource.addEventListener('replay:memory', e => {
  const mem = JSON.parse(e.data);
  memoryEvents.push(mem);
  renderMemory();
});

evtSource.addEventListener('replay:complete', e => {
  const summary = JSON.parse(e.data);
  renderComplete(summary);
});

// ── Snapshot handler for cognitive tracks ────────────────────
evtSource.addEventListener('snapshot', e => {
  // no-op for cognitive; we fetch tracks separately
});

// ── Periodic fetch cognitive tracks ──────────────────────────
async function fetchCognitiveTracks() {
  try {
    const r = await fetch('/api/replay/cognitive');
    const tracks = await r.json();

    // Bloom
    const bloom = tracks.bloom_evolution?.history || [];
    if (bloom.length > 0) {
      bloomHistory.push(...bloom);
      renderBloom();
    }

    // Confidence
    const conf = tracks.confidence_evolution?.history || [];
    if (conf.length > 0) {
      confidenceHistory.push(...conf);
      renderConfidence();
    }

    // Multimodal
    const mm = tracks.multimodal_adaptation?.history || [];
    if (mm.length > 0) {
      multimodalHistory.push(...mm);
      renderMultimodal();
    }

    // Prompts
    const pr = tracks.prompt_evolution?.history || [];
    if (pr.length > 0) {
      promptHistory.push(...pr);
      renderPrompt();
    }

    // Cognitive load
    const cl = tracks.cognitive_load?.history || [];
    if (cl.length > 0) {
      cognitiveHistory.push(...cl);
      renderCognitive();
    }

    // Narrative
    const nar = tracks.narrative_continuity?.history || [];
    if (nar.length > 0) {
      narrativeHistory.push(...nar);
      renderNarrative();
    }

    // Misconceptions
    const mis = tracks.misconceptions?.history || [];
    if (mis.length > 0) {
      misconceptionHistory.push(...mis);
      renderMisconceptions();
    }
  } catch (err) {
    // silent
  }
}

setInterval(fetchCognitiveTracks, 2000);
fetchCognitiveTracks();

// ── Render functions ─────────────────────────────────────────

function renderBloom() {
  const latest = bloomHistory[bloomHistory.length - 1];
  if (!latest) return;
  const dist = latest.value.distribution || {};
  const total = Object.values(dist).reduce((a, b) => a + b, 0) || 1;
  const colors = ['#3b82f6', '#22c55e', '#eab308', '#f97316', '#ef4444', '#a855f7'];
  const labels = ['Recordar', 'Comprender', 'Aplicar', 'Analizar', 'Evaluar', 'Crear'];

  let html = '<div class="bloom-bar">';
  for (let i = 1; i <= 6; i++) {
    const count = dist[String(i)] || 0;
    const pct = count / total;
    const height = Math.max(4, pct * 100);
    html += '<div class="bloom-col">';
    html += `<span style="font-size:.6rem;color:#94a3b8;">${count}</span>`;
    html += `<div class="bloom-fill" style="height:${height}px;background:${colors[i-1]};opacity:0.8;"></div>`;
    html += `<span class="bloom-label">${labels[i-1].slice(0, 5)}</span>`;
    html += '</div>';
  }
  html += '</div>';
  html += `<div style="display:flex;justify-content:space-between;font-size:.7rem;color:#64748b;">
    <span>Prom: <span style="color:#e2e8f0;">${latest.value.avg_bloom.toFixed(1)}</span></span>
    <span>Max: <span style="color:#e2e8f0;">${latest.value.max_bloom}</span></span>
    <span>Secciones: <span style="color:#e2e8f0;">${latest.value.section_count}</span></span>
  </div>`;
  document.getElementById('bloomContainer').innerHTML = html;
}

function renderConfidence() {
  if (confidenceHistory.length === 0) return;
  const data = confidenceHistory.map(h => h.value.mean);
  const labels = confidenceHistory.map((_, i) => '#' + (i + 1));
  confidenceChart.data.labels = labels;
  confidenceChart.data.datasets[0].data = data;
  confidenceChart.update();
  const avg = data.reduce((a, b) => a + b, 0) / data.length;
  document.querySelector('#confidenceStats .stat-value').textContent = avg.toFixed(2);
}

function renderMultimodal() {
  if (multimodalHistory.length === 0) return;
  const latest = multimodalHistory[multimodalHistory.length - 1];
  const mods = latest.value.modalities || {};
  const entries = Object.entries(mods);
  multimodalChart.data.labels = entries.map(([k]) => k);
  multimodalChart.data.datasets[0].data = entries.map(([, v]) => v);
  multimodalChart.update();
  document.querySelector('#multimodalStats .stat-value').textContent = latest.value.diversity.toFixed(2);
}

function renderPrompt() {
  if (promptHistory.length === 0) return;
  const latest = promptHistory[promptHistory.length - 1];
  const types = latest.value.types || {};
  const entries = Object.entries(types);
  promptChart.data.labels = entries.map(([k]) => k);
  promptChart.data.datasets[0].data = entries.map(([, v]) => v);
  promptChart.update();
  document.querySelector('#promptStats .stat-value').textContent = latest.value.count;
}

function renderCognitive() {
  if (cognitiveHistory.length === 0) return;
  const data = cognitiveHistory.map(h => h.value.score);
  const labels = cognitiveHistory.map((_, i) => '#' + (i + 1));
  cognitiveChart.data.labels = labels;
  cognitiveChart.data.datasets[0].data = data;
  cognitiveChart.update();
  const latest = cognitiveHistory[cognitiveHistory.length - 1];
  document.querySelector('#cognitiveStats .stat-value').textContent = latest.value.score + '%';
}

function renderReasoning() {
  const panel = document.getElementById('reasoningPanel');
  const agentColors = {
    ResearchAgent: '#3b82f6',
    StructuralPedagogicalAgent: '#22c55e',
    AdaptiveLearningAgent: '#a855f7',
    MultimodalPlanningAgent: '#f59e0b',
    PromptEngineeringAgent: '#f43f5e',
    ConsistencyAgent: '#06b6d4',
    ConsensusMediator: '#22c55e',
  };
  let html = '';
  for (let i = 0; i < reasoningSteps.length; i++) {
    const s = reasoningSteps[i];
    const isLast = i === reasoningSteps.length - 1;
    const color = agentColors[s.agent] || '#64748b';
    html += `<div class="reasoning-step ${isLast ? 'active' : ''}">`;
    html += `<div class="reasoning-dot" style="background:${color};${isLast ? 'box-shadow:0 0 8px '+color : ''}"></div>`;
    html += `<div style="display:flex;align-items:center;gap:6px;margin-bottom:4px;">`;
    html += `<span class="agent-badge" style="background:${color};">${s.agent.replace(/([A-Z])/g, ' $1').trim()}</span>`;
    html += `<span style="color:#475569;font-size:.65rem;">#${s.step}</span></div>`;
    html += `<p style="color:#e2e8f0;font-size:.7rem;margin-bottom:4px;">${s.reasoning}</p>`;
    html += `<div class="signal-text">Señal: ${s.signal}</div>`;
    html += `<div class="decision-text">Decisión: ${s.decision}</div>`;
    if (Object.keys(s.evidence).length > 0) {
      html += `<details><summary>Evidencia</summary><pre class="evidence">${JSON.stringify(s.evidence, null, 1)}</pre></details>`;
    }
    html += '</div>';
  }
  panel.innerHTML = html;
  panel.scrollTop = panel.scrollHeight;
}

function renderConsensus() {
  if (consensusHistory.length === 0) return;
  const data = consensusHistory.map(h => h.confidence);
  const labels = consensusHistory.map((_, i) => '#' + (i + 1));
  consensusTrendChart.data.labels = labels;
  consensusTrendChart.data.datasets[0].data = data;
  consensusTrendChart.update();

  const latest = consensusHistory[consensusHistory.length - 1];
  const badge = latest.unanimous ? 'badge-green' : 'badge-amber';
  const label = latest.unanimous ? 'UNÁNIME' : 'MAYORÍA';
  document.getElementById('consensusStats').innerHTML = `
    <div style="display:flex;justify-content:space-around;margin-top:8px;">
      <div><span style="color:#64748b;font-size:.7rem;">Decisión</span><br><span class="badge ${badge}" style="font-size:.8rem;">${label}</span></div>
      <div><span style="color:#64748b;font-size:.7rem;">Confianza</span><br><span style="color:#e2e8f0;font-size:1.1rem;font-weight:700;">${(latest.confidence * 100).toFixed(0)}%</span></div>
      <div><span style="color:#64748b;font-size:.7rem;">Votantes</span><br><span style="color:#e2e8f0;font-size:1.1rem;font-weight:700;">${latest.voter_count || latest.voter_breakdown ? Object.keys(latest.voter_breakdown || {}).length : 0}</span></div>
    </div>`;
  consensusDistChart.data.datasets[0].data = [
    latest.decision === 'approved' ? 1 : 0,
    latest.decision === 'rejected' ? 1 : 0,
    0,
  ];
  consensusDistChart.update();
}

function renderNarrative() {
  if (narrativeHistory.length === 0) return;
  const latest = narrativeHistory[narrativeHistory.length - 1];
  const val = latest.value;
  let html = '';
  if (val.has_narrative) {
    html += `<p style="color:#e2e8f0;font-size:.8rem;font-style:italic;margin-bottom:8px;">Hilo narrativo activo (${val.length} chars)</p>`;
    if (val.coherence_score !== null && val.coherence_score !== undefined) {
      const pct = (val.coherence_score * 100).toFixed(0);
      const color = val.coherence_score > 0.7 ? '#22c55e' : val.coherence_score > 0.4 ? '#f59e0b' : '#ef4444';
      html += `<div style="display:flex;align-items:center;gap:8px;">
        <span style="color:#64748b;font-size:.7rem;">Coherencia:</span>
        <div style="flex:1;height:6px;background:#334155;border-radius:3px;">
          <div style="width:${pct}%;height:100%;background:${color};border-radius:3px;transition:width 0.5s;"></div>
        </div>
        <span style="color:#e2e8f0;font-size:.7rem;font-weight:600;">${pct}%</span>
      </div>`;
    }
  } else {
    html = `<p style="color:#64748b;font-size:.7rem;">Sin hilo narrativo establecido</p>`;
  }
  document.getElementById('narrativeContainer').innerHTML = html;
}

function renderPacing() {
  if (pacingHistory.length === 0) return;
  const latest = pacingHistory[pacingHistory.length - 1];
  document.getElementById('pacingContainer').innerHTML = `
    <div style="display:flex;align-items:center;gap:8px;font-size:.75rem;">
      <span class="badge badge-amber" style="font-size:.7rem;">${latest.delta}</span>
      <span style="color:#64748b;">por</span>
      <span style="color:#e2e8f0;">${latest.agent}</span>
    </div>`;
}

function renderMisconceptions() {
  if (misconceptionHistory.length === 0) return;
  const latest = misconceptionHistory[misconceptionHistory.length - 1];
  const topics = latest.value.topics || [];
  let html = `<div style="color:#64748b;font-size:.7rem;margin-bottom:4px;">${latest.value.count} detectadas</div>`;
  html += topics.map(t => `<span class="badge badge-amber" style="font-size:.65rem;margin:2px;">${t.slice(0, 30)}</span>`).join(' ');
  document.getElementById('misconceptionsContainer').innerHTML = html;
}

function renderMemory() {
  if (memoryEvents.length === 0) return;
  let html = '';
  for (const ev of memoryEvents) {
    html += `<div style="display:flex;align-items:center;gap:6px;padding:3px 0;font-size:.7rem;border-bottom:1px solid #1e293b;">
      <span style="color:#475569;">#${ev.step}</span>
      <span class="badge badge-green" style="font-size:.6rem;">${ev.operation}</span>
      <span style="color:#94a3b8;flex:1;overflow:hidden;text-overflow:ellipsis;">${ev.key}</span>
    </div>`;
  }
  document.getElementById('memoryEvents').innerHTML = html;
}

function renderComplete(summary) {
  console.log('Replay complete:', summary);
}

// ── Tab switching ────────────────────────────────────────────
document.querySelectorAll('.tab').forEach(tab => {
  tab.addEventListener('click', () => {
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(tc => tc.style.display = 'none');
    tab.classList.add('active');
    document.getElementById('tab-' + tab.dataset.tab).style.display = '';
  });
});
</script>
</body>
</html>
"""
