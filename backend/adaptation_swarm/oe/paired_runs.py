"""Contraste PAREADO por (run_index, carga) entre la propuesta y `decision_table` (alternativa B de D.5/F). CAPACIDAD TÉCNICA SEPARADA: no sustituye al análisis A ni está conectada al resultado confirmatorio.

ESTADO: IMPLEMENTED_TECHNICALLY_NOT_METHODOLOGICALLY_APPROVED.
    · A (corridas independientes, `oe2_confirmatory.runs_comparison`) sigue siendo la ÚNICA ruta confirmatoria implementada; este módulo no la llama, no la modifica y `oe2_confirmatory`/`http_campaign` no lo importan.
    · B NO está seleccionada como análisis primario ni aprobada por el asesor. La elección A/B (`campaign_spec.oe2.methodological_decisions.http_pairing`) sigue PENDING y el guard `PEND` sigue bloqueando la campaña oficial.
    · NO se decide el estimando (escala original o log) ni la prueba (t pareada o Wilcoxon): quien llama debe PEDIRLOS de forma explícita; no hay valor por defecto ni selección automática por normalidad.
    · NO se fija `m` de Holm ni se conecta la salida a la familia: `hypotheses_for_holm` solo da el formato compatible con `oe2_confirmatory.holm_family`.
    · Errores y timeouts: se REGISTRAN por par; no hay regla de invalidez y no se inventa (decisión pendiente). Tampoco se resuelve cold/warm: los metadatos del servidor viajan con cada par.

Pares: para cada `(run_index, users)` una corrida de la propuesta y una de `decision_table`, ambas con persistencia común OFF y rol de contraste. NUNCA se empareja: otros sistemas, cargas distintas, la propuesta con persistencia ON,
ni corridas no comparables. Un miembro ausente deja el par INCOMPLETO (no se imputa); lo que no se puede emparejar se registra con su motivo, nada se descarta en silencio.
Regla de generador (misma que A): si alguna corrida de alguno de los dos sistemas en una carga de contraste no es comparable, ESA carga queda `generator_limited` para ambos sistemas y todos sus pares quedan excluidos (registrados).
Régimen: solo cargas ≤ 25 usuarios (contraste); las de estrés se registran y quedan fuera.
"""

from __future__ import annotations

import math
from typing import Mapping, Sequence

import numpy as np
from scipy import stats

from adaptation_swarm.analysis import comparison as cmp
from adaptation_swarm.oe import campaign_spec, http_window

STATUS = "IMPLEMENTED_TECHNICALLY_NOT_METHODOLOGICALLY_APPROVED"
PROPOSAL = campaign_spec.SPEC["oe2"]["proposal_system"]
BASELINE = campaign_spec.SPEC["oe2"]["conventional_system"]
METRICS = {"L_resp_P95_http": "latency_p95_ms", "throughput_http": "throughput_rps"}          # mismos nombres de hipótesis que la familia actual (A)
SCALES = ("raw", "log")
TESTS = ("paired_t", "wilcoxon")
ROW_REQUIRED = ("system", "users", "run_index", "persist_policy", "comparison_role")
PAIR_REQUIRED = ("batch_id", "seed")
CARRIED = ("server_instance", "server_restarted_before_run", "server_runs_served_before", "execution_index")               # cold/warm: se conservan, no se interpretan
PENDING = {"estimand": "PENDING (raw o log: lo pide quien llama)", "test": "PENDING (paired_t o wilcoxon: lo pide quien llama)", "primary_analysis": "NO: la ruta confirmatoria vigente es A",
           "holm": "NO conectado (m no fijado; ver oe2_confirmatory.holm_family)", "errors_timeouts_validity_rule": "PENDING: no existe regla; solo se registran", "advisor_approval": "NO"}


def _missing(r: Mapping, fields: Sequence[str]) -> list[str]:
    return [f for f in fields if r.get(f) is None]


def build_pairs(records: Sequence[Mapping]) -> dict:
    """Forma los pares y los clasifica. No calcula ningún estadístico. Devuelve `pairs` (todos, con estado y motivos) y los conteos que permiten ver qué entra y qué queda fuera y por qué."""
    ignored: list[dict] = []                                                                         # filas que ni siquiera son candidatas a par (con su motivo)
    eligible: list[Mapping] = []
    for r in records:
        rid = r.get("run_id")
        if r.get("system") not in (PROPOSAL, BASELINE):
            ignored.append({"run_id": rid, "reason": "other_system"})
            continue
        miss = _missing(r, ROW_REQUIRED)
        if miss:
            ignored.append({"run_id": rid, "reason": "missing_fields", "fields": miss})                # fail-closed: sin condición, rol o clave no se empareja
            continue
        if r["persist_policy"] != campaign_spec.COMPARISON_PERSISTENCE or r["comparison_role"] not in campaign_spec.CONTRAST_ROLES:
            ignored.append({"run_id": rid, "reason": "proposal_persistence_on" if (r["system"] == PROPOSAL and r["persist_policy"] == campaign_spec.PROPOSAL_COST_PERSISTENCE) else "not_contrast_condition"})
            continue
        eligible.append(r)

    groups: dict[tuple, dict[str, list[Mapping]]] = {}
    for r in eligible:
        groups.setdefault((r["run_index"], r["users"]), {PROPOSAL: [], BASELINE: []})[r["system"]].append(r)

    limited_levels = sorted({r["users"] for r in eligible if r.get("status") == "ok" and r.get("comparable") is not True and r["users"] <= http_window.CONTRAST_MAX_USERS})   # misma regla que A
    pairs = []
    for (run_index, users), g in sorted(groups.items(), key=lambda kv: (kv[0][1], kv[0][0])):
        sw, bl = g[PROPOSAL], g[BASELINE]
        reasons: list[str] = []
        if len(sw) > 1 or len(bl) > 1:
            reasons.append("duplicate_run")                                                           # no se elige entre duplicados
        if not sw:
            reasons.append("missing_proposal")
        if not bl:
            reasons.append("missing_baseline")
        s, b = (sw[0] if sw else None), (bl[0] if bl else None)
        if "duplicate_run" not in reasons and s is not None and b is not None:
            for r in (s, b):
                if r.get("status") != "ok":
                    reasons.append(f"run_status_not_ok:{r['system']}:{r.get('status')}")
                elif r.get("comparable") is not True:
                    reasons.append(f"not_comparable:{r['system']}:{r.get('non_comparable_reason') or 'comparable_not_declared'}")
            if users in limited_levels:
                reasons.append("generator_limited_level")
            for f in PAIR_REQUIRED:
                if _missing(s, [f]) or _missing(b, [f]):
                    reasons.append(f"{f}_missing")
                elif s[f] != b[f]:
                    reasons.append(f"{f}_mismatch")
            hs, hb = s.get("profile_sequence_sha256"), b.get("profile_sequence_sha256")
            if hs is not None and hb is not None and hs != hb:
                reasons.append("sequence_hash_mismatch")
        if users > http_window.CONTRAST_MAX_USERS:
            reasons.append("stress_regime_outside_contrast")
        only_missing = reasons and all(x in ("missing_proposal", "missing_baseline") for x in reasons)
        pair = {"run_index": run_index, "users": users, "status": "complete" if not reasons else ("incomplete" if only_missing else "excluded"), "reasons": reasons,
                "run_ids": {PROPOSAL: [r.get("run_id") for r in sw], BASELINE: [r.get("run_id") for r in bl]}}
        if s is not None and b is not None and "duplicate_run" not in reasons:
            hs, hb = s.get("profile_sequence_sha256"), b.get("profile_sequence_sha256")
            pair.update(batch_id=s.get("batch_id"), seed=s.get("seed"), same_seed=s.get("seed") is not None and s.get("seed") == b.get("seed"),
                        sequence_hash_checked=hs is not None and hb is not None, same_sequence_hash=(hs == hb) if hs is not None and hb is not None else None,
                        values={PROPOSAL: {m: s.get(f) for m, f in METRICS.items()}, BASELINE: {m: b.get(f) for m, f in METRICS.items()}},
                        has_errors_or_timeouts={PROPOSAL: bool((s.get("errors") or 0) or (s.get("timeouts") or 0)), BASELINE: bool((b.get("errors") or 0) or (b.get("timeouts") or 0))},
                        carried={PROPOSAL: {k: s.get(k) for k in CARRIED}, BASELINE: {k: b.get(k) for k in CARRIED}})
        pairs.append(pair)

    def count(pred) -> int:
        return sum(1 for p in pairs if pred(p))
    by_load: dict[int, dict] = {}
    for p in pairs:
        d = by_load.setdefault(p["users"], {"complete": 0, "incomplete": 0, "excluded": 0})
        d[p["status"]] += 1
    reason_counts: dict[str, int] = {}
    for p in pairs:
        for r in p["reasons"]:
            reason_counts[r.split(":")[0]] = reason_counts.get(r.split(":")[0], 0) + 1
    return {"status": STATUS, "n_rows_in": len(records), "rows_ignored": ignored, "n_rows_ignored": len(ignored), "n_pairs_total": len(pairs), "n_complete": count(lambda p: p["status"] == "complete"),
            "n_incomplete": count(lambda p: p["status"] == "incomplete"), "n_excluded": count(lambda p: p["status"] == "excluded"), "reason_counts": dict(sorted(reason_counts.items())), "by_load": {str(u): v for u, v in sorted(by_load.items())},
            "loads_with_complete_pairs": sorted(u for u, v in by_load.items() if v["complete"]), "loads_without_complete_pairs": sorted(u for u, v in by_load.items() if not v["complete"]),
            "generator_limited_loads": limited_levels, "n_same_seed": count(lambda p: p.get("same_seed") is True), "n_same_sequence_hash": count(lambda p: p.get("same_sequence_hash") is True),
            "n_sequence_hash_not_checked": count(lambda p: p.get("sequence_hash_checked") is False), "n_pairs_with_errors_or_timeouts": count(lambda p: any((p.get("has_errors_or_timeouts") or {}).values())),
            "error_timeout_rule": PENDING["errors_timeouts_validity_rule"], "pairs": pairs, "pending": PENDING}


def _differences(pairs: Sequence[Mapping], metric: str, scale: str) -> tuple[np.ndarray, np.ndarray, np.ndarray, str | None]:
    sw = np.array([p["values"][PROPOSAL][metric] for p in pairs], dtype=float)
    bl = np.array([p["values"][BASELINE][metric] for p in pairs], dtype=float)
    if not (np.all(np.isfinite(sw)) and np.all(np.isfinite(bl))):
        return sw, bl, sw, "not_testable_missing_or_non_finite_values"
    if scale == "log":
        if np.any(sw <= 0) or np.any(bl <= 0):
            return sw, bl, sw, "not_testable_non_positive_values"
        return sw, bl, np.log(sw) - np.log(bl), None
    return sw, bl, sw - bl, None


def _test_one(pairs: Sequence[Mapping], metric: str, scale: str, test: str) -> dict:
    base = {"n_pairs": len(pairs), "metric": metric, "scale": scale, "test": test, "delta": "swarm - decision_table",
            "estimand": "mean of d_i = swarm_i − decision_table_i" if scale == "raw" else "mean of log(swarm_i) − log(decision_table_i) (geometric ratio = exp(mean))"}
    if len(pairs) < 3:
        return {**base, "status": "not_testable_fewer_than_3_pairs", "p_value": None}
    sw, bl, d, err = _differences(pairs, metric, scale)
    if err:
        return {**base, "status": err, "p_value": None}
    base.update(mean_diff=float(d.mean()), median_diff=float(np.median(d)))
    if scale == "log":
        base["geometric_ratio"] = math.exp(float(d.mean()))
    if float(d.max()) == float(d.min()):
        return {**base, "status": "undefined_constant_differences", "p_value": None}
    base["diff_ci95_bootstrap"] = list(cmp._bootstrap_mean_ci(d))                                      # mismo bootstrap (semilla fija) que el resto del análisis
    if len(d) >= 3:
        base["shapiro_p_diagnostic"], base["normality_used_for_selection"] = float(stats.shapiro(d).pvalue), False             # solo informativo: NO selecciona la prueba
    try:
        res = stats.ttest_1samp(d, 0.0) if test == "paired_t" else stats.wilcoxon(d)                  # t pareada = t de una muestra sobre las diferencias (idéntica a `ttest_rel`)
    except ValueError as exc:
        return {**base, "status": f"test_error:{exc}", "p_value": None}
    return {**base, "status": "ok", "statistic": float(res.statistic), "p_value": float(res.pvalue)}


def paired_run_comparison(records: Sequence[Mapping], metric: str, *, scale: str, test: str) -> dict:
    """Contraste pareado de UNA métrica (`L_resp_P95_http` o `throughput_http`) por carga. `scale` (raw | log) y `test` (paired_t | wilcoxon) son OBLIGATORIOS y explícitos: no hay selección automática ni valor por defecto.
    Solo entran los pares COMPLETOS. Devuelve el resultado por carga y el informe de emparejamiento."""
    if metric not in METRICS:
        raise ValueError(f"métrica desconocida: {metric!r}; válidas: {sorted(METRICS)}")
    if scale not in SCALES:
        raise ValueError(f"scale debe pedirse de forma explícita: {SCALES}")
    if test not in TESTS:
        raise ValueError(f"test debe pedirse de forma explícita: {TESTS}")
    rep = build_pairs(records)
    by_load: dict[int, list[dict]] = {}
    for p in rep["pairs"]:
        if p["status"] == "complete":
            by_load.setdefault(p["users"], []).append(p)
    return {"status": STATUS, "confirmatory": False, "selected_as_primary": False, "approved_by_advisor": False, "metric": metric, "field": METRICS[metric], "scale": scale, "test": test, "alpha_not_applied": True,
            "loads": {str(u): _test_one(ps, metric, scale, test) for u, ps in sorted(by_load.items())}, "pairing": {k: v for k, v in rep.items() if k != "pairs"}, "pending": PENDING}


def paired_contrast(records: Sequence[Mapping], *, scale: str, test: str) -> dict:
    """Las dos métricas con la MISMA escala y prueba (el par de corridas es el mismo objeto para ambas; no se parea una sin la otra)."""
    return {m: paired_run_comparison(records, m, scale=scale, test=test) for m in METRICS}


def hypotheses_for_holm(contrast: Mapping[str, Mapping]) -> dict:
    """Formato `{hipótesis: resultado con p_value}` compatible con `oe2_confirmatory.holm_family` (mismos nombres `L_resp_P95_http@u<carga>` / `throughput_http@u<carga>`). NO la conecta ni fija `m`."""
    return {f"{m}@u{u}": res for m, comp in contrast.items() for u, res in comp["loads"].items()}
