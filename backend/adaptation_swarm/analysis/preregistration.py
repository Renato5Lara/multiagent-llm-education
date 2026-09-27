"""PRE-REGISTRO técnico del futuro K = 10 OFICIAL (cierre P5, decisión del tesista, 2026-09-26). NO es una ejecución ni contiene resultados: fija de antemano QUÉ se ejecutará y permite comprobar, antes de
ejecutar, que el plan real coincide con lo registrado.

Decisiones fijadas (del tesista, no del asesor):
    · semilla maestra OFICIAL = 26092601 (fecha de fijación). `424242` queda solo como semilla de PRUEBA de los tests: nunca para una corrida oficial;
    · biblioteca OFICIAL = `lib-v10-5dd83cd4` (su hash de manifiesto se calcula del disco, no se copia de documentos);
    · K = 10, réplicas de índice 0..9, con la derivación de `analysis/replicas.derive_batch_seeds`.

Funciones puras (sin red, procesos ni BD): `build_preregistration` lee el disco (manifiesto, artefactos, dataset) y devuelve el registro; `write_preregistration` lo escribe UNA vez en un archivo NUEVO;
`verify_preregistration` detecta deriva entre el archivo y el disco; `check_plan_matches_preregistration` compara un plan de réplicas con el pre-registro.

Este módulo NO aprueba la regla (`APPROVED_RULE_VERSIONS` sigue vacío) ni autoriza la corrida: solo la deja preparada y trazable. El estado de Git (árbol sucio o limpio) no puede determinarse sin ejecutar git: lo
recibe del llamador (`git_state`) o queda `None`.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from adaptation_swarm.analysis import inference, replicas
from adaptation_swarm.config import SETTINGS
from adaptation_swarm.fitness.fitness import FitnessWeights
from adaptation_swarm.gold import rubric_v2
from adaptation_swarm.gold.rubric_v2 import get_rule, is_approved, official_version, panel_protocol_fingerprint
from adaptation_swarm.multimodal.library import LibraryStore
from adaptation_swarm.multimodal.versioning import latest_version, manifest_hash
from adaptation_swarm.profiles.generator import read_dataset
from adaptation_swarm.pso.params import PSOParams
from adaptation_swarm.tools import isolated_env as iso

SCHEMA = "preregistration-k10-v1"
BANNER = "PRE-REGISTRO — NO EJECUTADO"
FIXED_ON = "2026-09-26"
OFFICIAL_MASTER_SEED = 26092601
TEST_MASTER_SEEDS = frozenset({424242})                       # semillas de PRUEBA (tests): jamás para una corrida oficial
OFFICIAL_LIBRARY_VERSION = "lib-v10-5dd83cd4"
OFFICIAL_RULE = ("gold-v2-cand-A", "incl-ge1")                # gold por arquetipo + inclusión e_m ≥ 1 (la agregación y el panel forman parte de `official_version`)
REQUIRED_PYTHON_SERIES = "3.12"                               # versión declarada por la especificación del estudio
REQUIREMENTS = iso.BACK / "requirements.txt"
FILE_NAME = "preregistration_k10.json"
DEFAULT_PATH = iso.BACK / "experiments" / "preregistration_k10_2026-09-26" / FILE_NAME
REPRODUCIBILITY_CRITERIA = (
    "mismo master_seed y K ⇒ exactamente las mismas 10 semillas de lote y las mismas 1000 semillas de ciclo (sin tiempo, PID, entorno ni random global)",
    "biblioteca identificada por versión + sha256 del manifiesto; cada artefacto leído se verifica contra el sha256 del manifiesto",
    "dataset identificado por versión + sha256 de profiles y de su manifiesto; exactamente 100 perfiles",
    "el plan se reconstruye en `revalidate_plan` (reglas, semillas, biblioteca, dataset, entorno, código): cualquier deriva lo rechaza antes de crear archivos",
    "salida en un directorio nuevo; nunca se sobrescribe; hashes de cada réplica en el manifiesto",
    "las réplicas del núcleo NO sustentan RNF-01 ni RNF-04 (experimento full-stack aparte)")


def _sha_file(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def _pins(requirements: Path = REQUIREMENTS) -> dict[str, str | None]:
    """Versiones fijadas en `requirements.txt` para las dependencias numéricas del núcleo (leídas, no copiadas)."""
    text = requirements.read_text(encoding="utf-8")
    out = {}
    for name in ("numpy", "scipy"):
        m = re.search(rf"^{name}==([0-9][^\s#]*)", text, flags=re.MULTILINE)
        out[name] = m.group(1) if m else None
    return out


def library_record(version: str = OFFICIAL_LIBRARY_VERSION, root: Path | None = None, *, deep: bool = True) -> dict:
    """Identidad de una biblioteca calculada del DISCO. `deep=True` verifica además cada artefacto (existencia y sha256) contra el manifiesto."""
    root = Path(root or SETTINGS.library_root)
    store = LibraryStore.open(root, version)                          # comprueba que el nombre de la versión coincide con el hash del cuerpo del manifiesto
    mpath = root / version / "manifest.json"
    manifest = json.loads(mpath.read_text(encoding="utf-8"))
    by_mod: dict[str, int] = {}
    for e in manifest["entries"]:
        by_mod[e["modality"]] = by_mod.get(e["modality"], 0) + 1
    rec = {"version": version, "manifest_file": f"{version}/manifest.json", "manifest_sha256": _sha_file(mpath), "manifest_id_ok": manifest_hash(manifest) == version.rsplit("-", 1)[1],
           "base_version": manifest["base_version"], "created_at": manifest["created_at"], "entries": len(manifest["entries"]), "concepts": len(manifest["anchors"]),
           "code_variants": by_mod.get("code", 0), "by_modality": {m: by_mod[m] for m in sorted(by_mod)}, "is_latest": store.version == latest_version(root)}
    if deep:
        bad, missing = [], []
        for e in manifest["entries"]:
            f = root / version / e["path"]
            if not f.exists():
                missing.append(e["path"])
            elif hashlib.sha256(f.read_bytes()).hexdigest() != e["sha256"]:
                bad.append(e["path"])
        rec["integrity"] = {"artifacts": len(manifest["entries"]), "missing": len(missing), "hash_mismatch": len(bad), "ok": not (missing or bad)}
    return rec


def dataset_record(profiles_path: Path = replicas.DEFAULT_PROFILES) -> dict:
    profiles = read_dataset(profiles_path)
    by_arch: dict[str, int] = {}
    by_diff: dict[str, int] = {}
    cells: dict[str, int] = {}
    for p in profiles:
        a, d = p.archetype.value, p.difficulty.value
        by_arch[a] = by_arch.get(a, 0) + 1
        by_diff[d] = by_diff.get(d, 0) + 1
        cells[f"{a}|{d}"] = cells.get(f"{a}|{d}", 0) + 1
    pairs = sorted((p.profile_id, p.concept_id) for p in profiles)
    return {"file": Path(profiles_path).name, "sha256": _sha_file(profiles_path), **replicas.dataset_identity(profiles_path), "n_profiles": len(profiles),
            "by_archetype": dict(sorted(by_arch.items())), "by_difficulty": dict(sorted(by_diff.items())), "n_cells": len(cells), "profiles_per_cell": sorted(set(cells.values())),
            "concepts_distinct": len({c for _, c in pairs}), "one_concept_per_profile": len({pid for pid, _ in pairs}) == len(pairs),
            "profile_concept_sha256": hashlib.sha256(json.dumps(pairs, separators=(",", ":")).encode("utf-8")).hexdigest()}


def build_preregistration(*, library_root: Path | None = None, profiles_path: Path = replicas.DEFAULT_PROFILES, deep: bool = True, git_state: dict | None = None) -> dict:
    """Construye el pre-registro leyendo el disco. Sin resultados: `contains_results` es siempre `False`."""
    rule = get_rule(*OFFICIAL_RULE)
    env, pins = replicas.environment(), _pins()
    seeds = replicas.derive_batch_seeds(OFFICIAL_MASTER_SEED, replicas.K_OFFICIAL)
    params = PSOParams()
    env_ok = {"python": env["python"].startswith(REQUIRED_PYTHON_SERIES + "."), "numpy": env["numpy"] == pins["numpy"], "scipy": env["scipy"] == pins["scipy"]}
    return {"schema": SCHEMA, "banner": BANNER, "status": "NO EJECUTADO", "contains_results": False, "fixed_on": FIXED_ON, "decided_by": "tesista (cierre P5)",
            "master_seed": OFFICIAL_MASTER_SEED, "master_seed_note": "424242 es solo la semilla de PRUEBA de los tests; nunca se usa en una corrida oficial",
            "k": replicas.K_OFFICIAL, "replica_indices": list(range(replicas.K_OFFICIAL)),
            "seed_derivation": {"batch": "sha256('replicas-v1|<master_seed>|<i>')[:8] big-endian & (2^63 - 1), i = 0..9", "cycle": "sha256('<batch_seed>|<profile_id>|<replicate>')[:8] big-endian, replicate = 0",
                                "rng": "numpy.random.Generator(PCG64(seed))", "excluded_historical_batch_seeds": sorted(replicas.HISTORICAL_BATCH_SEEDS)},
            "batch_seeds": seeds,
            "library": library_record(OFFICIAL_LIBRARY_VERSION, library_root, deep=deep), "dataset": dataset_record(profiles_path),
            "rule": {"official_version": official_version(rule), "gold": rule.gold.rule_version, "gold_fingerprint": rule.gold.fingerprint(), "inclusion": rule.inclusion.rule_id,
                     "aggregation": rubric_v2.OFFICIAL_AGGREGATION, "panel_protocol": rubric_v2.PANEL_PROTOCOL_VERSION, "panel_protocol_fingerprint": panel_protocol_fingerprint(),
                     "approved": is_approved(rule), "approval_note": "NO APROBADA: `APPROVED_RULE_VERSIONS` sigue vacío; este pre-registro no autoriza la corrida"},
            "pso": {"params": params.to_dict(), "config_hash": params.config_hash(), "fitness_weights": FitnessWeights().to_dict()},
            "inference": inference.PROTOCOL, "scope": replicas.SCOPE,
            "environment_required": {"python_series": REQUIRED_PYTHON_SERIES, "numpy": pins["numpy"], "scipy": pins["scipy"], "source": "backend/requirements.txt (numpy, scipy); Python: especificación del estudio"},
            "environment_at_fixing": {**env, "matches_required": env_ok,
                                      "python_3_12_status": "CUMPLE" if env_ok["python"] else "GAP TÉCNICO: el entorno de fijación NO es Python 3.12; verificar la equivalencia antes de la corrida oficial"},
            "git_at_fixing": {**replicas.code_version(), **(git_state or {})},
            "code_modules_at_fixing": replicas.module_fingerprints(), "reproducibility_criteria": list(REPRODUCIBILITY_CRITERIA)}


def write_preregistration(out_dir: Path, **kw) -> Path:
    """Escribe el pre-registro UNA vez, en un directorio NUEVO (nunca sobrescribe ni escribe en resultados congelados, datasets, biblioteca o paquetes de evidencia). Devuelve el directorio."""
    out = Path(out_dir)
    iso.check_new_output_targets([out / FILE_NAME])
    rec = build_preregistration(**kw)
    out.mkdir(parents=True, exist_ok=False)
    with (out / FILE_NAME).open("x", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, indent=2, sort_keys=True, ensure_ascii=False) + "\n")
    return out


# Estado de aprobación: cambia legítimamente con el REGISTRO FORMAL de la regla (`APPROVED_RULE_VERSIONS`) y NO es contenido metodológico inmutable. `verify_preregistration` lo excluye de la comparación
# de `rule` y lo trata aparte (`approval_state`): el archivo conserva la foto del momento de la fijación; el estado vigente se lee del sistema.
POST_REGISTRATION_RULE_FIELDS = ("approved", "approval_note")

_STABLE = ("schema", "banner", "status", "contains_results", "fixed_on", "master_seed", "k", "replica_indices", "seed_derivation", "batch_seeds", "rule", "pso", "inference", "scope",
           "environment_required", "reproducibility_criteria")


def _immutable(key: str, record: dict):
    """Valor de una sección estable SIN los campos de estado posteriores al registro (solo `rule` los tiene)."""
    v = record.get(key)
    if key == "rule" and isinstance(v, dict):
        return {k: x for k, x in v.items() if k not in POST_REGISTRATION_RULE_FIELDS}
    return v


def approval_state(path: Path = DEFAULT_PATH) -> dict:
    """Estado de aprobación: la foto guardada en el pre-registro (momento de la fijación) frente al estado vigente del sistema. Que difieran NO es deriva: es el registro formal de la regla."""
    stored = json.loads(Path(path).read_text(encoding="utf-8"))["rule"]
    live = is_approved(get_rule(*OFFICIAL_RULE))
    return {"at_fixing": {k: stored.get(k) for k in POST_REGISTRATION_RULE_FIELDS}, "live_approved": live, "changed_since_fixing": stored.get("approved") is not live}


def verify_preregistration(path: Path = DEFAULT_PATH, *, deep: bool = False, library_root: Path | None = None, profiles_path: Path = replicas.DEFAULT_PROFILES) -> list[str]:
    """Problemas de deriva entre el archivo y el disco (lista vacía = coincide). Compara las secciones METODOLÓGICAS inmutables (decisiones, semillas, biblioteca, dataset, regla sin su estado de aprobación, PSO,
    inferencia, alcance, entorno requerido); NO compara Git ni el entorno de fijación (informativos) ni `rule.approved`/`rule.approval_note` (estado posterior al registro: ver `approval_state`). Solo se exige
    que esos dos campos existan con su tipo. Con `deep=True` re-verifica cada artefacto de la biblioteca."""
    stored = json.loads(Path(path).read_text(encoding="utf-8"))
    fresh = build_preregistration(library_root=library_root, profiles_path=profiles_path, deep=deep)
    problems = [f"{k}: el archivo difiere del disco" for k in _STABLE if _immutable(k, stored) != _immutable(k, fresh)]
    rule = stored.get("rule") or {}
    if not isinstance(rule.get("approved"), bool) or not isinstance(rule.get("approval_note"), str):
        problems.append("rule.approved / rule.approval_note: ausentes o de tipo incorrecto")
    lib_keys = [k for k in fresh["library"] if k != "integrity"]
    problems += [f"library.{k}: {stored['library'].get(k)!r} ≠ {fresh['library'][k]!r}" for k in lib_keys if stored["library"].get(k) != fresh["library"][k]]
    if deep and stored["library"].get("integrity") != fresh["library"].get("integrity"):
        problems.append("library.integrity: difiere")
    problems += [f"dataset.{k}: {stored['dataset'].get(k)!r} ≠ {fresh['dataset'][k]!r}" for k in fresh["dataset"] if stored["dataset"].get(k) != fresh["dataset"][k]]
    if stored.get("master_seed") in TEST_MASTER_SEEDS:
        problems.append("la semilla maestra es una semilla de prueba")
    return problems


def code_modules_drift(path: Path = DEFAULT_PATH) -> list[str]:
    """Módulos cuyo fingerprint actual difiere del registrado en `code_modules_at_fixing` (lista vacía = el código es el de la fijación). Es la comprobación del sellado: el commit debe conservar estos hashes."""
    stored = json.loads(Path(path).read_text(encoding="utf-8"))["code_modules_at_fixing"]
    now = replicas.module_fingerprints()
    return sorted({k for k in set(stored) | set(now) if stored.get(k) != now.get(k)})


def verify_addendum(addendum_path: Path, prereg_path: Path = DEFAULT_PATH) -> list[str]:
    """Verifica un ADDENDUM del pre-registro (archivo aparte; nunca reescribe el original): que apunte al sha256 vigente del pre-registro, que su `changes_methodology` sea `False` y que cada archivo de evidencia
    citado siga teniendo el sha256 registrado (rutas relativas a `evidence_root`)."""
    add = json.loads(Path(addendum_path).read_text(encoding="utf-8"))
    problems = []
    if add.get("preregistration", {}).get("sha256") != _sha_file(prereg_path):
        problems.append("preregistration.sha256: no coincide con el pre-registro vigente")
    if add.get("changes_methodology") is not False:
        problems.append("changes_methodology debe ser False: un addendum no cambia decisiones metodológicas")
    root = iso.BACK / add.get("evidence_root", "")
    for rel, sha in (add.get("evidence_files") or {}).items():
        f = root / rel
        if not f.exists() or _sha_file(f) != sha:
            problems.append(f"evidencia {rel}: ausente o con otro sha256")
    return problems


def check_plan_matches_preregistration(plan: dict, prereg: dict) -> list[str]:
    """Compara un plan de réplicas (`replicas.build_plan`) con el pre-registro: semilla maestra, K, semillas, biblioteca, dataset y regla. Lista vacía = coincide. Úsese ANTES de una corrida oficial."""
    problems = []
    for label, a, b in (("master_seed", plan["master_seed"], prereg["master_seed"]), ("k", plan["k"], prereg["k"]), ("batch_seeds", plan["batch_seeds"], prereg["batch_seeds"]),
                        ("library.version", plan["library"]["version"], prereg["library"]["version"]), ("library.manifest_sha256", plan["library"]["manifest_sha256"], prereg["library"]["manifest_sha256"]),
                        ("dataset.sha256", plan["dataset"]["sha256"], prereg["dataset"]["sha256"]), ("dataset.version", plan["dataset"].get("version"), prereg["dataset"]["version"]),
                        ("dataset.n_used", plan["dataset"]["n_used"], prereg["dataset"]["n_profiles"]),
                        ("rule.official_version", None if plan["rule"] is None else plan["rule"]["official_version"], prereg["rule"]["official_version"])):
        if a != b:
            problems.append(f"{label}: plan {a!r} ≠ pre-registro {b!r}")
    if plan["master_seed"] in TEST_MASTER_SEEDS:
        problems.append("el plan usa una semilla de prueba")
    return problems


def main(argv: list[str] | None = None) -> None:
    import argparse
    ap = argparse.ArgumentParser(description="Escribe el pre-registro técnico del K = 10 oficial (NO ejecuta nada)")
    ap.add_argument("--out-dir", required=True, help="directorio NUEVO (fuera de resultados congelados, datasets, biblioteca y paquetes de evidencia)")
    ap.add_argument("--git-dirty", choices=["yes", "no", "unknown"], default="unknown", help="estado del árbol medido por el llamador (este módulo no ejecuta git)")
    a = ap.parse_args(argv)
    out = write_preregistration(iso.require_out_dir(a.out_dir), git_state={"dirty": {"yes": True, "no": False, "unknown": None}[a.git_dirty]})
    print(f"{BANNER}: escrito en {out}")


if __name__ == "__main__":
    main()
