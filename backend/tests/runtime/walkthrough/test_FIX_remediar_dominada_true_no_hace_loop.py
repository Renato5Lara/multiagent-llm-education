"""Regresión (Épica 2) + fix real (RFC-0006/3): `enrutar()` entraba en
loop infinito cuando una interpretación de Diagnosticar decía
`dominada=True` — `remediar.producir()` no propone nada en ese caso, y
sin guardia el router volvía a enrutar a "remediar" indefinidamente
hasta el `recursion_limit` de LangGraph. Descubierto al conectar
`runtime_bridge` con evidencia real (<2 errores, el caso más común y
deseable).

El fix original (guardia de no-loop) resolvió el síntoma pero dejó un
bug real sin descubrir hasta el Engineering Gate de RFC-0006/3: sin
Remediar, Orientar propone SOLO en "siguiente-paso(sesion)" — sin
rival, `tension_bloqueante()`/`convocar()` nunca corren, ninguna
decisión se deriva, y como `Adaptar.producir()` exige una decisión
vigente para actuar, Adaptar NUNCA se activaba. Un estudiante que
respondía bien no llegaba a ninguna Entrega — el walkthrough terminaba
en `END` en silencio, sin error. `derivar_decision_directa()`
(mecanica.py, RFC-0006 §3 D3; RFC-0003 INV-6) corrige esto: la
propuesta única de Orientar deriva decisión directa (bajo θ), Adaptar
se activa, y hay Entrega real. Ver ROADMAP-RFC-0006.md, ficha
RFC-0006/3, para la auditoría completa.

Sin dobles (ADR-0005 §3): PostgreSQL real, LangGraph real.
"""

from __future__ import annotations

import os

import psycopg2
import pytest

from runtime.boundary.outbound.entregas import proyectar_entrega
from runtime.engine.checkpoint import AlmacenTransiciones
from runtime.engine.graph import ejecutar_walkthrough
from runtime.kernel.state import Capacidad, EstadoValidacion, OrigenProvenance, Provenance, TipoClaim
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
        version_politica="v1",
        spec_version="foundation-2026-07-10",
    )


def _hecho_dominado() -> tuple[TransitionIntent, ...]:
    """1 error: por debajo de `_UMBRAL_ERRORES = 2` (diagnosticar) —
    la interpretación resultante dirá `dominada=True`."""
    return (
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


@pytest.fixture
def esquema():
    nombre = f"runtime_fix_remediar_{os.getpid()}"
    yield nombre
    with psycopg2.connect(_URL) as conexion, conexion.cursor() as cursor:
        cursor.execute(f"DROP SCHEMA IF EXISTS {nombre} CASCADE")


def test_dominada_true_no_produce_recursion_error(esquema):
    almacen = AlmacenTransiciones(_URL, esquema=esquema)
    almacen.preparar()

    # Antes del fix: esto lanzaba GraphRecursionError.
    final = ejecutar_walkthrough(almacen, _identidad("s-dominada"), _hecho_dominado())
    estado = final["estado"]

    interpretacion = next(
        c for c in estado.claims if c.tipo is TipoClaim.INTERPRETACION
    )
    assert interpretacion.afirmacion["dominada"] is True

    # Remediar no tenía nada que proponer — no debe aparecer.
    assert not any(c.autor is Capacidad.REMEDIAR for c in estado.claims)

    # Orientar sí propone (su contrato no depende de dominada).
    orientacion = next(c for c in estado.claims if c.autor is Capacidad.ORIENTAR)
    assert orientacion.afirmacion["accion"] == "avanzar-con-andamiaje"

    # [RFC-0006/3, fix real] Antes de derivar_decision_directa(): sin
    # rival, ninguna decisión se derivaba nunca — el walkthrough
    # terminaba aquí, sin Adaptar, sin Entrega. Ahora sí:
    assert len(estado.decisiones) == 1, (
        "la propuesta única de Orientar debe derivar una decisión "
        "directa (RFC-0006 §3 D3 / RFC-0003 INV-6) — antes de este fix "
        "esto quedaba en 0, silenciosamente"
    )
    decision = estado.decisiones[0]
    assert decision.origen == orientacion.id
    assert decision.contenido["accion"] == "avanzar-con-andamiaje"
    assert decision.estado_validacion is EstadoValidacion.PENDIENTE_DE_VALIDACION

    # Adaptar se activa porque ya existe la decisión que necesita.
    adaptacion = next(
        (c for c in estado.claims if c.autor is Capacidad.ADAPTAR), None
    )
    assert adaptacion is not None, (
        "Adaptar.producir() itera estado.decisiones — sin la decisión "
        "derivada arriba, nunca se activaba"
    )
    assert decision.id in adaptacion.respaldo

    # La Entrega (S1, lo que el estudiante ve) deja de ser (None, None)
    # — antes indistinguible de "estudiante nuevo sin evidencia".
    entrega = proyectar_entrega(estado)
    assert entrega.asunto is not None
    assert entrega.diseno is not None


def test_dominada_false_preserva_el_comportamiento_original(esquema):
    # No-regresión: el camino ya probado (≥2 errores) sigue igual.
    almacen = AlmacenTransiciones(_URL, esquema=esquema)
    almacen.preparar()
    hecho = (
        TransitionIntent(
            productor=Capacidad.EVALUAR,
            operacion="registrar_fact",
            argumentos={
                "autor": Capacidad.EVALUAR,
                "contenido": {"competencia": "COMP-2", "items_incorrectos": [1, 2]},
                "provenance": Provenance.de(OrigenProvenance.INSTRUMENTO, banco="v2"),
            },
            base=0,
        ),
    )
    final = ejecutar_walkthrough(almacen, _identidad("s-no-dominada"), hecho)
    estado = final["estado"]
    interpretacion = next(
        c for c in estado.claims if c.tipo is TipoClaim.INTERPRETACION
    )
    assert interpretacion.afirmacion["dominada"] is False
    remediacion = next(c for c in estado.claims if c.autor is Capacidad.REMEDIAR)
    assert remediacion.afirmacion["accion"] == "reforzar"

    # [RFC-0006/3, no-regresión] Esta rama pasa por la tensión D2 real
    # (Remediar vs Orientar) — resuelta por convocar()/derivar_decision(),
    # nunca por derivar_decision_directa() (esta función solo actúa
    # sobre propuestas SIN rival). El resultado debe ser idéntico a
    # antes de RFC-0006/2 y RFC-0006/3: Remediar gana (0.82 > 0.75).
    assert len(estado.decisiones) == 1
    decision = estado.decisiones[0]
    assert decision.contenido["accion"] == "reforzar"
    # decision.origen apunta a la DELIBERACIÓN (no al claim de Remediar
    # directamente) — así ya funcionaba derivar_decision() antes de
    # RFC-0006/2/3, sin cambios: el origen es la deliberación resuelta,
    # y su resultado.aceptados[0] es el claim ganador.
    deliberacion = next(d for d in estado.deliberaciones if d.id == decision.origen)
    assert deliberacion.resultado.aceptados[0] == remediacion.id
    adaptacion = next(c for c in estado.claims if c.autor is Capacidad.ADAPTAR)
    assert decision.id in adaptacion.respaldo
    entrega = proyectar_entrega(estado)
    assert entrega.diseno["modalidad"] == "visual"  # DISENO_POR_ACCION["reforzar"]
