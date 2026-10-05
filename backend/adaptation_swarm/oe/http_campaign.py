"""Orquestador de la campaña HTTP de OE2 y OE4 (L_resp P95 y throughput oficiales). Plan determinista + ejecución por corrida con Locust + resumen por ventana estacionaria (`http_window`).

    python -m adaptation_swarm.oe.http_campaign oe4|oe2 --campaign-id ID --out-dir NUEVO [--runs 10] [--users 1,5,10,25,50,100] [--particles 10,20,30] [--systems swarm,decision_table] [--persist-policy off]
            [--warmup 10] [--window 60] [--base-seed S] [--order randomized-blocks|sequential] [--official] [--dry-run]
    python -m adaptation_swarm.oe.http_campaign analyze --out-dir EXISTENTE            (rehace analysis.json desde runs.jsonl; determinista)

Diseño: OE4 = swarm × usuarios {1,5,10,25,50,100} × N {10,20,30}; OE2 = sistemas {swarm, decision_table} (convencional independiente; rules y bruteforce solo como contrastes auxiliares) × usuarios (N de referencia). ≥ 10 corridas independientes por celda. Cada corrida `i` tiene su PROPIA
semilla `derive_seed(base_seed, "http-campaign-run", i)`: dos corridas de una celda nunca comparten semilla; la misma `i` reutiliza la semilla entre celdas (diseño BLOQUEADO) y cada corrida sigue identificada por
`run_id`. N se fija reiniciando el servidor (`SWARM_API_N_PARTICLES`). Duración de cada corrida = calentamiento + ventana estacionaria (+ margen de arranque); el calentamiento se descarta en el análisis.

Se rechaza `--official` si el hardware no es el objetivo o quedan bloqueos de la especificación (`campaign_spec.open_blockers`); sin la marca la campaña es PILOT y queda etiquetada así. No simula resultados: sin
Locust y servidor reales no hay corridas. Los resultados nunca se escriben sobre un directorio existente.
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import os
import random
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Sequence

from adaptation_swarm.analysis import replicas as _infra
from adaptation_swarm.analysis.baseline_bruteforce import DEFAULT_PROFILES, TARGET_HARDWARE, hardware_profile, meets_target
from adaptation_swarm.baselines.conventional import SYSTEM_ROLES
from adaptation_swarm.oe import campaign_spec, code_state, http_window, oe2_confirmatory, profile_sequence, time_contract
from adaptation_swarm.oe import definitions as oe_defs
from adaptation_swarm.oe.conditions import SYSTEMS
from adaptation_swarm.oe.factorial import factorial_anova
from adaptation_swarm.profiles.generator import read_dataset
from adaptation_swarm.pso.params import PSOParams
from adaptation_swarm.schemas.ids import derive_seed

SCHEMA = "oe-http-campaign-v1"
OE4_USERS, OE4_PARTICLES = (1, 5, 10, 25, 50, 100), (10, 20, 30)
RUNS_PER_CELL_MIN = 10
DEFAULT_BASE_SEED = 26100501
DEFAULT_OE2_SYSTEMS = tuple(campaign_spec.SPEC["oe2"]["design"]["systems"])        # propuesta + convencional independiente (campaign_spec); rules y bruteforce son auxiliares opcionales
PERSIST_POLICIES = ("off",)                                                         # «on» no está soportada para comparar: el baseline nunca persiste
SEQUENCE_PREVIEW_REQUESTS = 50                                                      # peticiones por usuario que entran al hash de la secuencia esperada
START_MARGIN_S = 5.0                                         # arranque de usuarios (rampa); cae dentro del calentamiento, no de la ventana
RECORD_FIELDS = ("campaign_id", "campaign_spec_hash", "run_id", "batch_id", "seed", "system", "load", "swarm_N", "warmup_seconds", "stationary_seconds", "total_requests", "successful_requests", "errors",
                 "timeouts", "p50_ms", "mean_ms", "p95_ms", "throughput_http", "throughput_internal", "generator_cpu", "timestamp", "commit", "hardware", "definition_version")


def run_seed(base_seed: int, run_index: int) -> int:
    return derive_seed(base_seed, "http-campaign-run", run_index)


def plan(experiment: str, *, runs: int, base_seed: int, users: Sequence[int], particles: Sequence[int], systems: Sequence[str], order: str, campaign_id: str, profile_ids: Sequence[str] | None = None) -> list[dict]:
    """Todas las corridas previstas, en orden de ejecución. `randomized-blocks`: por ronda `i` todas las celdas en orden aleatorio determinista (Random(base_seed + i)): reparte la deriva térmica entre celdas."""
    if experiment == "oe4":
        cells = [{"system": "swarm", "load": u, "swarm_N": n} for n in particles for u in users]
    elif experiment == "oe2":
        ref_n = PSOParams().n_particles
        bad = [s for s in systems if s not in SYSTEMS]
        if bad:
            raise ValueError(f"sistemas desconocidos: {bad}; válidos: {SYSTEMS}")
        missing = {campaign_spec.SPEC["oe2"]["proposal_system"], campaign_spec.SPEC["oe2"]["conventional_system"]} - set(systems)
        if missing:
            raise ValueError(f"una campaña OE2 exige la propuesta y el convencional independiente; faltan: {sorted(missing)} (rules y bruteforce son contrastes auxiliares)")
        cells = [{"system": s, "load": u, "swarm_N": ref_n} for s in systems for u in users]
    else:
        raise ValueError(f"experimento desconocido: {experiment!r}")
    ids = list(profile_ids) if profile_ids is not None else [p.profile_id for p in read_dataset(DEFAULT_PROFILES)]
    out = []
    for i in range(runs):
        ordered = list(cells)
        if order == "randomized-blocks":
            random.Random(base_seed + i).shuffle(ordered)
        for c in ordered:
            cell = f"{c['system']}|u{c['load']}|N{c['swarm_N']}"
            seed = run_seed(base_seed, i)
            out.append({**c, "cell": cell, "run_index": i, "seed": seed, "system_role": time_contract.PROPOSAL if c["system"] == "swarm" else SYSTEM_ROLES[c["system"]], "persist_policy": "off",
                        "profile_sequence_sha256": profile_sequence.sequence_sha256(seed, c["load"], SEQUENCE_PREVIEW_REQUESTS, ids), "batch_id": f"{campaign_id}-b{i:02d}", "run_id": f"{campaign_id}-{cell}-r{i:02d}"})
    return out


def official_refusals(hw: dict, runs: int, warmup: float, window: float) -> list[str]:
    reasons = [] if meets_target(hw) else [f"hardware: no cercano al objetivo {TARGET_HARDWARE}"]
    if runs < RUNS_PER_CELL_MIN:
        reasons.append(f"corridas por celda {runs} < {RUNS_PER_CELL_MIN}")
    if warmup < http_window.WARMUP_S_MIN or window < http_window.WINDOW_S_MIN:
        reasons.append(f"calentamiento ≥ {http_window.WARMUP_S_MIN:.0f} s y ventana ≥ {http_window.WINDOW_S_MIN:.0f} s requeridos")
    return reasons + [f"bloqueo: {b}" for b in campaign_spec.open_blockers()]


def record(run: dict, summary: dict, prov: dict) -> dict:
    """Fila oficial de una corrida con los nombres de campo pedidos. Lo no medido es `None`, nunca un valor inventado (`throughput_internal` lo mide `oe/runner.py`, no el generador HTTP)."""
    ok = summary.get("status") == "ok"
    return {"campaign_id": prov["campaign_id"], "campaign_spec_hash": prov["campaign_spec"]["sha256"], "run_id": run["run_id"], "batch_id": run["batch_id"], "seed": run["seed"], "system": run["system"],
            "load": run["load"], "swarm_N": run["swarm_N"], "warmup_seconds": summary.get("warmup_s"), "stationary_seconds": summary.get("duration_s"), "total_requests": summary.get("requests_total"),
            "successful_requests": summary.get("requests_ok") if ok else None, "errors": summary.get("errors") if ok else None, "timeouts": summary.get("timeouts") if ok else None,
            "p50_ms": summary.get("latency_p50_ms"), "mean_ms": summary.get("latency_mean_ms"), "p95_ms": summary.get("latency_p95_ms"), "throughput_http": summary.get("throughput_rps"),
            "throughput_internal": None, "generator_cpu": summary.get("loadgen_cpu_percent_max"), "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"), "commit": prov["code"],
            "hardware": prov["hardware"], "definition_version": prov["definition_version"],
            # derivados para el análisis (no sustituyen a los campos oficiales)
            "status": summary.get("status"), "regime": summary.get("regime"), "error_rate": summary.get("error_rate"), "latency_p95_ms": summary.get("latency_p95_ms"),
            "throughput_rps": summary.get("throughput_rps"), "users": run["load"], "t_conv_ms_mean": summary.get("t_conv_ms_mean"), "generator_possibly_bottleneck": summary.get("generator_possibly_bottleneck"),
            "environment_class": prov["environment_class"], "official": prov["official"], "oe2_official": prov["oe2_official"],
            # contrato de tiempo, rol, persistencia y secuencia (Fase B)
            "system_role": run["system_role"], "persist_policy": run["persist_policy"], "decision_ms_mean": summary.get("decision_ms_mean"), "decision_ms_validation": time_contract.VALIDATION_STATUS,
            "profile_sequence_sha256": run["profile_sequence_sha256"], "profile_sequence_check": summary.get("profile_sequence_check"),
            "requests_without_cycle_metrics": summary.get("requests_without_cycle_metrics")}


def provenance(args: argparse.Namespace, runs: list[dict]) -> dict:
    hw = hardware_profile()
    refusals = official_refusals(hw, args.runs, args.warmup, args.window)
    return {"schema": SCHEMA, "campaign_id": args.campaign_id, "experiment": args.experiment, "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "campaign_spec": campaign_spec.identity(),
            "code": _infra.code_version(), "environment": _infra.environment(), "hardware": hw, "environment_class": "OFFICIAL_TARGET" if meets_target(hw) else "PILOT", "official": bool(args.official), "oe2_official": False,
            "official_refusals": refusals, "definition_version": {"requirements": oe_defs.REQUIREMENTS_VERSION, "f1": oe_defs.f1_selection_record(None)},
            "design": {"runs_per_cell": args.runs, "users": args.users, "particles": args.particles, "systems": args.systems, "warmup_s": args.warmup, "window_s": args.window, "base_seed": args.base_seed,
                       "order": args.order, "n_planned_runs": len(runs), "seed_rule": "derive_seed(base_seed, 'http-campaign-run', run_index); distinta por corrida, compartida entre celdas (bloqueado)"},
            "persist_policy": args.persist_policy, "api_persist_env_forced": "0" if args.persist_policy == "off" else None, "generator_shares_host_with_server": True,
            "code_state": code_state.git_state(), "campaign_source_fingerprints": code_state.source_fingerprints(),
            "systems": {s: (time_contract.PROPOSAL if s == "swarm" else SYSTEM_ROLES[s]) for s in sorted({r["system"] for r in runs})},
            "time_contract": {"version": time_contract.CONTRACT_VERSION, "status": time_contract.STATUS, "candidate_common_metric": time_contract.COMMON_METRIC, "validation": time_contract.VALIDATION_STATUS,
                              "t_conv_equivalence": time_contract.T_CONV_EQUIVALENCE, "definitions": time_contract.DEFINITIONS,
                              "known_limits": list(time_contract.KNOWN_LIMITS)},
            "profile_sequence": {"algorithm": profile_sequence.ALGORITHM, "preview_requests_per_user": SEQUENCE_PREVIEW_REQUESTS, "worker_index": 0,
                                 "sha256_by_run_index_and_load": {f"r{r['run_index']:02d}|u{r['load']}": r["profile_sequence_sha256"] for r in runs}}}


# ── ejecución (E/S real; inyectable en pruebas) ─────────────────────────────────────────────────────────────────
def locust_runner(host: str, locustfile: Path, plugin: Path, raw_dir: Path, python: str) -> Callable[[dict, float, float], tuple[list[dict], list[dict]]]:
    def run(r: dict, warmup: float, window: float) -> tuple[list[dict], list[dict]]:
        raw = raw_dir / f"{r['run_id']}.csv"
        env = {**os.environ, "SWARM_LOAD_RAW_CSV": str(raw), "SWARM_LOAD_BATCH_SEED": str(r["seed"]), "SWARM_LOAD_SYSTEM": r["system"], "SWARM_LOAD_WORKER_INDEX": "0"}
        total = int(warmup + window + START_MARGIN_S)
        subprocess.run([python, "-m", "locust", "-f", f"{locustfile},{plugin}", "--headless", "-u", str(r["load"]), "-r", str(r["load"]), "-t", f"{total}s", "--host", host], env=env, check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return http_window.read_raw(raw), http_window.read_cpu(Path(str(raw) + ".cpu.csv"))
    return run


class ServerPerN:
    """Un uvicorn por tamaño de enjambre N (el servidor lee `SWARM_API_N_PARTICLES` al arrancar). El arranque y la parada quedan FUERA de toda ventana de medición."""

    def __init__(self, python: str, port: int, api_key: str, ready_s: float = 90.0):
        self.python, self.port, self.key, self.ready_s, self.proc, self.n = python, port, api_key, ready_s, None, None

    def ensure(self, n: int) -> None:
        if self.n == n and self.proc and self.proc.poll() is None:
            return
        self.stop()
        env = {**os.environ, "SWARM_API_KEY": self.key, "SWARM_API_N_PARTICLES": str(n), "SWARM_API_PERSIST": "0"}        # política de campaña «off», forzada y verificada vía /health
        self.proc = subprocess.Popen([self.python, "-m", "uvicorn", "app.main:app", "--port", str(self.port)], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.n = n
        import urllib.request
        t0 = time.time()
        while time.time() - t0 < self.ready_s:
            try:
                req = urllib.request.Request(f"http://localhost:{self.port}/api/adaptation/health", headers={"X-Swarm-Key": self.key})
                health = json.loads(urllib.request.urlopen(req, timeout=5).read())
            except Exception:
                time.sleep(1.0)
                continue
            if health.get("persist_policy") != "off":                                    # no se asume: se verifica la política EFECTIVA del servidor
                self.stop()
                raise RuntimeError(f"política de persistencia efectiva {health.get('persist_policy')!r} ≠ 'off' (campaña): no se mide")
            return
        self.stop()
        raise RuntimeError(f"el servidor no respondió en {self.ready_s:.0f} s (N={n})")

    def stop(self) -> None:
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
            self.proc.wait(timeout=30)
        self.proc, self.n = None, None


def execute(runs: list[dict], prov: dict, *, warmup: float, window: float, do_run: Callable, ensure_server: Callable[[int], None], log: Callable[[str], None] = print,
            profile_ids: Sequence[str] | None = None) -> list[dict]:
    ids = list(profile_ids) if profile_ids is not None else [p.profile_id for p in read_dataset(DEFAULT_PROFILES)]
    out = []
    for k, r in enumerate(runs, 1):
        ensure_server(r["swarm_N"])
        log(f"[{k}/{len(runs)}] {r['run_id']} seed={r['seed']}")
        raw, cpu = do_run(r, warmup, window)
        summary = http_window.summarize_run(raw, cpu, users=r["load"], system=r["system"], run_id=r["run_id"], warmup_s=warmup, min_window_s=window,
                                         batch_seed=r["seed"], profile_ids=ids)
        out.append(record(r, summary, prov))
        log(f"    {summary['status']}: " + (f"P95 {summary['latency_p95_ms']:.0f} ms · {summary['throughput_rps']:.2f} req/s · error {summary['error_rate']:.2%}" if summary["status"] == "ok" else ""))
    return out


# ── análisis ───────────────────────────────────────────────────────────────────────────────────────────────────
def analyze_oe4(records: Sequence[dict]) -> dict:
    """OE4 sobre la unidad de CORRIDA: carga × N (con interacción) sobre log de métricas positivas; contraste (≤ 25 usuarios) separado del estrés (50/100). El error se analiza en escala natural (puede ser 0)."""
    ok = [r for r in records if r["status"] == "ok" and r["system"] == "swarm"]
    contrast = [r for r in ok if r["load"] <= http_window.CONTRAST_MAX_USERS]
    factors = ("load", "swarm_N")
    metrics = {"t_conv_ms_mean": True, "p95_ms": True, "throughput_http": True, "error_rate": False}
    out: dict = {"experiment": "oe4", "unit": "run", "factors": list(factors), "campaign_spec": campaign_spec.identity(),
                 "runs_per_cell": sorted({sum(1 for x in ok if (x["load"], x["swarm_N"]) == c) for c in {(x["load"], x["swarm_N"]) for x in ok}}) if ok else []}
    for name, subset in (("all_loads_including_stress", ok), ("contrast_regime_le_25", contrast)):
        out[name] = {m: factorial_anova(subset, factors, m, log=lg) for m, lg in metrics.items()}
    from adaptation_swarm.analysis import comparison as cmp
    by_load: dict[int, list[float]] = {}
    for r in ok:
        by_load.setdefault(r["load"], []).append(r["p95_ms"])
    loads = sorted(by_load)
    out["spearman_load_vs_p95"] = cmp.spearman([r["load"] for r in ok], [r["p95_ms"] for r in ok]) if len(ok) >= 3 else {"status": "not_testable"}
    out["p95_by_load_median_ms"] = {str(u): sorted(by_load[u])[len(by_load[u]) // 2] for u in loads}
    out["rnf04"] = {f"u{u}": {"runs": len(v), "runs_meeting_rnf04": sum(bool(r["throughput_http"] is not None and r["throughput_http"] >= http_window.RNF04_RPS and r["error_rate"] < http_window.RNF04_MAX_ERROR)
                                                                      for r in ok if r["load"] == u)} for u, v in ((u, [r for r in ok if r["load"] == u]) for u in loads)}
    return out


def analyze_records(experiment: str, records: Sequence[dict]) -> dict:
    if experiment == "oe4":
        return analyze_oe4(records)
    summaries = [{"status": r["status"], "system": r["system"], "users": r["load"], "latency_p95_ms": r["p95_ms"], "throughput_rps": r["throughput_http"], "run_id": r["run_id"]} for r in records]
    return oe2_confirmatory.analyze([], summaries)


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def write_campaign(out_dir: Path, prov: dict, runs: list[dict], records: list[dict], log_lines: list[str]) -> None:
    out_dir.mkdir(parents=True, exist_ok=False)
    analysis = analyze_records(prov["experiment"], records)
    files = {"plan.json": json.dumps(runs, indent=2, sort_keys=True), "runs.jsonl": "\n".join(json.dumps(r, sort_keys=True, default=str) for r in records) + "\n",
             "provenance.json": json.dumps(prov, indent=2, sort_keys=True, default=str), "analysis.json": json.dumps(analysis, indent=2, sort_keys=True, default=str), "run.log": "\n".join(log_lines) + "\n"}
    for n, t in files.items():
        with (out_dir / n).open("x", encoding="utf-8") as fh:
            fh.write(t)
    with (out_dir / "manifest.json").open("x", encoding="utf-8") as fh:
        fh.write(json.dumps({"schema": SCHEMA, "campaign_id": prov["campaign_id"], "environment_class": prov["environment_class"], "official": prov["official"], "oe2_official": prov["oe2_official"],
                             "files": {n: _sha((out_dir / n).read_bytes()) for n in files}}, indent=2, sort_keys=True))


def describe_plan(prov: dict, runs: list[dict]) -> dict:
    """Resumen verificable de lo que ejecutaría la campaña (lo que imprime el DRY-RUN). No ejecuta nada. Comprueba, sobre el plan, que cada (corrida, carga) tiene LA MISMA secuencia de perfiles para todos los sistemas."""
    roles = prov["systems"]
    by_key: dict[tuple, set] = {}
    for r in runs:
        by_key.setdefault((r["run_index"], r["load"]), set()).add(r["profile_sequence_sha256"])
    d = prov["design"]
    return {"experiment": prov["experiment"], "campaign": "OE2-PREPARATION-NOT-EXECUTED" if prov["experiment"] == "oe2" else "OE4-PREPARATION-NOT-EXECUTED", "official": prov["official"], "oe2_official": prov["oe2_official"],
            "proposal": [s for s, role in roles.items() if role == time_contract.PROPOSAL], "conventional_independent": [s for s, role in roles.items() if role == "conventional_independent"],
            "auxiliary_contrasts": [s for s, role in roles.items() if role in ("swarm_heuristic_ablation", "reference_optimum")],
            "configuration": {"runs_per_cell": d["runs_per_cell"], "n_planned_runs": d["n_planned_runs"], "users": d["users"], "swarm_N": d["particles"] if prov["experiment"] == "oe4" else [PSOParams().n_particles], "warmup_s": d["warmup_s"], "window_s": d["window_s"],
                              "order": d["order"], "base_seed": d["base_seed"], "seed_rule": d["seed_rule"]},
            "profile_sequence": {"algorithm": profile_sequence.ALGORITHM, "same_sequence_for_all_systems": all(len(v) == 1 for v in by_key.values()),
                                 "example_sha256_run00": next((r["profile_sequence_sha256"] for r in runs if r["run_index"] == 0), None)},
            "persist_policy": prov["persist_policy"], "metrics": {"candidate_common_time_metric": time_contract.COMMON_METRIC, "candidate_validation": time_contract.VALIDATION_STATUS, "t_conv_equivalence": time_contract.T_CONV_EQUIVALENCE, "t_conv_ms": "solo la propuesta (T_conv real)", "latency": "P95 HTTP por corrida", "throughput": "HTTP, peticiones correctas/s"},
            "load_conditions": {"contrast_users_le_25": [u for u in d["users"] if u <= http_window.CONTRAST_MAX_USERS], "stress_users_gt_25": [u for u in d["users"] if u > http_window.CONTRAST_MAX_USERS]},
            "provenance_prepared": sorted(k for k in ("campaign_spec", "code", "code_state", "campaign_source_fingerprints", "hardware", "systems", "time_contract", "profile_sequence", "persist_policy", "design") if k in prov),
            "code_state_dirty": prov["code_state"]["dirty"], "official_refusals": prov["official_refusals"]}


def _ints(s: str) -> list[int]:
    return [int(x) for x in s.split(",") if x]


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("experiment", choices=("oe2", "oe4", "analyze"))
    ap.add_argument("--campaign-id")
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--runs", type=int, default=RUNS_PER_CELL_MIN)
    ap.add_argument("--users", type=_ints, default=list(OE4_USERS))
    ap.add_argument("--particles", type=_ints, default=list(OE4_PARTICLES))
    ap.add_argument("--systems", type=lambda s: s.split(","), default=list(DEFAULT_OE2_SYSTEMS), help="OE2: propuesta + convencional independiente (por defecto); rules/bruteforce solo como contrastes auxiliares")
    ap.add_argument("--persist-policy", choices=PERSIST_POLICIES, default="off", help="política de persistencia de la campaña, IGUAL para ambos sistemas (el baseline no persiste: solo «off»)")
    ap.add_argument("--warmup", type=float, default=http_window.WARMUP_S_MIN)
    ap.add_argument("--window", type=float, default=http_window.WINDOW_S_MIN)
    ap.add_argument("--base-seed", type=int, default=DEFAULT_BASE_SEED)
    ap.add_argument("--order", choices=("sequential", "randomized-blocks"), default="randomized-blocks")
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--official", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)
    out_dir = Path(args.out_dir)
    if args.experiment == "analyze":
        recs = [json.loads(l) for l in (out_dir / "runs.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
        prov = json.loads((out_dir / "provenance.json").read_text(encoding="utf-8"))
        print(json.dumps(analyze_records(prov["experiment"], recs), indent=2, sort_keys=True, default=str))
        return
    if not args.campaign_id:
        raise SystemExit("--campaign-id es obligatorio")
    if out_dir.exists():
        raise SystemExit(f"{out_dir} ya existe: no se sobrescribe evidencia")
    runs = plan(args.experiment, runs=args.runs, base_seed=args.base_seed, users=args.users, particles=args.particles, systems=args.systems, order=args.order, campaign_id=args.campaign_id)
    prov = provenance(args, runs)
    if args.official and prov["official_refusals"]:
        raise SystemExit("CAMPAÑA OFICIAL RECHAZADA (no se escribió nada):\n  - " + "\n  - ".join(prov["official_refusals"]))
    if args.dry_run:
        print(f"DRY-RUN OK: {args.experiment}, {len(runs)} corridas ({len({r['cell'] for r in runs})} celdas × {args.runs}); clase {prov['environment_class']}; no se ejecutó nada")
        print(json.dumps(describe_plan(prov, runs), indent=2, sort_keys=True, ensure_ascii=False))
        return
    key = os.environ.get("SWARM_API_KEY")
    if not key:
        raise SystemExit("definir SWARM_API_KEY")
    back = Path(__file__).resolve().parents[2]
    raw_dir = out_dir.with_name(out_dir.name + ".tmp-raw")          # fuera de out_dir: write_campaign exige un directorio NUEVO
    raw_dir.mkdir(parents=True)
    server = ServerPerN(sys.executable, args.port, key)
    lines: list[str] = []

    def log(m: str) -> None:
        lines.append(m)
        print(m, flush=True)
    try:
        records = execute(runs, prov, warmup=args.warmup, window=args.window,
                          do_run=locust_runner(f"http://localhost:{args.port}", back / "loadtest" / "locustfile.py", Path(__file__).with_name("locust_raw_log.py"), raw_dir, sys.executable),
                          ensure_server=server.ensure, log=log)
    finally:
        server.stop()
    write_campaign(out_dir, prov, runs, records, lines)
    raw_dir.rename(out_dir / "raw")
    print(f"escrito: {out_dir} ({len(records)} corridas; clase {prov['environment_class']}; oficial={prov['official']})")


if __name__ == "__main__":
    main()
