"""Regla de evaluación de K = 10 v3 — P1 (inclusión) y P2 (gold) APROBADAS por el asesor el 28/09/2026 (`ESPECIFICACION-METODOLOGICA-P1-P2-2026-09-28.md` §3 y §4). Capa ADITIVA: módulo independiente de
`rubric_v2.py` (código sellado de K = 10 v2, que no se modifica), con su propio registro de reglas y su propio registro de aprobación.

P1 — inclusión:   S = { m | e_m ≥ 1  Y  e_m / Σe ≥ 0.20 },  con e_m ∈ {0,1,2}; Σe = 0 ⇒ S = ∅ (F1 = 0). La comparación es EXACTA (aritmética entera: 5·e_m ≥ Σe), sin coma flotante: hay casos
                  exactamente en el límite (p. ej. e = (1,1,1,2) da s = 0.20, que se INCLUYE por ser «≥»).
P2 — gold:        matriz explícita, normativa e inmutable, dependiente solo del arquetipo (nunca de W ni de la dificultad):
                      Visual-Dominant {diagram, code} · Logical-Syntactic {code, diagram} · Explanatory-Conceptual {text, diagram, code} · Balanced-Multimodal {code, diagram, text, audio}
                  `audio` solo aparece en Balanced y Balanced espera las cuatro modalidades (sin desempate).

Cumple el contrato `EvaluationRule` de `rubric_v2` (`rule_version`, `expected_set`, `predicted_set`, `to_dict`), de modo que la métrica de `f1_multilabel` puede consumirla. NO está conectada al ejecutor de K = 10:
el plan, la corrida y la evaluación v3 son piezas posteriores.

APROBACIÓN: `APPROVED_RULE_VERSIONS` de ESTE módulo está vacío. Su aprobación técnica se registrará con el sellado del pre-registro v3 (mismo procedimiento que siguió v2); no se añade nada al registro de `rubric_v2`. `official_version` identifica
solo la regla/rúbrica v3 (gold + inclusión); la agregación (P3) y el protocolo del panel (P4) se incorporarán a la versión completa al construir el pre-registro v3.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Mapping, Sequence

from adaptation_swarm.gold.labels_v2 import ALL_MODALITIES, modality_set
from adaptation_swarm.gold.rubric_v2 import NoRuleSelected, RuleNotApproved
from adaptation_swarm.profiles.models import Archetype, Difficulty
from adaptation_swarm.pso.space import MODALITIES

FAMILY = "gold-v3"
STATUS_PROVISIONAL = "PROVISIONAL"
STATUS_OFFICIAL = "OFICIAL"

GOLD_RULE_VERSION = "gold-v3-multimodal"
INCLUSION_RULE_ID = "incl-rel20"
RULE_VERSION = f"{GOLD_RULE_VERSION}+{INCLUSION_RULE_ID}"
# Identificador técnico del protocolo del panel de v3 (decisión de ingeniería: nombre, no metodología). Sus componentes (AC1, mayoría estricta, empate 5-5 inválido, umbrales) son los CERRADOS de
# DECISION-CLOSURE §15 y no cambian respecto de v2; solo cambia el gold que se muestra (matriz P2). Seguir el esquema de v2 (`panel-arq-ac1-maj-tie0-v2`) hace trazable la relación v2 → v3.
PANEL_PROTOCOL_VERSION = "panel-arq-ac1-maj-tie0-v3"
AGGREGATION_ID = "samples"                                  # = f1_multilabel.OFFICIAL_AGGREGATION (P3); verificado por prueba
FULL_RULE_VERSION = f"{RULE_VERSION}+{AGGREGATION_ID}+{PANEL_PROTOCOL_VERSION}"      # gold + inclusión + agregación + protocolo (≤ 80 caracteres: columna `rule_version`)

EMPHASIS_LEVELS = (0, 1, 2)            # e_m ∈ {0,1,2}: 0 apoyo · 1 estándar · 2 principal


def _fingerprint(d: dict) -> str:
    return hashlib.sha256(json.dumps(d, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")).hexdigest()


# ── P1: regla de INCLUSIÓN relativa ─────────────────────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class RelativeInclusionRule:
    """Una modalidad está incluida si e_m ≥ `min_emphasis` Y su proporción e_m / Σe ≥ `share_num` / `share_den` (comparación ENTERA exacta: `e_m · share_den ≥ share_num · Σe`)."""

    rule_id: str
    min_emphasis: int
    share_num: int
    share_den: int
    description: str

    def __post_init__(self) -> None:
        if self.min_emphasis < 1:
            raise ValueError("min_emphasis ≥ 1 (e_m = 0 nunca se incluye)")
        if self.share_num < 0 or self.share_den < 1 or self.share_num > self.share_den:
            raise ValueError("la proporción mínima debe ser share_num/share_den con 0 ≤ share_num ≤ share_den y share_den ≥ 1")

    def predicted_set(self, emphasis: Sequence[int]) -> frozenset[str]:
        if len(emphasis) != len(MODALITIES):
            raise ValueError(f"se esperaban {len(MODALITIES)} énfasis")
        if any(e not in EMPHASIS_LEVELS for e in emphasis):
            raise ValueError(f"e_m fuera del dominio {EMPHASIS_LEVELS}: {tuple(emphasis)}")
        total = sum(int(e) for e in emphasis)
        if total == 0:
            return frozenset()                                                   # Σe = 0 ⇒ S = ∅ (F1 = 0)
        return frozenset(m for m, e in zip(MODALITIES, emphasis) if e >= self.min_emphasis and int(e) * self.share_den >= self.share_num * total)

    def to_dict(self) -> dict:
        return {"rule_id": self.rule_id, "kind": "relative_share", "min_emphasis": self.min_emphasis, "share": f"{self.share_num}/{self.share_den}",
                "comparison": "e_m * share_den >= share_num * sum(e) (aritmética entera exacta)", "empty_total": "sum(e) = 0 => S = vacío", "description": self.description}


INCLUSION_RULES: dict[str, RelativeInclusionRule] = {r.rule_id: r for r in (
    RelativeInclusionRule(INCLUSION_RULE_ID, 1, 1, 5, "incluida si e_m ≥ 1 Y e_m / Σe ≥ 0.20 (comparación exacta: 5·e_m ≥ Σe); Σe = 0 ⇒ conjunto vacío"),
)}


# ── P2: GOLD por arquetipo (matriz explícita, normativa e inmutable) ────────────────────────────────────────────────
@dataclass(frozen=True, eq=False)
class GoldRuleV3:
    rule_version: str
    description: str
    expected_by_archetype: Mapping[Archetype, frozenset[str]]

    def __post_init__(self) -> None:
        if set(self.expected_by_archetype) != set(Archetype):
            raise ValueError("la matriz del gold debe definir los cuatro arquetipos")
        for arch, s in self.expected_by_archetype.items():
            modality_set(s)
            if not s:
                raise ValueError(f"el gold de {arch.value} no puede ser vacío")

    def expected_set(self, archetype: Archetype, difficulty: Difficulty | None = None) -> frozenset[str]:
        """Depende SOLO del arquetipo (la dificultad no interviene; tampoco W)."""
        return self.expected_by_archetype[archetype]

    @property
    def status(self) -> str:
        registered = GOLD_RULES.get(self.rule_version) is self
        return STATUS_OFFICIAL if registered and any(v.startswith(f"{self.rule_version}+") for v in APPROVED_RULE_VERSIONS) else STATUS_PROVISIONAL

    def to_dict(self) -> dict:
        exp = {a.value: [m for m in MODALITIES if m in s] for a, s in self.expected_by_archetype.items()}
        return {"rule_version": self.rule_version, "family": FAMILY, "description": self.description, "expected_by_archetype": exp, "depends_on": "archetype only"}

    def fingerprint(self) -> str:
        return _fingerprint(self.to_dict())


_GOLD_MATRIX: dict[Archetype, frozenset[str]] = {
    Archetype.VISUAL_DOMINANT: modality_set({"diagram", "code"}),
    Archetype.LOGICAL_SYNTACTIC: modality_set({"code", "diagram"}),
    Archetype.EXPLANATORY_CONCEPTUAL: modality_set({"text", "diagram", "code"}),
    Archetype.BALANCED_MULTIMODAL: modality_set(ALL_MODALITIES),              # las cuatro, SIN desempate
}

GOLD_RULES: dict[str, GoldRuleV3] = {g.rule_version: g for g in (
    GoldRuleV3(GOLD_RULE_VERSION, "Matriz P2 normativa: Visual {diagram, code}; Logical {code, diagram}; Explanatory {text, diagram, code}; Balanced las cuatro (audio solo en Balanced; sin desempate).", _GOLD_MATRIX),
)}


# ── REGLA DE EVALUACIÓN (gold + inclusión) ──────────────────────────────────────────────────────────────────────────
@dataclass(frozen=True, eq=False)
class MultilabelRuleV3:
    """Regla de evaluación multietiqueta 4×4 de v3: gold P2 + inclusión P1, ambos explícitos. Cumple el contrato `EvaluationRule`."""

    gold: GoldRuleV3
    inclusion: RelativeInclusionRule

    @property
    def rule_version(self) -> str:
        return f"{self.gold.rule_version}+{self.inclusion.rule_id}"

    def expected_set(self, archetype: Archetype, difficulty: Difficulty | None = None) -> frozenset[str]:
        return self.gold.expected_set(archetype, difficulty)

    def predicted_set(self, emphasis: Sequence[int]) -> frozenset[str]:
        return self.inclusion.predicted_set(emphasis)

    def to_dict(self) -> dict:
        return {"rule_version": self.rule_version, "gold": self.gold.to_dict(), "inclusion": self.inclusion.to_dict()}


# ── registro de APROBACIÓN propio de v3 (independiente del de v2) ───────────────────────────────────────────────────
# Vacío: se registra con el sellado del pre-registro v3. La clave será la `official_version` completa que fije el pre-registro (gold + inclusión + agregación + protocolo del panel), aún no emitida.
APPROVED_RULE_VERSIONS: frozenset[str] = frozenset()


def get_rule(gold_rule_version: str | None = None, inclusion_rule_id: str | None = None) -> MultilabelRuleV3:
    """Construye la regla v3. Ambos identificadores son obligatorios (no hay regla por defecto), igual que en v2."""
    if not gold_rule_version or not inclusion_rule_id:
        raise NoRuleSelected("indique gold_rule_version e inclusion_rule_id: no hay regla por defecto")
    try:
        return MultilabelRuleV3(GOLD_RULES[gold_rule_version], INCLUSION_RULES[inclusion_rule_id])
    except KeyError as exc:
        raise KeyError(f"regla desconocida: {exc.args[0]!r}; gold: {sorted(GOLD_RULES)}; inclusión: {sorted(INCLUSION_RULES)}") from exc


def is_registered_v3(rule: object) -> bool:
    """`rule` es una `MultilabelRuleV3` construida con el gold y la inclusión REGISTRADOS de v3. Una regla de v2, una ad hoc o una copia alterada no lo son, aunque repitan una `rule_version`."""
    return (type(rule) is MultilabelRuleV3
            and GOLD_RULES.get(rule.gold.rule_version) is rule.gold
            and INCLUSION_RULES.get(rule.inclusion.rule_id) == rule.inclusion)


def official_version(rule: object) -> str:
    """Identificador de la regla/rúbrica v3 (gold + inclusión). La agregación (P3) y el protocolo del panel (P4) se incorporan en el pre-registro v3, no aquí."""
    return rule.rule_version


def is_approved(rule: object) -> bool:
    """Aprobada = regla v3 registrada Y su `official_version` figura en el `APPROVED_RULE_VERSIONS` de ESTE módulo."""
    return is_registered_v3(rule) and official_version(rule) in APPROVED_RULE_VERSIONS


def status_of(rule: object) -> str:
    return STATUS_OFFICIAL if is_approved(rule) else STATUS_PROVISIONAL


def require_approved(rule: object) -> None:
    if not is_approved(rule):
        raise RuleNotApproved(f"la regla v3 {getattr(rule, 'rule_version', rule)!r} no está aprobada: solo puede usarse como PROVISIONAL")
