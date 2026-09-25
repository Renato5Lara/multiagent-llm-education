"""Matriz de confusión 4×4, Precision/Recall/F1 por clase y F1_adapt = macro-F1
(DECISION-CLOSURE §7.3). Funciones puras, sin LLM ni muestreo (salvo el bootstrap, que
recibe su semilla).

Filas = clase real (gold); columnas = clase predicha (argmax e_m de g_best).

Clases sin soporte (ni gold ni predicción) tienen P/R/F1 indefinidos (0/0). El cierre pide
"promedio sobre las 4 clases" pero no dice qué hacer con 0/0: se reportan DOS macro-F1 —
`macro_f1_defined` (excluye las clases 0/0) y `macro_f1_all4` (0/0 ⇒ 0) — y el principal
declarado es `f1_adapt = macro_f1_defined`. Con la tabla preregistrada `audio` nunca es
gold, así que `audio` solo puede aparecer como falso positivo.

Fórmulas, por clase c (TP, FP, FN se leen de la matriz de confusión):
    Precision_c = TP / (TP + FP)      Recall_c = TP / (TP + FN)      F1_c = 2·P·R / (P + R)
Divisiones entre cero: TP+FP = 0 ⇒ Precision indefinida (None); TP+FN = 0 ⇒ Recall indefinida (None);
F1 es None solo si ambas lo son; si una está definida y la otra no, o si P + R = 0, F1 = 0.
Sin ningún caso (matriz vacía) F1_adapt no está definido y se lanza `ValueError`: un 0.0 sería
indistinguible de «todo predicho mal».

Unidad de análisis: el CASO = un par (perfil sintético, concepto); n = 100 casos (DECISION-CLOSURE §7.3
y §8). `f1_adapt` es el macro-F1 de este módulo contra el gold preregistrado (`gold/rubric.py`); NO es el
evaluador proxy determinista de `app/benchmark/metrics.py` (métricas pedagógicas simuladas de otro benchmark).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import numpy as np

from adaptation_swarm.pso.space import MODALITIES

CLASSES = MODALITIES


def confusion_matrix(pairs: Sequence[tuple[str, str]]) -> np.ndarray:
    """`pairs` = [(gold, predicted), ...] → matriz (4×4) de enteros."""
    idx = {c: i for i, c in enumerate(CLASSES)}
    cm = np.zeros((len(CLASSES), len(CLASSES)), dtype=int)
    for gold, pred in pairs:
        cm[idx[gold], idx[pred]] += 1
    return cm


@dataclass(frozen=True)
class ClassScores:
    precision: float | None
    recall: float | None
    f1: float | None
    support: int


@dataclass(frozen=True)
class F1Report:
    confusion: np.ndarray
    per_class: dict[str, ClassScores]
    macro_f1_defined: float
    macro_f1_all4: float
    accuracy: float

    @property
    def f1_adapt(self) -> float:
        return self.macro_f1_defined

    def to_dict(self) -> dict:
        return {
            "classes": list(CLASSES),
            "confusion": self.confusion.tolist(),
            "per_class": {
                c: {"precision": s.precision, "recall": s.recall, "f1": s.f1, "support": s.support}
                for c, s in self.per_class.items()
            },
            "macro_f1_defined": self.macro_f1_defined,
            "macro_f1_all4": self.macro_f1_all4,
            "f1_adapt": self.f1_adapt,
            "accuracy": self.accuracy,
        }


def _safe_div(num: float, den: float) -> float | None:
    return None if den == 0 else num / den


def report_from_matrix(cm: np.ndarray) -> F1Report:
    if cm.sum() == 0:
        raise ValueError("sin casos: F1_adapt no está definido")
    per_class: dict[str, ClassScores] = {}
    f1_defined: list[float] = []
    f1_all4: list[float] = []
    for i, c in enumerate(CLASSES):
        tp = float(cm[i, i])
        fp = float(cm[:, i].sum() - cm[i, i])
        fn = float(cm[i, :].sum() - cm[i, i])
        p = _safe_div(tp, tp + fp)
        r = _safe_div(tp, tp + fn)
        if p is None and r is None:
            f1 = None
        elif p is None or r is None:
            f1 = 0.0   # una de las dos indefinida, la otra definida ⇒ el otro extremo es 0
        else:
            f1 = 0.0 if (p + r) == 0 else 2 * p * r / (p + r)
        per_class[c] = ClassScores(p, r, f1, int(cm[i, :].sum()))
        if f1 is not None:
            f1_defined.append(f1)
        f1_all4.append(0.0 if f1 is None else f1)
    total = cm.sum()
    return F1Report(
        confusion=cm,
        per_class=per_class,
        macro_f1_defined=float(np.mean(f1_defined)) if f1_defined else 0.0,
        macro_f1_all4=float(np.mean(f1_all4)),
        accuracy=float(np.trace(cm) / total) if total else 0.0,
    )


def f1_report(pairs: Sequence[tuple[str, str]]) -> F1Report:
    return report_from_matrix(confusion_matrix(pairs))


def bootstrap_ci(
    pairs: Sequence[tuple[str, str]], rng: np.random.Generator, n_boot: int = 2000, alpha: float = 0.05
) -> tuple[float, float]:
    """IC (1−α) por bootstrap percentil sobre los casos, para `f1_adapt`."""
    n = len(pairs)
    if n == 0:
        raise ValueError("sin pares")
    stats = np.empty(n_boot)
    for b in range(n_boot):
        sample = [pairs[i] for i in rng.integers(0, n, size=n)]
        stats[b] = f1_report(sample).f1_adapt
    return float(np.quantile(stats, alpha / 2)), float(np.quantile(stats, 1 - alpha / 2))
