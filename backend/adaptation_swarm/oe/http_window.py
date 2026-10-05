"""Medición HTTP OFICIAL (L_resp y throughput) desde el registro por petición del generador de carga: ventana estacionaria, sin calentamiento. Funciones PURAS sobre filas ya leídas.

Entrada (`locust_raw_log.py` escribe el CSV durante la corrida de Locust): por petición `t_end_epoch_s`, `response_ms`, `ok`, `timeout`; y por segundo `t_epoch_s`, `loadgen_cpu_percent` (proceso del generador).
La ventana estacionaria empieza `warmup_s` (≥ 10 s) después de la PRIMERA petición completada y termina en la última; es válida solo si dura ≥ `min_window_s` (60 s). Por corrida se reporta: peticiones totales / correctas /
errores / timeouts en la ventana, duración, throughput = correctas / duración, P50, media y P95 de la latencia de las correctas, y la CPU del generador. El indicador oficial de latencia es P95 POR CORRIDA;
la unidad de inferencia es la corrida (varias corridas independientes por sistema/carga), nunca la petición.

`users` > 25 marca el régimen `stress`: sus P95 no contrastan el umbral de 2 s (régimen aprobado ≤ 25 usuarios). Una corrida con la CPU del generador ≥ `LOADGEN_CPU_SATURATION` % de un núcleo se marca
`generator_possibly_bottleneck` (criterio técnico interno): no se descarta en silencio, se reporta para decidir su exclusión con una regla declarada de antemano.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Mapping, Sequence

from adaptation_swarm.metrics.performance import latency_report

WARMUP_S_MIN = 10.0
WINDOW_S_MIN = 60.0
CONTRAST_MAX_USERS = 25
LOADGEN_CPU_SATURATION = 90.0
RNF01_P95_MS = 2000.0
RNF04_RPS, RNF04_MAX_ERROR = 20.0, 0.01


def extract_cycle_metrics(body: Mapping) -> dict:
    """`t_conv_ms` y `k_stop` de la respuesta de AMBOS endpoints, con su forma explícita: la propuesta (`POST /api/adaptation`) los devuelve en el nivel superior; el convencional
    (`POST /api/adaptation/baseline/{system}`) en `metrics` (y no tiene `k_stop`). Una respuesta de otra forma lanza `ValueError`: nunca se asume ni se rellena."""
    if "t_conv_ms" in body:
        return {"shape": "swarm", "t_conv_ms": body["t_conv_ms"], "k_stop": body.get("k_stop")}
    metrics = body.get("metrics")
    if isinstance(metrics, Mapping) and "t_conv_ms" in metrics:
        return {"shape": "baseline", "t_conv_ms": metrics["t_conv_ms"], "k_stop": None}
    raise ValueError("respuesta sin t_conv_ms reconocible (ni nivel superior ni metrics.t_conv_ms)")


def read_raw(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as fh:
        return [{"t_end_epoch_s": float(r["t_end_epoch_s"]), "response_ms": float(r["response_ms"]), "ok": r["ok"] == "1", "timeout": r["timeout"] == "1",
                 "t_conv_ms": float(r["t_conv_ms"]) if r.get("t_conv_ms") else None, "metrics_ok": r.get("metrics_ok", "1") != "0"} for r in csv.DictReader(fh)]


def read_cpu(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as fh:
        return [{"t_epoch_s": float(r["t_epoch_s"]), "loadgen_cpu_percent": float(r["loadgen_cpu_percent"])} for r in csv.DictReader(fh)]


def summarize_run(raw: Sequence[Mapping], cpu: Sequence[Mapping], *, users: int, system: str, run_id: str, warmup_s: float = WARMUP_S_MIN, min_window_s: float = WINDOW_S_MIN) -> dict:
    base = {"run_id": run_id, "system": system, "users": users, "regime": "contrast" if users <= CONTRAST_MAX_USERS else "stress", "warmup_s": warmup_s, "min_window_s": min_window_s,
            "official_measurement": "HTTP end-to-end", "unit": "run"}
    if warmup_s < WARMUP_S_MIN:
        return {**base, "status": "invalid_warmup_below_10s"}
    if not raw:
        return {**base, "status": "no_requests"}
    t0 = min(r["t_end_epoch_s"] for r in raw)
    t1 = max(r["t_end_epoch_s"] for r in raw)
    start = t0 + warmup_s
    win = [r for r in raw if start <= r["t_end_epoch_s"] <= t1]
    duration = t1 - start
    out = {**base, "window_start_epoch_s": start, "window_end_epoch_s": t1, "duration_s": max(duration, 0.0), "requests_total": len(win)}
    if duration < min_window_s:
        return {**out, "status": "invalid_window_shorter_than_min", "requests_total_before_window": len(raw)}
    ok = [r for r in win if r["ok"]]
    lat = [r["response_ms"] for r in ok]
    rep = latency_report(lat)
    err = 1 - len(ok) / len(win) if win else None
    cpus = [c["loadgen_cpu_percent"] for c in cpu if start <= c["t_epoch_s"] <= t1]
    cpu_max = max(cpus) if cpus else None
    return {**out, "status": "ok", "requests_ok": len(ok), "errors": len(win) - len(ok), "timeouts": sum(r["timeout"] for r in win), "error_rate": err,
            "throughput_rps": len(ok) / duration, "latency_p50_ms": rep["p50_ms"], "latency_mean_ms": rep["mean_ms"], "latency_p95_ms": rep["p95_ms"],
            "requests_without_cycle_metrics": sum(1 for r in ok if not r.get("metrics_ok", True)),
            "t_conv_ms_mean": (sum(t) / len(t)) if (t := [r["t_conv_ms"] for r in ok if r.get("t_conv_ms") is not None]) else None,
            "loadgen_cpu_percent_mean": sum(cpus) / len(cpus) if cpus else None, "loadgen_cpu_percent_max": cpu_max,
            "generator_possibly_bottleneck": None if cpu_max is None else cpu_max >= LOADGEN_CPU_SATURATION,
            "rnf01_p95_below_2s": (rep["p95_ms"] < RNF01_P95_MS) if base["regime"] == "contrast" and lat else None,        # solo se evalúa en el régimen de contraste (≤ 25 usuarios)
            "rnf04_met": (len(ok) / duration >= RNF04_RPS and err < RNF04_MAX_ERROR) if win else None}


def summarize_runs(runs: Sequence[Mapping]) -> dict:
    """Agrupa corridas por (sistema, usuarios) y deja las listas por corrida: la inferencia usa estos vectores (una entrada por corrida)."""
    out: dict[str, dict] = {}
    for r in runs:
        if r["status"] != "ok":
            continue
        g = out.setdefault(f"{r['system']}|u{r['users']}", {"system": r["system"], "users": r["users"], "regime": r["regime"], "latency_p95_ms": [], "throughput_rps": [], "error_rate": [], "run_ids": []})
        g["latency_p95_ms"].append(r["latency_p95_ms"])
        g["throughput_rps"].append(r["throughput_rps"])
        g["error_rate"].append(r["error_rate"])
        g["run_ids"].append(r["run_id"])
    return out
