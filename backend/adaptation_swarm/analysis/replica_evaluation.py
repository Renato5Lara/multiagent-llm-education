"""Evaluación de `F1_adapt` sobre un directorio de K réplicas (respuestas del asesor, 2026-09-26: P3, R1–R4). Solo LEE un directorio de réplicas ya generado y devuelve (o escribe en un directorio NUEVO) un
informe determinista. No ejecuta réplicas, no usa red, procesos ni base de datos.

Flujo (todo derivado de la regla registrada en el manifiesto, nunca de un argumento del llamador):
    1. integridad del directorio (`replicas.verify`) y regla gold-v2 REGISTRADA reconstruida desde el manifiesto;
    2. F1 por caso de cada réplica con esa regla (P1: e_m ≥ 1; P1-bis: predicho vacío ⇒ 0) y `F1_adapt` de cada réplica = media del F1 por caso (P3, `samples`);
    3. R1: IC95 t de Student (gl = K − 1) sobre los K `F1_adapt`;
    4. R2: promedio de los K F1 de cada perfil ⇒ N valores (uno por perfil); Shapiro-Wilk y t/Wilcoxon contra 0.85 sobre ESOS valores (nunca sobre las K·N observaciones);
    5. R3: criterio conjunto AND (límite inferior del IC95 ≥ 0.85 Y prueba estadística);
    6. además, descriptivos: F1 por modalidad (2×2 One-vs-Rest), F1 por arquetipo y variabilidad de la convergencia entre réplicas.

Un informe es OFICIAL solo si el manifiesto es OFICIAL y la regla está aprobada (`rubric_v2.require_approved`); si no, es PROVISIONAL y no puede usarse como evidencia confirmatoria.
ALCANCE (R4): es el experimento CORE; no sirve para RNF-01 ni RNF-04 (`assert_claim_allowed`).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Mapping

import numpy as np

from adaptation_swarm.analysis import inference, replicas
from adaptation_swarm.gold.f1_multilabel import cases_from_records, multilabel_report, official_f1_adapt
from adaptation_swarm.gold.rubric_v2 import OFFICIAL_AGGREGATION, STATUS_OFFICIAL, STATUS_PROVISIONAL, get_rule, official_version, require_approved
from adaptation_swarm.pso.space import MODALITIES
from adaptation_swarm.tools import isolated_env as iso

SCHEMA_EVALUATION = "replica-evaluation-v1"


class ClaimNotSupported(ValueError):
    """Se intentó usar el experimento CORE para afirmar algo que solo el experimento FULL-STACK puede sostener (RNF-01, RNF-04)."""


def assert_claim_allowed(evaluation: Mapping, claim: str) -> None:
    scope = evaluation["scope"]
    if claim in scope["does_not_support"] or claim not in scope["supports"]:
        raise ClaimNotSupported(f"el experimento {scope['experiment']!r} no sustenta {claim!r}: usa el experimento full-stack separado")


def _distribution(values: list[float]) -> dict:
    x = np.asarray(values, dtype=float)
    q1, med, q3 = (float(v) for v in np.percentile(x, [25, 50, 75]))
    return {"n": int(x.size), "min": float(x.min()), "q1": q1, "median": med, "q3": q3, "max": float(x.max()), "mean": float(x.mean()), "sd": float(x.std(ddof=1))}


def _across(values: list) -> dict | None:
    v = [x for x in values if x is not None]
    if not v:
        return None
    a = np.asarray(v, dtype=float)
    return {"n": int(a.size), "mean": float(a.mean()), "sd": float(a.std(ddof=1)) if a.size > 1 else 0.0, "min": float(a.min()), "max": float(a.max())}


def evaluate(out_dir: Path, *, official: bool = True) -> dict:
    """Evalúa un directorio de réplicas. Con `official=True` exige manifiesto OFICIAL y regla aprobada (`RuleNotApproved`/`ValueError` si no)."""
    out = Path(out_dir)
    problems = replicas.verify(out)
    if problems:
        raise ValueError(f"directorio de réplicas no íntegro: {problems}")
    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    mr = manifest["rule"]
    if mr is None:
        raise ValueError("el directorio no trae una regla de evaluación: sin ella no hay F1 (réplicas sin regla)")
    rule = get_rule(mr["gold"]["rule_version"], mr["inclusion"]["rule_id"])                # solo reglas gold-v2 REGISTRADAS
    if official:
        if manifest["status"] != STATUS_OFFICIAL:
            raise ValueError("el manifiesto no es OFICIAL: la evaluación oficial exige un directorio OFICIAL")
        require_approved(rule)
        if manifest["k"] != inference.K_REPLICAS or manifest["dataset"]["n_used"] != replicas.N_PROFILES_OFFICIAL:
            raise ValueError("la evaluación oficial exige K = 10 y los 100 perfiles")
    status = STATUS_OFFICIAL if official else STATUS_PROVISIONAL

    f1_adapt, f1_by_replica, reports, cases_by_replica = [], [], [], []
    for i in range(manifest["k"]):
        cases = replicas.replica_cases(out, i)
        rep = multilabel_report(cases_from_records(cases, rule), rule, require_official=official)
        by_profile = {}
        for c, d in zip(cases, rep.per_case):
            if d["profile_id"] != c["profile_id"] or d["f1"] is None:
                raise ValueError(f"réplica {i}: F1 por caso indefinido o desalineado para {c['profile_id']!r}")
            if "f1" in c and c["f1"] != d["f1"]:
                raise ValueError(f"réplica {i}: el F1 almacenado de {c['profile_id']!r} no coincide con el recalculado")
            by_profile[c["profile_id"]] = d["f1"]
        f1_by_replica.append(by_profile)
        f1_adapt.append(official_f1_adapt(rep) if official else rep.f1(OFFICIAL_AGGREGATION))
        reports.append(rep)
        cases_by_replica.append(cases)

    ci = inference.student_t_ci(f1_adapt)
    profiles = inference.aggregate_by_profile(f1_by_replica)
    means = [profiles[p]["mean"] for p in sorted(profiles)]
    test = inference.profile_level_test(means)
    criterion = inference.combined_criterion(ci, test)

    by_modality = {m: {"f1_by_replica": [r.per_modality[m]["f1"] for r in reports],
                       "f1_across_replicas": _across([r.per_modality[m]["f1"] for r in reports]),
                       "ovr_2x2_by_replica": [r.ovr_2x2[m] for r in reports]} for m in MODALITIES}
    archetypes = sorted({a for r in reports for a in r.per_archetype})
    by_archetype = {a: {"f1_by_replica": [r.per_archetype[a]["f1_samples"] for r in reports],
                        "f1_across_replicas": _across([r.per_archetype[a]["f1_samples"] for r in reports])} for a in archetypes}
    mean_of_means = float(np.mean(means))
    pkg = Path(__file__).resolve().parent.parent
    eval_modules = {f: replicas._sha_file(pkg / f) for f in ("analysis/inference.py", "analysis/replica_evaluation.py", "gold/f1_multilabel.py", "gold/rubric_v2.py")}
    return {"schema": SCHEMA_EVALUATION, "status": status, "rule_version": official_version(rule), "aggregation": OFFICIAL_AGGREGATION,
            "k": manifest["k"], "n_profiles": len(profiles), "statistical_unit": inference.PROTOCOL["statistical_unit"],
            "f1_adapt_by_replica": f1_adapt, "ci95": ci,
            "profile_means": {"distribution": _distribution(means), "per_profile": profiles},
            "inference": test, "criterion": criterion,
            "consistency": {"mean_of_profile_means": mean_of_means, "mean_of_replica_f1_adapt": ci["mean"], "equal": bool(abs(mean_of_means - ci["mean"]) < 1e-12)},
            "by_modality": by_modality, "by_archetype": by_archetype,
            "convergence": inference.convergence_variability(cases_by_replica),
            "computational_cost": {"status": "no medido", "reason": "el experimento CORE no registra tiempos (las réplicas son byte-deterministas); el costo computacional se mide en el experimento full-stack"},
            "scope": manifest["scope"], "provenance": {"manifest_plan_sha256": manifest["plan_sha256"], "library": manifest["library"], "dataset": manifest["dataset"],
                                                       "code_version": manifest["code_version"], "gold_fingerprint": mr["gold_fingerprint"], "modules": manifest["modules"],
                                                       "master_seed": manifest["master_seed"], "batch_seeds": manifest["batch_seeds"], "evaluation_modules": eval_modules}}


def write_evaluation(evaluation: dict, out_dir: Path) -> Path:
    """Escribe `evaluation.json` en un directorio NUEVO (nunca dentro de resultados congelados, datasets, paquetes de evidencia ni sobre archivos existentes)."""
    out = Path(out_dir)
    iso.check_new_output_targets([out / "evaluation.json"])
    out.mkdir(parents=True, exist_ok=False)
    replicas._write_new(out / "evaluation.json", replicas._canonical(evaluation) + b"\n")
    return out
