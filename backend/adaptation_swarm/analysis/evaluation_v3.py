"""Evaluación de K = 10 v3 (capa ADITIVA; funciones puras, sin LLM, red, procesos ni BD). Consume las réplicas que prepara `analysis/replicas_v3.py` y la regla de `gold/rubric_v3.py`.
NO modifica ninguna pieza de v2 (`inference.py`, `f1_multilabel.py`, `replicas.py`, `rubric_v2.py`, `replica_evaluation.py`) ni ejecuta K = 10 v3.

P3 — agregación (aprobada; no se inventa otra): el F1 multietiqueta 4×4 con audio se evalúa POR CASO (Dice, F1_i = 2|G_i ∩ P_i| / (|G_i| + |P_i|); predicho vacío ⇒ 0) y `F1_adapt` de una réplica es la MEDIA del F1
por caso (agregación `samples`, `OFFICIAL_AGGREGATION`). Las cuatro matrices One-vs-Rest (code, diagram, text, audio: TP/FP/FN/TN, precisión, recall y F1) son DESCRIPTIVAS. El cálculo de la métrica es el de
`gold/f1_multilabel.py` (sin cambios: mismas definiciones que v2; lo único que cambia en v3 es la regla, P1 y P2); aquí no se reimplementa.

La regla se consume de `rubric_v3`: el conjunto esperado depende solo del arquetipo (P2; ni de la dificultad ni de W) y el predicho sale de la inclusión P1 (`e_m ≥ 1 ∧ e_m/Σe ≥ 0.20`), ninguna de las dos se reconstruye aquí.

La evaluación CONSERVA la granularidad: un registro por caso y réplica con `profile_id`, réplica, semillas, arquetipo, dificultad, concepto, `S`, énfasis, conjuntos esperado y predicho y F1 del caso. Con eso ofrece las
observaciones que consumirá la inferencia v3 (`F1_adapt` por réplica para el IC95 y las 100 medias por perfil para la prueba; `inference.aggregate_by_profile` de v2, reutilizada), pero NO ejecuta la inferencia: no
compara con 0.85, no declara RNF-03 ni H1 (`statistical_rule_v3` decide la prueba; su criterio conjunto es una pieza posterior). Los resúmenes `descriptive` son solo eso.

ESTADO: PROVISIONAL u OFICIAL. La evaluación OFICIAL exige que la regla esté aprobada en el registro de `rubric_v3` (hoy VACÍO: se registra con el sellado del pre-registro v3), K = 10 y los 100 perfiles; mientras tanto
se rechaza (`RuleNotApproved`). La salida es determinista (misma entrada ⇒ mismos bytes) y no lleva marcas de tiempo.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

import adaptation_swarm
from adaptation_swarm.analysis import inference, replicas_v3, statistical_rule_v3
from adaptation_swarm.gold import rubric_v3
from adaptation_swarm.gold.f1_multilabel import METRIC_VERSION, OFFICIAL_AGGREGATION, case_f1, cases_from_records, multilabel_report
from adaptation_swarm.gold.labels_v2 import emphasis_from_S
from adaptation_swarm.pso.space import MODALITIES

SCHEMA_EVALUATION = "evaluation-v3"
STATUS_PROVISIONAL = rubric_v3.STATUS_PROVISIONAL
STATUS_OFFICIAL = rubric_v3.STATUS_OFFICIAL
_EVALUATION_MODULES = ("analysis/evaluation_v3.py", "gold/rubric_v3.py", "analysis/statistical_rule_v3.py", "gold/f1_multilabel.py", "analysis/inference.py")


def _order(modalities) -> list[str]:
    return [m for m in MODALITIES if m in modalities]


def case_records(cases: Sequence[Mapping], rule: Any, *, replica_index: int, batch_seed: int | None = None) -> list[dict]:
    """Un registro por caso con TODA la granularidad (perfil, réplica, semillas, arquetipo, dificultad, concepto, `S`, énfasis, conjuntos y F1). La regla se aplica a través de `rubric_v3`."""
    labels = cases_from_records(cases, rule)
    out = []
    for c, lab in zip(cases, labels):
        S = list(c.get("g_best_S", c.get("S")))
        e = emphasis_from_S(S)
        f1 = case_f1(lab.gold, lab.predicted)
        if "f1" in c and c["f1"] != f1:
            raise ValueError(f"réplica {replica_index}: el F1 almacenado de {c['profile_id']!r} no coincide con el recalculado")
        out.append({"profile_id": c["profile_id"], "replica_index": replica_index, "batch_seed": batch_seed, "case_seed": c.get("seed"), "archetype": c.get("archetype"),
                    "difficulty": c.get("difficulty"), "concept_id": c.get("concept_id"), "S": S, "emphasis": dict(zip(MODALITIES, (int(x) for x in e))),
                    "expected_set": _order(lab.gold), "predicted_set": _order(lab.predicted), "f1": f1})
    return out


def _describe(values: Sequence[float]) -> dict:
    x = np.asarray(values, dtype=float)
    return {"n": int(x.size), "mean": float(x.mean()), "sd": float(x.std(ddof=1)) if x.size > 1 else None, "median": float(np.median(x)), "min": float(x.min()), "max": float(x.max())}


def evaluate_v3(replicas: Sequence[Mapping], *, rule: Any, official: bool = False, source: Mapping | None = None) -> dict:
    """Evalúa K réplicas (`[{"replica_index", "batch_seed", "cases": [...]}, ...]`) con la regla v3. Con `official=True` exige regla aprobada, K = 10 y 100 perfiles (`RuleNotApproved`/`ValueError` si no)."""
    if not rubric_v3.is_registered_v3(rule):
        raise ValueError("evaluation_v3 solo acepta una regla v3 REGISTRADA de `rubric_v3`")
    if not replicas:
        raise ValueError("sin réplicas")
    if official:
        rubric_v3.require_approved(rule)                                   # RuleNotApproved: hoy el registro v3 está vacío ⇒ la evaluación oficial está bloqueada
        if len(replicas) != replicas_v3.K_OFFICIAL or any(len(r["cases"]) != replicas_v3.N_PROFILES_OFFICIAL for r in replicas):
            raise ValueError("la evaluación oficial exige K = 10 y los 100 perfiles")
    status = STATUS_OFFICIAL if official else STATUS_PROVISIONAL

    per_replica, records, f1_by_replica_profile, all_labels = [], [], [], []
    for pos, rep in enumerate(replicas):
        idx = int(rep.get("replica_index", pos))
        recs = case_records(rep["cases"], rule, replica_index=idx, batch_seed=rep.get("batch_seed"))
        labels = cases_from_records(rep["cases"], rule)
        report = multilabel_report(labels, rule, require_official=False)                 # métrica de f1_multilabel (sin cambios); su `status` refleja el registro de v2 y NO se usa
        f1_adapt = report.f1(OFFICIAL_AGGREGATION)                                        # P3: media del F1 por caso (samples)
        if f1_adapt is None:
            raise ValueError(f"réplica {idx}: F1_adapt indefinido")
        ids = [r["profile_id"] for r in recs]
        if len(set(ids)) != len(ids):
            raise ValueError(f"réplica {idx}: perfiles repetidos")
        f1_by_replica_profile.append({r["profile_id"]: r["f1"] for r in recs})
        per_replica.append({"replica_index": idx, "batch_seed": rep.get("batch_seed"), "n_cases": report.n_cases, "f1_adapt": f1_adapt, "n_empty_predicted": report.n_empty_predicted,
                            "ovr_2x2": report.ovr_2x2, "per_archetype": report.per_archetype})
        records.extend(recs)
        all_labels.extend(labels)
    pooled = multilabel_report(all_labels, rule, require_official=False)                  # OVR descriptivo agrupando todas las réplicas
    profiles = inference.aggregate_by_profile(f1_by_replica_profile)
    profile_means = {p: profiles[p]["mean"] for p in sorted(profiles)}
    f1_adapt_by_replica = [r["f1_adapt"] for r in per_replica]
    descriptive = {"note": "DESCRIPTIVO: no compara con 0.85 ni decide RNF-03/H1 (la prueba es de statistical_rule_v3; el criterio conjunto, una pieza posterior)",
                   "f1_adapt_by_replica": _describe(f1_adapt_by_replica), "profile_means": _describe(list(profile_means.values())),
                   "ci95_replicas": inference.student_t_ci(f1_adapt_by_replica) if len(f1_adapt_by_replica) >= 2 else None}
    root = Path(adaptation_swarm.__file__).parent
    return {"schema": SCHEMA_EVALUATION, "status": status, "rule_version": rule.rule_version, "official_version": rubric_v3.official_version(rule), "rule": rule.to_dict(),
            "metric_version": METRIC_VERSION, "aggregation": OFFICIAL_AGGREGATION, "statistical_rule_version": statistical_rule_v3.STATISTICAL_PASS_RULE_VERSION,
            "k": len(replicas), "n_profiles": len(profile_means), "n_cases_total": len(records),
            "f1_adapt_by_replica": f1_adapt_by_replica, "profile_means": profile_means, "descriptive": descriptive,
            "ovr_2x2_pooled": {"modalities": list(MODALITIES), "by_modality": pooled.ovr_2x2, "n_cases": pooled.n_cases},
            "per_replica": per_replica, "cases": records, "source": dict(source) if source is not None else None,
            "evaluation_modules": {f: hashlib.sha256((root / f).read_bytes()).hexdigest() for f in _EVALUATION_MODULES}}


def inference_inputs(evaluation: Mapping) -> dict:
    """Observaciones que consumirá la inferencia v3: `f1_adapt_by_replica` (para el IC95 de `inference.student_t_ci`) y `profile_means` ordenados por `profile_id` (para
    `statistical_rule_v3.profile_level_test_v3`). No ejecuta ninguna prueba."""
    return {"f1_adapt_by_replica": list(evaluation["f1_adapt_by_replica"]), "profile_means": [evaluation["profile_means"][p] for p in sorted(evaluation["profile_means"])]}


def canonical_bytes(evaluation: Mapping) -> bytes:
    return json.dumps(evaluation, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def content_hash(evaluation: Mapping) -> str:
    return hashlib.sha256(canonical_bytes(evaluation)).hexdigest()


# ── adaptador: directorio de réplicas preparado por `replicas_v3` ────────────────────────────────────────────────
def load_replicas(out_dir: Path) -> tuple[dict, list[dict]]:
    """Manifiesto y réplicas de un directorio de `replicas_v3` (verifica la integridad por hash; no modifica nada)."""
    out = Path(out_dir)
    problems = replicas_v3.verify(out)
    if problems:
        raise ValueError(f"directorio de réplicas v3 no íntegro: {problems}")
    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    reps = []
    for e in manifest["replicas"]:
        body = json.loads((out / e["file"]).read_text(encoding="utf-8"))
        reps.append({"replica_index": body["replica_index"], "batch_seed": body["batch_seed"], "cases": body["cases"]})
    return manifest, reps


def evaluate_dir_v3(out_dir: Path, *, official: bool = False) -> dict:
    """Evalúa un directorio de `replicas_v3`. La regla se reconstruye desde el manifiesto (solo reglas v3 REGISTRADAS). Con `official=True` exige además un manifiesto OFICIAL."""
    manifest, reps = load_replicas(out_dir)
    mr = manifest["rule"]
    rule = rubric_v3.get_rule(mr["gold"]["rule_version"], mr["inclusion"]["rule_id"])
    if official:
        rubric_v3.require_approved(rule)                                   # primero la aprobación (RuleNotApproved), como en `evaluate_v3` y en `replicas_v3`
        if manifest["status"] != "OFICIAL":
            raise ValueError("el manifiesto no es OFICIAL: la evaluación oficial exige un directorio OFICIAL")
    source = {"plan_sha256": manifest["plan_sha256"], "master_seed": manifest["master_seed"], "batch_seeds": manifest["batch_seeds"], "library": manifest["library"], "dataset": manifest["dataset"],
              "code_version": manifest["code_version"], "manifest_status": manifest["status"], "full_rule_version": mr.get("full_rule_version"), "modules_v3": manifest["modules_v3"]}
    return evaluate_v3(reps, rule=rule, official=official, source=source)
