"""Acceso a los conceptos REALES del currículo (Postgres) y a su especificación de comportamiento
(código y asserts de referencia del catálogo CMG, usados solo como ESPECIFICACIÓN)."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select

from adaptation_swarm.multimodal.anchor import ConceptAnchor, build_anchor
from adaptation_swarm.profiles.generator import ConceptRef
from adaptation_swarm.schemas.errors import GenerationError


@dataclass(frozen=True)
class ConceptSpec:
    ref: ConceptRef
    learning_objective_id: str
    learning_objective_title: str
    reference_code: str
    reference_tests: str
    behavior_description: str = ""

    def anchor(self) -> ConceptAnchor:
        return build_anchor(
            concept_id=self.ref.concept_id, concept_title=self.ref.title,
            learning_objective_id=self.learning_objective_id,
            learning_objective_title=self.learning_objective_title, reference_code=self.reference_code,
        )


def load_concept_refs(session) -> list[ConceptRef]:
    from app.models.concept import Concept
    from app.models.learning_objective import LearningObjective

    rows = session.execute(
        select(Concept, LearningObjective).join(LearningObjective, Concept.learning_objective_id == LearningObjective.id)
    ).all()
    return [ConceptRef(concept_id=c.id, title=c.title, module=lo.title, order=c.order) for c, lo in rows]


def load_concept_specs(session, concept_ids: list[str]) -> list[ConceptSpec]:
    from app.models.concept import Concept
    from app.models.learning_objective import LearningObjective
    from app.services.cmg_concept_catalog import obtener_plantilla

    specs: list[ConceptSpec] = []
    for cid in concept_ids:
        row = session.execute(
            select(Concept, LearningObjective).join(LearningObjective, Concept.learning_objective_id == LearningObjective.id)
            .where(Concept.id == cid)
        ).first()
        if row is None:
            raise GenerationError(f"concepto {cid} inexistente en la base de datos")
        c, lo = row
        tpl = obtener_plantilla(c.title)
        if tpl is None:
            raise GenerationError(f"sin especificación de comportamiento para {c.title!r}")
        specs.append(ConceptSpec(ConceptRef(c.id, c.title, lo.title, c.order), lo.id, lo.title, tpl.code, tpl.tests,
                                 f"{tpl.exercise_prompt} Resultado esperado: {tpl.exercise_expected_outcome}"))
    return specs
