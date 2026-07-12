"""E3 — `resolver_escalada`: la autoridad humana cierra una deliberación
escalada (RFC-0009 §2.1, §3; RFC-0010 §1, fila E3 "resoluciones de
escalada del docente").

La escalada NO se produce orgánicamente todavía (Plataforma Operativa 4,
alcance aprobado: el disparador real de RFC-0006 §4 — θ/δ, límite de
reconvocatoria — es una épica posterior). Se construye aquí directamente
contra los reducers, la misma técnica ya usada en toda la suite de
boundary/reconstrucción — real, no un mock de dominio: Postgres real,
LangGraph real al resolver.

Sin dobles (ADR-0005 §3): PostgreSQL real, LangGraph real.
"""

from __future__ import annotations

import os
from decimal import Decimal

import psycopg2
import pytest

from runtime.boundary.inbound.escalada import resolver_escalada
from runtime.engine.checkpoint import AlmacenMemoria, AlmacenTransiciones, encadenar
from runtime.kernel.reducers import Aplicado, registrar_claim, registrar_deliberacion, registrar_fact
from runtime.kernel.state.entries import (
    Capacidad,
    DeliberacionEntry,
    Escalada,
    OrigenProvenance,
    Provenance,
    Resuelta,
    TipoClaim,
)
from runtime.kernel.state.state import Identidad, LearningState
from runtime.kernel.transitions import TransitionIntent

_URL = os.environ.get(
    "RUNTIME_TEST_DATABASE_URL",
    "postgresql://upao_user:upao_pass@localhost:5432/upao_mas_edu",
)

_OPERACIONES = {
    "registrar_fact": registrar_fact,
    "registrar_claim": registrar_claim,
    "registrar_deliberacion": registrar_deliberacion,
}


def _pg_disponible() -> bool:
    try:
        psycopg2.connect(_URL, connect_timeout=3).close()
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _pg_disponible(), reason="PostgreSQL no disponible (ADR-0005 §3 exige BD real)"
)


def _identidad(session_id: str) -> Identidad:
    return Identidad(
        session_id=session_id,
        student_id="maria",
        version_student_model="0",
        version_banco="banco-v2",
        version_politica="politica-v1",
        spec_version="foundation-2026-07-10",
    )


@pytest.fixture
def esquema():
    nombre = f"runtime_e3_escalada_test_{os.getpid()}"
    yield nombre
    with psycopg2.connect(_URL) as conexion, conexion.cursor() as cursor:
        cursor.execute(f"DROP SCHEMA IF EXISTS {nombre} CASCADE")


@pytest.fixture
def almacen(esquema):
    almacen = AlmacenTransiciones(_URL, esquema=esquema)
    almacen.preparar()
    return almacen


@pytest.fixture
def almacen_memoria(esquema):
    almacen_memoria = AlmacenMemoria(_URL, esquema=esquema)
    almacen_memoria.preparar()
    return almacen_memoria


def _aplicar_y_persistir(almacen, identidad, estado, registros, intent):
    resultado = _OPERACIONES[intent.operacion](estado, **intent.argumentos)
    assert isinstance(resultado, Aplicado)
    registro = encadenar(
        identidad, registros, {"intent": intent, "eventos": resultado.eventos}
    )
    almacen.persistir(registro)
    return resultado.estado, registros + (registro,)


def _sembrar_escalada(almacen, identidad):
    """Fact → interpretación → dos propuestas en tensión sobre el mismo
    asunto → deliberación ESCALADA (construida directamente, no por
    mecanica.py — ver docstring del módulo). La interpretación es
    obligatoria: domain/shared/causal.py recorre decisión → propuesta →
    interpretación → fact (tres saltos, no dos) para resolver la
    competencia que Adaptar necesita — sin ella, Adaptar nunca produce
    su claim y el walkthrough real gira en el nodo "adaptar" para
    siempre (GraphRecursionError observado al omitir este salto)."""
    almacen.abrir_sesion(identidad)
    estado = LearningState(identidad=identidad, contexto={"ruta": "condicionales"})
    registros = ()

    estado, registros = _aplicar_y_persistir(
        almacen, identidad, estado, registros,
        TransitionIntent(
            productor=Capacidad.EVALUAR,
            operacion="registrar_fact",
            argumentos={
                "autor": Capacidad.EVALUAR,
                "contenido": {"competencia": "COMP-2", "items_incorrectos": [3]},
                "provenance": Provenance.de(OrigenProvenance.INSTRUMENTO, banco="v2"),
            },
            base=0,
        ),
    )
    fact_id = estado.facts[0].id

    estado, registros = _aplicar_y_persistir(
        almacen, identidad, estado, registros,
        TransitionIntent(
            productor=Capacidad.DIAGNOSTICAR,
            operacion="registrar_claim",
            argumentos={
                "autor": Capacidad.DIAGNOSTICAR,
                "tipo": TipoClaim.INTERPRETACION,
                "asunto": "dominio(COMP-2)",
                "afirmacion": {"dominada": False, "errores": 1},
                "respaldo": (fact_id,),
                "confianza": Decimal("0.75"),
                "provenance": Provenance.de(OrigenProvenance.REGLA, id="scoring-v1"),
            },
            base=estado.transicion,
        ),
    )
    interpretacion_id = estado.claims[-1].id

    estado, registros = _aplicar_y_persistir(
        almacen, identidad, estado, registros,
        TransitionIntent(
            productor=Capacidad.REMEDIAR,
            operacion="registrar_claim",
            argumentos={
                "autor": Capacidad.REMEDIAR,
                "tipo": TipoClaim.PROPUESTA,
                "asunto": "siguiente-paso(sesion)",
                "afirmacion": {"accion": "reforzar"},
                "respaldo": (interpretacion_id,),
                "confianza": Decimal("0.60"),
                "provenance": Provenance.de(OrigenProvenance.REGLA, id="remediacion-v1"),
            },
            base=estado.transicion,
        ),
    )
    remediar_id = estado.claims[-1].id

    estado, registros = _aplicar_y_persistir(
        almacen, identidad, estado, registros,
        TransitionIntent(
            productor=Capacidad.ORIENTAR,
            operacion="registrar_claim",
            argumentos={
                "autor": Capacidad.ORIENTAR,
                "tipo": TipoClaim.PROPUESTA,
                "asunto": "siguiente-paso(sesion)",
                "afirmacion": {"accion": "avanzar-con-andamiaje"},
                "respaldo": (interpretacion_id,),
                "confianza": Decimal("0.58"),
                "provenance": Provenance.de(OrigenProvenance.REGLA, id="orientacion-v1"),
            },
            base=estado.transicion,
        ),
    )
    orientar_id = estado.claims[-1].id

    estado, registros = _aplicar_y_persistir(
        almacen, identidad, estado, registros,
        TransitionIntent(
            productor="kernel",
            operacion="registrar_deliberacion",
            argumentos={
                "participantes": (remediar_id, orientar_id),
                "resultado": Escalada(destinatario="docente"),
            },
            base=estado.transicion,
        ),
    )
    escalada_id = estado.deliberaciones[-1].id
    return escalada_id, remediar_id, orientar_id


class TestE3_ResolverEscalada:
    def test_resuelve_la_escalada_y_el_runtime_continua(self, almacen, almacen_memoria):
        identidad = _identidad("s-e3-resolver")
        escalada_id, remediar_id, _orientar_id = _sembrar_escalada(almacen, identidad)

        resolver_escalada(
            identidad,
            escalada_id=escalada_id,
            claim_elegido=remediar_id,
            human_reason="el estudiante ya mostró fatiga con el andamiaje",
            almacen=almacen,
            almacen_memoria=almacen_memoria,
        )

        registros = almacen.leer(identidad.session_id)
        from runtime.engine.checkpoint import reconstruir

        estado_final = reconstruir(
            identidad, contexto={"ruta": "condicionales"}, registros=registros
        )

        # El fact humano quedó registrado.
        facts_humanos = [
            f for f in estado_final.facts
            if f.provenance.origen == OrigenProvenance.HUMANO
        ]
        assert len(facts_humanos) == 1
        assert facts_humanos[0].contenido["human_reason"] == (
            "el estudiante ya mostró fatiga con el andamiaje"
        )

        # La deliberación de cierre quedó enlazada, con la regla explícita.
        cierre = next(
            d for d in estado_final.deliberaciones if d.enlaza_a == escalada_id
        )
        assert isinstance(cierre.resultado, Resuelta)
        assert cierre.resultado.regla == "decision-humana"
        assert cierre.resultado.aceptados == (remediar_id,)

        # El runtime continuó solo: derivó la decisión sin intervención
        # adicional (RFC-0009: "el sistema no finge que decidió solo",
        # pero tampoco se detiene más de lo necesario).
        assert any(d.origen == cierre.id for d in estado_final.decisiones)

    def test_rechaza_claim_que_no_es_participante(self, almacen, almacen_memoria):
        identidad = _identidad("s-e3-claim-ajeno")
        escalada_id, _remediar_id, _orientar_id = _sembrar_escalada(almacen, identidad)
        from runtime.kernel.state.entries import EntryId

        with pytest.raises(ValueError, match="P15"):
            resolver_escalada(
                identidad,
                escalada_id=escalada_id,
                claim_elegido=EntryId(transicion=999, entrada=1),
                human_reason=None,
                almacen=almacen,
                almacen_memoria=almacen_memoria,
            )

    def test_rechaza_escalada_ya_resuelta(self, almacen, almacen_memoria):
        identidad = _identidad("s-e3-doble-resolucion")
        escalada_id, remediar_id, _orientar_id = _sembrar_escalada(almacen, identidad)

        resolver_escalada(
            identidad, escalada_id=escalada_id, claim_elegido=remediar_id,
            human_reason=None, almacen=almacen, almacen_memoria=almacen_memoria,
        )

        with pytest.raises(ValueError, match="ya fue resuelta"):
            resolver_escalada(
                identidad, escalada_id=escalada_id, claim_elegido=remediar_id,
                human_reason=None, almacen=almacen, almacen_memoria=almacen_memoria,
            )

    def test_rechaza_id_que_no_es_escalada(self, almacen, almacen_memoria):
        identidad = _identidad("s-e3-no-escalada")
        _escalada_id, remediar_id, _orientar_id = _sembrar_escalada(almacen, identidad)

        with pytest.raises(ValueError, match="no es una deliberación escalada"):
            resolver_escalada(
                identidad, escalada_id=remediar_id, claim_elegido=remediar_id,
                human_reason=None, almacen=almacen, almacen_memoria=almacen_memoria,
            )
