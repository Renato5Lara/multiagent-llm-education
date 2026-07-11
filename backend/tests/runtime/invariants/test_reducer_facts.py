"""Suite de invariantes — el primer reducer (RFC-0003 §4)."""

from runtime.kernel.events import FactRegistrado, TransicionRechazada
from runtime.kernel.reducers import Aplicado, Rechazado, registrar_fact
from runtime.kernel.state import BOUNDARY, Capacidad, OrigenProvenance, Provenance
from runtime.kernel.state.state import Identidad, LearningState


def _estado() -> LearningState:
    return LearningState(
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


class TestINV_4_RegistrarFact:
    def test_aplicado_produce_estado_nuevo_y_evento(self):
        antes = _estado()
        resultado = registrar_fact(
            antes,
            autor=Capacidad.EVALUAR,
            contenido={"items_incorrectos": [3, 4, 8]},
            provenance=Provenance.de(OrigenProvenance.INSTRUMENTO, banco="v2"),
        )
        assert isinstance(resultado, Aplicado)
        assert len(resultado.estado.facts) == 1
        assert resultado.estado.transicion == 1
        evento = resultado.eventos[0]
        assert isinstance(evento, FactRegistrado)
        assert evento.transicion == 1
        assert str(evento.entry_id) == "T-000001/e1"

    def test_P14_el_estado_anterior_queda_intacto(self):
        antes = _estado()
        registrar_fact(
            antes,
            autor=BOUNDARY,
            contenido={"tiempo_seg": 35},
            provenance=Provenance.de(OrigenProvenance.TELEMETRIA),
        )
        assert antes.facts == ()
        assert antes.transicion == 0

    def test_rechazo_registrado_como_evento(self):
        # RFC-0003 §4: un rechazo es información, no una excepción silenciosa.
        resultado = registrar_fact(
            _estado(),
            autor="frontend",
            contenido={},
            provenance=Provenance.de(OrigenProvenance.TELEMETRIA),
        )
        assert isinstance(resultado, Rechazado)
        assert resultado.invariante == "INV-4"
        evento = resultado.eventos[0]
        assert isinstance(evento, TransicionRechazada)
        assert evento.invariante == "INV-4"

    def test_A4_tiempo_logico_avanza_por_transicion(self):
        # A4: la edad se mide en transiciones, jamás en reloj de pared.
        estado = _estado()
        for esperado in (1, 2, 3):
            resultado = registrar_fact(
                estado,
                autor=BOUNDARY,
                contenido={"n": esperado},
                provenance=Provenance.de(OrigenProvenance.TELEMETRIA),
            )
            assert isinstance(resultado, Aplicado)
            estado = resultado.estado
            assert estado.transicion == esperado

    def test_exactamente_dos_resultados_posibles(self):
        # H3 reubicada: el reducer jamás aplaza — aplica o rechaza-registra.
        aplicado = registrar_fact(
            _estado(),
            autor=BOUNDARY,
            contenido={},
            provenance=Provenance.de(OrigenProvenance.TELEMETRIA),
        )
        rechazado = registrar_fact(
            _estado(),
            autor="nadie",
            contenido={},
            provenance=Provenance.de(OrigenProvenance.TELEMETRIA),
        )
        assert isinstance(aplicado, (Aplicado, Rechazado))
        assert isinstance(rechazado, (Aplicado, Rechazado))
