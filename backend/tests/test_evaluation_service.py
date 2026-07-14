"""Regresión real de producción (Sprint 3, Caso 1 — validación en
navegador): las plantillas de evaluación por nivel de Bloom 2-6 tenían
EXACTAMENTE 1 pregunta cada una, mientras que Diagnosticar exige >= 2
items incorrectos para interpretar 'no domina' (scoring-v1,
`_UMBRAL_ERRORES` en runtime/domain/diagnosticar/productor.py). Con 1
sola pregunta posible, `errores` nunca podía alcanzar 2 — la propuesta
de Remediar ('reforzar') era ESTRUCTURALMENTE INALCANZABLE en
producción para cualquier evaluación de módulo cuyo Bloom objetivo no
fuera 1 (el único nivel que ya tenía 2 preguntas). Encontrado
recorriendo el flujo real en navegador, no por un test que faltara.
"""

from __future__ import annotations

from app.services.evaluation_service import _generate_questions


class TestBancoDePreguntasSuficienteParaElUmbral:
    def test_cada_nivel_bloom_tiene_al_menos_dos_preguntas(self):
        """>= 2 preguntas por nivel es el mínimo para que Diagnosticar
        pueda interpretar 'no domina' (>= 2 errores, scoring-v1)."""
        for bloom_level in range(1, 7):
            preguntas = _generate_questions(title="Módulo de prueba", bloom_level=bloom_level)
            assert len(preguntas) >= 2, (
                f"Bloom {bloom_level} tiene {len(preguntas)} pregunta(s) — "
                "con menos de 2, 'no domina' es inalcanzable (>=2 errores)"
            )

    def test_todas_las_preguntas_tienen_una_opcion_correcta_valida(self):
        for bloom_level in range(1, 7):
            for pregunta in _generate_questions(title="Módulo de prueba", bloom_level=bloom_level):
                assert 0 <= pregunta["correct"] < len(pregunta["options"])
