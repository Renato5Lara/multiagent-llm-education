"""Épica 1 — extremo a extremo: HTTP → FastAPI → Boundary → LangGraph →
Postgres → respuesta, sin pasar por BaseAgent (ADR-0009, CLAUDE.md
actualización 2026-07-12).

Usa el `client`/`estudiante_user` de tests/conftest.py (BD de la
plataforma en SQLite in-memory) — pero `/api/runtime/*` habla con
Postgres real vía `runtime.boundary`, igual que sus propias suites en
tests/runtime/boundary/. Requiere PostgreSQL real (ADR-0005 §3).

`aget_current_estudiante` depende de `aget_db` (`AsyncSession` sobre el
Postgres real de la plataforma) — un dependency distinto del `get_db`
(sync) que `client` ya sobreescribe hacia SQLite; ningún test existente
en el repo ejercita todavía una ruta autenticada async contra el
`client` compartido (gap preexistente, fuera del alcance de esta
Épica). Se sortea igual que se sortearía en cualquier ruta async:
sobreescribiendo `aget_current_estudiante` directamente con el usuario
de prueba, sin tocar la infraestructura compartida de tests/conftest.py.
"""

from __future__ import annotations

import os

import psycopg2
import pytest

from app.api.deps import aget_current_docente, aget_current_estudiante
from app.api.routes.runtime import aget_current_estudiante_o_docente
from app.main import app

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
    # Mismo Postgres que el resto de tests/runtime/, esquema propio y
    # descartable — no comparte tablas con la plataforma (ADR-0009 §2.4).
    monkeypatch.setenv("RUNTIME_DATABASE_URL", _URL)
    monkeypatch.setenv("RUNTIME_DATABASE_SCHEMA", f"runtime_http_test_{os.getpid()}")
    from app.services.runtime_connection import almacenes

    almacenes.cache_clear()
    yield
    esquema = os.environ["RUNTIME_DATABASE_SCHEMA"]
    with psycopg2.connect(_URL) as conexion, conexion.cursor() as cursor:
        cursor.execute(f"DROP SCHEMA IF EXISTS {esquema} CASCADE")
    almacenes.cache_clear()


@pytest.fixture
def autenticado(client, estudiante_user):
    app.dependency_overrides[aget_current_estudiante] = lambda: estudiante_user
    app.dependency_overrides[aget_current_estudiante_o_docente] = lambda: estudiante_user
    yield estudiante_user
    app.dependency_overrides.pop(aget_current_estudiante, None)
    app.dependency_overrides.pop(aget_current_estudiante_o_docente, None)


@pytest.fixture
def autenticado_docente(client, docente_user):
    app.dependency_overrides[aget_current_docente] = lambda: docente_user
    app.dependency_overrides[aget_current_estudiante_o_docente] = lambda: docente_user
    yield docente_user
    app.dependency_overrides.pop(aget_current_docente, None)
    app.dependency_overrides.pop(aget_current_estudiante_o_docente, None)


def test_recorrido_completo_http_hasta_una_entrega_de_adaptar(client, autenticado):
    abierta = client.post("/api/runtime/sessions", json={"session_id": "s-http-e2e"})
    assert abierta.status_code == 200, abierta.text
    identidad = abierta.json()
    assert identidad["session_id"] == "s-http-e2e"
    assert identidad["student_id"] == autenticado.id
    assert identidad["version_student_model"] == "0"

    entregado = client.post(
        "/api/runtime/hechos",
        json={
            "identidad": identidad,
            "contenido": {"competencia": "COMP-2", "items_incorrectos": [3, 4, 8]},
            "origen": "instrumento",
        },
    )
    assert entregado.status_code == 200, entregado.text
    entrega = entregado.json()
    assert entrega["asunto"] is not None
    assert entrega["diseno"] is not None


def test_traza_refleja_los_eventos_reales_via_http(client, autenticado):
    abierta = client.post("/api/runtime/sessions", json={"session_id": "s-http-traza"})
    identidad = abierta.json()

    client.post(
        "/api/runtime/hechos",
        json={
            "identidad": identidad,
            "contenido": {"competencia": "COMP-2", "items_incorrectos": [3, 4, 8]},
            "origen": "instrumento",
        },
    )

    traza = client.get("/api/runtime/sessions/s-http-traza/traza")
    assert traza.status_code == 200, traza.text
    pasos = traza.json()
    assert len(pasos) > 0
    assert pasos[0]["transicion"] == 1
    assert pasos[0]["eventos"][0]["tipo"] == "FactRegistrado"
    # El Platform Boundary autora facts con autor="boundary" (regla 1:
    # traduce, no interpreta ni reatribuye a una capacidad del dominio).
    assert pasos[0]["eventos"][0]["datos"]["autor"] == "boundary"


def test_traza_de_sesion_ajena_es_rechazada(client, autenticado):
    client.post("/api/runtime/sessions", json={"session_id": "s-http-traza-ajena"})

    class _OtroUsuario:
        id = "otro-estudiante-cualquiera"
        role = "estudiante"

    app.dependency_overrides[aget_current_estudiante_o_docente] = lambda: _OtroUsuario()
    try:
        resp = client.get("/api/runtime/sessions/s-http-traza-ajena/traza")
    finally:
        app.dependency_overrides[aget_current_estudiante_o_docente] = lambda: autenticado

    assert resp.status_code == 403


def test_estado_refleja_facts_y_claims_via_http(client, autenticado):
    abierta = client.post("/api/runtime/sessions", json={"session_id": "s-http-estado"})
    identidad = abierta.json()

    client.post(
        "/api/runtime/hechos",
        json={
            "identidad": identidad,
            "contenido": {"competencia": "COMP-2", "items_incorrectos": [3, 4, 8]},
            "origen": "instrumento",
        },
    )

    resp = client.get("/api/runtime/sessions/s-http-estado/estado")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert len(body["facts"]) == 1
    assert body["facts"][0]["autor"] == "boundary"
    assert len(body["claims"]) > 0
    assert body["transicion"] == len(body["facts"]) + len(body["claims"]) + len(
        body["deliberaciones"]
    ) + len(body["decisiones"])


def test_memoria_es_none_para_estudiante_sin_historia(client, autenticado):
    client.post("/api/runtime/sessions", json={"session_id": "s-http-memoria-nueva"})
    resp = client.get("/api/runtime/sessions/s-http-memoria-nueva/memoria")
    assert resp.status_code == 200, resp.text
    assert resp.json() is None


def test_memoria_lee_la_version_consolidada_por_una_sesion_previa(client, autenticado):
    abierta = client.post("/api/runtime/sessions", json={"session_id": "s-http-memoria-previa"})
    identidad = abierta.json()

    client.post(
        "/api/runtime/hechos",
        json={
            "identidad": identidad,
            "contenido": {"competencia": "COMP-2", "items_incorrectos": [3, 4, 8]},
            "origen": "instrumento",
            "cerrar_sesion": True,
        },
    )

    client.post("/api/runtime/sessions", json={"session_id": "s-http-memoria-siguiente"})
    resp = client.get("/api/runtime/sessions/s-http-memoria-siguiente/memoria")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body is not None
    assert body["session_id"] == "s-http-memoria-previa"
    assert body["catalogo"]


def test_replay_expone_el_estado_acumulado_via_http(client, autenticado):
    abierta = client.post("/api/runtime/sessions", json={"session_id": "s-http-replay"})
    identidad = abierta.json()

    client.post(
        "/api/runtime/hechos",
        json={
            "identidad": identidad,
            "contenido": {"competencia": "COMP-2", "items_incorrectos": [3, 4, 8]},
            "origen": "instrumento",
        },
    )

    resp = client.get("/api/runtime/sessions/s-http-replay/replay")
    assert resp.status_code == 200, resp.text
    pasos = resp.json()
    assert len(pasos) > 0
    assert pasos[0]["transicion"] == 1
    assert len(pasos[0]["estado"]["facts"]) == 1
    assert len(pasos[0]["estado"]["claims"]) == 0

    ultimo = pasos[-1]
    estado_final = client.get("/api/runtime/sessions/s-http-replay/estado").json()
    assert ultimo["estado"] == estado_final

    # Acumulativo: el conteo de entradas nunca decrece paso a paso.
    conteos = [
        len(p["estado"]["facts"]) + len(p["estado"]["claims"])
        + len(p["estado"]["deliberaciones"]) + len(p["estado"]["decisiones"])
        for p in pasos
    ]
    assert conteos == sorted(conteos)


def test_estado_memoria_y_replay_de_sesion_ajena_son_rechazados(client, autenticado):
    client.post("/api/runtime/sessions", json={"session_id": "s-http-ajena-2"})

    class _OtroUsuario:
        id = "otro-estudiante-cualquiera"
        role = "estudiante"

    app.dependency_overrides[aget_current_estudiante_o_docente] = lambda: _OtroUsuario()
    try:
        assert client.get("/api/runtime/sessions/s-http-ajena-2/estado").status_code == 403
        assert client.get("/api/runtime/sessions/s-http-ajena-2/memoria").status_code == 403
        assert client.get("/api/runtime/sessions/s-http-ajena-2/replay").status_code == 403
    finally:
        app.dependency_overrides[aget_current_estudiante_o_docente] = lambda: autenticado


def test_identidad_de_otro_estudiante_es_rechazada(client, autenticado):
    abierta = client.post("/api/runtime/sessions", json={"session_id": "s-http-ajena"})
    identidad_ajena = dict(abierta.json(), student_id="otro-estudiante-cualquiera")

    resp = client.post(
        "/api/runtime/hechos",
        json={
            "identidad": identidad_ajena,
            "contenido": {"competencia": "COMP-2", "items_incorrectos": []},
            "origen": "instrumento",
        },
    )
    assert resp.status_code == 403


def test_sin_autenticacion_es_rechazado(client):
    resp = client.post("/api/runtime/sessions", json={"session_id": "s-sin-auth"})
    assert resp.status_code in (401, 403)


def test_docente_puede_leer_estado_de_sesion_ajena(client, autenticado, autenticado_docente):
    # El docente NO es el dueño de la sesión (es el estudiante), y aun
    # así puede leer las 4 surfaces S3 — RFC-0009 §1: es el humano del
    # loop, autoridad, no un participante con ámbito por estudiante.
    client.post("/api/runtime/sessions", json={"session_id": "s-http-docente-lee"})

    for ruta in ("traza", "estado", "memoria", "replay"):
        resp = client.get(f"/api/runtime/sessions/s-http-docente-lee/{ruta}")
        assert resp.status_code == 200, f"{ruta}: {resp.text}"


def test_hecho_docente_via_http(client, autenticado, autenticado_docente):
    client.post("/api/runtime/sessions", json={"session_id": "s-http-hitl-docente"})

    resp = client.post(
        "/api/runtime/sessions/s-http-hitl-docente/hechos-docente",
        json={
            "contenido": {"competencia": "COMP-2", "items_incorrectos": [3, 4, 8]},
            "human_reason": "observé confusión persistente en clase",
        },
    )
    assert resp.status_code == 200, resp.text

    traza = client.get("/api/runtime/sessions/s-http-hitl-docente/traza")
    primer_paso = traza.json()[0]
    assert primer_paso["eventos"][0]["tipo"] == "FactRegistrado"
    assert primer_paso["eventos"][0]["datos"]["origen"] == "humano"


def test_hecho_docente_de_sesion_inexistente_es_404(client, autenticado_docente):
    resp = client.post(
        "/api/runtime/sessions/s-http-nunca-abierta/hechos-docente",
        json={"contenido": {"competencia": "COMP-2", "items_incorrectos": []}},
    )
    assert resp.status_code == 404


def _sembrar_escalada_en_sesion_http(identidad_json: dict) -> tuple[str, str]:
    """Añade tensión + escalada directamente contra los reducers, sobre
    la MISMA sesión/esquema ya abierta vía HTTP (mismo Postgres real que
    `almacenes()` usa) — igual técnica que test_E3_resolver_escalada.py;
    no organiza una segunda tubería, solo evita esperar a RFC-0006 §4
    para poder ejercitar el endpoint HTTP con una escalada real. Retorna
    (escalada_id, claim_remediar_id) como texto."""
    from decimal import Decimal

    from runtime.engine.checkpoint import AlmacenTransiciones, encadenar
    from runtime.kernel.reducers import registrar_claim, registrar_deliberacion, registrar_fact
    from runtime.kernel.state.entries import (
        Capacidad,
        Escalada,
        OrigenProvenance,
        Provenance,
        TipoClaim,
    )
    from runtime.kernel.state.state import Identidad, LearningState

    identidad = Identidad(**identidad_json)
    almacen = AlmacenTransiciones(
        os.environ["RUNTIME_DATABASE_URL"], esquema=os.environ["RUNTIME_DATABASE_SCHEMA"]
    )
    estado = LearningState(identidad=identidad, contexto={})
    registros = almacen.leer(identidad.session_id)
    if registros:
        estado = LearningState(identidad=identidad, contexto={})
        from runtime.engine.checkpoint import reconstruir
        estado = reconstruir(identidad, contexto={}, registros=registros)

    def _aplicar(operacion, argumentos, estado, registros):
        funcion = {"registrar_fact": registrar_fact, "registrar_claim": registrar_claim,
                   "registrar_deliberacion": registrar_deliberacion}[operacion]
        resultado = funcion(estado, **argumentos)
        assert resultado.__class__.__name__ == "Aplicado", resultado
        from runtime.kernel.transitions import TransitionIntent
        intent = TransitionIntent(productor="test", operacion=operacion, argumentos=argumentos, base=0)
        registro = encadenar(identidad, registros, {"intent": intent, "eventos": resultado.eventos})
        almacen.persistir(registro)
        return resultado.estado, registros + (registro,)

    estado, registros = _aplicar(
        "registrar_fact",
        {"autor": Capacidad.EVALUAR, "contenido": {"competencia": "COMP-2", "items_incorrectos": [3]},
         "provenance": Provenance.de(OrigenProvenance.INSTRUMENTO, banco="v2")},
        estado, registros,
    )
    fact_id = estado.facts[-1].id

    estado, registros = _aplicar(
        "registrar_claim",
        {"autor": Capacidad.DIAGNOSTICAR, "tipo": TipoClaim.INTERPRETACION,
         "asunto": "dominio(COMP-2)", "afirmacion": {"dominada": False, "errores": 1},
         "respaldo": (fact_id,), "confianza": Decimal("0.75"),
         "provenance": Provenance.de(OrigenProvenance.REGLA, id="scoring-v1")},
        estado, registros,
    )
    interpretacion_id = estado.claims[-1].id

    estado, registros = _aplicar(
        "registrar_claim",
        {"autor": Capacidad.REMEDIAR, "tipo": TipoClaim.PROPUESTA,
         "asunto": "siguiente-paso(sesion)", "afirmacion": {"accion": "reforzar"},
         "respaldo": (interpretacion_id,), "confianza": Decimal("0.60"),
         "provenance": Provenance.de(OrigenProvenance.REGLA, id="remediacion-v1")},
        estado, registros,
    )
    remediar_id = estado.claims[-1].id

    estado, registros = _aplicar(
        "registrar_claim",
        {"autor": Capacidad.ORIENTAR, "tipo": TipoClaim.PROPUESTA,
         "asunto": "siguiente-paso(sesion)", "afirmacion": {"accion": "avanzar-con-andamiaje"},
         "respaldo": (interpretacion_id,), "confianza": Decimal("0.58"),
         "provenance": Provenance.de(OrigenProvenance.REGLA, id="orientacion-v1")},
        estado, registros,
    )
    orientar_id = estado.claims[-1].id

    estado, registros = _aplicar(
        "registrar_deliberacion",
        {"participantes": (remediar_id, orientar_id), "resultado": Escalada(destinatario="docente")},
        estado, registros,
    )
    escalada_id = estado.deliberaciones[-1].id

    return str(escalada_id), str(remediar_id)


def test_resolver_escalada_via_http(client, autenticado, autenticado_docente):
    abierta = client.post("/api/runtime/sessions", json={"session_id": "s-http-hitl-escalada"})
    identidad_json = abierta.json()
    escalada_id, claim_elegido = _sembrar_escalada_en_sesion_http(identidad_json)

    resp = client.post(
        "/api/runtime/sessions/s-http-hitl-escalada/escaladas/resolver",
        json={
            "escalada_id": escalada_id,
            "claim_elegido": claim_elegido,
            "human_reason": "el estudiante ya mostró fatiga",
        },
    )
    assert resp.status_code == 200, resp.text

    estado = client.get("/api/runtime/sessions/s-http-hitl-escalada/estado").json()
    cierre = next(d for d in estado["deliberaciones"] if d.get("enlaza_a") == escalada_id)
    assert cierre["resultado"]["regla"] == "decision-humana"
    assert any(dec["origen"] == cierre["id"] for dec in estado["decisiones"])


def test_resolver_escalada_con_claim_ajeno_es_422(client, autenticado, autenticado_docente):
    abierta = client.post("/api/runtime/sessions", json={"session_id": "s-http-hitl-claim-ajeno"})
    identidad_json = abierta.json()
    escalada_id, _claim_elegido = _sembrar_escalada_en_sesion_http(identidad_json)

    resp = client.post(
        "/api/runtime/sessions/s-http-hitl-claim-ajeno/escaladas/resolver",
        json={"escalada_id": escalada_id, "claim_elegido": "T-999999/e1"},
    )
    assert resp.status_code == 422


def test_hecho_docente_requiere_rol_docente(client, autenticado):
    # Sin override de aget_current_docente: mismo gap ya documentado en el
    # docstring del módulo (ninguna ruta async se ejercita sin autenticar
    # de verdad) — 401 (sin token real) o 403 (rol) son ambos rechazo.
    client.post("/api/runtime/sessions", json={"session_id": "s-http-hitl-sin-rol"})
    resp = client.post(
        "/api/runtime/sessions/s-http-hitl-sin-rol/hechos-docente",
        json={"contenido": {"competencia": "COMP-2", "items_incorrectos": []}},
    )
    assert resp.status_code in (401, 403)
