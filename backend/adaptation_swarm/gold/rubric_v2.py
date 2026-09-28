"""Reglas de gold e inclusión de la familia `gold-v2` — TODAS PROVISIONALES hasta que el asesor apruebe una (D1, D2; 2026-09-25).

El asesor rechazó el desempate arbitrario de Balanced hacia `code` y pidió evaluar la inclusión/exclusión 4×4 con el audio incluido, con
nueva `rule_version` y nueva corrida. La respuesta NO define (a) qué significa que una modalidad esté «incluida» en `g_best`, ni (b) el
conjunto esperado de cada arquetipo. Este módulo por eso NO elige: ofrece candidatas explícitas y una guardia de aprobación.

    · No existe ninguna regla «por defecto»: siempre hay que pasar el identificador de la regla.
    · `APPROVED_RULE_VERSIONS` es el REGISTRO TÉCNICO (guardrail de ejecución) de las reglas aprobadas por el asesor; NO es el acto de aprobación, que es documental y anterior (2026-09-26). Una revisión
      añade aquí su `official_version(rule)` (gold + inclusión + agregación + panel); `require_approved()` lo usa como barrera y, para toda regla ausente, lanza `RuleNotApproved` y todo resultado
      se marca PROVISIONAL. El commit de sellado 5d7d12c conservó este conjunto vacío; el registro de la regla aprobada es posterior (ver `addendum_rule_registration_2026-09-27.json`).
    · gold-v1 (`gold/rubric.py`) NO se toca; `LegacyDominantRule` lo reproduce solo para comparar con la evidencia histórica.

INDEPENDENCIA DE W (DECISION-CLOSURE §6.3): el gold se deriva del arquetipo (y, en la candidata B, de su CENTROIDE constante), nunca del `W`
de AG1 caso por caso.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Mapping, Protocol, Sequence

from adaptation_swarm.gold import rubric as gold_v1
from adaptation_swarm.gold.labels_v2 import ALL_MODALITIES, modality_set
from adaptation_swarm.profiles.archetypes import CENTROIDS, CENTROIDS_VERSION
from adaptation_swarm.profiles.models import Archetype, Difficulty
from adaptation_swarm.pso.space import MODALITIES

FAMILY = "gold-v2"
STATUS_PROVISIONAL = "PROVISIONAL"
STATUS_OFFICIAL = "OFICIAL"

# Componentes de la `rule_version` OFICIAL (respuestas del asesor, 2026-09-26): la versión aprobada representa CONJUNTAMENTE la regla de inclusión y los conjuntos esperados (ambos en
# `MultilabelRule.rule_version`), la agregación de `F1_adapt` (P3: `samples`, media del F1 por caso) y el protocolo del panel (P4, X1–X5, X3-bis), que incluye el estadístico (Gwet AC1), la
# exigencia de mayoría aprobatoria por arquetipo y el empate como rechazo. La especificación completa del panel vive en `PANEL_PROTOCOL` (su huella se registra en el plan de réplicas).
OFFICIAL_AGGREGATION = "samples"
PANEL_PROTOCOL_VERSION = "panel-arq-ac1-maj-tie0-v2"
PANEL_PROTOCOL: dict = {
    "version": PANEL_PROTOCOL_VERSION, "unit": "archetype", "n_archetypes": 4, "min_evaluators": 10, "response": "approve_reject",
    "statistic": "gwet_ac1_binary_multi_rater", "reference": "Gwet, K. L. (2008). Br. J. Math. Stat. Psychol. 61(1), 29-48",
    "ac1_threshold": 0.70, "ac1_comparison": ">", "raw_agreement_min": 0.85, "raw_agreement_comparison": ">=",
    "archetype_approval": "approvals > n/2", "majority_rejection": "rejects > n/2", "tie": "reject (no aprobado; obliga a revisar la rule_version)",
    "denominator": "4*n (todos los juicios recolectados)", "combination": "AND(ac1, raw_agreement, every_archetype_approved, no_majority_rejection, no_tie)",
    "rule_version_review": "True si algún arquetipo no aprobado, algún empate, algún rechazo mayoritario, AC1 <= 0.70 o acuerdo crudo < 0.85 (X2, X3-bis, X6); nunca None",
    "fleiss_kappa": "fuera del protocolo oficial (solo gold-v1, histórico)"}


def panel_protocol_fingerprint() -> str:
    return _fingerprint(PANEL_PROTOCOL)


# Registro técnico (guardrail de ejecución) de las reglas aprobadas; `require_approved()` lo usa como barrera y `is_approved` además exige que sea una gold-v2 registrada. NO es el acto de aprobación
# metodológica (documental, 2026-09-26). Contiene la única regla aprobada, registrada el 2026-09-27 (resolución del asesor, opción A) DESPUÉS del sellado 5d7d12c, cuyo `rubric_v2.py` lo tenía vacío.
APPROVED_RULE_VERSIONS: frozenset[str] = frozenset({"gold-v2-cand-A+incl-ge1+samples+panel-arq-ac1-maj-tie0-v2"})


class RuleNotApproved(RuntimeError):
    """Se intentó usar como OFICIAL una regla que el asesor no ha aprobado."""


class NoRuleSelected(ValueError):
    """No se indicó una regla: no hay regla por defecto (evita fijar la de Balanced en silencio)."""


class EvaluationRule(Protocol):
    rule_version: str

    def expected_set(self, archetype: Archetype, difficulty: Difficulty | None) -> frozenset[str] | None: ...
    def predicted_set(self, emphasis: Sequence[int]) -> frozenset[str]: ...
    def to_dict(self) -> dict: ...


def _fingerprint(d: dict) -> str:
    return hashlib.sha256(json.dumps(d, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")).hexdigest()


# ── regla de INCLUSIÓN: de e_m ∈ {0,1,2} de g_best a un conjunto de modalidades ─────────────────────────────────────
@dataclass(frozen=True)
class InclusionRule:
    """Cuándo se considera «incluida» una modalidad en `g_best`. Las 4 modalidades están SIEMPRE presentes en el paquete (RF05); lo que varía es su
    énfasis e_m (0 apoyo, 1 estándar, 2 principal), así que «incluida» es una decisión de definición, no un hecho del sistema."""

    rule_id: str
    kind: str          # "threshold": e_m ≥ parameter · "top_set": e_m ≥ max(e) − parameter
    parameter: int
    description: str

    def __post_init__(self) -> None:
        if self.kind not in ("threshold", "top_set"):
            raise ValueError(f"kind desconocido: {self.kind!r}")
        if self.parameter < 0:
            raise ValueError("parameter ≥ 0")

    def predicted_set(self, emphasis: Sequence[int]) -> frozenset[str]:
        if len(emphasis) != len(MODALITIES):
            raise ValueError(f"se esperaban {len(MODALITIES)} énfasis")
        if self.kind == "threshold":
            return frozenset(m for m, e in zip(MODALITIES, emphasis) if e >= self.parameter)
        top = max(emphasis)
        return frozenset(m for m, e in zip(MODALITIES, emphasis) if e >= top - self.parameter)

    def to_dict(self) -> dict:
        return {"rule_id": self.rule_id, "kind": self.kind, "parameter": self.parameter, "description": self.description}


INCLUSION_RULES: dict[str, InclusionRule] = {r.rule_id: r for r in (
    InclusionRule("incl-ge1", "threshold", 1, "incluida si e_m ≥ 1 (estándar o principal)"),
    InclusionRule("incl-ge2", "threshold", 2, "incluida solo si e_m = 2 (principal)"),
    InclusionRule("incl-top-tol0", "top_set", 0, "incluida si e_m alcanza el máximo (empates exactos incluidos)"),
    InclusionRule("incl-top-tol1", "top_set", 1, "incluida si e_m está a ≤ 1 nivel del máximo"),
)}


# ── GOLD: conjunto esperado por arquetipo ─────────────────────────────────────────────────────────────────────────
def _set_from_centroid(archetype: Archetype, tol: float) -> frozenset[str]:
    """Modalidades cuyo peso en el CENTROIDE del arquetipo está a ≤ `tol` del máximo (constante preregistrada; no depende de W caso por caso)."""
    w = CENTROIDS[archetype].by_modality()
    top = max(w)
    return frozenset(m for m, v in zip(MODALITIES, w) if top - v <= tol + 1e-12)


@dataclass(frozen=True, eq=False)
class GoldRuleV2:
    rule_version: str
    description: str
    expected_by_archetype: Mapping[Archetype, frozenset[str] | None]        # None = «sin gold definido» (el caso se cuenta aparte y no puntúa)
    cell_overrides: Mapping[tuple[Archetype, Difficulty], frozenset[str] | None] = field(default_factory=dict)

    def expected_set(self, archetype: Archetype, difficulty: Difficulty | None = None) -> frozenset[str] | None:
        if difficulty is not None and (archetype, difficulty) in self.cell_overrides:
            return self.cell_overrides[(archetype, difficulty)]
        return self.expected_by_archetype[archetype]

    @property
    def status(self) -> str:
        """OFICIAL solo si es una gold-v2 REGISTRADA y alguna regla de evaluación aprobada la usa (`<gold>+<inclusión>`); coherente con `is_approved`."""
        registered = GOLD_RULES.get(self.rule_version) is self
        return STATUS_OFFICIAL if registered and any(v.startswith(f"{self.rule_version}+") for v in APPROVED_RULE_VERSIONS) else STATUS_PROVISIONAL

    def to_dict(self) -> dict:
        exp = {a.value: (None if s is None else [m for m in MODALITIES if m in s]) for a, s in self.expected_by_archetype.items()}
        ov = {f"{a.value}|{d.value}": (None if s is None else [m for m in MODALITIES if m in s]) for (a, d), s in self.cell_overrides.items()}
        return {"rule_version": self.rule_version, "family": FAMILY, "description": self.description, "centroids_version": CENTROIDS_VERSION,
                "expected_by_archetype": exp, "cell_overrides": ov}

    def fingerprint(self) -> str:
        return _fingerprint(self.to_dict())


def _table(**by_arch: frozenset[str] | None) -> dict[Archetype, frozenset[str] | None]:
    return {Archetype(k): v for k, v in by_arch.items()}


_A = _table(visual_dominant=modality_set({"diagram"}), logical_syntactic=modality_set({"code"}),
            explanatory_conceptual=modality_set({"text"}), balanced_multimodal=modality_set(ALL_MODALITIES))

GOLD_RULES: dict[str, GoldRuleV2] = {g.rule_version: g for g in (
    GoldRuleV2("gold-v2-cand-A", "Conjunto esperado: cada arquetipo espera su modalidad dominante; Balanced espera las cuatro (sin desempate).", _A),
    GoldRuleV2("gold-v2-cand-B-tol0.05", "Conjunto esperado = modalidades a ≤ 0.05 del máximo del CENTROIDE (misma τ que gold-v1). Con centroids-v1 coincide con la candidata A.",
               {a: _set_from_centroid(a, 0.05) for a in Archetype}),
    GoldRuleV2("gold-v2-cand-B-tol0.35", "Como B pero con tolerancia amplia 0.35 (límite superior de sensibilidad): visual y lógico esperan además el par código/diagrama.",
               {a: _set_from_centroid(a, 0.35) for a in Archetype}),
)}


# ── REGLAS DE EVALUACIÓN (gold + inclusión) ───────────────────────────────────────────────────────────────────────
@dataclass(frozen=True, eq=False)
class MultilabelRule:
    """Regla de evaluación multietiqueta 4×4: un gold v2 y una regla de inclusión, ambos EXPLÍCITOS."""

    gold: GoldRuleV2
    inclusion: InclusionRule

    @property
    def rule_version(self) -> str:
        return f"{self.gold.rule_version}+{self.inclusion.rule_id}"

    def expected_set(self, archetype: Archetype, difficulty: Difficulty | None = None) -> frozenset[str] | None:
        return self.gold.expected_set(archetype, difficulty)

    def predicted_set(self, emphasis: Sequence[int]) -> frozenset[str]:
        return self.inclusion.predicted_set(emphasis)

    def to_dict(self) -> dict:
        return {"rule_version": self.rule_version, "gold": self.gold.to_dict(), "inclusion": self.inclusion.to_dict()}


class LegacyDominantRule:
    """Reproduce la definición HISTÓRICA (gold-v1 + modalidad dominante con desempate) como conjuntos de UN elemento. Solo sirve para comparar
    con las corridas congeladas; no pertenece a la familia gold-v2 ni puede aprobarse como regla nueva."""

    rule_version = f"{gold_v1.RULE_VERSION}+dominant-compat"

    def expected_set(self, archetype: Archetype, difficulty: Difficulty | None = None) -> frozenset[str] | None:
        if difficulty is None:
            raise ValueError("gold-v1 se define por celda (arquetipo × dificultad)")
        return frozenset({gold_v1.expected_dominant(archetype, difficulty)})

    def predicted_set(self, emphasis: Sequence[int]) -> frozenset[str]:
        return frozenset({gold_v1.predicted_dominant(emphasis)})

    def to_dict(self) -> dict:
        return {"rule_version": self.rule_version, "family": "gold-v1", "note": "definición histórica de etiqueta única; NO es una regla v2"}


# ── acceso explícito y guardia de aprobación ──────────────────────────────────────────────────────────────────────
def get_rule(gold_rule_version: str | None, inclusion_rule_id: str | None) -> MultilabelRule:
    """Construye una regla de evaluación. NO hay valores por defecto: ambos identificadores son obligatorios."""
    if not gold_rule_version or not inclusion_rule_id:
        raise NoRuleSelected("indique gold_rule_version e inclusion_rule_id: no hay regla por defecto (la de Balanced no se fija en silencio)")
    try:
        return MultilabelRule(GOLD_RULES[gold_rule_version], INCLUSION_RULES[inclusion_rule_id])
    except KeyError as exc:
        raise KeyError(f"regla desconocida: {exc.args[0]!r}; gold: {sorted(GOLD_RULES)}; inclusión: {sorted(INCLUSION_RULES)}") from exc


def is_registered_v2(rule: object) -> bool:
    """`rule` es una `MultilabelRule` de la familia gold-v2 construida con el gold y la inclusión REGISTRADOS (`GOLD_RULES`/`INCLUSION_RULES`). Una regla histórica
    (`LegacyDominantRule`), una regla ad hoc o una copia alterada de una registrada no lo son, aunque repitan una `rule_version`."""
    return (type(rule) is MultilabelRule
            and GOLD_RULES.get(rule.gold.rule_version) is rule.gold
            and INCLUSION_RULES.get(rule.inclusion.rule_id) == rule.inclusion)


def official_version(rule: EvaluationRule) -> str:
    """`rule_version` OFICIAL: `<gold>+<inclusión>+<agregación>+<protocolo del panel>`. Es la ÚNICA clave que `APPROVED_RULE_VERSIONS` reconoce: aprobar solo la parte de
    gold/inclusión (P1/P2) no aprueba nada, porque la versión oficial debe cubrir también P3 y P4. Para una regla que no es una `MultilabelRule` (p. ej. la histórica) solo
    devuelve su versión, que nunca puede aprobarse (`is_approved` exige una regla gold-v2 registrada)."""
    if type(rule) is not MultilabelRule:
        return rule.rule_version
    return f"{rule.rule_version}+{OFFICIAL_AGGREGATION}+{PANEL_PROTOCOL_VERSION}"


def is_approved(rule: EvaluationRule) -> bool:
    """Aprobada = regla gold-v2 registrada Y su `official_version` (gold+inclusión+agregación+panel) figura en `APPROVED_RULE_VERSIONS`. Añadir a ese conjunto la versión
    de una regla histórica o inexistente no la aprueba."""
    return is_registered_v2(rule) and official_version(rule) in APPROVED_RULE_VERSIONS


def status_of(rule: EvaluationRule) -> str:
    return STATUS_OFFICIAL if is_approved(rule) else STATUS_PROVISIONAL


def require_approved(rule: EvaluationRule) -> None:
    if not is_approved(rule):
        raise RuleNotApproved(f"la regla {rule.rule_version!r} no está aprobada por el asesor: solo puede usarse como PROVISIONAL")
