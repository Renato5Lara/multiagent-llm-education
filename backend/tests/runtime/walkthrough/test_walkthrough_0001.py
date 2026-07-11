"""La quinta suite (ADR-0005 §1): el Walkthrough-0001 como test de
integración canónico — la historia de María sobre código real.

Sin dobles: PostgreSQL real, LangGraph real, capacidades regla reales.
"""

import os
from decimal import Decimal

import psycopg2
import pytest

from runtime.engine.checkpoint import AlmacenTransiciones, verificar
from runtime.engine.graph import ejecutar_walkthrough
from runtime.kernel.deliberation.mecanica import REGLA_POLITICA_V1
from runtime.kernel.state import (
    Capacidad,
    EntryId,
    EstadoValidacion,
    OrigenProvenance,
    Provenance,
    Resuelta,
    TipoClaim,
)
from runtime.kernel.state.state import Identidad
from runtime.kernel.transitions import TransitionIntent

_URL = os.environ.get(
    "RUNTIME_TEST_DATABASE_URL",
    "postgresql://upao_user:upao_pass@localhost:5432/upao_mas_edu",
)


def _pg_disponible() -> bool:
    try:
        psycopg2.connect(_URL, connect_timeout=3).close()
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _pg_disponible(), reason="PostgreSQL no disponible"
)


def _identidad(session_id: str) -> Identidad:
    return Identidad(
        session_id=session_id,
        student_id="maria",
        version_student_model="v7",
        version_banco="banco-v2",
        version_politica="politica-v1",
        spec_version="foundation-2026-07-10",
    )


def _hecho_del_mundo() -> tuple[TransitionIntent, ...]:
    """T1 del walkthrough: los resultados de la actividad diagnóstica."""
    return (
        TransitionIntent(
            productor=Capacidad.EVALUAR,
            operacion="registrar_fact",
            argumentos={
                "autor": Capacidad.EVALUAR,
                "contenido": {
                    "competencia": "COMP-2",
                    "items_incorrectos": [3, 4, 8],
                },
                "provenance": Provenance.de(
                    OrigenProvenance.INSTRUMENTO, banco="v2"
                ),
            },
            base=0,
        ),
    )


def _correr(session_id: str, esquema: str):
    almacen = AlmacenTransiciones(_URL, esquema=esquema)
    almacen.preparar()
    final = ejecutar_walkthrough(almacen, _identidad(session_id), _hecho_del_mundo())
    return almacen, final


@pytest.fixture
def esquema():
    nombre = f"runtime_wt_{os.getpid()}"
    yield nombre
    with psycopg2.connect(_URL) as conexion, conexion.cursor() as cursor:
        cursor.execute(f"DROP SCHEMA IF EXISTS {nombre} CASCADE")


@pytest.fixture
def esquema_b():
    nombre = f"runtime_wt_b_{os.getpid()}"
    yield nombre
    with psycopg2.connect(_URL) as conexion, conexion.cursor() as cursor:
        cursor.execute(f"DROP SCHEMA IF EXISTS {nombre} CASCADE")


class TestWalkthrough0001:
    def test_la_historia_de_maria_corre_de_punta_a_punta(self, esquema):
        _, final = _correr("s-maria", esquema)
        estado = final["estado"]

        # Capturar → Interpretar: Diagnosticar leyó el hecho del mundo.
        interpretacion = next(
            c for c in estado.claims if c.tipo is TipoClaim.INTERPRETACION
        )
        assert interpretacion.autor is Capacidad.DIAGNOSTICAR
        assert interpretacion.afirmacion["dominada"] is False

        # La tensión canónica n.º 1 existió y se deliberó (P8: hubo
        # desacuerdo real — reforzar vs avanzar, mismo asunto).
        deliberacion = estado.deliberaciones[0]
        assert len(deliberacion.participantes) == 2
        assert isinstance(deliberacion.resultado, Resuelta)
        assert deliberacion.resultado.regla == REGLA_POLITICA_V1

        # El rival quedó supersedido POR el episodio, no por el ganador.
        propuestas = [c for c in estado.claims if c.tipo is TipoClaim.PROPUESTA]
        rival = next(c for c in propuestas if not c.vigencia.vigente)
        assert rival.autor is Capacidad.ORIENTAR
        assert rival.vigencia.superseded_por == deliberacion.id

        # La decisión deriva del episodio y hereda SU confianza (INV-6/7).
        decision = estado.decisiones[0]
        assert decision.origen == deliberacion.id
        assert decision.asunto == "siguiente-paso(sesion)"
        assert decision.contenido["accion"] == "reforzar"
        assert decision.confianza == Decimal("0.82")
        assert decision.estado_validacion is EstadoValidacion.PENDIENTE_DE_VALIDACION

    def test_INV_10_toda_mutacion_paso_por_reducer_y_quedo_persistida(
        self, esquema
    ):
        almacen, final = _correr("s-inv10", esquema)
        estado, registros = final["estado"], final["registros"]
        # Una transición aplicada = un registro persistido; ni una más.
        assert len(registros) == estado.transicion == 6
        # Lo persistido es lo ejecutado, íntegro (P14, R3).
        assert almacen.leer("s-inv10") == registros
        assert verificar(_identidad("s-inv10"), registros) is None

    def test_P12_dos_ejecuciones_producen_hashes_identicos(
        self, esquema, esquema_b
    ):
        # Criterio 5 del tesista: el replay del walkthrough reproduce la
        # misma secuencia de transiciones, hashes, deliberaciones y
        # decisiones que la ejecución original.
        _, primera = _correr("s-replay", esquema)
        _, segunda = _correr("s-replay", esquema_b)
        assert [r.hash for r in primera["registros"]] == [
            r.hash for r in segunda["registros"]
        ]
        assert primera["registros"] == segunda["registros"]

    def test_ADR_0006_el_estado_sembrado_no_fue_mutado(self, esquema):
        # Regla 8: los nodos leyeron estados inmutables; cada versión
        # previa sigue intacta — la inicial, la primera.
        _, final = _correr("s-regla8", esquema)
        estado = final["estado"]
        # La historia por versiones: el fact original sigue vigente y la
        # interpretación conserva su respaldo navegable hasta él (P6).
        fact = estado.facts[0]
        assert fact.vigencia.vigente
        interpretacion = next(
            c for c in estado.claims if c.tipo is TipoClaim.INTERPRETACION
        )
        assert fact.id in interpretacion.respaldo


class TestValidarIntegradoAlFlujo:
    """PR-2: Validar deja de ser una capacidad huérfana del grafo.

    El estado inicial se siembra con la evidencia completa YA presente
    (decisión + fact posterior de Evaluar) en un único lote de
    `hechos_del_mundo` — los ids son predecibles porque cada reducer
    asigna `EntryId(transicion=indice, entrada=1)` en el orden en que
    `aplicar` procesa el lote (ver reducers/*.py). Esto prueba el
    contrato de enrutamiento (`enrutar` → "validar" cuando ya hay
    evidencia), no un mecanismo de reanudación de sesión — eso pertenece
    a P10/RFC-0008 y queda fuera de este PR."""

    @staticmethod
    def _hechos_con_evidencia_completa() -> tuple[TransitionIntent, ...]:
        fact_antes_id = EntryId(transicion=1, entrada=1)
        claim_diagnostico_id = EntryId(transicion=2, entrada=1)
        claim_remediar_id = EntryId(transicion=3, entrada=1)
        decision_id = EntryId(transicion=4, entrada=1)
        return (
            TransitionIntent(
                productor=Capacidad.EVALUAR,
                operacion="registrar_fact",
                argumentos={
                    "autor": Capacidad.EVALUAR,
                    "contenido": {
                        "competencia": "COMP-2",
                        "items_incorrectos": [3, 4, 8],
                    },
                    "provenance": Provenance.de(
                        OrigenProvenance.INSTRUMENTO, banco="v2"
                    ),
                },
                base=0,
            ),
            TransitionIntent(
                productor=Capacidad.DIAGNOSTICAR,
                operacion="registrar_claim",
                argumentos={
                    "autor": Capacidad.DIAGNOSTICAR,
                    "tipo": TipoClaim.INTERPRETACION,
                    "asunto": "dominio(COMP-2)",
                    "afirmacion": {"dominada": False, "errores": 3},
                    "respaldo": (fact_antes_id,),
                    "confianza": Decimal("0.78"),
                    "provenance": Provenance.de(
                        OrigenProvenance.REGLA, id="scoring-v1"
                    ),
                },
                base=1,
            ),
            TransitionIntent(
                productor=Capacidad.REMEDIAR,
                operacion="registrar_claim",
                argumentos={
                    "autor": Capacidad.REMEDIAR,
                    "tipo": TipoClaim.PROPUESTA,
                    "asunto": "siguiente-paso(sesion)",
                    "afirmacion": {"accion": "reforzar"},
                    "respaldo": (claim_diagnostico_id,),
                    "confianza": Decimal("0.82"),
                    "provenance": Provenance.de(
                        OrigenProvenance.REGLA, id="remediacion-v1"
                    ),
                },
                base=2,
            ),
            TransitionIntent(
                productor=Capacidad.REMEDIAR,
                operacion="registrar_decision",
                argumentos={
                    "origen": claim_remediar_id,
                    "contenido": {"accion": "reforzar"},
                },
                base=3,
            ),
            TransitionIntent(
                productor=Capacidad.EVALUAR,
                operacion="registrar_fact",
                argumentos={
                    "autor": Capacidad.EVALUAR,
                    "contenido": {
                        "competencia": "COMP-2",
                        "items_incorrectos": [3],
                    },
                    "provenance": Provenance.de(
                        OrigenProvenance.INSTRUMENTO, banco="v2"
                    ),
                },
                base=4,
            ),
        ), decision_id

    def test_validar_se_ejecuta_cuando_ya_existe_evidencia_posterior(self, esquema):
        almacen = AlmacenTransiciones(_URL, esquema=esquema)
        almacen.preparar()
        hechos, decision_id = self._hechos_con_evidencia_completa()
        final = ejecutar_walkthrough(almacen, _identidad("s-validar-integrado"), hechos)
        estado = final["estado"]

        veredicto = next(
            c
            for c in estado.claims
            if c.autor is Capacidad.VALIDAR and c.vigencia.vigente
        )
        assert veredicto.asunto == f"efecto({decision_id})"
        assert decision_id in veredicto.respaldo
        assert veredicto.afirmacion["funciono"] is True

        decision = estado.buscar(decision_id)
        assert decision.estado_validacion is EstadoValidacion.VALIDADA

        # PR-3: Modelar no necesita evidencia externa — su disparador es
        # el propio veredicto de Validar, ya presente en esta misma
        # invocación — así que se ejecuta a continuación sin intervención.
        modelado = next(
            c for c in estado.claims if c.autor is Capacidad.MODELAR and c.vigencia.vigente
        )
        assert veredicto.id in modelado.respaldo
        assert modelado.afirmacion["competencia"] == "COMP-2"
        assert modelado.afirmacion["efecto_positivo"] is True

        # El recorrido creció en dos transiciones exactas (Validar +
        # Modelar, PR-2 y PR-3): 5 hechos sembrados + veredicto + modelado.
        assert estado.transicion == 7
        assert len(final["registros"]) == 7

    def test_sin_evidencia_posterior_el_recorrido_termina_igual_que_antes(
        self, esquema
    ):
        # Guardia segura: con solo el hecho inicial (sin "después"), el
        # walkthrough debe seguir terminando en la primera decisión — el
        # mismo comportamiento que tenía antes de PR-2 (transicion == 6
        # por el camino Diagnosticar→Remediar/Orientar→Deliberar→Decidir).
        almacen = AlmacenTransiciones(_URL, esquema=esquema)
        almacen.preparar()
        final = ejecutar_walkthrough(
            almacen, _identidad("s-validar-sin-evidencia"), _hecho_del_mundo()
        )
        estado = final["estado"]
        assert not any(c.autor is Capacidad.VALIDAR for c in estado.claims)
        assert estado.transicion == 6
