# Reproducibilidad — UPAO-MAS-EDU v1.0.0

Protocolo para garantizar que el sistema produce resultados
consistentes e idénticos en cualquier entorno controlado.

---

## 1. Principios de Reproducibilidad

1. **Dependencias congeladas** — `requirements.lock` para Python,
   `package-lock.json` para frontend
2. **Semillas deterministas** — Experimentos usan seeds fijas por condición
3. **Consenso sin aleatoriedad** — Votación basada en DB state (no rand)
4. **Memoria determinista** — `compute_memory_confidence` usa recency-weighted
   average, no sampling
5. **Tracing con因果关系** — Causation chain fija por evento
6. **Propagación TTL** — Hop counting determinista, sin loops
7. **Benchmark con condiciones fijas** — 5 condiciones, 10 seeds cada una

---

## 2. Protocolo de Reproducibilidad

### 2.1 Setup Reproducible

```bash
# 1. Clonar en commit congelado
git checkout v1.0.0

# 2. Python environment
python3.12 -m venv .venv
source .venv/bin/activate
pip install --no-cache-dir -r backend/requirements.lock

# 3. Frontend
cd frontend && npm ci && cd ..

# 4. Base de datos
docker compose up -d postgres
alembic upgrade head
python backend/seed.py
```

### 2.2 Ejecutar Tests

```bash
# Todos los tests
cd backend && python -m pytest tests/ -q

# Tests específicos de propagación
python -m pytest tests/test_propagation_ttl.py -v

# Tests de experimento (benchmark)
python -m pytest tests/test_experiment*.py -v
```

### 2.3 Ejecutar Benchmark Reproducible

```bash
cd backend
python scripts/run_experiment.py --output /tmp/experiment_results
```

El experimento ejecuta 5 condiciones × 10 seeds = 50 runs.
Cada seed produce resultados idénticos entre ejecuciones.

### 2.4 Verificar Determinismo

```bash
# Ejecutar benchmark dos veces
python scripts/run_experiment.py --output /tmp/run1
python scripts/run_experiment.py --output /tmp/run2

# Comparar resultados (deben ser idénticos)
diff -r /tmp/run1 /tmp/run2
```

---

## 3. Propagación Determinista

### 3.1 Hop Counting

- `hop_count` comienza en 0
- Cada `forward()` incrementa en 1 exactamente
- `max_hops` verifica `hop_count >= max_hops`
- Sin off-by-one: hop 0 → forward → hop 1 (primer dispatch real)

### 3.2 TTL

- `ttl_seconds` verifica elapsed desde `created_at`
- `decay_factor^n` para strength depletion
- `min_strength` threshold fijo

### 3.3 Anti-Feedback-Loop

- `visited_agents` set impide visita duplicada
- `visited_events` set impide ciclo DAG
- `FeedbackLoopError` y `DAGCycleError` son deterministas

### 3.4 Garantías

| Propiedad | Garantía |
|-----------|----------|
| Sin loops infinitos | ✅ max_hops + TTL + decay |
| Sin propagación duplicada | ✅ visited_agents/events |
| Sin orphan events | ✅ stop_reason siempre definido |
| Sin race conditions | ✅ state enum inmutable por forward |
| Causalidad correcta | ✅ propagation_id lineage |

---

## 4. Consenso Determinista

### 4.1 Votación

- `MasteryVoter`, `PrereqVoter`, `SequenceVoter`, `TimeVoter`
- Todos basados en DB queries → mismo input = mismo output
- Sin llamadas LLM durante votación de consenso

### 4.2 Fallbacks

- Timeout → fallback vote (ABSTAIN)
- Emergency quorum → aprueba con mayoría simple
- Hung recovery → timeout + cancel cascade
- Sin aleatoriedad en decisiones de fallback

---

## 5. Memoria Compartida Determinista

### 5.1 Escritura

- `publish_observation()` con content-hash dedup
- `confidence = recency * 0.7 + agreement * 0.3`
- `ttl = f(type)` → tabla fija

### 5.2 Resolución de Conflictos

- `resolve_conflict()` → majority + weight averaging
- `merge_observations()` → deterministic field-wise merge
- `lineage_tracker` → evento causal siempre registrado

---

## 6. Diagnóstico Determinista

### 6.1 Detectores

Los 22 detectores de anomalías son funciones puras sobre
listas de `DiagnosticEvent`:

```python
signals = detector.analyze(events)  # → siempre mismo output para mismo input
```

### 6.2 Bug Reports

- `BugDiagnosticsBridge` convierte `AnomalySignal` → `BugReport`
- Mapeo fijo: `propagation_failure` → `BugCategory.PROPAGATION`

---

## 7. Validación de Reproducibilidad

Para verificar que el sistema es reproducible:

```bash
# 1. Validar entorno
python backend/scripts/validate_environment.py

# 2. Tests completos
cd backend && python -m pytest tests/ -q --tb=short

# 3. Benchmark bidireccional
python scripts/run_experiment.py --output /tmp/benchmark_a
python scripts/run_experiment.py --output /tmp/benchmark_b
diff <(sha256sum /tmp/benchmark_a/*) <(sha256sum /tmp/benchmark_b/*)
# Debe retornar 0 (sin diferencias)
```
