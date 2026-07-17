"""Guardián de P13 para Adaptar (ADR-0005 §7) — séptima capacidad.

El corazón de la hipótesis. Además del contrato compartido, vigila
explícitamente la frontera dominio/plataforma que el tesista exigió:
Adaptar decide categorías pedagógicas, nunca recursos físicos.
"""

from decimal import Decimal

from runtime.domain.adaptar import FakeLLMProvider, producir, producir_llm
from runtime.domain.shared.causal import senal_tutorizar_de_decision
from runtime.kernel.reducers import Aplicado, registrar_claim, registrar_decision, registrar_fact
from runtime.kernel.state import (
    Capacidad,
    OrigenProvenance,
    Provenance,
    TipoClaim,
)
from runtime.kernel.state.state import Identidad, LearningState

_PROHIBIDO = ("url", "http", ".pdf", ".mp4", "recurso_id", "video_", "pdf_")


def _identidad() -> Identidad:
    return Identidad(
        session_id="s-p13-adaptar",
        student_id="maria",
        version_student_model="v7",
        version_banco="banco-v2",
        version_politica="politica-v1",
        spec_version="foundation-2026-07-10",
    )


def _estado_con_decision(accion: str) -> LearningState:
    estado = LearningState(identidad=_identidad(), contexto={"ruta": "condicionales"})
    r1 = registrar_fact(
        estado,
        autor=Capacidad.EVALUAR,
        contenido={"competencia": "COMP-2", "items_incorrectos": [3, 4, 8]},
        provenance=Provenance.de(OrigenProvenance.INSTRUMENTO, banco="v2"),
    )
    assert isinstance(r1, Aplicado)
    r2 = registrar_claim(
        r1.estado,
        autor=Capacidad.DIAGNOSTICAR,
        tipo=TipoClaim.INTERPRETACION,
        asunto="dominio(COMP-2)",
        afirmacion={"dominada": False},
        respaldo=(r1.estado.facts[0].id,),
        confianza=Decimal("0.78"),
        provenance=Provenance.de(OrigenProvenance.REGLA, id="scoring-v1"),
    )
    assert isinstance(r2, Aplicado)
    r3 = registrar_claim(
        r2.estado,
        autor=Capacidad.REMEDIAR,
        tipo=TipoClaim.PROPUESTA,
        asunto="siguiente-paso(sesion)",
        afirmacion={"accion": accion},
        respaldo=(r2.estado.claims[0].id,),
        confianza=Decimal("0.82"),
        provenance=Provenance.de(OrigenProvenance.REGLA, id="remediacion-v1"),
    )
    assert isinstance(r3, Aplicado)
    r4 = registrar_decision(
        r3.estado, origen=r3.estado.claims[-1].id, contenido={"accion": accion}
    )
    assert isinstance(r4, Aplicado)
    return r4.estado


def _texto_plano(valor) -> str:
    return str(valor).lower()


class TestP13_AdaptarContratoCompartido:
    def test_mismo_operacion_tipo_asunto_y_respaldo(self):
        estado = _estado_con_decision("reforzar")
        decision_id = estado.decisiones[0].id
        (intent_regla,) = producir(estado)
        (intent_llm,) = producir_llm(estado, proveedor=FakeLLMProvider())

        for intent in (intent_regla, intent_llm):
            assert intent.operacion == "registrar_claim"
            assert intent.argumentos["autor"] is Capacidad.ADAPTAR
            assert intent.argumentos["tipo"] is TipoClaim.PROPUESTA
            assert intent.argumentos["asunto"] == "modalidad(COMP-2)"
            assert intent.argumentos["respaldo"] == (decision_id,)
            assert isinstance(intent.argumentos["confianza"], Decimal)
            afirmacion = intent.argumentos["afirmacion"]
            assert "modalidad" in afirmacion
            assert "profundidad" in afirmacion
            assert "alternativas_descartadas" in afirmacion
            assert len(afirmacion["alternativas_descartadas"]) >= 1

        assert intent_regla.argumentos["provenance"].origen == OrigenProvenance.REGLA
        assert intent_llm.argumentos["provenance"].origen == OrigenProvenance.LLM

    def test_frontera_dura_nunca_recursos_fisicos(self):
        # Exigencia explícita del tesista: Adaptar decide categorías
        # pedagógicas, jamás IDs de contenido, URLs ni rutas de plataforma.
        for accion in ("reforzar", "avanzar-con-andamiaje"):
            estado = _estado_con_decision(accion)
            (intent_regla,) = producir(estado)
            (intent_llm,) = producir_llm(estado, proveedor=FakeLLMProvider())
            for intent in (intent_regla, intent_llm):
                texto = _texto_plano(intent.argumentos["afirmacion"])
                for prohibido in _PROHIBIDO:
                    assert prohibido not in texto, (
                        f"Adaptar produjo algo que parece un recurso físico "
                        f"({prohibido!r}): {texto}"
                    )

    def test_responde_distinto_segun_la_accion(self):
        reforzar = _estado_con_decision("reforzar")
        avanzar = _estado_con_decision("avanzar-con-andamiaje")
        (intent_reforzar,) = producir(reforzar)
        (intent_avanzar,) = producir(avanzar)
        assert (
            intent_reforzar.argumentos["afirmacion"]["modalidad"]
            != intent_avanzar.argumentos["afirmacion"]["modalidad"]
        )

    def test_sin_decision_reconocida_no_dispara(self):
        estado = _estado_con_decision("accion-desconocida")
        assert producir(estado) == ()
        assert producir_llm(estado) == ()

    def test_no_adapta_la_misma_decision_dos_veces(self):
        estado = _estado_con_decision("reforzar")
        (intent,) = producir(estado)
        resultado = registrar_claim(estado, **intent.argumentos)
        assert isinstance(resultado, Aplicado)
        assert producir(resultado.estado) == ()


def _estado_con_decision_y_senal(accion: str, senal: str) -> LearningState:
    """PR-6: mismo fixture que `_estado_con_decision`, con un fact de
    Tutorizar añadido — ligado causalmente (`fact_origen`) al mismo fact
    original de Evaluar, nunca por posición."""
    estado = _estado_con_decision(accion)
    fact_evaluar_id = estado.facts[0].id
    r_senal = registrar_fact(
        estado,
        autor=Capacidad.TUTORIZAR,
        contenido={
            "senal": senal,
            "fact_origen": str(fact_evaluar_id),
            "items_incorrectos": 3,
            "items_totales": 10,
        },
        provenance=Provenance.de(OrigenProvenance.REGLA, id="deteccion-conductual-v1"),
    )
    assert isinstance(r_senal, Aplicado)
    return r_senal.estado


class TestP13_AdaptarConsumeSenalDeTutorizar:
    """RFC-0002 §3: Adaptar lee "señales de sesión" y escribe su propuesta
    "con las alternativas que evaluó" — deja de ser una tabla fija por
    acción cuando la señal de Tutorizar existe en el estado (PR-6)."""

    def test_resuelve_la_senal_por_causalidad_no_por_posicion(self):
        estado = _estado_con_decision_y_senal("reforzar", "confusion")
        decision = estado.decisiones[0]
        senal_fact = senal_tutorizar_de_decision(estado, decision)
        assert senal_fact is not None
        assert senal_fact.contenido["senal"] == "confusion"

    def test_la_misma_accion_produce_alternativas_distintas_segun_la_senal(self):
        confusion = _estado_con_decision_y_senal("reforzar", "confusion")
        frustracion = _estado_con_decision_y_senal("reforzar", "frustracion")

        (intent_confusion,) = producir(confusion)
        (intent_frustracion,) = producir(frustracion)

        assert (
            intent_confusion.argumentos["afirmacion"]["alternativas_descartadas"]
            != intent_frustracion.argumentos["afirmacion"]["alternativas_descartadas"]
        )

    def test_el_respaldo_crece_al_fact_de_tutorizar_cuando_existe(self):
        estado = _estado_con_decision_y_senal("reforzar", "frustracion")
        decision = estado.decisiones[0]
        senal_fact = senal_tutorizar_de_decision(estado, decision)

        (intent,) = producir(estado)
        assert intent.argumentos["respaldo"] == (decision.id, senal_fact.id)

    def test_regla_y_llm_coinciden_en_variar_por_senal(self):
        estado = _estado_con_decision_y_senal("reforzar", "frustracion")
        (intent_regla,) = producir(estado)
        (intent_llm,) = producir_llm(estado, proveedor=FakeLLMProvider())

        for intent in (intent_regla, intent_llm):
            razones = {
                alt["modalidad"]
                for alt in intent.argumentos["afirmacion"]["alternativas_descartadas"]
            }
            assert razones == {"guiado", "practica"}

    def test_sin_senal_en_el_estado_se_mantiene_el_diseno_por_accion(self):
        # Regresión: los fixtures sin Tutorizar (María, P13 base) no deben
        # cambiar de comportamiento — respaldo de un solo elemento.
        estado = _estado_con_decision("reforzar")
        (intent,) = producir(estado)
        assert intent.argumentos["respaldo"] == (estado.decisiones[0].id,)
        assert intent.argumentos["afirmacion"]["alternativas_descartadas"] == (
            {"modalidad": "textual", "razon": "ya insuficiente en el intento anterior"},
            {"modalidad": "ejemplo-codigo", "razon": "prematuro sin el concepto consolidado"},
        )


class TestP13_AdaptarResuelveTensionAvanzarVsFrustracion:
    """Tensión canónica #3 (RFC-0002 §4): el resultado puntual dominó
    (accion="avanzar-con-andamiaje"), pero la señal de sesión de Tutorizar
    contradice — Adaptar debe confiar en la evidencia conductual y
    retroceder la profundidad, no solo anotar la contradicción como
    alternativa descartada (2026-07-17, sprint "señales cambian el
    diseño real, no solo la traza")."""

    def test_avanzar_con_frustracion_retrocede_a_fundamentos(self):
        estado = _estado_con_decision_y_senal("avanzar-con-andamiaje", "frustracion")
        (intent_regla,) = producir(estado)
        (intent_llm,) = producir_llm(estado, proveedor=FakeLLMProvider())
        for intent in (intent_regla, intent_llm):
            assert intent.argumentos["afirmacion"]["profundidad"] == "fundamentos"

    def test_avanzar_con_confusion_o_fluidez_no_retrocede(self):
        # Regresión: solo la contradicción MÁS fuerte (frustración) cambia
        # profundidad — confusión y fluidez siguen afectando solo las
        # alternativas descartadas, como ya hacían antes de este sprint.
        confusion = _estado_con_decision_y_senal("avanzar-con-andamiaje", "confusion")
        fluidez = _estado_con_decision_y_senal("avanzar-con-andamiaje", "fluidez")
        (intent_confusion,) = producir(confusion)
        (intent_fluidez,) = producir(fluidez)
        assert intent_confusion.argumentos["afirmacion"]["profundidad"] == "aplicacion"
        assert intent_fluidez.argumentos["afirmacion"]["profundidad"] == "aplicacion"

    def test_reforzar_con_frustracion_ya_era_fundamentos_no_cambia_nada(self):
        # "reforzar" ya es "fundamentos" por defecto — la tensión #3 solo
        # es alcanzable desde "avanzar-con-andamiaje" (la única acción que
        # puede contradecir una señal de frustración real).
        estado = _estado_con_decision_y_senal("reforzar", "frustracion")
        (intent,) = producir(estado)
        assert intent.argumentos["afirmacion"]["profundidad"] == "fundamentos"
