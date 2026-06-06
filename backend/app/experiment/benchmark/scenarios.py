"""
Benchmark Scenarios — Generación de escenarios sintéticos con ground truth
para evaluación académica del sistema multi-agente pedagógico.
"""

from __future__ import annotations

import hashlib
import json
import random
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any


@dataclass
class GroundTruth:
    """Ground truth para un escenario de benchmark."""

    expected_pass: bool
    expected_bloom_level: int
    expected_mastery_score: float
    expected_misconceptions: list[str] = field(default_factory=list)
    expected_difficulty: str = "medium"
    expected_concepts: list[str] = field(default_factory=list)
    expert_notes: str = ""


@dataclass
class BenchmarkScenario:
    """Escenario de benchmark con ground truth."""

    scenario_id: str
    student_id: str
    module_id: str
    course_id: str
    student_profile: dict[str, Any] = field(default_factory=dict)
    learning_objectives: list[dict[str, Any]] = field(default_factory=list)
    previous_performance: dict[str, float] = field(default_factory=dict)
    misconceptions: list[str] = field(default_factory=list)
    bloom_level: int = 1
    difficulty: str = "medium"
    ground_truth: GroundTruth = field(default_factory=GroundTruth)
    concepts: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["ground_truth"] = asdict(self.ground_truth)
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> BenchmarkScenario:
        gt = GroundTruth(**d.pop("ground_truth", {}))
        return cls(**d, ground_truth=gt)


class ScenarioGenerator:
    """Generador determinista de escenarios sintéticos.

    Produce escenarios con ground truth conocido para evaluar
    las condiciones del benchmark.
    """

    BLOOM_LEVELS = {
        1: "recordar",
        2: "comprender",
        3: "aplicar",
        4: "analizar",
        5: "evaluar",
        6: "crear",
    }

    CONCEPTOS_PROGRAMACION = [
        "variables", "tipos_datos", "condicionales", "bucles",
        "funciones", "listas", "diccionarios", "recursion",
        "poo_clases", "poo_herencia", "poo_polimorfismo",
        "archivos", "excepciones", "modularidad", "algoritmos_basicos",
        "complejidad", "estructuras_datos", "sorting", "searching",
        "grafos", "arboles", "programacion_dinamica",
    ]

    MISCONCEPCIONES = [
        "confunde_asignacion_igualdad",
        "no_entiende_alcance_variables",
        "confunde_parametros_argumentos",
        "error_off_by_one_bucles",
        "confunde_lista_tupla",
        "no_entiende_herencia",
        "confunde_igualdad_referencia",
        "error_recursion_infinita",
        "confunde_return_print",
        "mal_manejo_excepciones",
        "confunde_var_local_global",
        "error_indice_fuera_rango",
    ]

    MODULOS = [
        "introduccion_programacion",
        "estructuras_control",
        "funciones_modularidad",
        "estructuras_datos_basicas",
        "poo_fundamentos",
        "poo_avanzado",
        "manejo_archivos",
        "algoritmos_busqueda",
        "algoritmos_ordenamiento",
        "estructuras_datos_avanzadas",
    ]

    PERFILES_ESTUDIANTE = [
        {"estilo": "visual", "ritmo": "lento", "modalidad": "practico"},
        {"estilo": "auditivo", "ritmo": "medio", "modalidad": "teorico"},
        {"estilo": "kinestesico", "ritmo": "rapido", "modalidad": "practico"},
        {"estilo": "lectura_escritura", "ritmo": "lento", "modalidad": "teorico"},
        {"estilo": "visual", "ritmo": "medio", "modalidad": "mixto"},
    ]

    def __init__(self, seed: int = 42, n_scenarios: int = 100):
        self.seed = seed
        self.n_scenarios = n_scenarios
        self._rng = random.Random(seed)

    def _scenario_id(self, idx: int) -> str:
        raw = f"benchmark-{self.seed}-{idx}"
        return f"scn_{hashlib.sha256(raw.encode()).hexdigest()[:12]}"

    def _pick_bloom_level(self, difficulty: str) -> int:
        ranges = {
            "easy": (1, 2),
            "medium": (2, 4),
            "hard": (4, 6),
        }
        lo, hi = ranges.get(difficulty, (1, 6))
        return self._rng.randint(lo, hi)

    def _pick_misconceptions(self, count_range: tuple[int, int]) -> list[str]:
        n = self._rng.randint(*count_range)
        return self._rng.sample(self.MISCONCEPCIONES, min(n, len(self.MISCONCEPCIONES)))

    def _pick_concepts(self, module: str, bloom: int) -> list[str]:
        base = self.CONCEPTOS_PROGRAMACION[:]
        n = min(3 + bloom, len(base))
        return self._rng.sample(base, n)

    def _compute_expected_pass(
        self, mastery: float, bloom: int, difficulty: str
    ) -> bool:
        threshold_map = {"easy": 0.4, "medium": 0.55, "hard": 0.7}
        adjusted = mastery - (bloom - 1) * 0.05
        return adjusted >= threshold_map.get(difficulty, 0.55)

    def generate(self) -> list[BenchmarkScenario]:
        scenarios: list[BenchmarkScenario] = []
        difficulties = ["easy", "medium", "hard"]
        diff_weights = [0.25, 0.50, 0.25]

        for i in range(self.n_scenarios):
            student_idx = self._rng.randint(0, len(self.PERFILES_ESTUDIANTE) - 1)
            profile = dict(self.PERFILES_ESTUDIANTE[student_idx])

            module_idx = self._rng.randint(0, len(self.MODULOS) - 1)
            module = self.MODULOS[module_idx]

            difficulty = self._rng.choices(difficulties, weights=diff_weights, k=1)[0]
            bloom = self._pick_bloom_level(difficulty)
            mastery = round(
                max(0.1, min(1.0, self._rng.gauss(0.6, 0.2))), 4
            )
            misconceptions = self._pick_misconceptions((1, 3))
            concepts = self._pick_concepts(module, bloom)

            expected_pass = self._compute_expected_pass(mastery, bloom, difficulty)

            previous_perf = {
                c: round(max(0.0, min(1.0, self._rng.gauss(mastery, 0.15))), 4)
                for c in concepts[:3]
            }

            gt = GroundTruth(
                expected_pass=expected_pass,
                expected_bloom_level=bloom,
                expected_mastery_score=mastery,
                expected_misconceptions=list(misconceptions),
                expected_difficulty=difficulty,
                expected_concepts=list(concepts),
            )

            scenario = BenchmarkScenario(
                scenario_id=self._scenario_id(i),
                student_id=f"stu_{self._rng.randint(1000, 9999)}",
                module_id=module,
                course_id=f"course_{self._rng.randint(1, 20)}",
                student_profile=profile,
                learning_objectives=[
                    {
                        "concept": c,
                        "bloom_level": max(1, bloom - 1 + self._rng.randint(0, 1)),
                        "weight": round(self._rng.uniform(0.3, 1.0), 2),
                    }
                    for c in concepts[:3]
                ],
                previous_performance=previous_perf,
                misconceptions=misconceptions,
                bloom_level=bloom,
                difficulty=difficulty,
                ground_truth=gt,
                concepts=concepts,
                metadata={
                    "module": module,
                    "student_idx": student_idx,
                    "seed": self.seed,
                },
            )
            scenarios.append(scenario)

        return scenarios

    def save(self, scenarios: list[BenchmarkScenario], path: str) -> None:
        data = {
            "seed": self.seed,
            "n_scenarios": len(scenarios),
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "scenarios": [s.to_dict() for s in scenarios],
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    @staticmethod
    def load(path: str) -> list[BenchmarkScenario]:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return [BenchmarkScenario.from_dict(s) for s in data["scenarios"]]
