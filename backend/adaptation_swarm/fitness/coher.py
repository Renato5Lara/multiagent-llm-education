"""Coher(S) = (a + b + c) / 3  (DECISION-CLOSURE §6.1) — determinista, sin modelos.

 (a) anclaje léxico: fracción de términos-ancla presentes en cada pieza (código, diagrama,
     texto), promediada sobre las tres piezas;
 (b) diagrama↔código: fracción de identificadores de las etiquetas del diagrama que son
     identificadores del código (vocabulario estructural excluido; 0 si no hay ninguno);
 (c) texto↔código: fracción de identificadores clave del ancla mencionados en el texto.
Rango [0,1].
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from adaptation_swarm.fitness.text_utils import (
    DIAGRAM_STRUCTURAL, identifiers, word_forms, word_tokens,
)
from adaptation_swarm.multimodal.anchor import ConceptAnchor

_LABEL_RE = re.compile(r'\[\s*"([^"]*)"\s*\]|\{\s*"([^"]*)"\s*\}|\(\s*"([^"]*)"\s*\)|\|([^|]*)\|')


@dataclass(frozen=True, slots=True)
class CoherBreakdown:
    a_anchor_terms: float
    b_diagram_code: float
    c_text_code: float

    @property
    def value(self) -> float:
        return (self.a_anchor_terms + self.b_diagram_code + self.c_text_code) / 3.0


def diagram_labels(mermaid: str) -> list[str]:
    """Etiquetas de nodo/arista de un diagrama Mermaid generado por AG3."""
    labels: list[str] = []
    for m in _LABEL_RE.finditer(mermaid):
        labels.append(next(g for g in m.groups() if g is not None))
    return labels


def _term_presence(terms: tuple[str, ...], piece: str) -> float:
    if not terms:
        return 0.0
    tokens = set(word_tokens(piece))
    hits = sum(1 for t in terms if word_forms(t) & tokens)
    return hits / len(terms)


def anchor_presence(anchor: ConceptAnchor, code: str, diagram: str, text: str) -> float:
    pieces = (code, "\n".join(diagram_labels(diagram)), text)
    return sum(_term_presence(anchor.terms, p) for p in pieces) / 3.0


def diagram_code_grounding(code: str, diagram: str) -> float:
    code_idents = set(identifiers(code))
    label_tokens = {
        t for lab in diagram_labels(diagram) for t in identifiers(lab)
        if len(t) > 1 and t not in DIAGRAM_STRUCTURAL
    }
    if not label_tokens:
        return 0.0
    return len(label_tokens & code_idents) / len(label_tokens)


def text_code_grounding(anchor: ConceptAnchor, text: str) -> float:
    if not anchor.code_identifiers:
        return 0.0
    text_idents = set(identifiers(text))
    return sum(1 for i in anchor.code_identifiers if i in text_idents) / len(anchor.code_identifiers)


def coher(anchor: ConceptAnchor, code: str, diagram: str, text: str) -> CoherBreakdown:
    return CoherBreakdown(
        a_anchor_terms=anchor_presence(anchor, code, diagram, text),
        b_diagram_code=diagram_code_grounding(code, diagram),
        c_text_code=text_code_grounding(anchor, text),
    )
