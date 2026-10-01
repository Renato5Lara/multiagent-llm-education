"""Fase estadística sobre `statistical_input.csv` (SOLO ese archivo + `environment.json`/`manifest.json` de la corrida): demuestra que los datos crudos bastan para normalidad y contraste sin volver a
ejecutar nada. Escribe `statistical_analysis.json` en un directorio NUEVO (la corrida original no se modifica).

El plan es el DISEÑO real de cada experimento (no una prueba fija) y NO formula hipótesis académicas: cada registro lleva solo la forma estadística (H0/H1 técnicas) y `academic_label = null`. Todo resultado hereda
la etiqueta de validez de la corrida (`EXPLORATORY` mientras el entorno sea PILOT o haya definiciones PENDING): este módulo NO convierte una corrida exploratoria en oficial.

    python -m adaptation_swarm.oe.stats_cli --run DIR --out-dir NUEVO [--alpha 0.05]
Plan por experimento:
    oe2  por nivel de carga y por indicador (t_conv_ms, latency_ms): propuesta vs cada convencional, PAREADO por perfil (media por perfil) + normalidad de las diferencias;
         throughput_rps: grupos independientes (unidad = lote)
    oe3  efectos principales por factor sobre t_conv_ms y k_stop (diseño factorial completo) o, con el diseño OFAT, cada condición vs la referencia (pareado, Holm)
    oe4  throughput entre niveles de carga (k independientes: Kruskal-Wallis + Holm) y efecto de N sobre t_conv_ms a carga 1 (k pareados)
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path

from adaptation_swarm.analysis import assumptions, comparison as cmp, hypothesis as hyp
from adaptation_swarm.oe.conditions import OE3_FACTORS


def load_long(path: Path) -> list[dict]:
    rows = []
    for r in csv.DictReader(path.open(encoding="utf-8")):
        r["value"] = float(r["value"])
        rows.append(r)
    return rows


def _unit_means(rows: list[dict], condition: str, metric: str) -> dict[str, float]:
    """Unidad = perfil: promedio de todas las observaciones (réplicas y lotes) de cada perfil, solo peticiones correctas."""
    return cmp.profile_means([(r["unit_id"], r["value"]) for r in rows if r["condition"] == condition and r["metric"] == metric and r["unit_type"] == "profile" and r["status"] == "completed"])


def _batches(rows: list[dict], condition: str) -> list[float]:
    return [r["value"] for r in rows if r["condition"] == condition and r["metric"] == "throughput_rps"]


def _meta(rows: list[dict]) -> dict[str, dict]:
    """condición → factores. Se reconstruyen del nombre normalizado de la condición (`swarm|batch|bc1|h1|pso|r1|N20|c1` o `rules|c10`)."""
    out = {}
    for c in sorted({r["condition"] for r in rows}):
        p = c.split("|")
        if p[0] != "swarm":
            out[c] = {"system": p[0], "concurrency": int(p[1][1:])}
        else:
            out[c] = {"system": "swarm", "dispatch": p[1], "broadcast_gbest": p[2] == "bc1", "heuristic_seed": p[3] == "h1", "mechanism": p[4], "replicas": int(p[5][1:]),
                      "n_particles": int(p[6][1:]), "concurrency": int(p[7][1:])}
    return out


def plan_oe2(rows, meta, alpha) -> dict:
    out, levels = {}, sorted({m["concurrency"] for m in meta.values()})
    for lv in levels:
        sw = next((c for c, m in meta.items() if m["system"] == "swarm" and m["concurrency"] == lv), None)
        for c, m in meta.items():
            if m["system"] == "swarm" or m["concurrency"] != lv or sw is None:
                continue
            key = f"c{lv}|swarm_vs_{m['system']}"
            out[key] = {}
            for metric in ("t_conv_ms", "latency_ms"):
                a, b = _unit_means(rows, sw, metric), _unit_means(rows, c, metric)
                common = sorted(set(a) & set(b))
                out[key][metric] = hyp.paired({k: a[k] for k in common}, {k: b[k] for k in common}, unit="profile_mean_over_replicates_and_batches", alpha=alpha) if len(common) >= 3 else {"status": "not_testable"}
            out[key]["throughput_rps"] = hyp.independent(_batches(rows, sw), _batches(rows, c), unit="batch", alpha=alpha)
    return out


def plan_oe3(rows, meta, alpha) -> dict:
    swarm = [c for c, m in meta.items() if m["system"] == "swarm"]
    if len(swarm) == 48:
        out = {}
        for metric in ("t_conv_ms", "k_stop"):
            recs = [{**{f: meta[c][f] for f in OE3_FACTORS}, "profile_id": u, metric: v} for c in swarm for u, v in _unit_means(rows, c, metric).items()]
            out[metric] = hyp.factorial(recs, OE3_FACTORS, metric, unit="profile_mean_over_replicates", alpha=alpha)
        return out
    ref = next((c for c in swarm if (meta[c]["dispatch"], meta[c]["broadcast_gbest"], meta[c]["heuristic_seed"], meta[c]["mechanism"], meta[c]["replicas"]) == ("batch", True, True, "pso", 1)), None)
    if ref is None:
        return {"status": "no_reference_condition"}
    out = {}
    for metric in ("t_conv_ms", "k_stop"):
        res = {c: hyp.paired(_unit_means(rows, c, metric), _unit_means(rows, ref, metric), unit="profile_mean_over_replicates", alpha=alpha) for c in swarm if c != ref}
        adj = cmp.holm({c: r["p_value"] for c, r in res.items() if r["p_value"] is not None})
        for c, r in res.items():
            r["p_holm"] = adj.get(c)
        out[metric] = {"reference": ref, "comparisons": res}
    return out


def plan_oe4(rows, meta, alpha) -> dict:
    out, by_n = {}, defaultdict(dict)
    for c, m in meta.items():
        by_n[m["n_particles"]][m["concurrency"]] = c
    for n, lv in sorted(by_n.items()):
        out[f"throughput_across_load|N{n}"] = hyp.k_independent({f"c{k}": _batches(rows, c) for k, c in sorted(lv.items())}, unit="batch", alpha=alpha)
    c1 = {n: lv[1] for n, lv in by_n.items() if 1 in lv}
    if len(c1) >= 2:
        out["particles_effect_t_conv_at_c1"] = hyp.k_paired({f"N{n}": _unit_means(rows, c, "t_conv_ms") for n, c in sorted(c1.items())}, unit="profile_mean_over_replicates_and_batches", alpha=alpha)
    return out


def analyze_run(run_dir: Path, alpha: float = 0.05) -> dict:
    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    rows, exp = load_long(run_dir / "statistical_input.csv"), manifest["experiment"]
    meta = _meta(rows)
    plan = {"oe2": plan_oe2, "oe3": plan_oe3, "oe4": plan_oe4}[exp](rows, meta, alpha)
    norm = {c: {m: assumptions.normality(list(_unit_means(rows, c, m).values()), unit="profile_mean_over_replicates_and_batches", alpha=alpha)
                for m in ("t_conv_ms", "latency_ms") if _unit_means(rows, c, m)} for c in sorted(meta)}
    return {"schema": "oe-statistical-analysis-v1", "experiment": exp, "source_run": str(run_dir), "source_checksums": manifest["files"].get("statistical_input.csv"),
            "validity_inherited": manifest["validity"], "environment_class": manifest["environment_class"], "official_execution": manifest["official_execution"],
            "label": "EXPLORATORY — NO es resultado oficial de tesis" if manifest["validity"] != "OFFICIAL_CANDIDATE" else "OFFICIAL_CANDIDATE (pendiente de decisión metodológica)",
            "alpha": alpha, "n_rows": len(rows), "normality_by_condition": norm, "contrasts": plan}


def main(argv: list[str] | None = None) -> None:
    from adaptation_swarm.tools import isolated_env as iso
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--run", type=Path, required=True)
    ap.add_argument("--out-dir")
    ap.add_argument("--alpha", type=float, default=0.05)
    a = ap.parse_args(argv)
    out_dir = iso.require_out_dir(a.out_dir)
    iso.check_new_output_targets([out_dir])
    res = analyze_run(a.run, a.alpha)
    out_dir.mkdir(parents=True, exist_ok=False)
    with (out_dir / "statistical_analysis.json").open("x", encoding="utf-8") as fh:
        fh.write(json.dumps(res, indent=2, sort_keys=True, default=str))
    print(res["label"], "->", out_dir / "statistical_analysis.json")


if __name__ == "__main__":
    main()
