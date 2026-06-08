"""
BloomProgression — manages Bloom-level progression across weeks.

Ensures:
  - Monotonic non-decreasing Bloom levels (conceptually)
  - Proper scaffolding (lower levels early, higher later)
  - Each week's content aligns with its Bloom target
"""

from __future__ import annotations

from typing import Any

BLOOM_LABELS: dict[int, str] = {
    1: "Recordar",
    2: "Comprender",
    3: "Aplicar",
    4: "Analizar",
    5: "Evaluar",
    6: "Crear",
}

BLOOM_VERBS: dict[int, list[str]] = {
    1: ["identificar", "definir", "listar", "nombrar", "recordar", "reconocer"],
    2: ["explicar", "describir", "interpretar", "resumir", "comparar", "ejemplificar"],
    3: ["aplicar", "implementar", "usar", "resolver", "ejecutar", "calcular"],
    4: ["analizar", "diferenciar", "organizar", "atribuir", "comparar", "contrastar"],
    5: ["evaluar", "juzgar", "criticar", "justificar", "argumentar", "revisar"],
    6: ["crear", "diseñar", "desarrollar", "planificar", "producir", "construir"],
}


class BloomProgression:
    """
    Validates and computes Bloom-level progression across weeks.

    A progression is valid if:
      - Starts at Bloom 1 or 2
      - Ends at Bloom 5 or 6
      - No more than 2-level jump between consecutive weeks
      - Never decreases (non-regression)
    """

    @staticmethod
    def validate(progression: list[int]) -> list[str]:
        issues: list[str] = []
        if not progression:
            return ["Progression is empty"]

        if progression[0] not in (1, 2):
            issues.append(f"Progression should start at Bloom 1 or 2, got {progression[0]}")

        if progression[-1] not in (5, 6):
            issues.append(f"Progression should end at Bloom 5 or 6, got {progression[-1]}")

        for i in range(1, len(progression)):
            diff = progression[i] - progression[i - 1]
            if diff < 0:
                issues.append(f"Bloom regression at week {i + 1}: {progression[i - 1]} → {progression[i]}")
            if diff > 2:
                issues.append(f"Bloom jump too large at week {i + 1}: {progression[i - 1]} → {progression[i]} (max 2)")

        for i, level in enumerate(progression):
            if level < 1 or level > 6:
                issues.append(f"Invalid Bloom level at week {i + 1}: {level}")

        return issues

    @staticmethod
    def is_valid(progression: list[int]) -> bool:
        return len(BloomProgression.validate(progression)) == 0

    @staticmethod
    def get_label(level: int) -> str:
        return BLOOM_LABELS.get(level, f"Nivel {level}")

    @staticmethod
    def get_verbs(level: int) -> list[str]:
        return BLOOM_VERBS.get(level, [])

    @staticmethod
    def describe_week(week_number: int, bloom_level: int, theme: str) -> dict[str, Any]:
        return {
            "week": week_number,
            "bloom_level": bloom_level,
            "bloom_label": BLOOM_LABELS.get(bloom_level, f"Nivel {bloom_level}"),
            "verbs": BLOOM_VERBS.get(bloom_level, []),
            "theme": theme,
            "description": (
                f"Semana {week_number}: {theme}. "
                f"Nivel Bloom {bloom_level} ({BLOOM_LABELS.get(bloom_level, '')}). "
                f"Verbose clave: {', '.join(BLOOM_VERBS.get(bloom_level, ['']))}."
            ),
        }


bloom_progression = BloomProgression()
