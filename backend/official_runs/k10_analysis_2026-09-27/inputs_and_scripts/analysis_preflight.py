"""PRE-FLIGHT del análisis oficial K=10 (solo lectura; no calcula ningún estadístico ni F1). Exit 1 si algún gate falla."""
import hashlib, json, os, sys
from pathlib import Path
sys.dont_write_bytecode = True
from adaptation_swarm.analysis import preregistration as pr, replicas as rp
from adaptation_swarm.gold import rubric_v2 as r
RUNS, OUT, NOTE = Path("/work/backend/official_runs/k10_official_2026-09-27"), Path(sys.argv[1]), Path("/note/NOTA-PREANALISIS-K10-2026-09-27.md")
RV = "gold-v2-cand-A+incl-ge1+samples+panel-arq-ac1-maj-tie0-v2"
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
res = []
def gate(n, ok, d=""):
    res.append(bool(ok)); print(("PASS " if ok else "FAIL ") + n + (f"  [{d}]" if d else ""))
files = [RUNS / f for f in ["plan.json", "manifest.json"] + [f"replica_{i:02d}.json" for i in range(10)]]
gate("A01 HEAD (leído de .git) == 3088e69 (commit de resultados)", rp.code_version()["commit"] == "3088e6912885376baba2de30a8940fa0c3453e20", rp.code_version()["commit"][:8])
gate("A02 los 12 archivos oficiales existen", all(f.is_file() for f in files))
lines = [l.split(None, 1) for l in (RUNS / "evidence" / "results_SHA256SUMS.txt").read_text().strip().splitlines()]
gate("A03 hashes == results_SHA256SUMS.txt (12/12)", len(lines) == 12 and all(sha(RUNS / Path(p.strip()).name) == h for h, p in lines), f"{len(lines)} líneas")
m, plan = json.loads((RUNS / "manifest.json").read_text()), json.loads((RUNS / "plan.json").read_text())
P = json.loads(pr.DEFAULT_PATH.read_text())
gate("A04 manifest: K=10, 100 perfiles, seed 26092601, regla oficial, OFICIAL", (m["k"], m["dataset"]["n_used"], m["master_seed"], m["rule"]["official_version"], m["status"]) == (10, 100, 26092601, RV, "OFICIAL"))
gate("A05 dataset y biblioteca oficiales", m["dataset"]["sha256"] == "005b5a82ae85b4e83e1b9a931578fd60e9c6789a6e407928fdba6674fc1ccd15" and m["library"] == {"version": "lib-v10-5dd83cd4", "manifest_sha256": "89716455a14c2674a3a6a93bf1609be2c0cf83ed62ae654b2832b7038543a0ab"})
gate("A06 corrida hecha con commit 5a1fe3b y Python 3.12.14 / numpy 2.5.3 / scipy 1.18.1", m["code_version"]["commit"] == "5a1fe3b2fcfa34d5a3a920a01a6b1a30fc7d79a5" and (m["environment"]["python"], m["environment"]["numpy"], m["environment"]["scipy"]) == ("3.12.14", "2.5.3", "1.18.1"))
env = rp.environment()
gate("A07 el análisis corre en Python 3.12.14 / numpy 2.5.3 / scipy 1.18.1", (env["python"], env["numpy"], env["scipy"]) == ("3.12.14", "2.5.3", "1.18.1"), str(env))
gate("A08 preregistro sha == 9e8cd236…", sha(pr.DEFAULT_PATH) == "9e8cd2360b38172d6ddbacee532985970a703f16746bf981c046e0230e714928")
gate("A09 verify_preregistration(deep=True) == []", pr.verify_preregistration(deep=True) == [])
gate("A10 único drift == ['gold/rubric_v2.py']", pr.code_modules_drift() == ["gold/rubric_v2.py"], str(pr.code_modules_drift()))
gate("A11 gold fingerprint == 1f917a7a…", m["rule"]["gold_fingerprint"] == "1f917a7ae50648c75a0ac984ea3fce1628727f4f58b64f2d71e7f0c98387edd2" == r.get_rule("gold-v2-cand-A", "incl-ge1").gold.fingerprint())
gate("A12 regla oficial aprobada y única", r.is_approved(r.get_rule("gold-v2-cand-A", "incl-ge1")) and r.APPROVED_RULE_VERSIONS == frozenset({RV}))
gate("A13 rp.verify(official_runs) == []", rp.verify(RUNS) == [])
pre = json.loads((pr.DEFAULT_PATH.parent / "addendum_presealing_2026-09-27.json").read_text())["B_sealed_code"]
sealed = {**P["code_modules_at_fixing"], **{k: v for k, v in pre["methodological_chain_outside_fingerprint"].items()}}
mods = ["analysis/inference.py", "analysis/replica_evaluation.py", "gold/f1_multilabel.py", "gold/labels_v2.py", "pso/space.py", "profiles/archetypes.py", "profiles/models.py"]
bad = [x for x in mods if sha(Path(pr.iso.BACK) / "adaptation_swarm" / x) != sealed[x]]
gate("A14 módulos del análisis == sellados", not bad, str(bad))
gate("A15 nota de pre-análisis presente y sin cambios (sha 9ed7f1e5…)", NOTE.is_file() and sha(NOTE) == "9ed7f1e52e0db2dc41235b763c11879847f35924fa91f7922d96a8a287a343b5")
gate("A16 el directorio de salida NO existe y su padre es escribible", not OUT.exists() and os.access(OUT.parent, os.W_OK), str(OUT))
print("\nRESUMEN PRE-FLIGHT ANÁLISIS:", sum(res), "PASS /", len(res)); sys.exit(0 if all(res) else 1)
