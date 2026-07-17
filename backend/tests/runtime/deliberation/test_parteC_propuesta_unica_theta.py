"""RFC-0006/3, Parte C — propuesta única deriva decisión directa bajo
el umbral θ (RFC-0006 §3, D3; RFC-0003 INV-6; ROADMAP-RFC-0006 Parte C).

`derivar_decision_directa()` corrige un bug preexistente (no una
capacidad nueva desde cero): una propuesta sin rival nunca derivaba
decisión, porque `derivar_decision()` solo lee deliberaciones resueltas.
El caso real es `"siguiente-paso(sesion)"` cuando `dominada=True` —
Orientar propone solo, el walkthrough terminaba en `END` sin decisión.
La cobertura E2E real de ESE caso (Postgres + LangGraph reales) vive en
`tests/runtime/walkthrough/test_FIX_remediar_dominada_true_no_hace_loop.py`
(extendida en esta mini-épica) — aquí se prueba la función pura, sin
LangGraph, sin productores.
"""

from __future__ import annotations

from decimal import Decimal

from runtime.kernel.deliberation.mecanica import derivar_decision_directa
from runtime.kernel.deliberation.politica import POLITICAS, Politica
from runtime.kernel.reducers import Aplicado, registrar_claim, registrar_decision, registrar_fact
from runtime.kernel.state.entries import Capacidad, OrigenProvenance, Provenance, TipoClaim
from runtime.kernel.state.state import Identidad, LearningState

_V1 = POLITICAS["v1"]
_POLITICA_THETA_ALTO = Politica(
    peso_refuerzo=Decimal("0"),
    peso_refutacion=Decimal("0"),
    peso_decaimiento=Decimal("0"),
    theta=Decimal("0.70"),
)


def _identidad(session_id: str = "s-parteC") -> Identidad:
    return Identidad(
        session_id=session_id,
        student_id="maria",
        version_student_model="v7",
        version_banco="banco-v2",
        version_politica="v1",
        spec_version="foundation-2026-07-10",
    )


def _estado_con_fact() -> tuple[LearningState, object]:
    estado = LearningState(identidad=_identidad(), contexto={"ruta": "condicionales"})
    r = registrar_fact(
        estado,
        autor=Capacidad.EVALUAR,
        contenido={"competencia": "COMP-2", "items_incorrectos": []},
        provenance=Provenance.de(OrigenProvenance.INSTRUMENTO, banco="v2"),
    )
    assert isinstance(r, Aplicado)
    return r.estado, r.estado.facts[0].id


def _con_propuesta(estado, fact_id, asunto: str, confianza: Decimal, autor=Capacidad.ORIENTAR):
    r = registrar_claim(
        estado,
        autor=autor,
        tipo=TipoClaim.PROPUESTA,
        asunto=asunto,
        afirmacion={"accion": "avanzar-con-andamiaje"},
        respaldo=(fact_id,),
        confianza=confianza,
        provenance=Provenance.de(OrigenProvenance.REGLA, id="orientacion-v1"),
    )
    assert isinstance(r, Aplicado)
    return r.estado, r.estado.claims[-1]


class TestPropuestaUnica_DerivaDirecta:
    def test_v1_theta_cero_siempre_deriva(self):
        """theta_v1 = 0: por A1, ce >= 0 siempre — cualquier propuesta
        única, sin importar su confianza declarada, deriva decisión."""
        estado, fact_id = _estado_con_fact()
        estado, claim = _con_propuesta(estado, fact_id, "siguiente-paso(sesion)", Decimal("0.01"))
        intent = derivar_decision_directa(estado, _V1)
        assert intent is not None
        assert intent.operacion == "registrar_decision"
        assert intent.argumentos["origen"] == claim.id
        assert intent.argumentos["contenido"] == {"accion": "avanzar-con-andamiaje"}

    def test_ce_por_debajo_de_theta_no_deriva(self):
        """D3 — insuficiencia: con una política real (theta=0.70) y una
        propuesta débil (confianza=0.50 < theta), NO deriva nada."""
        estado, fact_id = _estado_con_fact()
        estado, claim = _con_propuesta(estado, fact_id, "siguiente-paso(sesion)", Decimal("0.50"))
        intent = derivar_decision_directa(estado, _POLITICA_THETA_ALTO)
        assert intent is None

    def test_ce_igual_a_theta_si_deriva(self):
        """Frontera: ce == theta cuenta como "alcanza" (>=), no como
        insuficiencia."""
        estado, fact_id = _estado_con_fact()
        estado, claim = _con_propuesta(estado, fact_id, "siguiente-paso(sesion)", Decimal("0.70"))
        intent = derivar_decision_directa(estado, _POLITICA_THETA_ALTO)
        assert intent is not None
        assert intent.argumentos["origen"] == claim.id

    def test_dos_propuestas_rivales_no_derivan_directo(self):
        """Un asunto con ≥2 propuestas es tensión (RFC-0006/2), no
        propuesta única — esta función debe ignorarlo por completo,
        incluso bajo theta=0 (donde cualquier propuesta única sí
        derivaría). La resolución de la rivalidad es convocar()/
        derivar_decision(), nunca esta función."""
        estado, fact_id = _estado_con_fact()
        estado, _ = _con_propuesta(
            estado, fact_id, "siguiente-paso(sesion)", Decimal("0.82"), autor=Capacidad.REMEDIAR
        )
        estado, _ = _con_propuesta(
            estado, fact_id, "siguiente-paso(sesion)", Decimal("0.75"), autor=Capacidad.ORIENTAR
        )
        assert derivar_decision_directa(estado, _V1) is None

    def test_asunto_ya_decidido_no_se_re_deriva(self):
        """Si el claim ya originó una decisión (aunque sea de otra
        transición), no se deriva de nuevo — mismo criterio de
        `derivar_decision()` (con_decision = {d.origen ...})."""
        estado, fact_id = _estado_con_fact()
        estado, claim = _con_propuesta(estado, fact_id, "siguiente-paso(sesion)", Decimal("0.90"))
        r = registrar_decision(estado, origen=claim.id, contenido=dict(claim.afirmacion))
        assert isinstance(r, Aplicado)
        estado = r.estado
        assert derivar_decision_directa(estado, _V1) is None

    def test_sin_propuestas_devuelve_None(self):
        estado, _ = _estado_con_fact()
        assert derivar_decision_directa(estado, _V1) is None

    def test_dos_asuntos_distintos_cada_uno_propuesta_unica(self):
        """Escaneo por orden de asunto (determinista) — el primero en
        orden alfabético que alcanza theta se deriva; los demás quedan
        para el siguiente ciclo de enrutar() (un cambio por transición,
        mismo patrón que convocar()/derivar_decision())."""
        estado, fact_id = _estado_con_fact()
        estado, claim_a = _con_propuesta(estado, fact_id, "asunto-a", Decimal("0.60"))
        estado, claim_b = _con_propuesta(estado, fact_id, "asunto-b", Decimal("0.60"))
        intent = derivar_decision_directa(estado, _V1)
        assert intent is not None
        assert intent.argumentos["origen"] == claim_a.id
