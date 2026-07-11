"""Guardián de P13 para Tutorizar (ADR-0005 §7) — octava y última
capacidad de M2. Segunda familia fact-producer (junto a Evaluar): sin
tipo/asunto/respaldo/confianza — esos campos no existen en un fact.
"""

from runtime.domain.tutorizar import FakeLLMProvider, producir, producir_llm
from runtime.kernel.reducers import Aplicado, registrar_fact
from runtime.kernel.state import Capacidad, OrigenProvenance, Provenance
from runtime.kernel.state.state import Identidad, LearningState

_LIBRE_PROHIBIDO = ("hola", "veo que", "¿por qué", "intenta de nuevo", "!")


def _identidad() -> Identidad:
    return Identidad(
        session_id="s-p13-tutorizar",
        student_id="maria",
        version_student_model="v7",
        version_banco="banco-v2",
        version_politica="politica-v1",
        spec_version="foundation-2026-07-10",
    )


def _estado_con_evaluacion(incorrectos: list[int], total: int) -> LearningState:
    estado = LearningState(identidad=_identidad(), contexto={"ruta": "condicionales"})
    r1 = registrar_fact(
        estado,
        autor=Capacidad.EVALUAR,
        contenido={
            "competencia": "COMP-2",
            "items_incorrectos": incorrectos,
            "items_totales": total,
        },
        provenance=Provenance.de(OrigenProvenance.INSTRUMENTO, banco="v2"),
    )
    assert isinstance(r1, Aplicado)
    return r1.estado


class TestP13_TutorizarContratoCompartido:
    def test_mismo_operacion_y_mismas_claves_de_contenido(self):
        estado = _estado_con_evaluacion([3, 4, 8], 6)
        (intent_regla,) = producir(estado)
        (intent_llm,) = producir_llm(estado, proveedor=FakeLLMProvider())

        for intent in (intent_regla, intent_llm):
            assert intent.operacion == "registrar_fact"
            assert intent.argumentos["autor"] is Capacidad.TUTORIZAR
            contenido = intent.argumentos["contenido"]
            assert set(contenido) == {
                "senal",
                "fact_origen",
                "items_incorrectos",
                "items_totales",
            }
            # Sin tipo/asunto/respaldo/confianza — no existen en un fact.
            assert "confianza" not in intent.argumentos
            assert "respaldo" not in intent.argumentos
            assert "asunto" not in intent.argumentos

        assert intent_regla.argumentos["provenance"].origen == OrigenProvenance.REGLA
        assert intent_llm.argumentos["provenance"].origen == OrigenProvenance.LLM

    def test_frontera_dura_nunca_texto_libre_al_estudiante(self):
        # Exigencia del tesista: Tutorizar detecta, no redacta.
        for incorrectos, total in (([], 4), ([1, 2, 3], 3), ([1], 4)):
            estado = _estado_con_evaluacion(incorrectos, total)
            (intent_regla,) = producir(estado)
            (intent_llm,) = producir_llm(estado, proveedor=FakeLLMProvider())
            for intent in (intent_regla, intent_llm):
                texto = str(intent.argumentos["contenido"]).lower()
                for prohibido in _LIBRE_PROHIBIDO:
                    assert prohibido not in texto

    def test_clasifica_las_tres_senales(self):
        (fluidez,) = producir(_estado_con_evaluacion([], 4))
        (confusion,) = producir(_estado_con_evaluacion([1], 4))
        (frustracion,) = producir(_estado_con_evaluacion([1, 2, 3], 3))
        assert fluidez.argumentos["contenido"]["senal"] == "fluidez"
        assert confusion.argumentos["contenido"]["senal"] == "confusion"
        assert frustracion.argumentos["contenido"]["senal"] == "frustracion"

    def test_sin_evaluacion_no_dispara(self):
        estado = LearningState(
            identidad=_identidad(), contexto={"ruta": "condicionales"}
        )
        assert producir(estado) == ()
        assert producir_llm(estado) == ()

    def test_no_redetecta_el_mismo_fact_dos_veces(self):
        estado = _estado_con_evaluacion([3, 4, 8], 6)
        (intent,) = producir(estado)
        resultado = registrar_fact(estado, **intent.argumentos)
        assert isinstance(resultado, Aplicado)
        assert producir(resultado.estado) == ()
