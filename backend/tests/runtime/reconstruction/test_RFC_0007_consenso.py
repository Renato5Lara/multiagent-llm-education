"""RFC-0007 §2.2, fila "Consenso (RFC-0006)" — `derivar_consenso`.

Sin Postgres, sin LangGraph: `LearningState`/`Replay` construidos a mano
contra reducers puros y la mecánica real de `kernel/deliberation/`
(mismo patrón que `tests/runtime/deliberation/`). Los escenarios de
`Resuelta`/`Aplazada` pasan por `mecanica.convocar()` de verdad (no se
fabrica el resultado a mano) para que el margen recalculado por
`_margen` tenga con qué contrastarse honestamente; los escenarios de
cadena de reconvocatoria se construyen directo (mismo criterio que
`TestConflictoQueSeResuelve` en `test_RFC_0007_paisaje.py`): aíslan
`derivar_consenso` de la mecánica de reconvocatoria real, fuera de
alcance de esta pieza.
"""

from __future__ import annotations

from decimal import Decimal

from runtime.engine.checkpoint.consenso import MetricasConsenso, derivar_consenso
from runtime.engine.checkpoint.reconstruccion import TransicionEstado
from runtime.kernel.deliberation.confianza import calcular_confianza_efectiva
from runtime.kernel.deliberation.mecanica import convocar, derivar_decision_directa
from runtime.kernel.deliberation.politica import POLITICAS
from runtime.kernel.reducers import (
    Aplicado,
    registrar_claim,
    registrar_decision,
    registrar_deliberacion,
    registrar_fact,
)
from runtime.kernel.state.entries import (
    Aplazada,
    Capacidad,
    ClaimEntry,
    DeliberacionEntry,
    EntryId,
    Escalada,
    FactEntry,
    OrigenProvenance,
    Provenance,
    Resuelta,
    TipoClaim,
    Vigencia,
)
from runtime.kernel.state.state import Identidad, LearningState

_V1 = POLITICAS["v1"]
_V2 = POLITICAS["v2"]


def _identidad(session_id: str = "s-consenso") -> Identidad:
    return Identidad(
        session_id=session_id,
        student_id="maria",
        version_student_model="v7",
        version_banco="banco-v2",
        version_politica="v1",
        spec_version="foundation-2026-07-10",
    )


def _aplicar(estado: LearningState, resultado) -> LearningState:
    assert isinstance(resultado, Aplicado), resultado
    return resultado.estado


def _replay_de(*estados: LearningState) -> tuple[TransicionEstado, ...]:
    return tuple(TransicionEstado(transicion=e.transicion, estado=e) for e in estados)


def _con_fact(estado: LearningState) -> tuple[LearningState, EntryId]:
    estado = _aplicar(
        estado,
        registrar_fact(
            estado,
            autor=Capacidad.EVALUAR,
            contenido={"competencia": "COMP-2"},
            provenance=Provenance.de(OrigenProvenance.INSTRUMENTO, banco="v2"),
        ),
    )
    return estado, estado.facts[-1].id


class TestConsensoVacio:
    def test_replay_vacio_produce_metricas_vacias(self) -> None:
        metricas = derivar_consenso((), _V1)
        assert metricas == MetricasConsenso(
            convocatorias=0, no_convocatorias=0,
            resueltas=0, aplazadas=0, escaladas=0,
            margenes_resolucion=(), confianza_resolucion=(),
            longitud_cadenas_reconvocacion=(),
        )

    def test_estado_sin_deliberaciones_ni_decisiones(self) -> None:
        estado = LearningState(identidad=_identidad(), contexto={})
        estado, _fact_id = _con_fact(estado)
        metricas = derivar_consenso(_replay_de(estado), _V1)
        assert metricas.convocatorias == 0
        assert metricas.no_convocatorias == 0


class TestConvocatoriaResuelta:
    def test_convocar_real_bajo_v1_produce_resuelta_con_margen_recalculado(self) -> None:
        estado = LearningState(identidad=_identidad(), contexto={})
        estado, fact_id = _con_fact(estado)
        estado = _aplicar(estado, registrar_claim(
            estado, autor=Capacidad.REMEDIAR, tipo=TipoClaim.PROPUESTA,
            asunto="siguiente-paso(sesion)", afirmacion={"accion": "reforzar"},
            respaldo=(fact_id,), confianza=Decimal("0.82"),
            provenance=Provenance.de(OrigenProvenance.REGLA),
        ))
        estado = _aplicar(estado, registrar_claim(
            estado, autor=Capacidad.ORIENTAR, tipo=TipoClaim.PROPUESTA,
            asunto="siguiente-paso(sesion)", afirmacion={"accion": "avanzar"},
            respaldo=(fact_id,), confianza=Decimal("0.75"),
            provenance=Provenance.de(OrigenProvenance.REGLA),
        ))

        intent = convocar(estado, _V1)
        assert intent is not None
        estado = _aplicar(estado, registrar_deliberacion(estado, **intent.argumentos))
        deliberacion = estado.deliberaciones[-1]
        assert isinstance(deliberacion.resultado, Resuelta)

        metricas = derivar_consenso(_replay_de(estado), _V1)

        assert metricas.convocatorias == 1
        assert metricas.resueltas == 1
        assert metricas.aplazadas == 0
        assert metricas.escaladas == 0
        assert metricas.confianza_resolucion == (deliberacion.resultado.confianza,)
        assert len(metricas.margenes_resolucion) == 1
        # v1: delta=0, peso neutro — el margen recalculado es exactamente
        # la diferencia de confianzas declaradas (mismo criterio que
        # convocar() bajo v1, ver docstring de REGLA_POLITICA_V1).
        assert metricas.margenes_resolucion[0] == Decimal("0.82") - Decimal("0.75")


class TestConvocatoriaAplazada:
    def test_convocar_real_bajo_v2_produce_aplazada_con_margen_insuficiente(self) -> None:
        estado = LearningState(identidad=_identidad(), contexto={})
        estado, fact_id = _con_fact(estado)
        estado = _aplicar(estado, registrar_claim(
            estado, autor=Capacidad.REMEDIAR, tipo=TipoClaim.PROPUESTA,
            asunto="siguiente-paso(sesion)", afirmacion={"accion": "reforzar"},
            respaldo=(fact_id,), confianza=Decimal("0.82"),
            provenance=Provenance.de(OrigenProvenance.REGLA),
        ))
        estado = _aplicar(estado, registrar_claim(
            estado, autor=Capacidad.ORIENTAR, tipo=TipoClaim.PROPUESTA,
            asunto="siguiente-paso(sesion)", afirmacion={"accion": "avanzar"},
            respaldo=(fact_id,), confianza=Decimal("0.75"),
            provenance=Provenance.de(OrigenProvenance.REGLA),
        ))

        # margen real 0.07 < delta v2 (0.10) -> Aplazada (mismo escenario
        # que ADR-0012, Escenario A).
        intent = convocar(estado, _V2, urgente=False)
        assert intent is not None
        estado = _aplicar(estado, registrar_deliberacion(estado, **intent.argumentos))
        assert isinstance(estado.deliberaciones[-1].resultado, Aplazada)

        metricas = derivar_consenso(_replay_de(estado), _V2)

        assert metricas.aplazadas == 1
        assert metricas.resueltas == 0
        assert metricas.confianza_resolucion == ()  # Aplazada no tiene confianza de resolución
        assert len(metricas.margenes_resolucion) == 1
        assert metricas.margenes_resolucion[0] == Decimal("0.82") - Decimal("0.75")


class TestNoConvocatoria:
    def test_propuesta_unica_sobre_theta_es_no_convocatoria(self) -> None:
        estado = LearningState(identidad=_identidad(), contexto={})
        estado, fact_id = _con_fact(estado)
        estado = _aplicar(estado, registrar_claim(
            estado, autor=Capacidad.ORIENTAR, tipo=TipoClaim.PROPUESTA,
            asunto="siguiente-paso(sesion)", afirmacion={"accion": "avanzar"},
            respaldo=(fact_id,), confianza=Decimal("0.80"),
            provenance=Provenance.de(OrigenProvenance.REGLA),
        ))

        intent = derivar_decision_directa(estado, _V2)  # theta v2 = 0.5
        assert intent is not None
        estado = _aplicar(estado, registrar_decision(estado, **intent.argumentos))

        metricas = derivar_consenso(_replay_de(estado), _V2)

        assert metricas.convocatorias == 0
        assert metricas.no_convocatorias == 1
        assert metricas.resueltas == 0


class TestCadenasDeReconvocatoria:
    """`LearningState` construido directamente (no vía mecánica real) —
    ver docstring del módulo: aísla `derivar_consenso` de la mecánica
    real de reconvocatoria, fuera de alcance de esta pieza."""

    def test_cadena_aplazada_aplazada_escalada_cuenta_dos_aplazamientos(self) -> None:
        identidad = _identidad()
        fact = FactEntry(
            id=EntryId(1, 1), autor=Capacidad.EVALUAR, contenido={},
            provenance=Provenance.de(OrigenProvenance.INSTRUMENTO),
        )
        rival_a = ClaimEntry(
            id=EntryId(2, 1), autor=Capacidad.REMEDIAR, tipo=TipoClaim.PROPUESTA,
            asunto="siguiente-paso(sesion)", afirmacion={}, respaldo=(fact.id,),
            confianza=Decimal("0.6"), provenance=Provenance.de(OrigenProvenance.REGLA),
        )
        rival_b = ClaimEntry(
            id=EntryId(2, 2), autor=Capacidad.ORIENTAR, tipo=TipoClaim.PROPUESTA,
            asunto="siguiente-paso(sesion)", afirmacion={}, respaldo=(fact.id,),
            confianza=Decimal("0.6"), provenance=Provenance.de(OrigenProvenance.REGLA),
        )
        eslabon_1 = DeliberacionEntry(
            id=EntryId(3, 1), participantes=(rival_a.id, rival_b.id),
            resultado=Aplazada(evidencia_faltante="primera evidencia"),
        )
        eslabon_2 = DeliberacionEntry(
            id=EntryId(4, 1), participantes=(rival_a.id, rival_b.id),
            resultado=Aplazada(evidencia_faltante="segunda evidencia"),
            enlaza_a=eslabon_1.id,
        )
        eslabon_3 = DeliberacionEntry(
            id=EntryId(5, 1), participantes=(rival_a.id, rival_b.id),
            resultado=Escalada(destinatario="docente"),
            enlaza_a=eslabon_2.id,
        )
        estado = LearningState(
            identidad=identidad, contexto={}, facts=(fact,),
            claims=(rival_a, rival_b),
            deliberaciones=(eslabon_1, eslabon_2, eslabon_3),
            transicion=5,
        )

        metricas = derivar_consenso(_replay_de(estado), _V2)

        assert metricas.convocatorias == 3
        assert metricas.aplazadas == 2
        assert metricas.escaladas == 1
        assert metricas.longitud_cadenas_reconvocacion == (2,)
        # la Escalada no aporta margen (ver docstring de _margen)
        assert len(metricas.margenes_resolucion) == 2

    def test_deliberacion_resuelta_sin_reconvocatoria_no_aporta_cadena(self) -> None:
        estado = LearningState(identidad=_identidad(), contexto={})
        estado, fact_id = _con_fact(estado)
        estado = _aplicar(estado, registrar_claim(
            estado, autor=Capacidad.REMEDIAR, tipo=TipoClaim.PROPUESTA,
            asunto="siguiente-paso(sesion)", afirmacion={"accion": "reforzar"},
            respaldo=(fact_id,), confianza=Decimal("0.82"),
            provenance=Provenance.de(OrigenProvenance.REGLA),
        ))
        estado = _aplicar(estado, registrar_claim(
            estado, autor=Capacidad.ORIENTAR, tipo=TipoClaim.PROPUESTA,
            asunto="siguiente-paso(sesion)", afirmacion={"accion": "avanzar"},
            respaldo=(fact_id,), confianza=Decimal("0.75"),
            provenance=Provenance.de(OrigenProvenance.REGLA),
        ))
        intent = convocar(estado, _V1)
        estado = _aplicar(estado, registrar_deliberacion(estado, **intent.argumentos))

        metricas = derivar_consenso(_replay_de(estado), _V1)

        assert metricas.longitud_cadenas_reconvocacion == ()
