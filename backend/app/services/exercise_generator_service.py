"""
Generador de ejercicios de programación por concepto y nivel Bloom.
Cada plantilla produce preguntas teóricas, ejercicios de pseudocódigo
y ejercicios de código según (concepto, bloom_level).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from app.models.programming_domain import ProgrammingConcept

logger = logging.getLogger(__name__)


@dataclass
class ProgrammingExercise:
    concept: str
    bloom_level: int
    title: str
    problem_statement: str
    starter_code: str = ""
    expected_concepts: list[str] = field(default_factory=list)
    hints: list[str] = field(default_factory=list)
    difficulty: float = 0.5
    language: str = "pseudocode"


# ── Templates keyed by (concept, bloom_level) ─────────────────────

_EXERCISE_TEMPLATES: dict[tuple[ProgrammingConcept, int], list[dict[str, Any]]] = {
    (ProgrammingConcept.VARIABLES, 1): [
        {
            "title": "Declaración de variables",
            "problem": "Declara una variable llamada 'edad' que almacene tu edad. Luego declara una variable 'nombre' para tu nombre.",
            "starter": "// Declara las variables aquí\n\n",
            "concepts": ["variables", "tipos de dato"],
            "hints": ["Usa la palabra clave 'Definir' o el tipo de dato", "Asigna un valor con la flecha <-"],
            "difficulty": 0.3,
        },
        {
            "title": "Asignación y reasignación",
            "problem": "Declara una variable 'x' con valor 5. Luego reasigna x para que valga x + 3. ¿Cuál es el valor final?",
            "starter": "x <- 5\n",
            "concepts": ["variables", "asignación", "expresiones"],
            "hints": ["Primero asigna 5 a x", "Luego calcula x + 3 y asígnaselo a x"],
            "difficulty": 0.4,
        },
    ],
    (ProgrammingConcept.VARIABLES, 2): [
        {
            "title": "Intercambio de variables",
            "problem": "Escribe un algoritmo que intercambie los valores de dos variables A y B. No puedes usar una tercera variable temporal.",
            "starter": "A <- 10\nB <- 20\n\n",
            "concepts": ["variables", "asignación", "expresiones aritméticas"],
            "hints": ["Usa suma y resta para intercambiar", "A <- A + B; B <- A - B; A <- A - B"],
            "difficulty": 0.6,
        },
    ],
    (ProgrammingConcept.CONDITIONALS, 1): [
        {
            "title": "Mayor de edad",
            "problem": "Escribe un algoritmo que lea la edad de una persona y muestre 'Mayor de edad' si tiene 18 años o más, y 'Menor de edad' en caso contrario.",
            "starter": "Leer edad\n\n",
            "concepts": ["condicionales", "comparación", "entrada/salida"],
            "hints": ["Usa Si-Entonces-SiNo", "La condición es edad >= 18"],
            "difficulty": 0.4,
        },
    ],
    (ProgrammingConcept.CONDITIONALS, 2): [
        {
            "title": "Calculadora de notas",
            "problem": "Lee una nota numérica (0-20) y muestra la calificación: 0-10 'Deficiente', 11-14 'Regular', 15-17 'Bueno', 18-20 'Excelente'.",
            "starter": "Leer nota\n\n",
            "concepts": ["condicionales", "operadores lógicos", "entrada/salida"],
            "hints": ["Usa condiciones en cascada", "Empieza por el rango más bajo"],
            "difficulty": 0.5,
        },
    ],
    (ProgrammingConcept.LOOPS, 1): [
        {
            "title": "Contar hasta N",
            "problem": "Escribe un algoritmo que lea un número N y muestre los números del 1 al N.",
            "starter": "Leer N\ni <- 1\n",
            "concepts": ["bucles", "variables de control"],
            "hints": ["Usa Mientras o Para", "Incrementa i en cada iteración"],
            "difficulty": 0.4,
        },
    ],
    (ProgrammingConcept.LOOPS, 2): [
        {
            "title": "Suma de pares",
            "problem": "Calcula la suma de todos los números pares entre 1 y un número N ingresado por el usuario.",
            "starter": "Leer N\nsuma <- 0\n",
            "concepts": ["bucles", "condicionales", "operador módulo"],
            "hints": ["Un número es par si i % 2 == 0", "Usa un acumulador"],
            "difficulty": 0.5,
        },
    ],
    (ProgrammingConcept.ARRAYS, 1): [
        {
            "title": "Recorrer un arreglo",
            "problem": "Declara un arreglo de 5 números enteros. Luego muestra cada elemento del arreglo.",
            "starter": "Dimension arr[5]\narr[1] <- 10\narr[2] <- 20\narr[3] <- 30\narr[4] <- 40\narr[5] <- 50\n",
            "concepts": ["arreglos", "bucles", "índices"],
            "hints": ["Usa un bucle Para con índice de 1 a 5", "Accede con arr[i]"],
            "difficulty": 0.5,
        },
    ],
    (ProgrammingConcept.ARRAYS, 2): [
        {
            "title": "Buscar máximo en arreglo",
            "problem": "Dado un arreglo de N números, encuentra el valor máximo y su posición.",
            "starter": "Dimension arr[100]\n// Asume N y arr ya leídos\nmaximo <- arr[1]\nposicion <- 1\n",
            "concepts": ["arreglos", "bucles", "condicionales", "búsqueda"],
            "hints": ["Asume que el primer elemento es el máximo", "Compara cada elemento con el máximo actual"],
            "difficulty": 0.6,
        },
    ],
    (ProgrammingConcept.FUNCTIONS, 1): [
        {
            "title": "Función saludar",
            "problem": "Define una función llamada 'saludar' que reciba un nombre y muestre 'Hola, [nombre]!'.",
            "starter": "Funcion saludar(nombre)\n    \nFinFuncion\n\n// Llamar a la función\n",
            "concepts": ["funciones", "parámetros", "salida"],
            "hints": ["Usa Escribir dentro de la función", "Llama la función con saludar('Juan')"],
            "difficulty": 0.4,
        },
    ],
    (ProgrammingConcept.FUNCTIONS, 2): [
        {
            "title": "Función con retorno",
            "problem": "Define una función 'calcular_promedio' que reciba tres números y retorne su promedio.",
            "starter": "Funcion promedio <- calcular_promedio(a, b, c)\n    \nFinFuncion\n\nEscribir calcular_promedio(15, 18, 20)\n",
            "concepts": ["funciones", "retorno", "parámetros", "expresiones"],
            "hints": ["Suma los tres números", "Divide la suma entre 3", "Usa 'Retornar' para devolver el resultado"],
            "difficulty": 0.5,
        },
    ],
    (ProgrammingConcept.DEBUGGING, 1): [
        {
            "title": "Depurar error de sintaxis",
            "problem": "El siguiente código tiene errores. Encuéntralos y corrígelos:\n\n```\nLeer numero\nsi numero > 0\n    Escribir 'Positivo'\nFinSi\n    Escribir 'Fin'\n```",
            "starter": "// Corrige el código aquí\n",
            "concepts": ["depuración", "sintaxis", "condicionales"],
            "hints": ["Falta 'Entonces' después de la condición", "La indentación es importante"],
            "difficulty": 0.3,
        },
    ],
    (ProgrammingConcept.SEARCHING, 2): [
        {
            "title": "Búsqueda lineal",
            "problem": "Dado un arreglo de N números y un valor a buscar, determina si el valor existe y en qué posición.",
            "starter": "Dimension arr[100]\n// arr y N ya leídos\nLeer buscar\nencontrado <- Falso\n",
            "concepts": ["búsqueda", "arreglos", "bucles", "condicionales"],
            "hints": ["Recorre el arreglo desde 1 hasta N", "Si encuentras el valor, guarda la posición"],
            "difficulty": 0.5,
        },
    ],
}


def get_templates() -> dict[tuple[ProgrammingConcept, int], list[dict[str, Any]]]:
    return _EXERCISE_TEMPLATES


class ProgrammingExerciseGenerator:
    """Genera ejercicios de programación para un concepto y nivel Bloom específico."""

    def generate(
        self,
        concept: ProgrammingConcept,
        bloom_level: int,
        count: int = 1,
        language: str = "pseudocode",
    ) -> list[ProgrammingExercise]:
        templates = _EXERCISE_TEMPLATES.get((concept, bloom_level), [])
        if not templates:
            templates = _EXERCISE_TEMPLATES.get((concept, max(bloom_level - 1, 1)), [])
        if not templates:
            templates = self._fallback_template(concept, bloom_level)

        result = []
        for t in templates[:count]:
            result.append(ProgrammingExercise(
                concept=concept.value,
                bloom_level=bloom_level,
                title=t["title"],
                problem_statement=t["problem"],
                starter_code=t.get("starter", ""),
                expected_concepts=t.get("concepts", [concept.value]),
                hints=t.get("hints", []),
                difficulty=t.get("difficulty", 0.5),
                language=language,
            ))

        while len(result) < count:
            fb = self._fallback_template(concept, bloom_level)[0]
            result.append(ProgrammingExercise(
                concept=concept.value,
                bloom_level=bloom_level,
                title=f"Ejercicio de {concept.value}",
                problem_statement=fb["problem"],
                starter_code=fb.get("starter", ""),
                expected_concepts=[concept.value],
                hints=fb.get("hints", []),
                difficulty=fb.get("difficulty", 0.5),
                language=language,
            ))

        return result[:count]

    def generate_sequence(
        self,
        concepts: list[ProgrammingConcept],
        bloom_levels: list[int] | None = None,
        language: str = "pseudocode",
    ) -> list[list[ProgrammingExercise]]:
        result = []
        for i, concept in enumerate(concepts):
            bloom = bloom_levels[i] if bloom_levels and i < len(bloom_levels) else 2
            exercises = self.generate(concept, bloom, count=1, language=language)
            result.append(exercises)
        return result

    def _fallback_template(
        self,
        concept: ProgrammingConcept,
        bloom_level: int,
    ) -> list[dict[str, Any]]:
        name = concept.value.replace("_", " ")
        verbs = {
            1: "Define",
            2: "Explica",
            3: "Aplica",
            4: "Analiza",
        }
        verb = verbs.get(bloom_level, "Describe")
        return [
            {
                "title": f"{verb}: {name}",
                "problem": f"{verb} el concepto de {name} usando un ejemplo práctico.",
                "starter": f"// {verb} {name}\n\n",
                "concepts": [concept.value],
                "hints": [f"Piensa en un ejemplo cotidiano de {name}", "Usa pseudocódigo para ilustrar"],
                "difficulty": 0.3 + bloom_level * 0.1,
            },
        ]
