"""RFC-0006/5, Parte F — escalada orgánica (RFC-0006 §4; CONCEPT-0002
§5/§5 bis; ROADMAP-RFC-0006 Parte F).

Sin Postgres, sin LangGraph corriendo: `LearningState` construido a mano
contra reducers puros — mismo patrón que las Partes B/C/D/E. La versión
con el grafo real vive en
`tests/runtime/walkthrough/test_parteF_escalada_organica_grafo.py`.

Normas citadas por estos tests:
- RFC-0006 §4: "Escalada — dos vías, ambas de política: casos que la
  política reserva al humano, y el límite de reconvocatoria: una tensión
  aplazada y reconvocada N veces (política) sin discriminar escala al
  docente — ninguna deliberación puede diferirse para siempre".
- CONCEPT-0002 §5: la reconvocatoria es una NUEVA deliberación que
  referencia (`enlaza_a`) a la anterior — jamás reapertura (INV-3, P14);
  "la cadena deliberación → deliberación' es, ella misma, evidencia
  longitudinal".
- CONCEPT-0002 §5 bis (regla de oro): la escalada es uno de los TRES
  resultados posibles — el espacio sigue cerrado, ningún tipo nuevo.
- RFC-0009 §3: lo escalado espera la autoridad humana — la mecánica
  jamás lo resuelve por su cuenta (anti-bypass), ni siquiera bajo
  urgencia cuando el asunto está reservado.
- ROADMAP-RFC-0006 Parte F: contar la cadena por `enlaza_a` hacia atrás,
  "sin confundir una cadena larga con N tensiones distintas del mismo
  asunto"; "necesita tests contra cadenas de 3+ reconvocatorias".
"""

from __future__ import annotations

from decimal import Decimal

from runtime.kernel.deliberation.mecanica import (
    REGLA_PROVISIONAL,
    convocar,
    tension_bloqueante,
)
from runtime.kernel.deliberation.politica import Politica
from runtime.kernel.reducers import Aplicado, registrar_claim, registrar_deliberacion, registrar_fact
from runtime.kernel.state.entries import (
    Aplazada,
    Capacidad,
    Escalada,
    OrigenProvenance,
    Provenance,
    Resuelta,
    TipoClaim,
)
from runtime.kernel.state.state import Identidad, LearningState

_ASUNTO = "siguiente-paso(sesion)"

_RESERVA_DOCENTE = Politica(
    peso_refuerzo=Decimal("0"),
    peso_refutacion=Decimal("0"),
    peso_decaimiento=Decimal("0"),
    theta=Decimal("0"),
    asuntos_reservados=frozenset({_ASUNTO}),
)

_DELTA_010_LIMITE_2 = Politica(
    peso_refuerzo=Decimal("0"),
    peso_refutacion=Decimal("0"),
    peso_decaimiento=Decimal("0"),
    theta=Decimal("0"),
    delta=Decimal("0.10"),
    limite_reconvocatoria=2,
)


def _identidad(session_id: str = "s-parteF") -> Identidad:
    return Identidad(
        session_id=session_id,
        student_id="maria",
        version_student_model="v7",
        version_banco="banco-v2",
        version_politica="v1",
        spec_version="foundation-2026-07-10",
    )


def _estado_con_rivales(asunto: str, confianzas: tuple[Decimal, ...]):
    estado = LearningState(identidad=_identidad(), contexto={"ruta": "condicionales"})
    r = registrar_fact(
        estado,
        autor=Capacidad.EVALUAR,
        contenido={"competencia": "COMP-2", "items_incorrectos": []},
        provenance=Provenance.de(OrigenProvenance.INSTRUMENTO, banco="v2"),
    )
    assert isinstance(r, Aplicado)
    estado = r.estado
    for i, confianza in enumerate(confianzas):
        estado = _con_rival(estado, asunto, confianza, i)
    return estado


def _con_rival(estado: LearningState, asunto: str, confianza: Decimal, sello: int):
    r = registrar_claim(
        estado,
        autor=Capacidad.ORIENTAR,
        tipo=TipoClaim.PROPUESTA,
        asunto=asunto,
        afirmacion={"opcion": sello},
        respaldo=(estado.facts[0].id,),
        confianza=confianza,
        provenance=Provenance.de(OrigenProvenance.REGLA, id=f"regla-{asunto}-{sello}"),
    )
    assert isinstance(r, Aplicado)
    return r.estado


def _aplicar_convocatoria(estado: LearningState, politica: Politica, urgente: bool = False):
    intent = convocar(estado, politica, urgente)
    assert intent is not None
    r = registrar_deliberacion(estado, **intent.argumentos)
    assert isinstance(r, Aplicado)
    return r.estado, intent


class TestViaReserva:
    def test_asunto_reservado_escala_sin_resolver(self):
        """RFC-0006 §4, primera vía: la política reserva el asunto al
        humano — la tensión no se resuelve por mecánica, se escala."""
        estado = _estado_con_rivales(_ASUNTO, (Decimal("0.50"), Decimal("0.90")))
        estado, intent = _aplicar_convocatoria(estado, _RESERVA_DOCENTE)
        resultado = estado.deliberaciones[-1].resultado
        assert isinstance(resultado, Escalada)
        assert resultado.destinatario == "docente"
        # escalar no descarta: el docente selecciona entre lo que la
        # escalada puso sobre la mesa (P15, E3)
        for ref in estado.deliberaciones[-1].participantes:
            assert estado.buscar(ref).vigencia.vigente

    def test_la_urgencia_no_devuelve_la_autoridad_reservada(self):
        """Anti-bypass (RFC-0009 §3): resolver provisionalmente un asunto
        que la política reservó al docente sería decidir por mecánica lo
        que espera a una persona — la reserva precede a la urgencia."""
        estado = _estado_con_rivales(_ASUNTO, (Decimal("0.50"), Decimal("0.90")))
        intent = convocar(estado, _RESERVA_DOCENTE, urgente=True)
        assert isinstance(intent.argumentos["resultado"], Escalada)

    def test_un_asunto_no_reservado_se_resuelve_con_normalidad(self):
        """La reserva es POR ASUNTO — el resto del consenso no cambia."""
        estado = _estado_con_rivales("modalidad(obj-1)", (Decimal("0.50"), Decimal("0.90")))
        intent = convocar(estado, _RESERVA_DOCENTE)
        assert isinstance(intent.argumentos["resultado"], Resuelta)

    def test_el_asunto_escalado_espera_al_docente(self):
        """Tras la escalada, la tensión deja de ser bloqueante aunque el
        paisaje cambie: solo el docente (E3) cierra una escalada."""
        estado = _estado_con_rivales(_ASUNTO, (Decimal("0.50"), Decimal("0.90")))
        estado, _ = _aplicar_convocatoria(estado, _RESERVA_DOCENTE)
        assert tension_bloqueante(estado) is None
        # ni siquiera un rival nuevo (paisaje cambiado) la reconvoca
        estado = _con_rival(estado, _ASUNTO, Decimal("0.70"), 99)
        assert tension_bloqueante(estado) is None
        assert convocar(estado, _RESERVA_DOCENTE) is None


class TestReconvocatoria:
    def test_evidencia_nueva_reconvoca_enlazando_a_la_aplazada(self):
        """CONCEPT-0002 §5: "aparece una nueva propuesta rival sobre el
        mismo slot" — el paisaje del asunto cambió respecto de los
        participantes de la cabeza: nueva deliberación `enlaza_a` la
        aplazada, jamás reapertura (INV-3, P14)."""
        estado = _estado_con_rivales(_ASUNTO, (Decimal("0.50"), Decimal("0.55")))
        estado, _ = _aplicar_convocatoria(estado, _DELTA_010_LIMITE_2)
        aplazada = estado.deliberaciones[-1]
        assert isinstance(aplazada.resultado, Aplazada)

        estado = _con_rival(estado, _ASUNTO, Decimal("0.53"), 2)
        tension = tension_bloqueante(estado)
        assert tension is not None
        assert len(tension[2]) == 3  # los tres rivales vigentes
        intent = convocar(estado, _DELTA_010_LIMITE_2)
        assert intent.argumentos["enlaza_a"] == aplazada.id

    def test_reconvocatoria_que_discrimina_cierra_la_cadena(self):
        """La reconvocatoria no está condenada a aplazarse: si la
        evidencia nueva separa el margen, la resolución es plena y la
        cadena queda cerrada (la cabeza ya no está abierta)."""
        estado = _estado_con_rivales(_ASUNTO, (Decimal("0.50"), Decimal("0.55")))
        estado, _ = _aplicar_convocatoria(estado, _DELTA_010_LIMITE_2)
        aplazada = estado.deliberaciones[-1]

        estado = _con_rival(estado, _ASUNTO, Decimal("0.90"), 2)
        estado, intent = _aplicar_convocatoria(estado, _DELTA_010_LIMITE_2)
        cierre = estado.deliberaciones[-1]
        assert isinstance(cierre.resultado, Resuelta)
        assert cierre.enlaza_a == aplazada.id
        assert tension_bloqueante(estado) is None

    def test_sin_evidencia_nueva_no_hay_churn(self):
        """Con el paisaje idéntico a los participantes de la cabeza, la
        reconvocatoria reproduciría la misma resolución bit a bit —
        no se convoca (anti-churn, propiedad anti-ciclo del grafo)."""
        estado = _estado_con_rivales(_ASUNTO, (Decimal("0.50"), Decimal("0.55")))
        estado, _ = _aplicar_convocatoria(estado, _DELTA_010_LIMITE_2)
        # evidencia en OTRO asunto no toca este paisaje
        r = registrar_fact(
            estado,
            autor=Capacidad.TUTORIZAR,
            contenido={"senal": "pausa-larga"},
            provenance=Provenance.de(OrigenProvenance.TELEMETRIA),
        )
        assert isinstance(r, Aplicado)
        assert tension_bloqueante(r.estado) is None
        assert convocar(r.estado, _DELTA_010_LIMITE_2) is None


class TestViaLimiteDeReconvocatoria:
    def _cadena_de_dos_aplazadas(self):
        """aplazada₁ ← aplazada₂ (cadena real de 2, paisaje cambiando
        entre convocatorias sin que el margen discrimine jamás)."""
        estado = _estado_con_rivales(_ASUNTO, (Decimal("0.50"), Decimal("0.55")))
        estado, _ = _aplicar_convocatoria(estado, _DELTA_010_LIMITE_2)
        aplazada_1 = estado.deliberaciones[-1]

        estado = _con_rival(estado, _ASUNTO, Decimal("0.53"), 2)
        estado, _ = _aplicar_convocatoria(estado, _DELTA_010_LIMITE_2)
        aplazada_2 = estado.deliberaciones[-1]
        assert isinstance(aplazada_2.resultado, Aplazada)
        assert aplazada_2.enlaza_a == aplazada_1.id
        return estado, aplazada_1, aplazada_2

    def test_cadena_agotada_escala_al_docente(self):
        """RFC-0006 §4, segunda vía: con `limite_reconvocatoria=2`, la
        tercera convocatoria de una cadena que sigue sin discriminar no
        produce otra Aplazada — escala. Cadena completa de 3 (ROADMAP
        Parte F: tests contra cadenas de 3+): aplazada₁ ← aplazada₂ ←
        escalada, cada eslabón enlazado al anterior."""
        estado, aplazada_1, aplazada_2 = self._cadena_de_dos_aplazadas()

        estado = _con_rival(estado, _ASUNTO, Decimal("0.54"), 3)
        estado, _ = _aplicar_convocatoria(estado, _DELTA_010_LIMITE_2)
        escalada = estado.deliberaciones[-1]
        assert isinstance(escalada.resultado, Escalada)
        assert escalada.enlaza_a == aplazada_2.id
        assert aplazada_2.enlaza_a == aplazada_1.id
        # la historia entera sigue ahí — P14: nada se borra, la cadena
        # ES la evidencia longitudinal (CONCEPT-0002 §5)
        assert len(estado.deliberaciones) == 3

    def test_tras_la_escalada_ni_el_paisaje_nuevo_reconvoca(self):
        """El final de la cadena espera al humano: la escalada bloquea
        el asunto incondicionalmente (RFC-0009 §3)."""
        estado, _, _ = self._cadena_de_dos_aplazadas()
        estado = _con_rival(estado, _ASUNTO, Decimal("0.54"), 3)
        estado, _ = _aplicar_convocatoria(estado, _DELTA_010_LIMITE_2)

        estado = _con_rival(estado, _ASUNTO, Decimal("0.99"), 4)
        assert tension_bloqueante(estado) is None
        assert convocar(estado, _DELTA_010_LIMITE_2) is None

    def test_la_urgencia_precede_al_limite(self):
        """CONCEPT-0002 §4: "la provisionalidad es para el estudiante" —
        escalar es esperar a una persona, y con un estudiante en la
        pantalla la cadena agotada se resuelve provisional (INV-12 la
        vigila), no se difiere una vez más."""
        estado, _, _ = self._cadena_de_dos_aplazadas()
        estado = _con_rival(estado, _ASUNTO, Decimal("0.54"), 3)
        intent = convocar(estado, _DELTA_010_LIMITE_2, urgente=True)
        resultado = intent.argumentos["resultado"]
        assert isinstance(resultado, Resuelta)
        assert resultado.regla == REGLA_PROVISIONAL

    def test_otra_aplazada_del_mismo_asunto_fuera_de_la_cadena_no_cuenta(self):
        """ROADMAP Parte F, el error sutil: el límite cuenta la CADENA
        `enlaza_a`, no las deliberaciones sueltas del asunto. Una cadena
        cerrada por resolución plena no hereda sus aplazamientos a la
        tensión siguiente del mismo asunto."""
        estado = _estado_con_rivales(_ASUNTO, (Decimal("0.50"), Decimal("0.55")))
        estado, _ = _aplicar_convocatoria(estado, _DELTA_010_LIMITE_2)  # aplazada₁
        estado = _con_rival(estado, _ASUNTO, Decimal("0.53"), 2)
        estado, _ = _aplicar_convocatoria(estado, _DELTA_010_LIMITE_2)  # aplazada₂
        estado = _con_rival(estado, _ASUNTO, Decimal("0.90"), 3)
        estado, _ = _aplicar_convocatoria(estado, _DELTA_010_LIMITE_2)  # resuelta
        assert isinstance(estado.deliberaciones[-1].resultado, Resuelta)

        # tensión NUEVA sobre el mismo asunto: dos rivales frescos
        estado = _con_rival(estado, _ASUNTO, Decimal("0.60"), 4)
        estado, intent = _aplicar_convocatoria(estado, _DELTA_010_LIMITE_2)
        nueva = estado.deliberaciones[-1]
        # cadena nueva: aplazada (0.90 vs 0.60 no: margen 0.30 >= 0.10)
        # — el ganador de la resuelta sigue vigente, así que la tensión
        # es {ganador, rival nuevo} y el margen discrimina: Resuelta,
        # sin enlaza_a (cadena anterior quedó cerrada)
        assert isinstance(nueva.resultado, Resuelta)
        assert "enlaza_a" not in intent.argumentos
