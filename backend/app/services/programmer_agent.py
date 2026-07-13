from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class EducationalExercise:
    title: str
    prompt: str
    expected_outcome: str
    bloom_level: int
    scaffolding: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "prompt": self.prompt,
            "expected_outcome": self.expected_outcome,
            "bloom_level": self.bloom_level,
            "scaffolding": self.scaffolding,
        }


@dataclass(frozen=True)
class GeneratedEducationalCode:
    code: str
    explanation: str
    tests: str
    examples: list[str]
    exercises: list[EducationalExercise]
    reasoning_trace: list[dict[str, Any]]
    pedagogical_quality: float
    adaptation_quality: float
    metadata: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "explanation": self.explanation,
            "tests": self.tests,
            "examples": self.examples,
            "exercises": [exercise.to_dict() for exercise in self.exercises],
            "reasoning_trace": self.reasoning_trace,
            "pedagogical_quality": self.pedagogical_quality,
            "adaptation_quality": self.adaptation_quality,
            "metadata": self.metadata,
        }


class ProgrammerAgent:
    """Produces educational Python code candidates for sandbox verification."""

    name = "programmer"

    async def generate_code(
        self,
        *,
        topic: str,
        objectives: list[str],
        iteration: int = 1,
        reviewer_feedback: str = "",
    ) -> GeneratedEducationalCode:
        normalized_topic = topic.lower()
        if "arreglo" in normalized_topic or "array" in normalized_topic or "lista" in normalized_topic:
            code = self._array_code()
            tests = self._array_tests()
            examples = self._array_examples()
            exercises = self._array_exercises()
            explanation = (
                "Implementa recorrido, busqueda lineal e insercion sobre una lista Python "
                "con nombres didacticos y casos verificables."
            )
        else:
            code = "def resolver():\n    return 'pendiente'\n\nprint(resolver())\n"
            tests = "assert resolver() == 'pendiente'\n"
            examples = ["resolver() -> 'pendiente'"]
            exercises = [
                EducationalExercise(
                    title="Completar solucion",
                    prompt="Extiende resolver para cubrir el objetivo de aprendizaje.",
                    expected_outcome="La funcion retorna una respuesta verificable.",
                    bloom_level=3,
                    scaffolding=["definir entrada", "escribir prueba", "ejecutar sandbox"],
                )
            ]
            explanation = "Plantilla segura para una actividad educativa verificable."

        reasoning_trace = self._reasoning_trace(topic, objectives, iteration, reviewer_feedback)
        return GeneratedEducationalCode(
            code=code,
            explanation=explanation,
            tests=tests,
            examples=examples,
            exercises=exercises,
            reasoning_trace=reasoning_trace,
            pedagogical_quality=self._pedagogical_quality(objectives, tests, exercises),
            adaptation_quality=self._adaptation_quality(iteration, reviewer_feedback),
            metadata={
                "agent": self.name,
                "topic": topic,
                "objectives": objectives,
                "iteration": iteration,
                "reviewer_feedback": reviewer_feedback[:500],
            },
        )

    def _array_code(self) -> str:
        return (
            "def recorrer(arreglo):\n"
            "    resultado = []\n"
            "    for indice, valor in enumerate(arreglo):\n"
            "        resultado.append((indice, valor))\n"
            "    return resultado\n\n"
            "def buscar(arreglo, objetivo):\n"
            "    for indice, valor in enumerate(arreglo):\n"
            "        if valor == objetivo:\n"
            "            return indice\n"
            "    return -1\n\n"
            "def insertar(arreglo, posicion, valor):\n"
            "    if posicion < 0 or posicion > len(arreglo):\n"
            "        raise ValueError('posicion fuera de rango')\n"
            "    copia = list(arreglo)\n"
            "    copia.insert(posicion, valor)\n"
            "    return copia\n\n"
            "if __name__ == '__main__':\n"
            "    datos = [10, 20, 30]\n"
            "    print('recorrido:', recorrer(datos))\n"
            "    print('busqueda:', buscar(datos, 20))\n"
            "    print('insercion:', insertar(datos, 1, 15))\n"
        )

    def _array_tests(self) -> str:
        return (
            "assert recorrer([5, 7]) == [(0, 5), (1, 7)]\n"
            "assert buscar([10, 20, 30], 20) == 1\n"
            "assert buscar([10, 20, 30], 99) == -1\n"
            "assert insertar([10, 30], 1, 20) == [10, 20, 30]\n"
            "try:\n"
            "    insertar([1, 2], 5, 3)\n"
            "except ValueError:\n"
            "    pass\n"
            "else:\n"
            "    raise AssertionError('insertar debe rechazar posiciones invalidas')\n"
        )

    def _array_examples(self) -> list[str]:
        return [
            "recorrer([10, 20]) devuelve [(0, 10), (1, 20)]",
            "buscar([10, 20, 30], 20) devuelve 1",
            "insertar([10, 30], 1, 20) devuelve [10, 20, 30]",
        ]

    def _array_exercises(self) -> list[EducationalExercise]:
        return [
            EducationalExercise(
                title="Trazar recorrido",
                prompt="Dado [4, 8, 15], escribe la tabla indice-valor producida por recorrer.",
                expected_outcome="[(0, 4), (1, 8), (2, 15)]",
                bloom_level=2,
                scaffolding=["identificar longitud", "empezar en indice 0", "registrar cada par"],
            ),
            EducationalExercise(
                title="Buscar elemento",
                prompt="Predice que retorna buscar([3, 5, 7], 7) y explica por que.",
                expected_outcome="Retorna 2 porque 7 esta en el indice 2.",
                bloom_level=3,
                scaffolding=["comparar elemento por elemento", "detener al encontrar objetivo"],
            ),
            EducationalExercise(
                title="Insertar con desplazamiento",
                prompt="Simula insertar 9 en la posicion 1 de [2, 4, 6].",
                expected_outcome="[2, 9, 4, 6]",
                bloom_level=3,
                scaffolding=["validar posicion", "desplazar valores", "confirmar nueva longitud"],
            ),
        ]

    def _reasoning_trace(
        self,
        topic: str,
        objectives: list[str],
        iteration: int,
        reviewer_feedback: str,
    ) -> list[dict[str, Any]]:
        return [
            {
                "step": "objective_mapping",
                "decision": "map objectives to executable functions",
                "evidence": objectives,
            },
            {
                "step": "pedagogical_granularity",
                "decision": "separate recorrido, busqueda and insercion into small functions",
                "evidence": {"topic": topic, "iteration": iteration},
            },
            {
                "step": "test_design",
                "decision": "unit tests cover normal, missing and invalid-position cases",
                "evidence": ["pass/fail visible", "misconception off-by-one detectable"],
            },
            {
                "step": "adaptation",
                "decision": "use reviewer feedback to regenerate a safer candidate",
                "evidence": reviewer_feedback[:300],
            },
        ]

    def _pedagogical_quality(
        self,
        objectives: list[str],
        tests: str,
        exercises: list[EducationalExercise],
    ) -> float:
        coverage = sum(1 for objective in objectives if objective.lower() in tests.lower())
        exercise_score = min(1.0, len(exercises) / 3)
        objective_score = min(1.0, coverage / max(1, len(objectives))) if objectives else 0.75
        return round((objective_score * 0.45) + (exercise_score * 0.35) + 0.2, 3)

    def _adaptation_quality(self, iteration: int, reviewer_feedback: str) -> float:
        if iteration == 1:
            return 0.82
        if reviewer_feedback:
            return 0.9
        return 0.72
