"""Instrumentación de latencia y throughput (RNF01/RNF04) — SOLO instrumentación: no declara
cumplimiento de ningún umbral. Percentiles P50/P90/P95/P99 y throughput = N_ok / Δt (asesoría §3.5)."""

from __future__ import annotations

from typing import Sequence


def percentile(values: Sequence[float], p: float) -> float | None:
    """Percentil por interpolación lineal (p en [0,100])."""
    if not values:
        return None
    xs = sorted(values)
    if len(xs) == 1:
        return xs[0]
    pos = (len(xs) - 1) * (p / 100.0)
    lo = int(pos)
    hi = min(lo + 1, len(xs) - 1)
    return xs[lo] + (xs[hi] - xs[lo]) * (pos - lo)


def latency_report(latencies_ms: Sequence[float]) -> dict:
    return {
        "n": len(latencies_ms),
        "p50_ms": percentile(latencies_ms, 50), "p90_ms": percentile(latencies_ms, 90),
        "p95_ms": percentile(latencies_ms, 95), "p99_ms": percentile(latencies_ms, 99),
        "max_ms": max(latencies_ms) if latencies_ms else None,
        "mean_ms": sum(latencies_ms) / len(latencies_ms) if latencies_ms else None,
    }


def throughput_rps(n_ok: int, elapsed_s: float) -> float:
    if elapsed_s <= 0:
        raise ValueError("elapsed_s debe ser > 0")
    return n_ok / elapsed_s
