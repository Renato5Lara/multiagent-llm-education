"""Guardián de P13 para Evaluar (ADR-0005 §7) — primera capacidad cuyo
contrato es un FACT, no un claim. La comparación cambia de forma: sin
`tipo`/`asunto`/`respaldo`/`confianza` (esos campos no existen en
FactEntry — INV-4, la asimetría estructural). Sin walkthrough completo
todavía: Evaluar aún no está conectado a la ruta principal del grafo
(pertenece a "completar el ciclo pedagógico", prioridad 2 de M2).
"""

from runtime.domain.evaluar import FakeLLMProvider, producir, producir_llm
from runtime.kernel.state.entries import OrigenProvenance
from runtime.kernel.state.state import Identidad, LearningState


def _identidad() -> Identidad:
    return Identidad(
        session_id="s-p13-evaluar",
        student_id="maria",
        version_student_model="v7",
        version_banco="banco-v2",
        version_politica="politica-v1",
        spec_version="foundation-2026-07-10",
    )


def _estado() -> LearningState:
    return LearningState(identidad=_identidad(), contexto={"ruta": "condicionales"})


_RESPUESTAS = {1: True, 2: True, 3: False, 4: False, 5: True, 8: False}


class TestP13_EvaluarContratoCompartido:
    def test_mismo_autor_y_mismas_claves_de_contenido(self):
        estado = _estado()
        (intent_regla,) = producir(estado, _RESPUESTAS, competencia="COMP-2")
        (intent_llm,) = producir_llm(
            estado, _RESPUESTAS, competencia="COMP-2", proveedor=FakeLLMProvider()
        )

        for intent in (intent_regla, intent_llm):
            assert intent.operacion == "registrar_fact"
            assert intent.argumentos["autor"].value == "evaluar"
            contenido = intent.argumentos["contenido"]
            assert set(contenido) == {
                "competencia",
                "items_incorrectos",
                "items_totales",
            }
            # Sin tipo/asunto/respaldo/confianza — no existen en un fact
            # (INV-4): la asimetría estructural, verificada en el contrato.
            assert not hasattr(intent.argumentos, "tipo")
            assert "respaldo" not in intent.argumentos
            assert "confianza" not in intent.argumentos

        # A diferencia de las otras tres capacidades, la versión
        # determinista de Evaluar es INSTRUMENTO (examen autocalificado
        # contra un banco), no REGLA — una tercera divergencia del
        # patrón, además de fact-vs-claim y el parámetro externo.
        assert (
            intent_regla.argumentos["provenance"].origen
            == OrigenProvenance.INSTRUMENTO
        )
        assert intent_llm.argumentos["provenance"].origen == OrigenProvenance.LLM

    def test_el_conteo_coincide_por_construccion_del_fake(self):
        # El fake espeja el conteo real — el contrato no lo EXIGE
        # (el contenido puede variar), pero aquí ambos concuerdan porque
        # ambos cuentan sobre las MISMAS respuestas (P12: nada inventado).
        estado = _estado()
        (intent_regla,) = producir(estado, _RESPUESTAS, competencia="COMP-2")
        (intent_llm,) = producir_llm(
            estado, _RESPUESTAS, competencia="COMP-2", proveedor=FakeLLMProvider()
        )
        assert (
            intent_regla.argumentos["contenido"]["items_incorrectos"]
            == intent_llm.argumentos["contenido"]["items_incorrectos"]
            == [3, 4, 8]
        )

    def test_guard_clause_evita_reevaluar_la_misma_competencia(self):
        estado = _estado()
        (intent,) = producir(estado, _RESPUESTAS, competencia="COMP-2")
        # Simular que ya fue aplicado (fact vigente con esa competencia).
        import dataclasses

        from runtime.kernel.reducers import registrar_fact

        resultado = registrar_fact(estado, **intent.argumentos)
        estado_con_fact = resultado.estado
        assert producir(estado_con_fact, _RESPUESTAS, competencia="COMP-2") == ()
        assert (
            producir(estado_con_fact, _RESPUESTAS, competencia="COMP-5") != ()
        )  # otra competencia sí dispara
