"""Suite de invariantes — reducer de deliberaciones (INV-7, INV-8).

Fixture: la tensión canónica n.º 1 (RFC-0002 §4) — ¿avanzar o reforzar?
Remediar y Orientar proponen sobre el mismo asunto.
"""

from decimal import Decimal

from runtime.kernel.events import DeliberacionRegistrada, EntradaSupersedida
from runtime.kernel.reducers import (
    Aplicado,
    Rechazado,
    registrar_claim,
    registrar_deliberacion,
    registrar_fact,
)
from runtime.kernel.state import (
    Aplazada,
    Capacidad,
    EntryId,
    Escalada,
    OrigenProvenance,
    Provenance,
    Resuelta,
    TipoClaim,
)
from runtime.kernel.state.state import Identidad, LearningState


def _propuesta(estado, capacidad, accion, respaldo, asunto="siguiente-paso(sesion)"):
    resultado = registrar_claim(
        estado,
        autor=capacidad,
        tipo=TipoClaim.PROPUESTA,
        asunto=asunto,
        afirmacion={"accion": accion},
        respaldo=respaldo,
        confianza=Decimal("0.8"),
        provenance=Provenance.de(OrigenProvenance.LLM, modelo="m", version="1"),
    )
    assert isinstance(resultado, Aplicado)
    return resultado.estado


def _tension_canonica() -> tuple[LearningState, EntryId, EntryId]:
    """¿Avanzar o reforzar? — dos propuestas vigentes, mismo asunto."""
    estado = LearningState(
        identidad=Identidad(
            session_id="s-001",
            student_id="maria",
            version_student_model="v7",
            version_banco="banco-v2",
            version_politica="politica-v1",
            spec_version="foundation-2026-07-10",
        ),
        contexto={"ruta": "condicionales"},
    )
    r1 = registrar_fact(
        estado,
        autor=Capacidad.EVALUAR,
        contenido={"items_incorrectos": [3, 4, 8]},
        provenance=Provenance.de(OrigenProvenance.INSTRUMENTO, banco="v2"),
    )
    assert isinstance(r1, Aplicado)
    fact_id = r1.estado.facts[0].id
    estado = _propuesta(r1.estado, Capacidad.REMEDIAR, "reforzar", (fact_id,))
    reforzar_id = estado.claims[-1].id
    estado = _propuesta(estado, Capacidad.ORIENTAR, "avanzar", (fact_id,))
    avanzar_id = estado.claims[-1].id
    return estado, reforzar_id, avanzar_id


def _resuelta(aceptado: EntryId) -> Resuelta:
    return Resuelta(
        regla="mayor-confianza-efectiva",
        aceptados=(aceptado,),
        confianza=Decimal("0.74"),
    )


class TestINV_7_RegistrarDeliberacion:
    def test_resuelta_supersede_a_los_rivales(self):
        estado, reforzar, avanzar = _tension_canonica()
        resultado = registrar_deliberacion(
            estado,
            participantes=(reforzar, avanzar),
            resultado=_resuelta(reforzar),
        )
        assert isinstance(resultado, Aplicado)
        nuevo = resultado.estado
        # El aceptado sigue vigente; el rival, supersedido POR la deliberación.
        assert nuevo.es_vigente(reforzar)
        rival = nuevo.buscar(avanzar)
        assert not rival.vigencia.vigente
        assert rival.vigencia.superseded_por == nuevo.deliberaciones[0].id
        # Eventos: la supersesión del rival + el registro del episodio.
        assert isinstance(resultado.eventos[0], EntradaSupersedida)
        registro = resultado.eventos[-1]
        assert isinstance(registro, DeliberacionRegistrada)
        assert registro.resultado == "resuelta"

    def test_aplazada_no_supersede_nada(self):
        estado, reforzar, avanzar = _tension_canonica()
        resultado = registrar_deliberacion(
            estado,
            participantes=(reforzar, avanzar),
            resultado=Aplazada(evidencia_faltante="resultado de micro-actividad"),
        )
        assert isinstance(resultado, Aplicado)
        assert resultado.estado.es_vigente(reforzar)
        assert resultado.estado.es_vigente(avanzar)

    def test_aceptado_fuera_de_participantes_rechazado(self):
        # P15: la deliberación selecciona entre sus participantes.
        estado, reforzar, avanzar = _tension_canonica()
        resultado = registrar_deliberacion(
            estado,
            participantes=(reforzar, avanzar),
            resultado=_resuelta(EntryId(9, 9)),
        )
        assert isinstance(resultado, Rechazado)
        assert resultado.invariante == "INV-7"
        assert "P15" in resultado.motivo

    def test_aplazada_sin_evidencia_faltante_rechazada(self):
        estado, reforzar, avanzar = _tension_canonica()
        resultado = registrar_deliberacion(
            estado,
            participantes=(reforzar, avanzar),
            resultado=Aplazada(evidencia_faltante=""),
        )
        assert isinstance(resultado, Rechazado)
        assert resultado.invariante == "INV-7"

    def test_enlaza_a_solo_deliberaciones(self):
        # CONCEPT-0002 §5: no hay reapertura — hay nueva deliberación enlazada.
        estado, reforzar, avanzar = _tension_canonica()
        resultado = registrar_deliberacion(
            estado,
            participantes=(reforzar, avanzar),
            resultado=Escalada(),
            enlaza_a=reforzar,  # un claim, no una deliberación
        )
        assert isinstance(resultado, Rechazado)
        assert "reapertura" in resultado.motivo

    def test_P14_el_estado_anterior_queda_intacto(self):
        estado, reforzar, avanzar = _tension_canonica()
        registrar_deliberacion(
            estado, participantes=(reforzar, avanzar), resultado=_resuelta(reforzar)
        )
        assert estado.deliberaciones == ()
        assert estado.es_vigente(avanzar)


class TestINV_8_SoloClaimsEnTension:
    def test_los_facts_no_se_deliberan(self):
        estado, reforzar, _ = _tension_canonica()
        resultado = registrar_deliberacion(
            estado,
            participantes=(reforzar, estado.facts[0].id),
            resultado=_resuelta(reforzar),
        )
        assert isinstance(resultado, Rechazado)
        assert resultado.invariante == "INV-8"

    def test_mismo_asunto_obligatorio(self):
        estado, reforzar, _ = _tension_canonica()
        estado = _propuesta(
            estado,
            Capacidad.ADAPTAR,
            "visual",
            (estado.facts[0].id,),
            asunto="modalidad(objetivo-x)",
        )
        otro_asunto = estado.claims[-1].id
        resultado = registrar_deliberacion(
            estado,
            participantes=(reforzar, otro_asunto),
            resultado=_resuelta(reforzar),
        )
        assert isinstance(resultado, Rechazado)
        assert "MISMO asunto" in resultado.motivo

    def test_participante_supersedido_rechazado(self):
        estado, reforzar, avanzar = _tension_canonica()
        primera = registrar_deliberacion(
            estado, participantes=(reforzar, avanzar), resultado=_resuelta(reforzar)
        )
        assert isinstance(primera, Aplicado)
        # `avanzar` quedó supersedido: no puede participar de nuevo.
        segunda = registrar_deliberacion(
            primera.estado,
            participantes=(reforzar, avanzar),
            resultado=_resuelta(reforzar),
        )
        assert isinstance(segunda, Rechazado)
        assert segunda.invariante == "INV-8"
