"""Ejecutor de réplicas de K = 10 v3 (capa ADITIVA sobre `analysis/replicas.py`, que es código sellado de K = 10 v2 y NO se modifica). Es un PREPARATIVO: no se ejecuta ninguna corrida oficial v3.

Qué hace: lo mismo que el ejecutor v2 —K réplicas con `batch_seed` derivados de la semilla maestra, mismo dataset, misma biblioteca y misma configuración PSO/𝓕— pero evaluando con la regla v3
(`gold/rubric_v3`: P1 inclusión relativa y P2 gold) y dejando identificada la regla estadística v3 (`analysis/statistical_rule_v3`). REUTILIZA, sin modificarlas, las piezas puras de v2: `derive_batch_seeds`
(la misma derivación de semillas, de modo que K = 10 v3 es comparable con v2 y NO abre una trayectoria estocástica nueva), `replay_cycle` (el núcleo PSO+𝓕), `dataset_identity`, `environment`, `code_version` y
`module_fingerprints` (las 19 huellas de v2, que aquí solo se REGISTRAN; este módulo y las piezas v3 se huellan aparte en `modules_v3`).

PUERTA DE APROBACIÓN: `official=True` exige que la regla esté aprobada en el registro de `rubric_v3` (`APPROVED_RULE_VERSIONS`, hoy VACÍO: se registra con el sellado del pre-registro v3), K = 10, los 100 perfiles, la semilla
maestra de K = 10 (`K10_MASTER_SEED`, la misma de v2: cambiarla sería «seed fishing») y una versión completa de la regla EXPLÍCITA (`full_rule_version`), que este módulo no inventa: la fija el pre-registro v3 (gold + inclusión +
agregación + protocolo del panel). Mientras no esté aprobada la regla, la ejecución oficial queda BLOQUEADA (`RuleNotApproved`); lo demás es PROVISIONAL y debe pedirse explícitamente.

SALIDAS: siempre en un directorio NUEVO, nunca dentro de los resultados/análisis/pre-registro de K = 10 v2 ni de los sitios protegidos de la infraestructura v2; una corrida oficial v3 solo puede escribir bajo
`official_runs/k10_v3/`. `plan.json`, cada `replica_XX.json` y `manifest.json` son deterministas (misma entrada ⇒ mismos bytes); la marca de tiempo va aparte, en `execution_metadata.json`.

ALCANCE: experimento CORE (F1_adapt y convergencia), igual que v2 (`SCOPE`): no sirve para RNF-01/RNF-04. La evaluación (IC95, prueba por perfil, criterio RNF-03) es una pieza posterior (`evaluation_v3`).
No implementa línea de comandos: la ejecución formal se hará cuando exista el pre-registro v3.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import adaptation_swarm
from adaptation_swarm.analysis import replicas as _v2_infra                     # solo utilidades PURAS y constantes (no se modifica ni se usa su puerta de aprobación)
from adaptation_swarm.analysis import statistical_rule_v3
from adaptation_swarm.analysis.core_replay import replay_cycle
from adaptation_swarm.analysis.inference import PROTOCOL as INFERENCE_PROTOCOL
from adaptation_swarm.config import SETTINGS
from adaptation_swarm.fitness.fitness import FitnessWeights
from adaptation_swarm.gold import rubric_v3
from adaptation_swarm.gold.f1_multilabel import METRIC_VERSION, OFFICIAL_AGGREGATION, case_f1, cases_from_records
from adaptation_swarm.multimodal.library import LibraryStore
from adaptation_swarm.profiles.generator import read_dataset
from adaptation_swarm.pso.params import PSOParams
from adaptation_swarm.tools import isolated_env as iso

SCHEMA_PLAN = "replicas-plan-v3"
SCHEMA_MANIFEST = "replicas-manifest-v3"
SCHEMA_REPLICA = "replica-v3"
K_OFFICIAL = _v2_infra.K_OFFICIAL                          # D5b: K = 10
N_PROFILES_OFFICIAL = _v2_infra.N_PROFILES_OFFICIAL
K10_MASTER_SEED = 26092601                                 # la misma semilla maestra de K = 10 v2 (asesor, 28/09, opción C: se conservan semillas)
DEFAULT_PROFILES = _v2_infra.DEFAULT_PROFILES
SCOPE = _v2_infra.SCOPE

V3_OUTPUT_ROOT = iso.BACK / "official_runs" / "k10_v3"      # única raíz permitida para una corrida OFICIAL v3
_V2_FROZEN_DIRS = (iso.BACK / "official_runs" / "k10_official_2026-09-27", iso.BACK / "official_runs" / "k10_analysis_2026-09-27",
                   iso.BACK / "experiments" / "preregistration_k10_2026-09-26")
_V3_MODULES = ("analysis/statistical_rule_v3.py", "gold/rubric_v3.py", "analysis/replicas_v3.py")


def _sha_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _sha_file(p: Path) -> str:
    return _sha_bytes(Path(p).read_bytes())


def _canonical(obj: dict) -> bytes:
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def _write_new(path: Path, data: bytes) -> None:
    with path.open("xb") as fh:                              # modo exclusivo: falla si ya existe
        fh.write(data)


def module_fingerprints_v3() -> dict[str, str]:
    """sha256 de las piezas v3 (aparte de `module_fingerprints()` de v2, que no se altera y NO incluye archivos v3)."""
    root = Path(adaptation_swarm.__file__).parent
    return {f: _sha_file(root / f) for f in _V3_MODULES}


# ── puerta ─────────────────────────────────────────────────────────────────────────────────────────────────────
def _require_v3_rule(rule: object) -> None:
    if not rubric_v3.is_registered_v3(rule):
        raise ValueError("replicas_v3 solo acepta una regla v3 REGISTRADA de `rubric_v3` (no una regla de v2, ad hoc ni alterada)")


def _gate(*, official: bool, k: int, master_seed: int, rule: object, full_rule_version: str | None, limit_profiles: int | None) -> str:
    """Estado del plan. `official=True` exige regla v3 aprobada, versión completa explícita, K = 10, semilla maestra de K = 10 y los 100 perfiles; cualquier otra cosa es PROVISIONAL."""
    _require_v3_rule(rule)
    if not official:
        return "PROVISIONAL"
    rubric_v3.require_approved(rule)                         # RuleNotApproved: hoy el registro v3 está vacío ⇒ la ejecución oficial está bloqueada
    if not full_rule_version:
        raise rubric_v3.NoRuleSelected("una corrida oficial v3 exige la versión completa de la regla (gold + inclusión + agregación + protocolo del panel) fijada por el pre-registro; no se infiere")
    if not (full_rule_version == rule.rule_version or full_rule_version.startswith(rule.rule_version + "+")):
        raise ValueError(f"la versión completa {full_rule_version!r} no corresponde a la regla {rule.rule_version!r}")
    if k != K_OFFICIAL:
        raise ValueError(f"una corrida oficial exige K = {K_OFFICIAL} (decisión D5b del asesor), no {k}")
    if master_seed != K10_MASTER_SEED:
        raise ValueError(f"una corrida oficial v3 conserva la semilla maestra de K = 10 ({K10_MASTER_SEED}); otra semilla sería seed fishing y rompería la comparabilidad con v2")
    if limit_profiles is not None:
        raise ValueError("una corrida oficial usa los 100 perfiles: limit_profiles solo en una corrida provisional")
    return "OFICIAL"


def build_plan_v3(*, master_seed: int, k: int, library_version: str, rule: object, official: bool = False, full_rule_version: str | None = None,
                  library_root: Path | None = None, profiles_path: Path = DEFAULT_PROFILES, params: PSOParams = PSOParams(), fw: FitnessWeights = FitnessWeights(),
                  limit_profiles: int | None = None) -> dict:
    """Plan de la ejecución v3 (no calcula nada). Todo es explícito: semilla maestra, K, versión de biblioteca y regla (sin valores por defecto para ellos)."""
    status = _gate(official=official, k=k, master_seed=master_seed, rule=rule, full_rule_version=full_rule_version, limit_profiles=limit_profiles)
    library_root = Path(library_root or SETTINGS.library_root)
    manifest_file = library_root / library_version / "manifest.json"
    profiles = read_dataset(profiles_path)
    if status == "OFICIAL" and len(profiles) != N_PROFILES_OFFICIAL:
        raise ValueError(f"una corrida oficial usa {N_PROFILES_OFFICIAL} perfiles, el dataset trae {len(profiles)}")
    n_used = len(profiles) if limit_profiles is None else min(limit_profiles, len(profiles))
    seeds = _v2_infra.derive_batch_seeds(master_seed, k)                                           # la MISMA derivación que v2
    return {"schema": SCHEMA_PLAN, "status": status, "master_seed": master_seed, "k": k, "batch_seeds": seeds,
            "config": {"pso": params.to_dict(), "fitness_weights": fw.to_dict(), "config_hash": params.config_hash(), "replicate_index": 0},
            "library": {"version": library_version, "manifest_sha256": _sha_file(manifest_file)},
            "dataset": {"file": Path(profiles_path).name, "sha256": _sha_file(profiles_path), "n_profiles": len(profiles), "n_used": n_used, "limited": n_used != len(profiles),
                        **_v2_infra.dataset_identity(profiles_path)},
            "rule": {**rule.to_dict(), "status": rubric_v3.status_of(rule), "official_version": rubric_v3.official_version(rule), "full_rule_version": full_rule_version,
                     "gold_fingerprint": rule.gold.fingerprint()},
            "protocol": {"aggregation": OFFICIAL_AGGREGATION, "metric_version": METRIC_VERSION,
                         "inference": {**INFERENCE_PROTOCOL, "statistical_pass_rule": statistical_rule_v3.STATISTICAL_PASS_RULE_VERSION}},
            "scope": SCOPE, "code_version": _v2_infra.code_version(), "environment": _v2_infra.environment(),
            "modules": _v2_infra.module_fingerprints(), "modules_v3": module_fingerprints_v3(),
            "independence": {"derivation": "sha256('replicas-v1|master|i')[:8] & (2^63-1) (la misma de v2)", "historical_batch_seeds_excluded": sorted(_v2_infra.HISTORICAL_BATCH_SEEDS)}}


# ── salida ─────────────────────────────────────────────────────────────────────────────────────────────────────
def _new_dir(out_dir: Path, *, official: bool) -> Path:
    out = Path(out_dir)
    resolved = out.resolve()
    for frozen in _V2_FROZEN_DIRS:
        if resolved == frozen.resolve() or frozen.resolve() in resolved.parents:
            raise ValueError(f"{out}: dentro de {frozen.relative_to(iso.BACK.parent)}, artefacto congelado de K = 10 v2; los resultados v3 no se mezclan con los de v2")
    if official and not (resolved == V3_OUTPUT_ROOT.resolve() or V3_OUTPUT_ROOT.resolve() in resolved.parents):
        raise ValueError(f"{out}: una corrida oficial v3 solo escribe bajo {V3_OUTPUT_ROOT.relative_to(iso.BACK.parent)}")
    iso.check_new_output_targets([out / "plan.json", out / "manifest.json", out / "execution_metadata.json"])      # no dentro de resultados/datasets/paquetes; nada existente
    out.mkdir(parents=True, exist_ok=False)                                                                       # un directorio NUEVO: nunca se reutiliza ni sobrescribe
    return out


def write_plan(plan: dict, out_dir: Path) -> Path:
    out = _new_dir(out_dir, official=plan["status"] == "OFICIAL")
    _write_new(out / "plan.json", _canonical(plan) + b"\n")
    return out


def revalidate_plan(plan: dict, *, profiles_path: Path = DEFAULT_PROFILES, library_root: Path | None = None) -> str:
    """Estado del plan tras RECONSTRUIRLO con la misma puerta que `build_plan_v3`. No confía en ningún campo del plan: un plan manipulado, incompleto o que declare ser OFICIAL sin regla v3 aprobada se rechaza
    antes de crear archivo alguno."""
    if not isinstance(plan, dict) or plan.get("schema") != SCHEMA_PLAN:
        raise ValueError("plan no reconocido")
    try:
        status = plan["status"]
        if status not in ("OFICIAL", "PROVISIONAL"):
            raise ValueError(f"estado de plan no reconocido: {status!r}")
        r, ds = plan["rule"], plan["dataset"]
        rule = rubric_v3.get_rule(r["gold"]["rule_version"], r["inclusion"]["rule_id"])                      # solo reglas v3 REGISTRADAS
        expected = build_plan_v3(master_seed=plan["master_seed"], k=plan["k"], library_version=plan["library"]["version"], rule=rule, official=status == "OFICIAL",
                                 full_rule_version=r.get("full_rule_version"), library_root=library_root, profiles_path=profiles_path, params=PSOParams(**plan["config"]["pso"]),
                                 fw=FitnessWeights(**plan["config"]["fitness_weights"]), limit_profiles=ds["n_used"] if ds["limited"] else None)
        identical = _canonical(plan) == _canonical(expected)
    except (KeyError, TypeError, AttributeError) as exc:
        raise ValueError(f"plan incompleto o manipulado: {exc!r}") from exc
    if not identical:
        raise ValueError("el plan no coincide con el que se reconstruye a partir de sus parámetros: manipulado, incompleto o el código/datos cambiaron")
    return expected["status"]


def run_replicas_v3(plan: dict, out_dir: Path, *, profiles_path: Path = DEFAULT_PROFILES, library_root: Path | None = None) -> dict:
    """Ejecuta el plan v3: K réplicas × perfiles, en proceso (núcleo PSO+𝓕, sin Redis, LLM ni red). Devuelve el manifiesto (también escrito en `manifest.json`). El estado lo fija `revalidate_plan`, no
    el campo `status` del plan. Con un plan OFICIAL y la regla no aprobada lanza `RuleNotApproved` ANTES de crear archivo alguno."""
    status = revalidate_plan(plan, profiles_path=profiles_path, library_root=library_root)
    library_root = Path(library_root or SETTINGS.library_root)
    store = LibraryStore.open(library_root, plan["library"]["version"])
    profiles = read_dataset(profiles_path)[: plan["dataset"]["n_used"]]
    params, fw = PSOParams(**plan["config"]["pso"]), FitnessWeights(**plan["config"]["fitness_weights"])
    rp = plan["rule"]
    rule = rubric_v3.get_rule(rp["gold"]["rule_version"], rp["inclusion"]["rule_id"])
    provenance = {"rule_version": rp["rule_version"], "full_rule_version": rp["full_rule_version"], "gold_fingerprint": rp["gold_fingerprint"],
                  "statistical_rule_version": statistical_rule_v3.STATISTICAL_PASS_RULE_VERSION, "dataset_sha256": plan["dataset"]["sha256"],
                  "library_version": plan["library"]["version"], "library_manifest_sha256": plan["library"]["manifest_sha256"], "code_version": plan["code_version"],
                  "environment": plan["environment"], "config": plan["config"], "protocol": plan["protocol"], "scope": plan["scope"]}
    out = write_plan(plan, out_dir)
    entries, all_case_seeds = [], []
    memo_by_concept: dict[str, dict] = {}                                     # términos de 𝓕 por (concepto, variantes): no dependen de la semilla
    for i, bs in enumerate(plan["batch_seeds"]):
        cases = []
        for p in profiles:
            r = replay_cycle(store, p, params, fw, bs, replicate=plan["config"]["replicate_index"], memo=memo_by_concept.setdefault(p.concept_id, {}))
            cases.append({"profile_id": p.profile_id, "archetype": p.archetype.value if p.archetype else None, "difficulty": p.difficulty.value if p.difficulty else None,
                          "concept_id": p.concept_id, "seed": r["seed"], "S": r["S"], "F": r["F"], "k_stop": r["k"], "stop_reason": r["stop_reason"]})
            all_case_seeds.append(r["seed"])
        for c, lab in zip(cases, cases_from_records(cases, rule)):            # F1 por caso con la regla v3 fijada en el plan (Dice; predicho vacío ⇒ 0)
            c["f1"] = None if lab.gold is None else case_f1(lab.gold, lab.predicted)
        body = _canonical({"schema": SCHEMA_REPLICA, "replica_id": i, "replica_index": i, "batch_seed": bs, "library_version": plan["library"]["version"],
                           "config_hash": plan["config"]["config_hash"], "provenance": provenance, "cases": cases}) + b"\n"
        name = f"replica_{i:02d}.json"
        _write_new(out / name, body)
        entries.append({"index": i, "batch_seed": bs, "file": name, "sha256": _sha_bytes(body), "n_cases": len(cases)})
    if len(set(all_case_seeds)) != len(all_case_seeds):
        raise RuntimeError("semillas de ciclo repetidas entre réplicas: las réplicas no son independientes")
    manifest = {"schema": SCHEMA_MANIFEST, "status": status, "plan_sha256": _sha_file(out / "plan.json"), "master_seed": plan["master_seed"], "k": plan["k"], "batch_seeds": plan["batch_seeds"],
                "replicas": entries, "n_case_seeds": len(all_case_seeds), "n_distinct_case_seeds": len(set(all_case_seeds)), "config": plan["config"], "library": plan["library"],
                "dataset": plan["dataset"], "rule": plan["rule"], "protocol": plan["protocol"], "scope": plan["scope"], "code_version": plan["code_version"],
                "environment": plan["environment"], "modules": plan["modules"], "modules_v3": plan["modules_v3"]}
    _write_new(out / "manifest.json", _canonical(manifest) + b"\n")
    meta = {"executed_at_utc": datetime.now(timezone.utc).isoformat(), "commit": plan["code_version"]["commit"], "plan_sha256": manifest["plan_sha256"],
            "manifest_sha256": _sha_file(out / "manifest.json"), "note": "marca de tiempo aparte: plan, réplicas y manifiesto son deterministas"}
    _write_new(out / "execution_metadata.json", _canonical(meta) + b"\n")
    return manifest


def verify(out_dir: Path) -> list[str]:
    """Problemas de integridad de un directorio de réplicas v3 (lista vacía = íntegro): hashes de cada réplica y del plan frente al manifiesto."""
    out, problems = Path(out_dir), []
    m = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    if m.get("schema") != SCHEMA_MANIFEST:
        problems.append("manifiesto no es de v3")
    if _sha_file(out / "plan.json") != m["plan_sha256"]:
        problems.append("plan.json no coincide con el manifiesto")
    for e in m["replicas"]:
        if _sha_file(out / e["file"]) != e["sha256"]:
            problems.append(f"{e['file']}: sha256 distinto del manifiesto")
    if len(set(m["batch_seeds"])) != len(m["batch_seeds"]):
        problems.append("batch_seeds repetidas")
    return problems
