"""Auditoría DIAGNÓSTICA de F1_adapt de una corrida ya ejecutada (solo lectura: no modifica gold, dataset, PSO ni la
corrida). Objetivo: explicar de dónde sale el F1 medido (implementación, gold, predicción, distribución o límite del
algoritmo) SIN tocar nada para subirlo.

REQUIERE PostgreSQL: lee `swarm_runs`, `swarm_profiles` y `swarm_cycles` de la corrida (transacción `READ ONLY`; no escribe en la base) y la biblioteca M1 (solo lectura, sin audio).
Solo opera sobre la base AISLADA de pruebas (tests/adaptation_swarm/integration_env/), con `DATABASE_URL` EXPLÍCITA en el entorno (no se lee backend/.env); rechaza desarrollo y producción.
No usa Redis, OpenAI ni subprocesos. Escribe únicamente en `--out-dir` (obligatorio; nunca `experiments/results/`, resultados congelados) y sin sobrescribir.

Uso (desde backend/):
    export DATABASE_URL=postgresql+psycopg://swarm_test:…@127.0.0.1:55432/swarm_test
    python -m adaptation_swarm.analysis.f1_audit --run-label corrida-poc-1 --out-dir /ruta/nueva [--out-md /ruta/nueva/f1.md]
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from sqlalchemy import select, text

from adaptation_swarm.fitness.fitness import FitnessWeights
from adaptation_swarm.gold.f1 import f1_report
from adaptation_swarm.gold.rubric import GOLD_TABLE, dominant_modality, predicted_dominant
from adaptation_swarm.multimodal.library import LibraryStore
from adaptation_swarm.config import SETTINGS
from adaptation_swarm.profiles.models import Archetype, Difficulty, ModalityWeights
from adaptation_swarm.pso.space import MODALITIES, all_configurations
from adaptation_swarm.fitness.coher import coher
from adaptation_swarm.fitness.costt import costt
from adaptation_swarm.fitness.fitness import evaluate
from adaptation_swarm.fitness.redund import redund
from adaptation_swarm.tools import isolated_env as iso


def _optimal_labels(store, concept_id, W: ModalityWeights, fw: FitnessWeights):
    """Etiquetas predichas por TODAS las configuraciones que alcanzan el óptimo global de 𝓕."""
    anchor, table = store.anchor(concept_id), store.calibration()
    memo, best, labs = {}, -1e18, []
    for cfg in all_configurations():
        v = cfg.variants
        if v not in memo:
            vc, vd, vt, va = v
            code, dia, txt = store.code(concept_id, vc).text, store.diagram(concept_id, vc, vd).text, store.text(concept_id, vt).text
            memo[v] = (coher(anchor, code, dia, txt).value, redund(anchor, code, dia, txt), costt(v, table))
        f = evaluate(cfg, W.by_modality(), *memo[v], fw).F
        lab = predicted_dominant(cfg.emphasis)
        if f > best + 1e-12:
            best, labs = f, [lab]
        elif abs(f - best) <= 1e-12:
            labs.append(lab)
    return best, Counter(labs)


def load_cases(run_label: str):
    from app.db.session import SessionLocal            # importar aquí: la app fija el destino al importarse y antes se verifica el destino aislado
    from app.models.swarm_adaptation import SwarmCycle, SwarmProfile, SwarmRun

    with SessionLocal() as s:
        s.execute(text("SET TRANSACTION READ ONLY"))    # primera sentencia: la base rechaza cualquier escritura
        run = s.get(SwarmRun, run_label)
        prof = {p.profile_id: p for p in s.scalars(select(SwarmProfile).where(SwarmProfile.dataset_version == run.dataset_version))}
        cycles = list(s.scalars(select(SwarmCycle).where(SwarmCycle.run_label == run_label)))
        cases = []
        for c in cycles:
            p = prof[c.profile_id]
            cases.append({"profile_id": c.profile_id, "archetype": p.archetype, "difficulty": p.difficulty,
                          "concept_id": c.concept_id, "concept": p.payload["metadata"]["concept_title"],
                          "gold": p.gold_label, "pred_stored": c.predicted_dominant, "S": c.g_best_S, "W": c.W,
                          "F": c.g_best_F, "k_stop": c.k_stop, "status": c.status})
        return run, cases


def audit(run_label: str, library_version: str | None = None) -> dict:
    run, cases = load_cases(run_label)
    store = LibraryStore.open(SETTINGS.library_root, library_version or run.library_version)
    fw = FitnessWeights(**run.config["fitness_weights"])
    ok = [c for c in cases if c["status"] == "completed"]
    # 1) ¿la implementación recomputa lo almacenado?  (etiqueta desde S; gold desde la tabla)
    bug_pred = [c["profile_id"] for c in ok if predicted_dominant([c["S"][0], c["S"][2], c["S"][4], c["S"][6]]) != c["pred_stored"]]
    bug_gold = [c["profile_id"] for c in ok
                if GOLD_TABLE[(Archetype(c["archetype"]), Difficulty(c["difficulty"]))] != c["gold"]]
    pairs = [(c["gold"], c["pred_stored"]) for c in ok]
    rep = f1_report(pairs)
    # 2) ¿la matriz recomputada por otro camino coincide?
    idx = {m: i for i, m in enumerate(MODALITIES)}
    cm2 = np.zeros((4, 4), int)
    for g, p in pairs:
        cm2[idx[g], idx[p]] += 1
    # 3) atribución de cada error
    for c in ok:
        W = ModalityWeights(**c["W"])
        c["w_argmax"] = dominant_modality(list(W.by_modality()))            # lo que Simil favorece por sí solo
        c["correct"] = c["gold"] == c["pred_stored"]
        best, labs = _optimal_labels(store, c["concept_id"], W, fw)
        c["opt_labels"] = dict(labs)
        c["opt_gold_reachable"] = c["gold"] in labs
    def cause(c):
        if c["correct"]:
            return "acierto"
        if c["w_argmax"] != c["gold"]:
            return "W(perfil) no favorece la modalidad gold (gold ≠ argmax W)"
        if not c["opt_gold_reachable"]:
            return "el óptimo global de 𝓕 no incluye la etiqueta gold (Coher/Redund/CostT dominan sobre Simil)"
        return "el óptimo de 𝓕 sí permite la etiqueta gold: la búsqueda del PSO no lo alcanzó"
    causes = Counter(cause(c) for c in ok)
    def breakdown(key):
        d = defaultdict(lambda: {"n": 0, "errors": 0})
        for c in ok:
            d[c[key]]["n"] += 1
            d[c[key]]["errors"] += 0 if c["correct"] else 1
        return {k: {**v, "error_rate": round(v["errors"] / v["n"], 3)} for k, v in sorted(d.items())}
    w_pairs = [(c["gold"], c["w_argmax"]) for c in ok]
    opt_pairs = [(c["gold"], Counter(c["opt_labels"]).most_common(1)[0][0]) for c in ok]
    return {
        "run_label": run_label, "library_version": store.version, "n": len(ok),
        "implementation_checks": {"prediction_recompute_mismatches": bug_pred, "gold_table_mismatches": bug_gold,
                                  "confusion_matrix_recompute_equal": bool((cm2 == rep.confusion).all()),
                                  "stored_f1_recomputed": rep.f1_adapt},
        "f1": rep.to_dict(),
        "tp_fp_fn_by_class": {m: {"TP": int(rep.confusion[i, i]), "FP": int(rep.confusion[:, i].sum() - rep.confusion[i, i]),
                                  "FN": int(rep.confusion[i, :].sum() - rep.confusion[i, i])} for i, m in enumerate(MODALITIES)},
        "errors_by_archetype": breakdown("archetype"), "errors_by_difficulty": breakdown("difficulty"),
        "errors_by_concept": breakdown("concept"), "errors_by_predicted_modality": {
            m: {"n": sum(1 for c in ok if c["pred_stored"] == m), "wrong": sum(1 for c in ok if c["pred_stored"] == m and not c["correct"])}
            for m in MODALITIES},
        "error_causes": dict(causes),
        "reference_bounds": {
            "f1_if_prediction_were_argmax_W": f1_report(w_pairs).f1_adapt,
            "f1_if_prediction_were_global_optimum_of_F(most_common_label)": f1_report(opt_pairs).f1_adapt,
            "f1_measured": rep.f1_adapt,
            "cases_where_gold_not_argmax_W": sum(1 for c in ok if c["w_argmax"] != c["gold"]),
            "cases_where_gold_unreachable_by_any_optimal_config": sum(1 for c in ok if not c["opt_gold_reachable"])},
        "error_cases": [{k: c[k] for k in ("profile_id", "archetype", "difficulty", "concept", "gold", "pred_stored", "w_argmax", "opt_labels", "S")}
                        for c in ok if not c["correct"]],
    }


def to_markdown(a: dict) -> str:
    f, ic = a["f1"], a["implementation_checks"]
    lines = [f"# Auditoría de F1_adapt — {a['run_label']} (solo diagnóstico; no modifica nada)", "",
             f"Biblioteca: `{a['library_version']}` · casos completados: {a['n']}", "",
             "## 1. ¿Implementación incorrecta?",
             f"- Recomputo de la etiqueta predicha desde S: **{len(ic['prediction_recompute_mismatches'])} discrepancias**.",
             f"- Etiqueta gold vs tabla preregistrada: **{len(ic['gold_table_mismatches'])} discrepancias**.",
             f"- Matriz de confusión recomputada por otro camino: **{'idéntica' if ic['confusion_matrix_recompute_equal'] else 'DIFERENTE'}**; "
             f"F1_adapt recomputado = {ic['stored_f1_recomputed']:.4f}.", "",
             "## 2. Matriz (filas gold, columnas predicción: code, diagram, text, audio)", "```", json.dumps(f["confusion"]), "```",
             "| clase | TP | FP | FN | precision | recall | F1 |", "|---|---|---|---|---|---|---|"]
    for m, v in a["tp_fp_fn_by_class"].items():
        pc = f["per_class"][m]
        fmt = lambda x: "—" if x is None else f"{x:.3f}"
        lines.append(f"| {m} | {v['TP']} | {v['FP']} | {v['FN']} | {fmt(pc['precision'])} | {fmt(pc['recall'])} | {fmt(pc['f1'])} |")
    lines += ["", "## 3. Errores por segmento", "", "| arquetipo | n | errores | tasa |", "|---|---|---|---|"]
    lines += [f"| {k} | {v['n']} | {v['errors']} | {v['error_rate']} |" for k, v in a["errors_by_archetype"].items()]
    lines += ["", "| dificultad | n | errores | tasa |", "|---|---|---|---|"]
    lines += [f"| {k} | {v['n']} | {v['errors']} | {v['error_rate']} |" for k, v in a["errors_by_difficulty"].items()]
    lines += ["", "| concepto | n | errores | tasa |", "|---|---|---|---|"]
    lines += [f"| {k} | {v['n']} | {v['errors']} | {v['error_rate']} |" for k, v in a["errors_by_concept"].items() if v["errors"]]
    lines += ["", "| modalidad predicha | n | equivocadas |", "|---|---|---|"]
    lines += [f"| {k} | {v['n']} | {v['wrong']} |" for k, v in a["errors_by_predicted_modality"].items()]
    rb = a["reference_bounds"]
    lines += ["", "## 4. Atribución de los errores", "", "| causa | casos |", "|---|---|"]
    lines += [f"| {k} | {v} |" for k, v in a["error_causes"].items()]
    lines += ["", "## 5. Cotas de referencia (mismo gold, misma definición)", "",
              f"- F1 si la predicción fuese `argmax W` (con el desempate declarado): **{rb['f1_if_prediction_were_argmax_W']:.3f}**",
              f"- F1 si la predicción fuese el **óptimo global de 𝓕** (fuerza bruta): **{rb['f1_if_prediction_were_global_optimum_of_F(most_common_label)']:.3f}**",
              f"- F1 medido: **{rb['f1_measured']:.3f}**",
              f"- Casos donde el gold ≠ argmax(W): {rb['cases_where_gold_not_argmax_W']} (ruido del muestreo de W / modulación frente al centroide del arquetipo)",
              f"- Casos donde ninguna configuración óptima de 𝓕 produce la etiqueta gold: {rb['cases_where_gold_unreachable_by_any_optimal_config']}", ""]
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser(description="Auditoría de solo lectura de F1_adapt de una corrida (REQUIERE PostgreSQL aislado; ver el docstring del módulo)")
    ap.add_argument("--run-label", required=True, help="corrida a auditar (puede ser una congelada: solo se lee)")
    ap.add_argument("--library-version")
    ap.add_argument("--out-dir", help="directorio NUEVO y explícito del JSON (obligatorio; nunca experiments/results/)")
    ap.add_argument("--out-md", help="ruta NUEVA del informe Markdown (opcional; no se sobrescribe)")
    args = ap.parse_args()
    out_dir = iso.require_out_dir(args.out_dir)
    json_path = out_dir / f"adaptation_swarm_{args.run_label}_f1_audit.json"
    iso.check_output_targets([json_path] + ([Path(args.out_md)] if args.out_md else []))     # antes de tocar la base
    iso.require_isolated_database()
    a = audit(args.run_label, args.library_version)
    out_dir.mkdir(parents=True, exist_ok=True)
    with json_path.open("x", encoding="utf-8") as fh:                                          # modo "x": nunca sobrescribe
        fh.write(json.dumps(a, indent=2, ensure_ascii=False))
    md = to_markdown(a)
    if args.out_md:
        with Path(args.out_md).open("x", encoding="utf-8") as fh:
            fh.write(md)
    print(md)


if __name__ == "__main__":
    main()
