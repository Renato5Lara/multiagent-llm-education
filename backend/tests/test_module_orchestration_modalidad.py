"""Épica 2 — `_aplicar_modalidad_desde_entrega`: segunda decisión
adaptativa que `module_orchestration_service` deja de tomar por sí
mismo. Mismo patrón que `_bloom_target_desde_entrega` (asunto matching,
ADR-0010): `entrega.asunto` debe ser `f"modalidad({competencia})"`
(`runtime/domain/adaptar/productor.py`), nunca la competencia sola.

Unidad pura, sin Postgres ni LLM.
"""

from __future__ import annotations

from app.models.student_progress import PathModule
from app.services.module_orchestration_service import (
    _aplicar_modalidad_desde_entrega,
    _asunto_de_modalidad,
)
from runtime.boundary import Entrega


def _modulo(titulo: str) -> PathModule:
    return PathModule(id="m1", path_id="p1", title=titulo)


def _entrega_para(modulo: PathModule, diseno: dict) -> Entrega:
    return Entrega(asunto=_asunto_de_modalidad(modulo), diseno=diseno)


_PROMPTS = [
    {"modality": "image", "prompt": "diagrama", "enabled": True},
    {"modality": "video", "prompt": "video", "enabled": True},
    {"modality": "audio", "prompt": "podcast", "enabled": True},
]


class TestAplicarModalidadDesdeEntrega:
    def test_sin_decision_no_toca_nada(self):
        modulo = _modulo("Condicionales")
        entrega = Entrega(asunto=None, diseno=None)
        resultado = _aplicar_modalidad_desde_entrega(_PROMPTS, modulo, entrega)
        assert resultado == _PROMPTS

    def test_decision_sobre_otro_modulo_se_ignora(self):
        modulo = _modulo("Condicionales")
        otro_modulo = _modulo("Bucles y Repetición")
        entrega = _entrega_para(otro_modulo, {"modalidad": "visual"})
        resultado = _aplicar_modalidad_desde_entrega(_PROMPTS, modulo, entrega)
        assert resultado == _PROMPTS

    def test_visual_habilita_solo_imagen(self):
        modulo = _modulo("Condicionales")
        entrega = _entrega_para(modulo, {"modalidad": "visual"})
        resultado = _aplicar_modalidad_desde_entrega(_PROMPTS, modulo, entrega)
        habilitados = {p["modality"] for p in resultado if p["enabled"]}
        assert habilitados == {"image"}
        # El contenido (prompt) no se toca — solo enabled.
        assert all(p["prompt"] == q["prompt"] for p, q in zip(resultado, _PROMPTS))

    def test_mixta_deja_todo_habilitado(self):
        modulo = _modulo("Condicionales")
        entrega = _entrega_para(modulo, {"modalidad": "mixta"})
        resultado = _aplicar_modalidad_desde_entrega(_PROMPTS, modulo, entrega)
        assert resultado == _PROMPTS

    def test_no_muta_la_lista_original(self):
        modulo = _modulo("Condicionales")
        entrega = _entrega_para(modulo, {"modalidad": "visual"})
        original = [dict(p) for p in _PROMPTS]
        _aplicar_modalidad_desde_entrega(_PROMPTS, modulo, entrega)
        assert _PROMPTS == original
