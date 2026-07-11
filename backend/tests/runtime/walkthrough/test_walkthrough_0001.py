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


class TestCierreM2:
    """Cierre de M2 (post PR-5): las ocho capacidades están cableadas al
    grafo. Esta suite congela esa fotografía antes de PR-6.

    Hallazgo de esta pasada, no un defecto: bajo el diseño actual,
    `ejecutar_walkthrough` es una única invocación síncrona sin
    reanudación (P10/RFC-0008 todavía no existen como mecanismo). Eso
    hace que Validar (que exige un fact de Evaluar *posterior*, en
    transicion, a la decisión) NUNCA pueda unirse al mismo recorrido
    natural que Tutorizar (que exige que la decisión *todavía* no
    exista). Ambas guardias son correctas por separado — el límite es
    estructural, no un bug de PR-1..5. Por eso el cierre usa DOS tests
    complementarios en vez de uno solo: el recorrido natural (6
    capacidades + kernel, en un solo `invoke`) y la cadena causal
    completa (las 8, con evidencia pre-sembrada — misma técnica de
    PR-2/3)."""

    def test_orden_natural_de_las_capacidades_en_un_solo_recorrido(self, esquema):
        almacen = AlmacenTransiciones(_URL, esquema=esquema)
        almacen.preparar()
        final = ejecutar_walkthrough(
            almacen,
            _identidad("s-cierre-m2-natural"),
            TestTutorizarIntegradoAlFlujo._hecho_del_mundo_completo(),
        )
        estado, registros = final["estado"], final["registros"]

        entradas = (
            [(f.id.transicion, "fact", f.autor) for f in estado.facts]
            + [(c.id.transicion, "claim", c.autor) for c in estado.claims]
            + [(d.id.transicion, "delib", None) for d in estado.deliberaciones]
            + [(d.id.transicion, "decision", None) for d in estado.decisiones]
        )
        entradas.sort(key=lambda e: e[0])
        orden_observado = [(kind, autor) for _, kind, autor in entradas]

        # El orden ES el programa pedagógico (enrutar, RFC-0004 §4):
        # Tutorizar corre antes que exista ninguna decisión; Adaptar,
        # apenas existe. Validar/Modelar no aparecen — ver docstring.
        assert orden_observado == [
            ("fact", Capacidad.EVALUAR),
            ("fact", Capacidad.TUTORIZAR),
            ("claim", Capacidad.DIAGNOSTICAR),
            ("claim", Capacidad.REMEDIAR),
            ("claim", Capacidad.ORIENTAR),
            ("delib", None),
            ("decision", None),
            ("claim", Capacidad.ADAPTAR),
        ]
        assert not any(c.autor is Capacidad.VALIDAR for c in estado.claims)
        assert not any(c.autor is Capacidad.MODELAR for c in estado.claims)

        # P14 + RFC-0008: un registro persistido por transición aplicada,
        # cadena de hashes verificable, lo persistido == lo ejecutado.
        assert len(registros) == estado.transicion == 8
        assert almacen.leer("s-cierre-m2-natural") == registros
        assert verificar(_identidad("s-cierre-m2-natural"), registros) is None

    def test_cadena_causal_completa_recorre_de_modelar_al_fact_original_sin_saltos(
        self, esquema
    ):
        almacen = AlmacenTransiciones(_URL, esquema=esquema)
        almacen.preparar()
        hechos, decision_id = TestValidarIntegradoAlFlujo._hechos_con_evidencia_completa()
        final = ejecutar_walkthrough(
            almacen, _identidad("s-cierre-m2-causal"), hechos
        )
        estado, registros = final["estado"], final["registros"]

        # El recorrido causal es tipado y navegable por referencias (P6,
        # RFC-0003 §5) — cada paso se resuelve con estado.buscar(), sin
        # adivinar ningún eslabón: Modelar → Validar → Decisión → (claim
        # de Remediar) → (claim de Diagnosticar) → fact original.
        modelado = next(
            c for c in estado.claims if c.autor is Capacidad.MODELAR and c.vigencia.vigente
        )
        veredicto = estado.buscar(modelado.respaldo[0])
        assert veredicto.autor is Capacidad.VALIDAR

        decision = estado.buscar(decision_id)
        assert decision_id in veredicto.respaldo
        assert decision.id == decision_id

        claim_remediar = estado.buscar(decision.origen)
        assert claim_remediar.autor is Capacidad.REMEDIAR

        claim_diagnostico = estado.buscar(claim_remediar.respaldo[0])
        assert claim_diagnostico.autor is Capacidad.DIAGNOSTICAR

        fact_original = estado.buscar(claim_diagnostico.respaldo[0])
        assert fact_original.autor is Capacidad.EVALUAR
        assert fact_original.contenido["competencia"] == "COMP-2"

        # Este fixture (sin rival de Orientar, sin items_totales) cubre
        # Evaluar/Diagnosticar/Remediar/Adaptar/Validar/Modelar — no
        # Orientar ni Tutorizar, que sí quedaron probados en
        # test_orden_natural_de_las_capacidades_en_un_solo_recorrido. La
        # UNIÓN de ambos tests de esta clase cubre las 8 (ver docstring).
        autores_presentes = {c.autor for c in estado.claims} | {
            f.autor for f in estado.facts
        }
        assert autores_presentes == {
            Capacidad.EVALUAR,
            Capacidad.DIAGNOSTICAR,
            Capacidad.REMEDIAR,
            Capacidad.ADAPTAR,
            Capacidad.VALIDAR,
            Capacidad.MODELAR,
        }

        assert len(registros) == estado.transicion
        assert almacen.leer("s-cierre-m2-causal") == registros
        assert verificar(_identidad("s-cierre-m2-causal"), registros) is None
