"""Validación del gold por el panel, POR ARQUETIPO — protocolo DEFINITIVO (respuestas del asesor, 2026-09-26: P4, R5, X1–X5, X3-bis). Cálculo puro (sin base de datos). Sustituye para gold-v2 al protocolo de
20 celdas de `metrics/sus.analyze_gold_panel` (Fleiss κ, gold-v1), que se conserva SIN cambios solo como historial: NADA de aquí usa Fleiss κ.

Unidad del juicio: los 4 ARQUETIPOS. Cada evaluador ve el conjunto COMPLETO esperado del arquetipo (`EXPECTED_SETS`: solo del arquetipo, sin dificultad ni W, audio solo en Balanced) y responde Aprobar/Rechazar.
`votes[arquetipo] = [True (aprueba) | False (rechaza), …]`, un valor por evaluador (n ≥ 10; el mismo n en los 4 arquetipos). Denominador de toda proporción global: 4·n (todos los juicios recolectados).

Estadístico ÚNICO y oficial: Gwet AC1 multi-evaluador para respuestas binarias (Gwet, 2008). NO hay ninguna rama «si κ…» ni fallback: AC1 se calcula siempre. La proporción global de aprobación es solo DESCRIPTIVA.

Criterio (conjuntivo; cada componente se registra por separado):
    panel_valid = (AC1 > 0.70) Y (acuerdo crudo ≥ 0.85) Y (todo arquetipo APROBADO) Y (ningún rechazo mayoritario) Y (ningún empate)
    · arquetipo aprobado ⇔ aprobaciones > n/2 (6/10 sí; 5/10 NO; 4/10 NO);  · rechazo mayoritario ⇔ rechazos > n/2;  · empate ⇔ aprobaciones == rechazos;
    · empate exacto (n par, n/2 – n/2): NO hay mayoría; el arquetipo queda NO aprobado (empate = rechazo) y se registra en `tied_archetypes`;
    · acuerdo crudo = juicios que coinciden con la categoría MAYORITARIA de su arquetipo / (4·n); en un empate no existe categoría mayoritaria: esos juicios no cuentan como coincidentes.
Las comparaciones con 0.70 (estricta) y 0.85 (inclusiva) se hacen con racionales exactos (`fractions.Fraction`), no con floats: el error binario no puede mover un caso de la frontera.
Consecuencia (X2, X3-bis, X6): `rule_version_review = True` si ocurre CUALQUIERA de: (1) algún arquetipo no aprobado, (2) algún empate, (3) algún rechazo mayoritario, (4) AC1 ≤ 0.70, (5) acuerdo crudo < 0.85 — aunque todos
los arquetipos tengan mayoría aprobatoria (un gold requiere aprobación del contenido Y confiabilidad del juicio). Nunca es `None`: `False` solo si `panel_valid`. El panel valida un gold ya congelado; la tabla no se
edita según las respuestas (un cambio es una `rule_version` nueva).
Mientras haya menos de 10 evaluadores el estado es PENDIENTE y no se extrae ninguna conclusión.
"""

from __future__ import annotations

from fractions import Fraction
from typing import Mapping, Sequence

from adaptation_swarm.gold.rubric_v2 import GOLD_RULES, PANEL_PROTOCOL, PANEL_PROTOCOL_VERSION
from adaptation_swarm.profiles.models import Archetype
from adaptation_swarm.pso.space import MODALITIES

MIN_EVALUATORS = PANEL_PROTOCOL["min_evaluators"]
AC1_THRESHOLD = PANEL_PROTOCOL["ac1_threshold"]                   # AC1 > 0.70
RAW_AGREEMENT_MIN = PANEL_PROTOCOL["raw_agreement_min"]           # acuerdo crudo ≥ 0.85
PENDING = "PENDIENTE DE RECOLECCIÓN HUMANA"
VALIDATED = "VALIDATED"
NOT_VALIDATED = "NOT_VALIDATED"
AC1_METHOD = "gwet_ac1_binary_multi_rater"
AC1_REFERENCE = PANEL_PROTOCOL["reference"]

ARCHETYPES = tuple(a.value for a in Archetype)
_GOLD = GOLD_RULES["gold-v2-cand-A"]
EXPECTED_SETS: dict[str, tuple[str, ...]] = {a.value: tuple(m for m in MODALITIES if m in _GOLD.expected_by_archetype[a]) for a in Archetype}


def _threshold(x: float | int | Fraction) -> Fraction:
    """Umbral como racional EXACTO a partir de su representación decimal más corta (0.70 → 7/10; 0.85 → 17/20), sin el error binario del float."""
    return x if isinstance(x, Fraction) else Fraction(repr(x))


def _ac1_exact(approvals: Sequence[int], n: int) -> Fraction:
    """AC1 en aritmética RACIONAL exacta (misma fórmula que `gwet_ac1_binary_multi_rater`). Solo decide la frontera de los umbrales: el valor reportado sigue siendo el float."""
    n_items = len(approvals)
    p_a = sum(Fraction(a * (a - 1) + (n - a) * (n - a - 1), n * (n - 1)) for a in approvals) / n_items
    pi = Fraction(sum(approvals), n_items * n)
    p_e = 2 * pi * (1 - pi)
    return (p_a - p_e) / (1 - p_e)


def _validated(votes: Mapping[str, Sequence[bool]]) -> tuple[int, dict[str, int]]:
    """(n de evaluadores, aprobaciones por arquetipo). Exige los 4 arquetipos con el MISMO n ≥ 2 de votos booleanos."""
    if set(votes) != set(ARCHETYPES):
        raise ValueError(f"se esperaban exactamente los arquetipos {ARCHETYPES}")
    sizes = {len(votes[a]) for a in ARCHETYPES}
    if len(sizes) != 1 or min(sizes) < 2:
        raise ValueError("los 4 arquetipos deben tener el mismo número (≥ 2) de evaluadores")
    for a in ARCHETYPES:
        if any(not isinstance(v, (bool, int)) or v not in (0, 1) for v in votes[a]):
            raise ValueError(f"los votos deben ser Aprobar (True) / Rechazar (False): {a}")
    return sizes.pop(), {a: sum(1 for v in votes[a] if v) for a in ARCHETYPES}


def gwet_ac1_binary_multi_rater(votes: Mapping[str, Sequence[bool]]) -> dict:
    """Gwet AC1 multi-evaluador para respuestas binarias (Gwet, 2008): los 4 arquetipos son los ítems y los n evaluadores los jueces.
        p_a = (1/N) Σ_i [a_i(a_i − 1) + (n − a_i)(n − a_i − 1)] / (n(n − 1))       (acuerdo observado por pares; a_i = aprobaciones del ítem i)
        π   = Σ_i a_i / (N·n)  (proporción global de «aprobar»);   p_e = 2π(1 − π)  (= Σ_k π_k(1 − π_k)/(q − 1), q = 2)
        AC1 = (p_a − p_e) / (1 − p_e)
    Devuelve observed_agreement, chance_agreement, ac1 (float), ac1_exact (fracción exacta, solo trazabilidad), n_items, n_raters y category_marginals."""
    n, approvals = _validated(votes)
    n_items = len(ARCHETYPES)
    exact = _ac1_exact(list(approvals.values()), n)
    p_a = sum((a * (a - 1) + (n - a) * (n - a - 1)) / (n * (n - 1)) for a in approvals.values()) / n_items
    pi = sum(approvals.values()) / (n_items * n)
    p_e = 2 * pi * (1 - pi)
    return {"method": AC1_METHOD, "reference": AC1_REFERENCE, "observed_agreement": p_a, "chance_agreement": p_e, "ac1": (p_a - p_e) / (1 - p_e),
            "ac1_exact": f"{exact.numerator}/{exact.denominator}", "n_items": n_items, "n_raters": n, "category_marginals": {"approve": pi, "reject": 1 - pi}}


def votes_matrix(votes: Mapping[str, Sequence[bool]]) -> list[dict]:
    """Matriz ABSOLUTA de votos (obligatoria en el resultado): archetype | approve | reject | total | approval_rate | majority_status."""
    n, approvals = _validated(votes)
    rows = []
    for a in ARCHETYPES:
        yes, no = approvals[a], n - approvals[a]
        status = "approve_majority" if yes > n / 2 else ("reject_majority" if no > n / 2 else "tie")
        rows.append({"archetype": a, "approve": yes, "reject": no, "total": n, "approval_rate": yes / n, "majority_status": status})
    return rows


def raw_agreement(votes: Mapping[str, Sequence[bool]]) -> dict:
    """R5a: juicios coincidentes con la categoría mayoritaria de su arquetipo / (4·n). Un empate no tiene mayoría: sus juicios no cuentan como coincidentes."""
    n, _ = _validated(votes)
    rows = votes_matrix(votes)
    coincident = sum(max(r["approve"], r["reject"]) for r in rows if r["majority_status"] != "tie")
    return {"value": coincident / (len(rows) * n), "coincident": coincident, "denominator": len(rows) * n, "tied_archetypes": [r["archetype"] for r in rows if r["majority_status"] == "tie"]}


def analyze_archetype_panel(votes: Mapping[str, Sequence[bool]], rule_version: str) -> dict:
    """Análisis y decisión del panel por arquetipo. `rule_version` es la versión OFICIAL cuyo gold se valida (queda registrada en el resultado)."""
    sizes = {a: len(votes.get(a, ())) for a in ARCHETYPES}
    n = min(sizes.values())
    if n < MIN_EVALUATORS or len(set(sizes.values())) != 1:
        return {"status": PENDING, "n_evaluators": n, "rule_version": rule_version, "n_by_archetype": sizes, "validation_status": PENDING}
    matrix = votes_matrix(votes)
    raw = raw_agreement(votes)
    ac1 = gwet_ac1_binary_multi_rater(votes)
    total = len(matrix) * n
    approvals = sum(r["approve"] for r in matrix)
    approved = {r["archetype"]: r["approve"] > n / 2 for r in matrix}                     # archetype_approved[a] = approvals[a] > n/2 (5/10 NO aprueba)
    majority_rejection = {r["archetype"]: r["reject"] > n / 2 for r in matrix}
    tie = {r["archetype"]: r["approve"] == r["reject"] for r in matrix}
    majority_rej = [a for a, v in majority_rejection.items() if v]
    every_approved = all(approved.values())
    no_majority_rejection = not any(majority_rejection.values())
    no_tie = not any(tie.values())
    # Fronteras decididas en aritmética RACIONAL exacta (PX6): un AC1 matemáticamente igual a 0.70 NO pasa aunque el float salga 0.7000000000000002; el valor reportado sigue siendo el float.
    ac1_pass = bool(_ac1_exact([r["approve"] for r in matrix], n) > _threshold(AC1_THRESHOLD))                       # AC1 ≤ 0.70 no pasa
    raw_pass = bool(Fraction(raw["coincident"], raw["denominator"]) >= _threshold(RAW_AGREEMENT_MIN))               # acuerdo crudo < 0.85 no pasa
    valid = bool(ac1_pass and raw_pass and every_approved and no_majority_rejection and no_tie)
    reasons = [f"archetype_not_approved:{a}" for a, ok in approved.items() if not ok] + [f"majority_rejection:{a}" for a in majority_rej] + \
              [f"tie:{a}" for a, t in tie.items() if t] + ([] if ac1_pass else ["ac1_not_above_threshold"]) + ([] if raw_pass else ["raw_agreement_below_minimum"])
    return {"status": "COMPLETO (n≥10)", "n_evaluators": n, "n_judgments": total, "rule_version": rule_version, "panel_protocol": PANEL_PROTOCOL_VERSION,
            "expected_sets": {a: list(EXPECTED_SETS[a]) for a in ARCHETYPES}, "votes_matrix": matrix,
            "archetype_approved": approved, "majority_rejection": majority_rejection, "tie": tie, "every_archetype_approved": every_approved,
            "majority_rejection_archetypes": majority_rej, "no_majority_rejection": no_majority_rejection, "tied_archetypes": raw["tied_archetypes"], "no_tie": no_tie,
            "raw_agreement": raw["value"], "raw_agreement_detail": {"coincident": raw["coincident"], "denominator": raw["denominator"]}, "raw_agreement_min": RAW_AGREEMENT_MIN, "raw_agreement_pass": raw_pass,
            "ac1": ac1["ac1"], "ac1_detail": ac1, "ac1_threshold": AC1_THRESHOLD, "ac1_pass": ac1_pass,
            "approval_rate": approvals / total,                                                # DESCRIPTIVO: no activa ningún fallback
            "panel_valid": valid, "validation_status": VALIDATED if valid else NOT_VALIDATED,
            "rule_version_review": not valid, "review_reasons": reasons}                          # X6: nunca None; False solo si el panel es válido
