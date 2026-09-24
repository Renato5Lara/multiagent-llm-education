"""Redund(S): solapamiento de contenido NO perteneciente al ConceptAnchor
(DECISION-CLOSURE §6.1) — para no contradecir a Coher, que premia compartir
justamente los términos-ancla.

Redund = media de Jaccard de trigramas de tokens de contenido (anclas, identificadores del
ancla, palabras reservadas y vocabulario estructural excluidos) sobre los tres pares
(código–texto, código–diagrama, diagrama–texto). Rango [0,1]; determinista.
"""

from __future__ import annotations

from adaptation_swarm.fitness.coher import diagram_labels
from adaptation_swarm.fitness.text_utils import content_tokens, jaccard, ngrams
from adaptation_swarm.multimodal.anchor import ConceptAnchor


def redund(anchor: ConceptAnchor, code: str, diagram: str, text: str) -> float:
    excl = anchor.excluded_tokens
    grams = {
        "code": ngrams(content_tokens(code, excl)),
        "diagram": ngrams(content_tokens("\n".join(diagram_labels(diagram)), excl)),
        "text": ngrams(content_tokens(text, excl)),
    }
    pairs = (("code", "text"), ("code", "diagram"), ("diagram", "text"))
    return sum(jaccard(grams[a], grams[b]) for a, b in pairs) / len(pairs)
