"""IT-04 -- Integracion Runtime <-> PostgreSQL (almacen de eventos).

Componentes reales: app/services/runtime_connection.py (AlmacenTransiciones,
AlmacenMemoria via psycopg2 directo, no SQLAlchemy) escribiendo en el
esquema `runtime` del MISMO PostgreSQL que usa la plataforma
(postgresql://.../upao_mas_edu), pero con una via de conexion
completamente independiente de la API. Se verifica que una accion del
runtime disparada por HTTP efectivamente persiste filas reales en
runtime_sessions/runtime_transitions.
"""
import uuid

import requests

from tests.integration.conftest import BASE_URL, PG_URL, auth_header


def test_hecho_registrado_por_boundary_persiste_en_esquema_runtime_de_postgresql(
    estudiante_session, pg_conn
):
    session_id = f"s-it04-{uuid.uuid4().hex[:8]}"
    headers = auth_header(estudiante_session)

    print(f"[IT-04] Abriendo sesion de runtime real: {session_id}")
    abierta = requests.post(
        f"{BASE_URL}/api/runtime/sessions", json={"session_id": session_id}, headers=headers, timeout=15
    )
    assert abierta.status_code == 200
    identidad = abierta.json()

    print("[IT-04] Registrando un hecho real via /api/runtime/hechos")
    entregado = requests.post(
        f"{BASE_URL}/api/runtime/hechos",
        json={
            "identidad": identidad,
            "contenido": {"competencia": "COMP-2", "items_incorrectos": [3, 4, 8]},
            "origen": "instrumento",
        },
        headers=headers,
        timeout=30,
    )
    assert entregado.status_code == 200

    print(f"[IT-04] Verificando persistencia directa en PostgreSQL ({PG_URL}), esquema runtime")
    with pg_conn.cursor() as cur:
        cur.execute("SELECT session_id FROM runtime.runtime_sessions WHERE session_id = %s", (session_id,))
        fila_sesion = cur.fetchone()
        cur.execute(
            "SELECT count(*) FROM runtime.runtime_transitions WHERE session_id = %s", (session_id,)
        )
        (num_transiciones,) = cur.fetchone()
    print(f"[IT-04] runtime_sessions: {fila_sesion} | runtime_transitions para esta sesion: {num_transiciones}")

    assert fila_sesion is not None, (
        "app/services/runtime_connection.py debio insertar la sesion en runtime.runtime_sessions "
        "por una via de conexion (psycopg2 directo) totalmente independiente de la API que la creo"
    )
    assert num_transiciones > 0, "El hecho registrado debio generar al menos una transicion persistida"
