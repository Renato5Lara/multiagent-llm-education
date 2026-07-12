"""La quinta suite (ADR-0005 §1): el Walkthrough-0001 como test de
integración canónico — la historia de María sobre código real.

Sin dobles: PostgreSQL real, LangGraph real, capacidades regla reales.
"""

import dataclasses
import os
from decimal import Decimal

import psycopg2
import pytest

from runtime.engine.checkpoint import (
    AlmacenMemoria,
    AlmacenTransiciones,
    reconstruir,
    verificar,
)
from runtime.engine.graph import ejecutar_walkthrough
from runtime.kernel.state.salidas import proyectar_salidas
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
        assert len(registros) == estado.transicion == 7  # PR-5: +Adaptar
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

        # PR-5: Adaptar no necesita evidencia posterior — su disparador es
        # la decisión misma ("reforzar" ya está en DISENO_POR_ACCION), así
        # que corre ANTES que Validar (que sí espera el fact posterior).
        adaptacion = next(
            c for c in estado.claims if c.autor is Capacidad.ADAPTAR and c.vigencia.vigente
        )
        assert decision_id in adaptacion.respaldo
        assert adaptacion.afirmacion["modalidad"] == "visual"

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

        # El recorrido creció en tres transiciones exactas (Adaptar,
        # Validar, Modelar — PR-5, PR-2, PR-3): 5 hechos sembrados +
        # adaptación + veredicto + modelado.
        assert estado.transicion == 8
        assert len(final["registros"]) == 8

    def test_sin_evidencia_posterior_el_recorrido_termina_igual_que_antes(
        self, esquema
    ):
        # Guardia segura: con solo el hecho inicial (sin "después"),
        # Validar no debe disparar — pero Adaptar sí (PR-5: no depende de
        # evidencia posterior, solo de la decisión). transicion == 7 desde
        # PR-5 (antes era 6, por el camino Diagnosticar→Remediar/
        # Orientar→Deliberar→Decidir; ahora +Adaptar).
        almacen = AlmacenTransiciones(_URL, esquema=esquema)
        almacen.preparar()
        final = ejecutar_walkthrough(
            almacen, _identidad("s-validar-sin-evidencia"), _hecho_del_mundo()
        )
        estado = final["estado"]
        assert not any(c.autor is Capacidad.VALIDAR for c in estado.claims)
        assert any(c.autor is Capacidad.ADAPTAR for c in estado.claims)
        assert estado.transicion == 7


class TestTutorizarIntegradoAlFlujo:
    """PR-4: Tutorizar deja de ser huérfana del grafo.

    Su disparador es el PRIMER fact de Evaluar — pero exige
    `items_totales` (domain.tutorizar.producir), campo que el fixture
    canónico de María (`_hecho_del_mundo`, arriba) nunca sembró — solo
    `items_incorrectos`. Por eso Tutorizar no se activa en ninguno de los
    tests existentes (María, los guardianes P13, este mismo archivo): es
    el comportamiento correcto de la guardia, no una omisión de PR-4. Este
    test siembra su propio hecho, completo, para demostrar la integración."""

    @staticmethod
    def _hecho_del_mundo_completo() -> tuple[TransitionIntent, ...]:
        return (
            TransitionIntent(
                productor=Capacidad.EVALUAR,
                operacion="registrar_fact",
                argumentos={
                    "autor": Capacidad.EVALUAR,
                    "contenido": {
                        "competencia": "COMP-2",
                        "items_incorrectos": [3, 4, 8],
                        "items_totales": 10,
                    },
                    "provenance": Provenance.de(
                        OrigenProvenance.INSTRUMENTO, banco="v2"
                    ),
                },
                base=0,
            ),
        )

    def test_tutorizar_detecta_la_senal_desde_el_primer_fact_de_evaluar(
        self, esquema
    ):
        almacen = AlmacenTransiciones(_URL, esquema=esquema)
        almacen.preparar()
        final = ejecutar_walkthrough(
            almacen,
            _identidad("s-tutorizar-integrado"),
            self._hecho_del_mundo_completo(),
        )
        estado = final["estado"]

        fact_evaluar = next(f for f in estado.facts if f.autor is Capacidad.EVALUAR)
        senal = next(f for f in estado.facts if f.autor is Capacidad.TUTORIZAR)
        assert senal.contenido["fact_origen"] == str(fact_evaluar.id)
        assert senal.contenido["senal"] == "confusion"  # 3 de 10 incorrectos

        # Tutorizar no bloquea nada: el resto del recorrido sigue intacto.
        interpretacion = next(
            c for c in estado.claims if c.tipo is TipoClaim.INTERPRETACION
        )
        assert interpretacion.autor is Capacidad.DIAGNOSTICAR
        assert estado.decisiones

    def test_sin_items_totales_tutorizar_no_dispara_igual_que_antes(self, esquema):
        # Guardia segura: el fixture canónico de María no incluye
        # items_totales — Tutorizar no debe activarse. transicion == 7
        # desde PR-5 (Adaptar sí dispara con la sola decisión).
        almacen = AlmacenTransiciones(_URL, esquema=esquema)
        almacen.preparar()
        final = ejecutar_walkthrough(
            almacen, _identidad("s-tutorizar-sin-total"), _hecho_del_mundo()
        )
        estado = final["estado"]
        assert not any(f.autor is Capacidad.TUTORIZAR for f in estado.facts)
        assert estado.transicion == 7


class TestM4_PR1B_ReanudacionDeSesion:
    """M4 PR-1B: sustituye a `TestCierreM2` (M2). Aquella suite dejó
    documentado que Validar (exige un fact de Evaluar *posterior* a la
    decisión) y Tutorizar (exige que la decisión *todavía* no exista)
    nunca podían coexistir en el mismo recorrido — porque
    `ejecutar_walkthrough` era una única invocación síncrona sin
    reanudación (P10/RFC-0008 no existían como mecanismo). Con PR-1A
    (reconstrucción determinista) + PR-1B (reanudación en
    `ejecutar_walkthrough`), esa limitación ya no es estructural: esta
    suite demuestra las OCHO capacidades en la MISMA sesión, en dos
    invocaciones separadas — con dos `AlmacenTransiciones` distintos
    apuntando al mismo `session_id`, simulando dos procesos (mismo
    patrón que el kill-test de R1-R6)."""

    def test_las_ocho_capacidades_en_la_misma_sesion_reanudada(self, esquema):
        identidad = _identidad("s-m4-pr1b-reanudada")

        # Invocación #1 ("proceso" 1): siembra el fact completo (con
        # items_totales, dispara Tutorizar) y corre hasta el END natural
        # — sin evidencia posterior todavía, Validar no puede disparar.
        almacen_1 = AlmacenTransiciones(_URL, esquema=esquema)
        almacen_1.preparar()
        final_1 = ejecutar_walkthrough(
            almacen_1, identidad, TestTutorizarIntegradoAlFlujo._hecho_del_mundo_completo()
        )
        estado_1, registros_1 = final_1["estado"], final_1["registros"]

        assert not any(c.autor is Capacidad.VALIDAR for c in estado_1.claims)
        assert not any(c.autor is Capacidad.MODELAR for c in estado_1.claims)
        assert any(f.autor is Capacidad.TUTORIZAR for f in estado_1.facts)
        assert len(registros_1) == estado_1.transicion == 8
        assert verificar(identidad, registros_1) is None

        decision_id = estado_1.decisiones[0].id

        # Invocación #2 ("proceso" 2, nuevo AlmacenTransiciones — misma
        # identidad, mismo esquema): la única evidencia nueva es el fact
        # posterior de Evaluar. `ejecutar_walkthrough` debe reconstruir
        # las 8 transiciones previas (PR-1A), nunca reejecutar
        # Diagnosticar/Remediar/Orientar/Tutorizar/Adaptar de nuevo.
        almacen_2 = AlmacenTransiciones(_URL, esquema=esquema)
        fact_posterior = (
            TransitionIntent(
                productor=Capacidad.EVALUAR,
                operacion="registrar_fact",
                argumentos={
                    "autor": Capacidad.EVALUAR,
                    "contenido": {"competencia": "COMP-2", "items_incorrectos": [3]},
                    "provenance": Provenance.de(OrigenProvenance.INSTRUMENTO, banco="v2"),
                },
                base=8,
            ),
        )
        final_2 = ejecutar_walkthrough(almacen_2, identidad, fact_posterior)
        estado_2, registros_2 = final_2["estado"], final_2["registros"]

        # Las 8 transiciones previas se reconstruyeron, no se repitieron:
        # mismos EntryId, mismo autor por transición — nunca una segunda
        # interpretación de Diagnosticar ni una segunda deliberación.
        assert estado_2.transicion == 11  # 8 reconstruidas + fact + validar + modelar
        assert len(registros_2) == 11
        assert registros_2[:8] == registros_1  # las primeras 8 no se re-persistieron
        assert verificar(identidad, registros_2) is None

        veredicto = next(
            c for c in estado_2.claims if c.autor is Capacidad.VALIDAR and c.vigencia.vigente
        )
        assert veredicto.asunto == f"efecto({decision_id})"
        assert veredicto.afirmacion["funciono"] is True

        modelado = next(
            c for c in estado_2.claims if c.autor is Capacidad.MODELAR and c.vigencia.vigente
        )
        assert veredicto.id in modelado.respaldo

        decision = estado_2.buscar(decision_id)
        assert decision.estado_validacion is EstadoValidacion.VALIDADA

        # Las OCHO capacidades, en la misma sesión — la coexistencia que
        # antes era estructuralmente imposible en un solo recorrido.
        autores_presentes = {c.autor for c in estado_2.claims} | {
            f.autor for f in estado_2.facts
        }
        assert autores_presentes == {
            Capacidad.EVALUAR,
            Capacidad.TUTORIZAR,
            Capacidad.DIAGNOSTICAR,
            Capacidad.REMEDIAR,
            Capacidad.ORIENTAR,
            Capacidad.ADAPTAR,
            Capacidad.VALIDAR,
            Capacidad.MODELAR,
        }

        # El recorrido causal completo sigue siendo navegable por
        # referencias tras la reanudación (P6, RFC-0003 §5) — no solo el
        # contenido coincide, la cadena de respaldo también sobrevive a
        # la reconstrucción.
        veredicto_desde_modelado = estado_2.buscar(modelado.respaldo[0])
        assert veredicto_desde_modelado.autor is Capacidad.VALIDAR
        decision_desde_veredicto = estado_2.buscar(veredicto.respaldo[0])
        assert decision_desde_veredicto.id == decision_id
        deliberacion = estado_2.buscar(decision.origen)
        claim_remediar = estado_2.buscar(deliberacion.resultado.aceptados[0])
        assert claim_remediar.autor is Capacidad.REMEDIAR
        claim_diagnostico = estado_2.buscar(claim_remediar.respaldo[0])
        assert claim_diagnostico.autor is Capacidad.DIAGNOSTICAR
        fact_original = estado_2.buscar(claim_diagnostico.respaldo[0])
        assert fact_original.autor is Capacidad.EVALUAR

    def test_identidad_distinta_no_reanuda_lanza_INV_2(self, esquema):
        # R5: la reanudación exige la identidad EXACTA de la sesión —
        # ya lo garantiza AlmacenTransiciones.abrir_sesion (PR-1A no lo
        # tocó); esta prueba solo confirma que ejecutar_walkthrough no lo
        # esconde ni lo captura.
        identidad = _identidad("s-m4-pr1b-identidad")
        almacen_1 = AlmacenTransiciones(_URL, esquema=esquema)
        almacen_1.preparar()
        ejecutar_walkthrough(almacen_1, identidad, _hecho_del_mundo())

        otra_identidad = dataclasses.replace(identidad, student_id="otro-estudiante")
        almacen_2 = AlmacenTransiciones(_URL, esquema=esquema)
        with pytest.raises(ValueError, match="INV-2"):
            ejecutar_walkthrough(almacen_2, otra_identidad, _hecho_del_mundo())


class TestM4_PR2_ProyeccionDeCierre:
    """M4 PR-2: T14 (Cierre) del Walkthrough-0001 — `salidas` como
    proyección pura (RFC-0003 §2, RFC-0005 §2), nunca como mutación del
    dominio. Engineering Review previa estableció, con evidencia, que
    `salidas` no pasa por el pipeline de reducers/eventos — se recalcula
    en cada invocación de `ejecutar_walkthrough`. Reusa el mismo patrón
    de dos invocaciones de `TestM4_PR1B_ReanudacionDeSesion` porque el
    criterio de aceptación central es la idempotencia frente a la
    reconstrucción, no solo el contenido de `salidas`."""

    def test_salidas_refleja_la_deuda_abierta_antes_de_validar(self, esquema):
        # Invocación #1: sin evidencia posterior, la decisión queda
        # pendiente — RFC-0005 §2 (3): esa deuda debe verse en `salidas`
        # sin que nada mute EstadoValidacion en el DecisionEntry mismo.
        identidad = _identidad("s-m4-pr2-deuda")
        almacen = AlmacenTransiciones(_URL, esquema=esquema)
        almacen.preparar()
        final = ejecutar_walkthrough(
            almacen, identidad, TestTutorizarIntegradoAlFlujo._hecho_del_mundo_completo()
        )
        estado = final["estado"]
        decision = estado.decisiones[0]

        assert estado.salidas is not None
        assert estado.salidas["modelo_propuesto"] == ()
        assert len(estado.salidas["deuda_abierta"]) == 1
        assert estado.salidas["deuda_abierta"][0]["decision_id"] == str(decision.id)
        # La decisión persistida NUNCA se muta para señalar la deuda —
        # sigue exactamente como el reducer la dejó.
        assert decision.estado_validacion is EstadoValidacion.PENDIENTE_DE_VALIDACION

    def test_salidas_refleja_el_modelo_propuesto_tras_validar_y_modelar(self, esquema):
        identidad = _identidad("s-m4-pr2-modelo")
        almacen_1 = AlmacenTransiciones(_URL, esquema=esquema)
        almacen_1.preparar()
        ejecutar_walkthrough(
            almacen_1, identidad, TestTutorizarIntegradoAlFlujo._hecho_del_mundo_completo()
        )

        almacen_2 = AlmacenTransiciones(_URL, esquema=esquema)
        fact_posterior = (
            TransitionIntent(
                productor=Capacidad.EVALUAR,
                operacion="registrar_fact",
                argumentos={
                    "autor": Capacidad.EVALUAR,
                    "contenido": {"competencia": "COMP-2", "items_incorrectos": [3]},
                    "provenance": Provenance.de(OrigenProvenance.INSTRUMENTO, banco="v2"),
                },
                base=8,
            ),
        )
        final_2 = ejecutar_walkthrough(almacen_2, identidad, fact_posterior)
        estado_2 = final_2["estado"]

        assert estado_2.salidas["deuda_abierta"] == ()
        assert estado_2.salidas["modelo_propuesto"] == (
            {"competencia": "COMP-2", "efecto_positivo": True},
        )
        assert estado_2.salidas["ruta_actualizada"] == "condicionales"
        assert estado_2.salidas["resumen_destilado"]["decisiones_validadas"] == 1

    def test_proyectar_salidas_es_idempotente_frente_a_la_reconstruccion(self, esquema):
        # Criterio de aceptación arquitectónico fijado en la Engineering
        # Review: proyectar_salidas(reconstruir(historia)) ==
        # proyectar_salidas(estado_final_original).
        identidad = _identidad("s-m4-pr2-idempotencia")
        almacen_1 = AlmacenTransiciones(_URL, esquema=esquema)
        almacen_1.preparar()
        ejecutar_walkthrough(
            almacen_1, identidad, TestTutorizarIntegradoAlFlujo._hecho_del_mundo_completo()
        )

        almacen_2 = AlmacenTransiciones(_URL, esquema=esquema)
        fact_posterior = (
            TransitionIntent(
                productor=Capacidad.EVALUAR,
                operacion="registrar_fact",
                argumentos={
                    "autor": Capacidad.EVALUAR,
                    "contenido": {"competencia": "COMP-2", "items_incorrectos": [3]},
                    "provenance": Provenance.de(OrigenProvenance.INSTRUMENTO, banco="v2"),
                },
                base=8,
            ),
        )
        final_2 = ejecutar_walkthrough(almacen_2, identidad, fact_posterior)
        estado_original = final_2["estado"]

        registros = almacen_2.leer(identidad.session_id)
        estado_reconstruido = reconstruir(
            identidad, contexto={"ruta": "condicionales"}, registros=registros
        )

        assert proyectar_salidas(estado_reconstruido) == proyectar_salidas(estado_original)
        # La igualdad no es casualidad: `estado_original.salidas` ya es
        # el resultado de proyectar_salidas sobre sí mismo (T14, dentro
        # de ejecutar_walkthrough) — confirmarlo explícitamente.
        assert estado_original.salidas == proyectar_salidas(estado_reconstruido)


class TestM4_PR5_ConsolidacionDeMemoria:
    """M4 PR-5: wiring de Consolidar (ADR-0008) en `ejecutar_walkthrough`
    — solo la escritura; Cargar queda para PR-6 (ADR-0008 §2.4)."""

    def test_cerrar_sesion_sin_almacen_memoria_es_error_de_programacion(self, esquema):
        # ADR-0004 E-2: precondición fuerte, nunca un None silencioso.
        almacen = AlmacenTransiciones(_URL, esquema=esquema)
        almacen.preparar()
        with pytest.raises(ValueError, match="almacen_memoria"):
            ejecutar_walkthrough(
                almacen,
                _identidad("s-pr5-sin-almacen"),
                _hecho_del_mundo(),
                cerrar_sesion=True,
            )

    def test_cerrar_sesion_consolida_exactamente_lo_que_salidas_contiene(self, esquema):
        identidad = _identidad("s-pr5-consolida")
        almacen_transiciones = AlmacenTransiciones(_URL, esquema=esquema)
        almacen_transiciones.preparar()
        almacen_memoria = AlmacenMemoria(_URL, esquema=esquema)
        almacen_memoria.preparar()

        final = ejecutar_walkthrough(
            almacen_transiciones,
            identidad,
            TestTutorizarIntegradoAlFlujo._hecho_del_mundo_completo(),
            cerrar_sesion=True,
            almacen_memoria=almacen_memoria,
        )

        version = almacen_memoria.cargar("maria")
        assert version is not None
        assert version.session_id == "s-pr5-consolida"
        # Consolidar consume EXACTAMENTE proyectar_salidas() (ADR-0008
        # §4) — sin transformación, ni siquiera de tipo (tuplas propias
        # de Python se leen de vuelta como listas desde jsonb, pero el
        # contenido debe coincidir campo a campo).
        assert version.catalogo["ruta_actualizada"] == final["estado"].salidas["ruta_actualizada"]
        assert version.catalogo["deuda_abierta"] == list(
            final["estado"].salidas["deuda_abierta"]
        )

    def test_sesion_reanudada_consolida_una_sola_vez_al_cerrar(self, esquema):
        # Combina PR-1B (reanudación) + PR-5 (consolidación): la
        # primera invocación NO cierra; solo la segunda, con evidencia
        # posterior, cierra y consolida — una única versión, no dos.
        identidad = _identidad("s-pr5-reanudada-cierra")
        almacen_1 = AlmacenTransiciones(_URL, esquema=esquema)
        almacen_1.preparar()
        almacen_memoria = AlmacenMemoria(_URL, esquema=esquema)
        almacen_memoria.preparar()

        ejecutar_walkthrough(
            almacen_1, identidad, TestTutorizarIntegradoAlFlujo._hecho_del_mundo_completo()
        )
        assert almacen_memoria.cargar("maria") is None  # invoke#1 no cerró

        almacen_2 = AlmacenTransiciones(_URL, esquema=esquema)
        fact_posterior = (
            TransitionIntent(
                productor=Capacidad.EVALUAR,
                operacion="registrar_fact",
                argumentos={
                    "autor": Capacidad.EVALUAR,
                    "contenido": {"competencia": "COMP-2", "items_incorrectos": [3]},
                    "provenance": Provenance.de(OrigenProvenance.INSTRUMENTO, banco="v2"),
                },
                base=8,
            ),
        )
        ejecutar_walkthrough(
            almacen_2,
            identidad,
            fact_posterior,
            cerrar_sesion=True,
            almacen_memoria=almacen_memoria,
        )

        version = almacen_memoria.cargar("maria")
        assert version is not None
        assert version.catalogo["modelo_propuesto"] == [
            {"competencia": "COMP-2", "efecto_positivo": True}
        ]

    def test_cerrar_dos_veces_la_misma_sesion_falla_sin_generar_segunda_version(
        self, esquema
    ):
        identidad = _identidad("s-pr5-doble-cierre")
        almacen = AlmacenTransiciones(_URL, esquema=esquema)
        almacen.preparar()
        almacen_memoria = AlmacenMemoria(_URL, esquema=esquema)
        almacen_memoria.preparar()

        ejecutar_walkthrough(
            almacen,
            identidad,
            _hecho_del_mundo(),
            cerrar_sesion=True,
            almacen_memoria=almacen_memoria,
        )
        almacen_repetido = AlmacenTransiciones(_URL, esquema=esquema)
        with pytest.raises(ValueError, match="ya fue consolidada"):
            ejecutar_walkthrough(
                almacen_repetido,
                identidad,
                (),
                cerrar_sesion=True,
                almacen_memoria=almacen_memoria,
            )

        version = almacen_memoria.cargar("maria")
        assert version is not None
        assert version.session_id == "s-pr5-doble-cierre"  # sigue siendo v1, no v2
