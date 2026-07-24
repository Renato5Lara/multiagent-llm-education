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


def _estado_con_evaluacion(
    incorrectos: list[int],
    total: int,
    hints_used: int | None = None,
    time_ms: int | None = None,
) -> LearningState:
    estado = LearningState(identidad=_identidad(), contexto={"ruta": "condicionales"})
    contenido = {
        "competencia": "COMP-2",
        "items_incorrectos": incorrectos,
        "items_totales": total,
    }
    if hints_used is not None:
        contenido["hints_used"] = hints_used
    if time_ms is not None:
        contenido["time_ms"] = time_ms
    r1 = registrar_fact(
        estado,
        autor=Capacidad.EVALUAR,
        contenido=contenido,
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

    def test_sin_hints_ni_tiempo_conserva_el_comportamiento_previo(self):
        # Retrocompatibilidad: hechos sin `hints_used`/`time_ms` (todo el
        # historial anterior a este sprint) clasifican exactamente igual
        # que antes — ninguna de las claves nuevas aparece en el contenido.
        (intent,) = producir(_estado_con_evaluacion([1], 4))
        contenido = intent.argumentos["contenido"]
        assert contenido["senal"] == "confusion"
        assert "hints_used" not in contenido
        assert "time_ms" not in contenido

    def test_acierto_con_muchas_ayudas_o_tiempo_lento_no_es_fluidez_real(self):
        # RFC-0002 R4: la señal deja de usar la proporción de errores como
        # ÚNICO proxy — acertar apoyándose en muchas ayudas o tardando
        # mucho no debe leerse como la misma fluidez que acertar rápido y
        # sin apoyo (el usuario, 2026-07-17: "¿está aprendiendo?", no solo
        # "¿respondió bien?").
        (con_ayudas,) = producir(_estado_con_evaluacion([], 4, hints_used=2))
        (lento,) = producir(_estado_con_evaluacion([], 4, time_ms=120_000))
        (fluidez_real,) = producir(
            _estado_con_evaluacion([], 4, hints_used=0, time_ms=10_000)
        )
        assert con_ayudas.argumentos["contenido"]["senal"] == "confusion"
        assert lento.argumentos["contenido"]["senal"] == "confusion"
        assert fluidez_real.argumentos["contenido"]["senal"] == "fluidez"

    def test_falla_parcial_muy_rapida_es_confusion_no_frustracion(self):
        # Falla parcial + muy rápido: probable intento apresurado, no
        # frustración genuina — sigue siendo la señal que ya dispara
        # cambiar de ejemplo (ALTERNATIVAS_POR_SENAL en Adaptar).
        (intent,) = producir(_estado_con_evaluacion([1], 4, time_ms=2_000))
        assert intent.argumentos["contenido"]["senal"] == "confusion"

    def test_falla_parcial_con_muchas_ayudas_y_tiempo_lento_escala_a_frustracion(self):
        # Falla parcial + mucho apoyo + mucho tiempo: seguir insistiendo
        # con el mismo enfoque ya no basta — se trata como frustración
        # (dispara alternativas de acompañamiento, no solo otro ejemplo).
        (intent,) = producir(
            _estado_con_evaluacion([1], 4, hints_used=3, time_ms=100_000)
        )
        assert intent.argumentos["contenido"]["senal"] == "frustracion"

    def test_hints_y_tiempo_se_propagan_igual_en_ambas_versiones(self):
        estado = _estado_con_evaluacion([1], 4, hints_used=2, time_ms=95_000)
        (intent_regla,) = producir(estado)
        (intent_llm,) = producir_llm(estado, proveedor=FakeLLMProvider())
        for intent in (intent_regla, intent_llm):
            contenido = intent.argumentos["contenido"]
            assert contenido["senal"] == "frustracion"
            assert contenido["hints_used"] == 2
            assert contenido["time_ms"] == 95_000
