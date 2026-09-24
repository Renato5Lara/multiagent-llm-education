"""Tests de P0 — CMG Generation Service. No usa Postgres: `Concept`/
`LearningObjective` se instancian en memoria (sin persistir), porque
`generar_cmg` nunca hace I/O de base de datos — solo lee atributos."""

from __future__ import annotations

import pytest

from app.core.config import settings
from app.models.concept import Concept
from app.models.learning_objective import LearningObjective
from app.services.cmg_generation_service import (
    CONTROL_CONFIG,
    GenerationConfig,
    generar_cmg,
)


def _concept() -> Concept:
    return Concept(id="c-1", title="Bucle while", learning_objective_id="lo-1", order=1)


def _objetivo(bloom_level: int = 3) -> LearningObjective:
    return LearningObjective(
        id="lo-1", course_id="course-1", title="Bucles", bloom_level=bloom_level, order=5,
    )


@pytest.fixture(autouse=True)
def _sin_llm(monkeypatch):
    """Determinismo total del contrato estructural (§9 del encargo):
    sin `OPENAI_API_KEY`, el camino LLM nunca se ejerce — fuerza el
    fallback de plantilla, igual que el resto del proyecto cuando no
    hay credencial (`OPENAI_API_KEY` vacío por defecto en este entorno
    de test)."""
    monkeypatch.setattr(settings, "OPENAI_API_KEY", "")


class TestProfundidad:
    async def test_fundamentos_limita_bloom_target(self):
        cmg = await generar_cmg(_concept(), _objetivo(bloom_level=4), GenerationConfig(modalidad="mixta", profundidad="fundamentos"))
        assert cmg.bloom_target == 2  # min(4, 2)

    async def test_aplicacion_conserva_bloom_target(self):
        cmg = await generar_cmg(_concept(), _objetivo(bloom_level=4), GenerationConfig(modalidad="mixta", profundidad="aplicacion"))
        assert cmg.bloom_target == 4


class TestModalidad:
    async def test_visual_deshabilita_video_y_audio(self):
        cmg = await generar_cmg(_concept(), _objetivo(), GenerationConfig(modalidad="visual", profundidad="aplicacion"))
        por_modalidad = {p["modality"]: p["enabled"] for p in cmg.multimodal_prompts}
        assert por_modalidad == {"image": True, "video": False, "audio": False}

    async def test_mixta_habilita_todo(self):
        cmg = await generar_cmg(_concept(), _objetivo(), GenerationConfig(modalidad="mixta", profundidad="aplicacion"))
        por_modalidad = {p["modality"]: p["enabled"] for p in cmg.multimodal_prompts}
        assert por_modalidad == {"image": True, "video": True, "audio": True}


class TestContratoEstructural:
    async def test_experimental_y_control_producen_el_mismo_contrato(self):
        """§9: mismo Concept + misma config → mismo contrato estructural
        (nunca igualdad literal de texto — el LLM puede variar)."""
        cmg_exp = await generar_cmg(_concept(), _objetivo(), GenerationConfig(modalidad="visual", profundidad="fundamentos"))
        cmg_ctrl = await generar_cmg(_concept(), _objetivo(), CONTROL_CONFIG)
        for cmg in (cmg_exp, cmg_ctrl):
            assert cmg.explanation
            assert cmg.code
            assert cmg.exercise.prompt
            assert cmg.diagram_mermaid
            assert cmg.diagram_valid is True
        assert cmg_exp.modalidad != cmg_ctrl.modalidad
        assert cmg_exp.profundidad != cmg_ctrl.profundidad

    async def test_explanation_source_es_template_sin_api_key(self):
        cmg = await generar_cmg(_concept(), _objetivo(), CONTROL_CONFIG)
        assert cmg.explanation_source == "template"

    async def test_no_recibe_student_id_ni_learning_state(self):
        """§5: el generador no debe poder recibir student_id/LearningState
        — verificado por firma, no solo por convención."""
        import inspect

        firma = inspect.signature(generar_cmg)
        assert "student_id" not in firma.parameters
        assert "learning_state" not in firma.parameters
        assert "estado" not in firma.parameters
