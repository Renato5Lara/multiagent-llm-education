"""Verificación PURA de equivalencia de entorno (no ejecuta K=10 ni réplicas oficiales). Imprime un JSON determinista. Se ejecuta igual en Python 3.12 (contenedor) y 3.14 (host)."""
import hashlib, importlib, json, sys, csv
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))
import numpy as np, scipy
out = {"env": {"python": sys.version.split()[0], "numpy": np.__version__, "scipy": scipy.__version__}}

# 1. imports
mods = ["adaptation_swarm.pso.engine", "adaptation_swarm.pso.rng", "adaptation_swarm.pso.space", "adaptation_swarm.pso.params", "adaptation_swarm.pso.decode", "adaptation_swarm.fitness.fitness",
        "adaptation_swarm.fitness.simil", "adaptation_swarm.fitness.coher", "adaptation_swarm.fitness.redund", "adaptation_swarm.fitness.costt", "adaptation_swarm.analysis.core_replay",
        "adaptation_swarm.analysis.replicas", "adaptation_swarm.analysis.inference", "adaptation_swarm.analysis.replica_evaluation", "adaptation_swarm.analysis.preregistration",
        "adaptation_swarm.multimodal.library", "adaptation_swarm.profiles.generator", "adaptation_swarm.profiles.w_mapping", "adaptation_swarm.gold.rubric_v2", "adaptation_swarm.gold.f1_multilabel",
        "adaptation_swarm.metrics.gold_panel", "adaptation_swarm.metrics.convergence", "adaptation_swarm.schemas.ids"]
res = {}
for m in mods:
    try: importlib.import_module(m); res[m] = "ok"
    except Exception as e: res[m] = f"ERROR {type(e).__name__}: {e}"
out["imports"] = res

from adaptation_swarm.analysis import replicas as rp
from adaptation_swarm.schemas.ids import derive_seed
from adaptation_swarm.pso.rng import make_rng
# 2. semillas de lote (26092601)
out["batch_seeds_26092601"] = rp.derive_batch_seeds(26092601, 10)
# 3. RNG: huella de flujos PCG64 (uniform y random, como el PSO) para las 10 semillas de lote y 3 semillas de ciclo
def rng_fingerprint(seed):
    r = make_rng(seed); u = r.uniform(0.0, 2.0, size=(20, 8)); a = r.random((20, 8)); b = r.random((20, 8))
    return hashlib.sha256(u.tobytes() + a.tobytes() + b.tobytes()).hexdigest()[:24]
out["rng"] = {str(s): rng_fingerprint(s) for s in out["batch_seeds_26092601"]}
out["rng_first_values"] = {str(out["batch_seeds_26092601"][0]): [float(x) for x in make_rng(out["batch_seeds_26092601"][0]).random(3)]}
from adaptation_swarm.profiles.generator import read_dataset
P = read_dataset(rp.DEFAULT_PROFILES)
out["cycle_seed_sample"] = {p.profile_id: derive_seed(out["batch_seeds_26092601"][0], p.profile_id, 0) for p in P[:3]}
out["rng_cycle"] = {p.profile_id: rng_fingerprint(derive_seed(out["batch_seeds_26092601"][0], p.profile_id, 0)) for p in P[:3]}
# 4. biblioteca y dataset (identidad; sin resultados)
from adaptation_swarm.multimodal.library import LibraryStore
from adaptation_swarm.config import SETTINGS
st = LibraryStore.open(SETTINGS.library_root, "lib-v10-5dd83cd4")
out["library_v10"] = {"version": st.version, "manifest_sha256": hashlib.sha256((Path(SETTINGS.library_root) / st.version / "manifest.json").read_bytes()).hexdigest(), "concepts": len(st.concepts())}
out["dataset"] = rp.dataset_identity(rp.DEFAULT_PROFILES) | {"sha256": hashlib.sha256(rp.DEFAULT_PROFILES.read_bytes()).hexdigest(), "n": len(P)}
# 5. plan PROVISIONAL (solo campos; no ejecuta nada) y su huella sin el entorno
plan = rp.build_plan(master_seed=26092601, k=10, library_version="lib-v10-5dd83cd4", provisional=True)
core = {k: v for k, v in plan.items() if k not in ("environment", "code_version")}
out["plan"] = {"environment": plan["environment"], "sha256_sin_entorno_ni_codigo": hashlib.sha256(rp._canonical(core)).hexdigest(), "batch_seeds_ok": plan["batch_seeds"] == out["batch_seeds_26092601"]}
# 6. pre-registro sin deriva
from adaptation_swarm.analysis import preregistration as pr
out["preregistration_drift"] = pr.verify_preregistration(pr.DEFAULT_PATH, deep=False)
# 7. replay CONTROLADO de casos históricos (subconjunto pequeño; NO la corrida completa; NO se escribe nada)
import numpy as np
from adaptation_swarm.analysis.core_replay import replay_cycle
from adaptation_swarm.fitness.fitness import FitnessWeights
from adaptation_swarm.pso.params import PSOParams
EXP = Path("experiments/results"); PKG = Path("experiments/evidence_package_2026-09-24-final/02_corridas_y_auditorias")
byid = {p.profile_id: p for p in P}
replay = {}
for label, picks in (("corrida-poc-1", [0, 13, 27, 41, 55, 69, 83, 99]), ("corrida-poc-2", [5, 30, 62, 91])):
    run = json.load(open(EXP / f"adaptation_swarm_{label}.json", encoding="utf-8")); cfg = run["config"]
    seeds = {r["profile_id"]: int(r["seed"]) for r in csv.DictReader(open(PKG / f"db_{label}_cycles.csv", encoding="utf-8"))}
    lib = LibraryStore.open(SETTINGS.library_root, cfg["library_version"]); params = PSOParams(**cfg["pso"]); fw = FitnessWeights(**cfg["fitness_weights"])
    rows, memo = [], {}
    for i in picks:
        c = run["cases"][i]; p = byid[c["profile_id"]]
        r = replay_cycle(lib, p, params, fw, cfg["batch_seed"], replicate=0, memo=memo.setdefault(p.concept_id, {}))
        rows.append({"i": i, "profile_id": c["profile_id"], "seed_ok": r["seed"] == seeds[c["profile_id"]], "S_ok": list(r["S"]) == list(c["g_best_S"]), "F_ok": abs(r["F"] - c["g_best_F"]) < 1e-12,
                     "F_bytes": repr(float(r["F"])), "F_historico": repr(float(c["g_best_F"])), "k_ok": r["k"] == c["k_stop"], "stop_ok": r["stop_reason"] == c["stop_reason"],
                     "S": list(map(int, r["S"])), "k": r["k"], "stop": r["stop_reason"], "seed": r["seed"]})
    replay[label] = {"library": cfg["library_version"], "n": len(rows), "todos_coinciden": all(all(v for k, v in x.items() if k.endswith("_ok")) for x in rows), "casos": rows}
out["replay"] = replay
print(json.dumps(out, sort_keys=True, ensure_ascii=False, indent=1))
