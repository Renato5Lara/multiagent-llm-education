"""Ejecutor de los experimentos OE2 (propuesta vs. sistemas convencionales), OE3 (efecto de la configuración) y OE4 (desempeño bajo distintas condiciones de simulación).

Cada experimento es un conjunto de `Condition` (oe/conditions.py). Para cada condición se ejecutan `batches` lotes; un lote = los perfiles × `k_replicates` réplicas, atendidos en BUCLE CERRADO por
`concurrency` usuarios virtuales sin tiempo de espera (la misma semántica que Locust). Se mide, por petición, la latencia (envoltura alrededor de la llamada), `t_conv_ms`, `k_stop`, el número de mensajes
y la calidad (𝓕 y brecha respecto del óptimo global); por lote, el throughput = peticiones correctas / tiempo de pared del lote.

Mismas condiciones para todos los sistemas: mismos perfiles y semillas (`derive_seed(batch_seed, profile_id, replicate)`), misma biblioteca, mismo 𝓕; el calentamiento (`warmup` peticiones) se descarta y
se declara. La propuesta corre sobre el bus Redis REAL (aislado); los sistemas convencionales corren en un pool de hilos (equivalente a un servidor síncrono que atiende varias peticiones).

ALCANCE: simulación en proceso (sin HTTP): la carga HTTP con Locust/JMeter vive en `loadtest/`. Nada se declara «oficial» aquí: el manifiesto lista las condiciones de validez (hardware objetivo, 100
perfiles, K ≥ 10, ≥ 5 lotes para el throughput) y marca la corrida EXPLORATORIA mientras alguna no se cumpla. La definición de «sistema convencional» (conventional.py) está PENDIENTE de confirmación.

    python -m adaptation_swarm.oe.runner oe2|oe3|oe4 --label L --out-dir NUEVO [--dry-run] [--limit n] [--k K] [--batches R] [--concurrency 1,10,25] [--design full|ofat] [--warmup W]
    python -m adaptation_swarm.oe.runner analyze --out-dir EXISTENTE            (rehace analysis.json desde observations.jsonl; determinista)
Requiere SWARM_REDIS_URL explícito y aislado (puerto 56379), como el resto de los ejecutores.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import time
import uuid
from collections import deque
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Awaitable, Callable

from adaptation_swarm.analysis import replicas as _infra
from adaptation_swarm.analysis.baseline_bruteforce import TARGET_HARDWARE, bruteforce_search, hardware_profile, meets_target
from adaptation_swarm.analysis.core_replay import precompute_terms
from adaptation_swarm.baselines.conventional import ConventionalAdapter
from adaptation_swarm.bus.redis_bus import RedisBus
from adaptation_swarm.config import SETTINGS
from adaptation_swarm.fitness.fitness import FitnessWeights
from adaptation_swarm.multimodal.library import LibraryStore
from adaptation_swarm.oe import analysis as oe_analysis
from adaptation_swarm.oe import definitions as oe_defs
from adaptation_swarm.oe import export as oe_export
from adaptation_swarm.oe.conditions import Condition, oe2_systems, oe3_full_factorial, oe3_one_factor_at_a_time, oe4_grid
from adaptation_swarm.profiles.generator import read_dataset
from adaptation_swarm.profiles.models import ProfileRequest
from adaptation_swarm.profiles.w_mapping import compute_weights
from adaptation_swarm.schemas.ids import derive_seed
from adaptation_swarm.stack import SwarmStack
from adaptation_swarm.tools import isolated_env as iso

SCHEMA = "oe-run-v2"      # v2: + seed y marca de tiempo por observación, statistical_input.csv, entorno PILOT/OFFICIAL_TARGET, equivalencia y definiciones
DEFAULT_PROFILES = _infra.DEFAULT_PROFILES
DEFAULT_BATCH_SEED = 26093001                      # semilla de lote propia de OE2–OE4 (no reutiliza las históricas 20260923 ni la maestra de K = 10)
MIN_BATCHES_FOR_THROUGHPUT = 5
MIN_K_FOR_CLAIM = 10
N_PROFILES_FOR_CLAIM = 100
PENDING_DECISIONS = [
    "Definición de «sistema convencional» (baselines/conventional.py: reglas fijas y búsqueda exhaustiva) por confirmar con el asesor.",
    "Hardware objetivo (8 vCPU / 32 GB, P6): hasta medir en él, los resultados son EXPLORATORIOS (D10).",
    "Definición operativa de «eficiencia de la adaptación» (OE3): se reportan sus componentes (t_conv_ms, k_stop, mensajes, brecha al óptimo); no se fabrica un índice compuesto.",
]

Call = Callable[[ProfileRequest, int], Awaitable[dict]]


def _sha_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


async def _closed_loop(call: Call, tasks: list[tuple[ProfileRequest, int]], concurrency: int) -> tuple[list[dict], float]:
    """`concurrency` usuarios virtuales que toman la siguiente tarea apenas terminan la anterior (sin espera). Devuelve (filas, tiempo de pared del lote en s)."""
    queue, rows = deque(tasks), []

    async def user() -> None:
        while queue:
            prof, rep = queue.popleft()
            started = datetime.now(timezone.utc).isoformat(timespec="milliseconds")
            t0 = time.perf_counter()
            out = await call(prof, rep)
            out["latency_ms"] = (time.perf_counter() - t0) * 1000.0
            out.update(t_start_utc=started, profile_id=prof.profile_id, archetype=prof.archetype.value if prof.archetype else None,
                       difficulty=prof.difficulty.value if prof.difficulty else None, replicate=rep)
            rows.append(out)

    t0 = time.perf_counter()
    await asyncio.gather(*(user() for _ in range(min(concurrency, len(tasks)) or 1)))
    return rows, time.perf_counter() - t0


def _swarm_row(r) -> dict:
    m = r.metrics
    return {"status": r.status, "stop_reason": r.stop_reason, "k_stop": r.k_stop, "t_conv_ms": r.t_conv_ms, "total_ms": r.total_ms, "F": r.g_best_F,
            "S": r.g_best_S, "predicted": r.predicted_dominant, "n_messages": m.n_messages if m else None,
            "comm_overhead_ms": m.comm_overhead_ms if m else None, "inflight_overlap": m.inflight_overlap if m else None, "n_evaluations": None,
            "package_valid": bool(r.package and r.package["validation"]["valid"] and r.package["chain_valid"]),
            "w_valid": bool(r.W) and abs(sum(r.W.values()) - 1.0) < 1e-9,                       # RF02: AG1 entregó W normalizada
            "iterations_logged": bool(r.k_stop is not None and len(r.iterations) == r.k_stop + 1),   # RF04: log de iteraciones completo
            "error": None if r.error is None else r.error.get("message"), "error_code": None if r.error is None else r.error.get("code")}


def _baseline_row(r) -> dict:
    return {"status": r.status, "stop_reason": None, "k_stop": None, "t_conv_ms": r.t_conv_ms, "total_ms": r.total_ms, "F": r.F, "S": r.S, "predicted": r.predicted_dominant,
            "n_messages": 0, "comm_overhead_ms": None, "inflight_overlap": None, "n_evaluations": r.n_evaluations,
            "package_valid": bool(r.package and r.package["validation"]["valid"] and r.package["chain_valid"]), "w_valid": None, "iterations_logged": None,
            "error": r.error, "error_code": None}


async def run_condition(store: LibraryStore, cond: Condition, profiles: list[ProfileRequest], *, k: int, batches: int, warmup: int, batch_seed: int,
                        fw: FitnessWeights, log=print, batch_offset: int = 0, exec_index: int | None = None) -> tuple[list[dict], list[dict]]:
    tasks = [(p, rep) for rep in range(k) for p in profiles]
    obs: list[dict] = []
    bat: list[dict] = []
    warm = [(p, 0) for p in profiles[:warmup]]

    async def execute(call: Call) -> None:
        if warm:
            await _closed_loop(call, list(warm), cond.concurrency)
        for b in range(batches):
            b_started = datetime.now(timezone.utc).isoformat(timespec="milliseconds")
            rows, elapsed = await _closed_loop(call, list(tasks), cond.concurrency)
            ok = [r for r in rows if r["status"] == "completed"]
            for r in rows:
                r.update(condition=cond.name, batch=b + batch_offset, exec_index=exec_index, **{f"f_{kk}": vv for kk, vv in cond.factors().items()})
            obs.extend(rows)
            bat.append({"condition": cond.name, "batch": b + batch_offset, "exec_index": exec_index, "concurrency": cond.concurrency, "n_requests": len(rows), "n_ok": len(ok), "n_failed": len(rows) - len(ok),
                        "t_start_utc": b_started, "elapsed_s": elapsed, "throughput_rps": len(ok) / elapsed if elapsed > 0 else None})
            log(f"  {cond.name} lote {b + 1}/{batches}: {len(ok)}/{len(rows)} ok, {elapsed:.2f} s, {len(ok) / elapsed:.1f} req/s")

    if cond.system == "swarm":
        params = cond.pso_params()
        prefix = f"swarm-oe-{uuid.uuid4().hex[:8]}:"
        try:
            async with SwarmStack(library_version=store.version, prefix=prefix, params=params, fitness_weights=fw,
                                  protocol=cond.protocol(), replicas=cond.replicas) as stack:
                async def call(p: ProfileRequest, rep: int) -> dict:
                    return {**_swarm_row(await stack.orchestrator.run_cycle(p, batch_seed=batch_seed, replicate=rep)), "seed": derive_seed(batch_seed, p.profile_id, rep)}
                await execute(call)
        finally:                                    # limpieza DESPUÉS de detener los agentes (si no, sus consumidores pierden el grupo y registran «bus caído»)
            cleanup = await RedisBus(prefix=prefix).connect()
            await cleanup.purge_prefix()
            await cleanup.close()
    else:
        adapter = ConventionalAdapter(store, cond.system, fw)

        async def call(p: ProfileRequest, rep: int) -> dict:
            return {**_baseline_row(await asyncio.to_thread(adapter.adapt, p)), "seed": None}      # determinista: no usa semilla
        await execute(call)
    return obs, bat


def add_optimum_gap(store: LibraryStore, profiles: list[ProfileRequest], obs: list[dict], fw: FitnessWeights) -> dict[str, float]:
    """Óptimo global de 𝓕 por perfil (fuerza bruta, FUERA de todo cronómetro) y brecha `F* − F` de cada observación."""
    opt: dict[str, float] = {}
    for p in profiles:
        memo: dict = {}
        precompute_terms(store, p.concept_id, memo)
        opt[p.profile_id] = bruteforce_search(store, p.concept_id, compute_weights(p), fw, memo=memo)["F"]
    for r in obs:
        r["F_opt"] = opt[r["profile_id"]]
        r["gap_vs_optimum"] = None if r.get("F") is None else opt[r["profile_id"]] - r["F"]
    return opt


def execution_plan(conds: list[Condition], batches: int, order: str, seed: int) -> list[tuple[Condition, int, int]]:
    """Orden de ejecución, determinista dado `seed`. `sequential`: cada condición con todos sus lotes seguidos (comportamiento original). `randomized-blocks`: `batches` RONDAS; en cada ronda todas las
    condiciones corren una vez en orden aleatorio (semilla = seed + ronda). Reparte la deriva térmica/temporal entre condiciones (el efecto condición deja de confundirse con la posición temporal); cada observación y
    lote registra `exec_index` para poder modelar la deriva."""
    if order == "sequential":
        plan = [(c, 0, len(conds)) for c in conds]
        return plan
    import random
    out = []
    for rnd in range(batches):
        shuffled = list(conds)
        random.Random(seed + rnd).shuffle(shuffled)
        out += [(c, rnd, len(conds) * batches) for c in shuffled]
    return out


def equivalence(obs: list[dict]) -> dict:
    """Condiciones EQUIVALENTES entre sistemas: a cada nivel de carga, todas las condiciones procesaron exactamente las mismas tareas (perfil, réplica) el mismo número de veces; la propuesta y los convencionales
    comparten además biblioteca, 𝓕, hardware y proceso (una sola corrida). Se verifica con los datos crudos, no se asume."""
    by_level: dict[int, dict[str, list]] = {}
    for r in obs:
        by_level.setdefault(int(r["f_concurrency"]), {}).setdefault(r["condition"], []).append((r["profile_id"], r["replicate"], r["batch"]))
    out = {}
    for level, conds in sorted(by_level.items()):
        sig = {c: sorted(v) for c, v in conds.items()}
        ref = next(iter(sig.values()))
        out[f"c{level}"] = {"conditions": sorted(sig), "same_tasks_and_batches": all(v == ref for v in sig.values()), "n_requests_each": {c: len(v) for c, v in sig.items()}}
    return {"per_load_level": out, "all_equivalent": all(v["same_tasks_and_batches"] for v in out.values()),
            "shared_by_construction": ["dataset", "biblioteca", "pesos de 𝓕", "hardware y proceso", "ensamblado y validación del paquete", "semilla derivada (propuesta) / determinista (convencionales)"]}


def conditions_for(experiment: str, args: argparse.Namespace) -> list[Condition]:
    if experiment == "oe2":
        return [c for cc in args.concurrency for c in oe2_systems(cc)]
    if experiment == "oe3":
        return oe3_full_factorial() if args.design == "full" else oe3_one_factor_at_a_time()
    return oe4_grid(concurrency=tuple(args.concurrency), n_particles=tuple(args.particles))


def validity(experiment: str, *, hw: dict, n_profiles: int, k: int, batches: int, warmup: int, conditions: list[Condition]) -> dict:
    conds = {"hardware_cercano_al_objetivo": meets_target(hw), "dataset_completo": n_profiles >= N_PROFILES_FOR_CLAIM, "calentamiento_declarado": warmup > 0}
    if experiment in ("oe2", "oe3"):
        conds["k_replicas_suficientes"] = k >= MIN_K_FOR_CLAIM
    if experiment in ("oe2", "oe4"):
        conds["lotes_suficientes_para_throughput"] = batches >= MIN_BATCHES_FOR_THROUGHPUT
    if experiment == "oe2":
        conds["propuesta_y_convencionales_presentes"] = {c.system for c in conditions} >= {"swarm", "rules", "bruteforce"}
    reasons = [f"no se cumple: {k_}" for k_, ok in conds.items() if not ok]
    blocked = oe_defs.blocked_for(experiment)
    official_execution = ("PENDING_HARDWARE" if not conds["hardware_cercano_al_objetivo"] else
                          ("BLOCKED_DEFINITION" if blocked else ("READY" if not reasons else "NOT_READY")))
    return {"conditions": conds, "status": "OFFICIAL_CANDIDATE" if not reasons and not blocked else "EXPLORATORY", "reasons": reasons, "blocked_definitions": blocked,
            "official_execution": official_execution, "environment_class": "OFFICIAL_TARGET" if conds["hardware_cercano_al_objetivo"] else "PILOT",
            "target_hardware": TARGET_HARDWARE, "pending_decisions": PENDING_DECISIONS}


def provenance(store: LibraryStore, profiles_path: Path, args: argparse.Namespace, conditions: list[Condition], n_profiles: int) -> dict:
    hw = hardware_profile()
    return {"schema": SCHEMA, "experiment": args.experiment, "label": args.label, "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "code": _infra.code_version(), "environment": _infra.environment(), "hardware": hw, "library_version": store.version,
            "dataset": {**_infra.dataset_identity(profiles_path), "file": profiles_path.name, "file_sha256": _sha_bytes(profiles_path.read_bytes()), "n_profiles": n_profiles},
            "design": {"k_replicates": args.k, "batches": args.batches, "warmup_requests": args.warmup, "batch_seed": args.batch_seed, "concurrency_levels": args.concurrency,
                       "design": getattr(args, "design", None), "order": getattr(args, "order", "sequential"), "particles": getattr(args, "particles", None)},
            "fitness_weights": FitnessWeights().to_dict(), "redis": iso.mask(SETTINGS.redis_url), "module_fingerprints": _infra.module_fingerprints(),
            "conditions": [{"name": c.name, **c.factors(), "pso": c.pso_params().to_dict(), "pso_config_hash": c.pso_params().config_hash()} for c in conditions],
            "validity": validity(args.experiment, hw=hw, n_profiles=n_profiles, k=args.k, batches=args.batches, warmup=args.warmup, conditions=conditions),
            "definitions": {"requirements_version": oe_defs.REQUIREMENTS_VERSION, "registry": oe_defs.DEFINITIONS, "f1_definition_versions": oe_defs.F1_DEFINITION_VERSIONS,
                            "f1_selected": oe_defs.f1_selection_record(getattr(args, "f1_definition_version", None))}}


def write_results(out_dir: Path, prov: dict, obs: list[dict], bat: list[dict], log_lines: list[str] | None = None) -> dict:
    out_dir.mkdir(parents=True, exist_ok=False)
    label, exp = prov["label"], prov["experiment"]
    analysis = oe_analysis.analyze(exp, obs, bat)
    eq = equivalence(obs)
    env = {"environment_class": prov["validity"]["environment_class"], "official_execution": prov["validity"]["official_execution"], "hardware": prov["hardware"], "software": prov["environment"],
           "redis": prov["redis"], "target_hardware": prov["validity"]["target_hardware"], "code": prov["code"], "library_version": prov["library_version"], "dataset": prov["dataset"]}
    files = {"observations.jsonl": "\n".join(json.dumps(r, sort_keys=True, default=str) for r in obs) + "\n",
             "batches.json": json.dumps(bat, indent=2, sort_keys=True), "provenance.json": json.dumps({**prov, "equivalence": eq}, indent=2, sort_keys=True, default=str),
             "analysis.json": json.dumps(analysis, indent=2, sort_keys=True, default=str),
             "raw_observations.csv": oe_export.raw_observations_csv(label, exp, obs), "statistical_input.csv": oe_export.statistical_input_csv(label, exp, obs, bat),
             "environment.json": json.dumps(env, indent=2, sort_keys=True, default=str),
             "summary.json": json.dumps({"experiment": exp, "label": label, "conditions": analysis["conditions"], "equivalence": eq["all_equivalent"]}, indent=2, sort_keys=True, default=str),
             "logs/run.log": "\n".join(log_lines or []) + "\n"}
    (out_dir / "logs").mkdir()
    for name, text in files.items():
        with (out_dir / name).open("x", encoding="utf-8") as fh:
            fh.write(text)
    sums = {n: _sha_bytes((out_dir / n).read_bytes()) for n in files}
    with (out_dir / "checksums.txt").open("x", encoding="utf-8") as fh:
        fh.write("".join(f"{h}  {n}\n" for n, h in sorted(sums.items())))
    manifest = {"schema": SCHEMA, "experiment": exp, "validity": prov["validity"]["status"], "environment_class": env["environment_class"], "official_execution": env["official_execution"],
                "files": sums}
    with (out_dir / "manifest.json").open("x", encoding="utf-8") as fh:
        fh.write(json.dumps(manifest, indent=2, sort_keys=True))
    return analysis


def analyze_dir(out_dir: Path) -> dict:
    """Rehace `analysis.json` desde los datos crudos (determinista) y lo compara con el archivado."""
    obs = [json.loads(l) for l in (out_dir / "observations.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    bat = json.loads((out_dir / "batches.json").read_text(encoding="utf-8"))
    prov = json.loads((out_dir / "provenance.json").read_text(encoding="utf-8"))
    return oe_analysis.analyze(prov["experiment"], obs, bat)


def official_gate(validity_: dict) -> list[str]:
    """Razones por las que una ejecución declarada `--official` NO puede comenzar (lista vacía = puede). Se evalúa ANTES de conectar o escribir nada: una máquina que no cumple el hardware objetivo no puede producir
    resultados que se confundan con oficiales (el requisito de 8 vCPU / 32 GB no se relaja). Reutiliza `validity`, sin reglas nuevas."""
    reasons = [f"hardware: {r}" for r in validity_["reasons"] if "hardware" in r]
    if validity_["official_execution"] == "PENDING_HARDWARE" and not reasons:
        reasons.append(f"hardware: no cercano al objetivo {validity_['target_hardware']}")
    reasons += [r for r in validity_["reasons"] if "hardware" not in r]
    reasons += [f"definición bloqueada: {b}" for b in validity_["blocked_definitions"]]
    return reasons


def _ints(s: str) -> list[int]:
    return [int(x) for x in s.split(",") if x]


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("experiment", choices=("oe2", "oe3", "oe4", "analyze"))
    ap.add_argument("--label")
    ap.add_argument("--out-dir")
    ap.add_argument("--library-version")
    ap.add_argument("--profiles", type=Path, default=DEFAULT_PROFILES)
    ap.add_argument("--limit", type=int)
    ap.add_argument("--k", type=int, default=1, help="réplicas por perfil y lote (semillas derivadas)")
    ap.add_argument("--batches", type=int, default=1, help="lotes por condición (repeticiones de tiempo; necesarios para inferir throughput)")
    ap.add_argument("--warmup", type=int, default=10, help="peticiones de calentamiento descartadas por condición")
    ap.add_argument("--batch-seed", type=int, default=DEFAULT_BATCH_SEED)
    ap.add_argument("--concurrency", type=_ints, default=[1])
    ap.add_argument("--particles", type=_ints, default=[10, 20, 30])
    ap.add_argument("--design", choices=("full", "ofat"), default="ofat")
    ap.add_argument("--f1-definition-version", choices=sorted(oe_defs.F1_DEFINITION_VERSIONS), help="versión de la definición F1 que la corrida declara en su provenance (este ejecutor no calcula F1; sin valor se registra `selected: null`)")
    ap.add_argument("--order", choices=("sequential", "randomized-blocks"), default="sequential", help="orden de ejecución de las condiciones (randomized-blocks: --batches rondas con orden aleatorio por ronda)")
    ap.add_argument("--official", action="store_true", help="declara la ejecución como OFICIAL: se niega a arrancar si el hardware objetivo o las condiciones de validez no se cumplen (sin esta marca la corrida es PILOT/exploratoria)")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)
    out_dir = iso.require_out_dir(args.out_dir)
    if args.experiment == "analyze":
        print(json.dumps(analyze_dir(out_dir), indent=2, sort_keys=True, default=str))
        return
    if not args.label:
        raise SystemExit("--label es obligatorio")
    iso.check_label(args.label)
    iso.check_new_output_targets([out_dir])
    iso.require_isolated_redis()
    store = LibraryStore.open(SETTINGS.library_root, args.library_version)
    profiles = read_dataset(args.profiles)[: args.limit] if args.limit else read_dataset(args.profiles)
    missing = sorted({p.concept_id for p in profiles if not store.is_complete(p.concept_id)})
    if missing:
        raise SystemExit(f"BLOQUEADO: la biblioteca {store.version} no cubre {len(missing)} conceptos")
    conds = conditions_for(args.experiment, args)
    prov = provenance(store, args.profiles, args, conds, len(profiles))
    if args.official:
        refusals = official_gate(prov["validity"])
        if refusals:
            raise SystemExit("EJECUCIÓN OFICIAL RECHAZADA (no se escribió nada):\n  - " + "\n  - ".join(refusals))
    if args.dry_run:
        print(f"DRY-RUN OK: {args.experiment}, {len(conds)} condiciones × {args.batches} lotes × {len(profiles)} perfiles × {args.k} réplicas; validez: {prov['validity']['status']}; "
              f"no se conectó ni se escribió nada")
        for r in prov["validity"]["reasons"]:
            print("  -", r)
        return
    fw, obs, bat, lines = FitnessWeights(), [], [], []

    def log(msg: str) -> None:
        lines.append(msg)
        print(msg, flush=True)

    for exec_index, (c, batch_no, n_total) in enumerate(execution_plan(conds, args.batches, args.order, args.batch_seed), 1):
        log(f"[{exec_index}/{n_total}] {c.name} (lote {batch_no})")
        o, b = asyncio.run(run_condition(store, c, profiles, k=args.k, batches=1 if args.order == "randomized-blocks" else args.batches, warmup=args.warmup,
                                         batch_seed=args.batch_seed, fw=fw, log=log, batch_offset=batch_no, exec_index=exec_index))
        obs.extend(o)
        bat.extend(b)
    add_optimum_gap(store, profiles, obs, fw)
    analysis = write_results(out_dir, prov, obs, bat, lines)
    print(f"escrito: {out_dir} ({len(obs)} observaciones; validez {prov['validity']['status']})")
    print(json.dumps(analysis.get("headline", {}), indent=2, default=str))


if __name__ == "__main__":
    main()
