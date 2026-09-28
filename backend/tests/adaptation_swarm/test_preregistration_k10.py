"""Pre-registro técnico del K = 10 OFICIAL (cierre P5, decisión del tesista: master_seed = 26092601, biblioteca `lib-v10`). Puras: leen el disco y comparan; NO ejecutan réplicas (ni K = 10, ni el panel), no tocan el
dataset ni la biblioteca y no aprueban ninguna regla. El único `build_plan` de este archivo es PROVISIONAL o usa una aprobación en memoria, solo para comparar campos (no ejecuta nada)."""

import ast
import difflib
import hashlib
import json
import shutil
import subprocess
from pathlib import Path

import pytest

from adaptation_swarm.analysis import preregistration as pr
from adaptation_swarm.analysis import replicas as rp
from adaptation_swarm.gold import rubric_v2
from adaptation_swarm.gold.rubric_v2 import get_rule, official_version
from adaptation_swarm.schemas import ids

PREREG = pr.DEFAULT_PATH
LIB = pr.OFFICIAL_LIBRARY_VERSION


@pytest.fixture(scope="module")
def prereg():
    return json.loads(PREREG.read_text(encoding="utf-8"))


# ── semilla maestra y derivación (funciones puras) ──────────────────────────────────────────────────────────────────
def test_the_official_master_seed_is_26092601_and_424242_stays_a_test_seed():
    assert pr.OFFICIAL_MASTER_SEED == 26092601 and 424242 in pr.TEST_MASTER_SEEDS and pr.OFFICIAL_MASTER_SEED not in pr.TEST_MASTER_SEEDS
    assert 26092601 not in rp.HISTORICAL_BATCH_SEEDS and 424242 != 26092601


def test_ten_batch_seeds_are_deterministic_distinct_in_range_and_match_an_independent_derivation():
    a, b = rp.derive_batch_seeds(26092601, 10), rp.derive_batch_seeds(26092601, 10)
    assert a == b and len(a) == 10 and len(set(a)) == 10                                            # determinista, 10 y distintas
    assert all(0 <= s < 2 ** 63 for s in a) and not set(a) & rp.HISTORICAL_BATCH_SEEDS              # dentro del rango; ninguna es la histórica
    independent = [int.from_bytes(hashlib.sha256(f"replicas-v1|26092601|{i}".encode()).digest()[:8], "big") & ((1 << 63) - 1) for i in range(10)]
    assert a == independent                                                                         # índices 0..9, fórmula documentada
    assert set(a).isdisjoint(rp.derive_batch_seeds(424242, 10))                                     # distintas de las de la semilla de prueba


def test_the_derivation_does_not_depend_on_time_pid_environment_or_global_random():
    forbidden = {"time", "datetime", "os", "random", "getpid", "environ", "uuid", "secrets", "getenv"}
    for fn in (rp.derive_batch_seeds, ids.derive_seed):
        import inspect
        tree = ast.parse(inspect.getsource(fn).lstrip())
        names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)} | {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
        assert not names & forbidden, (fn.__name__, names & forbidden)


def test_the_thousand_cycle_seeds_are_unique():
    from adaptation_swarm.profiles.generator import read_dataset
    ps = read_dataset(rp.DEFAULT_PROFILES)
    cycle = [ids.derive_seed(bs, p.profile_id, 0) for bs in rp.derive_batch_seeds(26092601, 10) for p in ps]
    assert len(cycle) == 1000 == len(set(cycle))


# ── el pre-registro: contenido y ausencia de resultados ─────────────────────────────────────────────────────────────
def test_the_preregistration_is_marked_not_executed_and_holds_no_results(prereg):
    assert prereg["banner"] == "PRE-REGISTRO — NO EJECUTADO" and prereg["status"] == "NO EJECUTADO" and prereg["contains_results"] is False
    assert prereg["master_seed"] == 26092601 and prereg["k"] == 10 and prereg["replica_indices"] == list(range(10)) and prereg["batch_seeds"] == rp.derive_batch_seeds(26092601, 10)
    assert not {"f1", "f1_adapt", "ci95", "results", "criterion", "replicas"} & set(prereg)
    assert "424242" in prereg["master_seed_note"]
    assert not list((Path(__file__).resolve().parents[2] / "experiments").glob("replicas*")) and not list((Path(__file__).resolve().parents[2] / "experiments").rglob("replica_00.json"))


def test_the_preregistered_library_is_lib_v10_with_a_manifest_hash_taken_from_disk(prereg):
    lib = prereg["library"]
    disk = Path(rp.SETTINGS.library_root) / LIB / "manifest.json"
    assert lib["version"] == LIB == "lib-v10-5dd83cd4" and lib["manifest_sha256"] == hashlib.sha256(disk.read_bytes()).hexdigest()
    assert lib["manifest_id_ok"] is True and lib["entries"] == 1080 and lib["concepts"] == 30 and lib["code_variants"] == 90 and lib["is_latest"] is True
    assert lib["by_modality"] == {"audio": 270, "code": 90, "cpp": 90, "diagram": 270, "svg": 270, "text": 90} and lib["base_version"] == "lib-v9-a0231e9b"
    assert lib["integrity"] == {"artifacts": 1080, "missing": 0, "hash_mismatch": 0, "ok": True}


def test_the_preregistered_dataset_is_profiles_v1_with_its_hash_and_distribution(prereg):
    ds, disk = prereg["dataset"], rp.DEFAULT_PROFILES
    assert ds["file"] == "profiles-v1.jsonl" and ds["version"] == "v1" and ds["sha256"] == hashlib.sha256(disk.read_bytes()).hexdigest() and ds["n_profiles"] == 100
    assert ds["sha256"] == json.loads(disk.with_name("manifest-v1.json").read_text(encoding="utf-8"))["sha256"]                # coincide con lo que declara el propio manifiesto del dataset
    assert ds["by_archetype"] == {a: 25 for a in ("balanced_multimodal", "explanatory_conceptual", "logical_syntactic", "visual_dominant")}
    assert ds["by_difficulty"] == {d: 20 for d in ("arrays_vectors", "conditional", "functions", "repetitive", "sequential")} and ds["n_cells"] == 20 and ds["profiles_per_cell"] == [5]
    assert ds["concepts_distinct"] == 30 and ds["one_concept_per_profile"] is True


def test_the_preregistered_rule_version_is_the_registered_one_and_its_frozen_photo_is_not_approved(prereg):
    rule = get_rule(*pr.OFFICIAL_RULE)
    r = prereg["rule"]
    assert r["official_version"] == official_version(rule) == "gold-v2-cand-A+incl-ge1+samples+panel-arq-ac1-maj-tie0-v2"
    assert (r["gold"], r["inclusion"], r["aggregation"], r["panel_protocol"]) == ("gold-v2-cand-A", "incl-ge1", "samples", "panel-arq-ac1-maj-tie0-v2")
    assert r["gold_fingerprint"] == rule.gold.fingerprint() and r["panel_protocol_fingerprint"] == rubric_v2.panel_protocol_fingerprint()
    assert r["approved"] is False                                                                   # la FOTO congelada del archivo no cambia: el pre-registro NO aprueba nada
    assert rubric_v2.APPROVED_RULE_VERSIONS == frozenset({r["official_version"]})                   # estado VIVO: registro técnico posterior, exactamente esta regla y solo esa


def test_the_environment_is_declared_and_the_python_312_gap_is_explicit(prereg):
    req, at = prereg["environment_required"], prereg["environment_at_fixing"]
    assert req["python_series"] == "3.12" and req["numpy"] == pr._pins()["numpy"] and req["scipy"] == pr._pins()["scipy"] and req["numpy"] and req["scipy"]
    assert at["matches_required"]["python"] is at["python"].startswith("3.12.")                     # coherencia interna: el GAP se declara, no se oculta
    assert at["python_3_12_status"].startswith("CUMPLE" if at["matches_required"]["python"] else "GAP TÉCNICO")
    assert prereg["git_at_fixing"]["dirty"] in (True, False, None) and prereg["git_at_fixing"]["commit"]


def test_the_preregistration_matches_the_disk_without_drift():
    assert pr.verify_preregistration(PREREG, deep=False) == []


def test_drift_between_the_file_and_the_disk_is_detected(tmp_path, prereg):
    for field, value in (("master_seed", 424242), ("batch_seeds", [1] * 10), ("k", 9)):
        forged = json.loads(json.dumps(prereg))
        forged[field] = value
        f = tmp_path / f"forged_{field}.json"
        f.write_text(json.dumps(forged), encoding="utf-8")
        assert pr.verify_preregistration(f, deep=False), field
    forged = json.loads(json.dumps(prereg))
    forged["library"]["manifest_sha256"] = "0" * 64
    f = tmp_path / "forged_lib.json"
    f.write_text(json.dumps(forged), encoding="utf-8")
    assert any("manifest_sha256" in p for p in pr.verify_preregistration(f, deep=False))
    forged = json.loads(json.dumps(prereg))
    forged["dataset"]["sha256"] = "0" * 64
    f = tmp_path / "forged_ds.json"
    f.write_text(json.dumps(forged), encoding="utf-8")
    assert any("dataset.sha256" in p for p in pr.verify_preregistration(f, deep=False))


def test_a_test_seed_in_the_file_is_reported(tmp_path, prereg):
    forged = json.loads(json.dumps(prereg))
    forged["master_seed"] = 424242
    f = tmp_path / "seed.json"
    f.write_text(json.dumps(forged), encoding="utf-8")
    assert any("semilla de prueba" in p for p in pr.verify_preregistration(f, deep=False))


def test_the_preregistration_is_written_once_and_never_overwritten(tmp_path):
    out = pr.write_preregistration(tmp_path / "prereg", deep=False, git_state={"dirty": None})
    assert (out / pr.FILE_NAME).exists() and json.loads((out / pr.FILE_NAME).read_text(encoding="utf-8"))["banner"] == pr.BANNER
    with pytest.raises(SystemExit, match="no se sobrescriben"):
        pr.write_preregistration(tmp_path / "prereg", deep=False)
    with pytest.raises(SystemExit):
        pr.write_preregistration(Path(rp.SETTINGS.library_root) / "prereg", deep=False)              # ni dentro de la biblioteca ni de datasets protegidos


# ── el plan real frente al pre-registro (no ejecuta nada) ──────────────────────────────────────────────────────────
def _official_plan(monkeypatch, **kw):
    rule = get_rule(*pr.OFFICIAL_RULE)
    monkeypatch.setattr(rubric_v2, "APPROVED_RULE_VERSIONS", frozenset({official_version(rule)}))   # aprobación SOLO en memoria y durante la prueba; no se ejecuta ninguna réplica
    return rp.build_plan(**{"master_seed": pr.OFFICIAL_MASTER_SEED, "k": 10, "library_version": LIB, "provisional": False, "rule": rule, **kw})


def test_a_plan_with_the_preregistered_choices_matches_the_preregistration(monkeypatch, prereg):
    plan = _official_plan(monkeypatch)
    assert pr.check_plan_matches_preregistration(plan, prereg) == [] and plan["status"] == "OFICIAL"
    assert plan["library"]["manifest_sha256"] == prereg["library"]["manifest_sha256"] and plan["dataset"]["version"] == "v1"
    assert plan["dataset"]["manifest_sha256"] == prereg["dataset"]["manifest_sha256"]


def test_a_plan_that_deviates_from_the_preregistration_is_reported(monkeypatch, prereg):
    assert any("master_seed" in p for p in pr.check_plan_matches_preregistration(_official_plan(monkeypatch, master_seed=424242), prereg))
    assert any("library.version" in p for p in pr.check_plan_matches_preregistration(_official_plan(monkeypatch, library_version="lib-v9-a0231e9b"), prereg))
    provisional = rp.build_plan(master_seed=26092601, k=10, library_version=LIB, provisional=True)
    assert any("rule.official_version" in p for p in pr.check_plan_matches_preregistration(provisional, prereg))     # un plan sin regla no coincide


def test_the_plan_and_manifest_record_the_environment_dataset_identity_and_an_unknown_dirty_state(monkeypatch):
    plan = _official_plan(monkeypatch)
    env = plan["environment"]
    assert set(env) == {"python", "implementation", "numpy", "scipy"} and env == rp.environment()
    assert plan["code_version"]["dirty"] is None and plan["code_version"]["commit"]                   # el árbol sucio/limpio NO se puede distinguir: se declara desconocido, no «limpio»
    assert {"version", "manifest_file", "manifest_sha256"} <= set(plan["dataset"])
    assert "analysis/inference.py" in plan["modules"] and "gold/rubric_v2.py" in plan["modules"]


def test_an_official_run_is_still_impossible_without_an_approved_rule():
    unapproved = get_rule("gold-v2-cand-A", "incl-ge2")                                             # gold-v2 registrada, ausente de APPROVED_RULE_VERSIONS
    assert official_version(unapproved) not in rubric_v2.APPROVED_RULE_VERSIONS
    with pytest.raises(rubric_v2.RuleNotApproved):
        rp.build_plan(master_seed=pr.OFFICIAL_MASTER_SEED, k=10, library_version=LIB, provisional=False, rule=unapproved)


def test_the_library_directory_is_not_modified_by_the_audit_and_is_the_only_official_choice():
    v9 = Path(rp.SETTINGS.library_root) / "lib-v9-a0231e9b" / "manifest.json"
    v10 = Path(rp.SETTINGS.library_root) / LIB / "manifest.json"
    assert v9.exists() and v10.exists() and hashlib.sha256(v10.read_bytes()).hexdigest() != hashlib.sha256(v9.read_bytes()).hexdigest()
    assert pr.OFFICIAL_LIBRARY_VERSION.startswith("lib-v10-")
    _ = shutil                                                                                       # (sin copias ni escrituras en la biblioteca)


# ── A · verify_preregistration: contenido metodológico inmutable frente al estado de aprobación ─────────────────────
PREREG_SHA256 = "9e8cd2360b38172d6ddbacee532985970a703f16746bf981c046e0230e714928"          # sha256 del pre-registro original: no debe cambiar jamás


def _copy(prereg, tmp_path, name, mutate):
    forged = json.loads(json.dumps(prereg))
    mutate(forged)
    f = tmp_path / name
    f.write_text(json.dumps(forged), encoding="utf-8")
    return f


def _set(path):
    def apply(d, value):
        node = d
        for k in path[:-1]:
            node = node[k]
        node[path[-1]] = value
    return apply


def test_the_original_preregistration_file_is_untouched_and_passes():
    assert hashlib.sha256(PREREG.read_bytes()).hexdigest() == PREREG_SHA256                        # ni una coma cambió desde la fijación
    assert pr.verify_preregistration(PREREG, deep=False) == []
    assert pr.approval_state(PREREG) == {"at_fixing": {"approved": False, "approval_note": json.loads(PREREG.read_text(encoding="utf-8"))["rule"]["approval_note"]},
                                         "live_approved": True, "changed_since_fixing": True}       # foto congelada (no aprobada) ≠ estado vivo (registro técnico posterior): es lo que `approval_state` distingue


def test_the_approval_state_after_formal_registration_is_not_methodological_drift(tmp_path, prereg, monkeypatch):
    for approved, note in ((True, "APROBADA (PX9) y registrada formalmente"), (False, ""), (True, "otra nota")):
        f = _copy(prereg, tmp_path, f"approval_{approved}_{len(note)}.json", lambda d, a=approved, n=note: d["rule"].update({"approved": a, "approval_note": n}))
        assert pr.verify_preregistration(f, deep=False) == [], (approved, note)                     # cambiar SOLO el estado de aprobación NO es deriva
    rule = get_rule(*pr.OFFICIAL_RULE)
    monkeypatch.setattr(rubric_v2, "APPROVED_RULE_VERSIONS", frozenset({official_version(rule)}))    # aprobación SOLO en memoria: el original sigue sin dar deriva
    assert pr.verify_preregistration(PREREG, deep=False) == []
    st = pr.approval_state(PREREG)
    assert st["live_approved"] is True and st["at_fixing"]["approved"] is False and st["changed_since_fixing"] is True


def test_a_malformed_approval_state_is_reported_but_it_is_not_a_methodology_change(tmp_path, prereg):
    for bad in ({"approved": "no"}, {"approval_note": 5}):
        f = _copy(prereg, tmp_path, f"bad_{list(bad)[0]}.json", lambda d, b=bad: d["rule"].update(b))
        assert any("approved" in p for p in pr.verify_preregistration(f, deep=False))
    f = _copy(prereg, tmp_path, "missing.json", lambda d: d["rule"].pop("approved"))
    assert any("approved" in p for p in pr.verify_preregistration(f, deep=False))


METHODOLOGICAL_FIELDS = [
    (("master_seed",), 424243), (("k",), 9), (("replica_indices",), [0, 1, 2]), (("batch_seeds",), [1] * 10), (("seed_derivation", "batch"), "otra derivación"),
    (("library", "version"), "lib-v9-a0231e9b"), (("library", "manifest_sha256"), "0" * 64), (("library", "entries"), 1077), (("library", "by_modality", "cpp"), 87),
    (("dataset", "sha256"), "0" * 64), (("dataset", "version"), "v2"), (("dataset", "n_profiles"), 99), (("dataset", "profile_concept_sha256"), "0" * 64),
    (("rule", "official_version"), "gold-v2-cand-A+incl-ge1+samples+panel-arq-v1"), (("rule", "gold_fingerprint"), "0" * 64), (("rule", "panel_protocol_fingerprint"), "0" * 64),
    (("rule", "inclusion"), "incl-ge2"), (("rule", "aggregation"), "macro"), (("rule", "panel_protocol"), "panel-arq-v1"),
    (("pso", "config_hash"), "0" * 64), (("pso", "params", "n_particles"), 30), (("inference", "alternative"), "two-sided"), (("scope", "experiment"), "full_stack"),
    (("environment_required", "numpy"), "0.0.0"), (("environment_required", "python_series"), "3.14"), (("contains_results",), True), (("status",), "EJECUTADO"),
]


@pytest.mark.parametrize("path, value", METHODOLOGICAL_FIELDS, ids=[".".join(p) for p, _ in METHODOLOGICAL_FIELDS])
def test_changing_any_methodological_field_is_detected_as_drift(tmp_path, prereg, path, value):
    f = _copy(prereg, tmp_path, "m.json", lambda d: _set(path)(d, value))
    assert pr.verify_preregistration(f, deep=False), path


def test_code_module_drift_is_detected_by_tampering_with_the_recorded_fingerprints(tmp_path, prereg):
    f = _copy(prereg, tmp_path, "c.json", lambda d: d["code_modules_at_fixing"].update({"pso/engine.py": "0" * 64}))
    assert pr.code_modules_drift(f) == ["gold/rubric_v2.py", "pso/engine.py"]                        # el drift autorizado de rubric_v2 + el manipulado: la detección sigue viva
    assert pr.verify_preregistration(f, deep=False) == []                                            # los fingerprints de código son informativos para `verify`; el sellado usa `code_modules_drift`


# ── drift posterior al sellado: el ÚNICO permitido es el registro técnico de la regla aprobada, anclado al commit de sellado ──
SEALING_COMMIT = "5d7d12c9776a62d1234afb71acb505cd84cb5872"
RUBRIC = "gold/rubric_v2.py"
RUBRIC_IN_GIT = "backend/adaptation_swarm/gold/rubric_v2.py"
SEALED_RUBRIC_SHA256 = "071a2ae8896e549f02c57195188bd759ede81cfabd6c3a07e2a06c38298f596a"          # rubric_v2.py en el commit de sellado (= `code_modules_at_fixing`)
REGISTERED_RUBRIC_SHA256 = "cdf55ce0b08712df162423873686e8821d3daa019926ae666bbcd1e15b29b262"       # rubric_v2.py tras el registro técnico posterior (atestiguado por el addendum)
OFFICIAL_RV = "gold-v2-cand-A+incl-ge1+samples+panel-arq-ac1-maj-tie0-v2"
REGISTRATION_ADDENDUM = PREREG.parent / "addendum_rule_registration_2026-09-27.json"


def _sealed_rubric_source() -> bytes:
    """`rubric_v2.py` tal como está en el commit de sellado (`git show`). Sin git o sin ese commit en el entorno la prueba se OMITE de forma explícita; los hashes literales se comprueban aparte."""
    try:
        return subprocess.run(["git", "-C", str(pr.iso.REPO), "show", f"{SEALING_COMMIT}:{RUBRIC_IN_GIT}"], capture_output=True, check=True, timeout=30).stdout
    except (OSError, subprocess.SubprocessError):
        pytest.skip(f"git o el commit de sellado {SEALING_COMMIT[:7]} no están disponibles en este entorno")


def test_the_hash_recorded_for_rubric_v2_is_the_content_committed_at_the_sealing_commit(prereg):
    assert prereg["code_modules_at_fixing"][RUBRIC] == SEALED_RUBRIC_SHA256
    assert hashlib.sha256(_sealed_rubric_source()).hexdigest() == SEALED_RUBRIC_SHA256               # git show 5d7d12c:… coincide con lo registrado en el pre-registro


def test_rubric_v2_is_the_only_module_with_drift_since_the_sealing_and_it_is_attested(prereg):
    stored, now = prereg["code_modules_at_fixing"], rp.module_fingerprints()
    assert set(stored) == set(now) and pr.code_modules_drift(PREREG) == [RUBRIC]
    assert {m for m in stored if m != RUBRIC and stored[m] != now[m]} == set()                       # ningún otro módulo sellado deriva
    assert now[RUBRIC] == REGISTERED_RUBRIC_SHA256 != stored[RUBRIC]
    add = json.loads(REGISTRATION_ADDENDUM.read_text(encoding="utf-8"))
    assert pr.verify_addendum(REGISTRATION_ADDENDUM) == []                                           # el addendum apunta al pre-registro intacto y su evidencia coincide con el disco
    assert add["changes_methodology"] is False and add["preregistration"]["sha256"] == PREREG_SHA256
    assert add["evidence_root"] == "adaptation_swarm" and add["evidence_files"] == {RUBRIC: REGISTERED_RUBRIC_SHA256}


def _executable_without_registry_value(src: bytes):
    """AST del módulo sin su docstring y con el VALOR de `APPROVED_RULE_VERSIONS` neutralizado; devuelve también ese valor (constructor y argumentos literales)."""
    tree = ast.parse(src.decode("utf-8"))
    body = tree.body[1:] if isinstance(tree.body[0], ast.Expr) and isinstance(tree.body[0].value, ast.Constant) else tree.body
    registry = []
    for node in body:
        if isinstance(node, ast.AnnAssign) and getattr(node.target, "id", None) == "APPROVED_RULE_VERSIONS":
            registry.append((node.value.func.id, [ast.literal_eval(a) for a in node.value.args]))
            node.value = ast.Constant("<registro>")
    return [ast.dump(n) for n in body], registry


def test_the_rubric_v2_drift_is_exactly_the_technical_registration_and_its_immediate_documentation():
    sealed, current = _sealed_rubric_source(), (Path(rp.__file__).resolve().parent.parent / RUBRIC).read_bytes()
    code_then, registry_then = _executable_without_registry_value(sealed)
    code_now, registry_now = _executable_without_registry_value(current)
    assert code_then == code_now                                                                     # el código ejecutable es idéntico salvo el valor del registro
    assert registry_then == [("frozenset", [])] and registry_now == [("frozenset", [{OFFICIAL_RV}])]  # de vacío a exactamente la regla aprobada, sin otra
    old, new = sealed.decode("utf-8").splitlines(), current.decode("utf-8").splitlines()
    regions = [(old[i1:i2], new[j1:j2]) for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, old, new, autojunk=False).get_opcodes() if tag != "equal"]
    assert len(regions) == 2 and all("APPROVED_RULE_VERSIONS" in "\n".join(o + n) for o, n in regions)   # solo la docstring y el comentario+constante del registro


# ── F · addendum de la evidencia de Python 3.12.14 (archivo aparte; el original no se toca) ────────────────────────
ADDENDUM = PREREG.parent / "addendum_python312_2026-09-26.json"


def test_the_python_312_addendum_exists_points_to_the_original_and_changes_no_methodology():
    add = json.loads(ADDENDUM.read_text(encoding="utf-8"))
    assert add["changes_methodology"] is False and add["preregistration"]["sha256"] == PREREG_SHA256 == hashlib.sha256(PREREG.read_bytes()).hexdigest()
    assert pr.verify_addendum(ADDENDUM) == []
    su = add["summary"]
    assert su["environments"]["python_3_12"]["python"].startswith("3.12.") and su["environments"]["python_3_12"]["numpy"] == su["environments"]["python_3_14"]["numpy"]
    assert su["batch_seeds_master_26092601_equal"] and su["rng_pcg64_fingerprints_equal"] and su["library_v10_identity_equal"] and su["dataset_identity_equal"] and su["preregistration_drift_in_python_3_12"] == []
    assert su["historical_replay"]["corrida-poc-1"]["all_match_historical"] and su["historical_replay"]["corrida-poc-2"]["identical_to_python_3_14"]
    assert su["imports_ok"] == {"python_3_12": 23, "python_3_14": 23, "total": 23}
    assert any("R + irrCAC" in x for x in add["not_covered_by_this_addendum"]) and any("APPROVED_RULE_VERSIONS" in x for x in add["not_covered_by_this_addendum"])


def test_addendum_verification_detects_tampering(tmp_path):
    add = json.loads(ADDENDUM.read_text(encoding="utf-8"))
    for name, mutate in (("sha", lambda d: d["preregistration"].update({"sha256": "0" * 64})), ("meth", lambda d: d.update({"changes_methodology": True})),
                         ("evi", lambda d: d["evidence_files"].update({"result_python_3.12.14.json": "0" * 64})), ("gone", lambda d: d["evidence_files"].update({"no_existe.json": "0" * 64}))):
        forged = json.loads(json.dumps(add))
        mutate(forged)
        f = tmp_path / f"{name}.json"
        f.write_text(json.dumps(forged), encoding="utf-8")
        assert pr.verify_addendum(f), name


# ── G · inclusión y agregación: cobertura por los fingerprints de módulos existentes (evidencia; sin nueva decisión) ──
def test_inclusion_and_aggregation_are_covered_by_the_existing_module_fingerprints(prereg):
    pkg = Path(rp.__file__).resolve().parent.parent
    now = rp.module_fingerprints()
    for module in ("gold/rubric_v2.py", "gold/f1_multilabel.py", "gold/labels_v2.py"):
        assert module in now and module in prereg["code_modules_at_fixing"]
    for module in ("gold/f1_multilabel.py", "gold/labels_v2.py"):
        assert prereg["code_modules_at_fixing"][module] == hashlib.sha256((pkg / module).read_bytes()).hexdigest()      # estos coinciden con los de la fijación
    assert prereg["code_modules_at_fixing"][RUBRIC] == SEALED_RUBRIC_SHA256 and now[RUBRIC] == REGISTERED_RUBRIC_SHA256   # rubric_v2: sellado + registro técnico posterior (ver las pruebas de drift)
    assert 'InclusionRule("incl-ge1", "threshold", 1,' in (pkg / "gold" / "rubric_v2.py").read_text(encoding="utf-8")        # la regla de inclusión vive en un módulo fingerprintado
    assert 'OFFICIAL_AGGREGATION = "samples"' in (pkg / "gold" / "rubric_v2.py").read_text(encoding="utf-8")
    assert "def official_f1_adapt" in (pkg / "gold" / "f1_multilabel.py").read_text(encoding="utf-8")                           # y su implementación (samples) en otro
    assert set(pr.code_modules_drift(PREREG)) <= {RUBRIC}                                                                        # y solo rubric_v2 difiere de la fijación (registro técnico atestiguado)
