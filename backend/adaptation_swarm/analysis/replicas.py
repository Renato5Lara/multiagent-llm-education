"""Ejecutor PURO de réplicas con semillas independientes (respuesta del asesor, 2026-09-25, D5: K = 10). Es un PREPARATIVO: no se ejecuta ninguna corrida oficial
hasta que el asesor apruebe la regla de gold/inclusión (`gold/rubric_v2.APPROVED_RULE_VERSIONS`).

Qué hace: para cada réplica i ∈ [0, K) usa un `batch_seed` propio (derivado de una SEMILLA MAESTRA pre-registrada) con el mismo dataset, la misma biblioteca y la misma
configuración PSO/𝓕, y guarda por caso la configuración final `S`, `𝓕`, `k_stop`, `stop_reason` y la semilla del ciclo. Si el plan trae una regla de evaluación (gold-v2 registrada), guarda además el
F1 POR CASO de cada perfil (`f1`, Dice, P1-bis: predicho vacío ⇒ 0), calculado con esa regla a partir de `S` (la regla se fija en el plan ANTES de ejecutar); sin regla (`--provisional`) no hay F1.
La agregación entre réplicas (R1–R3) vive en `analysis/inference.py` y `analysis/replica_evaluation.py`, no aquí.

ALCANCE (R4, asesor 2026-09-26): esto es el experimento CORE (F1_adapt y convergencia). NO sirve para afirmar RNF-01 (latencia) ni RNF-04 (throughput): eso exige el experimento FULL-STACK, separado y
todavía no ejecutado (`SCOPE`).

Qué NO hace: no usa Redis, PostgreSQL, LLM, audio ni red; no ejerce la pila de agentes ni mide latencia (ver `core_replay`). Las réplicas del núcleo son válidas para el F1
porque el núcleo reproduce exactamente las corridas históricas.

Garantías (comprobadas por `tests/adaptation_swarm/test_replicas_executor.py`): semillas distintas entre sí y de las históricas; salida en un directorio NUEVO (nunca dentro de
resultados congelados, datasets, paquetes de evidencia, ni sobre archivos existentes); `plan.json` antes de ejecutar y `manifest.json` al final con semillas, hashes de cada
réplica, de la biblioteca, del dataset y de los módulos que determinan el resultado; determinismo (misma entrada ⇒ mismos bytes); `run()` NO confía en el plan: `revalidate_plan` lo reconstruye con la misma puerta que `build_plan` (regla gold-v2 registrada y aprobada, K = 10, 100 perfiles) y rechaza cualquier plan manipulado o incompleto antes de crear archivos; la salida está limitada a un directorio nuevo que no esté en resultados congelados, datasets, paquetes de evidencia, `loadtest/results/` ni `adaptation_swarm/`.

    python -m adaptation_swarm.analysis.replicas plan --master-seed N --library-version lib-vN-hash --out-dir NUEVO
    python -m adaptation_swarm.analysis.replicas run  --master-seed N --library-version lib-vN-hash --out-dir NUEVO --gold-rule V --inclusion-rule ID   # oficial (regla aprobada)
    python -m adaptation_swarm.analysis.replicas run  --master-seed N --library-version lib-vN-hash --out-dir NUEVO --provisional [--limit-profiles n]   # exploratorio
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import re
import sys
from pathlib import Path

from adaptation_swarm.analysis.core_replay import replay_cycle
from adaptation_swarm.analysis.inference import PROTOCOL as INFERENCE_PROTOCOL
from adaptation_swarm.config import SETTINGS
from adaptation_swarm.fitness.fitness import FitnessWeights
from adaptation_swarm.gold.f1_multilabel import METRIC_VERSION, case_f1, cases_from_records
from adaptation_swarm.gold.rubric_v2 import (OFFICIAL_AGGREGATION, PANEL_PROTOCOL, PANEL_PROTOCOL_VERSION, EvaluationRule, NoRuleSelected, get_rule,
                                             official_version, panel_protocol_fingerprint, require_approved, status_of)
from adaptation_swarm.multimodal.library import LibraryStore
from adaptation_swarm.profiles.generator import read_dataset
from adaptation_swarm.pso.params import PSOParams
from adaptation_swarm.schemas.ids import derive_seed
from adaptation_swarm.tools import isolated_env as iso

SCHEMA_PLAN = "replicas-plan-v1"
SCHEMA_MANIFEST = "replicas-manifest-v1"
SCHEMA_REPLICA = "replica-v1"
K_OFFICIAL = 10                                             # D5b
N_PROFILES_OFFICIAL = 100
HISTORICAL_BATCH_SEEDS = frozenset({20260923})              # corrida-poc-1/2 y sensibilidad: no se reutiliza
DEFAULT_PROFILES = iso.REPO / "datasets" / "synthetic_profiles" / "profiles-v1.jsonl"
MAX_BATCH_SEED = (1 << 63) - 1                              # cabe en BigInteger con signo (swarm_runs.batch_seed)
# R4: el experimento CORE mide F1_adapt y convergencia; RNF-01/RNF-04 exigen un experimento FULL-STACK separado (no ejecutado aquí). Nunca se mezclan.
SCOPE = {"experiment": "core_replay_k10", "supports": ["F1_adapt", "convergence"], "does_not_support": ["RNF-01", "RNF-04", "L_resp", "throughput"],
         "full_stack_experiment": "separado; no ejecutado por este módulo"}


def derive_batch_seeds(master_seed: int, k: int) -> list[int]:
    """`k` semillas de lote independientes derivadas de la semilla maestra (sha256; 63 bits). Distintas entre sí y de las históricas."""
    if k < 1:
        raise ValueError("k ≥ 1")
    seeds = []
    for i in range(k):
        d = hashlib.sha256(f"replicas-v1|{master_seed}|{i}".encode("utf-8")).digest()
        s = int.from_bytes(d[:8], "big") & MAX_BATCH_SEED
        if s in HISTORICAL_BATCH_SEEDS or s in seeds:
            raise ValueError(f"colisión de semillas con master_seed={master_seed}: elija otra semilla maestra")
        seeds.append(s)
    return seeds


def _sha_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _sha_file(p: Path) -> str:
    return _sha_bytes(p.read_bytes())


def module_fingerprints() -> dict[str, str]:
    """sha256 de los fuentes que determinan el resultado del núcleo (trazabilidad del código que produjo las réplicas)."""
    import adaptation_swarm
    root = Path(adaptation_swarm.__file__).parent
    files = ["pso/engine.py", "pso/params.py", "pso/decode.py", "pso/space.py", "pso/rng.py", "fitness/fitness.py", "fitness/simil.py", "fitness/coher.py",
             "fitness/redund.py", "fitness/costt.py", "profiles/w_mapping.py", "schemas/ids.py", "analysis/core_replay.py", "multimodal/library.py",
             "gold/labels_v2.py", "gold/rubric_v2.py", "gold/f1_multilabel.py", "analysis/inference.py", "analysis/replicas.py"]
    return {f: _sha_file(root / f) for f in files}


def code_version() -> dict:
    """Commit del repositorio leído de `.git` (sin ejecutar git). NO determina si el árbol está limpio: `dirty` es `None` (desconocido, nunca se inventa «limpio»); la trazabilidad del código que produjo las
    réplicas la dan `module_fingerprints`."""
    git = iso.REPO / ".git"
    try:
        head = (git / "HEAD").read_text(encoding="utf-8").strip()
        if not head.startswith("ref: "):
            return {"commit": head, "ref": None, "dirty": None}
        ref = head[5:]
        ref_file = git / ref
        if ref_file.exists():
            return {"commit": ref_file.read_text(encoding="utf-8").strip(), "ref": ref, "dirty": None}
        for line in (git / "packed-refs").read_text(encoding="utf-8").splitlines():
            if line.endswith(" " + ref):
                return {"commit": line.split(" ", 1)[0], "ref": ref, "dirty": None}
    except OSError:
        pass
    return {"commit": None, "ref": None, "dirty": None}


def environment() -> dict:
    """Entorno que produce las réplicas: intérprete y las dependencias numéricas del núcleo (numpy: PCG64/uniform/random del PSO; scipy: inferencia). Un plan creado en otro entorno se rechaza en `revalidate_plan`."""
    import numpy
    import scipy
    return {"python": platform.python_version(), "implementation": platform.python_implementation(), "numpy": numpy.__version__, "scipy": scipy.__version__}


def dataset_identity(profiles_path: Path) -> dict:
    """Versión y manifiesto del dataset, según el archivo hermano `manifest-<versión>.json` de `profiles-<versión>.jsonl`. `None` si el nombre no sigue esa convención (nada se inventa)."""
    m = re.fullmatch(r"profiles-(.+)\.jsonl", Path(profiles_path).name)
    manifest = Path(profiles_path).with_name(f"manifest-{m.group(1)}.json") if m else None
    if manifest is None or not manifest.exists():
        return {"version": None, "manifest_file": None, "manifest_sha256": None}
    return {"version": json.loads(manifest.read_text(encoding="utf-8")).get("dataset_version"), "manifest_file": manifest.name, "manifest_sha256": _sha_file(manifest)}


def _canonical(obj: dict) -> bytes:
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def _gate(*, provisional: bool, k: int, rule: EvaluationRule | None, limit_profiles: int | None) -> str:
    """Una corrida OFICIAL exige regla aprobada, K = 10 y los 100 perfiles; cualquier otra cosa es PROVISIONAL y debe pedirse explícitamente."""
    if provisional:
        return "PROVISIONAL"
    if rule is None:
        raise NoRuleSelected("una corrida oficial exige una regla de evaluación explícita y aprobada")
    require_approved(rule)                                                        # RuleNotApproved si no está aprobada
    if k != K_OFFICIAL:
        raise ValueError(f"una corrida oficial exige K = {K_OFFICIAL} (decisión D5b del asesor), no {k}")
    if limit_profiles is not None:
        raise ValueError("una corrida oficial usa los 100 perfiles: --limit-profiles solo con --provisional")
    return "OFICIAL"


def build_plan(*, master_seed: int, k: int, library_version: str, library_root: Path = None, profiles_path: Path = DEFAULT_PROFILES,
               params: PSOParams = PSOParams(), fw: FitnessWeights = FitnessWeights(), rule: EvaluationRule | None = None,
               provisional: bool = False, limit_profiles: int | None = None) -> dict:
    """Plan de la ejecución (no calcula nada). Aplica la puerta de aprobación."""
    status = _gate(provisional=provisional, k=k, rule=rule, limit_profiles=limit_profiles)
    library_root = Path(library_root or SETTINGS.library_root)
    manifest_file = library_root / library_version / "manifest.json"
    profiles = read_dataset(profiles_path)
    if status == "OFICIAL" and len(profiles) != N_PROFILES_OFFICIAL:
        raise ValueError(f"una corrida oficial usa {N_PROFILES_OFFICIAL} perfiles, el dataset trae {len(profiles)}")
    n_used = len(profiles) if limit_profiles is None else min(limit_profiles, len(profiles))
    seeds = derive_batch_seeds(master_seed, k)
    return {"schema": SCHEMA_PLAN, "status": status, "master_seed": master_seed, "k": k, "batch_seeds": seeds,
            "config": {"pso": params.to_dict(), "fitness_weights": fw.to_dict(), "config_hash": params.config_hash(), "replicate_index": 0},
            "library": {"version": library_version, "manifest_sha256": _sha_file(manifest_file)},
            "dataset": {"file": profiles_path.name, "sha256": _sha_file(profiles_path), "n_profiles": len(profiles), "n_used": n_used, "limited": n_used != len(profiles),
                        **dataset_identity(profiles_path)},
            "rule": None if rule is None else {**rule.to_dict(), "status": status_of(rule), "official_version": official_version(rule),
                                               "gold_fingerprint": rule.gold.fingerprint()},
            "protocol": {"aggregation": OFFICIAL_AGGREGATION, "metric_version": METRIC_VERSION, "panel_protocol_version": PANEL_PROTOCOL_VERSION, "panel": PANEL_PROTOCOL,
                                    "panel_protocol_fingerprint": panel_protocol_fingerprint(), "inference": INFERENCE_PROTOCOL},
            "scope": SCOPE, "code_version": code_version(), "environment": environment(),
            "modules": module_fingerprints(),
            "independence": {"derivation": "sha256('replicas-v1|master|i')[:8] & (2^63-1)", "historical_batch_seeds_excluded": sorted(HISTORICAL_BATCH_SEEDS)}}


def _new_dir(out_dir: Path) -> Path:
    out = Path(out_dir)
    iso.check_new_output_targets([out / "plan.json", out / "manifest.json"])       # no dentro de resultados/datasets/paquetes; nada existente
    out.mkdir(parents=True, exist_ok=False)                                   # un directorio NUEVO: nunca se reutiliza ni sobrescribe
    return out


def _write_new(path: Path, data: bytes) -> None:
    with path.open("xb") as fh:                                               # modo exclusivo: falla si ya existe
        fh.write(data)


def write_plan(plan: dict, out_dir: Path) -> Path:
    out = _new_dir(out_dir)
    _write_new(out / "plan.json", _canonical(plan) + b"\n")
    return out


def revalidate_plan(plan: dict, *, profiles_path: Path = DEFAULT_PROFILES, library_root: Path = None) -> str:
    """Estado (OFICIAL/PROVISIONAL) de un plan tras RECONSTRUIRLO con la misma puerta que `build_plan`. NO confía en ningún campo del plan (`status`, `rule`, `k`,
    `batch_seeds`, `dataset`, `config`…): reconstruye el plan esperado a partir de sus parámetros de entrada y exige que sea idéntico. Así, un plan manipulado o incompleto se rechaza
    (`ValueError`; `RuleNotApproved`/`NoRuleSelected` si declara ser OFICIAL sin regla gold-v2 aprobada) antes de crear cualquier archivo. Una corrida OFICIAL exige regla gold-v2
    aprobada, K = 10 y exactamente los 100 perfiles."""
    if not isinstance(plan, dict) or plan.get("schema") != SCHEMA_PLAN:
        raise ValueError("plan no reconocido")
    try:
        status = plan["status"]
        if status not in ("OFICIAL", "PROVISIONAL"):
            raise ValueError(f"estado de plan no reconocido: {status!r}")
        r, ds = plan["rule"], plan["dataset"]
        rule = None if r is None else get_rule(r["gold"]["rule_version"], r["inclusion"]["rule_id"])         # solo reglas REGISTRADAS
        expected = build_plan(master_seed=plan["master_seed"], k=plan["k"], library_version=plan["library"]["version"], library_root=library_root,
                              profiles_path=profiles_path, params=PSOParams(**plan["config"]["pso"]), fw=FitnessWeights(**plan["config"]["fitness_weights"]),
                              rule=rule, provisional=status == "PROVISIONAL", limit_profiles=ds["n_used"] if ds["limited"] else None)
        if plan["library"]["manifest_sha256"] != expected["library"]["manifest_sha256"]:
            raise ValueError("el manifiesto de la biblioteca cambió respecto del plan")
        if plan["dataset"]["sha256"] != expected["dataset"]["sha256"]:
            raise ValueError("el dataset cambió respecto del plan")
        identical = _canonical(plan) == _canonical(expected)
    except (KeyError, TypeError, AttributeError) as exc:
        raise ValueError(f"plan incompleto o manipulado: {exc!r}") from exc
    if not identical:
        raise ValueError("el plan no coincide con el que se reconstruye a partir de sus parámetros: manipulado o incompleto")
    return expected["status"]


def run(plan: dict, out_dir: Path, *, profiles_path: Path = DEFAULT_PROFILES, library_root: Path = None) -> dict:
    """Ejecuta el plan: K réplicas × perfiles, en proceso. Devuelve el manifiesto (también escrito en `manifest.json`). El estado del manifiesto lo fija
    `revalidate_plan`, no el campo `status` del plan."""
    status = revalidate_plan(plan, profiles_path=profiles_path, library_root=library_root)
    library_root = Path(library_root or SETTINGS.library_root)
    store = LibraryStore.open(library_root, plan["library"]["version"])
    profiles = read_dataset(profiles_path)[: plan["dataset"]["n_used"]]
    params, fw = PSOParams(**plan["config"]["pso"]), FitnessWeights(**plan["config"]["fitness_weights"])
    rp = plan["rule"]
    rule = None if rp is None else get_rule(rp["gold"]["rule_version"], rp["inclusion"]["rule_id"])
    provenance = {"rule_version": None if rp is None else rp["official_version"], "gold_fingerprint": None if rp is None else rp["gold_fingerprint"],
                  "dataset_sha256": plan["dataset"]["sha256"], "library_version": plan["library"]["version"], "library_manifest_sha256": plan["library"]["manifest_sha256"],
                  "code_version": plan["code_version"], "environment": plan["environment"], "config": plan["config"], "protocol": plan["protocol"], "scope": plan["scope"]}
    out = write_plan(plan, out_dir)
    entries = []
    all_case_seeds: list[int] = []
    memo_by_concept: dict[str, dict] = {}                                     # términos de 𝓕 por (concepto, variantes): no dependen de la semilla
    for i, bs in enumerate(plan["batch_seeds"]):
        cases = []
        for p in profiles:
            r = replay_cycle(store, p, params, fw, bs, replicate=plan["config"]["replicate_index"], memo=memo_by_concept.setdefault(p.concept_id, {}))
            cases.append({"profile_id": p.profile_id, "archetype": p.archetype.value if p.archetype else None,
                          "difficulty": p.difficulty.value if p.difficulty else None, "concept_id": p.concept_id, "seed": r["seed"],
                          "S": r["S"], "F": r["F"], "k_stop": r["k"], "stop_reason": r["stop_reason"]})
            all_case_seeds.append(r["seed"])
        if rule is not None:                                                  # F1 por caso (= por perfil en esta réplica) con la regla fijada en el plan
            for c, lab in zip(cases, cases_from_records(cases, rule)):
                c["f1"] = None if lab.gold is None else case_f1(lab.gold, lab.predicted)
        body = _canonical({"schema": SCHEMA_REPLICA, "replica_id": i, "replica_index": i, "batch_seed": bs, "library_version": plan["library"]["version"],
                           "config_hash": plan["config"]["config_hash"], "provenance": provenance, "cases": cases}) + b"\n"
        name = f"replica_{i:02d}.json"
        _write_new(out / name, body)
        entries.append({"index": i, "batch_seed": bs, "file": name, "sha256": _sha_bytes(body), "n_cases": len(cases)})
    if len(set(all_case_seeds)) != len(all_case_seeds):
        raise RuntimeError("semillas de ciclo repetidas entre réplicas: las réplicas no son independientes")
    manifest = {"schema": SCHEMA_MANIFEST, "status": status, "plan_sha256": _sha_file(out / "plan.json"), "master_seed": plan["master_seed"], "k": plan["k"],
                "batch_seeds": plan["batch_seeds"], "replicas": entries, "n_case_seeds": len(all_case_seeds), "n_distinct_case_seeds": len(set(all_case_seeds)),
                "config": plan["config"], "library": plan["library"], "dataset": plan["dataset"], "rule": plan["rule"], "protocol": plan["protocol"], "scope": plan["scope"],
                "code_version": plan["code_version"], "environment": plan["environment"], "modules": plan["modules"]}
    _write_new(out / "manifest.json", _canonical(manifest) + b"\n")
    return manifest


def verify(out_dir: Path) -> list[str]:
    """Problemas de integridad de un directorio de réplicas (lista vacía = íntegro): hashes de cada réplica y del plan frente al manifiesto."""
    out, problems = Path(out_dir), []
    m = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    if _sha_file(out / "plan.json") != m["plan_sha256"]:
        problems.append("plan.json no coincide con el manifiesto")
    for e in m["replicas"]:
        if _sha_file(out / e["file"]) != e["sha256"]:
            problems.append(f"{e['file']}: sha256 distinto del manifiesto")
    if len(set(m["batch_seeds"])) != len(m["batch_seeds"]):
        problems.append("batch_seeds repetidas")
    return problems


def replica_cases(out_dir: Path, index: int) -> list[dict]:
    return json.loads((Path(out_dir) / f"replica_{index:02d}.json").read_text(encoding="utf-8"))["cases"]


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("command", choices=["plan", "run"])
    ap.add_argument("--master-seed", type=int, required=True, help="semilla maestra PRE-REGISTRADA (sin valor por defecto)")
    ap.add_argument("--k", type=int, default=K_OFFICIAL)
    ap.add_argument("--library-version", required=True)
    ap.add_argument("--out-dir", required=True, help="directorio NUEVO (fuera de resultados congelados, datasets y paquetes de evidencia)")
    ap.add_argument("--profiles", default=str(DEFAULT_PROFILES))
    ap.add_argument("--gold-rule"); ap.add_argument("--inclusion-rule")
    ap.add_argument("--provisional", action="store_true"); ap.add_argument("--limit-profiles", type=int)
    a = ap.parse_args(argv)
    rule = get_rule(a.gold_rule, a.inclusion_rule) if (a.gold_rule or a.inclusion_rule) else None
    out = iso.require_out_dir(a.out_dir)
    plan = build_plan(master_seed=a.master_seed, k=a.k, library_version=a.library_version, profiles_path=Path(a.profiles), rule=rule,
                      provisional=a.provisional, limit_profiles=a.limit_profiles)
    if a.command == "plan":
        print(f"plan {plan['status']} escrito en {write_plan(plan, out)}")
        return
    m = run(plan, out, profiles_path=Path(a.profiles))
    print(f"{m['status']}: {m['k']} réplicas × {m['dataset']['n_used']} perfiles en {out}")


if __name__ == "__main__":
    main()
