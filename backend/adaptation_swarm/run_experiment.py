"""Experimento de los n=100 casos sintéticos (DECISION-CLOSURE §8) y barrido de sensibilidad
pre-registrado (§6.2, §DEC-08). Ejecuta ciclos REALES (Redis + LangGraph + biblioteca con audio real).

Uso (desde backend/), SOLO sobre el entorno aislado (tests/adaptation_swarm/integration_env/) con el destino EXPLÍCITO en el entorno:
    export SWARM_REDIS_URL=redis://127.0.0.1:56379/0                        # y, si se persiste, DATABASE_URL=postgresql+psycopg://swarm_test:…@127.0.0.1:55432/swarm_test
    python -m adaptation_swarm.run_experiment --run-label repro-1 --out-dir /ruta/nueva --dry-run    # valida el plan y las salvaguardas; no conecta ni escribe
    python -m adaptation_swarm.run_experiment --sweep --out-dir /ruta/nueva                          # sensibilidad (Redis; sin BD)
    python -m adaptation_swarm.run_experiment --run-label repro-1 --out-dir /ruta/nueva              # los 100 casos (Redis + PostgreSQL; --no-persist omite PostgreSQL)

Requisitos y efectos (nada se hace al importar el módulo):
  · Redis (obligatorio, DEC-05) y la biblioteca M1 con audio y SVG, en solo lectura: el ciclo valida el paquete abriendo el audio. No llama a OpenAI ni genera audio.
  · PostgreSQL solo sin `--no-persist`: escribe swarm_profiles/swarm_runs/swarm_cycles/… en la base indicada.
  · Ejecuta `git rev-parse|branch|status` (solo lectura) para registrar el commit; no modifica el repositorio.
  · Escribe únicamente en `--out-dir` (obligatorio, sin valor por defecto), jamás dentro de `experiments/results/` (resultados congelados) ni sobre un archivo existente;
    las etiquetas de las corridas congeladas (`corrida-poc-1/2`) no se reutilizan.

Todo valor reportado es MEDIDO; los umbrales de la asesoría se muestran como referencia, y solo se marca
"cumple"/"no cumple" para lo que este experimento realmente mide. L_resp/Throughput HTTP NO se miden aquí
(ver `loadtest/`): la latencia de ciclo reportada es en proceso, sin HTTP.
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
import subprocess
import time
import uuid
from collections import Counter
from dataclasses import replace
from pathlib import Path

import numpy as np

from adaptation_swarm import SPEC_VERSION
from adaptation_swarm.bus.redis_bus import RedisBus
from adaptation_swarm.config import SETTINGS
from adaptation_swarm.fitness.fitness import FitnessWeights
from adaptation_swarm.gold.dataset import gold_for
from adaptation_swarm.gold.f1 import bootstrap_ci, f1_report
from adaptation_swarm.metrics.convergence import convergence_summary
from adaptation_swarm.metrics.performance import latency_report
from adaptation_swarm.metrics.search_quality import brute_force_optimum
from adaptation_swarm.multimodal.library import LibraryStore
from adaptation_swarm.profiles.generator import read_dataset
from adaptation_swarm.profiles.models import ModalityWeights
from adaptation_swarm.profiles.w_mapping import compute_weights
from adaptation_swarm.pso.params import PSOParams
from adaptation_swarm.pso.rng import make_rng
from adaptation_swarm.stack import SwarmStack
from adaptation_swarm.tools import isolated_env as iso

ROOT = Path(__file__).resolve().parents[2]
DATASET = ROOT / "datasets" / "synthetic_profiles" / "profiles-v1.jsonl"
SENSITIVITY_FILE = "adaptation_swarm_sensitivity.json"
REFERENCE_WEIGHTS = FitnessWeights()                      # 0.40 / 0.30 / 0.15 / 0.15
BATCH_SEED = 20260923


def _git() -> dict:
    def run(*a):
        return subprocess.run(["git", *a], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    return {"commit": run("rev-parse", "HEAD"), "branch": run("branch", "--show-current"),
            "dirty": bool(run("status", "--porcelain"))}


def weights_with_alpha(alpha: float) -> FitnessWeights:
    """α variable; β, γ, δ reescalados proporcionalmente para conservar α+β+γ+δ = 1 (§6.2)."""
    rest = REFERENCE_WEIGHTS.beta + REFERENCE_WEIGHTS.gamma + REFERENCE_WEIGHTS.delta
    k = (1.0 - alpha) / rest
    return FitnessWeights(alpha, REFERENCE_WEIGHTS.beta * k, REFERENCE_WEIGHTS.gamma * k, REFERENCE_WEIGHTS.delta * k)


async def run_cases(store: LibraryStore, profiles, params: PSOParams, fw: FitnessWeights, *, repository=None,
                    batch_seed: int = BATCH_SEED, with_optimum: bool = True, log=print) -> dict:
    prefix = f"swarm-exp-{uuid.uuid4().hex[:6]}:"
    results, rows, pairs = [], [], []
    async with SwarmStack(library_version=store.version, prefix=prefix, params=params, fitness_weights=fw,
                          repository=repository) as stack:
        for i, prof in enumerate(profiles, 1):
            r = await stack.orchestrator.run_cycle(prof, batch_seed=batch_seed)
            g = gold_for(prof)
            gap = None
            n_opt = None
            if r.status == "completed":
                pairs.append((g.expected_dominant, r.predicted_dominant))
                if with_optimum:
                    opt = brute_force_optimum(store, prof.concept_id, ModalityWeights(**r.W), fw)
                    gap, n_opt = opt.F - r.g_best_F, opt.n_optimal
            results.append(r)
            rows.append({
                "profile_id": prof.profile_id, "archetype": prof.archetype.value, "difficulty": prof.difficulty.value,
                "concept": prof.metadata["concept_title"], "status": r.status, "stop_reason": r.stop_reason,
                "k_stop": r.k_stop, "t_conv_ms": None if r.t_conv_ms is None else round(r.t_conv_ms, 2),
                "total_ms": round(r.total_ms, 2), "g_best_F": r.g_best_F, "g_best_S": r.g_best_S,
                "expected": g.expected_dominant, "predicted": r.predicted_dominant,
                "gap_vs_bruteforce": gap, "n_optimal_configs": n_opt,
                "n_messages": r.metrics.n_messages, "comm_overhead_ms": r.metrics.comm_overhead_ms,
                "error": None if r.error is None else r.error.get("message")})
            if i % 20 == 0:
                log(f"  {i}/{len(profiles)} ciclos")
    cleanup = await RedisBus(prefix=prefix).connect()      # limpieza DESPUÉS de detener los agentes
    await cleanup.purge_prefix()
    await cleanup.close()
    return {"results": results, "rows": rows, "pairs": pairs}


def summarize(run: dict, *, batch_seed: int) -> dict:
    results, rows, pairs = run["results"], run["rows"], run["pairs"]
    metrics = [r.metrics for r in results]
    conv = convergence_summary(metrics)
    ok = [r for r in results if r.status == "completed"]
    f1 = f1_report(pairs) if pairs else None
    ci = bootstrap_ci(pairs, make_rng(batch_seed), n_boot=2000) if pairs else None
    gaps = [x["gap_vs_bruteforce"] for x in rows if x["gap_vs_bruteforce"] is not None]
    return {
        "n": len(results), "completed": len(ok), "failed": len(results) - len(ok),
        "convergence": conv,
        "f1": None if f1 is None else {**f1.to_dict(), "ci95_bootstrap": list(ci), "n_pairs": len(pairs)},
        "search_quality": {
            "mean_gap_to_global_optimum": float(np.mean(gaps)) if gaps else None,
            "max_gap": float(max(gaps)) if gaps else None,
            "cases_at_global_optimum": sum(1 for g in gaps if g <= 1e-9), "n": len(gaps)},
        "cycle_latency_in_process_ms": latency_report([r.total_ms for r in ok]),
        "t_conv_ms": latency_report([r.t_conv_ms for r in ok if r.t_conv_ms is not None]),
        "comm_overhead_ms_mean": float(np.mean([m.comm_overhead_ms for m in metrics if m.comm_overhead_ms is not None])) if ok else None,
        "audio_in_every_package": all(r.package and r.package["audio"]["path"] for r in ok),
        "package_validation": {
            "all_valid": all(r.package["validation"]["valid"] for r in ok) if ok else None,
            "packages_with_cpp": sum(1 for r in ok if r.package["code"].get("cpp")),
            "packages_with_svg": sum(1 for r in ok if (r.package["diagram"].get("svg") or None)),
        },
        "pso_diagnostics": {
            "gbest_never_changed_after_init": sum(1 for r in ok if r.pso_diagnostics and r.pso_diagnostics["gbest_never_changed_after_init"]),
            "first_gbest_change_k": dict(Counter(r.pso_diagnostics["first_gbest_change_k"] for r in ok if r.pso_diagnostics)),
            "mean_duplicate_particles_pct": float(np.mean([r.pso_diagnostics["mean_duplicate_particles_pct"] for r in ok if r.pso_diagnostics])) if ok else None,
            "mean_pbest_updates_after_init": float(np.mean([r.pso_diagnostics["pbest_updates_after_init"] for r in ok if r.pso_diagnostics])) if ok else None,
            "mean_gbest_updates_after_init": float(np.mean([r.pso_diagnostics["gbest_updates_after_init"] for r in ok if r.pso_diagnostics])) if ok else None,
        },
        "predicted_distribution": {c: sum(1 for _g, p in pairs if p == c) for c in ("code", "diagram", "text", "audio")},
    }


def report_paths(label: str, out_dir: Path) -> list[Path]:
    return [out_dir / f"adaptation_swarm_{label}.json", out_dir / f"adaptation_swarm_{label}_cases.csv"]


def write_reports(label: str, cfg: dict, summary: dict, rows: list[dict], out_dir: Path) -> Path:
    """Escribe SOLO en `out_dir`; modo "x": nunca sobrescribe un archivo existente."""
    json_path, csv_path = report_paths(label, out_dir)
    if any(p.exists() for p in (json_path, csv_path)):                    # antes de escribir nada: sin escrituras parciales
        raise FileExistsError(f"ya existe un resultado de '{label}' en {out_dir}: los resultados no se sobrescriben")
    out_dir.mkdir(parents=True, exist_ok=True)
    with json_path.open("x", encoding="utf-8") as fh:
        fh.write(json.dumps({"config": cfg, "summary": summary, "cases": rows}, indent=2, default=str))
    with csv_path.open("x", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows({k: (json.dumps(v) if isinstance(v, list) else v) for k, v in r.items()} for r in rows)
    return json_path


async def run_sweep(store, profiles, log=print) -> dict:
    """Sensibilidad pre-registrada: α ∈ {0.3, 0.4, 0.5} (β,γ,δ reescalados) y N ∈ {10, 20, 30}."""
    grid = [("alpha=0.3", PSOParams(), weights_with_alpha(0.3)), ("alpha=0.4(ref)", PSOParams(), weights_with_alpha(0.4)),
            ("alpha=0.5", PSOParams(), weights_with_alpha(0.5)),
            ("N=10", PSOParams(n_particles=10), REFERENCE_WEIGHTS), ("N=20(ref)", PSOParams(n_particles=20), REFERENCE_WEIGHTS),
            ("N=30", PSOParams(n_particles=30), REFERENCE_WEIGHTS)]
    out, base_pred = {}, None
    for name, params, fw in grid:
        log(f"sweep {name}")
        run = await run_cases(store, profiles, params, fw, with_optimum=True, log=lambda *_: None)
        s = summarize(run, batch_seed=BATCH_SEED)
        pred = [r.predicted_dominant for r in run["results"]]
        if name in ("alpha=0.4(ref)",):
            base_pred = pred
        out[name] = {"weights": fw.to_dict(), "params": params.to_dict(), "f1_adapt": s["f1"]["f1_adapt"],
                     "accuracy": s["f1"]["accuracy"], "CR": s["convergence"]["CR"],
                     "k_stop_mean": s["convergence"]["k_stop"]["mean"], "mean_gap": s["search_quality"]["mean_gap_to_global_optimum"],
                     "predicted_distribution": s["predicted_distribution"], "_pred": pred}
    for name, v in out.items():
        v["agreement_with_reference_predictions"] = float(np.mean([a == b for a, b in zip(v.pop("_pred"), base_pred)]))
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-label", help="etiqueta de la corrida NUEVA (obligatoria salvo con --sweep o --dry-run sin corrida); no puede ser corrida-poc-1/2")
    ap.add_argument("--out-dir", help="directorio de resultados NUEVO y explícito (obligatorio para escribir); nunca experiments/results/")
    ap.add_argument("--batch-seed", type=int, default=BATCH_SEED)
    ap.add_argument("--library-version")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--dry-run", action="store_true", help="valida plan, biblioteca y salvaguardas sin conectar ni escribir")
    ap.add_argument("--no-persist", action="store_true", help="no escribe en PostgreSQL")
    ap.add_argument("--sweep", action="store_true", help="barrido de sensibilidad pre-registrado")
    args = ap.parse_args()

    # 1) salvaguardas que no necesitan ningún servicio: modo explícito, etiqueta, destino de resultados nuevo y sin sobrescribir
    if not args.sweep and not args.run_label:
        raise SystemExit("modo obligatorio: --sweep o --run-label <etiqueta nueva> (con --dry-run solo se valida)")
    if args.run_label:
        iso.check_label(args.run_label)
    out_dir = iso.require_out_dir(args.out_dir)
    iso.check_output_targets([out_dir / SENSITIVITY_FILE] if args.sweep else report_paths(args.run_label, out_dir))
    # 2) destinos EXPLÍCITOS y aislados (no conectan): Redis siempre; PostgreSQL solo si se persiste
    persist = not args.sweep and not args.no_persist
    iso.require_isolated_redis()
    if persist:
        iso.require_isolated_database()

    store = LibraryStore.open(SETTINGS.library_root, args.library_version)
    profiles = read_dataset(DATASET)[: args.limit] if args.limit else read_dataset(DATASET)
    missing = sorted({p.concept_id for p in profiles if not store.is_complete(p.concept_id)})
    if missing:
        raise SystemExit(f"BLOQUEADO: la biblioteca {store.version} no cubre {len(missing)} conceptos: {missing}")
    if args.dry_run:
        print(f"DRY-RUN OK: {len(profiles)} perfiles, biblioteca {store.version}, todos los conceptos cubiertos; "
              f"salida en {out_dir} ({'sensibilidad' if args.sweep else args.run_label}); PostgreSQL: {'sí' if persist else 'no'}; no se conectó ni se escribió nada")
        return
    if args.sweep:
        res = asyncio.run(run_sweep(store, profiles))
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / SENSITIVITY_FILE
        with path.open("x", encoding="utf-8") as fh:                       # modo "x": nunca sobrescribe
            fh.write(json.dumps({"library_version": store.version, "n": len(profiles), "batch_seed": args.batch_seed,
                                 "git": _git(), "results": res}, indent=2))
        for k, v in res.items():
            print(f"{k:16s} F1_adapt={v['f1_adapt']:.3f} acc={v['accuracy']:.3f} CR={v['CR']:.2f} k̄={v['k_stop_mean']:.2f} "
                  f"gap̄={v['mean_gap']:.4f} concuerda_con_ref={v['agreement_with_reference_predictions']:.2f}")
        print(path)
        return
    params, fw = PSOParams(), REFERENCE_WEIGHTS
    repo = None
    if persist:
        from adaptation_swarm.persistence.repository import PostgresCycleRepository
        repo = PostgresCycleRepository()
        repo.save_profiles(profiles, "v1")
        repo.sync_library(store)
        repo.start_run(args.run_label, batch_seed=args.batch_seed, dataset_version="v1", library_version=store.version,
                       config={"pso": params.to_dict(), "fitness_weights": fw.to_dict()}, config_hash=params.config_hash(),
                       git_commit=_git()["commit"])
    t0 = time.perf_counter()
    run = asyncio.run(run_cases(store, profiles, params, fw, repository=repo, batch_seed=args.batch_seed))
    summary = summarize(run, batch_seed=args.batch_seed)
    cfg = {"run_label": args.run_label, "spec_version": SPEC_VERSION, "batch_seed": args.batch_seed,
           "pso": params.to_dict(), "fitness_weights": fw.to_dict(), "library_version": store.version,
           "dataset": "profiles-v1", "git": _git(), "elapsed_s": round(time.perf_counter() - t0, 1)}
    if repo is not None:
        repo.finish_run(args.run_label, summary)
    path = write_reports(args.run_label, cfg, summary, run["rows"], out_dir)
    c, f = summary["convergence"], summary["f1"]
    print(f"casos={summary['n']} completados={summary['completed']} fallidos={summary['failed']}")
    print(f"CR={c['CR']:.3f} stop_reasons={c['stop_reasons']} k_stop(max)={c['k_stop']['max']}")
    if f:
        print(f"F1_adapt={f['f1_adapt']:.3f} IC95={[round(x, 3) for x in f['ci95_bootstrap']]} macro_all4={f['macro_f1_all4']:.3f} acc={f['accuracy']:.3f}")
    print(path)


if __name__ == "__main__":
    main()
