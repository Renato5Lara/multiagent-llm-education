"""RFC-0007 §2.2, fila "Paisaje (H8 — ADOPTADA)" — `calcular_paisaje`.

Sin Postgres, sin LangGraph: `LearningState` construido a mano contra
reducers puros (mismo patrón que `tests/runtime/deliberation/`). Política
`"v1"` (pesos en cero, RFC-0006/1): `ce` == confianza declarada, así los
casos pueden fijar la entropía esperada sin depender de refuerzo/decaimiento.
"""

from __future__ import annotations

from decimal import Decimal
from math import isclose, log2

from runtime.engine.checkpoint.paisaje import Paisaje, calcular_paisaje
from runtime.kernel.deliberation.mecanica import convocar
from runtime.kernel.deliberation.politica import POLITICAS
from runtime.kernel.reducers import Aplicado, registrar_claim, registrar_deliberacion, registrar_fact
from runtime.kernel.state.entries import (
    Aplazada,
    Capacidad,
    OrigenProvenance,
    Provenance,
    TipoClaim,
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
