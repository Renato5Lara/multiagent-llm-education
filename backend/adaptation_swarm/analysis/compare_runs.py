"""Compara dos corridas (p. ej. corrida-poc-1 vs corrida-poc-2) SIN modificar ninguna. Muestra qué cambió (métricas, etiquetas por
caso, 𝓕, k_stop) para atribuir diferencias a la única variable que difiere (versión de biblioteca/validaciones), no a ajustes post-hoc.

    python -m adaptation_swarm.analysis.compare_runs corrida-poc-1 corrida-poc-2 [--out-md ruta.md]"""

import argparse
import json
from pathlib import Path

from adaptation_swarm.gold.f1 import f1_report

OUT = Path(__file__).resolve().parents[2] / "experiments" / "results"


def load(label: str) -> dict:
    return json.loads((OUT / f"adaptation_swarm_{label}.json").read_text())


def compare(a_label: str, b_label: str) -> dict:
    a, b = load(a_label), load(b_label)
    ca = {c["profile_id"]: c for c in a["cases"]}
    cb = {c["profile_id"]: c for c in b["cases"]}
    common = sorted(set(ca) & set(cb))
    changed = [p for p in common if ca[p]["predicted"] != cb[p]["predicted"]]
    fixed = [p for p in changed if cb[p]["predicted"] == cb[p]["expected"] and ca[p]["predicted"] != ca[p]["expected"]]
    broken = [p for p in changed if ca[p]["predicted"] == ca[p]["expected"] and cb[p]["predicted"] != cb[p]["expected"]]
    def f1(cases): return f1_report([(c["expected"], c["predicted"]) for c in cases if c["status"] == "completed"]).f1_adapt
    return {
        "runs": [a_label, b_label],
        "config_diff": {k: [a["config"].get(k), b["config"].get(k)] for k in ("library_version", "batch_seed", "pso", "fitness_weights", "dataset")
                        if a["config"].get(k) != b["config"].get(k)},
        "f1_adapt": [f1(a["cases"]), f1(b["cases"])],
        "f1_ci95": [a["summary"]["f1"]["ci95_bootstrap"], b["summary"]["f1"]["ci95_bootstrap"]],
        "CR": [a["summary"]["convergence"]["CR"], b["summary"]["convergence"]["CR"]],
        "k_stop_mean": [a["summary"]["convergence"]["k_stop"]["mean"], b["summary"]["convergence"]["k_stop"]["mean"]],
        "k_stop_max": [a["summary"]["convergence"]["k_stop"]["max"], b["summary"]["convergence"]["k_stop"]["max"]],
        "mean_gap_to_optimum": [a["summary"]["search_quality"]["mean_gap_to_global_optimum"], b["summary"]["search_quality"]["mean_gap_to_global_optimum"]],
        "cases": len(common), "predicted_label_changed": len(changed), "changed_to_correct": len(fixed), "changed_to_incorrect": len(broken),
        "identical_g_best_S": sum(1 for p in common if ca[p]["g_best_S"] == cb[p]["g_best_S"]),
        "mean_abs_delta_F": sum(abs(ca[p]["g_best_F"] - cb[p]["g_best_F"]) for p in common) / max(len(common), 1),
    }


def to_md(c: dict) -> str:
    r = c["runs"]
    L = [f"# {r[0]} vs {r[1]}", "", "**Ninguna corrida se modificó.** Diferencias de configuración: " + json.dumps(c["config_diff"], ensure_ascii=False), "",
         "| métrica | " + r[0] + " | " + r[1] + " |", "|---|---|---|",
         f"| F1_adapt | {c['f1_adapt'][0]:.4f} | {c['f1_adapt'][1]:.4f} |",
         f"| IC95 F1 | {[round(x,3) for x in c['f1_ci95'][0]]} | {[round(x,3) for x in c['f1_ci95'][1]]} |",
         f"| CR | {c['CR'][0]:.2f} | {c['CR'][1]:.2f} |", f"| k_stop media / máx | {c['k_stop_mean'][0]:.2f} / {c['k_stop_max'][0]} | {c['k_stop_mean'][1]:.2f} / {c['k_stop_max'][1]} |",
         f"| brecha media al óptimo global | {c['mean_gap_to_optimum'][0]:.4f} | {c['mean_gap_to_optimum'][1]:.4f} |", "",
         f"Casos comparados: {c['cases']} · etiqueta predicha distinta: {c['predicted_label_changed']} (→ correcta: {c['changed_to_correct']}, → incorrecta: {c['changed_to_incorrect']}) · "
         f"mismo g_best: {c['identical_g_best_S']} · |ΔF| medio: {c['mean_abs_delta_F']:.4f}", ""]
    return "\n".join(L)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("a"); ap.add_argument("b"); ap.add_argument("--out-md")
    x = ap.parse_args()
    res = compare(x.a, x.b)
    md = to_md(res)
    if x.out_md:
        Path(x.out_md).write_text(md, encoding="utf-8")
    print(md)
