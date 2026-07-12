"""M4 PR-1A — reconstrucción de LearningState desde el log de
transiciones (RFC-0008 §3, modo "reconstrucción"; R3 Exactitud, R4
Suficiencia; P10).

`RegistroTransicion.canonico` persiste `{intent, eventos}` por
transición, nunca una foto del `LearningState` (ver
`engine/graph/walkthrough.py::aplicar`). Esta suite demuestra que
`reconstruir()` recupera el MISMO `LearningState`, transición por
transición, a través de `kernel.reducers` puros — sin invocar ningún
productor ni proveedor LLM (ADR-0007).

Ejercita las 5 operaciones que hoy producen `TransitionIntent`:
registrar_fact, registrar_claim, registrar_deliberacion,
registrar_decision, validar_decision — para que el codec
(`desde_canonico`) se pruebe contra los 5 contratos de argumentos
reales, no contra una única forma simplificada.

Sin dobles (ADR-0005 §3): PostgreSQL real, esquema temporal por corrida.
"""

from __future__ import annotations

import dataclasses
import os
from decimal import Decimal

import psycopg2
import pytest

from runtime.engine.checkpoint import (
    AlmacenTransiciones,
    RegistroTransicion,
    encadenar,
    reconstruir,
    verificar,
)
from runtime.kernel.reducers import (
    Aplicado,
    registrar_claim,
    registrar_decision,
    registrar_deliberacion,
    registrar_fact,
    validar_decision,
)
from runtime.kernel.state.entries import (
    Capacidad,
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
    "registrar_decision": registrar_decision,
    "validar_decision": validar_decision,
}


def _pg_disponible() -> bool:
    try:
        psycopg2.connect(_URL, connect_timeout=3).close()
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _pg_disponible(), reason="PostgreSQL no disponible (R3 exige BD real)"
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


@pytest.fixture
def almacen():
    esquema = f"runtime_test_{os.getpid()}"
    almacen = AlmacenTransiciones(_URL, esquema=esquema)
    almacen.preparar()
    yield almacen
    with psycopg2.connect(_URL) as conexion, conexion.cursor() as cursor:
        cursor.execute(f"DROP SCHEMA {esquema} CASCADE")


def _aplicar_y_persistir(
    almacen, identidad, estado, registros, intent: TransitionIntent
):
    """Mismo patrón que `aplicar()` en engine/graph/walkthrough.py:
    reducir → encadenar → persistir, por transición."""
    resultado = _OPERACIONES[intent.operacion](estado, **intent.argumentos)
    assert isinstance(resultado, Aplicado)
    registro = encadenar(
        identidad, registros, {"intent": intent, "eventos": resultado.eventos}
    )
    almacen.persistir(registro)
    return resultado.estado, registros + (registro,)


def _construir_historia(almacen, identidad):
    """Fact → interpretación → tensión (dos propuestas) → deliberación
    → decisión → fact posterior → validación — las 5 operaciones,
    8 transiciones."""
    almacen.abrir_sesion(identidad)
    estado = LearningState(identidad=identidad, contexto={"ruta": "condicionales"})
    registros: tuple[RegistroTransicion, ...] = ()

    estado, registros = _aplicar_y_persistir(
        almacen,
        identidad,
        estado,
        registros,
        TransitionIntent(
            productor=Capacidad.EVALUAR,
            operacion="registrar_fact",
            argumentos={
                "autor": Capacidad.EVALUAR,
                "contenido": {"competencia": "COMP-2", "items_incorrectos": [3, 4, 8]},
                "provenance": Provenance.de(OrigenProvenance.INSTRUMENTO, banco="v2"),
            },
            base=0,
        ),
    )
    fact_evaluar_id = estado.facts[0].id

    estado, registros = _aplicar_y_persistir(
        almacen,
        identidad,
        estado,
        registros,
        TransitionIntent(
            productor=Capacidad.DIAGNOSTICAR,
            operacion="registrar_claim",
            argumentos={
                "autor": Capacidad.DIAGNOSTICAR,
                "tipo": TipoClaim.INTERPRETACION,
                "asunto": "dominio(COMP-2)",
                "afirmacion": {"dominada": False, "errores": 3},
                "respaldo": (fact_evaluar_id,),
                "confianza": Decimal("0.78"),
                "provenance": Provenance.de(OrigenProvenance.REGLA, id="scoring-v1"),
            },
            base=estado.transicion,
        ),
    )
    interpretacion_id = estado.claims[0].id

    estado, registros = _aplicar_y_persistir(
        almacen,
        identidad,
        estado,
        registros,
        TransitionIntent(
            productor=Capacidad.REMEDIAR,
            operacion="registrar_claim",
            argumentos={
                "autor": Capacidad.REMEDIAR,
                "tipo": TipoClaim.PROPUESTA,
                "asunto": "siguiente-paso(sesion)",
                "afirmacion": {"accion": "reforzar"},
                "respaldo": (interpretacion_id,),
                "confianza": Decimal("0.82"),
                "provenance": Provenance.de(OrigenProvenance.REGLA, id="remediacion-v1"),
            },
            base=estado.transicion,
        ),
    )
    remediar_id = estado.claims[-1].id

    estado, registros = _aplicar_y_persistir(
        almacen,
        identidad,
        estado,
        registros,
        TransitionIntent(
            productor=Capacidad.ORIENTAR,
            operacion="registrar_claim",
            argumentos={
                "autor": Capacidad.ORIENTAR,
                "tipo": TipoClaim.PROPUESTA,
                "asunto": "siguiente-paso(sesion)",
                "afirmacion": {"accion": "avanzar-con-andamiaje"},
                "respaldo": (interpretacion_id,),
                "confianza": Decimal("0.65"),
                "provenance": Provenance.de(OrigenProvenance.REGLA, id="orientacion-v1"),
            },
            base=estado.transicion,
        ),
    )
    orientar_id = estado.claims[-1].id

    estado, registros = _aplicar_y_persistir(
        almacen,
        identidad,
        estado,
        registros,
        TransitionIntent(
            productor="kernel",
            operacion="registrar_deliberacion",
            argumentos={
                "participantes": (remediar_id, orientar_id),
                "resultado": Resuelta(
                    regla="mayor-confianza-declarada",
                    aceptados=(remediar_id,),
                    confianza=Decimal("0.82"),
                ),
            },
            base=estado.transicion,
        ),
    )
    deliberacion_id = estado.deliberaciones[0].id

    estado, registros = _aplicar_y_persistir(
        almacen,
        identidad,
        estado,
        registros,
        TransitionIntent(
            productor="kernel",
            operacion="registrar_decision",
            argumentos={
                "origen": deliberacion_id,
                "contenido": {"accion": "reforzar"},
            },
            base=estado.transicion,
        ),
    )
    decision_id = estado.decisiones[0].id

    estado, registros = _aplicar_y_persistir(
        almacen,
        identidad,
        estado,
        registros,
        TransitionIntent(
            productor=Capacidad.EVALUAR,
            operacion="registrar_fact",
            argumentos={
                "autor": Capacidad.EVALUAR,
                "contenido": {"competencia": "COMP-2", "items_incorrectos": [3]},
                "provenance": Provenance.de(OrigenProvenance.INSTRUMENTO, banco="v2"),
            },
            base=estado.transicion,
        ),
    )
    fact_posterior_id = estado.facts[-1].id

    estado, registros = _aplicar_y_persistir(
        almacen,
        identidad,
        estado,
        registros,
        TransitionIntent(
            productor=Capacidad.VALIDAR,
            operacion="validar_decision",
            argumentos={
                "decision_id": decision_id,
                "autor": Capacidad.VALIDAR,
                "asunto": f"efecto({decision_id})",
                "afirmacion": {"competencia": "COMP-2", "funciono": True},
                "respaldo": (decision_id, fact_posterior_id),
                "confianza": Decimal("0.80"),
                "provenance": Provenance.de(OrigenProvenance.REGLA, id="validacion-v1"),
            },
            base=estado.transicion,
        ),
    )
    return estado, registros


class TestR3_ReconstruccionLearningState:
    def test_reconstruir_produce_el_mismo_estado(self, almacen):
        identidad = _identidad("s-m4-pr1a-r3")
        estado_original, registros = _construir_historia(almacen, identidad)

        leidos = almacen.leer(identidad.session_id)
        assert leidos == registros  # R3, ya cubierto por R1-R6: lo leído == lo persistido

        estado_reconstruido = reconstruir(
            identidad, contexto={"ruta": "condicionales"}, registros=leidos
        )

        assert estado_reconstruido == estado_original
        assert estado_reconstruido.transicion == 8
        assert verificar(identidad, leidos) is None

    def test_reconstruccion_jamas_importa_domain(self):
        """ADR-0007: la reconstrucción nunca reinvoca un productor ni un
        proveedor LLM — verificación estructural, mismo patrón que
        `test_BLUEPRINT_reglas_de_importacion.py`: si el módulo de
        reconstrucción importara cualquier `runtime.domain.*` (las 8
        capacidades), sería la señal de que empezó a decidir en vez de
        solo reproducir reducers ya aplicados."""
        import re
        from pathlib import Path

        fuente = Path(
            __file__
        ).resolve().parents[3] / "runtime" / "engine" / "checkpoint" / "reconstruccion.py"
        texto = fuente.read_text(encoding="utf-8")
        assert not re.search(r"^\s*(import|from)\s+runtime\.domain(\.|\s)", texto, re.M), (
            "reconstruccion.py importa runtime.domain — violaría ADR-0007: "
            "la reconstrucción no debe poder invocar un productor"
        )

    def test_transicion_persistida_alterada_rompe_la_reconstruccion(self, almacen):
        """R3: si el canónico persistido fuera distinto de lo que el
        reducer vuelve a producir, reconstruir() debe abortar ruidosamente
        (ADR-0004 E-2), nunca reconstruir en silencio un estado falso."""
        identidad = _identidad("s-m4-pr1a-alterado")
        _, registros = _construir_historia(almacen, identidad)
        leidos = almacen.leer(identidad.session_id)

        alterado = dataclasses.replace(leidos[1], canonico=leidos[0].canonico)
        manipulados = (leidos[0], alterado) + leidos[2:]

        with pytest.raises(RuntimeError):
            reconstruir(
                identidad, contexto={"ruta": "condicionales"}, registros=manipulados
            )
