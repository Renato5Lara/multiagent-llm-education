"""Driver del ANÁLISIS OFICIAL K=10. NO implementa estadística propia: llama a `replica_evaluation.evaluate(official=True)` y a `write_evaluation`, y PROYECTA sus campos.
Lo único que calcula es la condición externa de la NOTA-PREANALISIS §4.1: approved_test_criterion = (p < alpha) AND (mean > 0.85), leyendo `p_value` y `mean` de la salida sellada."""
import datetime, hashlib, json, os, platform, shutil, sys
from pathlib import Path
sys.dont_write_bytecode = True
from adaptation_swarm.analysis import inference, replica_evaluation as ev, replicas as rp, preregistration as pr

RUNS, OUT, NOTE = Path("/work/backend/official_runs/k10_official_2026-09-27"), Path(sys.argv[1]) if len(sys.argv) > 1 else None, Path("/note/NOTA-PREANALISIS-K10-2026-09-27.md")
RV = "gold-v2-cand-A+incl-ge1+samples+panel-arq-ac1-maj-tie0-v2"
PENDING = "PENDIENTE"


def derive(evaluation: dict) -> dict:
    """Comparación y RNF-03 según la nota (§4.1, §4). Solo LEE campos de la salida sellada; no recalcula nada."""
    t, c, ci = evaluation["inference"], evaluation["criterion"], evaluation["ci95"]
    p, mean = t["p_value"], t["mean"]
    approved = None if p is None else bool(p < inference.ALPHA and mean > inference.BENCHMARK_F1)
    code_pass = t["statistical_pass"]
    ci_pass = c["ci_pass"]
    rnf03 = None if approved is None else bool(ci_pass and approved)
    label = lambda v: "INDETERMINADO" if v is None else ("CUMPLE" if v else "NO CUMPLE")
    return {
        "code_output": {"statistical_pass": code_pass, "verdict": c["verdict"], "combined_pass": c["combined_pass"], "p_value": p, "mean": mean, "test": t["test"], "status": t["status"]},
        "condition_mean_gt_benchmark": None if mean is None else bool(mean > inference.BENCHMARK_F1),
        "approved_test_criterion": approved, "code_and_approved_agree": code_pass == approved,
        "approved_rule": f"p < {inference.ALPHA} AND mean > {inference.BENCHMARK_F1} (Consulta 4, DEC-F1-TEST)",
        "CI_PASS": ci_pass, "ci_lower": ci["lower"], "ci_lower_ge_benchmark_check": bool(ci["lower"] >= inference.BENCHMARK_F1) == ci_pass,
        "RNF03": rnf03, "RNF03_label": label(rnf03), "RNF03_rule": "CI_PASS AND approved_test_criterion (Consulta 5, DEC-RNF03); INDETERMINADO si la prueba lo es",
        "when_code_and_approved_differ": "se reportan ambos; para RNF-03 prevalece la regla aprobada (nota §4.1)",
        "RNF02": "PENDIENTE / NO DETERMINADO (solo descriptivo; sin regla metodológica formal — nota §5)",
        "RNF01": PENDING + " (experimento full-stack; K=10 no lo mide)", "RNF04": PENDING + " (experimento full-stack; K=10 no lo mide)", "RNF05": PENDING + " (SUS: evaluación humana)",
        "H1": {"F1_RNF03": label(rnf03), "L_resp_lt_2s": PENDING, "SUS_gt_75": PENDING, "H1_declared": "NO (componentes pendientes; la hipótesis es conjuntiva)"}}


if __name__ == "__main__":
    sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
    t0 = datetime.datetime.now(datetime.timezone.utc)
    evaluation = ev.evaluate(RUNS, official=True)                       # exige manifiesto OFICIAL, regla aprobada, K=10 y 100 perfiles; verifica integridad y f1 almacenado
    derived = derive(evaluation)
    ev.write_evaluation(evaluation, OUT)                                # crea OUT (nuevo) con evaluation.json
    def put(name, obj):
        with (OUT / name).open("x", encoding="utf-8") as fh:
            fh.write(json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False) + "\n")
    m = json.loads((RUNS / "manifest.json").read_text())
    P = json.loads(pr.DEFAULT_PATH.read_text())
    inputs = {f: sha(RUNS / f) for f in ["plan.json", "manifest.json"] + [f"replica_{i:02d}.json" for i in range(10)]}
    put("01_metadata.json", {"analysis": "k10-official-analysis-v1", "results_commit": "3088e6912885376baba2de30a8940fa0c3453e20", "sealing_commit": "5d7d12c9776a62d1234afb71acb505cd84cb5872",
                             "run_commit": m["code_version"]["commit"], "rule_version": evaluation["rule_version"], "aggregation": evaluation["aggregation"], "k": evaluation["k"], "n_profiles": evaluation["n_profiles"],
                             "master_seed": m["master_seed"], "batch_seeds": m["batch_seeds"], "dataset_sha256": m["dataset"]["sha256"], "library": m["library"], "preregistration_sha256": sha(pr.DEFAULT_PATH),
                             "gold_fingerprint": m["rule"]["gold_fingerprint"], "panel_protocol_fingerprint": m["protocol"]["panel_protocol_fingerprint"], "status": evaluation["status"],
                             "statistical_unit": evaluation["statistical_unit"], "pre_analysis_note_sha256": sha(NOTE), "driver_sha256": sha(Path(__file__)), "preflight_sha256": sha(Path(__file__).with_name("analysis_preflight.py")),
                             "started_utc": t0.isoformat(timespec="seconds"), "scope": evaluation["scope"]})
    put("02_f1_adapt_by_replica.json", {"f1_adapt_by_replica": [{"replica": i, "batch_seed": m["batch_seeds"][i], "f1_adapt": v} for i, v in enumerate(evaluation["f1_adapt_by_replica"])]})
    put("03_summary_k10_ci95.json", {"n": evaluation["ci95"]["k"], "ci95": evaluation["ci95"], "CI_PASS": derived["CI_PASS"], "criterion_from_code": evaluation["criterion"]})
    put("04_profile_aggregation.json", evaluation["profile_means"])
    inf = evaluation["inference"]
    put("05_shapiro_wilk.json", {k: inf[k] for k in ("n", "alpha", "shapiro_w", "shapiro_p", "normal")} | {"note": "solo determina t vs Wilcoxon (preregistro)"})
    put("06_inferential_test.json", inf)
    put("07_code_vs_approved_criterion.json", {k: derived[k] for k in ("code_output", "condition_mean_gt_benchmark", "approved_test_criterion", "code_and_approved_agree", "approved_rule", "when_code_and_approved_differ")})
    put("08_rnf03.json", {k: derived[k] for k in ("CI_PASS", "ci_lower", "ci_lower_ge_benchmark_check", "approved_test_criterion", "RNF03", "RNF03_label", "RNF03_rule")})
    put("09_convergence_descriptive.json", {"convergence": evaluation["convergence"], "RNF02": derived["RNF02"]})
    put("10_descriptives_modality_archetype.json", {"by_modality": evaluation["by_modality"], "by_archetype": evaluation["by_archetype"], "note": "DESCRIPTIVOS; ningún criterio de aceptación/rechazo"})
    put("11_input_hashes.json", {"results": inputs, "preregistration": sha(pr.DEFAULT_PATH), "dataset": m["dataset"]["sha256"], "library_manifest": m["library"]["manifest_sha256"], "gold_fingerprint": m["rule"]["gold_fingerprint"],
                                 "pre_analysis_note": sha(NOTE), "analysis_modules": evaluation["provenance"]["evaluation_modules"], "plan_sha256": m["plan_sha256"]})
    put("12_environment.json", {"python": platform.python_version(), "implementation": platform.python_implementation(), "numpy": rp.environment()["numpy"], "scipy": rp.environment()["scipy"], "platform": platform.platform(),
                                "image_id": os.environ.get("K10_IMAGE_ID"), "lock_sha256": sha("/prep/requirements-k10.lock"), "code_version_at_analysis": rp.code_version()})
    put("13_status_rnf_h1.json", {k: derived[k] for k in ("RNF01", "RNF02", "RNF04", "RNF05", "H1")} | {"RNF03": derived["RNF03_label"]})
    (OUT / "inputs_and_scripts").mkdir()
    for src, name in ((NOTE, NOTE.name), (Path(__file__), "analysis_driver.py"), (Path(__file__).with_name("analysis_preflight.py"), "analysis_preflight.py")):
        shutil.copyfile(src, OUT / "inputs_and_scripts" / name)
    files = sorted(p.relative_to(OUT).as_posix() for p in OUT.rglob("*") if p.is_file())
    put("ANALYSIS_MANIFEST.json", {"schema": "k10-analysis-manifest-v1", "finished_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"), "command": "python analysis_driver.py <out_dir>  (evaluate(official=True) + write_evaluation)",
                                   "outputs_sha256": {f: sha(OUT / f) for f in files}, "n_outputs": len(files), "results_modified": False, "replicas_used": 10, "profiles_per_replica": 100})
    files = sorted(p.relative_to(OUT).as_posix() for p in OUT.rglob("*") if p.is_file())
    with (OUT / "SHA256SUMS").open("x", encoding="utf-8") as fh:
        fh.write("".join(f"{sha(OUT / f)}  {f}\n" for f in files))
    print("análisis escrito en", OUT, "|", len(files) + 1, "archivos")
