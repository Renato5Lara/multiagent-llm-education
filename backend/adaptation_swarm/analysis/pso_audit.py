"""Diagnóstico del comportamiento del PSO de una corrida YA ejecutada (solo lectura, desde swarm_iterations): qué hace el
enjambre y por qué para en k≈1–2. No modifica nada. Para corridas nuevas la misma información se registra en vivo
(`swarm_iterations.diagnostics`).

REQUIERE PostgreSQL: lee `swarm_cycles` y `swarm_iterations` de la corrida (transacción `READ ONLY`; no escribe en la base).
Solo opera sobre la base AISLADA de pruebas (tests/adaptation_swarm/integration_env/), con `DATABASE_URL` EXPLÍCITA en el entorno (no se lee backend/.env); rechaza desarrollo y producción.
No usa Redis, OpenAI, la biblioteca ni subprocesos. Escribe únicamente en `--out-dir` (obligatorio; nunca `experiments/results/`, resultados congelados) y sin sobrescribir.

Uso (desde backend/):
    export DATABASE_URL=postgresql+psycopg://swarm_test:…@127.0.0.1:55432/swarm_test
    python -m adaptation_swarm.analysis.pso_audit --run-label corrida-poc-1 --out-dir /ruta/nueva [--out-md /ruta/nueva/pso.md]
"""

from __future__ import annotations

import argparse
import json
import statistics
from collections import Counter
from pathlib import Path

import numpy as np
from sqlalchemy import select, text

from adaptation_swarm.metrics.pso_diagnostics import swarm_diagnostics
from adaptation_swarm.tools import isolated_env as iso


def audit(run_label: str) -> dict:
    from app.db.session import SessionLocal            # importar aquí: la app fija el destino al importarse y antes se verifica el destino aislado
    from app.models.swarm_adaptation import SwarmCycle, SwarmIteration

    per_cycle, per_iter = [], {}
    with SessionLocal() as s:
        s.execute(text("SET TRANSACTION READ ONLY"))    # primera sentencia: la base rechaza cualquier escritura
        cycles = list(s.scalars(select(SwarmCycle).where(SwarmCycle.run_label == run_label, SwarmCycle.status == "completed")))
        for c in cycles:
            its = list(s.scalars(select(SwarmIteration).where(SwarmIteration.cycle_id == c.id).order_by(SwarmIteration.k)))
            prev_pbest = None
            first_change, pb_updates, gb_updates, dups = None, [], [], []
            for it in its:
                P = it.particles
                x = np.array([p["x"] for p in P]); S = np.array([p["S"] for p in P]); F = np.array([p["F"] for p in P])
                d = swarm_diagnostics(x, S, F)
                pb = np.array([p["pbest_F"] for p in P])
                pb_updates.append(int(len(P)) if prev_pbest is None else int((pb > prev_pbest + 1e-15).sum()))
                prev_pbest = pb
                gb_updates.append(it.k == 0 or (it.delta_F is not None and it.delta_F > 1e-15))
                if it.k >= 1 and it.delta_F is not None and it.delta_F > 1e-15 and first_change is None:
                    first_change = it.k
                dups.append(d["duplicate_particles_pct"])
                per_iter.setdefault(it.k, []).append(d)
            per_cycle.append({"k_stop": c.k_stop, "first_gbest_change_k": first_change,
                              "pbest_updates_after_init": int(sum(pb_updates[1:])),
                              "gbest_updates_after_init": int(sum(1 for u in gb_updates[1:] if u)),
                              "mean_duplicate_pct": float(np.mean(dups)), "gbest_F_final": c.g_best_F,
                              "gbest_F_initial": its[0].gbest_F, "gain_over_init": c.g_best_F - its[0].gbest_F})
    def m(key, seq=per_cycle):
        v = [x[key] for x in seq if x[key] is not None]
        return {"mean": statistics.fmean(v), "median": statistics.median(v), "min": min(v), "max": max(v)} if v else None
    return {
        "run_label": run_label, "n_cycles": len(per_cycle),
        "k_stop": m("k_stop"),
        "gbest_never_changed_after_init": sum(1 for c in per_cycle if c["first_gbest_change_k"] is None),
        "first_gbest_change_k_distribution": dict(Counter(c["first_gbest_change_k"] for c in per_cycle)),
        "gbest_updates_after_init": m("gbest_updates_after_init"),
        "pbest_updates_after_init": m("pbest_updates_after_init"),
        "mean_duplicate_particles_pct": m("mean_duplicate_pct"),
        "gbest_gain_over_initialization": m("gain_over_init"),
        "cases_where_search_improved_on_initialization": sum(1 for c in per_cycle if c["gain_over_init"] > 1e-12),
        "by_iteration": {k: {kk: float(np.mean([d[kk] for d in v])) for kk in
                             ("unique_positions_S", "duplicate_particles_pct", "unique_F", "F_std", "mean_pairwise_distance_x_l2",
                              "mean_pairwise_distance_S_l1")} for k, v in sorted(per_iter.items())},
    }


def to_markdown(a: dict) -> str:
    L = [f"# Diagnóstico del PSO — {a['run_label']} (solo lectura; no modifica nada)", "",
         f"Ciclos analizados: {a['n_cycles']} · k_stop: media {a['k_stop']['mean']:.2f}, mediana {a['k_stop']['median']}, máx {a['k_stop']['max']}", "",
         "## Qué hace el enjambre",
         f"- g_best **nunca cambió después de la inicialización** en {a['gbest_never_changed_after_init']}/{a['n_cycles']} ciclos.",
         f"- Iteración del primer cambio de g_best (k → nº de ciclos): {a['first_gbest_change_k_distribution']}",
         f"- Actualizaciones de g_best tras k=0: media {a['gbest_updates_after_init']['mean']:.2f} (máx {a['gbest_updates_after_init']['max']}).",
         f"- Actualizaciones de p_best tras k=0: media {a['pbest_updates_after_init']['mean']:.1f} por ciclo.",
         f"- Ciclos en los que la búsqueda mejoró 𝓕 respecto de la mejor partícula inicial: **{a['cases_where_search_improved_on_initialization']}/{a['n_cycles']}** "
         f"(mejora media {a['gbest_gain_over_initialization']['mean']:.4f}, máx {a['gbest_gain_over_initialization']['max']:.4f}).",
         f"- Partículas duplicadas (misma S decodificada): media {a['mean_duplicate_particles_pct']['mean']:.1f}%.", "",
         "## Por iteración (promedio sobre ciclos que llegaron a esa iteración)", "",
         "| k | S únicas | % duplicadas | 𝓕 distintas | σ(𝓕) | dist. media x (L2) | dist. media S (L1) |", "|---|---|---|---|---|---|---|"]
    for k, v in a["by_iteration"].items():
        L.append(f"| {k} | {v['unique_positions_S']:.1f} | {v['duplicate_particles_pct']:.1f} | {v['unique_F']:.1f} | {v['F_std']:.4f} | "
                 f"{v['mean_pairwise_distance_x_l2']:.2f} | {v['mean_pairwise_distance_S_l1']:.2f} |")
    L += ["", "Lectura: 𝓕 es constante a tramos sobre S=φ(x) y la regla de parada literal `|ΔF|<ε` se cumple en cuanto una iteración no mejora g_best. "
          "No se modificó ninguna regla (DEC-10); cualquier cambio requeriría una decisión formal nueva.", ""]
    return "\n".join(L)


def main() -> None:
    ap = argparse.ArgumentParser(description="Diagnóstico de solo lectura del PSO de una corrida (REQUIERE PostgreSQL aislado; ver el docstring del módulo)")
    ap.add_argument("--run-label", required=True, help="corrida a auditar (puede ser una congelada: solo se lee)")
    ap.add_argument("--out-dir", help="directorio NUEVO y explícito del JSON (obligatorio; nunca experiments/results/)")
    ap.add_argument("--out-md", help="ruta NUEVA del informe Markdown (opcional; no se sobrescribe)")
    a = ap.parse_args().__dict__
    out_dir = iso.require_out_dir(a["out_dir"])
    json_path = out_dir / f"adaptation_swarm_{a['run_label']}_pso_audit.json"
    iso.check_output_targets([json_path] + ([Path(a["out_md"])] if a["out_md"] else []))     # antes de tocar la base
    iso.require_isolated_database()
    res = audit(a["run_label"])
    out_dir.mkdir(parents=True, exist_ok=True)
    with json_path.open("x", encoding="utf-8") as fh:                                          # modo "x": nunca sobrescribe
        fh.write(json.dumps(res, indent=2))
    md = to_markdown(res)
    if a["out_md"]:
        with Path(a["out_md"]).open("x", encoding="utf-8") as fh:
            fh.write(md)
    print(md)


if __name__ == "__main__":
    main()
