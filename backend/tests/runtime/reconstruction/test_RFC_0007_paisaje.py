"""RFC-0007 §2.2, fila "Paisaje (H8 — ADOPTADA)" — `calcular_paisaje` y
`derivar_paisaje`.

Sin Postgres, sin LangGraph: `LearningState` construido a mano contra
reducers puros (mismo patrón que `tests/runtime/deliberation/`). Política
`"v1"` (pesos en cero, RFC-0006/1): `ce` == confianza declarada, así los
casos pueden fijar la entropía esperada sin depender de refuerzo/decaimiento.
`TestConflictoQueSeResuelve` construye los `LearningState` directamente
(no vía reducer): `derivar_paisaje` es una función pura sobre la
secuencia de estados de un `Replay` — su contrato no depende de cómo se
produjo cada estado, y construirlos a mano aísla la prueba de la
mecánica de supersesión de claims (fuera de alcance de esta pieza)."""

from __future__ import annotations

from decimal import Decimal
from math import isclose, log2

from runtime.engine.checkpoint.paisaje import Paisaje, calcular_paisaje, derivar_paisaje
from runtime.engine.checkpoint.reconstruccion import TransicionEstado
from runtime.kernel.deliberation.mecanica import convocar
from runtime.kernel.deliberation.politica import POLITICAS
from runtime.kernel.reducers import Aplicado, registrar_claim, registrar_deliberacion, registrar_fact
from runtime.kernel.state.entries import (
    Aplazada,
    Capacidad,
    ClaimEntry,
    EntryId,
    FactEntry,
    OrigenProvenance,
    Provenance,
    TipoClaim,
    Vigencia,
)
from runtime.kernel.state.state import Identidad, LearningState

_POLITICA = POLITICAS["v1"]


def _identidad() -> Identidad:
    return Identidad(
        session_id="s-paisaje",
        student_id="maria",
        version_student_model="v7",
        version_banco="banco-v2",
        version_politica="v1",
        spec_version="foundation-2026-07-10",
    )


def _aplicar(estado: LearningState, resultado) -> LearningState:
    assert isinstance(resultado, Aplicado), resultado
    return resultado.estado


def _con_fact(estado: LearningState) -> tuple[LearningState, "EntryId"]:
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


def _con_claim(
    estado: LearningState,
    *,
    asunto: str,
    respaldo,
    confianza: str,
    tipo: TipoClaim = TipoClaim.PROPUESTA,
    autor: Capacidad = Capacidad.ADAPTAR,
) -> LearningState:
    return _aplicar(
        estado,
        registrar_claim(
            estado,
            autor=autor,
            tipo=tipo,
            asunto=asunto,
            afirmacion={"valor": asunto},
            respaldo=respaldo,
            confianza=Decimal(confianza),
            provenance=Provenance.de(OrigenProvenance.REGLA),
        ),
    )


class TestPaisajeVacio:
    def test_estado_sin_claims_produce_paisaje_vacio(self) -> None:
        estado = LearningState(identidad=_identidad(), contexto={})
        paisaje = calcular_paisaje(estado, _POLITICA)
        assert paisaje == Paisaje(densidad={}, conflicto={}, entropia={})


class TestDensidad:
    def test_un_claim_vigente_cuenta_como_densidad_uno(self) -> None:
        estado = LearningState(identidad=_identidad(), contexto={})
        estado, fact_id = _con_fact(estado)
        estado = _con_claim(estado, asunto="modalidad(sesion)", respaldo=(fact_id,), confianza="0.7")

        paisaje = calcular_paisaje(estado, _POLITICA)

        assert paisaje.densidad == {"modalidad(sesion)": 1}
        assert paisaje.conflicto == {}
        assert paisaje.entropia == {"modalidad(sesion)": 0.0}


class TestConflicto:
    def test_dos_propuestas_rivales_sin_deliberacion_es_bloqueante(self) -> None:
        estado = LearningState(identidad=_identidad(), contexto={})
        estado, fact_id = _con_fact(estado)
        estado = _con_claim(
            estado, asunto="siguiente-paso(sesion)", respaldo=(fact_id,),
            confianza="0.82", autor=Capacidad.REMEDIAR,
        )
        estado = _con_claim(
            estado, asunto="siguiente-paso(sesion)", respaldo=(fact_id,),
            confianza="0.75", autor=Capacidad.ORIENTAR,
        )

        paisaje = calcular_paisaje(estado, _POLITICA)

        assert paisaje.conflicto == {"siguiente-paso(sesion)": "bloqueante"}
        assert paisaje.densidad == {"siguiente-paso(sesion)": 2}

    def test_rivalidad_con_deliberacion_aplazada_abierta_es_latente(self) -> None:
        estado = LearningState(identidad=_identidad(), contexto={})
        estado, fact_id = _con_fact(estado)
        estado = _con_claim(
            estado, asunto="siguiente-paso(sesion)", respaldo=(fact_id,),
            confianza="0.50", autor=Capacidad.REMEDIAR,
        )
        estado = _con_claim(
            estado, asunto="siguiente-paso(sesion)", respaldo=(fact_id,),
            confianza="0.50", autor=Capacidad.ORIENTAR,
        )
        # margen 0 < delta de una política con delta > 0 aplazaría — aquí
        # se registra la Aplazada directamente para aislar la prueba de
        # `conflicto` de la mecánica de `convocar` (ya cubierta en
        # `tests/runtime/deliberation/`).
        participantes = tuple(c.id for c in estado.claims if c.tipo is TipoClaim.PROPUESTA)
        estado = _aplicar(
            estado,
            registrar_deliberacion(
                estado,
                participantes=participantes,
                resultado=Aplazada(evidencia_faltante="más evidencia de validación"),
            ),
        )

        paisaje = calcular_paisaje(estado, _POLITICA)

        assert paisaje.conflicto == {"siguiente-paso(sesion)": "latente"}

    def test_un_solo_claim_no_genera_conflicto(self) -> None:
        estado = LearningState(identidad=_identidad(), contexto={})
        estado, fact_id = _con_fact(estado)
        estado = _con_claim(estado, asunto="modalidad(sesion)", respaldo=(fact_id,), confianza="0.7")

        paisaje = calcular_paisaje(estado, _POLITICA)
        assert paisaje.conflicto == {}


class TestEntropia:
    def test_confianzas_iguales_produce_entropia_maxima_de_un_bit(self) -> None:
        estado = LearningState(identidad=_identidad(), contexto={})
        estado, fact_id = _con_fact(estado)
        estado = _con_claim(
            estado, asunto="siguiente-paso(sesion)", respaldo=(fact_id,),
            confianza="0.5", autor=Capacidad.REMEDIAR,
        )
        estado = _con_claim(
            estado, asunto="siguiente-paso(sesion)", respaldo=(fact_id,),
            confianza="0.5", autor=Capacidad.ORIENTAR,
        )

        paisaje = calcular_paisaje(estado, _POLITICA)

        assert isclose(paisaje.entropia["siguiente-paso(sesion)"], 1.0, abs_tol=1e-9)

    def test_confianza_dominante_produce_entropia_baja(self) -> None:
        estado = LearningState(identidad=_identidad(), contexto={})
        estado, fact_id = _con_fact(estado)
        estado = _con_claim(
            estado, asunto="siguiente-paso(sesion)", respaldo=(fact_id,),
            confianza="0.95", autor=Capacidad.REMEDIAR,
        )
        estado = _con_claim(
            estado, asunto="siguiente-paso(sesion)", respaldo=(fact_id,),
            confianza="0.05", autor=Capacidad.ORIENTAR,
        )

        paisaje = calcular_paisaje(estado, _POLITICA)
        esperado = -(0.95 * log2(0.95) + 0.05 * log2(0.05))

        assert isclose(paisaje.entropia["siguiente-paso(sesion)"], esperado, abs_tol=1e-9)
        assert paisaje.entropia["siguiente-paso(sesion)"] < 1.0


class TestDerivarPaisaje:
    def test_replay_de_un_solo_paso_tiene_estabilidad_cero_y_sin_tiempos(self) -> None:
        estado = LearningState(identidad=_identidad(), contexto={})
        estado, fact_id = _con_fact(estado)
        estado = _con_claim(estado, asunto="modalidad(sesion)", respaldo=(fact_id,), confianza="0.7")
        replay = (TransicionEstado(transicion=estado.transicion, estado=estado),)

        pasos, tiempos = derivar_paisaje(replay, _POLITICA)

        assert len(pasos) == 1
        assert pasos[0].transicion == estado.transicion
        assert pasos[0].paisaje == calcular_paisaje(estado, _POLITICA)
        assert pasos[0].estabilidad == 0
        assert tiempos == {}

    def test_aparicion_de_conflicto_eleva_la_estabilidad_del_paso(self) -> None:
        estado = LearningState(identidad=_identidad(), contexto={})
        estado, fact_id = _con_fact(estado)
        estado1 = _con_claim(
            estado, asunto="siguiente-paso(sesion)", respaldo=(fact_id,),
            confianza="0.82", autor=Capacidad.REMEDIAR,
        )
        estado2 = _con_claim(
            estado1, asunto="siguiente-paso(sesion)", respaldo=(fact_id,),
            confianza="0.75", autor=Capacidad.ORIENTAR,
        )
        replay = (
            TransicionEstado(transicion=estado1.transicion, estado=estado1),
            TransicionEstado(transicion=estado2.transicion, estado=estado2),
        )

        pasos, tiempos = derivar_paisaje(replay, _POLITICA)

        assert pasos[0].estabilidad == 0  # primer eslabón: no hay "anterior" en este replay
        assert pasos[1].estabilidad == 1  # un asunto cambió: aparece el conflicto
        assert tiempos == {}  # el conflicto sigue abierto al final del replay


class TestConflictoQueSeResuelve:
    """`LearningState` construidos directamente (no vía reducer) — ver
    docstring del módulo: aísla `derivar_paisaje` de la mecánica real de
    supersesión de claims, fuera de alcance de esta pieza."""

    def test_tiempo_logico_de_estabilizacion_es_la_diferencia_de_transiciones(self) -> None:
        identidad = _identidad()
        fact = FactEntry(
            id=EntryId(1, 1),
            autor=Capacidad.EVALUAR,
            contenido={},
            provenance=Provenance.de(OrigenProvenance.INSTRUMENTO),
        )
        rival_a = ClaimEntry(
            id=EntryId(2, 1), autor=Capacidad.REMEDIAR, tipo=TipoClaim.PROPUESTA,
            asunto="siguiente-paso(sesion)", afirmacion={}, respaldo=(fact.id,),
            confianza=Decimal("0.6"), provenance=Provenance.de(OrigenProvenance.REGLA),
        )
        rival_b_vigente = ClaimEntry(
            id=EntryId(2, 2), autor=Capacidad.ORIENTAR, tipo=TipoClaim.PROPUESTA,
            asunto="siguiente-paso(sesion)", afirmacion={}, respaldo=(fact.id,),
            confianza=Decimal("0.6"), provenance=Provenance.de(OrigenProvenance.REGLA),
        )
        rival_b_superseded = ClaimEntry(
            id=rival_b_vigente.id, autor=rival_b_vigente.autor, tipo=rival_b_vigente.tipo,
            asunto=rival_b_vigente.asunto, afirmacion=rival_b_vigente.afirmacion,
            respaldo=rival_b_vigente.respaldo, confianza=rival_b_vigente.confianza,
            provenance=rival_b_vigente.provenance,
            vigencia=Vigencia(superseded_por=EntryId(5, 1)),
        )
        estado_t2 = LearningState(
            identidad=identidad, contexto={}, facts=(fact,),
            claims=(rival_a, rival_b_vigente), transicion=2,
        )
        estado_t5 = LearningState(
            identidad=identidad, contexto={}, facts=(fact,),
            claims=(rival_a, rival_b_superseded), transicion=5,
        )
        replay = (
            TransicionEstado(transicion=2, estado=estado_t2),
            TransicionEstado(transicion=5, estado=estado_t5),
        )

        pasos, tiempos = derivar_paisaje(replay, _POLITICA)

        assert pasos[0].paisaje.conflicto == {"siguiente-paso(sesion)": "bloqueante"}
        assert pasos[1].paisaje.conflicto == {}
        assert tiempos == {"siguiente-paso(sesion)": 3}
