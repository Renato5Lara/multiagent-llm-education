"""Medición HTTP OFICIAL (L_resp y throughput) desde el registro por petición del generador de carga: ventana estacionaria, sin calentamiento. Funciones PURAS sobre filas ya leídas.

Entrada (`locust_raw_log.py` escribe el CSV durante la corrida de Locust): por petición `t_end_epoch_s`, `response_ms`, `ok`, `timeout`; y por segundo `t_epoch_s`, `loadgen_cpu_percent` (proceso del generador).
La ventana estacionaria empieza `warmup_s` (≥ 10 s) después de la PRIMERA petición completada y termina en la última; es válida solo si dura ≥ `min_window_s` (60 s). Por corrida se reporta: peticiones totales / correctas /
errores / timeouts en la ventana, duración, throughput = correctas / duración, P50, media y P95 de la latencia de las correctas, y la CPU del generador. El indicador oficial de latencia es P95 POR CORRIDA;
la unidad de inferencia es la corrida (varias corridas independientes por sistema/carga), nunca la petición.

`users` > 25 marca el régimen `stress`: sus P95 no contrastan el umbral de 2 s (régimen aprobado ≤ 25 usuarios). Una corrida con la CPU del generador ≥ `LOADGEN_CPU_SATURATION` % de un núcleo queda
`generator_saturated` (alias histórico: `generator_possibly_bottleneck`) y, por la política PREREGISTRADA `GENERATOR_POLICY` (provisional técnica), `comparable = False`: la corrida se conserva y se reporta, y la carga
entera sale de la familia confirmatoria para AMBOS sistemas. Es una condición que INVALIDA la comparabilidad, no un simple aviso; no hay exclusiones manuales.
"""

from __future__ import annotations

import csv
import re
from pathlib import Path
from typing import Mapping, Sequence

from adaptation_swarm.metrics.performance import latency_report, percentile
from adaptation_swarm.oe.profile_sequence import check_logged

WARMUP_S_MIN = 10.0
WINDOW_S_MIN = 60.0
CONTRAST_MAX_USERS = 25
LOADGEN_CPU_SATURATION = 90.0
RNF01_P95_MS = 2000.0
RNF04_RPS, RNF04_MAX_ERROR = 20.0, 0.01

# B7 — POLÍTICA PREREGISTRADA del generador de carga (se fija ANTES de ver resultados; simétrica para todos los sistemas; el umbral es el ya existente en este módulo).
GENERATOR_POLICY = {
    "id": "generator-saturation-v1", "status": "PROVISIONAL_TECHNICAL",
    "metric": "loadgen_cpu_percent: CPU del proceso de Locust, 100 = un núcleo (muestras de 1 s)",
    "threshold_percent": LOADGEN_CPU_SATURATION,
    "statistic": "máximo de las muestras de CPU dentro de la ventana estacionaria",
    "saturated_means": "algún segundo de la ventana con CPU ≥ umbral: el generador pudo limitar la carga ofrecida, así que la corrida mide al generador y no al sistema",
    "on_saturation": "la corrida se CONSERVA con todos sus datos pero queda `comparable = False` (`non_comparable_reason = generator_saturated`)",
    "on_missing_cpu_samples": "no verificable ⇒ `comparable = False` (`generator_cpu_unavailable`): no se supone que el generador esté bien",
    "level_rule": "si ALGUNA corrida de ALGÚN sistema en una carga es no comparable, esa carga queda `generator_limited` y sale de la familia confirmatoria para AMBOS sistemas (simetría); se reporta, no se borra",
    "manual_exclusions": "prohibidas: ninguna corrida se excluye a mano ni después de ver resultados; solo esta regla",
    "scope": "todos los sistemas y todas las cargas por igual",
}
NON_COMPARABLE_SATURATED = "generator_saturated"
NON_COMPARABLE_NO_CPU = "generator_cpu_unavailable"


def extract_cycle_metrics(body: Mapping) -> dict:
    """Métricas de ciclo de la respuesta de AMBOS endpoints, con su forma explícita (contrato `oe/time_contract.py`):
    · propuesta (`POST /api/adaptation`): `t_conv_ms` (T_conv de AG0), `decision_ms` (tiempo operacional de decisión, copia del anterior; candidata a métrica común, validación pendiente), `k_stop` en el nivel superior;
    · convencional (`POST /api/adaptation/baseline/{system}`): `metrics.decision_ms`; `t_conv_ms` = None (no hay convergencia iterativa), sin `k_stop`.
    Una respuesta de otra forma lanza `ValueError`: nunca se asume ni se rellena."""
    pid = body.get("profile_id")
    if "t_conv_ms" in body:
        if "decision_ms" not in body:
            raise ValueError("respuesta de la propuesta sin `decision_ms` (contrato de tiempo oe2-time-contract-v1)")
        return {"shape": "swarm", "t_conv_ms": body["t_conv_ms"], "decision_ms": body["decision_ms"], "k_stop": body.get("k_stop"), "profile_id": pid}
    metrics = body.get("metrics")
    if isinstance(metrics, Mapping) and "decision_ms" in metrics:
        return {"shape": "baseline", "t_conv_ms": metrics.get("t_conv_ms"), "decision_ms": metrics["decision_ms"], "k_stop": None, "profile_id": pid}
    raise ValueError("respuesta sin métricas de tiempo reconocibles (ni t_conv_ms/decision_ms en el nivel superior ni metrics.decision_ms)")


def _opt_float(v):
    return float(v) if v not in (None, "") else None


def _opt_int(v):
    return int(v) if v not in (None, "") else None


def classify_error(exception) -> str:
    """Clase del error de una petición, por TIPO de la excepción (no por texto): `""` = sin error; `timeout` = timeout de cliente (requests.Timeout y subclases: ReadTimeout, ConnectTimeout);
    `http_<código>` = el servidor respondió con un estado ≠ 200 (Locust lo envuelve en CatchResponseError con el texto «HTTP <código>»); `incomplete_package` = respuesta 200 con paquete incompleto;
    `exception_<Tipo>` = cualquier otra excepción (conexión, etc.). Un timeout nunca se confunde con una excepción genérica."""
    if exception is None:
        return ""
    names = {c.__name__ for c in type(exception).__mro__}
    if names & {"Timeout", "ReadTimeout", "ConnectTimeout"}:
        return "timeout"
    if "CatchResponseError" in names:
        msg = str(exception)
        m = re.match(r"HTTP (\d{3})(?!\d)", msg)
        if m:
            return f"http_{m.group(1)}"
        if "incompleto" in msg:
            return "incomplete_package"
        return "response_check_failed"
    return f"exception_{type(exception).__name__}"


def read_raw(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as fh:
        return [{"t_end_epoch_s": float(r["t_end_epoch_s"]), "response_ms": float(r["response_ms"]), "ok": r["ok"] == "1", "timeout": r["timeout"] == "1",
                 "t_conv_ms": float(r["t_conv_ms"]) if r.get("t_conv_ms") else None, "metrics_ok": r.get("metrics_ok", "1") != "0", "error_kind": r.get("error_kind", ""),
                 "decision_ms": _opt_float(r.get("decision_ms")), "profile_id": r.get("profile_id") or None, "user_index": _opt_int(r.get("user_index")), "seq_pos": _opt_int(r.get("seq_pos"))}
                for r in csv.DictReader(fh)]


def read_cpu(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as fh:
        return [{"t_epoch_s": float(r["t_epoch_s"]), "loadgen_cpu_percent": float(r["loadgen_cpu_percent"])} for r in csv.DictReader(fh)]


def summarize_run(raw: Sequence[Mapping], cpu: Sequence[Mapping], *, users: int, system: str, run_id: str, warmup_s: float = WARMUP_S_MIN, min_window_s: float = WINDOW_S_MIN,
                  batch_seed: int | None = None, profile_ids: Sequence[str] | None = None, worker_index: int = 0) -> dict:
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
    saturated = None if cpu_max is None else cpu_max >= GENERATOR_POLICY["threshold_percent"]
    reason = NON_COMPARABLE_NO_CPU if saturated is None else (NON_COMPARABLE_SATURATED if saturated else None)
    dec = sorted(r["decision_ms"] for r in ok if r.get("decision_ms") is not None)
    errors_by_kind: dict[str, int] = {}
    for r in win:
        if not r["ok"]:
            k = r.get("error_kind") or ("timeout" if r["timeout"] else "unclassified")
            errors_by_kind[k] = errors_by_kind.get(k, 0) + 1
    return {**out, "status": "ok", "requests_ok": len(ok), "errors": len(win) - len(ok), "timeouts": sum(r["timeout"] for r in win), "error_rate": err,
            "error_count": len(win) - len(ok), "timeout_count": sum(r["timeout"] for r in win), "errors_by_kind": errors_by_kind,
            "errors_non_timeout": (len(win) - len(ok)) - sum(r["timeout"] for r in win),
            "throughput_rps": len(ok) / duration, "latency_p50_ms": rep["p50_ms"], "latency_mean_ms": rep["mean_ms"], "latency_p95_ms": rep["p95_ms"],
            "requests_without_cycle_metrics": sum(1 for r in ok if not r.get("metrics_ok", True)),
            "decision_ms_mean": (sum(dec) / len(dec)) if dec else None, "decision_ms_median": percentile(dec, 50) if dec else None, "decision_ms_p95": percentile(dec, 95) if dec else None,       # tiempo operacional de decisión (candidata; validación pendiente: oe/time_contract.py); NO se mezcla con t_conv_ms_mean
            "profile_sequence_check": (check_logged(raw, batch_seed, profile_ids, worker_index) if batch_seed is not None and profile_ids is not None else None),
            "t_conv_ms_mean": (sum(t) / len(t)) if (t := [r["t_conv_ms"] for r in ok if r.get("t_conv_ms") is not None]) else None,
            "loadgen_cpu_percent_mean": sum(cpus) / len(cpus) if cpus else None, "loadgen_cpu_percent_max": cpu_max,
            "generator_possibly_bottleneck": saturated, "generator_saturated": saturated, "generator_policy": GENERATOR_POLICY["id"],
            "comparable": reason is None, "non_comparable_reason": reason,                      # B7: regla preregistrada; la corrida se conserva
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
