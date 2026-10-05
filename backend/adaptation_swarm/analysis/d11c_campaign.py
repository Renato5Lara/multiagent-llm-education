"""Campaña D11C-EMPIRICAL-BASELINE: PSO frente a FUERZA BRUTA sobre el mismo espacio, cronometrados con el mismo protocolo (asesor, 25/09, D11c). Capa ADITIVA sobre `baseline_bruteforce` (que no se modifica):
reutiliza SU fuerza bruta, SU PSO (`core_replay.replay_cycle`), SU 𝓕 (`fitness.evaluate` con `FitnessWeights`), SU espacio (`pso.space`, 6.561 configuraciones) y SU derivación de semillas.

IDENTIDAD: `campaign = "D11C-EMPIRICAL-BASELINE"` (constante: ningún argumento la cambia). NO es OE2-OFFICIAL y NO resuelve la contradicción entre el benchmark documental §2.1 y el OE2 estadístico de la tesis
(pregunta abierta D11c: ¿reemplaza o complementa §2.1?). No existe bandera «oficial»: toda salida lleva `official = False` y `oe2_official = False`. Reserva de fidelidad: la transcripción de D11c del 25/09 es del
tesista; falta el texto original del asesor. `rules` y los sistemas de §2.1 (LMS, LLM) quedan FUERA.

TERMINOLOGÍA DE TIEMPOS (esta capa NO produce T_conv):
    T_conv               reservado para la definición oficial existente (AG0: parte tras inicializar el enjambre y pasa por el bus de agentes). D11C NO la mide ni publica `t_conv_ms`.
    pso_search_ms        tiempo de búsqueda del PSO medido por D11C: `core_replay.replay_cycle` completo EN PROCESO. Incluye `compute_weights`, `derive_seed`/RNG, `engine.initialize` y el bucle hasta la parada
                         literal; NO incluye bus, agentes, HTTP ni persistencia. Su punto de inicio NO coincide con el de T_conv de AG0 y no se pretende que coincida. Solo PSO (None en fuerza bruta).
    elapsed_search_ms    tiempo de búsqueda del método: PSO = `pso_search_ms`; fuerza bruta = enumerar las 6.561 configuraciones (W ya calculado FUERA del cronómetro: asimetría declarada, no corregida).
Son tiempos de búsqueda en proceso (NO latencia HTTP / L_resp). Cada tiempo es la MEDIANA de `repeats` repeticiones tras `warmup`, en `cold` (caché de términos de 𝓕 vacía en cada medición) y `warm` (precalculada).

Unidad de ejecución y filas (largas, sin duplicar observaciones):
    fuerza bruta  UNA fila por (perfil, modo): determinista, sin semilla, `F_star` = óptimo global, `n_evaluations` = 6.561.
    pso           una fila por (perfil, réplica, modo): semilla `derive_seed(batch_seed, profile_id, replicate)`, `k_stop`, `n_evaluations` = N·(k+1), `delta_F` = F* − F(g_best) ≥ 0.
ΔF: solo descriptivos (media, mediana, mín, máx, cuota en el óptimo): NO se define ni se aplica prueba inferencial (decisión metodológica pendiente). Los recuentos del resumen son las ejecuciones REALES de cada método.

    python -m adaptation_swarm.analysis.d11c_campaign --library-version lib-vN-hash --campaign-id ID --out-dir NUEVO [--batch-seed S] [--replicates K] [--repeats R] [--limit-profiles n]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import statistics
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from adaptation_swarm.analysis import replicas as _infra
from adaptation_swarm.analysis.baseline_bruteforce import DEFAULT_PROFILES, TOL, _timed, bruteforce_search, claim_conditions, hardware_profile
from adaptation_swarm.analysis.core_replay import precompute_terms, replay_cycle
from adaptation_swarm.config import SETTINGS
from adaptation_swarm.fitness.fitness import FitnessWeights
from adaptation_swarm.multimodal.library import LibraryStore
from adaptation_swarm.oe import definitions as oe_defs
from adaptation_swarm.profiles.generator import read_dataset
from adaptation_swarm.profiles.models import ProfileRequest
from adaptation_swarm.profiles.w_mapping import compute_weights
from adaptation_swarm.pso.params import PSOParams
from adaptation_swarm.pso.space import SPACE_SIZE
from adaptation_swarm.schemas.ids import derive_seed
from adaptation_swarm.tools import isolated_env as iso

CAMPAIGN = "D11C-EMPIRICAL-BASELINE"
SCHEMA = "d11c-campaign-v2"            # v2: sin `t_conv_ms`; `pso_search_ms`/`elapsed_search_ms`; una fila de fuerza bruta por (perfil, modo)
DEFAULT_BATCH_SEED = 26100601
MODES = ("cold", "warm")
FIDELITY_RESERVATION = "D11c transcrito por el tesista (25/09): falta localizar el texto original del asesor"
OPEN_QUESTION = "D11c: ¿la línea base fuerza bruta reemplaza o complementa el benchmark documental §2.1? Sin resolver; esta campaña no la resuelve"
NOT_INCLUDED = ["rules (sin aprobación como línea base oficial)", "LMS tradicional", "LLM monolítico"]
SCOPE = "tiempos de BÚSQUEDA en proceso (no T_conv oficial, no L_resp HTTP); línea base D11c, no evidencia de OE2"
TIME_METRICS = {
    "pso_search_ms": "replay_cycle completo en proceso: incluye compute_weights, derive_seed/RNG, engine.initialize y el bucle hasta la parada; sin bus, agentes, HTTP ni persistencia. NO es T_conv de AG0 (otro punto de inicio).",
    "elapsed_search_ms": "tiempo de búsqueda del método: PSO = pso_search_ms; fuerza bruta = enumeración de las 6.561 configuraciones (W calculado fuera del cronómetro: asimetría declarada)",
    "T_conv": "reservado para la definición oficial existente; D11C no lo produce ni publica `t_conv_ms`",
}
CLAIM_MEANING = ("Condiciones TÉCNICAS de la línea base D11C (hardware, perfiles, repeticiones). NO autorizan OE2, NO aprueban el benchmark §2.1, NO son resultado oficial ni habilitan afirmaciones sobre latencia/carga.")
_FORBIDDEN_IN_CAMPAIGN_ID = re.compile(r"oe2|official|oficial", re.I)
_REPO_MODULES = ("analysis/d11c_campaign.py", "analysis/baseline_bruteforce.py")


def validate_campaign_id(campaign_id: str) -> str:
    """Identificador TÉCNICO de la corrida. No puede contener `OE2`/`official`/`oficial` (insensible a mayúsculas) ni ser una etiqueta congelada; la identidad metodológica es la constante `CAMPAIGN`."""
    iso.check_label(campaign_id)
    if _FORBIDDEN_IN_CAMPAIGN_ID.search(campaign_id):
        raise SystemExit(f"--campaign-id {campaign_id!r} rechazado: no puede sugerir OE2 ni «oficial» (esta campaña es {CAMPAIGN}, NO oficial)")
    return campaign_id


def run_cases(store: LibraryStore, profiles: list[ProfileRequest], params: PSOParams, fw: FitnessWeights, batch_seed: int, *, campaign_id: str, replicates: int = 1,
              repeats: int = 3, warmup: int = 1) -> list[dict]:
    validate_campaign_id(campaign_id)
    rows: list[dict] = []
    for prof in profiles:
        W = compute_weights(prof)
        warm: dict = {}
        precompute_terms(store, prof.concept_id, warm)                     # modo warm: fuera del cronómetro
        for mode in MODES:
            fresh = (lambda: {}) if mode == "cold" else (lambda: warm)
            base = {"campaign": CAMPAIGN, "campaign_id": campaign_id, "official": False, "oe2_official": False, "profile_id": prof.profile_id,
                    "archetype": prof.archetype.value if prof.archetype else None, "timing_mode": mode, "space_size": SPACE_SIZE, "batch_seed": batch_seed}
            t_bf, bf = _timed(lambda: bruteforce_search(store, prof.concept_id, W, fw, memo=fresh()), repeats, warmup)
            rows.append({**base, "run_id": f"{CAMPAIGN}|{campaign_id}|{prof.profile_id}|{mode}|bruteforce", "method": "bruteforce", "replicate": None, "seed": None, "S": bf["S"], "F": bf["F"],
                         "F_star": bf["F"], "delta_F": None, "pso_at_global_optimum": None, "pso_search_ms": None, "elapsed_search_ms": t_bf, "k_stop": None, "stop_reason": None,
                         "n_evaluations": bf["evals"], "n_optimal": bf["n_optimal"]})
            for rep in range(replicates):
                seed = derive_seed(batch_seed, prof.profile_id, rep)
                t_pso, pso = _timed(lambda: replay_cycle(store, prof, params, fw, batch_seed, replicate=rep, memo=fresh()), repeats, warmup)
                delta = bf["F"] - pso["F"]
                rows.append({**base, "run_id": f"{CAMPAIGN}|{campaign_id}|{prof.profile_id}|{mode}|r{rep:02d}|pso", "method": "pso", "replicate": rep, "seed": seed, "S": pso["S"], "F": pso["F"],
                             "F_star": bf["F"], "delta_F": delta, "pso_at_global_optimum": delta <= TOL, "pso_search_ms": t_pso, "elapsed_search_ms": t_pso, "k_stop": pso["k"],
                             "stop_reason": pso["stop_reason"], "n_evaluations": params.n_particles * (pso["k"] + 1)})
    return rows


def _tstats(xs: list[float]) -> dict | None:
    xs = sorted(x for x in xs if x is not None)
    return {"n": len(xs), "median": statistics.median(xs), "mean": statistics.fmean(xs), "min": xs[0], "max": xs[-1]} if xs else None


def describe(rows: list[dict]) -> dict:
    """Estadísticos DESCRIPTIVOS (sin inferencia). El recuento de cada método son sus ejecuciones REALES: fuerza bruta una por (perfil, modo); PSO una por (perfil, réplica, modo)."""
    pso = [r for r in rows if r["method"] == "pso"]
    bf = [r for r in rows if r["method"] == "bruteforce"]
    out: dict = {"campaign": CAMPAIGN, "official": False, "inference": "NO definida: la prueba para ΔF y para los tiempos es una decisión metodológica pendiente", "scope": SCOPE,
                 "n_runs": {"pso": len(pso), "bruteforce": len(bf)}, "n_profiles": len({r["profile_id"] for r in rows}),
                 "reserved_metrics": {"T_conv": "T_conv oficial no es producido por D11C"}}
    d = [r["delta_F"] for r in pso if r["timing_mode"] == MODES[0]]
    if d:
        out["delta_F"] = {"n": len(d), "unit": "(perfil, réplica)", "mean": statistics.fmean(d), "median": statistics.median(d), "min": min(d), "max": max(d),
                          "share_pso_at_global_optimum": sum(x <= TOL for x in d) / len(d), "definition": "F* − F(g_best) ≥ 0"}
    out["elapsed_search_ms"] = {m: {"pso": _tstats([r["elapsed_search_ms"] for r in pso if r["timing_mode"] == m]), "bruteforce": _tstats([r["elapsed_search_ms"] for r in bf if r["timing_mode"] == m])} for m in MODES}
    out["pso_search_ms"] = {m: _tstats([r["pso_search_ms"] for r in pso if r["timing_mode"] == m]) for m in MODES}
    out["k_stop_pso"] = _tstats([r["k_stop"] for r in pso if r["timing_mode"] == MODES[0]])
    return out


def _sha_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def campaign_module_fingerprints() -> dict[str, str]:
    """sha256 de los fuentes que producen ESTA campaña (los de `module_fingerprints()` v2 no incluyen ni este módulo ni `baseline_bruteforce`)."""
    root = Path(__file__).resolve().parents[1]
    return {m: _sha_file(root / m) for m in _REPO_MODULES}


def git_state(repo: Path | None = None) -> dict:
    """Estado REAL del árbol (`git status --porcelain`): `dirty` True/False, o None si git no está disponible (desconocido; nunca se supone «limpio»)."""
    try:
        res = subprocess.run(["git", "status", "--porcelain"], cwd=str(repo or iso.REPO), capture_output=True, text=True, timeout=30, check=True)
    except (OSError, subprocess.SubprocessError):
        return {"dirty": None, "method": "git status --porcelain", "modified_paths": None, "note": "git no disponible: estado desconocido"}
    paths = [l[3:] for l in res.stdout.splitlines() if l.strip()]
    return {"dirty": bool(paths), "method": "git status --porcelain", "n_modified_or_untracked": len(paths), "modified_paths": paths[:50]}


def d11c_conditions(hw: dict, n_profiles: int, repeats: int) -> dict:
    """`claim_conditions` de la línea base, renombradas: condiciones TÉCNICAS de D11C, no una autorización."""
    c = claim_conditions(hw, n_profiles, repeats)
    met = bool(c["claim_allowed"])
    return {"conditions": c["conditions"], "d11c_technical_conditions_met": met, "meaning": CLAIM_MEANING,
            "not_authorization_of": ["OE2", "benchmark §2.1", "resultado oficial", "afirmación de reducción de latencia o de carga"],
            "verdict": ("Se cumplen las condiciones técnicas de la línea base D11C. " + CLAIM_MEANING) if met else c["verdict"]}


def provenance(store: LibraryStore, profiles_path: Path, profiles: list[ProfileRequest], params: PSOParams, fw: FitnessWeights, *, campaign_id: str, batch_seed: int, replicates: int, repeats: int,
               warmup: int, hardware: dict | None = None) -> dict:
    validate_campaign_id(campaign_id)
    hw = hardware or hardware_profile()
    return {"schema": SCHEMA, "campaign": CAMPAIGN, "campaign_id": campaign_id, "official": False, "oe2_official": False, "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "code": _infra.code_version(), "code_state": git_state(), "environment": _infra.environment(), "hardware": hw, "library_version": store.version,
            "dataset": {**_infra.dataset_identity(profiles_path), "file": Path(profiles_path).name, "n_profiles": len(profiles)},
            "design": {"batch_seed": batch_seed, "replicates": replicates, "repeats": repeats, "warmup": warmup, "modes": list(MODES), "space_size": SPACE_SIZE,
                       "seed_rule": "derive_seed(batch_seed, profile_id, replicate)", "bruteforce_seed": None, "rows": "bruteforce: una por (perfil, modo); pso: una por (perfil, réplica, modo)"},
            "objective": {"function": "adaptation_swarm.fitness.fitness.evaluate", "weights": fw.to_dict(), "W": "profiles.w_mapping.compute_weights (el mismo para ambos métodos)"},
            "pso": {**params.to_dict(), "config_hash": params.config_hash()},
            "definitions": {"t_conv": oe_defs.DEFINITIONS["t_conv"], "conventional_system_oe2": oe_defs.DEFINITIONS["conventional_system_oe2"], "f1_selected": oe_defs.f1_selection_record(None)},
            "time_metrics": TIME_METRICS, "d11c_conditions": d11c_conditions(hw, len(profiles), repeats),
            "module_fingerprints": _infra.module_fingerprints(), "campaign_module_fingerprints": campaign_module_fingerprints(),
            "fidelity_reservation": FIDELITY_RESERVATION, "open_question": OPEN_QUESTION, "not_included": NOT_INCLUDED, "scope": SCOPE}


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def write_campaign(out_dir: Path, prov: dict, rows: list[dict]) -> Path:
    if prov.get("campaign") != CAMPAIGN or prov.get("official") is not False or prov.get("oe2_official") is not False:
        raise ValueError("la provenance no corresponde a D11C-EMPIRICAL-BASELINE no oficial")
    if any(r.get("campaign") != CAMPAIGN or r.get("official") is not False or "t_conv_ms" in r for r in rows):
        raise ValueError("filas incompatibles con D11C (identidad, bandera oficial o `t_conv_ms`)")
    out = Path(out_dir)
    iso.check_new_output_targets([out])
    out.mkdir(parents=True, exist_ok=False)
    files = {"d11c_runs.jsonl": "\n".join(json.dumps(r, sort_keys=True) for r in rows) + "\n", "provenance.json": json.dumps(prov, indent=2, sort_keys=True, default=str),
             "summary.json": json.dumps(describe(rows), indent=2, sort_keys=True)}
    for n, t in files.items():
        with (out / n).open("x", encoding="utf-8") as fh:
            fh.write(t)
    with (out / "manifest.json").open("x", encoding="utf-8") as fh:
        fh.write(json.dumps({"schema": SCHEMA, "campaign": CAMPAIGN, "official": False, "files": {n: _sha((out / n).read_bytes()) for n in files}}, indent=2, sort_keys=True))
    return out


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--library-version", required=True)
    ap.add_argument("--campaign-id", required=True, help="identificador TÉCNICO de la corrida (no puede sugerir OE2 ni «oficial»)")
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--profiles", type=Path, default=DEFAULT_PROFILES)
    ap.add_argument("--batch-seed", type=int, default=DEFAULT_BATCH_SEED)
    ap.add_argument("--replicates", type=int, default=1)
    ap.add_argument("--repeats", type=int, default=3)
    ap.add_argument("--warmup", type=int, default=1)
    ap.add_argument("--limit-profiles", type=int)
    a = ap.parse_args(argv)
    out = iso.require_out_dir(a.out_dir)
    validate_campaign_id(a.campaign_id)
    iso.check_new_output_targets([out])
    store = LibraryStore.open(SETTINGS.library_root, a.library_version)
    profiles = read_dataset(a.profiles)
    profiles = profiles[: a.limit_profiles] if a.limit_profiles else profiles
    params, fw = PSOParams(), FitnessWeights()
    rows = run_cases(store, profiles, params, fw, a.batch_seed, campaign_id=a.campaign_id, replicates=a.replicates, repeats=a.repeats, warmup=a.warmup)
    prov = provenance(store, a.profiles, profiles, params, fw, campaign_id=a.campaign_id, batch_seed=a.batch_seed, replicates=a.replicates, repeats=a.repeats, warmup=a.warmup)
    path = write_campaign(out, prov, rows)
    print(json.dumps(describe(rows), indent=2, sort_keys=True))
    print(f"{CAMPAIGN} (NO OFICIAL, no es OE2): {path}")


if __name__ == "__main__":
    main()
