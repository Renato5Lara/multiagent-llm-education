"""Análisis OE3 (N3): ANOVA factorial completo 2×2×2×2×3 sobre la unidad de corrida (condición × lote), con la infraestructura existente (`oe/factorial.py`).
Respuestas: T_conv (ms, log), k_stop, brecha frente al óptimo (calidad de la solución) y n_messages (costo de comunicación). Uso: python analyze_oe3.py (desde backend/)."""
from __future__ import annotations

import csv
import json
from pathlib import Path

from adaptation_swarm.oe import factorial as fx

HERE = Path(__file__).parent
FACTORS = ["f_heuristic_seed", "f_replicas", "f_dispatch", "f_broadcast_gbest", "f_mechanism"]
RESPONSES = {"t_conv_ms": True, "k_stop": False, "gap_vs_optimum": False, "n_messages": False, "F": False}   # nombre → ¿escala log?

obs = [json.loads(line) for line in (HERE / "run" / "observations.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
for r in obs:                                                                                                 # los factores se comparan como texto
    for f in FACTORS:
        r[f] = str(r[f])
rows = fx.aggregate_runs(obs, list(RESPONSES))
out = {"n_obs": len(obs), "n_runs": len(rows), "factors": FACTORS, "anova": {}}
for resp, log in RESPONSES.items():
    out["anova"][resp] = fx.factorial_anova(rows, FACTORS, resp, log=log)
(HERE / "anova_oe3.json").write_text(json.dumps(out, indent=2, sort_keys=True, default=str), encoding="utf-8")

with (HERE / "runs_oe3.csv").open("w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    w.writerow(["condition", "batch", *FACTORS, "n_requests", *RESPONSES])
    for r in rows:
        w.writerow([r["condition"], r["batch"], *[r[f] for f in FACTORS], r["n_requests"], *[r[m] for m in RESPONSES]])

lines = ["# OE3 — efectos principales (ANOVA factorial por corrida; término → p; η² parcial)\n"]
for resp, res in out["anova"].items():
    if res.get("status") != "ok":
        lines.append(f"## {resp}: {res.get('status')}\n")
        continue
    lines.append(f"## {resp} (n = {res['n_runs']} corridas, {'log' if res['log_transform'] else 'escala original'}; inferencia: {res['inference']}; residuos normales: {res['diagnostics']['residuals_normal']})\n")
    lines.append("| término | p | η² parcial | significativo |\n|---|---|---|---|")
    for t, v in sorted(res["terms"].items(), key=lambda kv: kv[1].get("p_permutation", kv[1]["p_value"])):
        if ":" in t and not v["significant"]:
            continue
        lines.append(f"| {t} | {v.get('p_permutation', v['p_value']):.3g} | {v['partial_eta_sq']:.3f} | {'sí' if v['significant'] else 'no'} |")
    lines.append("")
    for f in FACTORS:
        mm = res["marginal_means"][f]
        lines.append(f"- {f}: " + ", ".join(f"{lv} = {d.get('geometric_mean', d['mean']):.4g}" for lv, d in mm.items()))
    lines.append("")
(HERE / "anova_oe3.md").write_text("\n".join(lines), encoding="utf-8")
print("\n".join(lines))
