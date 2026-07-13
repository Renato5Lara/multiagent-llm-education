"""RFC-0006/2, Parte B — detección y clasificación D1/D2
(RFC-0006 §3; CONCEPT-0002 §1; ROADMAP-RFC-0006 Parte B).

Sin Postgres, sin LangGraph: `LearningState` construido a mano contra
reducers puros, o mediante los productores reales cuando el escenario
existe de verdad en el walkthrough (mismo patrón que
`tests/runtime/deliberation/`).

Cubre las 3 tensiones canónicas de CONCEPT-0002 §1 ("Mapa de las
tensiones canónicas") + un cuarto caso de control que NO es tensión:

1. "¿avanzar o reforzar?" — D2 pura (Remediar vs Orientar, REAL — usa
   los productores reales, no una fixture inventada, porque esta
   tensión YA está viva en el walkthrough hoy; es la superficie de
   regresión real de esta mini-épica).
2. "¿qué modalidad?" — D2 (con raíz D1 a nivel pedagógico, pero
   clasificada D2 a nivel de código: son dos `PROPUESTA` rivales, no
   dos `INTERPRETACION`; hoy ningún productor real crea rivalidad en
   `modalidad(...)`, así que este caso se construye a mano, como
   demostración de que el mecanismo de clasificación es genérico, no
   atado a un asunto concreto).
3. "¿dominó el objetivo?" — D1 pura (dos `INTERPRETACION` rivales;
   construido a mano porque ningún productor real puede producirlo
   hoy — ver docstring de `mecanica.py`/la ficha RFC-0006/2, D1 es
   estructuralmente inalcanzable en el walkthrough actual).
4. Control: un único claim, ninguna rivalidad → `None`.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from runtime.domain.diagnosticar.productor import producir as producir_diagnostico
from runtime.domain.orientar.productor import producir as producir_orientacion
from runtime.domain.remediar.productor import producir as producir_remediacion
from runtime.kernel.deliberation.mecanica import (
    REGLA_POLITICA_V1,
    convocar,
    tension_bloqueante,
)
from runtime.kernel.reducers import Aplicado, registrar_claim, registrar_fact
from runtime.kernel.state.entries import (
    Capacidad,
    OrigenProvenance,
    Provenance,
    Resuelta,
    TipoClaim,
)
from runtime.kernel.state.state import Identidad, LearningState


def _identidad(session_id: str = "s-parteB") -> Identidad:
    return Identidad(
        session_id=session_id,
        student_id="maria",
        version_student_model="v7",
        version_banco="banco-v2",
        version_politica="v1",
        spec_version="foundation-2026-07-10",
    )


def _aplicar_claim(estado: LearningState, intent) -> LearningState:
    r = registrar_claim(estado, **intent.argumentos)
    assert isinstance(r, Aplicado)
    return r.estado


class TestTensionCanonica1_AvanzarOReforzar_D2Real:
    """"¿avanzar o reforzar?" — D2 pura (CONCEPT-0002 §1). Test de
    REGRESIÓN: usa los productores reales de Diagnosticar/Remediar/
    Orientar (no una fixture inventada) — esta tensión YA está viva hoy
    en `"siguiente-paso(sesion)"` (Remediar 0.82 vs Orientar 0.75); el
    refactor de `tension_bloqueante()` debe preservarla bit a bit."""

    def _estado_con_tension_real(self) -> LearningState:
        estado = LearningState(identidad=_identidad(), contexto={"ruta": "condicionales"})
        r = registrar_fact(
            estado,
            autor=Capacidad.EVALUAR,
            contenido={"competencia": "COMP-2", "items_incorrectos": [1, 2, 3]},
            provenance=Provenance.de(OrigenProvenance.INSTRUMENTO, banco="v2"),
        )
        assert isinstance(r, Aplicado)
        estado = r.estado

        (intent_diag,) = producir_diagnostico(estado)
        estado = _aplicar_claim(estado, intent_diag)

        (intent_remediar,) = producir_remediacion(estado)
        estado = _aplicar_claim(estado, intent_remediar)

        (intent_orientar,) = producir_orientacion(estado)
        estado = _aplicar_claim(estado, intent_orientar)
        return estado

    def test_se_detecta_como_D2(self):
        estado = self._estado_con_tension_real()
        tension = tension_bloqueante(estado)
        assert tension is not None
        tipo, asunto, participantes = tension
        assert tipo == "D2"
        assert asunto == "siguiente-paso(sesion)"
        assert len(participantes) == 2

    def test_convocar_resuelve_igual_que_antes_del_refactor(self):
        """Remediar declara 0.82 > Orientar 0.75 — Remediar gana por
        mayor-confianza-declarada. Este resultado es idéntico al que
        producía `tension_bloqueante()` antes de clasificar D1/D2: Parte
        B no cambia ni un bit de la resolución, solo la clasifica."""
        estado = self._estado_con_tension_real()
        intent = convocar(estado)
        assert intent is not None
        assert intent.operacion == "registrar_deliberacion"
        resultado = intent.argumentos["resultado"]
        assert isinstance(resultado, Resuelta)
        assert resultado.regla == REGLA_POLITICA_V1
        assert resultado.confianza == Decimal("0.82")
        ganador = estado.buscar(resultado.aceptados[0])
        assert ganador.autor is Capacidad.REMEDIAR
        assert ganador.afirmacion == {"accion": "reforzar"}


class TestTensionCanonica2_QueModalidad_D2ConRaizD1:
    """"¿qué modalidad?" — D2 con raíz D1 a nivel pedagógico
    (CONCEPT-0002 §1), pero clasificada D2 a nivel de código: dos
    `PROPUESTA` rivales sobre el mismo asunto de modalidad. Construido a
    mano — hoy ningún productor real genera rivalidad en
    `modalidad(...)` (solo Adaptar propone ahí, sin rival) — esto
    demuestra que la clasificación es genérica por `TipoClaim`, no
    atada a `"siguiente-paso(sesion)"`."""

    def test_se_detecta_como_D2(self):
        estado = LearningState(identidad=_identidad(), contexto={"ruta": "condicionales"})
        r = registrar_fact(
            estado,
            autor=Capacidad.EVALUAR,
            contenido={"competencia": "COMP-2", "items_incorrectos": []},
            provenance=Provenance.de(OrigenProvenance.INSTRUMENTO, banco="v2"),
        )
        assert isinstance(r, Aplicado)
        fact_id = r.estado.facts[0].id
        estado = r.estado

        for accion, confianza in (("video", Decimal("0.60")), ("texto", Decimal("0.65"))):
            r = registrar_claim(
                estado,
                autor=Capacidad.ADAPTAR,
                tipo=TipoClaim.PROPUESTA,
                asunto="modalidad(COMP-2)",
                afirmacion={"formato": accion},
                respaldo=(fact_id,),
                confianza=confianza,
                provenance=Provenance.de(OrigenProvenance.REGLA, id="modalidad-v1"),
            )
            assert isinstance(r, Aplicado)
            estado = r.estado

        tipo, asunto, participantes = tension_bloqueante(estado)
        assert tipo == "D2"
        assert asunto == "modalidad(COMP-2)"
        assert len(participantes) == 2


class TestTensionCanonica3_DominoElObjetivo_D1Pura:
    """"¿dominó el objetivo?" — D1 pura (CONCEPT-0002 §1): dos
    `INTERPRETACION` rivales sobre el mismo asunto. Construido a mano —
    ningún productor real puede generar esto hoy (ver docstring de
    `mecanica.py`): es la primera vez que el sistema puede siquiera
    RECONOCER esta forma de tensión, aunque nada la active todavía."""

    def test_se_detecta_como_D1(self):
        estado = LearningState(identidad=_identidad(), contexto={"ruta": "condicionales"})
        r = registrar_fact(
            estado,
            autor=Capacidad.EVALUAR,
            contenido={"competencia": "COMP-2", "items_incorrectos": [1]},
            provenance=Provenance.de(OrigenProvenance.INSTRUMENTO, banco="v2"),
        )
        assert isinstance(r, Aplicado)
        fact_id = r.estado.facts[0].id
        estado = r.estado

        for dominada, confianza in ((True, Decimal("0.55")), (False, Decimal("0.60"))):
            r = registrar_claim(
                estado,
                autor=Capacidad.DIAGNOSTICAR,
                tipo=TipoClaim.INTERPRETACION,
                asunto="dominio(COMP-2)",
                afirmacion={"dominada": dominada},
                respaldo=(fact_id,),
                confianza=confianza,
                provenance=Provenance.de(OrigenProvenance.REGLA, id="scoring-v1"),
            )
            assert isinstance(r, Aplicado)
            estado = r.estado

        tipo, asunto, participantes = tension_bloqueante(estado)
        assert tipo == "D1"
        assert asunto == "dominio(COMP-2)"
        assert len(participantes) == 2

    def test_D1_no_estaba_detectable_antes_de_esta_pieza(self):
        """Verificación estructural: antes de Parte B, `tension_bloqueante()`
        solo miraba `PROPUESTA` — dos `INTERPRETACION` rivales pasaban
        inadvertidas. Esta prueba fija que ahora sí se detectan (ver
        test anterior) y documenta el porqué, no solo el qué."""
        estado = LearningState(identidad=_identidad(), contexto={"ruta": "condicionales"})
        r = registrar_fact(
            estado,
            autor=Capacidad.EVALUAR,
            contenido={"competencia": "COMP-2", "items_incorrectos": [1]},
            provenance=Provenance.de(OrigenProvenance.INSTRUMENTO, banco="v2"),
        )
        assert isinstance(r, Aplicado)
        fact_id = r.estado.facts[0].id
        estado = r.estado
        r = registrar_claim(
            estado,
            autor=Capacidad.DIAGNOSTICAR,
            tipo=TipoClaim.INTERPRETACION,
            asunto="dominio(COMP-2)",
            afirmacion={"dominada": True},
            respaldo=(fact_id,),
            confianza=Decimal("0.55"),
            provenance=Provenance.de(OrigenProvenance.REGLA, id="scoring-v1"),
        )
        assert isinstance(r, Aplicado)
        estado = r.estado
        # un único claim: sin rivalidad, ninguna tensión de ningún tipo
        assert tension_bloqueante(estado) is None


class TestControl_SinRivalidad:
    """Cuarto caso — control: ninguna tensión, ningún claim en absoluto.
    No clasificar de más: `tension_bloqueante()` debe devolver `None`,
    no un falso D1 o D2."""

    def test_estado_vacio_no_es_tension(self):
        estado = LearningState(identidad=_identidad(), contexto={"ruta": "condicionales"})
        assert tension_bloqueante(estado) is None


class TestEnrutarNoCambia:
    """Criterio de cierre de la ficha: `enrutar()` / `walkthrough.py` no
    se modifica en esta mini-épica — verificación estructural."""

    def test_walkthrough_no_tiene_cambios_de_rama_para_D1_D2(self):
        import re
        from pathlib import Path

        fuente = (
            Path(__file__).resolve().parents[3]
            / "runtime"
            / "engine"
            / "graph"
            / "walkthrough.py"
        )
        texto = fuente.read_text(encoding="utf-8")
        # tension_bloqueante() sigue usándose solo como chequeo de
        # existencia — ninguna rama nueva que lea su tipo (D1/D2).
        assert '"D1"' not in texto
        assert '"D2"' not in texto
        assert "tension_bloqueante(estado) is not None" in texto
