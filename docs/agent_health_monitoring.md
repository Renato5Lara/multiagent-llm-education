# Agent Health Monitoring System — Design Document

## 1. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                    AgentHealthMonitor (Orchestrator)                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────────┐   │
│  │  Health   │  │ Anomaly  │  │Behavioral│  │   MetaMonitor    │   │
│  │  Scorer   │  │  Engine  │  │ Monitor  │  │(FP / Overhead /  │   │
│  │           │  │          │  │          │  │  Amplification)  │   │
│  └────┬──────┘  └────┬─────┘  └────┬─────┘  └────────┬─────────┘   │
│       │              │              │                  │            │
│       ▼              ▼              ▼                  ▼            │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    EventBus (internal)                      │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
           │                      │                        │
           ▼                      ▼                        ▼
┌──────────────┐   ┌────────────────────┐   ┌─────────────────────┐
│ Consensus    │   │ CircuitBreaker     │   │ SwarmDiagnostics    │
│ Engine       │   │ Registry           │   │ Engine              │
│ (vote events)│   │ (state transitions)│   │ (detectors/metrics) │
└──────────────┘   └────────────────────┘   └─────────────────────┘
           │                      │                        │
           ▼                      ▼                        ▼
    DiagnosticEvent         BreakerHealth            AnomalySignal
    (event_type:           (health snapshot)         (detection)
     health:*)
```

### Design Principles

1. **Non-invasive**: Monitor wraps/intercepts, never modifies core consensus or circuit breaker internals.
2. **Layered**: Health scoring is a separate concern from anomaly detection. The scorer consumes signals from detectors.
3. **Bounded memory**: Circular buffers with configurable max sizes. No unbounded growth.
4. **Self-aware**: MetaMonitor tracks the monitoring system itself (false positives, overhead, feedback loops).
5. **Graceful degradation**: If the monitor itself fails, the swarm continues operating (fail-open).

---

## 2. Core Data Model

### 2.1 AgentHealthProfile

```python
@dataclass
class AgentHealthProfile:
    agent_name: str
    health_score: float            # 0.0 (dead) to 1.0 (perfect)
    degradation_level: DegradationLevel
    behavioral_baseline: BehavioralBaseline
    recent_signals: list[HealthSignal]
    sliding_stats: AgentSlidingStats
    cognitive_drift: float         # 0.0 = no drift, 1.0 = complete drift
    last_updated: datetime
```

### 2.2 DegradationLevel

```python
class DegradationLevel(IntEnum):
    NONE = 0       # health_score >= 0.8
    MILD = 1       # health_score >= 0.6
    MODERATE = 2   # health_score >= 0.4
    SEVERE = 3     # health_score >= 0.2
    CRITICAL = 4   # health_score < 0.2
```

### 2.3 HealthSignal

A unified signal carrying both anomaly data and health-relevant metrics:

```python
@dataclass
class HealthSignal:
    signal_type: str                # "timeout", "divergence", "hallucination", "slow", ...
    agent_name: str
    severity: float                 # 0.0–1.0
    metric_value: float
    timestamp: datetime
    evidence: dict
    source: str                     # detector name or "scorer"
```

### 2.4 BehavioralBaseline

```python
@dataclass
class BehavioralBaseline:
    approval_rate: float            # historical average
    confidence_mean: float
    confidence_std: float
    latency_p50: float             # ms
    latency_p95: float
    consistency_score: float       # how consistent are decisions
    sample_count: int
    window_minutes: int = 60
```

### 2.5 AgentSlidingStats

```python
@dataclass
class AgentSlidingStats:
    recent_decisions: deque[tuple[str, float, datetime]]  # (decision, confidence, ts)
    recent_latencies: deque[float]
    recent_errors: deque[str]
    recent_anomalies: deque[AnomalySignal]
    max_samples: int = 100
```

---

## 3. Health Scoring System

### 3.1 Scoring Formula

```
health_score = base_score - penalty_total + recovery_bonus

base_score = w_consensus * consensus_reliability
           + w_latency   * latency_score
           + w_consist   * consistency_score
           + w_calibr    * calibration_score

penalty_total = Σ(signal.severity * w_signal_type * decay_factor(t))

recovery_bonus = recovery_rate * time_since_last_anomaly / window
```

Default weights (configurable per agent type):

| Component | Weight | Range |
|---|---|---|
| Consensus reliability | 0.35 | [0, 1] |
| Latency score | 0.20 | [0, 1] |
| Consistency | 0.25 | [0, 1] |
| Calibration | 0.20 | [0, 1] |

Signal penalty weights:

| Signal Type | Weight | Source |
|---|---|---|
| circuit_breaker_open | 0.30 | CircuitBreakerRegistry |
| timeout | 0.25 | ConsensusTimeoutPolicy |
| hallucination | 0.35 | HallucinationDetector |
| divergence | 0.20 | AgentDivergenceDetector |
| slow_response | 0.15 | SlowAgentDetector |
| consensus_instability | 0.25 | ConsensusInstabilityDetector |
| cognitive_drift | 0.20 | CognitiveDriftDetector |
| propagation_anomaly | 0.15 | PropagationAnomalyDetector |

### 3.2 Decay Function

Recent signals matter more (exponential decay):

```python
def decay_factor(t: datetime, now: datetime, half_life_minutes: float = 10.0) -> float:
    elapsed = (now - t).total_seconds() / 60.0
    return 2.0 ** (-elapsed / half_life_minutes)
```

### 3.3 Score → Degradation Level Mapping

```
health_score >= 0.80 → NONE
health_score >= 0.60 → MILD     (weight adjustment, increased monitoring)
health_score >= 0.40 → MODERATE (circuit breaker sensitivity increase)
health_score >= 0.20 → SEVERE   (vote weight reduction, possible quarantine)
health_score <  0.20 → CRITICAL (circuit breaker isolation bypass, manual review)
```

### 3.4 HealthScoreVoter — Weight-Aware Voting Proxy

```python
class HealthScoreVoter:
    """Wraps a voter to apply health score as a dynamic weight.

    Degradation mapping:
        NONE     → weight = 1.0
        MILD     → weight = 0.9
        MODERATE → weight = 0.7
        SEVERE   → weight = 0.4
        CRITICAL → weight = 0.0 (abstain)
    """
```

Integrates with `ConsensusResult.weights_used` for transparency.

---

## 4. Detection Subsystems

Each detector follows the existing `BaseDetector` ABC and integrates with the `SwarmDiagnosticsEngine`.

### 4.1 DegradedAgentDetector

**Purpose**: Detect agents with consistently poor performance across multiple dimensions.

**Triggers**:
- Health score stays below threshold for entire window
- Multiple circuit breaker OPEN events in window
- High error rate (> threshold) sustained over window
- Consecutive timeouts above threshold

**Signals**:
- `DEGRADED_AGENT` (WARNING / CRITICAL based on severity)
- `AGENT_FAILURE_ACCELERATION` (WARNING — increasing failure rate)

**Implementation**:

```python
class DegradedAgentDetector(BaseDetector):
    name = "degraded_agent"

    def __init__(self, health_threshold=0.4, min_window_events=5, window_seconds=300.0):
        ...

    def analyze(self, events, *, metrics=None) -> list[AnomalySignal]:
        # Group by agent
        # For each agent:
        #   1. Count circuit breaker open events
        #   2. Count timeouts from consensus events
        #   3. Measure sustained error rate
        #   4. If multiple dimensions indicate degradation → signal
```

### 4.2 HallucinationDetector

**Purpose**: Detect agents producing outputs that are inconsistent, overconfident, or unreliable.

**Detection Dimensions**:

| Dimension | Metric | Threshold |
|---|---|---|
| Overconfidence | High confidence + low approval rate | confidence > 0.8 AND approval < 0.3 |
| Decision flipping | Alternating approve/reject on similar inputs | flip_rate > 0.4 |
| Confidence calibration error | |confidence - approval_rate| | error > 0.5 |
| Output quality regression | Decreasing quality score over time | negative slope > 0.1/window |

**Signals**:

- `HALLUCINATION_LIKELY` (CRITICAL — overconfidence pattern)
- `DECISION_FLIPPING` (WARNING — erratic behavior)
- `CALIBRATION_DRIFT` (WARNING — confidence no longer matches reality)

**Implementation**:

```python
class HallucinationDetector(BaseDetector):
    name = "hallucination_detector"

    def __init__(self, overconfidence_threshold=0.3, flip_window=10, calibration_error_threshold=0.5):
        ...

    def _detect_overconfidence(self, events: list) -> list[AnomalySignal]:
        # Find voters with high average confidence but low approval rate
        # This suggests the agent is confidently wrong

    def _detect_flipping(self, events: list) -> list[AnomalySignal]:
        # Sequence analysis: look for A-B-A-B patterns in decisions
        # Count ratio of adjacent-opposing decisions

    def _detect_calibration_drift(self, events: list) -> list[AnomalySignal]:
        # Compare confidence vs actual approval rate
        # Large gap = poor calibration
```

### 4.3 SlowAgentDetector

**Purpose**: Detect agents with problematic latency.

**Triggers**:
- P95 latency exceeds threshold
- Latency trend is increasing (positive slope)
- Timeout frequency > threshold
- Cascading delay impact (this agent's slowness is delaying others)

**Signals**:
- `SLOW_AGENT` (WARNING — P95 exceeded)
- `LATENCY_TREND_INCREASING` (WARNING — getting worse)
- `CASCADING_SLOWDOWN` (CRITICAL — affecting other agents)

**Implementation**:

```python
class SlowAgentDetector(BaseDetector):
    name = "slow_agent"

    def __init__(self, latency_p95_threshold_ms=5000.0, min_samples=10, trend_window=20):
        ...

    def analyze(self, events, *, metrics=None) -> list[AnomalySignal]:
        # Group vote events by source agent
        # For each agent with enough samples:
        #   1. Compute P95 latency
        #   2. Compute latency trend (linear regression slope over window)
        #   3. Count timeout events for this agent
        #   4. Check cascading impact (are other agents waiting on this one?)
```

### 4.4 DivergenceDetector (Extended)

Extends the existing `AgentDivergenceDetector` with additional dimensions.

**New Dimensions**:
- **Cross-agent divergence**: An agent's decisions increasingly differ from the swarm majority
- **Confidence divergence**: Agent's confidence pattern diverges from peer group
- **Specialization erosion**: Domain affinity weakens over time

**Signals** (new, in addition to existing):
- `CROSS_AGENT_DIVERGENCE` (WARNING)
- `CONFIDENCE_DIVERGENCE` (INFO)
- `SPECIALIZATION_SHIFT` (INFO)

### 4.5 ConsensusInstabilityDetector (Extended)

Extends the existing `QuorumInstabilityDetector` with broader instability detection.

**New Dimensions**:
- **Approval rate volatility**: Variance of approval rate over time exceeds threshold
- **Confidence collapse**: Average confidence across all voters drops sharply
- **Polarization index**: Votes split into two opposing camps (approve vs reject) with few abstain
- **Entropy measurement**: Shannon entropy of vote distribution

**Signals** (new):
- `APPROVAL_VOLATILITY` (WARNING)
- `CONFIDENCE_COLLAPSE` (CRITICAL)
- `SWARM_POLARIZATION` (WARNING)
- `CONSENSUS_ENTROPY_HIGH` (INFO)

```python
class ConsensusInstabilityDetector(BaseDetector):
    name = "consensus_instability"

    def __init__(self, volatility_threshold=0.3, entropy_threshold=0.8, polarization_ratio=0.8):
        ...

    def analyze(self, events, *, metrics=None) -> list[AnomalySignal]:
        # Group consensus events
        # For each consensus run:
        #   1. Compute approval rate variance over window
        #   2. Track average confidence level
        #   3. Compute polarization (frac of votes in two largest camps)
        #   4. Compute Shannon entropy of vote distribution
        #   5. Detect trends across consecutive runs
```

### 4.6 CognitiveDriftDetector

**Purpose**: Detect long-term behavioral changes in agents (concept drift).

**Mechanism**:
- Maintains two windows: recent (short-term) and baseline (long-term)
- Compares behavioral distributions using statistical tests
- Tracks gradual shifts rather than sudden changes

**Detection Dimensions**:
- **Vote distribution drift**: Kolmogorov-Smirnov test on recent vs baseline vote decisions
- **Confidence drift**: Moving average of confidence diverging from long-term baseline
- **Latency drift**: Gradual slowdown that wouldn't trigger the fast detector
- **Threshold drift**: Agent's effective decision boundary shifting

**Signals**:
- `COGNITIVE_DRIFT_DETECTED` (WARNING)
- `THRESHOLD_SHIFT` (INFO — agent boundary moved)
- `CONFIDENCE_TREND` (INFO — gradual confidence change)

```python
class CognitiveDriftDetector(BaseDetector):
    name = "cognitive_drift"

    def __init__(self, baseline_window=100, recent_window=20, ks_threshold=0.3, drift_rate_threshold=0.05):
        ...

    def _ks_test_vote_distribution(self, baseline, recent) -> float:
        # Two-sample Kolmogorov-Smirnov statistic
        # Returns D statistic (max vertical deviation between ECDFs)

    def _compute_drift_rate(self, values: list[float]) -> float:
        # Linear regression slope over time
        # Positive = drifting in one direction
```

### 4.7 PropagationAnomalyDetector (Extended)

Extends the existing `PropagationFailureDetector` with agent-level tracking.

**New Dimensions**:
- **Agent propagation failure rate**: How often an agent's events fail to propagate
- **Propagation delay per agent**: Average time for agent's events to reach consumers
- **Dead letter tracking**: Events from specific agents ending up in dead letter queues

**Signals**:
- `AGENT_PROPAGATION_FAILURE` (WARNING)
- `PROPAGATION_DELAY_INCREASING` (INFO)

---

## 5. Behavioral Monitoring

### 5.1 BehavioralBaselineManager

Maintains and updates per-agent behavioral baselines.

```python
class BehavioralBaselineManager:
    """Maintains rolling baselines for each agent.

    Uses exponential moving average for efficient online updating.
    """

    def __init__(self, alpha_approval=0.05, alpha_latency=0.1, max_agents=50):
        self._baselines: dict[str, BehavioralBaseline] = {}
        self._alpha_approval = alpha_approval  # EMA smoothing factor
        self._alpha_latency = alpha_latency

    def update(self, agent_name: str, decision: str, confidence: float,
               latency_ms: float | None = None) -> BehavioralBaseline:
        # Update EMA for approval rate
        # Update EMA for latency stats
        # Update consistency score (variance of decisions)

    def get_baseline(self, agent_name: str) -> BehavioralBaseline | None:
        ...

    def compute_deviation(self, agent_name: str, current_approval: float) -> float:
        # How many std devs from baseline
        ...
```

### 5.2 Pattern Lifecycle

```
Normal → Observed (suspicious) → Flagged → Confirmed (anomaly signal)
                                → Dismissed (false positive, feed MetaMonitor)
```

This lifecycle prevents alert fatigue by requiring multi-cycle confirmation.

---

## 6. Collective Stability Metrics

Computed swarm-wide, not per-agent.

### 6.1 Metrics

| Metric | Formula | Range | Meaning |
|---|---|---|---|
| Consensus convergence rate | `approvals / (approvals + rejects)` per run | [0, 1] | How often consensus is reached cleanly |
| Agreement entropy | `-Σ p_i * log₂(p_i)` for vote distribution | [0, log₂(N)] | High = fragmented opinions |
| Polarization index | `|approve_frac - reject_frac|` | [0, 1] | 0 = balanced, 1 = unanimous |
| Stability score | `1 - anomaly_rate / max_rate` | [0, 1] | 1 = perfectly stable |
| Anomaly density | `active_anomalies / time_window` | [0, ∞) | Anomalies per unit time |
| Trust coherence | variance of trust scores across agents | [0, ∞) | Low = consistent trust |
| Decision latency P95 | P95 of time to reach consensus | [0, ∞) | ms |
| Swarm throughput | `consensus_decisions / time_window` | [0, ∞) | Decisions per minute |

### 6.2 CollectiveStabilityScorer

```python
class CollectiveStabilityScorer:
    def compute(self, engine: SwarmDiagnosticsEngine,
                profiles: dict[str, AgentHealthProfile]) -> CollectiveStabilityReport:
        ...

@dataclass
class CollectiveStabilityReport:
    stability_score: float
    agreement_entropy: float
    polarization_index: float
    convergence_rate: float
    anomaly_density: float
    decision_latency_p95: float
    swarm_throughput: float
    at_risk_agents: list[str]
    degradation_distribution: dict[DegradationLevel, int]
    recommendation: str
```

---

## 7. Adaptive Degradation

### 7.1 AdaptiveDegradationManager

Coordinates degradation responses across systems:

```python
class AdaptiveDegradationManager:
    def __init__(self, registry: CircuitBreakerRegistry,
                 consensus_engine: ConsensusEngine,
                 health_monitor: AgentHealthMonitor):
        ...

    def apply_degradation(self, profile: AgentHealthProfile) -> None:
        level = profile.degradation_level
        agent = profile.agent_name

        if level >= DegradationLevel.SEVERE:
            # Reduce circuit breaker thresholds for this agent
            # Lower failure_threshold, shorter recovery_timeout
            self._registry._breakers[agent].force_reconfigure(...)

        if level >= DegradationLevel.CRITICAL:
            # Isolate the agent entirely
            self._registry._breakers[agent].force_isolate(
                f"Health score {profile.health_score:.2f} below critical"
            )

    def recover_agent(self, agent_name: str) -> None:
        # Gradual reintegration
        # 1. Force-close circuit breaker
        # 2. Set health score to conservative starting value (e.g., 0.5)
        # 3. Mark agent for increased monitoring
```

### 7.2 HealthScore Feedback to ConsensusEngine

The `HealthScoreVoter` wraps each voter and weights its vote by health:

```python
class HealthScoreVoter:
    def vote(self, ctx):
        if self._profile.degradation_level >= DegradationLevel.CRITICAL:
            return ConsensusVote(ABSTAIN, 0.0, "Agent health critical")

        weight = DEGRADATION_WEIGHTS[self._profile.degradation_level]
        vote = self._voter.vote(ctx)
        vote.weights_used[weight] = vote.weights_used.get(weight, []) + [self._voter.voter_name]
```

---

## 8. Swarm Observability

### 8.1 HealthDashboard API

```
GET /api/swarm/health/agents          → list[AgentHealthProfile]
GET /api/swarm/health/agents/{name}   → AgentHealthProfile (detailed)
GET /api/swarm/health/collective      → CollectiveStabilityReport
GET /api/swarm/health/history/{name}  → time-series of health scores
GET /api/swarm/health/meta            → MetaMonitorReport
```

### 8.2 Event types

New `DiagnosticEvent` event types for the health monitoring system:

```
health:score_updated      → agent, score, level
health:degradation_change  → agent, from_level, to_level
health:recovery            → agent
health:meta:false_positive → detector, signal_id, corrected
health:meta:overhead       → monitor_latency, memory_usage
health:meta:amplification  → loop_detected, action_taken
```

### 8.3 Integration with Existing Systems

| System | Integration Point | Data Flow |
|---|---|---|
| SwarmDiagnosticsEngine | Register new detectors, consume events | Events → HealthSignals |
| CircuitBreakerRegistry | Health affects breaker config | Health → DegradationManager → Breaker config |
| ConsensusEngine | HealthScoreVoter wraps voters | Voter → HealthScoreVoter → Weighted vote |
| ConsensusTimeoutPolicy | Health influences adaptive timeouts | Latency metrics → Timeout policy tuning |
| FastAPI | Health dashboard endpoints | Monitor → API → JSON |

---

## 9. MetaMonitor: Self-Aware Monitoring

### 9.1 False Positive Detection

```python
class FalsePositiveDetector(BaseDetector):
    """Detects when the monitoring system itself generates false alarms.

    Strategies:
    1. Cross-validation: An anomaly is confirmed only when 2+ detectors agree
    2. Temporal coherence: Isolated single-event anomalies are low-confidence
    3. Historical comparison: Same anomaly pattern that previously was false
    4. Outcome tracking: Was action taken? Did it help? If not → FP
    """

    name = "false_positive_detector"

    def __init__(self, cross_validation_min=2, fp_tracking_window=100):
        self._false_positives: dict[str, int] = {}  # detector_name → FP count
        self._anomaly_outcomes: deque[AnomalyOutcome] = deque(maxlen=fp_tracking_window)

    def analyze(self, events, *, metrics=None) -> list[AnomalySignal]:
        # Track outcomes: was action taken? Did health improve?
        # If anomaly triggered but no action taken or health unchanged → potential FP
        # Maintain per-detector FP rate
        # Emit signal when a detector's FP rate exceeds threshold

    def record_outcome(self, signal: AnomalySignal, action_taken: bool,
                       health_improved: bool) -> None:
        # Called by orchestrator after evaluating intervention results
        ...
```

**Rules**:
- Single-detector anomaly = `confidence=0.3` (low)
- Cross-validated (2+ detectors agree) = `confidence=0.7` (medium)
- Cross-validated + temporal persistence (seen in 3+ consecutive windows) = `confidence=0.95` (high)
- Detector with FP rate > 20% → auto-disable, emit `DETECTOR_FP_HIGH` signal

### 9.2 Monitoring Overhead Detection

```python
class MonitoringOverheadDetector(BaseDetector):
    """Measures the cost of monitoring itself and detects when it's excessive.

    Metrics tracked:
    - Time spent in monitor.analyze() per cycle
    - Memory used by event buffers
    - Number of active detectors
    - Event ingestion rate vs processing rate (backlog)
    """

    name = "monitoring_overhead"

    def __init__(self, max_analyze_time_ms=100.0, max_event_buffer=10000,
                 max_detectors=30):
        self._cycle_times: deque[float] = deque(maxlen=100)
        ...

    def analyze(self, events, *, metrics=None) -> list[AnomalySignal]:
        # If analyze() takes too long → sampling rate needed
        # If buffer is too large → increase sampling or reduce retention
        # Too many detectors → suggest merging or tiering
```

**Adaptive Sampling**:
```python
class AdaptiveSampler:
    """Reduces monitoring granularity when swarm is healthy."""

    def __init__(self, hysteresys_factor=0.5):
        self._sampling_rate = 1.0  # 1.0 = all events, 0.1 = 10% of events
        self._healthy_window = 0

    def adjust(self, health_status: str, overhead_ms: float) -> float:
        if health_status == "healthy" and overhead_ms > 50:
            self._sampling_rate = max(0.1, self._sampling_rate * 0.8)
        elif health_status in ("degraded", "critical"):
            self._sampling_rate = min(1.0, self._sampling_rate * 1.5)
        return self._sampling_rate
```

### 9.3 Feedback Amplification Detection

```python
class FeedbackAmplificationDetector(BaseDetector):
    """Detects when monitoring responses create feedback loops
    that amplify rather than dampen instability.

    Known anti-patterns:
    1. Monitor detects slow agent → circuit breaker opens → reduced quorum →
       consensus fails → more monitoring events → more circuit breakers → cascade
    2. Monitor detects high error rate → lower thresholds → more triggers →
       more errors logged → thresholds lowered further → death spiral
    3. Degradation → weight reduction → consensus failure → more degradation
    """

    name = "feedback_amplification"

    def __init__(self, cascade_threshold=3, time_window_seconds=60.0,
                 max_interventions_per_window=5):
        self._intervention_log: deque[Intervention] = deque(maxlen=100)
        ...

    def analyze(self, events, *, metrics=None) -> list[AnomalySignal]:
        # Pattern 1: Cascading breaker opens
        # Pattern 2: Threshold adjustments followed by more triggers
        # Pattern 3: Repeated degradation escalation

        # Correlation analysis:
        #   intervention → outcome → more intervention → worse outcome
```

**Mitigation Strategies**:

| Pattern | Mitigation |
|---|---|
| Cascading circuit breakers | Damping factor: stagger recovery, add jitter to recovery timeout |
| Threshold death spiral | Hysteresis: different thresholds for entering vs exiting degradation |
| Degradation reinforcement | Cooldown: minimum time between degradation level changes |
| Consensus failure cycle | Emergency quorum: bypass degraded agents and use remaining quorum |

---

## 10. Implementation Plan

### Phase 1: Foundation (files under `app/core/agent_health/`)

1. `agent_health_profile.py` — Core data model (AgentHealthProfile, DegradationLevel, HealthSignal, BehavioralBaseline)
2. `health_scorer.py` — HealthScore formula, scoring weights, decay function
3. `behavioral_baseline.py` — BehavioralBaselineManager, EMA computation
4. `agent_health_monitor.py` — AgentHealthMonitor orchestrator (event ingestion, signal processing, health update cycle)
5. `adaptive_degradation.py` — AdaptiveDegradationManager, DegradationLevel → action mapping
6. `collective_stability.py` — CollectiveStabilityScorer, stability metrics computation

### Phase 2: Extended Detectors (files under `app/swarm_diagnostics/detectors/`)

7. `degraded_agent.py` — DegradedAgentDetector
8. `hallucination.py` — HallucinationDetector
9. `slow_agent.py` — SlowAgentDetector
10. Update `divergence.py` — Extend AgentDivergenceDetector
11. `consensus_instability.py` — ConsensusInstabilityDetector
12. `cognitive_drift.py` — CognitiveDriftDetector

### Phase 3: MetaMonitor (files under `app/core/agent_health/`)

13. `meta_monitor.py` — MetaMonitor orchestrator
14. `false_positive_detector.py` — FalsePositiveDetector
15. `monitoring_overhead.py` — AdaptiveSampler, MonitoringOverheadDetector
16. `feedback_amplification.py` — FeedbackAmplificationDetector, mitigations

### Phase 4: Integration

17. `health_score_voter.py` — HealthScoreVoter wrapping BaseVoter
18. Register all new detectors in `swarm_diagnostics/core.py`
19. Add new `AnomalyType` values in `anomaly_signal.py`
20. FastAPI health dashboard endpoints

### Phase 5: Tests

21. `tests/test_agent_health.py` — Per-component and integration tests
22. `tests/test_health_detectors.py` — Detector tests (following existing patterns)
23. `tests/test_meta_monitor.py` — MetaMonitor tests

---

## 11. Existing Code Integration Map

| New Component | Extends / Consumes | Location |
|---|---|---|
| AgentHealthMonitor | Consumes DiagnosticEvent from SwarmDiagnosticsEngine | `app/core/agent_health/` (new) |
| HealthScorer | Consumes AnomalySignal from all detectors | `app/core/agent_health/` (new) |
| BehavioralBaselineManager | Reads vote events via SwarmMetricsCollector | `app/core/agent_health/` (new) |
| AdaptiveDegradationManager | Calls CircuitBreakerRegistry methods | `app/core/agent_health/` (new) |
| HealthScoreVoter | Wraps BaseVoter, feeds ConsensusResult.weights_used | `app/core/agent_health/` (new) |
| DegradedAgentDetector | BaseDetector ABC, registered in SwarmDiagnosticsEngine | `app/swarm_diagnostics/detectors/` (new) |
| HallucinationDetector | BaseDetector ABC | `app/swarm_diagnostics/detectors/` (new) |
| SlowAgentDetector | BaseDetector ABC | `app/swarm_diagnostics/detectors/` (new) |
| ConsensusInstabilityDetector | BaseDetector ABC + extends QuorumInstabilityDetector concept | `app/swarm_diagnostics/detectors/` (new) |
| CognitiveDriftDetector | BaseDetector ABC | `app/swarm_diagnostics/detectors/` (new) |
| AnomalyType (new values) | Enum in `anomaly_signal.py` | Edit existing file |
| SwarmDiagnosticsEngine._register_default_detectors | Add new detector instances | Edit existing file |
| ConsensusResult.weights_used | Already exists, HealthScoreVoter populates it | No change needed |
| CircuitBreakerRegistry | AdaptiveDegradationManager calls force_reconfigure/force_isolate | No change needed |
| SwarmMetricsCollector | BehavioralBaselineManager reads vote counts | No change needed |

---

## 12. Risk Mitigation

### 12.1 Monitoring System Failure

If the health monitor itself fails:
- **Breakers fail-open**: Circuit breaker registry continues operating independently
- **Voters fail-open**: HealthScoreVoter defaults to weight = 1.0 if health score unavailable
- **Detectors fail-closed**: Individual detector failures are caught and logged; non-failing detectors continue

### 12.2 Feedback Loop Prevention

- **Hysteresis**: Degradation escalation requires sustained signal > threshold for N consecutive windows
- **Cooldown**: Minimum 2 windows between degradation level increases
- **Rate limiting**: Maximum 1 intervention per agent per window
- **Damping**: Recovery actions use half the intensity of degradation actions

### 12.3 False Positive Budget

Each detector has a configurable false positive budget:
- If FP rate > 20% over 100 signals → detector auto-disables, emits `DETECTOR_DISABLED` signal
- If FP rate 10–20% → detector confidence is reduced by 50%
- Auto-reenable after 24h or manual override via API
