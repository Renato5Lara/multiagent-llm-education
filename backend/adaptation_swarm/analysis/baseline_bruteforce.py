"""Línea base empírica: PSO frente a FUERZA BRUTA sobre el mismo espacio (respuesta del asesor, 2026-09-25, D11c).

Para cada perfil, con la MISMA biblioteca, el MISMO 𝓕 (pesos, términos y `W`) y el MISMO espacio de 6.561 configuraciones, se cronometran y comparan:
    · PSO: `core_replay.replay_cycle` (semilla → 𝓕 → parada literal);
    · fuerza bruta: enumeración exhaustiva de todas las configuraciones (óptimo global);
y se reporta: tiempo de BÚSQUEDA, nº de evaluaciones de 𝓕, solución elegida y brecha de 𝓕 (F_bruta − F_PSO ≥ 0).

Dos modos de tiempo, ambos declarados:
    · "cold": la caché de términos de 𝓕 (Coher/Redund/CostT por combinación de variantes) parte vacía en cada medición (cuenta calcularlos); la lectura de archivos de la
      biblioteca sí está en caché del store, igual para ambos métodos;
    · "warm": esa caché está precalculada (las 81 combinaciones); mide solo evaluar 𝓕 y recorrer el espacio.
Cada medición es la MEDIANA de `repeats` repeticiones tras `warmup`; las repeticiones son en proceso, un método tras otro, en el mismo interpretador.

ALCANCE Y CAUTELAS (obligatorias en el informe):
    · Mide tiempo de búsqueda en proceso, NO `L_resp` (no incluye bus, agentes, HTTP ni persistencia).
    · NO se afirma reducción de latencia ni de carga salvo que se cumplan TODAS las condiciones de `claim_conditions` (hardware cercano al objetivo, dataset completo,
      repeticiones suficientes). En cualquier otro caso el informe dice «NO CONCLUYENTE» y explica por qué. Una medición local exploratoria no autoriza la afirmación.
    · «Cercano a 8 vCPU / 32 GB» es una definición OPERATIVA por confirmar (addendum P6): aquí, ≥ 8 vCPU y ≥ 90 % de la RAM objetivo.

    python -m adaptation_swarm.analysis.baseline_bruteforce --library-version lib-vN-hash --batch-seed N --out-dir NUEVO [--repeats 5] [--limit-profiles n]
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import statistics
import time
from pathlib import Path

import numpy as np

from adaptation_swarm.analysis.core_replay import Terms, precompute_terms, replay_cycle, variant_terms
from adaptation_swarm.config import SETTINGS
from adaptation_swarm.fitness.fitness import FitnessWeights, evaluate
from adaptation_swarm.multimodal.library import LibraryStore
from adaptation_swarm.profiles.generator import read_dataset
from adaptation_swarm.profiles.models import ProfileRequest
from adaptation_swarm.profiles.w_mapping import compute_weights
from adaptation_swarm.pso.params import PSOParams
from adaptation_swarm.pso.space import SPACE_SIZE, all_configurations
from adaptation_swarm.tools import isolated_env as iso

REPORT_VERSION = "baseline-bruteforce-v1"
TARGET_HARDWARE = {"vcpu": 8, "ram_gib": 32.0}
TARGET_RAM_FRACTION = 0.9            # «cercano» (definición operativa por confirmar, addendum P6)
MIN_REPEATS_FOR_CLAIM = 5
N_PROFILES_FOR_CLAIM = 100
DEFAULT_PROFILES = iso.REPO / "datasets" / "synthetic_profiles" / "profiles-v1.jsonl"
TOL = 1e-12


def hardware_profile() -> dict:
    """Hardware y software del proceso (solo lectura de /proc; sin ejecutar comandos)."""
    model, mem_gib = None, None
    try:
        for line in Path("/proc/cpuinfo").read_text().splitlines():
            if line.startswith("model name"):
                model = line.split(":", 1)[1].strip()
                break
        for line in Path("/proc/meminfo").read_text().splitlines():
            if line.startswith("MemTotal:"):
                mem_gib = round(int(line.split()[1]) / (1024 ** 2), 2)
                break
    except OSError:
        pass
    return {"vcpu": os.cpu_count(), "cpu_model": model, "ram_gib": mem_gib, "python": platform.python_version(), "numpy": np.__version__,
            "platform": platform.platform()}


def meets_target(hw: dict, target: dict = TARGET_HARDWARE, ram_fraction: float = TARGET_RAM_FRACTION) -> bool:
    return bool(hw.get("vcpu") and hw["vcpu"] >= target["vcpu"] and hw.get("ram_gib") and hw["ram_gib"] >= ram_fraction * target["ram_gib"])


def bruteforce_search(store: LibraryStore, concept_id: str, W, fw: FitnessWeights, *, memo: dict[tuple[int, ...], Terms]) -> dict:
    """Óptimo global por enumeración exhaustiva. Misma semántica que `metrics.search_quality.brute_force_optimum` (primer máximo; empates con tolerancia 1e-12)."""
    wm = W.by_modality()
    best_F, best_S, n_best, n = float("-inf"), (), 0, 0
    for cfg in all_configurations():
        f = evaluate(cfg, wm, *variant_terms(store, concept_id, cfg.variants, memo), fw).F
        n += 1
        if f > best_F + TOL:
            best_F, best_S, n_best = f, cfg.vector, 1
        elif abs(f - best_F) <= TOL:
            n_best += 1
    return {"S": list(best_S), "F": best_F, "n_optimal": n_best, "evals": n}


def _timed(fn, repeats: int, warmup: int):
    for _ in range(warmup):
        fn()
    times, out = [], None
    for _ in range(repeats):
        t0 = time.perf_counter_ns()
        out = fn()
        times.append((time.perf_counter_ns() - t0) / 1e6)
    return statistics.median(times), out


def compare_profile(store: LibraryStore, prof: ProfileRequest, params: PSOParams, fw: FitnessWeights, batch_seed: int, *, repeats: int, warmup: int) -> dict:
    W = compute_weights(prof)
    warm: dict = {}
    precompute_terms(store, prof.concept_id, warm)                         # modo warm: términos ya calculados (fuera del cronómetro)
    res: dict = {}
    for mode in ("cold", "warm"):
        fresh = (lambda: {}) if mode == "cold" else (lambda: warm)
        t_pso, r_pso = _timed(lambda: replay_cycle(store, prof, params, fw, batch_seed, memo=fresh()), repeats, warmup)
        t_bf, r_bf = _timed(lambda: bruteforce_search(store, prof.concept_id, W, fw, memo=fresh()), repeats, warmup)
        res[mode] = {"pso_ms": t_pso, "bruteforce_ms": t_bf, "ratio_bruteforce_over_pso": (t_bf / t_pso) if t_pso > 0 else None}
        res["_pso"], res["_bf"] = r_pso, r_bf
    pso, bf = res.pop("_pso"), res.pop("_bf")
    gap = bf["F"] - pso["F"]
    return {"profile_id": prof.profile_id, "archetype": prof.archetype.value if prof.archetype else None,
            "pso": {"S": pso["S"], "F": pso["F"], "k_stop": pso["k"], "stop_reason": pso["stop_reason"], "evals": params.n_particles * (pso["k"] + 1)},
            "bruteforce": {"S": bf["S"], "F": bf["F"], "n_optimal": bf["n_optimal"], "evals": bf["evals"]},
            "gap_F": gap, "pso_at_global_optimum": gap <= TOL, "same_S": pso["S"] == bf["S"], "timing_ms": res}


def _stats(xs: list[float]) -> dict:
    s = sorted(xs)
    return {"n": len(s), "median": statistics.median(s), "mean": statistics.fmean(s), "p95": s[min(len(s) - 1, int(0.95 * len(s)))], "max": s[-1]}


def claim_conditions(hw: dict, n_profiles: int, repeats: int) -> dict:
    conds = {"hardware_cercano_al_objetivo": meets_target(hw), "dataset_completo": n_profiles >= N_PROFILES_FOR_CLAIM, "repeticiones_suficientes": repeats >= MIN_REPEATS_FOR_CLAIM}
    reasons = []
    if not conds["hardware_cercano_al_objetivo"]:
        reasons.append(f"el hardware medido ({hw.get('vcpu')} vCPU, {hw.get('ram_gib')} GiB) no es cercano al objetivo ({TARGET_HARDWARE['vcpu']} vCPU / {TARGET_HARDWARE['ram_gib']:.0f} GB)")
    if not conds["dataset_completo"]:
        reasons.append(f"solo {n_profiles} perfiles (se exigen {N_PROFILES_FOR_CLAIM})")
    if not conds["repeticiones_suficientes"]:
        reasons.append(f"solo {repeats} repeticiones (se exigen ≥ {MIN_REPEATS_FOR_CLAIM})")
    allowed = all(conds.values())
    return {"conditions": conds, "claim_allowed": allowed,
            "verdict": ("Medición en condiciones válidas: puede compararse el tiempo de BÚSQUEDA de ambos métodos (no equivale a L_resp)." if allowed
                        else "NO CONCLUYENTE: " + "; ".join(reasons) + ". No se afirma reducción de latencia ni de carga.")}


def run_baseline(store: LibraryStore, profiles: list[ProfileRequest], params: PSOParams, fw: FitnessWeights, batch_seed: int, *, repeats: int = 5,
                 warmup: int = 1, hardware: dict | None = None) -> dict:
    rows = [compare_profile(store, p, params, fw, batch_seed, repeats=repeats, warmup=warmup) for p in profiles]
    hw = hardware or hardware_profile()
    summ = {mode: {m: _stats([r["timing_ms"][mode][m] for r in rows]) for m in ("pso_ms", "bruteforce_ms")} for mode in ("cold", "warm")}
    for mode in ("cold", "warm"):
        summ[mode]["ratio_of_medians_bruteforce_over_pso"] = summ[mode]["bruteforce_ms"]["median"] / summ[mode]["pso_ms"]["median"] if summ[mode]["pso_ms"]["median"] > 0 else None
    return {"report_version": REPORT_VERSION, "library_version": store.version, "batch_seed": batch_seed, "pso": params.to_dict(), "fitness_weights": fw.to_dict(),
            "space_size": SPACE_SIZE, "n_profiles": len(rows), "repeats": repeats, "warmup": warmup, "hardware": hw, "target_hardware": TARGET_HARDWARE,
            "claim": claim_conditions(hw, len(rows), repeats),
            "search_quality": {"mean_gap_F": statistics.fmean(r["gap_F"] for r in rows), "max_gap_F": max(r["gap_F"] for r in rows),
                               "share_pso_at_global_optimum": sum(r["pso_at_global_optimum"] for r in rows) / len(rows),
                               "min_gap_F": min(r["gap_F"] for r in rows), "mean_evals_pso": statistics.fmean(r["pso"]["evals"] for r in rows), "evals_bruteforce": SPACE_SIZE},
            "timing_summary_ms": summ, "cases": rows}


def to_markdown(rep: dict) -> str:
    c, q, t = rep["claim"], rep["search_quality"], rep["timing_summary_ms"]
    L = [f"# Línea base: PSO frente a fuerza bruta ({rep['library_version']})", "",
         f"**{c['verdict']}**", "",
         f"Perfiles: {rep['n_profiles']} · repeticiones: {rep['repeats']} (mediana) · hardware: {rep['hardware']['vcpu']} vCPU, {rep['hardware']['ram_gib']} GiB, {rep['hardware']['cpu_model']}",
         f"Espacio: {rep['space_size']} configuraciones · evaluaciones de 𝓕: PSO ≈ {q['mean_evals_pso']:.0f} por perfil, fuerza bruta {q['evals_bruteforce']}", "",
         "| modo | PSO mediana (ms) | fuerza bruta mediana (ms) | razón de medianas (bruta/PSO) |", "|---|---|---|---|"]
    for mode in ("cold", "warm"):
        L.append(f"| {mode} | {t[mode]['pso_ms']['median']:.3f} | {t[mode]['bruteforce_ms']['median']:.3f} | {t[mode]['ratio_of_medians_bruteforce_over_pso']:.1f} |")
    L += ["", f"Brecha de 𝓕 (F_bruta − F_PSO): media {q['mean_gap_F']:.5f}, máx {q['max_gap_F']:.5f}; el PSO alcanza el óptimo global en {100*q['share_pso_at_global_optimum']:.0f} % de los perfiles.",
          "", "Mide tiempo de BÚSQUEDA en proceso, no `L_resp`. «cold» incluye calcular los términos de 𝓕; «warm» los tiene precalculados.", ""]
    return "\n".join(L)


def write_report(rep: dict, out_dir: Path) -> Path:
    out = Path(out_dir)
    iso.check_new_output_targets([out / "baseline.json", out / "baseline.md"])
    out.mkdir(parents=True, exist_ok=False)
    for name, data in (("baseline.json", json.dumps(rep, indent=1, sort_keys=True, ensure_ascii=False)), ("baseline.md", to_markdown(rep))):
        with (out / name).open("x", encoding="utf-8") as fh:
            fh.write(data)
    return out


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--library-version", required=True); ap.add_argument("--batch-seed", type=int, required=True)
    ap.add_argument("--out-dir", required=True, help="directorio NUEVO (fuera de resultados congelados, datasets y paquetes de evidencia)")
    ap.add_argument("--profiles", default=str(DEFAULT_PROFILES)); ap.add_argument("--repeats", type=int, default=5); ap.add_argument("--limit-profiles", type=int)
    a = ap.parse_args(argv)
    out = iso.require_out_dir(a.out_dir)
    iso.check_new_output_targets([out / "baseline.json", out / "baseline.md"])           # falla ANTES de medir si el destino no es válido
    store = LibraryStore.open(SETTINGS.library_root, a.library_version)
    profiles = read_dataset(Path(a.profiles))
    profiles = profiles[: a.limit_profiles] if a.limit_profiles else profiles
    rep = run_baseline(store, profiles, PSOParams(), FitnessWeights(), a.batch_seed, repeats=a.repeats)
    print(to_markdown(rep)); print(f"informe en {write_report(rep, out)}")


if __name__ == "__main__":
    main()
