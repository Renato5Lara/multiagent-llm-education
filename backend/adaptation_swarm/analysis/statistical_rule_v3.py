"""Regla estadística de K = 10 v3 (capa ADITIVA sobre `analysis/inference.py`; funciones puras).

La regla aprobada (Consulta 4, `DEC-F1-TEST`; `DECISION-CLOSURE` §15, C4) define «prueba superada» como

    p < α  Y  media muestral de los 100 promedios por perfil > benchmark (0.85)

en las dos ramas (t de una muestra y Wilcoxon). `inference.profile_level_test` —código sellado de K = 10 v2, huellado en su pre-registro— calcula `statistical_pass = (p < α)`: en la rama t
un p < α unilateral ya implica media > benchmark, pero en la de Wilcoxon no. Ese archivo NO se modifica (su sha256 forma parte del sellado v2); esta capa LO REUTILIZA sin copiar ninguna estadística
(Shapiro-Wilk, t, Wilcoxon, α, benchmark) y solo sustituye la decisión `statistical_pass`.

`inference.combined_criterion` solo lee `statistical_pass` del contraste, así que se reutiliza tal cual con el resultado de `profile_level_test_v3` (criterio conjunto `ci_pass AND statistical_pass`).
"""

from __future__ import annotations

from typing import Sequence

from adaptation_swarm.analysis import inference

# Identificador estable de la regla, para la trazabilidad del pre-registro y del manifiesto de K = 10 v3.
STATISTICAL_PASS_RULE_VERSION = "statistical-pass-v3:p<alpha&mean>benchmark"
STATISTICAL_PASS_RULE_TEXT = "prueba superada ⇔ p < alpha AND media muestral > benchmark (Consulta 4, DEC-F1-TEST)"


def profile_level_test_v3(profile_means: Sequence[float], *, benchmark: float = inference.BENCHMARK_F1, alpha: float = inference.ALPHA) -> dict:
    """`inference.profile_level_test` con la decisión `statistical_pass` de la regla v3. Conserva todos los campos del contraste v2 (prueba elegida, estadístico, `p_value`, `mean`, `shapiro_*`…); si la
    prueba es indefinida (muestra constante), `statistical_pass` sigue siendo `None` (INDETERMINADO), nunca PASS. Añade `statistical_rule_version`."""
    test = inference.profile_level_test(profile_means, benchmark=benchmark, alpha=alpha)
    if test["statistical_pass"] is None:
        return {**test, "statistical_rule_version": STATISTICAL_PASS_RULE_VERSION}
    return {**test, "statistical_pass": bool(test["p_value"] < alpha and test["mean"] > benchmark), "statistical_rule_version": STATISTICAL_PASS_RULE_VERSION}
