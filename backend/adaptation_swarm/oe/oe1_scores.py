"""Indicadores OE1 operacionalizados (decisión técnica interna, ver `campaign_spec.py`; `definitions.py` sigue marcándolos PENDING hasta que exista aprobación). Funciones PURAS sobre la tabla de `oe1.requirement_table`.

compliance_score_oe1: SOLO los RF/RNF existentes (`oe1.REQUIREMENTS`; no se agrega ninguno). Por requisito: MET = 1 · NOT_MET = 0 · NOT_MEASURED = excluido del denominador y reportado aparte. El estado parcial (0.5) NO existe
porque ningún criterio de aceptación existente lo define. Score por dimensión = media de sus requisitos evaluados; global = media de las dimensiones con al menos un requisito evaluado. No hay clasificación de criticidad
⇒ no hay análisis de sensibilidad de pesos ni «críticos fallidos» (se declara). Anti-circularidad: `exclude_ids` (p. ej. RNF03 = F1) deja fuera del puntaje el requisito que se correlacionará con F1.

reliability_oe1: proporción de peticiones con salida válida (esquema/paquete válido, sin error, sin timeout) con IC de Wilson. NO es CR (tasa de convergencia), NO es MTBF; la reproducibilidad determinista (REL-D) es evidencia aparte.
"""

from __future__ import annotations

import math
from typing import Mapping, Sequence

from scipy import stats

from adaptation_swarm.oe.oe1 import DIMENSIONS, MET, NOT_MET, NOT_MEASURED


def wilson_interval(successes: int, n: int, confidence: float = 0.95) -> tuple[float, float]:
    if n <= 0 or not 0 <= successes <= n:
        raise ValueError("n > 0 y 0 ≤ éxitos ≤ n")
    z = float(stats.norm.ppf(1 - (1 - confidence) / 2))
    p = successes / n
    den = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return max(0.0, centre - half), min(1.0, centre + half)


def reliability_oe1(obs: Sequence[Mapping]) -> dict:
    """Válida = status completed ∧ package_valid ∧ sin error ni timeout. `package_valid` ausente cuenta como NO válida (no se asume)."""
    def valid(r: Mapping) -> bool:
        return r.get("status") == "completed" and r.get("package_valid") is True and not r.get("error") and not r.get("error_code") and not r.get("timeout")
    n = len(obs)
    if n == 0:
        return {"status": "no_requests", "n": 0}
    k = sum(valid(r) for r in obs)
    lo, hi = wilson_interval(k, n)
    return {"status": "ok", "definition": "peticiones con salida válida / peticiones", "valid": k, "n": n, "proportion": k / n, "wilson_ci95": [lo, hi]}


def compliance_score_oe1(table: Sequence[Mapping], *, exclude_ids: Sequence[str] = ()) -> dict:
    rows = [r for r in table if r["id"] not in set(exclude_ids)]
    value = {MET: 1.0, NOT_MET: 0.0}
    per_dim: dict[str, dict] = {}
    for d in DIMENSIONS:
        ev = [r for r in rows if r["dimension"] == d and r["status"] in value]
        per_dim[d] = {"score": (sum(value[r["status"]] for r in ev) / len(ev)) if ev else None, "evaluated": [r["id"] for r in ev],
                      "not_evaluated": [r["id"] for r in rows if r["dimension"] == d and r["status"] == NOT_MEASURED]}
    scores = [v["score"] for v in per_dim.values() if v["score"] is not None]
    return {"global": sum(scores) / len(scores) if scores else None, "dimensions": per_dim, "failed": [r["id"] for r in rows if r["status"] == NOT_MET],
            "critical_failed": None, "critical_note": "no existe clasificación de criticidad: sin «críticos fallidos» ni sensibilidad de pesos",
            "not_evaluated": [r["id"] for r in rows if r["status"] == NOT_MEASURED], "partial_credit": "no definido por ningún criterio de aceptación existente",
            "excluded_for_circularity": sorted(set(exclude_ids)), "dimensions_without_evidence": [d for d, v in per_dim.items() if v["score"] is None]}


def oe1_per_run(obs: Sequence[Mapping], bat: Sequence[Mapping]) -> list[dict]:
    """`reliability_oe1` y `compliance_score_oe1` por CORRIDA (condición, lote) de la propuesta; RNF03 (F1) se excluye del puntaje (anti-circularidad). Los requisitos que dependen de sondas o paneles quedan
    NOT_MEASURED (no evaluados), no se rellenan."""
    from adaptation_swarm.oe.oe1 import requirement_table
    runs: dict[tuple, list[Mapping]] = {}
    for r in obs:
        if r.get("f_system", "swarm") == "swarm":
            runs.setdefault((r["condition"], r["batch"]), []).append(r)
    out = []
    for (cond, batch), rows in sorted(runs.items(), key=lambda kv: (str(kv[0][0]), kv[0][1])):
        table = requirement_table(rows, [b for b in bat if b["condition"] == cond and b["batch"] == batch])
        out.append({"condition": cond, "batch": batch, "reliability_oe1": reliability_oe1(rows), "compliance_score_oe1": compliance_score_oe1(table, exclude_ids=("RNF03",))})
    return out
