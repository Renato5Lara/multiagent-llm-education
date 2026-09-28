"""Verificación de INTEGRIDAD TÉCNICA de las 10 réplicas oficiales (solo lectura). NO calcula F1 agregado, estadísticos ni interpreta resultados."""
import hashlib, json, sys
from pathlib import Path
sys.dont_write_bytecode = True
from adaptation_swarm.analysis import preregistration as pr, replicas as rp
from adaptation_swarm.schemas.ids import derive_seed
OUT = Path(sys.argv[1]); RV = "gold-v2-cand-A+incl-ge1+samples+panel-arq-ac1-maj-tie0-v2"
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
res = []
def chk(n, c, d=""):
    res.append(bool(c)); print(("PASS " if c else "FAIL ") + n + (f"  [{d}]" if d else ""))
prereg = json.loads(pr.DEFAULT_PATH.read_text(encoding="utf-8"))
files = sorted(p.name for p in OUT.iterdir()); expected = sorted(["plan.json", "manifest.json"] + [f"replica_{i:02d}.json" for i in range(10)])
chk("I01 archivos == plan + manifest + 10 réplicas, sin extras ni subdirectorios", files == expected and all(p.is_file() for p in OUT.iterdir()), f"{len(files)} archivos")
docs = {}
try:
    for f in expected: docs[f] = json.loads((OUT / f).read_text(encoding="utf-8"))
    chk("I02 los 12 archivos se leen como JSON válido", True)
except Exception as e:
    chk("I02 los 12 archivos se leen como JSON válido", False, repr(e)); sys.exit(1)
m, plan = docs["manifest.json"], docs["plan.json"]
chk("I03 rp.verify(out) == [] (verificador existente: hashes de réplicas y plan vs manifiesto)", rp.verify(OUT) == [], str(rp.verify(OUT)))
chk("I04 manifest: schema, status OFICIAL, master_seed 26092601, k 10", (m["schema"], m["status"], m["master_seed"], m["k"]) == (rp.SCHEMA_MANIFEST, "OFICIAL", 26092601, 10))
seeds = prereg["batch_seeds"]
chk("I05 batch_seeds del manifiesto == 10 seeds sellados, distintos, en orden", m["batch_seeds"] == seeds == rp.derive_batch_seeds(26092601, 10) and len(set(seeds)) == 10)
chk("I06 manifest.replicas: índices 0..9, batch_seed y n_cases=100 por réplica",
    [(e["index"], e["batch_seed"], e["file"], e["n_cases"]) for e in m["replicas"]] == [(i, seeds[i], f"replica_{i:02d}.json", 100) for i in range(10)])
chk("I07 sha256 de cada réplica recalculado == manifiesto", all(sha(OUT / e["file"]) == e["sha256"] for e in m["replicas"]))
chk("I08 plan_sha256 del manifiesto == sha256(plan.json)", m["plan_sha256"] == sha(OUT / "plan.json"))
chk("I09 plan.json == plan reconstruido a partir del preregistro (check_plan_matches_preregistration == [])", pr.check_plan_matches_preregistration(plan, prereg) == [], str(pr.check_plan_matches_preregistration(plan, prereg))[:80])
same = all(m[k] == plan[k] for k in ("master_seed", "k", "batch_seeds", "config", "library", "dataset", "rule", "protocol", "scope", "code_version", "environment", "modules"))
chk("I10 manifiesto y plan coinciden en todos los campos compartidos", same)
chk("I11 identidad: biblioteca, dataset (100 perfiles, no limitado) y regla oficial aprobada",
    m["library"] == {"version": "lib-v10-5dd83cd4", "manifest_sha256": prereg["library"]["manifest_sha256"]} and m["dataset"]["sha256"] == prereg["dataset"]["sha256"]
    and m["dataset"]["n_used"] == m["dataset"]["n_profiles"] == 100 and m["dataset"]["limited"] is False
    and m["rule"]["official_version"] == RV and m["rule"]["status"] == "OFICIAL" and m["rule"]["gold_fingerprint"] == prereg["rule"]["gold_fingerprint"])
chk("I12 código y entorno registrados: commit 5a1fe3b, Python 3.12.14, numpy/scipy, módulos == fijación salvo rubric_v2 (hash actual)",
    m["code_version"]["commit"] == "5a1fe3b2fcfa34d5a3a920a01a6b1a30fc7d79a5" and m["environment"] == {"python": "3.12.14", "implementation": "CPython", "numpy": "2.5.3", "scipy": "1.18.1"}
    and m["modules"]["gold/rubric_v2.py"] == "cdf55ce0b08712df162423873686e8821d3daa019926ae666bbcd1e15b29b262"
    and all(m["modules"][k] == v for k, v in prereg["code_modules_at_fixing"].items() if k != "gold/rubric_v2.py"), f'dirty={m["code_version"]["dirty"]}')
ids = [p.profile_id for p in rp.read_dataset(rp.DEFAULT_PROFILES)]
KEYS = {"profile_id", "archetype", "difficulty", "concept_id", "seed", "S", "F", "k_stop", "stop_reason", "f1"}
all_seeds, bad = [], []
for i in range(10):
    d = docs[f"replica_{i:02d}.json"]; cs = d["cases"]
    ok = (d["schema"] == rp.SCHEMA_REPLICA and d["replica_id"] == d["replica_index"] == i and d["batch_seed"] == seeds[i] and d["library_version"] == "lib-v10-5dd83cd4"
          and d["config_hash"] == plan["config"]["config_hash"] and d["provenance"]["rule_version"] == RV and d["provenance"]["dataset_sha256"] == prereg["dataset"]["sha256"]
          and d["provenance"]["library_manifest_sha256"] == prereg["library"]["manifest_sha256"] and d["provenance"]["code_version"]["commit"] == m["code_version"]["commit"]
          and len(cs) == 100 and [c["profile_id"] for c in cs] == ids and all(KEYS <= set(c) for c in cs)
          and all(c["seed"] == derive_seed(seeds[i], c["profile_id"], 0) for c in cs) and all(isinstance(c["S"], list) and len(c["S"]) == 8 for c in cs))
    all_seeds += [c["seed"] for c in cs]
    if not ok: bad.append(i)
chk("I13 cada réplica: estructura, procedencia, 100 casos en el orden del dataset, campos completos y seed de ciclo == derive_seed(batch_seed, perfil, 0)", not bad, f"réplicas con problema: {bad}")
chk("I14 semillas de ciclo: 1000 en total, todas distintas; == n_case_seeds del manifiesto", len(all_seeds) == 1000 == len(set(all_seeds)) == m["n_case_seeds"] == m["n_distinct_case_seeds"])
chk("I15 ninguna semilla de lote histórica ni de prueba", not (set(seeds) & rp.HISTORICAL_BATCH_SEEDS) and 424242 not in (m["master_seed"],))
print("\nRESUMEN INTEGRIDAD:", sum(res), "PASS /", len(res)); sys.exit(0 if all(res) else 1)
