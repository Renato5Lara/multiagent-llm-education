"""ConceptAnchor — insumo común de AG2/AG3/AG4 y de Coher/Redund (DECISION-CLOSURE §6.1):

    {concept_id, concept_version, learning_objective_id, terms[], code_identifiers[]}

Se deriva UNA vez por concepto a partir del `Concept`/`LearningObjective` reales del
currículo y del código de referencia (especificación de comportamiento).
"""

from __future__ import annotations

import ast
import builtins
from dataclasses import asdict, dataclass

from adaptation_swarm.fitness.text_utils import STOPWORDS_ES, normalize, word_forms
from adaptation_swarm.schemas.ids import sha256_text

_BUILTINS = frozenset(dir(builtins))


@dataclass(frozen=True, slots=True)
class ConceptAnchor:
    concept_id: str
    concept_title: str
    concept_version: str
    learning_objective_id: str
    learning_objective_title: str
    terms: tuple[str, ...]
    code_identifiers: tuple[str, ...]
    function_names: tuple[str, ...]

    def to_dict(self) -> dict:
        return asdict(self)

    @property
    def excluded_tokens(self) -> frozenset[str]:
        """Vocabulario del ancla que Redund NO debe contar como solapamiento."""
        out: set[str] = set()
        for t in self.terms:
            out.update(word_forms(t))
        out.update(self.code_identifiers)
        for ident in self.code_identifiers:
            out.update(p for p in ident.split("_") if p)
        return frozenset(out)


def extract_terms(*titles: str) -> tuple[str, ...]:
    seen: list[str] = []
    for title in titles:
        cleaned = normalize(title)
        for ch in ":-()/,.\"'":
            cleaned = cleaned.replace(ch, " ")
        for w in cleaned.split():
            if len(w) >= 4 and w not in STOPWORDS_ES and w.isalpha() and w not in seen:
                seen.append(w)
    return tuple(seen)


def extract_code_identifiers(code: str) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """(identificadores, nombres_de_función) de un código Python: funciones + variables
    asignadas y parámetros de longitud ≥3, sin builtins. Orden de aparición."""
    tree = ast.parse(code)
    funcs: list[str] = []
    others: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            if node.name not in funcs:
                funcs.append(node.name)
            for a in node.args.args:
                if len(a.arg) >= 3 and a.arg not in others:
                    others.append(a.arg)
        elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
            if len(node.id) >= 3 and node.id not in _BUILTINS and node.id not in others:
                others.append(node.id)
    idents = tuple(dict.fromkeys([f.lower() for f in funcs] + [o.lower() for o in others]))
    return idents, tuple(f.lower() for f in funcs)


def build_anchor(
    *, concept_id: str, concept_title: str, learning_objective_id: str,
    learning_objective_title: str, reference_code: str,
) -> ConceptAnchor:
    identifiers, functions = extract_code_identifiers(reference_code)
    terms = extract_terms(concept_title, learning_objective_title)
    version = sha256_text("|".join((concept_id, concept_title, learning_objective_title,
                                    reference_code, ",".join(terms))))[:16]
    return ConceptAnchor(
        concept_id=concept_id, concept_title=concept_title, concept_version=version,
        learning_objective_id=learning_objective_id,
        learning_objective_title=learning_objective_title,
        terms=terms, code_identifiers=identifiers, function_names=functions,
    )
