"""Exportación de datos para la fase estadística: nunca solo promedios. Funciones PURAS sobre las observaciones crudas del ejecutor.

    raw_observations.csv     una fila por petición (ancho): condición, factores, unidad (perfil), réplica, lote, semilla, marca de tiempo, estado y todas las métricas
    statistical_input.csv    formato LARGO, una fila por (observación, métrica) + una por (lote, throughput_rps): lo que se carga directamente en la prueba de normalidad y de hipótesis
Cada fila lleva `run_label`, `experiment` y `unit_id` (perfil, o `batch:<n>` para el throughput), de modo que la unidad estadística es explícita.
"""

from __future__ import annotations

import csv
import io
from typing import Mapping, Sequence

METRICS = ("t_conv_ms", "latency_ms", "total_ms", "k_stop", "n_messages", "F", "gap_vs_optimum", "comm_overhead_ms", "n_evaluations")
FACTOR_PREFIX = "f_"
RAW_FIELDS = ("run_label", "experiment", "condition", "profile_id", "archetype", "difficulty", "replicate", "batch", "exec_index", "seed", "t_start_utc", "status", "stop_reason", "package_valid", "w_valid",
              "iterations_logged", "inflight_overlap", "error_code", *METRICS, "predicted", "S", "F_opt")
LONG_FIELDS = ("run_label", "experiment", "condition", "unit_type", "unit_id", "replicate", "batch", "exec_index", "seed", "t_start_utc", "status", "metric", "value")


def _factor_cols(obs: Sequence[Mapping]) -> list[str]:
    return sorted({k for r in obs for k in r if k.startswith(FACTOR_PREFIX)})


def _csv(fields: Sequence[str], rows: Sequence[Mapping]) -> str:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=list(fields), extrasaction="ignore", lineterminator="\n")
    w.writeheader()
    for r in rows:
        w.writerow({k: ("" if r.get(k) is None else r[k]) for k in fields})
    return buf.getvalue()


def raw_observations_csv(run_label: str, experiment: str, obs: Sequence[Mapping]) -> str:
    fcols = _factor_cols(obs)
    rows = [{**r, "run_label": run_label, "experiment": experiment, "S": "" if r.get("S") is None else "-".join(map(str, r["S"]))} for r in obs]
    return _csv([*RAW_FIELDS, *fcols], rows)


def statistical_input_rows(run_label: str, experiment: str, obs: Sequence[Mapping], bat: Sequence[Mapping]) -> list[dict]:
    out = []
    for r in obs:
        for m in METRICS:
            if r.get(m) is not None:
                out.append({"run_label": run_label, "experiment": experiment, "condition": r["condition"], "unit_type": "profile", "unit_id": r["profile_id"], "replicate": r["replicate"],
                            "batch": r["batch"], "exec_index": r.get("exec_index"), "seed": r.get("seed"), "t_start_utc": r.get("t_start_utc"), "status": r["status"], "metric": m, "value": r[m]})
    for b in bat:
        if b.get("throughput_rps") is not None:
            out.append({"run_label": run_label, "experiment": experiment, "condition": b["condition"], "unit_type": "batch", "unit_id": f"batch:{b['batch']}", "replicate": None,
                        "batch": b["batch"], "exec_index": b.get("exec_index"), "seed": None, "t_start_utc": b.get("t_start_utc"), "status": "completed", "metric": "throughput_rps", "value": b["throughput_rps"]})
    return out


def statistical_input_csv(run_label: str, experiment: str, obs: Sequence[Mapping], bat: Sequence[Mapping]) -> str:
    return _csv(LONG_FIELDS, statistical_input_rows(run_label, experiment, obs, bat))
