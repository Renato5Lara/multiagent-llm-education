"""Dataset gold: (profile_id → etiqueta esperada), derivado SOLO de (arquetipo, dificultad)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from adaptation_swarm.gold.rubric import RULE_VERSION, expected_dominant
from adaptation_swarm.profiles.models import ProfileRequest


@dataclass(frozen=True, slots=True)
class GoldLabel:
    profile_id: str
    concept_id: str
    archetype: str
    difficulty: str
    expected_dominant: str
    rule_version: str = RULE_VERSION

    def to_dict(self) -> dict:
        return {
            "profile_id": self.profile_id, "concept_id": self.concept_id,
            "archetype": self.archetype, "difficulty": self.difficulty,
            "expected_dominant": self.expected_dominant, "rule_version": self.rule_version,
        }


def gold_for(profile: ProfileRequest) -> GoldLabel:
    if profile.archetype is None or profile.difficulty is None:
        raise ValueError("el gold necesita arquetipo y dificultad del perfil")
    return GoldLabel(
        profile_id=profile.profile_id, concept_id=profile.concept_id,
        archetype=profile.archetype.value, difficulty=profile.difficulty.value,
        expected_dominant=expected_dominant(profile.archetype, profile.difficulty),
    )


def build_gold_dataset(profiles: Iterable[ProfileRequest]) -> list[GoldLabel]:
    return [gold_for(p) for p in profiles]
