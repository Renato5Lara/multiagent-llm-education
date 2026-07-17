"""RFC-0006/4b, Parte E — aplazamiento y decisión provisional
(RFC-0006 §4; CONCEPT-0002 §4/§5 bis; ROADMAP-RFC-0006 Parte E).

Sin Postgres, sin LangGraph corriendo: `LearningState` construido a mano
contra reducers puros — mismo patrón que las Partes B/C/D. La versión
con el grafo real (LangGraph + Postgres, sin `GraphRecursionError`) vive
en `tests/runtime/walkthrough/test_parteE_walkthrough_aplazamiento.py`.

Normas citadas por estos tests:
- RFC-0006 §4: "Margen < δ → aplazada, registrando qué evidencia
  discriminaría (INV-7)"; "Decisión provisional — si el slot es urgente
  ... se resuelve con el mejor claim disponible".
- CONCEPT-0002 §4: la declaración de evidencia faltante es accionable;
  "el aplazamiento es para el sistema; la provisionalidad es para el
  estudiante".
- CONCEPT-0002 §5: no hay reapertura — mientras una deliberación quede
  abierta (aplazada/escalada sin enlace posterior), su asunto no vuelve
  a ser bloqueante (la reconvocatoria es Parte F).
- INV-12: la decisión derivada de una provisional queda, como todas,
  pendiente-de-validación.
- ROADMAP-RFC-0006 §5/2: `urgente` es parámetro externo del Boundary,
  jamás derivado de `estado.ejecucion`.
"""

from __future__ import annotations

from decimal import Decimal

from runtime.kernel.deliberation.mecanica import (
    REGLA_POLITICA_V1,
    REGLA_PROVISIONAL,
    convocar,
    derivar_decision,
    tension_bloqueante,
)
from runtime.kernel.deliberation.politica import POLITICAS, Politica
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
    Escalada,
    EstadoValidacion,
    OrigenProvenance,
    Provenance,
    Resuelta,
    TipoClaim,
)
from runtime.kernel.state.state import Identidad, LearningState

_V1 = POLITICAS["v1"]

_DELTA_010 = Politica(
    peso_refuerzo=Decimal("0"),
    peso_refutacion=Decimal("0"),
    peso_decaimiento=Decimal("0"),
    theta=Decimal("0"),
    delta=Decimal("0.10"),
)


def _identidad(session_id: str = "s-parteE") -> Identidad:
    return Identidad(
        session_id=session_id,
        student_id="maria",
        version_student_model="v7",
        version_banco="banco-v2",
        version_politica="v1",
        spec_version="foundation-2026-07-10",
    )


def _estado_con_dos_rivales(tipo: TipoClaim, asunto: str, confianzas: tuple[Decimal, Decimal]):
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

    ids = []
    autor = Capacidad.DIAGNOSTICAR if tipo is TipoClaim.INTERPRETACION else Capacidad.ORIENTAR
    for i, confianza in enumerate(confianzas):
        r = registrar_claim(
            estado,
            autor=autor,
            tipo=tipo,
            asunto=asunto,
            afirmacion={"opcion": i},
            respaldo=(fact_id,),
            confianza=confianza,
            provenance=Provenance.de(OrigenProvenance.REGLA, id=f"regla-{i}"),
        )
        assert isinstance(r, Aplicado)
        estado = r.estado
        ids.append(estado.claims[-1].id)
    return estado, ids


def _aplicar_convocatoria(estado: LearningState, politica: Politica, urgente: bool = False):
    """convocar → registrar_deliberacion, devolviendo el estado nuevo."""
    intent = convocar(estado, politica, urgente)
    assert intent is not None
    r = registrar_deliberacion(estado, **intent.argumentos)
    assert isinstance(r, Aplicado)
    return r


class TestAplazamiento:
    def test_margen_insuficiente_registra_aplazada_accionable(self):
        """RFC-0006 §4: "Margen < δ → aplazada, registrando qué evidencia
        discriminaría"; CONCEPT-0002 §4: la declaración es accionable —
        nombra el asunto y los claims que la evidencia debe separar."""
        estado, (id_a, id_b) = _estado_con_dos_rivales(
            TipoClaim.INTERPRETACION, "dominio(COMP-2)", (Decimal("0.50"), Decimal("0.55"))
        )
        intent = convocar(estado, _DELTA_010)
        assert intent is not None
        resultado = intent.argumentos["resultado"]
        assert isinstance(resultado, Aplazada)
        assert "dominio(COMP-2)" in resultado.evidencia_faltante
        assert str(id_a) in resultado.evidencia_faltante
        assert str(id_b) in resultado.evidencia_faltante

    def test_aplazada_pasa_el_reducer_y_no_supersede_a_nadie(self):
        """A diferencia de una Resuelta, aplazar no descarta rivales:
        ambos claims siguen vigentes esperando la evidencia (CONCEPT-0002
        §4 — el aplazamiento es productivo, no una selección)."""
        estado, ids = _estado_con_dos_rivales(
            TipoClaim.PROPUESTA, "siguiente-paso(sesion)", (Decimal("0.50"), Decimal("0.55"))
        )
        r = _aplicar_convocatoria(estado, _DELTA_010)
        assert isinstance(r.estado.deliberaciones[-1].resultado, Aplazada)
        for claim_id in ids:
            assert r.estado.buscar(claim_id).vigencia.vigente
        assert r.eventos[-1].resultado == "aplazada"

    def test_asunto_aplazado_deja_de_ser_bloqueante(self):
        """CONCEPT-0002 §5: no hay reapertura. Mientras la aplazada siga
        abierta (sin deliberación enlazada posterior — Parte F), volver a
        convocarla duplicaría deliberaciones sin evidencia nueva."""
        estado, _ = _estado_con_dos_rivales(
            TipoClaim.PROPUESTA, "siguiente-paso(sesion)", (Decimal("0.50"), Decimal("0.55"))
        )
        r = _aplicar_convocatoria(estado, _DELTA_010)
        assert tension_bloqueante(r.estado) is None
        assert convocar(r.estado, _DELTA_010) is None

    def test_otro_asunto_sigue_siendo_bloqueante(self):
        """El aplazamiento espera POR ASUNTO, no congela el consenso:
        una tensión nueva en otro asunto se detecta con normalidad."""
        estado, _ = _estado_con_dos_rivales(
            TipoClaim.PROPUESTA, "siguiente-paso(sesion)", (Decimal("0.50"), Decimal("0.55"))
        )
        r = _aplicar_convocatoria(estado, _DELTA_010)
        estado = r.estado
        for i, confianza in enumerate((Decimal("0.30"), Decimal("0.90"))):
            r2 = registrar_claim(
                estado,
                autor=Capacidad.DIAGNOSTICAR,
                tipo=TipoClaim.INTERPRETACION,
                asunto="dominio(COMP-3)",
                afirmacion={"opcion": i},
                respaldo=(estado.facts[0].id,),
                confianza=confianza,
                provenance=Provenance.de(OrigenProvenance.REGLA, id=f"regla-b{i}"),
            )
            assert isinstance(r2, Aplicado)
            estado = r2.estado
        tension = tension_bloqueante(estado)
        assert tension is not None
        assert tension[1] == "dominio(COMP-3)"

    def test_escalada_abierta_tambien_espera_no_hay_bypass_del_docente(self):
        """RFC-0009 §3: una tensión escalada espera la autoridad humana.
        La mecánica jamás debe reconvocarla y resolver por su cuenta lo
        que el docente tiene sobre la mesa (S2)."""
        estado, ids = _estado_con_dos_rivales(
            TipoClaim.PROPUESTA, "siguiente-paso(sesion)", (Decimal("0.50"), Decimal("0.55"))
        )
        r = registrar_deliberacion(
            estado, participantes=tuple(ids), resultado=Escalada()
        )
        assert isinstance(r, Aplicado)
        assert tension_bloqueante(r.estado) is None
        assert convocar(r.estado, _V1) is None


class TestDecisionProvisional:
    def test_urgente_resuelve_con_el_mejor_claim_disponible(self):
        """RFC-0006 §4: "si el slot es urgente ... se resuelve con el
        mejor claim disponible"; CONCEPT-0002 §5 bis: la provisional no
        es un resultado nuevo — es una selección con su regla registrada
        (INV-7), mismo estatus que "decision-humana"."""
        estado, (id_bajo, id_alto) = _estado_con_dos_rivales(
            TipoClaim.PROPUESTA, "siguiente-paso(sesion)", (Decimal("0.50"), Decimal("0.55"))
        )
        intent = convocar(estado, _DELTA_010, urgente=True)
        assert intent is not None
        resultado = intent.argumentos["resultado"]
        assert isinstance(resultado, Resuelta)
        assert resultado.regla == REGLA_PROVISIONAL
        assert resultado.aceptados == (id_alto,)
        assert resultado.confianza == Decimal("0.55")  # ce del ganador

    def test_urgencia_no_degrada_una_resolucion_plena(self):
        """`urgente` solo actúa cuando la regla no discrimina: con margen
        suficiente, la resolución es plena aunque haya alguien esperando."""
        estado, (id_bajo, id_alto) = _estado_con_dos_rivales(
            TipoClaim.PROPUESTA, "siguiente-paso(sesion)", (Decimal("0.40"), Decimal("0.90"))
        )
        intent = convocar(estado, _DELTA_010, urgente=True)
        resultado = intent.argumentos["resultado"]
        assert resultado.regla == REGLA_POLITICA_V1
        assert resultado.aceptados == (id_alto,)

    def test_decision_derivada_queda_pendiente_de_validacion(self):
        """INV-12: la decisión derivada de una provisional no recibe un
        estado especial — queda pendiente-de-validación como todas, y es
        Validar quien la vigila (CONCEPT-0002 §4)."""
        estado, _ = _estado_con_dos_rivales(
            TipoClaim.PROPUESTA, "siguiente-paso(sesion)", (Decimal("0.50"), Decimal("0.55"))
        )
        r = _aplicar_convocatoria(estado, _DELTA_010, urgente=True)
        intent = derivar_decision(r.estado)
        assert intent is not None
        r2 = registrar_decision(r.estado, **intent.argumentos)
        assert isinstance(r2, Aplicado)
        decision = r2.estado.decisiones[-1]
        assert decision.estado_validacion is EstadoValidacion.PENDIENTE_DE_VALIDACION

    def test_v1_hace_la_parte_e_estructuralmente_inalcanzable(self):
        """Regresión de la prueba matemática de la Parte D: bajo v1
        (delta=0) el margen nunca es negativo, así que ni el empate exacto
        aplaza ni la urgencia cambia la regla registrada."""
        estado, _ = _estado_con_dos_rivales(
            TipoClaim.INTERPRETACION, "dominio(COMP-2)", (Decimal("0.50"), Decimal("0.50"))
        )
        for urgente in (False, True):
            intent = convocar(estado, _V1, urgente=urgente)
            assert intent is not None
            assert intent.argumentos["resultado"].regla == REGLA_POLITICA_V1


class TestEnrutarConDeliberacionAbierta:
    def test_enrutar_no_encola_decidir_ni_deliberar(self):
        """La propiedad anti-ciclo (precedente GraphRecursionError): con
        una aplazada abierta no hay decisión derivable ("decidir"
        ciclaría) ni tensión bloqueante ("deliberar" duplicaría) — el
        grafo sigue su fall-through normal y termina o avanza por otra
        capacidad."""
        from runtime.engine.graph.walkthrough import enrutar

        estado, _ = _estado_con_dos_rivales(
            TipoClaim.PROPUESTA, "siguiente-paso(sesion)", (Decimal("0.50"), Decimal("0.55"))
        )
        r = _aplicar_convocatoria(estado, _DELTA_010)
        grafo = {"estado": r.estado, "intents": (), "registros": ()}
        assert enrutar(grafo, _DELTA_010) not in ("decidir", "deliberar")

    def test_enrutar_si_encola_decidir_con_una_resuelta_sin_decision(self):
        """La guardia nueva no rompe el camino feliz: una deliberación
        resuelta sin decisión sigue enrutando a "decidir"."""
        from runtime.engine.graph.walkthrough import enrutar

        estado, _ = _estado_con_dos_rivales(
            TipoClaim.PROPUESTA, "siguiente-paso(sesion)", (Decimal("0.40"), Decimal("0.90"))
        )
        r = _aplicar_convocatoria(estado, _V1)
        assert isinstance(r.estado.deliberaciones[-1].resultado, Resuelta)
        grafo = {"estado": r.estado, "intents": (), "registros": ()}
        assert enrutar(grafo, _V1) == "decidir"
