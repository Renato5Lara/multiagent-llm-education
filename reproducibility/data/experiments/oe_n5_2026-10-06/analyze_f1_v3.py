"""Resumen de la precisión (F1_adapt v3, PROVISIONAL) por arquetipo, dificultad y modalidad a partir de f1_v3_provisional_evaluation.json (sin recalcular la métrica)."""
import json
import statistics as st
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).parent
e = json.loads((HERE / "f1_v3_provisional_evaluation.json").read_text(encoding="utf-8"))
pm = list(e["profile_means"].values())
by_arch, by_diff = defaultdict(list), defaultdict(list)
for c in e["cases"]:
    by_arch[c["archetype"]].append(c["f1"])
    by_diff[c["difficulty"]].append(c["f1"])
summary = {
    "definition": {"f1": "v3 (4×4 con audio, agregación samples)", "rule_version": e["rule_version"], "status": e["status"], "metric_version": e["metric_version"], "k": e["k"], "n_profiles": e["n_profiles"], "n_cases": e["n_cases_total"]},
    "f1_adapt_by_replica": e["f1_adapt_by_replica"], "replicas_ci95": e["descriptive"]["ci95_replicas"],
    "profile_means": {"n": len(pm), "mean": st.mean(pm), "median": st.median(pm), "sd": st.stdev(pm), "min": min(pm), "max": max(pm)},
    "by_archetype": {a: {"n_cases": len(v), "mean_f1": st.mean(v)} for a, v in sorted(by_arch.items())},
    "by_difficulty": {a: {"n_cases": len(v), "mean_f1": st.mean(v)} for a, v in sorted(by_diff.items())},
    "by_modality_ovr": {m: {k: d[k] for k in ("precision", "recall", "f1", "tp", "fp", "fn", "tn")} for m, d in e["ovr_2x2_pooled"]["by_modality"].items()},
}
(HERE / "f1_v3_summary.json").write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
print(json.dumps({k: summary[k] for k in ("profile_means", "by_archetype", "by_difficulty")}, indent=1))
print({m: (round(d["precision"], 3), round(d["recall"], 3), round(d["f1"], 3)) for m, d in summary["by_modality_ovr"].items()})
