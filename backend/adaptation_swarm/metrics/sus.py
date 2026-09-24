"""SUS (System Usability Scale; Brooke, 1996) y análisis del panel — SOLO cálculo. No genera ni simula respuestas.

Puntaje (asesoría §4.4): ítems impares (1,3,5,7,9) → respuesta − 1; ítems pares (2,4,6,8,10) → 5 − respuesta;
suma × 2.5 → 0–100. Estado del estudio: PENDIENTE DE RECOLECCIÓN HUMANA hasta reunir n ≥ 10 evaluadores reales.
Plan estadístico de la asesoría: Shapiro-Wilk (α=0.05) → t de una muestra (si normal) o Wilcoxon (si no) contra el
umbral (SUS > 75), con IC95%."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Sequence

import numpy as np
from scipy import stats

MIN_EVALUATORS = 10
SUS_THRESHOLD = 75.0
PENDING = "PENDIENTE DE RECOLECCIÓN HUMANA"


def sus_score(items: Sequence[int]) -> float:
    if len(items) != 10 or any((not isinstance(i, (int, np.integer))) or i < 1 or i > 5 for i in items):
        raise ValueError("SUS exige 10 ítems enteros entre 1 y 5")
    total = sum((v - 1) if idx % 2 == 0 else (5 - v) for idx, v in enumerate(items))   # idx 0 = ítem 1 (impar)
    return total * 2.5


def study_status(n_participants: int) -> str:
    return "COMPLETO (n≥10)" if n_participants >= MIN_EVALUATORS else PENDING


@dataclass(frozen=True)
class SusAnalysis:
    n: int
    status: str
    mean: float | None = None
    sd: float | None = None
    min: float | None = None
    max: float | None = None
    ci95: tuple[float, float] | None = None
    shapiro_p: float | None = None
    test: str | None = None
    test_p: float | None = None
    exceeds_threshold: bool | None = None       # hallazgo estadístico, no un veredicto automático

    def to_dict(self) -> dict:
        return {k: (list(v) if isinstance(v, tuple) else v) for k, v in self.__dict__.items()}


def analyze_sus(scores: Sequence[float]) -> SusAnalysis:
    """Análisis del plan de la asesoría. Con n < 10 NO calcula conclusiones: devuelve el estado PENDIENTE."""
    n = len(scores)
    if n < MIN_EVALUATORS:
        return SusAnalysis(n=n, status=PENDING)
    x = np.asarray(scores, float)
    mean, sd = float(x.mean()), float(x.std(ddof=1))
    half = float(stats.t.ppf(0.975, n - 1) * sd / math.sqrt(n)) if sd > 0 else 0.0
    shapiro_p = float(stats.shapiro(x).pvalue) if n >= 3 and sd > 0 else None
    if shapiro_p is None or shapiro_p > 0.05:
        res = stats.ttest_1samp(x, SUS_THRESHOLD, alternative="greater")
        test, p = "t de Student de una muestra (H1: media > 75)", float(res.pvalue)
    else:
        res = stats.wilcoxon(x - SUS_THRESHOLD, alternative="greater")
        test, p = "Wilcoxon de rangos con signo (H1: mediana > 75)", float(res.pvalue)
    return SusAnalysis(n=n, status=study_status(n), mean=mean, sd=sd, min=float(x.min()), max=float(x.max()),
                       ci95=(mean - half, mean + half), shapiro_p=shapiro_p, test=test, test_p=p,
                       exceeds_threshold=bool(mean > SUS_THRESHOLD and p < 0.05))


def fleiss_kappa(table: np.ndarray) -> float:
    """κ de Fleiss. `table[i, j]` = nº de evaluadores que asignaron la categoría j al sujeto i (misma n por sujeto)."""
    t = np.asarray(table, float)
    n_sub, _ = t.shape
    n_rat = t[0].sum()
    if not np.all(t.sum(axis=1) == n_rat) or n_rat < 2:
        raise ValueError("todos los sujetos deben tener el mismo nº (≥2) de evaluadores")
    p_j = t.sum(axis=0) / (n_sub * n_rat)
    p_i = ((t ** 2).sum(axis=1) - n_rat) / (n_rat * (n_rat - 1))
    p_bar, p_e = p_i.mean(), (p_j ** 2).sum()
    return 1.0 if p_e == 1 else float((p_bar - p_e) / (1 - p_e))


def analyze_gold_panel(agrees_by_cell: dict[tuple[str, str], list[bool]]) -> dict:
    """Acuerdo del panel con la tabla gold (20 celdas; cada valor = lista de votos «razonable»/«no razonable»)."""
    n_raters = {len(v) for v in agrees_by_cell.values()}
    n = min(n_raters) if n_raters else 0
    if n < MIN_EVALUATORS or len(n_raters) != 1:
        return {"status": PENDING, "n_evaluators": n}
    table = np.array([[sum(v), len(v) - sum(v)] for v in agrees_by_cell.values()])
    return {"status": study_status(n), "n_evaluators": n, "cells": len(table),
            "share_agree": float(table[:, 0].sum() / table.sum()), "fleiss_kappa": fleiss_kappa(table),
            "cells_with_majority_disagreement": [k for k, v in agrees_by_cell.items() if sum(v) < len(v) / 2]}
