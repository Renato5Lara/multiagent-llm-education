"""Registro EXPLÍCITO de versiones del panel por arquetipo: relaciona, sin fallbacks, `panel_protocol_version` ↔ `rule_version` ↔ gold/conjuntos esperados ↔ plantilla ↔ estado.

Existe para que un juicio humano NUNCA pueda quedar registrado bajo una versión distinta de la que se mostró al evaluador (riesgo detectado en la auditoría F1 v2/v3: `import_archetype_csv` guardaba todo con la
`rule_version` v2 fija). `metrics/gold_panel.py` NO se modifica: su sha256 está certificado (PX8) y sigue siendo la implementación del estadístico (Gwet AC1 y criterios PX1–PX7, que NO cambian en v3); su `EXPECTED_SETS`
es el gold v2 HISTÓRICO. Aquí se elige la configuración y se corrige el reporte (`expected_sets`, `panel_protocol`, `rule_version`) para la versión seleccionada.

    v2  HISTÓRICO OFICIAL        `panel-arq-ac1-maj-tie0-v2` · gold `gold-v2-cand-A` · inclusión `incl-ge1` (valores sellados en `rubric_v2`; no se cambia nada)
    v3  DEFINIDO, NO APROBADO — `panel_protocol_version` y `full_rule_version` son identificadores técnicos definidos en `rubric_v3` (el nombre es una decisión de ingeniería; los componentes del protocolo son
        los cerrados en DECISION-CLOSURE §15). NO se registran en ningún `APPROVED_RULE_VERSIONS` hasta el sellado del pre-registro v3: no sirven para una evaluación oficial. Los conjuntos esperados son los de la
        matriz P2 del 28/09 (`rubric_v3`); el panel valida el GOLD: la inclusión F1 (`incl-rel20`) no se recalcula aquí.

Resolución sin inferencias: `get_panel_spec(<protocolo>)` y `spec_for_rule_version(<rule_version>)` lanzan `KeyError` si no están registrados; no existe ningún camino v3 → v2.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from adaptation_swarm.gold import rubric_v3
from adaptation_swarm.gold.rubric_v2 import GOLD_RULES as GOLD_RULES_V2, PANEL_PROTOCOL_VERSION as V2_PROTOCOL, get_rule as get_rule_v2, official_version as official_version_v2
from adaptation_swarm.metrics import gold_panel
from adaptation_swarm.profiles.models import Archetype
from adaptation_swarm.pso.space import MODALITIES

STATUS_V2 = "HISTORICAL_OFFICIAL_V2"
STATUS_V3 = "PROVISIONAL_TECHNICAL_PREPARATION_V3_NOT_APPROVED"

V3_PROTOCOL = rubric_v3.PANEL_PROTOCOL_VERSION                                         # identificador técnico definido en rubric_v3; su APROBACIÓN se registra con el sellado
V3_RULE_VERSION = rubric_v3.FULL_RULE_VERSION


@dataclass(frozen=True)
class PanelSpec:
    panel_protocol_version: str
    rule_version: str                       # clave con la que se persisten los juicios (`GoldPanelArchetypeRating.rule_version`, ≤ 80 caracteres)
    gold_rule_version: str
    inclusion_rule_id: str
    expected_sets: Mapping[str, tuple[str, ...]]
    template: str                           # archivo de plantilla bajo human_eval/templates/
    status: str

    @property
    def official(self) -> bool:
        return self.status == STATUS_V2

    def shown(self, archetype: str) -> str:
        """Texto que la plantilla muestra al evaluador para el arquetipo (conjuntos en el orden canónico de modalidades)."""
        return "+".join(self.expected_sets[archetype])


def _ordered(sets: Mapping[Archetype, frozenset[str]]) -> dict[str, tuple[str, ...]]:
    return {a.value: tuple(m for m in MODALITIES if m in sets[a]) for a in Archetype}


_V2_RULE = get_rule_v2("gold-v2-cand-A", "incl-ge1")
SPEC_V2 = PanelSpec(V2_PROTOCOL, official_version_v2(_V2_RULE), "gold-v2-cand-A", "incl-ge1", dict(gold_panel.EXPECTED_SETS), "gold_panel_archetype_template.csv", STATUS_V2)
SPEC_V3 = PanelSpec(V3_PROTOCOL, V3_RULE_VERSION, rubric_v3.GOLD_RULE_VERSION, rubric_v3.INCLUSION_RULE_ID,
                    _ordered(rubric_v3.GOLD_RULES[rubric_v3.GOLD_RULE_VERSION].expected_by_archetype), "gold_panel_archetype_template_v3_provisional.csv", STATUS_V3)

PANEL_SPECS: dict[str, PanelSpec] = {s.panel_protocol_version: s for s in (SPEC_V2, SPEC_V3)}
assert len(PANEL_SPECS) == 2 and len({s.rule_version for s in PANEL_SPECS.values()}) == 2
assert all(len(s.rule_version) <= 80 for s in PANEL_SPECS.values())
assert SPEC_V2.expected_sets == gold_panel.EXPECTED_SETS                                  # el registro v2 ES el gold histórico, no una copia editable


def get_panel_spec(panel_protocol_version: str) -> PanelSpec:
    try:
        return PANEL_SPECS[panel_protocol_version]
    except KeyError:
        raise KeyError(f"panel_protocol_version no registrado: {panel_protocol_version!r}; registrados: {sorted(PANEL_SPECS)}") from None


def spec_for_rule_version(rule_version: str) -> PanelSpec:
    for s in PANEL_SPECS.values():
        if s.rule_version == rule_version:
            return s
    raise KeyError(f"rule_version del panel no registrada: {rule_version!r}; registradas: {sorted(s.rule_version for s in PANEL_SPECS.values())}")


def analyze_panel(spec: PanelSpec, votes: Mapping[str, list[bool]]) -> dict:
    """Análisis del panel con el estadístico y los criterios de `gold_panel` (idénticos en v2 y v3: PX1–PX7 no cambian) y el REPORTE de la versión seleccionada: `rule_version`, `panel_protocol`, `expected_sets`
    y estado. Sin esta capa, el resultado de un panel v3 mostraría los conjuntos y el protocolo v2."""
    r = gold_panel.analyze_archetype_panel(votes, spec.rule_version)
    r["panel_protocol"] = spec.panel_protocol_version
    r["expected_sets"] = {a: list(spec.expected_sets[a]) for a in gold_panel.ARCHETYPES}
    r["panel_spec_status"] = spec.status
    r["official"] = spec.official
    return r
