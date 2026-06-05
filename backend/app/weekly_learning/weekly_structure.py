"""
WeeklyStructureFactory — defines progression templates for weekly structures.

Each template maps week_number → Bloom level, theme, and pedagogical focus.

Templates:
  5-week:  Introducción → Comprensión → Aplicación → Resolución → Proyecto
  8-week:  Adds intermediate steps
  16-week: Full semester progression
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import ClassVar


@dataclass
class WeekTemplate:
    week: int
    bloom_level: int
    theme_suffix: str
    pedagogical_focus: str
    bloom_label: str


@dataclass
class StructureTemplate:
    name: str
    total_weeks: int
    weeks: list[WeekTemplate] = field(default_factory=list)


class WeeklyStructureFactory:
    """
    Creates weekly structure templates based on the number of weeks.

    Usage:
        template = WeeklyStructureFactory.get_template(5)
        for week in template.weeks:
            print(week.bloom_level, week.theme_suffix)
    """

    TEMPLATES: ClassVar[dict[int, StructureTemplate]] = {}

    @classmethod
    def _build_templates(cls) -> None:
        if cls.TEMPLATES:
            return

        cls.TEMPLATES[5] = StructureTemplate(
            name="5 semanas — progresión Bloom completa",
            total_weeks=5,
            weeks=[
                WeekTemplate(1, 1, "Introducción y fundamentos", "Activar saberes previos, explorar conceptos básicos", "Recordar"),
                WeekTemplate(2, 2, "Comprensión y análisis conceptual", "Profundizar en definiciones, ejemplos y contraejemplos", "Comprender"),
                WeekTemplate(3, 3, "Aplicación guiada", "Resolver ejercicios prácticos con supervisión", "Aplicar"),
                WeekTemplate(4, 4, "Resolución de problemas", "Analizar casos complejos, evaluar soluciones", "Analizar/Evaluar"),
                WeekTemplate(5, 6, "Proyecto integrador", "Diseñar y crear una solución completa", "Crear"),
            ],
        )

        cls.TEMPLATES[8] = StructureTemplate(
            name="8 semanas — profundización progresiva",
            total_weeks=8,
            weeks=[
                WeekTemplate(1, 1, "Introducción y fundamentos", "Conceptos base, activación de saberes", "Recordar"),
                WeekTemplate(2, 1, "Exploración de casos", "Ejemplos variados, primeras aproximaciones", "Recordar"),
                WeekTemplate(3, 2, "Comprensión detallada", "Análisis de propiedades, comparaciones", "Comprender"),
                WeekTemplate(4, 2, "Relaciones y conexiones", "Vincular con otros temas, transferir conocimiento", "Comprender"),
                WeekTemplate(5, 3, "Aplicación en contextos controlados", "Ejercicios prácticos estructurados", "Aplicar"),
                WeekTemplate(6, 4, "Análisis de problemas reales", "Diagnosticar, descomponer, resolver", "Analizar"),
                WeekTemplate(7, 5, "Evaluación crítica", "Comparar enfoques, justificar decisiones", "Evaluar"),
                WeekTemplate(8, 6, "Proyecto integrador final", "Diseñar, implementar y presentar solución", "Crear"),
            ],
        )

        cls.TEMPLATES[16] = StructureTemplate(
            name="16 semanas — semestre completo",
            total_weeks=16,
            weeks=[
                WeekTemplate(1, 1, "Introducción al curso", "Visión general, expectativas, evaluación diagnóstica", "Recordar"),
                WeekTemplate(2, 1, "Conceptos fundamentales", "Definiciones, terminología, primeros ejemplos", "Recordar"),
                WeekTemplate(3, 2, "Exploración guiada", "Laboratorio guiado, ejercicios supervisados", "Comprender"),
                WeekTemplate(4, 2, "Profundización conceptual", "Análisis de variantes, casos frontera", "Comprender"),
                WeekTemplate(5, 3, "Aplicación básica", "Resolver problemas tipo con herramientas dadas", "Aplicar"),
                WeekTemplate(6, 3, "Aplicación avanzada", "Combinar conceptos, soluciones multi-paso", "Aplicar"),
                WeekTemplate(7, 4, "Análisis de casos", "Estudios de caso, identificación de patrones", "Analizar"),
                WeekTemplate(8, 4, "Análisis comparativo", "Comparar y contrastar enfoques", "Analizar"),
                WeekTemplate(9, 4, "Evaluación de soluciones", "Revisión por pares, rúbricas, crítica constructiva", "Analizar"),
                WeekTemplate(10, 5, "Evaluación de diseño", "Seleccionar la mejor solución para un problema dado", "Evaluar"),
                WeekTemplate(11, 5, "Optimización y mejora", "Refactorizar, optimizar, justificar cambios", "Evaluar"),
                WeekTemplate(12, 6, "Proyecto — planificación", "Definir alcance, requisitos, diseño", "Crear"),
                WeekTemplate(13, 6, "Proyecto — implementación", "Desarrollar la solución propuesta", "Crear"),
                WeekTemplate(14, 6, "Proyecto — integración", "Integrar componentes, pruebas", "Crear"),
                WeekTemplate(15, 6, "Proyecto — presentación", "Documentar, presentar, defender", "Crear"),
                WeekTemplate(16, 6, "Cierre y retroalimentación", "Reflexión final, plan de mejora continua", "Crear"),
            ],
        )

        # Custom — infer from any total_weeks by linear interpolation
        cls._infer_custom(10)
        cls._infer_custom(12)
        cls._infer_custom(14)

    @classmethod
    def _infer_custom(cls, n_weeks: int) -> None:
        if n_weeks in cls.TEMPLATES:
            return

        bloom_curve = cls._generate_bloom_curve(n_weeks)
        labels = ["", "Recordar", "Comprender", "Aplicar", "Analizar", "Evaluar", "Crear"]
        phases = [
            "Introducción y fundamentos",
            "Exploración de conceptos",
            "Comprensión detallada",
            "Aplicación guiada",
            "Práctica independiente",
            "Análisis de casos",
            "Evaluación crítica",
            "Solución de problemas",
            "Proyecto integrador",
            "Cierre y reflexión",
            "Proyecto — planificación",
            "Proyecto — implementación",
            "Proyecto — integración",
            "Proyecto — presentación",
        ]

        weeks = []
        for i in range(1, n_weeks + 1):
            bloom = bloom_curve[i - 1]
            phase_idx = min(i - 1, len(phases) - 1)
            weeks.append(WeekTemplate(
                week=i,
                bloom_level=bloom,
                theme_suffix=phases[phase_idx],
                pedagogical_focus=f"Nivel Bloom {bloom}: {labels[bloom]}" if bloom < len(labels) else "Nivel avanzado",
                bloom_label=labels[bloom] if bloom < len(labels) else "Avanzado",
            ))

        cls.TEMPLATES[n_weeks] = StructureTemplate(
            name=f"{n_weeks} semanas — progresión adaptativa",
            total_weeks=n_weeks,
            weeks=weeks,
        )

    @staticmethod
    def _generate_bloom_curve(n_weeks: int) -> list[int]:
        """Generate a Bloom progression curve that spans 1→6 over n_weeks."""
        if n_weeks <= 1:
            return [3]
        if n_weeks <= 3:
            return [1, 3, 6][:n_weeks]

        curve = []
        # First quarter: Bloom 1-2
        q1 = max(1, n_weeks // 4)
        for i in range(q1):
            progress = i / max(q1 - 1, 1)
            curve.append(max(1, min(2, round(1 + progress))))
        # Second quarter: Bloom 2-3
        q2 = max(1, n_weeks // 4)
        for i in range(q2):
            progress = i / max(q2 - 1, 1)
            curve.append(max(2, min(3, round(2 + progress))))
        # Third quarter: Bloom 3-4
        q3 = max(1, n_weeks // 4)
        for i in range(q3):
            progress = i / max(q3 - 1, 1)
            curve.append(max(3, min(4, round(3 + progress))))
        # Fourth quarter: Bloom 5-6
        remaining = n_weeks - len(curve)
        for i in range(remaining):
            progress = i / max(remaining - 1, 1)
            curve.append(max(5, min(6, round(5 + progress))))

        return curve[:n_weeks]

    @classmethod
    def get_template(cls, total_weeks: int) -> StructureTemplate:
        cls._build_templates()
        if total_weeks not in cls.TEMPLATES:
            cls._infer_custom(total_weeks)
        return cls.TEMPLATES.get(total_weeks, cls.TEMPLATES[5])

    @classmethod
    def list_available(cls) -> list[dict]:
        cls._build_templates()
        return [
            {"total_weeks": k, "name": v.name}
            for k, v in sorted(cls.TEMPLATES.items())
        ]


# Singleton
weekly_structure_factory = WeeklyStructureFactory()
