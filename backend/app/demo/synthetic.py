from __future__ import annotations

import random
from dataclasses import dataclass, asdict


@dataclass(frozen=True)
class SyntheticStudent:
    student_id: str
    name: str
    profile: str
    mastery: float
    motivation: float
    risk: float
    learning_style: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class SyntheticModule:
    module_id: str
    title: str
    topic: str
    difficulty: float
    prerequisite_gap: float
    assessment_score: float

    def to_dict(self) -> dict:
        return asdict(self)


class SyntheticGenerator:
    """Deterministic synthetic demo data.

    A seed gives reproducible sessions for sustentation and replay.
    """

    def __init__(self, seed: int = 42):
        self._rng = random.Random(seed)

    def student(self) -> SyntheticStudent:
        profiles = [
            ("Ana Torres", "visual-fast", "visual"),
            ("Luis Mendoza", "reflective-steady", "reading"),
            ("Camila Rojas", "practice-first", "kinesthetic"),
        ]
        name, profile, style = self._rng.choice(profiles)
        mastery = round(self._rng.uniform(0.42, 0.68), 2)
        motivation = round(self._rng.uniform(0.52, 0.9), 2)
        risk = round(max(0.05, 1.0 - ((mastery + motivation) / 2)), 2)
        return SyntheticStudent(
            student_id=f"demo-student-{self._rng.randint(1000, 9999)}",
            name=name,
            profile=profile,
            mastery=mastery,
            motivation=motivation,
            risk=risk,
            learning_style=style,
        )

    def module(self) -> SyntheticModule:
        modules = [
            ("Algoritmos Greedy", "programacion", 0.62),
            ("Normalizacion de Bases de Datos", "datos", 0.58),
            ("Derivadas Aplicadas", "calculo", 0.66),
        ]
        title, topic, difficulty = self._rng.choice(modules)
        gap = round(self._rng.uniform(0.12, 0.42), 2)
        score = round(max(0.05, min(0.98, 1.0 - difficulty - gap + self._rng.uniform(0.22, 0.44))), 2)
        return SyntheticModule(
            module_id=f"demo-module-{self._rng.randint(1000, 9999)}",
            title=title,
            topic=topic,
            difficulty=difficulty,
            prerequisite_gap=gap,
            assessment_score=score,
        )

