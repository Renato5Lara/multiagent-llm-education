"""Métrica de INCLUSIÓN/EXCLUSIÓN multimodal 4×4 con audio incluido (respuesta del asesor, 2026-09-25, D1). Funciones puras, sin LLM ni muestreo
(salvo el bootstrap, que recibe su generador). NO sustituye a `gold/f1.py` (definición histórica de etiqueta única), que no se toca.

Definiciones (MASTER-SPEC §13), por modalidad m ∈ {code, diagram, text, audio}, sobre los casos que TIENEN gold:
    TP_m: m ∈ gold ∧ m ∈ predicho        FP_m: m ∉ gold ∧ m ∈ predicho        FN_m: m ∈ gold ∧ m ∉ predicho        TN_m: ninguno de los dos
    Precision_m = TP/(TP+FP)             Recall_m = TP/(TP+FN)                F1_m = 2·P·R/(P+R)

Convención de divisiones entre cero (la MISMA que `gold/f1.py`, para poder comparar): Precision indefinida si TP+FP = 0; Recall indefinido si TP+FN = 0;
F1 = None si ambas lo son; si una está definida y la otra no, o P+R = 0, F1 = 0.

Matriz 4×4 (`matrix_4x4`): M[i][j] = nº de casos con la modalidad i en el gold y la j en lo predicho (co-ocurrencia). Su diagonal es TP; con etiquetas
de UN elemento coincide exactamente con la matriz de confusión clásica de `gold/f1.py` (propiedad comprobada por prueba). Es una INTERPRETACIÓN de «4×4»
que el asesor debe confirmar (ver addendum, P1–P3): en un problema multietiqueta la matriz clásica no está definida.

AGREGACIONES — la métrica OFICIAL es `samples` (P3, respuesta del asesor 2026-09-26; `rubric_v2.OFFICIAL_AGGREGATION`), expuesta por `official_f1_adapt(report)`, que exige un
informe OFICIAL. Las demás son solo DESCRIPTIVAS/históricas y NO son `F1_adapt`. `MultilabelReport.f1(aggregation)` sigue exigiendo la agregación explícita (sin valor por defecto):
    · "macro_defined": media del F1 de las modalidades con F1 definido      · "macro_all4": lo mismo con None ⇒ 0
    · "micro": F1 de los TP/FP/FN sumados de las 4 modalidades (2ΣTP / (2ΣTP + ΣFP + ΣFN))
    · "samples": media del F1 POR CASO (Dice: 2|G∩P| / (|G|+|P|)); es la «unidad por caso» que pide D11a para el contraste inferencial.

Conjunto predicho vacío con gold no vacío ⇒ F1 del caso = 0 (P1-bis): el caso NO se excluye y entra en la media. Se permite la configuración con e_m = 0 en las 4 modalidades (R6: el PSO no
se restringe); simplemente puntúa 0.

Análisis por modalidad (P3-OvR): `ovr_2x2[m]` = matriz 2×2 One-vs-Rest [[TP, FN], [FP, TN]] (filas: gold m / no m; columnas: predicho m / no m) de CADA modalidad, con precisión, recall y F1;
`matrix_4x4` (co-ocurrencia) se conserva solo como descriptiva y NO interviene en ninguna agregación. `per_archetype[a]` = F1 medio por caso del arquetipo (descriptivo).

Casos sin gold definido (`gold is None`) se EXCLUYEN de todo y se cuentan (`n_no_gold`). Un caso con gold y predicho vacíos tiene F1 por caso indefinido y no
entra en `samples` (se cuenta en `n_case_f1_undefined`).

Salida reproducible y versionada: `to_dict()` es determinista; `content_hash()` es el sha256 de su JSON canónico. Todo resultado lleva `status`
PROVISIONAL u OFICIAL según la aprobación de la regla (`rubric_v2.APPROVED_RULE_VERSIONS`), y `metric_version`.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Iterable, Sequence

import numpy as np

from adaptation_swarm.gold.labels_v2 import emphasis_from_S, modality_set
from adaptation_swarm.gold.rubric_v2 import (OFFICIAL_AGGREGATION, STATUS_OFFICIAL, EvaluationRule, RuleNotApproved, is_approved, require_approved,
                                             status_of)
from adaptation_swarm.profiles.models import Archetype, Difficulty
from adaptation_swarm.pso.space import MODALITIES

METRIC_VERSION = "f1-multilabel-v2"
AGGREGATIONS = ("macro_defined", "macro_all4", "micro", "samples")


@dataclass(frozen=True)
class CaseLabels:
    profile_id: str
    gold: frozenset[str] | None          # None = sin gold definido
    predicted: frozenset[str]
    archetype: str | None = None

    def __post_init__(self) -> None:
        if self.gold is not None:
            modality_set(self.gold)
        modality_set(self.predicted)


def _prf(tp: int, fp: int, fn: int) -> tuple[float | None, float | None, float | None]:
    p = None if tp + fp == 0 else tp / (tp + fp)
    r = None if tp + fn == 0 else tp / (tp + fn)
    if p is None and r is None:
        f1 = None
    elif p is None or r is None:
        f1 = 0.0
    else:
        f1 = 0.0 if p + r == 0 else 2 * p * r / (p + r)
    return p, r, f1


def case_f1(gold: frozenset[str], predicted: frozenset[str]) -> float | None:
    """F1 de un caso (Dice). None si gold y predicho están vacíos."""
    den = len(gold) + len(predicted)
    return None if den == 0 else 2 * len(gold & predicted) / den


def cases_from_records(records: Iterable[dict], rule: EvaluationRule) -> list[CaseLabels]:
    """Etiquetas de gold y predicción a partir de filas con `profile_id`, `archetype`, `difficulty` y `g_best_S` (o `S`), aplicando una regla
    EXPLÍCITA. Sirve tanto para las corridas históricas como para las réplicas nuevas."""
    out = []
    for r in records:
        S = r.get("g_best_S", r.get("S"))
        if S is None:
            raise ValueError(f"el caso {r.get('profile_id')!r} no trae g_best_S/S")
        arch, diff = Archetype(r["archetype"]), (Difficulty(r["difficulty"]) if r.get("difficulty") else None)
        out.append(CaseLabels(r["profile_id"], rule.expected_set(arch, diff), rule.predicted_set(emphasis_from_S(S)), r["archetype"]))
    return out


@dataclass(frozen=True)
class MultilabelReport:
    metric_version: str
    rule: dict
    status: str
    n_cases: int
    n_no_gold: int
    n_empty_predicted: int
    n_case_f1_undefined: int
    per_modality: dict[str, dict[str, Any]]
    matrix_4x4: list[list[int]]
    exact_match: float | None
    macro_defined: float | None
    macro_all4: float
    micro: dict[str, float | None]
    samples: dict[str, Any]
    per_case: list[dict[str, Any]]
    ovr_2x2: dict[str, dict[str, Any]]
    per_archetype: dict[str, dict[str, Any]]

    def f1(self, aggregation: str) -> float | None:
        """F1 bajo una agregación EXPLÍCITA. No hay agregación por defecto (decisión pendiente P3)."""
        if aggregation not in AGGREGATIONS:
            raise ValueError(f"agregación desconocida {aggregation!r}; válidas: {AGGREGATIONS}")
        return {"macro_defined": self.macro_defined, "macro_all4": self.macro_all4, "micro": self.micro["f1"], "samples": self.samples["f1"]}[aggregation]

    def to_dict(self) -> dict:
        return {"metric_version": self.metric_version, "rule": self.rule, "status": self.status, "n_cases": self.n_cases, "n_no_gold": self.n_no_gold,
                "n_empty_predicted": self.n_empty_predicted, "n_case_f1_undefined": self.n_case_f1_undefined, "modalities": list(MODALITIES),
                "per_modality": self.per_modality, "matrix_4x4": self.matrix_4x4, "exact_match": self.exact_match,
                "official_aggregation": OFFICIAL_AGGREGATION,
                "aggregations": {"macro_defined": self.macro_defined, "macro_all4": self.macro_all4, "micro": self.micro, "samples": self.samples},
                "ovr_2x2": self.ovr_2x2, "per_archetype": self.per_archetype, "per_case": self.per_case}

    def content_hash(self) -> str:
        return hashlib.sha256(json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")).hexdigest()


def multilabel_report(cases: Sequence[CaseLabels], rule: EvaluationRule, *, require_official: bool = False) -> MultilabelReport:
    """Evalúa `cases` bajo `rule`. Con `require_official=True` exige que la regla esté aprobada (`RuleNotApproved` si no)."""
    if require_official:
        require_approved(rule)
    scored = [c for c in cases if c.gold is not None]
    if not scored:
        raise ValueError("sin casos con gold definido: la métrica no está definida")
    idx = {m: i for i, m in enumerate(MODALITIES)}
    counts = {m: [0, 0, 0, 0] for m in MODALITIES}                       # tp, fp, fn, tn
    matrix = np.zeros((len(MODALITIES),) * 2, dtype=int)
    per_case: list[dict[str, Any]] = []
    for c in scored:
        g, p = c.gold, c.predicted
        for m in MODALITIES:
            k = 0 if (m in g and m in p) else 1 if (m not in g and m in p) else 2 if (m in g and m not in p) else 3
            counts[m][k] += 1
        for gi in g:
            for pj in p:
                matrix[idx[gi], idx[pj]] += 1
        per_case.append({"profile_id": c.profile_id, "archetype": c.archetype, "gold": [m for m in MODALITIES if m in g],
                         "predicted": [m for m in MODALITIES if m in p], "f1": case_f1(g, p)})
    per_mod: dict[str, dict[str, Any]] = {}
    ovr: dict[str, dict[str, Any]] = {}
    f1_def, f1_all = [], []
    for m in MODALITIES:
        tp, fp, fn, tn = counts[m]
        pr, rc, f1 = _prf(tp, fp, fn)
        per_mod[m] = {"tp": tp, "fp": fp, "fn": fn, "tn": tn, "precision": pr, "recall": rc, "f1": f1, "support": tp + fn}
        ovr[m] = {"matrix": [[tp, fn], [fp, tn]], "tp": tp, "fp": fp, "fn": fn, "tn": tn, "precision": pr, "recall": rc, "f1": f1}
        if f1 is not None:
            f1_def.append(f1)
        f1_all.append(0.0 if f1 is None else f1)
    TP, FP, FN = (sum(counts[m][k] for m in MODALITIES) for k in (0, 1, 2))
    mp, mr, mf = _prf(TP, FP, FN)
    micro_f1 = None if (2 * TP + FP + FN) == 0 else 2 * TP / (2 * TP + FP + FN)
    defined = [d["f1"] for d in per_case if d["f1"] is not None]
    n_match = sum(1 for c in scored if c.gold == c.predicted)
    by_arch: dict[str, list[float]] = {}
    n_by_arch: dict[str, int] = {}
    for d in per_case:
        a = d["archetype"] if d["archetype"] is not None else "(sin arquetipo)"
        n_by_arch[a] = n_by_arch.get(a, 0) + 1
        if d["f1"] is not None:
            by_arch.setdefault(a, []).append(d["f1"])
    per_archetype = {a: {"n": n_by_arch[a], "f1_samples": float(np.mean(by_arch[a])) if a in by_arch else None} for a in sorted(n_by_arch)}
    return MultilabelReport(
        metric_version=METRIC_VERSION, rule=rule.to_dict(), status=status_of(rule), n_cases=len(scored), n_no_gold=len(cases) - len(scored),
        n_empty_predicted=sum(1 for c in scored if not c.predicted), n_case_f1_undefined=len(scored) - len(defined),
        per_modality=per_mod, matrix_4x4=matrix.tolist(), exact_match=n_match / len(scored),
        macro_defined=float(np.mean(f1_def)) if f1_def else None, macro_all4=float(np.mean(f1_all)),
        micro={"precision": mp, "recall": mr, "f1": micro_f1, "tp": TP, "fp": FP, "fn": FN},
        samples={"f1": float(np.mean(defined)) if defined else None, "n_defined": len(defined)}, per_case=per_case,
        ovr_2x2=ovr, per_archetype=per_archetype)


def official_report(cases: Sequence[CaseLabels], rule: EvaluationRule) -> MultilabelReport:
    """Informe OFICIAL: exige una regla aprobada (`RuleNotApproved` si no). Es el único camino que produce un `F1_adapt` oficial."""
    return multilabel_report(cases, rule, require_official=True)


def official_f1_adapt(report: MultilabelReport) -> float:
    """`F1_adapt` OFICIAL = media del F1 por caso (agregación `samples`, P3). Exige un informe OFICIAL: un informe PROVISIONAL no produce un `F1_adapt`."""
    if report.status != STATUS_OFFICIAL:
        raise RuleNotApproved("solo un informe OFICIAL (regla aprobada) tiene un F1_adapt oficial")
    v = report.f1(OFFICIAL_AGGREGATION)
    if v is None:
        raise ValueError("F1_adapt indefinido: ningún caso con F1 por caso definido")
    return v


def bootstrap_ci(cases: Sequence[CaseLabels], rule: EvaluationRule, aggregation: str, rng: np.random.Generator, n_boot: int = 2000,
                 alpha: float = 0.05) -> tuple[float, float]:
    """IC (1−α) por bootstrap percentil sobre los casos, para la agregación indicada (el generador se recibe: no hay semilla implícita)."""
    if aggregation not in AGGREGATIONS:
        raise ValueError(f"agregación desconocida {aggregation!r}")
    if not cases:
        raise ValueError("sin casos")
    stats = []
    for _ in range(n_boot):
        sample = [cases[i] for i in rng.integers(0, len(cases), size=len(cases))]
        try:
            v = multilabel_report(sample, rule).f1(aggregation)
        except ValueError:
            continue
        if v is not None:
            stats.append(v)
    if not stats:
        raise ValueError("el bootstrap no produjo ningún valor definido")
    return float(np.quantile(stats, alpha / 2)), float(np.quantile(stats, 1 - alpha / 2))


__all__ = ["METRIC_VERSION", "AGGREGATIONS", "OFFICIAL_AGGREGATION", "CaseLabels", "MultilabelReport", "RuleNotApproved", "is_approved", "case_f1", "cases_from_records",
           "multilabel_report", "official_report", "official_f1_adapt", "bootstrap_ci"]
