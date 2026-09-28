"""PRE-FLIGHT de K=10 (solo lectura: no escribe nada, no ejecuta réplicas). Uso: python k10_preflight.py <out_dir_futuro>. Sale con código 1 si cualquier gate falla."""
import hashlib, json, sys
from pathlib import Path
sys.dont_write_bytecode = True
from adaptation_swarm.analysis import preregistration as pr, replicas as rp
from adaptation_swarm.gold import rubric_v2 as r
from adaptation_swarm.multimodal.versioning import manifest_hash  # noqa: F401  (import de verificación)
from adaptation_swarm.tools import isolated_env as iso

EXPECT = {"head": "5a1fe3b2fcfa34d5a3a920a01a6b1a30fc7d79a5", "prereg_sha": "9e8cd2360b38172d6ddbacee532985970a703f16746bf981c046e0230e714928",
          "dataset_sha": "005b5a82ae85b4e83e1b9a931578fd60e9c6789a6e407928fdba6674fc1ccd15", "lib_manifest_sha": "89716455a14c2674a3a6a93bf1609be2c0cf83ed62ae654b2832b7038543a0ab",
          "rubric_sha": "cdf55ce0b08712df162423873686e8821d3daa019926ae666bbcd1e15b29b262", "rule": "gold-v2-cand-A+incl-ge1+samples+panel-arq-ac1-maj-tie0-v2",
          "master_seed": 26092601, "k": 10, "lib": "lib-v10-5dd83cd4", "python_series": "3.12", "numpy": "2.5.3", "scipy": "1.18.1"}
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
out_dir = Path(sys.argv[1]); results = []
def gate(name, ok, detail=""):
    results.append((name, bool(ok), detail)); print(("PASS " if ok else "FAIL ") + name + (f"  [{detail}]" if detail else ""))

prereg = json.loads(pr.DEFAULT_PATH.read_text(encoding="utf-8"))
rule = r.get_rule(*pr.OFFICIAL_RULE)
env = rp.environment(); cv = rp.code_version()
gate("G01 HEAD == 5a1fe3b (leído de .git, sin binario git)", cv["commit"] == EXPECT["head"], cv["commit"])
gate("G02 Python 3.12.x", env["python"].startswith(EXPECT["python_series"] + "."), env["python"])
gate("G03 numpy/scipy == pines del preregistro", (env["numpy"], env["scipy"]) == (EXPECT["numpy"], EXPECT["scipy"]) == (prereg["environment_required"]["numpy"], prereg["environment_required"]["scipy"]), f'{env["numpy"]}/{env["scipy"]}')
gate("G04 regla oficial aprobada y única en el registro", r.is_approved(rule) and r.APPROVED_RULE_VERSIONS == frozenset({EXPECT["rule"]}) and r.official_version(rule) == EXPECT["rule"])
gate("G05 sha del preregistro", sha(pr.DEFAULT_PATH) == EXPECT["prereg_sha"])
gate("G06 verify_preregistration(deep=True) == []", pr.verify_preregistration(deep=True) == [], str(pr.verify_preregistration(deep=True))[:80])
drift = pr.code_modules_drift(); now = rp.module_fingerprints()
gate("G07 drift de código == ['gold/rubric_v2.py'] con el hash registrado", drift == ["gold/rubric_v2.py"] and now["gold/rubric_v2.py"] == EXPECT["rubric_sha"], str(drift))
pre = json.loads((pr.DEFAULT_PATH.parent / "addendum_presealing_2026-09-27.json").read_text(encoding="utf-8"))["B_sealed_code"]["methodological_chain_outside_fingerprint"]
bad = [p for p, h in pre.items() if sha(Path(iso.BACK) / "adaptation_swarm" / p) != h]
gate("G08 cadena metodológica fuera del fingerprint (18) sin cambios", not bad, str(bad))
add = pr.DEFAULT_PATH.parent / "addendum_rule_registration_2026-09-27.json"
gate("G09 verify_addendum(registro) == []", pr.verify_addendum(add) == [])
gate("G10 dataset sha y 100 perfiles", sha(rp.DEFAULT_PROFILES) == EXPECT["dataset_sha"] and len(rp.read_dataset(rp.DEFAULT_PROFILES)) == rp.N_PROFILES_OFFICIAL == 100)
lib = pr.library_record(EXPECT["lib"], deep=True)
gate("G11 manifest lib-v10 e integridad de 1080 artefactos", lib["manifest_sha256"] == EXPECT["lib_manifest_sha"] and lib["integrity"]["ok"] and lib["integrity"]["artifacts"] == 1080, str(lib["integrity"]))
seeds = rp.derive_batch_seeds(EXPECT["master_seed"], EXPECT["k"])
gate("G12 semilla maestra, K=10 y 10 seeds == sellados y distintos", seeds == prereg["batch_seeds"] and len(set(seeds)) == 10 and prereg["master_seed"] == EXPECT["master_seed"] and prereg["k"] == 10)
plan = rp.build_plan(master_seed=EXPECT["master_seed"], k=EXPECT["k"], library_version=EXPECT["lib"], rule=rule, provisional=False)      # EN MEMORIA: no escribe
gate("G13 plan OFICIAL (en memoria) coincide con el preregistro", plan["status"] == "OFICIAL" and pr.check_plan_matches_preregistration(plan, prereg) == [], str(pr.check_plan_matches_preregistration(plan, prereg))[:80])
gate("G14 plan.environment == environment_required del preregistro (NO lo comprueba el ejecutor)", plan["environment"]["python"].startswith("3.12.") and plan["environment"]["numpy"] == prereg["environment_required"]["numpy"] and plan["environment"]["scipy"] == prereg["environment_required"]["scipy"])
gate("G15 revalidate_plan(plan) == OFICIAL", rp.revalidate_plan(plan) == "OFICIAL")
gate("G16 plan.modules == módulos registrados salvo rubric_v2", all(plan["modules"][m] == prereg["code_modules_at_fixing"][m] for m in prereg["code_modules_at_fixing"] if m != "gold/rubric_v2.py"))
try:
    iso.check_new_output_targets([out_dir / "plan.json", out_dir / "manifest.json"]); ok, d = not out_dir.exists(), str(out_dir)
except SystemExit as e:
    ok, d = False, str(e)
gate("G17 directorio de salida NUEVO y permitido (no results/, datasets/, paquetes, adaptation_swarm/, loadtest/results/)", ok, d)
gate("G18 el padre del destino existe y es escribible", out_dir.parent.is_dir() and __import__("os").access(out_dir.parent, __import__("os").W_OK), str(out_dir.parent))
print("\nRESUMEN:", sum(1 for _, ok, _ in results if ok), "PASS /", len(results)); sys.exit(0 if all(ok for _, ok, _ in results) else 1)
