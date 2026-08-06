"""Épica 2 — `runtime_bridge.registrar_evidencia_evaluacion`: el primer
puente real entre evidencia de evaluación de la plataforma y una
decisión del runtime LangGraph (ADR-0010).

Sin dobles (ADR-0005 §3): PostgreSQL real, LangGraph real.
"""

from __future__ import annotations

import os

import psycopg2
import pytest

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
    not _pg_disponible(), reason="PostgreSQL no disponible (ADR-0005 §3 exige BD real)"
)


@pytest.fixture(autouse=True)
def _runtime_env(monkeypatch):
    esquema = f"runtime_bridge_test_{os.getpid()}"
    monkeypatch.setenv("RUNTIME_DATABASE_URL", _URL)
    monkeypatch.setenv("RUNTIME_DATABASE_SCHEMA", esquema)
    from app.services.runtime_connection import almacenes

    almacenes.cache_clear()
    yield
    with psycopg2.connect(_URL) as conexion, conexion.cursor() as cursor:
        cursor.execute(f"DROP SCHEMA IF EXISTS {esquema} CASCADE")
    almacenes.cache_clear()


def test_evidencia_de_evaluacion_produce_una_entrega_de_adaptar():
    from app.services.runtime_bridge import registrar_evidencia_evaluacion
    from runtime.boundary import Entrega

    entrega = registrar_evidencia_evaluacion(
        student_id="maria",
        course_id="fundamentos-programacion",
        titulo_modulo="Condicionales",
        items_incorrectos=[0, 2, 3],
    )
    assert isinstance(entrega, Entrega)
    assert entrega.asunto is not None
    assert entrega.diseno is not None


def test_competencia_registrada_es_el_slug_del_modulo_no_comp_n():
    from app.services.runtime_bridge import registrar_evidencia_evaluacion
    from runtime.engine.checkpoint import reconstruir
    from runtime.kernel.state.state import Identidad
    from app.services.runtime_connection import (
        SPEC_VERSION,
        VERSION_BANCO,
        VERSION_POLITICA,
        almacenes,
    )

    registrar_evidencia_evaluacion(
        student_id="maria",
        course_id="fundamentos-programacion",
        titulo_modulo="Bucles y Repetición",
        items_incorrectos=[1],
    )

    almacen, _ = almacenes()
    identidad = Identidad(
        session_id="curso:fundamentos-programacion:estudiante:maria",
        student_id="maria",
        version_student_model="0",
        version_banco=VERSION_BANCO,
        version_politica=VERSION_POLITICA,
        spec_version=SPEC_VERSION,
    )
    registros = almacen.leer(identidad.session_id)
    estado = reconstruir(identidad, {}, registros)
    fact = next(f for f in estado.facts if "items_incorrectos" in f.contenido)
    assert fact.contenido["competencia"] == "bucles-y-repeticion"


def test_dos_modulos_del_mismo_curso_comparten_la_misma_sesion_de_runtime():
    # session_id determinista por estudiante+curso (no por evaluación):
    # el runtime acumula evidencia de varios módulos en la misma sesión.
    from app.services.runtime_bridge import registrar_evidencia_evaluacion

    registrar_evidencia_evaluacion(
        student_id="juan", course_id="curso-x", titulo_modulo="Funciones",
        items_incorrectos=[],
    )
    entrega_2 = registrar_evidencia_evaluacion(
        student_id="juan", course_id="curso-x", titulo_modulo="Arreglos",
        items_incorrectos=[0, 1],
    )
    # No lanza INV-2: la segunda llamada reanuda la misma identidad de
    # sesión que la primera (mismo estudiante, mismo curso).
    assert entrega_2 is not None


def test_consultar_decision_vigente_sin_evidencia_es_entrega_vacia():
    from app.services.runtime_bridge import consultar_decision_vigente
    from runtime.boundary import Entrega

    entrega = consultar_decision_vigente(student_id="nueva", course_id="curso-x")
    assert entrega == Entrega(asunto=None, diseno=None)


def test_consultar_decision_vigente_refleja_la_ultima_evidencia_registrada():
    from app.services.runtime_bridge import (
        consultar_decision_vigente,
        registrar_evidencia_evaluacion,
    )

    registrar_evidencia_evaluacion(
        student_id="pedro", course_id="curso-y", titulo_modulo="Recursividad",
        items_incorrectos=[0, 1, 2],
    )
    entrega = consultar_decision_vigente(student_id="pedro", course_id="curso-y")
    assert entrega.asunto is not None
    assert entrega.diseno is not None


def test_consultar_decision_vigente_no_registra_ningun_hecho():
    from app.services.runtime_bridge import consultar_decision_vigente
    from app.services.runtime_connection import (
        SPEC_VERSION,
        VERSION_BANCO,
        VERSION_POLITICA,
        almacenes,
    )

    consultar_decision_vigente(student_id="ana", course_id="curso-z")
    consultar_decision_vigente(student_id="ana", course_id="curso-z")
    almacen, _ = almacenes()
    assert almacen.leer("curso:curso-z:estudiante:ana") == ()


# ── Derivación compartida de la Entrega (una traducción, N consumidores) ──


def test_derivaciones_compartidas_de_la_entrega():
    from app.services.runtime_bridge import (
        asunto_de_modalidad,
        bloom_target_desde_entrega,
        modalidad_desde_entrega,
    )
    from runtime.boundary import Entrega

    asunto = asunto_de_modalidad("Bucles y Repetición")
    assert asunto == "modalidad(bucles-y-repeticion)"

    reforzar = Entrega(asunto=asunto, diseno={"modalidad": "visual", "profundidad": "fundamentos"})
    avanzar = Entrega(asunto=asunto, diseno={"modalidad": "mixta", "profundidad": "aplicacion"})
    otro_modulo = Entrega(asunto="modalidad(condicionales)", diseno={"modalidad": "visual", "profundidad": "fundamentos"})
    sin_decision = Entrega(asunto=None, diseno=None)

    # fundamentos nunca pide más que Comprender; aplicacion conserva
    assert bloom_target_desde_entrega(4, asunto, reforzar) == 2
    assert bloom_target_desde_entrega(4, asunto, avanzar) == 4
    # decisión de OTRA competencia no gobierna este módulo (ADR-0010)
    assert bloom_target_desde_entrega(4, asunto, otro_modulo) == 4
    assert bloom_target_desde_entrega(None, asunto, sin_decision) == 3

    assert modalidad_desde_entrega(asunto, reforzar) == "visual"
    assert modalidad_desde_entrega(asunto, otro_modulo) is None
    assert modalidad_desde_entrega(asunto, sin_decision) is None


# ── Estrategia de contenido (adaptive-decision) sobre Runtime ────────


def test_decision_adaptativa_sin_evidencia_es_none():
    from app.services.runtime_bridge import decision_adaptativa

    assert decision_adaptativa(student_id="nadie", course_id="curso-ad0") is None


def test_decision_adaptativa_deriva_de_la_entrega_del_runtime():
    """Con evidencia débil (2/3 incorrectos → 'reforzar'), la estrategia
    sale de la decisión del runtime: modalidad visual gobierna el orden
    y 'fundamentos' empuja teoría/ejemplo al frente; la competencia
    interpretada como no dominada queda como énfasis — cero tablas VARK
    involucradas."""
    from app.services.runtime_bridge import (
        decision_adaptativa,
        registrar_evidencia_evaluacion,
    )

    registrar_evidencia_evaluacion(
        student_id="rocio",
        course_id="curso-ad1",
        titulo_modulo="Bucles",
        items_incorrectos=[0, 2],
        items_totales=3,
    )
    decision = decision_adaptativa(student_id="rocio", course_id="curso-ad1")
    assert decision is not None
    assert decision["modality_label"] == "visual"  # accion "reforzar"
    # fundamentos: theory/example al frente del orden visual
    assert decision["content_order"][:2] == ["theory", "example"]
    assert set(decision["content_order"]) == {
        "theory", "example", "diagram", "video", "exercise", "simulation", "game",
    }
    assert decision["emphasis_topics"] == ["bucles"]
    assert decision["emphasis_topic_labels"] == ["Bucles"]
    assert decision["skip_hint_topics"] == []


def test_decision_adaptativa_competencia_dominada_va_a_skip_hint():
    from app.services.runtime_bridge import (
        decision_adaptativa,
        registrar_evidencia_evaluacion,
    )

    registrar_evidencia_evaluacion(
        student_id="rocio",
        course_id="curso-ad2",
        titulo_modulo="Variables",
        items_incorrectos=[],
        items_totales=4,
    )
    decision = decision_adaptativa(student_id="rocio", course_id="curso-ad2")
    assert decision is not None
    assert decision["skip_hint_topics"] == ["variables"]
    # Aditivo (Sesión UX/UI 2026-08-05, H1): `skip_hint_topics` se
    # mantiene crudo (lo usa Dashboard.tsx para deduplicar contra
    # `competencies`), `skip_hint_topic_labels` es la vista traducida.
    assert decision["skip_hint_topic_labels"] == ["Variables"]


def test_decision_adaptativa_traduce_slugs_reales_del_diagnostico_inicial():
    """`PRIOR_KNOWLEDGE_TOPIC_MAP` (student_service.py) es la fuente real
    de `titulo_modulo` para el diagnóstico inicial — la única evidencia
    que TODO estudiante real genera. Sus slugs en inglés ("arrays",
    "algorithms") deben traducirse igual que los de `ProgrammingConcept`
    (Sesión UX/UI 2026-08-05, H1) — sin esto, "Arrays"/"Algorithms"
    aparecían crudos en el dashboard y la ruta adaptativa."""
    from app.services.runtime_bridge import (
        decision_adaptativa,
        registrar_evidencia_evaluacion,
    )

    registrar_evidencia_evaluacion(
        student_id="camila",
        course_id="curso-ad2b",
        titulo_modulo="arrays",
        items_incorrectos=[0, 1, 2],
        items_totales=3,
    )
    registrar_evidencia_evaluacion(
        student_id="camila",
        course_id="curso-ad2b",
        titulo_modulo="algorithms",
        items_incorrectos=[],
        items_totales=3,
    )
    decision = decision_adaptativa(student_id="camila", course_id="curso-ad2b")
    assert decision is not None
    assert decision["emphasis_topics"] == ["arrays"]
    assert decision["emphasis_topic_labels"] == ["Arreglos"]
    assert decision["skip_hint_topics"] == ["algorithms"]
    assert decision["skip_hint_topic_labels"] == ["Algoritmos"]


def test_decision_adaptativa_excluye_competencias_del_pretest():
    """El pre-test (knowledge_test_service._evidencia_por_competencia)
    registra evidencia con `titulo_modulo=COMPETENCY_LABELS[topic]` — p.
    ej. "Comprensión del problema", una dimensión cognitiva COMP_0..
    COMP_5, nunca un tema real de Fundamentos de Programación. Mezclarla
    con un tema real ("Loops") en `emphasis_topics`/`skip_hint_topics`
    sugiere al estudiante que el sistema no distingue su propio curso de
    una taxonomía genérica (hallazgo E2E jul 2026). Diagnosticar sigue
    interpretando ambas familias de asunto igual — solo la vista que
    arma `decision_adaptativa` para el estudiante filtra la del pre-test."""
    from app.data.knowledge_test_bank import COMPETENCY_LABELS
    from app.services.runtime_bridge import (
        decision_adaptativa,
        registrar_evidencia_evaluacion,
    )

    registrar_evidencia_evaluacion(
        student_id="karla",
        course_id="curso-ad3",
        titulo_modulo=COMPETENCY_LABELS["comp_0_problema"],  # "Comprensión del problema"
        items_incorrectos=[0],
        items_totales=2,
    )
    registrar_evidencia_evaluacion(
        student_id="karla",
        course_id="curso-ad3",
        titulo_modulo="Loops",
        items_incorrectos=[0, 1],
        items_totales=3,
    )
    decision = decision_adaptativa(student_id="karla", course_id="curso-ad3")
    assert decision is not None
    assert decision["emphasis_topics"] == ["loops"]
    assert "comprension-del-problema" not in decision["emphasis_topics"]
    assert "comprension-del-problema" not in decision["skip_hint_topics"]


# ── Tutor sobre Runtime ──────────────────────────────────────────────


def test_contexto_tutor_sin_evidencia_es_vacio_y_no_registra_nada():
    from app.services.runtime_bridge import contexto_pedagogico_tutor
    from app.services.runtime_connection import almacenes

    contexto = contexto_pedagogico_tutor(student_id="lucia", course_id="curso-t")
    assert contexto == {
        "asunto": None,
        "diseno": None,
        "senales": [],
        "memoria": None,
    }
    almacen, _ = almacenes()
    assert almacen.leer("curso:curso-t:estudiante:lucia") == ()


def test_items_totales_activa_la_senal_de_tutorizar_y_el_contexto_la_expone():
    """RFC-0002 R4: con el total de ítems, Tutorizar clasifica la señal
    conductual (2 de 3 incorrectos → confusión) — y el contexto del
    tutor la refleja junto a la adaptación vigente."""
    from app.services.runtime_bridge import (
        contexto_pedagogico_tutor,
        registrar_evidencia_evaluacion,
    )

    registrar_evidencia_evaluacion(
        student_id="lucia",
        course_id="curso-t2",
        titulo_modulo="Condicionales",
        items_incorrectos=[0, 2],
        items_totales=3,
    )
    contexto = contexto_pedagogico_tutor(student_id="lucia", course_id="curso-t2")
    assert contexto["asunto"] is not None
    assert contexto["diseno"] is not None
    assert "modalidad" in contexto["diseno"]
    assert contexto["senales"] == ["confusion"]


def test_registrar_pregunta_tutor_entra_como_interaccion_humana():
    """La pregunta del estudiante es evidencia de sesión (E2, provenance
    humano) — el runtime la ve; el chat de la plataforma solo redacta."""
    from app.services.runtime_bridge import registrar_pregunta_tutor
    from app.services.runtime_connection import (
        SPEC_VERSION,
        VERSION_BANCO,
        VERSION_POLITICA,
        almacenes,
    )
    from runtime.engine.checkpoint import reconstruir
    from runtime.kernel.state.entries import OrigenProvenance
    from runtime.kernel.state.state import Identidad

    registrar_pregunta_tutor(
        student_id="lucia",
        course_id="curso-t3",
        pregunta="¿Por qué mi bucle while no termina nunca?",
    )

    almacen, _ = almacenes()
    identidad = Identidad(
        session_id="curso:curso-t3:estudiante:lucia",
        student_id="lucia",
        version_student_model="0",
        version_banco=VERSION_BANCO,
        version_politica=VERSION_POLITICA,
        spec_version=SPEC_VERSION,
    )
    estado = reconstruir(identidad, {}, almacen.leer(identidad.session_id))
    pregunta = next(f for f in estado.facts if "pregunta" in f.contenido)
    assert pregunta.contenido["interaccion"] == "pregunta-tutor"
    assert "while" in pregunta.contenido["pregunta"]
    assert pregunta.provenance.origen is OrigenProvenance.HUMANO


def test_la_pregunta_no_altera_la_adaptacion_vigente():
    """El chat observa y aporta evidencia, pero no dispara una nueva
    adaptación por sí solo: la Entrega vigente antes y después de la
    pregunta es la misma."""
    from app.services.runtime_bridge import (
        consultar_decision_vigente,
        registrar_evidencia_evaluacion,
        registrar_pregunta_tutor,
    )

    registrar_evidencia_evaluacion(
        student_id="lucia",
        course_id="curso-t4",
        titulo_modulo="Funciones",
        items_incorrectos=[1],
        items_totales=4,
    )
    antes = consultar_decision_vigente(student_id="lucia", course_id="curso-t4")
    registrar_pregunta_tutor(
        student_id="lucia", course_id="curso-t4", pregunta="¿Qué es una función?"
    )
    despues = consultar_decision_vigente(student_id="lucia", course_id="curso-t4")
    assert antes == despues


# ── El diagnóstico inicial entra al Runtime (cold-start retirado) ────


def test_diagnostico_produce_el_mapa_completo():
    """Traducción fiel de escala (Likert k/5 → (5−k) incorrectos de 5)
    y mapa COMPLETO (2026-07-13): cada tema del diagnóstico produce su
    interpretación — el débil como énfasis, el fuerte como dominado —
    en la misma decisión adaptativa; la sección VARK (q9+) no es
    evidencia de tema y se ignora."""
    from app.services.runtime_bridge import decision_adaptativa
    from app.services.student_service import _registrar_diagnostico_en_runtime

    _registrar_diagnostico_en_runtime(
        student_id="diag-1",
        course_id="curso-diag",
        answers={"1": 2, "2": 5, "9": 4},  # algorithms 2/5, variables 5/5
    )
    decision = decision_adaptativa(student_id="diag-1", course_id="curso-diag")
    assert decision is not None
    assert decision["emphasis_topics"] == ["algorithms"]
    assert decision["skip_hint_topics"] == ["variables"]
    assert decision["modality_label"] == "visual"  # decisión real: reforzar


def test_diagnostico_umbral_4_sobrevive_la_traduccion():
    """El umbral del instrumento (score>=4 = dominado) bajo scoring-v1:
    4/5 → 1 error → dominada; 3/5 → 2 errores → no dominada — ambos
    interpretados en el mapa."""
    from app.services.runtime_bridge import decision_adaptativa
    from app.services.student_service import _registrar_diagnostico_en_runtime

    _registrar_diagnostico_en_runtime(
        student_id="diag-2", course_id="curso-diag2", answers={"6": 4, "7": 3},
    )
    decision = decision_adaptativa(student_id="diag-2", course_id="curso-diag2")
    assert decision["skip_hint_topics"] == ["loops"]      # 4/5
    assert decision["emphasis_topics"] == ["arrays"]      # 3/5


def test_sin_evidencia_alguna_decision_neutra():
    from app.services.runtime_bridge import decision_adaptativa_neutra

    neutra = decision_adaptativa_neutra()
    assert neutra["modality_label"] == "mixta"
    assert neutra["emphasis_topics"] == []
    assert neutra["content_order"][0] == "theory"
